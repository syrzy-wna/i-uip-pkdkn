"""Pelayan REST API FastAPI bagi UIP-Command (Unit Inspektorat & Perundangan KKM)."""

from __future__ import annotations

import time
from dataclasses import asdict
from typing import Any, Dict, Optional

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from backend.core.config import settings
from backend.core.database import get_uip_db
from backend.core.model_router import UIPModelRouter
from backend.services.compound_checker import CompoundNoticeChecker
from backend.services.doc_generator import generate_docx_by_type
from backend.services.ip_auditor import IPTechnicalAuditor, extract_text_from_upload
from backend.services.sample_cases import SAMPLE_CASES
from backend.services.uip_advisor import UIPAdvisorService

db_service = get_uip_db()
router_service = UIPModelRouter()
auditor_service = IPTechnicalAuditor(router=router_service)
compound_checker = CompoundNoticeChecker()
advisor_service = UIPAdvisorService(router=router_service)


def _extract_bearer_token(authorization: Optional[str]) -> str:
    if not authorization:
        return ""
    parts = authorization.strip().split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    return authorization.strip()


def _resolve_current_officer(authorization: Optional[str]) -> Optional[Dict[str, Any]]:
    token = _extract_bearer_token(authorization)
    if not token:
        return None
    return db_service.get_user_by_token(token)


def _require_authenticated_officer(
    authorization: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    user = _resolve_current_officer(authorization)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Akses disekat: Sila daftar atau log masuk akaun pegawai terlebih dahulu.",
        )
    return user


def _require_dev_admin(
    current_officer: Dict[str, Any] = Depends(_require_authenticated_officer),
) -> Dict[str, Any]:
    email = str(current_officer.get("email") or "").strip().lower()
    if email not in settings.dev_admin_emails:
        raise HTTPException(
            status_code=403,
            detail="Akses disekat: Konsol Pembangun dan Tetapan Sistem hanya untuk akaun pembangun rasmi (zero4eleven@gmail.com).",
        )
    return current_officer


