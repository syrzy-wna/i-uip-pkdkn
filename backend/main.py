"""Pelayan REST API FastAPI bagi UIP-Command (Unit Inspektorat & Perundangan KKM)."""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
from collections import defaultdict, deque
from dataclasses import asdict
from typing import Any, Dict, Optional
from urllib.parse import quote, urlparse

from fastapi import APIRouter, Depends, FastAPI, File, Form, Header, HTTPException, Query, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from backend.core.config import settings
from backend.core.database import get_uip_db
from backend.core.model_router import UIPModelRouter
from backend.services.compound_checker import CompoundNoticeChecker
from backend.services.dev_vault import DevArchiveVaultService, sanitize_filename
from backend.services.doc_generator import generate_docx_by_type
from backend.services.ip_auditor import IPTechnicalAuditor, extract_text_from_upload
from backend.services.sample_cases import SAMPLE_CASES
from backend.services.uip_advisor import UIPAdvisorService

logger = logging.getLogger("uip.dev_vault")
MAX_UPLOAD_BYTES = 15 * 1024 * 1024  # Had 15 MB bagi setiap muat naik fail
IMAGE_UPLOAD_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")
_ALLOWED_OLLAMA_HOSTS = {"127.0.0.1", "localhost", "::1", "host.docker.internal"}

db_service = get_uip_db()
router_service = UIPModelRouter()
auditor_service = IPTechnicalAuditor(router=router_service)
compound_checker = CompoundNoticeChecker()
advisor_service = UIPAdvisorService(router=router_service, db=db_service)
dev_vault_service = DevArchiveVaultService(db=db_service, redactor=router_service.redactor)

_rate_limit_lock = threading.Lock()
_rate_limit_buckets: Dict[str, deque[float]] = defaultdict(deque)


def _check_rate_limit(bucket_key: str, max_requests: int, window_sec: float = 60.0) -> None:
    """Penghad kadar permintaan (sliding window) dalam memori untuk melindungi titik akhir pengesahan & AI."""
    now = time.monotonic()
    with _rate_limit_lock:
        dq = _rate_limit_buckets[bucket_key]
        while dq and now - dq[0] > window_sec:
            dq.popleft()
        if len(dq) >= max_requests:
            raise HTTPException(
                status_code=429,
                detail="Terlalu banyak permintaan dalam masa singkat. Sila tunggu sebentar dan cuba semula.",
            )
        dq.append(now)


def _client_ip(request: Optional[Request]) -> str:
    if request is None:
        return "local"
    xff = request.headers.get("x-forwarded-for") or ""
    if xff:
        return xff.split(",")[0].strip() or "unknown"
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _validate_ollama_base_url(raw_url: Optional[str]) -> Optional[str]:
    if raw_url is None:
        return None
    val = raw_url.strip()
    if not val:
        return ""
    parsed = urlparse(val)
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in ("http", "https") or host not in _ALLOWED_OLLAMA_HOSTS:
        raise HTTPException(
            status_code=400,
            detail="Alamat pelayan Ollama hanya dibenarkan pada hos tempatan (localhost / 127.0.0.1 / host.docker.internal).",
        )
    return val


async def _read_upload_limited(upload: UploadFile, max_bytes: int = MAX_UPLOAD_BYTES) -> bytes:
    """Baca fail muat naik secara berperingkat dan sekat fail melebihi had saiz (413)."""
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await upload.read(512 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"Saiz fail melebihi had maksimum ({max_bytes // (1024 * 1024)} MB). Sila mampatkan fail dan cuba semula.",
            )
        chunks.append(chunk)
    return b"".join(chunks)


def _merge_authoritative_officer(
    current_officer: Dict[str, Any], requested_profile: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """Kunci medan identiti rasmi kepada pegawai yang log masuk; hanya terima pilihan perkakasan S.90A jika ada."""
    merged = dict(current_officer)
    if isinstance(requested_profile, dict):
        for safe_hw in ("default_computer_desc", "default_printer_desc", "default_camera_desc"):
            val = requested_profile.get(safe_hw)
            if isinstance(val, str) and val.strip():
                merged[safe_hw] = val.strip()
    return merged


def _archive_safely(**kwargs: Any) -> None:
    """Merekod ke Arkib & Bucket Dev secara non-fatal agar aliran pengguna kekal lancar."""
    try:
        dev_vault_service.archive_event(**kwargs)
    except Exception as exc:
        logger.warning("Arkib DevVault gagal (non-fatal): %s", exc)


def _extract_bearer_token(
    authorization: Optional[str], x_auth_token: Optional[str] = None
) -> str:
    if x_auth_token and x_auth_token.strip():
        return x_auth_token.strip()
    if not authorization:
        return ""
    parts = authorization.strip().split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    return authorization.strip()


def _resolve_current_officer(
    authorization: Optional[str], x_auth_token: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    token = _extract_bearer_token(authorization, x_auth_token)
    if not token:
        return None
    return db_service.get_user_by_token(token)


def _require_authenticated_officer(
    authorization: Optional[str] = Header(default=None),
    x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
) -> Dict[str, Any]:
    user = _resolve_current_officer(authorization, x_auth_token)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Sila log masuk ke akaun pegawai anda terlebih dahulu untuk meneruskan.",
        )
    return user


def _require_dev_admin(
    current_officer: Dict[str, Any] = Depends(_require_authenticated_officer),
) -> Dict[str, Any]:
    email = str(current_officer.get("email") or "").strip().lower()
    if email not in settings.dev_admin_emails:
        raise HTTPException(
            status_code=403,
            detail="Halaman ini terhad kepada pentadbir sistem sahaja.",
        )
    return current_officer


def _est_tokens(text: Optional[str]) -> int:
    if not text:
        return 0
    return max(1, len(text) // 4)


_is_cloud_run = bool(os.getenv("K_SERVICE"))

app = FastAPI(
    title="UIP-Command API",
    description=(
        "Aplikasi Pengurusan Kertas Siasatan (IP), Notis Kompaun & Semakan Pra-TPR "
        "untuk Unit Inspektorat dan Perundangan (UIP), Kementerian Kesihatan Malaysia."
    ),
    version="2.6.0",
    docs_url=None if _is_cloud_run else "/docs",
    redoc_url=None if _is_cloud_run else "/redoc",
    openapi_url=None if _is_cloud_run else "/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)


@app.exception_handler(Exception)
async def global_json_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Ralat dalaman tidak dijangka pada %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Ralat dalaman pelayan. Sila cuba sebentar lagi atau hubungi pentadbir sistem."},
    )


class RedactRequest(BaseModel):
    text: str = Field(..., min_length=1)
    use_ollama: bool = True


class RehydrateRequest(BaseModel):
    text: str
    token_map: Dict[str, str]


class GenerateDraftRequest(BaseModel):
    case_text: str = Field(..., min_length=1)
    akta_utama: str = "Akta 852"
    workflow: str = "ip_builder"
    use_ollama: bool = True
    fast_mode: bool = True
    case_id: Optional[str] = None
    officer_profile: Optional[Dict[str, Any]] = None


class RegisterAccountRequest(BaseModel):
    email: str
    password: str
    full_name: str
    ic_number: str = ""
    designation: str = "Penolong Pegawai Kesihatan Persekitaran (PPKP)"
    grade: str = "U5"
    kkm_authority_card_no: str = ""
    prosecution_authorization_no: str = ""
    state_jkn: str = ""
    district_pkd: str = ""
    office_address: str = ""
    unit_assignment: str = "Unit Inspektorat dan Perundangan (UIP)"
    default_magistrate_court: str = ""
    system_role: str = "PEGAWAI_PENYIASAT"
    default_computer_desc: str = "Komputer Meja Rasmi KKM Pejabat Kesihatan"
    default_printer_desc: str = "Pencetak Laser Warna Pejabat Kesihatan"
    default_camera_desc: str = "Kamera Digital Rasmi Pejabat Kesihatan"


class LoginRequest(BaseModel):
    email: str
    password: str


class GoogleAuthRequest(BaseModel):
    id_token: Optional[str] = None
    access_token: Optional[str] = None
    kkm_authority_card_no: str = ""
    grade: str = "U5"
    designation: str = "Penolong Pegawai Kesihatan Persekitaran (PPKP)"
    state_jkn: str = ""
    district_pkd: str = ""


class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = None
    ic_number: Optional[str] = None
    designation: Optional[str] = None
    grade: Optional[str] = None
    kkm_authority_card_no: Optional[str] = None
    prosecution_authorization_no: Optional[str] = None
    state_jkn: Optional[str] = None
    district_pkd: Optional[str] = None
    office_address: Optional[str] = None
    unit_assignment: Optional[str] = None
    default_magistrate_court: Optional[str] = None
    system_role: Optional[str] = None
    default_computer_desc: Optional[str] = None
    default_printer_desc: Optional[str] = None
    default_camera_desc: Optional[str] = None


class AdvisorConsultRequest(BaseModel):
    question: str = ""
    akta_hint: str = "Semua"
    scenario_id: Optional[str] = None
    use_ai: bool = False
    officer_profile: Optional[Dict[str, Any]] = None


class AdvisorSopBrainRequest(BaseModel):
    question: str
    akta_hint: str = "Semua"
    guna_cache: Optional[bool] = None


class ExportDocxRequest(BaseModel):
    doc_type: str = Field(
        default="pakej_ip",
        description="borang_114 | diari_siasatan | rakaman_112 | pakej_ip | notis_kompaun",
    )
    payload: Dict[str, Any]


class CompoundCheckRequest(BaseModel):
    no_notis: str = ""
    nama_penerima: str = ""
    no_kp: str = ""
    nama_premis: str = ""
    alamat_kejadian: str = ""
    no_ssm: str = ""
    tarikh_masa: str = ""
    peruntukan_undang: str = ""
    peruntukan_kompaun: str = ""
    kesalahan_ringkas: str = ""
    amaun_kompaun_rm: str = ""
    tempoh_bayaran: str = "14 hari"
    pegawai_pengeluar: str = ""
    no_kad_kuasa: str = ""
    status_serahan: str = "tandatangan_terima"
    saksi_ppkp: str = ""


class RuntimeSettingsRequest(BaseModel):
    gemini_api_key: Optional[str] = None
    google_client_id: Optional[str] = None
    ollama_base_url: Optional[str] = None
    ollama_model: Optional[str] = None
    decision_model: Optional[str] = None
    multimodal_model: Optional[str] = None
    reasoning_model: Optional[str] = None
    standard_fallback_model: Optional[str] = None


class UpsertCaseRequest(BaseModel):
    id: Optional[str] = None
    no_ip: Optional[str] = None
    tajuk_kes: Optional[str] = None
    akta_utama: str = "Akta 852"
    workflow: str = "audit_ip"
    badge: str = "Kes PKD"
    nama_okt: str = ""
    no_kp_okt: str = ""
    nama_premis: str = ""
    no_ssm: str = ""
    alamat_kejadian: str = ""
    tarikh_kejadian: str = ""
    masa_kejadian: str = ""
    pegawai_io: str = ""
    no_kad_kuasa: str = ""
    status_kes: str = "DALAM SIASATAN"
    skor_audit: Optional[float] = None
    case_text: str = ""
    checklist: Optional[Dict[str, str]] = None
    audit_report: Optional[Dict[str, Any]] = None
    draft: Optional[Dict[str, Any]] = None


@app.get("/")
def root() -> Dict[str, str]:
    return {
        "aplikasi": "UIP-Command API",
        "status": "aktif",
        "dokumentasi": "/docs" if not _is_cloud_run else "disabled",
    }


@app.get("/healthz")
@app.get("/api/health")
def healthz() -> Dict[str, str]:
    return {
        "status": "ok",
        "db": "postgres" if db_service.use_postgres else "sqlite",
    }


@app.get("/api/status")
def get_status(
    authorization: Optional[str] = Header(default=None),
    x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
) -> Dict[str, Any]:
    from backend.rag.legal_engine import get_legal_library

    caller = _resolve_current_officer(authorization, x_auth_token)
    is_admin = bool(caller and str(caller.get("email") or "").strip().lower() in settings.dev_admin_emails)

    payload = dict(router_service.get_system_status())
    if not is_admin:
        payload["masked_api_key"] = "********" if settings.has_gemini_key else ""
        if isinstance(payload.get("ollama"), dict):
            payload["ollama"] = {
                **payload["ollama"],
                "base_url": "",
            }
    payload["cloud_run_revision"] = os.getenv("K_REVISION") or "local"
    payload["statute_library_version"] = get_legal_library().statute_library_version
    try:
        from backend.services.sop_brain import get_sop_brain

        payload["sop_brain"] = get_sop_brain().get_status_summary()
    except Exception:
        payload["sop_brain"] = None
    return payload


@app.get("/api/settings")
def get_runtime_settings(
    authorization: Optional[str] = Header(default=None),
    x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
) -> Dict[str, Any]:
    caller = _resolve_current_officer(authorization, x_auth_token)
    is_admin = bool(caller and str(caller.get("email") or "").strip().lower() in settings.dev_admin_emails)
    return {
        "gemini_api_key_configured": settings.has_gemini_key,
        "masked_gemini_api_key": settings.masked_gemini_key if is_admin else ("********" if settings.has_gemini_key else ""),
        "google_client_id": settings.google_client_id,
        "google_client_id_configured": bool(settings.google_client_id),
        "ollama_base_url": settings.ollama_base_url if is_admin else "",
        "ollama_model": settings.ollama_model,
        "decision_model": settings.decision_model,
        "multimodal_model": settings.multimodal_model,
        "reasoning_model": settings.reasoning_model,
        "standard_fallback_model": settings.standard_fallback_model,
    }


@app.post("/api/settings")
def update_runtime_settings(
    req: RuntimeSettingsRequest,
    _admin: Dict[str, Any] = Depends(_require_dev_admin),
) -> Dict[str, Any]:
    dump = req.model_dump()
    if dump.get("ollama_base_url") is not None:
        dump["ollama_base_url"] = _validate_ollama_base_url(dump["ollama_base_url"])
    db_service.save_runtime_settings(dump)
    router_service.refresh_clients()
    advisor_service.clear_cache()
    return {
        "status": "disimpan",
        "system_status": router_service.get_system_status(),
        "settings": {
            "gemini_api_key_configured": settings.has_gemini_key,
            "masked_gemini_api_key": settings.masked_gemini_key,
            "google_client_id": settings.google_client_id,
            "google_client_id_configured": bool(settings.google_client_id),
            "ollama_base_url": settings.ollama_base_url,
            "ollama_model": settings.ollama_model,
            "decision_model": settings.decision_model,
            "multimodal_model": settings.multimodal_model,
            "reasoning_model": settings.reasoning_model,
            "standard_fallback_model": settings.standard_fallback_model,
        },
    }


@app.get("/api/samples")
def get_samples(
    _officer: Dict[str, Any] = Depends(_require_authenticated_officer),
) -> Dict[str, Any]:
    return {"samples": SAMPLE_CASES}


@app.get("/api/cases")
def list_cases(
    current_officer: Dict[str, Any] = Depends(_require_authenticated_officer),
) -> Dict[str, Any]:
    is_admin = bool(current_officer.get("is_dev_admin"))
    return {
        "cases": db_service.list_cases(
            owner_user_id=str(current_officer.get("id") or ""),
            is_admin=is_admin,
        )
    }


@app.post("/api/cases")
def save_case(
    req: UpsertCaseRequest,
    current_officer: Dict[str, Any] = Depends(_require_authenticated_officer),
) -> Dict[str, Any]:
    t0 = time.perf_counter()
    is_admin = bool(current_officer.get("is_dev_admin"))
    try:
        saved = db_service.upsert_case(
            req.model_dump(exclude_none=True),
            owner_user_id=str(current_officer.get("id") or ""),
            is_admin=is_admin,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    latency_ms = int((time.perf_counter() - t0) * 1000)
    db_service.log_activity(
        action_type="SIMPAN_KES_IP",
        action_detail=f"Simpan fail {saved.get('no_ip', '')} ({saved.get('akta_utama', '')})",
        user=current_officer,
        model_used="local-sqlite-db",
        latency_ms=latency_ms,
    )
    _archive_safely(
        category="DRAFT_COMPOUND",
        action_type="SIMPAN_KES_IP",
        endpoint="/api/cases",
        user=current_officer,
        title=f"Simpan Kes IP: {saved.get('no_ip') or saved.get('tajuk_kes') or saved.get('id')}",
        akta_utama=str(saved.get("akta_utama") or ""),
        case_id=str(saved.get("id") or ""),
        raw_input_text=str(saved.get("case_text") or ""),
        request_payload=req.model_dump(exclude_none=True),
        analysis_payload=saved,
        model_used="local-sqlite-db",
        latency_ms=latency_ms,
        status_summary=str(saved.get("status_kes") or ""),
    )
    return {"case": saved}


@app.delete("/api/cases/{case_id}")
def delete_case(
    case_id: str,
    current_officer: Dict[str, Any] = Depends(_require_authenticated_officer),
) -> Dict[str, Any]:
    is_admin = bool(current_officer.get("is_dev_admin"))
    try:
        deleted = db_service.delete_case(
            case_id,
            owner_user_id=str(current_officer.get("id") or ""),
            is_admin=is_admin,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    if not deleted:
        raise HTTPException(status_code=404, detail="Kes IP tidak dijumpai.")
    return {"deleted": True, "id": case_id}


@app.post("/api/redact")
def redact_text(
    req: RedactRequest,
    _officer: Dict[str, Any] = Depends(_require_authenticated_officer),
) -> Dict[str, Any]:
    result = router_service.redactor.redact(req.text, use_ollama=req.use_ollama)
    return {
        "original_text": result.original_text,
        "redacted_text": result.redacted_text,
        "token_map": result.token_map,
        "entities": [asdict(e) for e in result.entities],
        "engine_used": result.engine_used,
        "ollama_available": result.ollama_available,
        "warnings": result.warnings,
    }


@app.post("/api/rehydrate")
def rehydrate_text(
    req: RehydrateRequest,
    _officer: Dict[str, Any] = Depends(_require_authenticated_officer),
) -> Dict[str, str]:
    return {
        "restored_text": router_service.redactor.rehydrate(req.text, req.token_map)
    }


@app.post("/api/check-compound")
def check_compound_notice(
    req: CompoundCheckRequest,
    current_officer: Dict[str, Any] = Depends(_require_authenticated_officer),
) -> Dict[str, Any]:
    t0 = time.perf_counter()
    res = compound_checker.check_notice(req.model_dump())
    latency_ms = int((time.perf_counter() - t0) * 1000)
    db_service.log_activity(
        action_type="SEMAK_KOMPAUN",
        action_detail=f"Semak notis kompaun {req.no_notis or '(draf)'} - {req.peruntukan_undang or 'Umum'}",
        user=current_officer,
        model_used="local-compound-validator",
        latency_ms=latency_ms,
    )
    _archive_safely(
        category="DRAFT_COMPOUND",
        action_type="SEMAK_KOMPAUN",
        endpoint="/api/check-compound",
        user=current_officer,
        title=f"Semak Notis Kompaun: {req.no_notis or req.nama_premis or '(Draf)'}",
        akta_utama=req.peruntukan_undang or "",
        raw_input_text=f"Premis: {req.nama_premis}\nOKS: {req.nama_penerima} ({req.no_kp})\nPeruntukan: {req.peruntukan_undang}\nKesalahan: {req.kesalahan_ringkas}\nAmaun: {req.amaun_kompaun_rm}".strip(),
        raw_response_text=res.get("suggested_offense_text", ""),
        request_payload=req.model_dump(),
        analysis_payload=res,
        model_used="local-compound-validator",
        latency_ms=latency_ms,
        status_summary=f"{res.get('readiness_status', '')} ({res.get('score_percent', 0)}%)",
    )
    return res


@app.post("/api/audit-ip")
async def audit_ip_endpoint(
    text: Optional[str] = Form(default=None),
    akta_utama: str = Form(default="Akta 852"),
    use_ollama: bool = Form(default=True),
    fast_mode: bool = Form(default=False),
    case_id: Optional[str] = Form(default=None),
    file: Optional[UploadFile] = File(default=None),
    current_officer: Dict[str, Any] = Depends(_require_authenticated_officer),
) -> Dict[str, Any]:
    if not fast_mode:
        _check_rate_limit(f"ai:{current_officer.get('id') or 'anon'}", max_requests=25, window_sec=60.0)
    t0 = time.perf_counter()
    raw_text = (text or "").strip()
    filename = "teks_kertas_siasatan.txt"
    upload_bytes: Optional[bytes] = None
    upload_filename: Optional[str] = None
    upload_mime: Optional[str] = None

    if file is not None:
        file_bytes = await _read_upload_limited(file)
        filename = file.filename or "kertas_siasatan.pdf"
        if not file_bytes:
            raise HTTPException(status_code=400, detail="Fail yang dimuat naik kosong.")
        upload_bytes = file_bytes
        upload_filename = filename
        upload_mime = file.content_type or "application/octet-stream"
        low_fn = filename.lower()
        try:
            if low_fn.endswith(IMAGE_UPLOAD_EXTENSIONS) or upload_mime.startswith("image/"):
                ocr_res = await run_in_threadpool(
                    router_service.extract_multimodal_evidence,
                    file_bytes=file_bytes,
                    filename=filename,
                    mime_type=upload_mime,
                    doc_hint="dokumen_kertas_siasatan",
                )
                extracted = (ocr_res.raw_text or ocr_res.structured_summary or "").strip()
            else:
                extracted = await run_in_threadpool(extract_text_from_upload, file_bytes, filename)
                if low_fn.endswith(".pdf") and len(re.sub(r"--- Muka Surat \d+ ---|\s+", "", extracted)) < 40:
                    # PDF imbasan tanpa lapisan teks -> ekstrak melalui OCR multimodal
                    ocr_res = await run_in_threadpool(
                        router_service.extract_multimodal_evidence,
                        file_bytes=file_bytes,
                        filename=filename,
                        mime_type="application/pdf",
                        doc_hint="dokumen_kertas_siasatan",
                    )
                    ocr_text = (ocr_res.raw_text or ocr_res.structured_summary or "").strip()
                    if ocr_text:
                        extracted = ocr_text
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        ext_clean = extracted.strip()
        if ext_clean:
            if not raw_text:
                raw_text = ext_clean
            elif ext_clean not in raw_text:
                raw_text = f"{ext_clean}\n\n{raw_text}".strip()

    if not raw_text:
        raise HTTPException(
            status_code=400,
            detail="Sila masukkan teks Kertas Siasatan atau muat naik fail PDF/DOCX/TXT/Gambar.",
        )

    report = await run_in_threadpool(
        auditor_service.audit_ip,
        raw_text=raw_text,
        akta_utama=akta_utama,
        filename=filename,
        use_ollama_redaction=use_ollama,
        fast_mode=fast_mode,
    )
    report_dict = {
        "filename": report.filename,
        "akta_utama": report.akta_utama,
        "overall_score": report.overall_score,
        "readiness_status": report.readiness_status,
        "counts": report.counts,
        "criteria_results": [asdict(c) for c in report.criteria_results],
        "tpr_summary_notes": report.tpr_summary_notes,
        "kuiri_tpr": report.kuiri_tpr,
        "ip_folder_checklist": report.ip_folder_checklist,
        "statutory_citations": report.statutory_citations,
        "redaction_summary": report.redaction_summary,
        "models_used": report.models_used,
        "extracted_text": report.extracted_text,
        "sop_audit_pra_tpr": report.sop_audit_pra_tpr,
    }

    if case_id:
        is_admin = bool(current_officer.get("is_dev_admin"))
        try:
            db_service.upsert_case(
                {
                    "id": case_id,
                    "akta_utama": akta_utama,
                    "case_text": raw_text,
                    "status_kes": report.readiness_status,
                    "skor_audit": report.overall_score,
                    "audit_report": report_dict,
                },
                owner_user_id=str(current_officer.get("id") or ""),
                is_admin=is_admin,
            )
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc))

    audit_model = str((report.models_used or {}).get("decision_engine") or "local-statute-fallback")
    is_gemini_audit = (
        "gemini" in audit_model.lower()
        and "fallback" not in audit_model.lower()
        and "pantas" not in audit_model.lower()
        and "cache" not in audit_model.lower()
    )
    latency_ms = int((time.perf_counter() - t0) * 1000)
    db_service.log_activity(
        action_type="AUDIT_IP_20",
        action_detail=f"Semak 20 Kriteria ({akta_utama}) — Skor {report.overall_score:.1f}% ({report.readiness_status})",
        user=current_officer,
        model_used=audit_model,
        est_input_tokens=_est_tokens(raw_text) if is_gemini_audit else 0,
        est_output_tokens=550 if is_gemini_audit else 0,
        latency_ms=latency_ms,
    )
    _archive_safely(
        category="AUDIT_IP",
        action_type="AUDIT_IP_20",
        endpoint="/api/audit-ip",
        user=current_officer,
        title=f"Audit IP ({akta_utama}): {upload_filename or filename}",
        akta_utama=akta_utama,
        case_id=case_id or "",
        raw_input_text=raw_text,
        raw_response_text="\n".join(report.tpr_summary_notes or []),
        request_payload={"akta_utama": akta_utama, "filename": filename, "fast_mode": fast_mode, "case_id": case_id},
        analysis_payload=report_dict,
        model_used=audit_model,
        is_cloud_api=is_gemini_audit,
        latency_ms=latency_ms,
        status_summary=f"{report.readiness_status} ({report.overall_score:.1f}%)",
        attachment_bytes=upload_bytes,
        attachment_filename=upload_filename,
        attachment_mime=upload_mime,
    )

    return report_dict


@app.post("/api/extract-evidence")
async def extract_evidence_endpoint(
    file: UploadFile = File(...),
    doc_hint: str = Form(default="bukti_kesalahan"),
    current_officer: Dict[str, Any] = Depends(_require_authenticated_officer),
) -> Dict[str, Any]:
    _check_rate_limit(f"ai:{current_officer.get('id') or 'anon'}", max_requests=25, window_sec=60.0)
    t0 = time.perf_counter()
    file_bytes = await _read_upload_limited(file)
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Fail bukti kosong.")
    safe_filename = file.filename or "bukti.jpg"
    try:
        result = await run_in_threadpool(
            router_service.extract_multimodal_evidence,
            file_bytes=file_bytes,
            filename=safe_filename,
            mime_type=file.content_type or "application/octet-stream",
            doc_hint=doc_hint,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    is_cloud = "gemini" in (result.model_used or "").lower() and "sim" not in (result.model_used or "").lower()
    latency_ms = int((time.perf_counter() - t0) * 1000)
    db_service.log_activity(
        action_type="EKSTRAK_BUKTI_OCR",
        action_detail=f"Ekstrak gambar/fail bukti: {safe_filename} ({doc_hint})",
        user=current_officer,
        model_used=result.model_used,
        est_input_tokens=1300 if is_cloud else 0,
        est_output_tokens=450 if is_cloud else 0,
        latency_ms=latency_ms,
    )
    payload_out = {
        "filename": safe_filename,
        "extracted_fields": result.extracted_fields,
        "structured_summary": result.structured_summary,
        "raw_text": result.raw_text,
        "confidence": result.confidence,
        "model_used": result.model_used,
        "warnings": result.warnings,
    }
    _archive_safely(
        category="OCR_EVIDENCE",
        action_type="EKSTRAK_BUKTI_OCR",
        endpoint="/api/extract-evidence",
        user=current_officer,
        title=f"Ekstrak OCR ({doc_hint}): {safe_filename}",
        raw_input_text=result.raw_text or "",
        raw_response_text=result.structured_summary or "",
        request_payload={"doc_hint": doc_hint, "filename": safe_filename},
        analysis_payload=payload_out,
        model_used=result.model_used or "",
        is_cloud_api=is_cloud,
        latency_ms=latency_ms,
        status_summary=f"Keyakinan OCR {round((result.confidence or 0) * 100)}%",
        attachment_bytes=file_bytes,
        attachment_filename=safe_filename,
        attachment_mime=file.content_type or "application/octet-stream",
    )
    return payload_out


@app.post("/api/generate-draft")
def generate_draft_endpoint(
    req: GenerateDraftRequest,
    current_officer: Dict[str, Any] = Depends(_require_authenticated_officer),
) -> Dict[str, Any]:
    if not req.fast_mode:
        _check_rate_limit(f"ai:{current_officer.get('id') or 'anon'}", max_requests=25, window_sec=60.0)
    t0 = time.perf_counter()
    active_officer = _merge_authoritative_officer(current_officer, req.officer_profile)
    result = router_service.generate_legal_drafts(
        case_text=req.case_text,
        akta_utama=req.akta_utama,
        workflow=req.workflow,
        use_ollama_redaction=req.use_ollama,
        officer_profile=active_officer,
        fast_mode=req.fast_mode,
    )
    result_dict = asdict(result)
    if req.case_id:
        is_admin = bool(current_officer.get("is_dev_admin"))
        try:
            db_service.upsert_case(
                {
                    "id": req.case_id,
                    "akta_utama": req.akta_utama,
                    "case_text": req.case_text,
                    "draft": result_dict,
                },
                owner_user_id=str(current_officer.get("id") or ""),
                is_admin=is_admin,
            )
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc))
    draft_model = str((result.models_used or {}).get("legal_reasoning") or "local-template-engine")
    is_cloud = (
        "gemini" in draft_model.lower()
        and "templat" not in draft_model.lower()
        and "pantas" not in draft_model.lower()
        and "cache" not in draft_model.lower()
    )
    latency_ms = int((time.perf_counter() - t0) * 1000)
    db_service.log_activity(
        action_type="JANA_DRAF_IP",
        action_detail=f"Jana draf & Borang 114 ({req.akta_utama}, aliran: {req.workflow})",
        user=current_officer,
        model_used=draft_model,
        est_input_tokens=_est_tokens(req.case_text) if is_cloud else 0,
        est_output_tokens=_est_tokens(json.dumps(result.borang_114, ensure_ascii=False)) if is_cloud else 0,
        latency_ms=latency_ms,
    )
    _archive_safely(
        category="DRAFT_COMPOUND",
        action_type="JANA_DRAF_IP",
        endpoint="/api/generate-draft",
        user=current_officer,
        title=f"Jana Draf IP & Borang 114 ({req.akta_utama})",
        akta_utama=req.akta_utama,
        case_id=req.case_id or "",
        raw_input_text=req.case_text,
        raw_response_text=str((result.borang_114 or {}).get("teks_pertuduhan") or result.fakta_kes or ""),
        request_payload={"akta_utama": req.akta_utama, "workflow": req.workflow, "fast_mode": req.fast_mode, "case_id": req.case_id},
        analysis_payload=result_dict,
        model_used=draft_model,
        is_cloud_api=is_cloud,
        latency_ms=latency_ms,
        status_summary=f"Aliran {req.workflow}",
    )
    return result_dict


@app.post("/api/export-docx")
def export_docx_endpoint(
    req: ExportDocxRequest,
    current_officer: Dict[str, Any] = Depends(_require_authenticated_officer),
) -> Response:
    t0 = time.perf_counter()
    enriched_payload = dict(req.payload or {})
    if "officer_profile" not in enriched_payload or not isinstance(enriched_payload.get("officer_profile"), dict):
        enriched_payload["officer_profile"] = current_officer
    else:
        enriched_payload["officer_profile"] = _merge_authoritative_officer(
            current_officer, enriched_payload.get("officer_profile")
        )
    docx_bytes, filename = generate_docx_by_type(req.doc_type, enriched_payload)
    latency_ms = int((time.perf_counter() - t0) * 1000)
    db_service.log_activity(
        action_type="EXPORT_DOCX",
        action_detail=f"Muat turun fail Word rasmi: {filename} ({req.doc_type})",
        user=current_officer,
        model_used="python-docx-local",
        latency_ms=latency_ms,
    )
    _archive_safely(
        category="DRAFT_COMPOUND",
        action_type="EXPORT_DOCX",
        endpoint="/api/export-docx",
        user=current_officer,
        title=f"Eksport Dokumen Word: {filename}",
        akta_utama=str((req.payload or {}).get("akta_utama") or ""),
        raw_input_text=json.dumps(req.payload, ensure_ascii=False)[:12000],
        request_payload={"doc_type": req.doc_type},
        analysis_payload={"filename": filename, "doc_type": req.doc_type, "size_bytes": len(docx_bytes)},
        model_used="python-docx-local",
        latency_ms=latency_ms,
        status_summary=f"Word .docx ({len(docx_bytes)} bait)",
        attachment_bytes=docx_bytes,
        attachment_filename=filename,
        attachment_mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    safe_fname = sanitize_filename(filename, "dokumen.docx")
    encoded_fname = quote(safe_fname)
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f"attachment; filename=\"{safe_fname}\"; filename*=UTF-8''{encoded_fname}",
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-store, private",
        },
    )