def _est_tokens(text: Optional[str]) -> int:
    if not text:
        return 0
    return max(1, len(text) // 4)

app = FastAPI(
    title="UIP-Command API",
    description=(
        "Aplikasi Pengurusan Kertas Siasatan (IP), Notis Kompaun & Semakan Pra-TPR "
        "untuk Unit Inspektorat dan Perundangan (UIP), Kementerian Kesihatan Malaysia."
    ),
    version="2.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_json_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"detail": f"Ralat dalaman pelayan: {str(exc)[:240]}"},
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
    state_jkn: str = "Jabatan Kesihatan Negeri Terengganu"
    district_pkd: str = "Pejabat Kesihatan Daerah Kuala Nerus"
    office_address: str = ""
    unit_assignment: str = "Unit Inspektorat dan Perundangan (UIP)"
    default_magistrate_court: str = "MAHKAMAH MAJISTRET DI KUALA TERENGGANU, DALAM NEGERI TERENGGANU DARUL IMAN"
    system_role: str = "PEGAWAI_PENYIASAT"
    default_computer_desc: str = "Komputer Meja Rasmi KKM Dell OptiPlex Pejabat PKD"
    default_printer_desc: str = "Pencetak Laser Warna Pejabat PKD"
    default_camera_desc: str = "Kamera Digital Rasmi Pejabat KKM"


class LoginRequest(BaseModel):
    email: str
    password: str


class GoogleAuthRequest(BaseModel):
    id_token: Optional[str] = None
    access_token: Optional[str] = None
    kkm_authority_card_no: str = ""
    grade: str = "U5"
    designation: str = "Penolong Pegawai Kesihatan Persekitaran (PPKP)"
    state_jkn: str = "Jabatan Kesihatan Negeri Terengganu"
    district_pkd: str = "Pejabat Kesihatan Daerah Kuala Nerus"


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
        "dokumentasi": "/docs",
    }


@app.get("/healthz")
@app.get("/api/health")
def healthz() -> Dict[str, str]:
    return {
        "status": "ok",
        "db": "postgres" if db_service.use_postgres else "sqlite",
    }


@app.get("/api/status")
def get_status() -> Dict[str, Any]:
    return router_service.get_system_status()


@app.get("/api/settings")
def get_runtime_settings() -> Dict[str, Any]:
    return {
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
    }


@app.post("/api/settings")
def update_runtime_settings(
    req: RuntimeSettingsRequest,
    _admin: Dict[str, Any] = Depends(_require_dev_admin),
) -> Dict[str, Any]:
    db_service.save_runtime_settings(req.model_dump())
    router_service.refresh_clients()
    return {
        "status": "disimpan",
        "system_status": router_service.get_system_status(),
        "settings": get_runtime_settings(),
    }


@app.get("/api/samples")
def get_samples(
    _officer: Dict[str, Any] = Depends(_require_authenticated_officer),
) -> Dict[str, Any]:
    return {"samples": SAMPLE_CASES}


@app.get("/api/cases")
def list_cases(
    _officer: Dict[str, Any] = Depends(_require_authenticated_officer),
) -> Dict[str, Any]:
    return {"cases": db_service.list_cases()}


@app.post("/api/cases")
def save_case(
    req: UpsertCaseRequest,
    current_officer: Dict[str, Any] = Depends(_require_authenticated_officer),
) -> Dict[str, Any]:
    saved = db_service.upsert_case(req.model_dump(exclude_none=True))
    db_service.log_activity(
        action_type="SIMPAN_KES_IP",
        action_detail=f"Simpan fail {saved.get('no_ip', '')} ({saved.get('akta_utama', '')})",
        user=current_officer,
        model_used="local-sqlite-db",
        latency_ms=8,
    )
    return {"case": saved}


@app.delete("/api/cases/{case_id}")
def delete_case(
    case_id: str,
    _officer: Dict[str, Any] = Depends(_require_authenticated_officer),
) -> Dict[str, Any]:
    deleted = db_service.delete_case(case_id)
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
    db_service.log_activity(
        action_type="SEMAK_KOMPAUN",
        action_detail=f"Semak notis kompaun {req.no_notis or '(draf)'} - {req.peruntukan_undang or 'Umum'}",
        user=current_officer,
        model_used="local-compound-validator",
        latency_ms=int((time.perf_counter() - t0) * 1000),
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
    t0 = time.perf_counter()
    raw_text = (text or "").strip()
    filename = "teks_kertas_siasatan.txt"

    if file is not None:
        file_bytes = await file.read()
        filename = file.filename or "kertas_siasatan.pdf"
        if not file_bytes:
            raise HTTPException(status_code=400, detail="Fail yang dimuat naik kosong.")
        extracted = extract_text_from_upload(file_bytes, filename)
        if extracted.strip():
            raw_text = f"{extracted}\n\n{raw_text}".strip() if raw_text else extracted

    if not raw_text:
        raise HTTPException(
            status_code=400,
            detail="Sila masukkan teks Kertas Siasatan atau muat naik fail PDF/DOCX/TXT.",
        )

    report = auditor_service.audit_ip(
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
    }

    if case_id:
        db_service.upsert_case({
            "id": case_id,
            "akta_utama": akta_utama,
            "case_text": raw_text,
            "status_kes": report.readiness_status,
            "skor_audit": report.overall_score,
            "audit_report": report_dict,
        })

    audit_model = str((report.models_used or {}).get("decision_engine") or "local-statute-fallback")
    is_gemini_audit = (
        "gemini" in audit_model.lower()
        and "fallback" not in audit_model.lower()
        and "pantas" not in audit_model.lower()
        and "cache" not in audit_model.lower()
    )
    db_service.log_activity(
        action_type="AUDIT_IP_20",
        action_detail=f"Semak 20 Kriteria ({akta_utama}) — Skor {report.overall_score:.1f}% ({report.readiness_status})",
        user=current_officer,
        model_used=audit_model,
        est_input_tokens=_est_tokens(raw_text) if is_gemini_audit else 0,
        est_output_tokens=550 if is_gemini_audit else 0,
        latency_ms=int((time.perf_counter() - t0) * 1000),
    )

    return report_dict


@app.post("/api/extract-evidence")
async def extract_evidence_endpoint(
    file: UploadFile = File(...),
    doc_hint: str = Form(default="bukti_kesalahan"),
    current_officer: Dict[str, Any] = Depends(_require_authenticated_officer),
) -> Dict[str, Any]:
    t0 = time.perf_counter()
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Fail bukti kosong.")
    result = router_service.extract_multimodal_evidence(
        file_bytes=file_bytes,
        filename=file.filename or "bukti.jpg",
        mime_type=file.content_type or "application/octet-stream",
        doc_hint=doc_hint,
    )
    is_cloud = "gemini" in (result.model_used or "").lower() and "sim" not in (result.model_used or "").lower()
    db_service.log_activity(
        action_type="EKSTRAK_BUKTI_OCR",
        action_detail=f"Ekstrak gambar/fail bukti: {file.filename or 'bukti'} ({doc_hint})",
        user=current_officer,
        model_used=result.model_used,
        est_input_tokens=1300 if is_cloud else 0,
        est_output_tokens=450 if is_cloud else 0,
        latency_ms=int((time.perf_counter() - t0) * 1000),
    )
    return {
        "filename": file.filename,
        "extracted_fields": result.extracted_fields,
        "structured_summary": result.structured_summary,
        "raw_text": result.raw_text,
        "confidence": result.confidence,
        "model_used": result.model_used,
        "warnings": result.warnings,
    }


@app.post("/api/generate-draft")
def generate_draft_endpoint(
    req: GenerateDraftRequest,
    current_officer: Dict[str, Any] = Depends(_require_authenticated_officer),
) -> Dict[str, Any]:
    t0 = time.perf_counter()
    active_officer = req.officer_profile or current_officer
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
        db_service.upsert_case({
            "id": req.case_id,
            "akta_utama": req.akta_utama,
            "case_text": req.case_text,
            "draft": result_dict,
        })
    draft_model = str((result.models_used or {}).get("legal_reasoning") or "local-template-engine")
    is_cloud = (
        "gemini" in draft_model.lower()
        and "templat" not in draft_model.lower()
        and "pantas" not in draft_model.lower()
        and "cache" not in draft_model.lower()
    )
    db_service.log_activity(
        action_type="JANA_DRAF_IP",
        action_detail=f"Jana draf & Borang 114 ({req.akta_utama}, aliran: {req.workflow})",
        user=active_officer,
        model_used=draft_model,
        est_input_tokens=_est_tokens(req.case_text) if is_cloud else 0,
        est_output_tokens=_est_tokens(result.borang_114) if is_cloud else 0,
        latency_ms=int((time.perf_counter() - t0) * 1000),
    )
    return result_dict


@app.post("/api/export-docx")
def export_docx_endpoint(
    req: ExportDocxRequest,
    current_officer: Dict[str, Any] = Depends(_require_authenticated_officer),
) -> Response:
    t0 = time.perf_counter()
    docx_bytes, filename = generate_docx_by_type(req.doc_type, req.payload)
    db_service.log_activity(
        action_type="EXPORT_DOCX",
        action_detail=f"Muat turun fail Word rasmi: {filename} ({req.doc_type})",
        user=current_officer,
        model_used="python-docx-local",
        latency_ms=int((time.perf_counter() - t0) * 1000),
    )
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
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
    db_service.log_activity(
        action_type="CARIAN_RAG_AKTA",
        action_detail=f"Cari teks akta ({akta or 'Semua'}): {q[:80]}",
        user=current_officer,
        model_used=router_service.rag_store.engine_name,
        latency_ms=int((time.perf_counter() - t0) * 1000),
    )
    return {
        "query": q,
        "engine": router_service.rag_store.engine_name,
        "results": [asdict(c) for c in chunks],
    }


@app.post("/api/rag/ingest")
async def ingest_statutory_act(
    file: UploadFile = File(...),
    _officer: Dict[str, Any] = Depends(_require_authenticated_officer),
) -> Dict[str, Any]:
    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="Fail akta kosong.")
    fname = file.filename or "akta_tambahan.txt"
    if not fname.lower().endswith((".txt", ".pdf", ".md")):
        raise HTTPException(status_code=400, detail="Hanya fail .txt, .md atau .pdf disokong.")
    total_chunks = router_service.rag_store.ingest_uploaded_file(fname, raw_bytes)
    return {
        "status": "berjaya",
        "filename": fname,
        "total_chunks_indexed": total_chunks,
        "acts_loaded": router_service.rag_store.list_available_acts(),
    }


# ---------------- Akaun Pegawai KKM Sebenar ----------------


@app.get("/api/auth/demo-accounts")
def get_demo_accounts() -> Dict[str, Any]:
    return {"accounts": db_service.list_demo_accounts()}


@app.post("/api/auth/register")
def register_officer_account(req: RegisterAccountRequest) -> Dict[str, Any]:
    try:
        res = db_service.register_user(req.model_dump())
        try:
            db_service.log_activity(
                action_type="REGISTER_ACCOUNT",
                action_detail=f"Daftar akaun baharu (Emel KKM): {res['user'].get('email', '')}",
                user=res.get("user"),
                model_used="local-sqlite-auth",
                latency_ms=15,
            )
        except Exception:
            pass
        return res
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/auth/login")
def login_officer_account(req: LoginRequest) -> Dict[str, Any]:
    res = db_service.authenticate_user(req.email, req.password)
    if not res:
        raise HTTPException(
            status_code=401,
            detail="Emel atau kata laluan tidak tepat. Sila semak semula.",
        )
    try:
        db_service.log_activity(
            action_type="LOGIN_EMAIL",
            action_detail=f"Log masuk emel: {res['user'].get('email', '')}",
            user=res.get("user"),
            model_used="local-sqlite-auth",
            latency_ms=12,
        )
    except Exception:
        pass
    return res


@app.post("/api/auth/google")
def google_auth_officer(req: GoogleAuthRequest) -> Dict[str, Any]:
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
        return res
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/auth/me")
def get_my_officer_profile(
    authorization: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    user = _resolve_current_officer(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Sesi log masuk tidak sah atau sudah tamat.")
    return {"user": user}


@app.put("/api/auth/profile")
def update_my_officer_profile(
    req: UpdateProfileRequest,
    authorization: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    user = _resolve_current_officer(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Sila log masuk dahulu untuk mengemas kini profil.")
    updated = db_service.update_user_profile(user["id"], req.model_dump(exclude_none=True))
    return {"user": updated}


@app.post("/api/auth/logout")
def logout_officer_account(
    authorization: Optional[str] = Header(default=None),
) -> Dict[str, bool]:
    token = _extract_bearer_token(authorization)
    return {"logged_out": db_service.logout_session(token)}


# ---------------- Tanya Pakar UIP & Penasihat Kes ----------------


@app.get("/api/advisor/scenarios")
def list_advisor_scenarios(
    _officer: Dict[str, Any] = Depends(_require_authenticated_officer),
) -> Dict[str, Any]:
    return {"scenarios": advisor_service.list_scenarios()}


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
    t0 = time.perf_counter()
    officer = req.officer_profile or current_officer
    res = advisor_service.consult(
        question=req.question,
        akta_hint=req.akta_hint,
        scenario_id=req.scenario_id,
        use_ai=req.use_ai,
        officer_profile=officer,
    )
    model_used = str(res.get("engine_used") or "Mod Pantas — Matriks SOP UIP KKM + Strict RAG")
    is_cloud = bool(
        "gemini" in model_used.lower()
        and "pantas" not in model_used.lower()
        and "cache" not in model_used.lower()
    )
    q_preview = (req.question or req.scenario_id or "Situasi UIP").strip()[:100]
    db_service.log_activity(
        action_type="TANYA_PAKAR_UIP",
        action_detail=f"Soalan ({res.get('akta_disyorkan', req.akta_hint)}): {q_preview}",
        user=officer,
        model_used=model_used,
        est_input_tokens=max(600, _est_tokens(req.question) + 500) if is_cloud else 0,
        est_output_tokens=_est_tokens(res.get("alasan_keputusan", "")) + 650 if is_cloud else 0,
        latency_ms=int((time.perf_counter() - t0) * 1000),
    )
    return res


# ---------------- Konsol Pembangun (Dev g.dev/syrzy) ----------------


@app.get("/api/dev/overview")
def get_dev_console_overview(
    _admin: Dict[str, Any] = Depends(_require_dev_admin),
) -> Dict[str, Any]:
    return db_service.get_dev_overview()