@app.get("/api/rag/query")
def query_statutory_rag(
    q: str = Query(..., min_length=2),
    akta: Optional[str] = Query(default=None),
    top_k: int = Query(default=4, ge=1, le=10),
    current_officer: Dict[str, Any] = Depends(_require_authenticated_officer),
) -> Dict[str, Any]:
    t0 = time.perf_counter()
    chunks = router_service.rag_store.search_statutes(query=q, akta_filter=akta, top_k=top_k)
    latency_ms = int((time.perf_counter() - t0) * 1000)
    redacted_q = router_service.redactor.redact(q[:120], use_ollama=False).redacted_text
    db_service.log_activity(
        action_type="CARIAN_RAG_AKTA",
        action_detail=f"Cari teks akta ({akta or 'Semua'}): {redacted_q[:80]}",
        user=current_officer,
        model_used=router_service.rag_store.engine_name,
        latency_ms=latency_ms,
    )
    out = {
        "query": q,
        "engine": router_service.rag_store.engine_name,
        "results": [asdict(c) for c in chunks],
    }
    _archive_safely(
        category="ADVISOR_QA",
        action_type="CARIAN_RAG_AKTA",
        endpoint="/api/rag/query",
        user=current_officer,
        title=f"Carian Akta RAG ({akta or 'Semua'}): {q[:90]}",
        akta_utama=akta or "Semua",
        raw_input_text=q,
        raw_response_text="\n".join(f"[{c.akta_code} {c.section}] {c.text[:200]}" for c in chunks),
        request_payload={"q": q, "akta": akta, "top_k": top_k},
        analysis_payload=out,
        model_used=router_service.rag_store.engine_name,
        latency_ms=latency_ms,
        status_summary=f"{len(chunks)} seksyen dijumpai",
    )
    return out


@app.post("/api/rag/ingest")
async def ingest_statutory_act(
    file: UploadFile = File(...),
    statute_id: Optional[str] = Form(default=None),
    official_title_bm: Optional[str] = Form(default=None),
    act_number_or_pu: Optional[str] = Form(default=None),
    verified_by_admin: bool = Form(default=False),
    current_officer: Dict[str, Any] = Depends(_require_dev_admin),
) -> Dict[str, Any]:
    from backend.rag.legal_engine import get_legal_library

    t0 = time.perf_counter()
    raw_bytes = await _read_upload_limited(file)
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="Fail akta kosong.")
    fname = file.filename or "akta_tambahan.txt"
    if not fname.lower().endswith((".txt", ".pdf", ".md")):
        raise HTTPException(status_code=400, detail="Hanya fail .txt, .md atau .pdf disokong.")
    try:
        total_chunks = await run_in_threadpool(router_service.rag_store.ingest_uploaded_file, fname, raw_bytes)
        legal_lib = get_legal_library()
        ingest_meta = await run_in_threadpool(
            legal_lib.ingest_statute_bytes,
            filename=fname,
            raw_bytes=raw_bytes,
            statute_id=statute_id,
            official_title_bm=official_title_bm,
            act_number_or_pu=act_number_or_pu,
            verified_by_admin=verified_by_admin,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    stale_marked = db_service.invalidate_advisor_qa_cache(
        akta_code=ingest_meta["canonical_akta_code"],
        new_version=ingest_meta["statute_library_version"],
    )
    advisor_service.clear_cache()
    out = {
        "status": "berjaya",
        "filename": fname,
        "total_chunks_indexed": total_chunks,
        "acts_loaded": router_service.rag_store.list_available_acts(),
        "legal_library_ingest": ingest_meta,
        "stale_qa_cache_marked": stale_marked,
    }
    _archive_safely(
        category="OCR_EVIDENCE",
        action_type="INGEST_AKTA_RAG",
        endpoint="/api/rag/ingest",
        user=current_officer,
        title=f"Ingest Teks Akta RAG: {fname}",
        analysis_payload=out,
        model_used=router_service.rag_store.engine_name,
        latency_ms=int((time.perf_counter() - t0) * 1000),
        status_summary=f"{total_chunks} chunk diindeks",
        attachment_bytes=raw_bytes,
        attachment_filename=fname,
        attachment_mime=file.content_type or "application/octet-stream",
    )
    return out


# ---------------- Pustaka Akta Verbatim & Daftar Kesalahan Menyeluruh (Closed-Book Legal Engine) ----------------


class VerifyStatuteRequest(BaseModel):
    statute_id: Optional[str] = None
    offence_id: Optional[str] = None
    verified: bool = True


class UpdateOffenceRequest(BaseModel):
    offence_title: Optional[str] = None
    offence_section: Optional[str] = None
    read_together_with: Optional[list[str]] = None
    target_offender: Optional[str] = None
    mandatory_elements: Optional[list[Dict[str, Any]]] = None
    explicit_exclusions_and_traps: Optional[list[str]] = None
    penalty_section: Optional[str] = None
    penalty_first_offence: Optional[Dict[str, Any]] = None
    penalty_subsequent_offence: Optional[Dict[str, Any]] = None
    compound_info: Optional[Dict[str, Any]] = None
    special_legal_requirements: Optional[list[str]] = None
    mandatory_exhibits: Optional[list[str]] = None
    charge_sheet_template_bm: Optional[str] = None
    verified_status: Optional[str] = None


class RegisterUnindexedStatuteRequest(BaseModel):
    statute_id: str
    official_title_bm: str
    act_number_or_pu: str
    official_title_en: str = ""


class ValidateLegalOutputRequest(BaseModel):
    ai_response: Any
    question_context: str = ""


class PurgeQACacheRequest(BaseModel):
    akta_code: Optional[str] = None


@app.get("/api/legal/registry")
def get_legal_registry_and_coverage(
    _officer: Dict[str, Any] = Depends(_require_authenticated_officer),
) -> Dict[str, Any]:
    from backend.rag.legal_engine import get_legal_library

    return get_legal_library().get_coverage_audit_report()


@app.get("/api/legal/snapshot")
def get_legal_library_snapshot(
    _officer: Dict[str, Any] = Depends(_require_authenticated_officer),
) -> Dict[str, Any]:
    from backend.rag.legal_engine import get_legal_library

    lib = get_legal_library()
    return {
        "statute_library_version": lib.statute_library_version,
        "statutes_registry": lib.statutes_registry,
        "statute_sections_verbatim": [
            {k: v for k, v in s.items() if k != "embedding_vector"}
            for s in lib.statute_sections_verbatim
        ],
        "master_offences_matrix": lib.list_master_offences(),
        "repealed_and_blocked_provisions": lib.repealed_and_blocked_provisions,
    }


@app.get("/api/legal/sections")
def list_legal_verbatim_sections(
    statute_id: Optional[str] = Query(default=None),
    akta: Optional[str] = Query(default=None),
    q: Optional[str] = Query(default=None),
    _officer: Dict[str, Any] = Depends(_require_authenticated_officer),
) -> Dict[str, Any]:
    from backend.rag.legal_engine import get_legal_library

    return get_legal_library().list_verbatim_sections(
        statute_id=statute_id,
        akta_code=akta,
        q=q,
    )


@app.get("/api/legal/offences")
def list_legal_master_offences(
    statute_id: Optional[str] = Query(default=None),
    akta: Optional[str] = Query(default=None),
    target_offender: Optional[str] = Query(default=None),
    is_compoundable: Optional[bool] = Query(default=None),
    verified_status: Optional[str] = Query(default=None),
    q: Optional[str] = Query(default=None),
    _officer: Dict[str, Any] = Depends(_require_authenticated_officer),
) -> Dict[str, Any]:
    from backend.rag.legal_engine import get_legal_library

    lib = get_legal_library()
    items = lib.list_master_offences(
        statute_id=statute_id,
        akta_code=akta,
        target_offender=target_offender,
        is_compoundable=is_compoundable,
        verified_status=verified_status,
        q=q,
    )
    return {
        "statute_library_version": lib.statute_library_version,
        "total": len(items),
        "offences": items,
    }


@app.get("/api/legal/repealed")
def list_repealed_and_blocked_provisions(
    _officer: Dict[str, Any] = Depends(_require_authenticated_officer),
) -> Dict[str, Any]:
    from backend.rag.legal_engine import get_legal_library

    lib = get_legal_library()
    return {
        "statute_library_version": lib.statute_library_version,
        "provisions": lib.repealed_and_blocked_provisions,
    }


@app.post("/api/legal/validate")
def validate_legal_output_endpoint(
    req: ValidateLegalOutputRequest,
    _officer: Dict[str, Any] = Depends(_require_authenticated_officer),
) -> Dict[str, Any]:
    from backend.rag.legal_engine import get_legal_library, validate_legal_output

    lib = get_legal_library()
    return validate_legal_output(
        req.ai_response,
        lib.to_snapshot_dict(),
        question_context=req.question_context,
    )


@app.post("/api/legal/ingest")
async def ingest_gazette_pdf_endpoint(
    file: UploadFile = File(...),
    statute_id: Optional[str] = Form(default=None),
    official_title_bm: Optional[str] = Form(default=None),
    act_number_or_pu: Optional[str] = Form(default=None),
    verified_by_admin: bool = Form(default=False),
    current_officer: Dict[str, Any] = Depends(_require_dev_admin),
) -> Dict[str, Any]:
    return await ingest_statutory_act(
        file=file,
        statute_id=statute_id,
        official_title_bm=official_title_bm,
        act_number_or_pu=act_number_or_pu,
        verified_by_admin=verified_by_admin,
        current_officer=current_officer,
    )


@app.post("/api/legal/verify")
def verify_gazette_statute_or_offence(
    req: VerifyStatuteRequest,
    _admin: Dict[str, Any] = Depends(_require_dev_admin),
) -> Dict[str, Any]:
    from backend.rag.legal_engine import get_legal_library

    return get_legal_library().verify_statute_or_offence(
        statute_id=req.statute_id,
        offence_id=req.offence_id,
        verified=req.verified,
        updated_by=str(_admin.get("email") or ""),
    )


@app.put("/api/legal/offences/{offence_id}")
def update_master_offence_endpoint(
    offence_id: str,
    req: UpdateOffenceRequest,
    _admin: Dict[str, Any] = Depends(_require_dev_admin),
) -> Dict[str, Any]:
    from backend.rag.legal_engine import get_legal_library

    lib = get_legal_library()
    updated = lib.update_offence(
        offence_id,
        req.model_dump(exclude_none=True),
        updated_by=str(_admin.get("email") or ""),
    )
    if not updated:
        raise HTTPException(status_code=404, detail=f"Kesalahan '{offence_id}' tidak dijumpai.")
    stale_marked = db_service.invalidate_advisor_qa_cache(
        akta_code=None,
        new_version=lib.statute_library_version,
    )
    advisor_service.clear_cache()
    return {
        "status": "dikemaskini",
        "offence": updated,
        "statute_library_version": lib.statute_library_version,
        "stale_qa_cache_marked": stale_marked,
    }


@app.post("/api/legal/register-statute")
def register_unindexed_statute_endpoint(
    req: RegisterUnindexedStatuteRequest,
    _admin: Dict[str, Any] = Depends(_require_dev_admin),
) -> Dict[str, Any]:
    from backend.rag.legal_engine import get_legal_library

    entry = get_legal_library().register_unindexed_statute(
        statute_id=req.statute_id,
        official_title_bm=req.official_title_bm,
        act_number_or_pu=req.act_number_or_pu,
        official_title_en=req.official_title_en,
    )
    return {"status": "didaftarkan", "statute": entry}


@app.post("/api/legal/purge-qa-cache")
def purge_advisor_qa_cache_endpoint(
    req: PurgeQACacheRequest,
    _admin: Dict[str, Any] = Depends(_require_dev_admin),
) -> Dict[str, Any]:
    from backend.rag.legal_engine import get_legal_library

    lib = get_legal_library()
    new_ver = lib.bump_version(tag="purge")
    purged_count = db_service.invalidate_advisor_qa_cache(
        akta_code=req.akta_code,
        new_version=new_ver,
    )
    advisor_service.clear_cache()
    return {
        "status": "dibersihkan",
        "stale_records_marked": purged_count,
        "statute_library_version": new_ver,
    }


# ---------------- Akaun Pegawai KKM Sebenar ----------------


@app.get("/api/auth/demo-accounts")
def get_demo_accounts() -> Dict[str, Any]:
    return {"accounts": db_service.list_demo_accounts()}


@app.post("/api/auth/register")
def register_officer_account(req: RegisterAccountRequest, request: Request) -> Dict[str, Any]:
    _check_rate_limit(f"auth:reg:{_client_ip(request)}", max_requests=15, window_sec=60.0)
    try:
        res = db_service.register_user(req.model_dump())
        try:
            db_service.log_activity(
                action_type="REGISTER_ACCOUNT",
                action_detail=f"Daftar akaun baharu (E-mel KKM): {res['user'].get('email', '')}",
                user=res.get("user"),
                model_used="local-sqlite-auth",
                latency_ms=15,
            )
        except Exception:
            pass
        _archive_safely(
            category="USER_REGISTER",
            action_type="REGISTER_ACCOUNT",
            endpoint="/api/auth/register",
            user=res.get("user"),
            title=f"Daftar Pegawai (E-mel): {res['user'].get('full_name', '')} ({res['user'].get('email', '')})",
            raw_input_text=f"Nama: {res['user'].get('full_name', '')}\nE-mel: {res['user'].get('email', '')}\nGred: {res['user'].get('grade', '')}\nPejabat: {res['user'].get('district_pkd', '')}\nKad Kuasa: {res['user'].get('kkm_authority_card_no', '')}",
            request_payload={k: v for k, v in req.model_dump().items() if k != "password"},
            analysis_payload={"user": res.get("user"), "auth_provider": "email"},
            model_used="local-sqlite-auth",
            latency_ms=15,
            status_summary="Pendaftaran E-mel KKM",
        )
        return res
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/auth/login")
def login_officer_account(req: LoginRequest, request: Request) -> Dict[str, Any]:
    _check_rate_limit(f"auth:login:{_client_ip(request)}", max_requests=20, window_sec=60.0)
    res = db_service.authenticate_user(req.email, req.password)
    if not res:
        raise HTTPException(
            status_code=401,
            detail="E-mel atau kata laluan tidak tepat. Sila semak semula.",
        )
    try:
        db_service.log_activity(
            action_type="LOGIN_EMAIL",
            action_detail=f"Log masuk e-mel: {res['user'].get('email', '')}",
            user=res.get("user"),
            model_used="local-sqlite-auth",
            latency_ms=12,
        )
    except Exception:
        pass
    return res


@app.post("/api/auth/google")
def google_auth_officer(req: GoogleAuthRequest, request: Request) -> Dict[str, Any]:
    _check_rate_limit(f"auth:google:{_client_ip(request)}", max_requests=20, window_sec=60.0)
    try:
        res = db_service.authenticate_or_register_google_user(req.model_dump())
        status_txt = "Daftar baharu" if res.get("is_new_account") else "Log masuk pantas"
        try:
            db_service.log_activity(
                action_type="LOGIN_GOOGLE",
                action_detail=f"{status_txt} Google Connector: {res['user'].get('email', '')}",
                user=res.get("user"),
                model_used="google-oauth2-gis",
                latency_ms=14,
            )
        except Exception:
            pass
        if res.get("is_new_account"):
            _archive_safely(
                category="USER_REGISTER",
                action_type="REGISTER_GOOGLE",
                endpoint="/api/auth/google",
                user=res.get("user"),
                title=f"Daftar Pegawai (Google OAuth): {res['user'].get('full_name', '')} ({res['user'].get('email', '')})",
                raw_input_text=f"Nama: {res['user'].get('full_name', '')}\nE-mel: {res['user'].get('email', '')}\nGred: {res['user'].get('grade', '')}\nPejabat: {res['user'].get('district_pkd', '')}\nKad Kuasa: {res['user'].get('kkm_authority_card_no', '')}",
                request_payload={k: v for k, v in req.model_dump().items() if k not in ("id_token", "access_token")},
                analysis_payload={"user": res.get("user"), "auth_provider": "google", "is_new_account": True},
                model_used="google-oauth2-gis",
                latency_ms=14,
                status_summary="Pendaftaran Baharu Google",
            )
        return res
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/auth/me")
def get_my_officer_profile(
    authorization: Optional[str] = Header(default=None),
    x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
) -> Dict[str, Any]:
    user = _resolve_current_officer(authorization, x_auth_token)
    if not user:
        raise HTTPException(status_code=401, detail="Sesi log masuk tidak sah atau sudah tamat.")
    return {"user": user}


@app.put("/api/auth/profile")
def update_my_officer_profile(
    req: UpdateProfileRequest,
    authorization: Optional[str] = Header(default=None),
    x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
) -> Dict[str, Any]:
    user = _resolve_current_officer(authorization, x_auth_token)
    if not user:
        raise HTTPException(status_code=401, detail="Sila log masuk dahulu untuk mengemas kini profil.")
    changes = req.model_dump(exclude_none=True)
    updated = db_service.update_user_profile(user["id"], changes)
    _archive_safely(
        category="USER_REGISTER",
        action_type="UPDATE_PROFILE",
        endpoint="/api/auth/profile",
        user=updated or user,
        title=f"Kemas Kini Profil Pegawai: {(updated or user).get('full_name', '')}",
        raw_input_text=json.dumps(changes, ensure_ascii=False),
        request_payload=changes,
        analysis_payload={"user": updated or user, "changed_fields": list(changes.keys())},
        model_used="local-sqlite-auth",
        status_summary=f"{len(changes)} medan dikemas kini",
    )
    return {"user": updated}


@app.post("/api/auth/logout")
def logout_officer_account(
    authorization: Optional[str] = Header(default=None),
    x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
) -> Dict[str, bool]:
    token = _extract_bearer_token(authorization, x_auth_token)
    return {"logged_out": db_service.logout_session(token)}


# ---------------- Tanya Pakar UIP & Penasihat Kes ----------------


@app.get("/api/advisor/scenarios")
def list_advisor_scenarios(
    _officer: Dict[str, Any] = Depends(_require_authenticated_officer),
) -> Dict[str, Any]:
    return {"scenarios": advisor_service.list_scenarios()}


@app.get("/api/advisor/answered")
def list_advisor_answered_questions(
    akta: Optional[str] = Query(default=None),
    q: Optional[str] = Query(default=None),
    limit: int = Query(default=120, ge=1, le=200),
    _officer: Dict[str, Any] = Depends(_require_authenticated_officer),
) -> Dict[str, Any]:
    return db_service.list_advisor_answered_questions(
        akta=akta,
        q=q,
        limit=limit,
    )


@app.post("/api/advisor/consult")
def consult_uip_advisor(
    req: AdvisorConsultRequest,
    current_officer: Dict[str, Any] = Depends(_require_authenticated_officer),
) -> Dict[str, Any]:
    if not req.question.strip() and not req.scenario_id:
        raise HTTPException(
            status_code=400,
            detail="Sila taip soalan situasi kes atau pilih salah satu templat situasi.",
        )
    if req.use_ai:
        _check_rate_limit(f"ai:{current_officer.get('id') or 'anon'}", max_requests=25, window_sec=60.0)
    t0 = time.perf_counter()
    officer = _merge_authoritative_officer(current_officer, req.officer_profile)
    res = advisor_service.consult(
        question=req.question,
        akta_hint=req.akta_hint,
        scenario_id=req.scenario_id,
        use_ai=req.use_ai,
        officer_profile=officer,
    )
    model_used = str(res.get("engine_used") or "Mod Pantas — Matriks SOP UIP KKM + Strict RAG")
    is_cloud = bool(
        not res.get("from_qa_collection")
        and (res.get("ai_succeeded") or "gemini" in model_used.lower())
        and "pantas" not in model_used.lower()
        and "cache" not in model_used.lower()
        and "koleksi" not in model_used.lower()
    )
    raw_q_preview = (req.question or req.scenario_id or "Situasi UIP").strip()[:140]
    q_preview = router_service.redactor.redact(raw_q_preview, use_ollama=False).redacted_text[:100]
    latency_ms = int((time.perf_counter() - t0) * 1000)
    db_service.log_activity(
        action_type="TANYA_PAKAR_UIP",
        action_detail=f"Soalan ({res.get('akta_disyorkan', req.akta_hint)}): {q_preview}",
        user=current_officer,
        model_used=model_used,
        est_input_tokens=max(600, _est_tokens(req.question) + 500) if is_cloud else 0,
        est_output_tokens=_est_tokens(res.get("alasan_keputusan", "")) + 650 if is_cloud else 0,
        latency_ms=latency_ms,
    )
    # Larang jawapan fallback / ralat / gagal validasi / Seksyen 2 Tafsiran disimpan sebagai cache Koleksi Q&A (TANYA_PAKAR_UIP);
    # rekod bukan cache disimpan di bawah TANYA_PAKAR_UIP_NO_CACHE untuk audit Dev Vault sahaja (tidak muncul dalam Koleksi Q&A).
    from backend.core.database import _is_corrupted_or_fallback_qa

    is_cacheable_qa = not _is_corrupted_or_fallback_qa(res)
    _archive_safely(
        category="ADVISOR_QA",
        action_type="TANYA_PAKAR_UIP" if is_cacheable_qa else "TANYA_PAKAR_UIP_NO_CACHE",
        endpoint="/api/advisor/consult",
        user=current_officer,
        title=f"Tanya Pakar ({res.get('akta_disyorkan', req.akta_hint)}): {q_preview}",
        akta_utama=str(res.get("akta_disyorkan") or req.akta_hint or ""),
        raw_input_text=req.question or f"[Templat Situasi: {req.scenario_id}]",
        raw_response_text=f"{res.get('keputusan_tindakan', '')}\n\n{res.get('alasan_keputusan', '')}".strip(),
        request_payload={
            "question": req.question,
            "akta_hint": req.akta_hint,
            "scenario_id": req.scenario_id,
            "use_ai": req.use_ai,
            "reused_from_qa_id": res.get("matched_collection_id"),
            "cacheable_qa": is_cacheable_qa,
        },
        analysis_payload=res,
        model_used=model_used,
        is_cloud_api=is_cloud,
        latency_ms=latency_ms,
        status_summary=str(res.get("keputusan_tindakan") or ""),
    )
    return res


@app.post("/api/advisor/sop-brain")
def consult_sop_brain_endpoint(
    req: AdvisorSopBrainRequest,
    current_officer: Dict[str, Any] = Depends(_require_authenticated_officer),
) -> Dict[str, Any]:
    if not (req.question or "").strip():
        raise HTTPException(
            status_code=400,
            detail="Sila taip soalan situasi kes untuk rujukan Otak SOP KKM 2024.",
        )
    _check_rate_limit(f"ai:{current_officer.get('id') or 'anon'}", max_requests=25, window_sec=60.0)
    return advisor_service.consult_sop_brain(
        question=req.question.strip(),
        akta_hint=req.akta_hint,
        guna_cache=req.guna_cache,
    )


# ---------------- Konsol Pembangun & Private Vault Bucket (zero4eleven@gmail.com sahaja) ----------------


class DevVaultExportRequest(BaseModel):
    mode: str = "redacted"
    format: str = "zip"
    category: Optional[str] = None
    q: Optional[str] = None
    user_email: Optional[str] = None
    include_files: bool = True
    limit: int = Field(default=500, ge=1, le=2000)


dev_router = APIRouter(
    prefix="/api/dev",
    dependencies=[Depends(_require_dev_admin)],
)


@dev_router.get("/overview")
def get_dev_console_overview() -> Dict[str, Any]:
    return db_service.get_dev_overview()


@dev_router.get("/vault/health")
def get_dev_vault_health() -> Dict[str, Any]:
    return db_service.get_dev_vault_health()


@dev_router.get("/vault/records")
def list_dev_vault_records(
    category: Optional[str] = Query(default=None),
    q: Optional[str] = Query(default=None),
    user_email: Optional[str] = Query(default=None),
    has_file: bool = Query(default=False),
    limit: int = Query(default=30, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> Dict[str, Any]:
    return db_service.list_dev_archive(
        category=category,
        q=q,
        user_email=user_email,
        has_file=has_file,
        limit=limit,
        offset=offset,
    )


@dev_router.get("/vault/records/{record_id}")
def get_dev_vault_record_detail(
    record_id: str,
    admin: Dict[str, Any] = Depends(_require_dev_admin),
) -> Dict[str, Any]:
    row = db_service.get_dev_archive_record(record_id, include_b64=False)
    if not row:
        raise HTTPException(status_code=404, detail="Rekod arkib dev tidak dijumpai.")
    db_service.log_dev_vault_access(
        admin.get("email", "zero4eleven@gmail.com"),
        "VIEW_DETAIL",
        record_id=record_id,
        detail=str(row.get("title") or "")[:180],
    )
    return dev_vault_service.format_detail_response(row)


@dev_router.get("/vault/records/{record_id}/file")
def download_dev_vault_file(
    record_id: str,
    kind: str = Query(default="attachment"),
    admin: Dict[str, Any] = Depends(_require_dev_admin),
) -> Response:
    safe_kind = "json" if kind == "json" else "attachment"
    try:
        data_bytes, fname, mime = dev_vault_service.resolve_file_download(
            record_id, kind=safe_kind
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    db_service.log_dev_vault_access(
        admin.get("email", "zero4eleven@gmail.com"),
        f"DOWNLOAD_{safe_kind.upper()}",
        record_id=record_id,
        detail=f"{fname} ({len(data_bytes)} bait)",
    )
    clean_fname = sanitize_filename(fname, f"{record_id}.bin")
    return Response(
        content=data_bytes,
        media_type=mime,
        headers={
            "Content-Disposition": f'attachment; filename="{clean_fname}"',
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-store, private",
            "Content-Security-Policy": "sandbox",
        },
    )


@dev_router.post("/vault/export")
def export_dev_vault_bundle_endpoint(
    req: DevVaultExportRequest,
    admin: Dict[str, Any] = Depends(_require_dev_admin),
) -> Response:
    fmt = "jsonl" if req.format == "jsonl" else "zip"
    mode = "full" if req.mode == "full" else "redacted"
    data_bytes, fname, mime = dev_vault_service.build_export_bundle(
        mode=mode,
        fmt=fmt,
        category=req.category,
        q=req.q,
        user_email=req.user_email,
        include_files=req.include_files,
        limit=req.limit,
    )
    db_service.log_dev_vault_access(
        admin.get("email", "zero4eleven@gmail.com"),
        f"EXPORT_{mode.upper()}_{fmt.upper()}",
        detail=f"{fname} ({len(data_bytes)} bait)",
    )
    clean_fname = sanitize_filename(fname, f"iuip-dev-vault.{fmt}")
    return Response(
        content=data_bytes,
        media_type=mime,
        headers={
            "Content-Disposition": f'attachment; filename="{clean_fname}"',
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-store, private",
            "Content-Security-Policy": "sandbox",
        },
    )


@dev_router.post("/vault/retry-s3-sync")
def retry_dev_vault_s3_sync(
    limit: int = Query(default=50, ge=1, le=200),
    admin: Dict[str, Any] = Depends(_require_dev_admin),
) -> Dict[str, Any]:
    res = dev_vault_service.retry_s3_sync(limit=limit)
    db_service.log_dev_vault_access(
        admin.get("email", "zero4eleven@gmail.com"),
        "RETRY_S3_SYNC",
        detail=str(res.get("message") or "")[:180],
    )
    return res


app.include_router(dev_router)
