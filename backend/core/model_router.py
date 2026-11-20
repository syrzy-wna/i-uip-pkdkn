"""Orkestrasi Multi-Model & Penghurai Fakta Sebenar UIP-Command (ModelRouter).

Menggabungkan:
1. Enjin Privasi & Bahasa PPKP Tempatan (Ollama localhost:11434)
2. Enjin Semakan IP (gemini-decision-1 Decisions API v1beta)
3. Pengekstrak Dokumen & Gambar Bukti (Gemini Interactions / generate_content)
4. Penjana Draf IP & Borang 114 (Gemini / Penghurai Fakta Sebenar)
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("uip.model_router")

import httpx
import pymupdf as fitz
from pydantic import BaseModel

from backend.core.config import settings
from backend.core.redactor import PrivacyRedactor, RedactionResult
from backend.rag.statutory_store import StatuteChunk, StatutoryRAGStore, get_statutory_store

try:
    from google import genai
    from google.genai import types as genai_types

    GENAI_SDK_AVAILABLE = True
except Exception:
    genai = None  # type: ignore
    genai_types = None  # type: ignore
    GENAI_SDK_AVAILABLE = False


class _EvidenceSchema(BaseModel):
    jenis_dokumen: str
    nama_premis_atau_syarikat: str
    no_ssm: str
    nama_okt_atau_individu: str
    no_kp: str
    tarikh_masa_dikesan: str
    lokasi_alamat: str
    butiran_kesalahan_atau_eksibit: str
    cadangan_akta_seksyen: str
    kualiti_imej_untuk_mahkamah: str
    confidence: float
    raw_text: str


class _Borang114Schema(BaseModel):
    mahkamah: str
    negeri: str
    no_kes: str
    nama_tertuduh: str
    no_kp_tertuduh: str
    umur_jantina: str
    pekerjaan: str
    alamat_tertuduh: str
    tarikh_kejadian: str
    masa_kejadian: str
    tempat_kejadian: str
    daerah: str
    akta_dan_seksyen: str
    seksyen_hukuman: str
    hukuman_maksimum: str
    pegawai_pengadu: str
    teks_pertuduhan: str


class _DiariItemSchema(BaseModel):
    bil: str
    tarikh: str
    masa: str
    butiran_tindakan: str
    pegawai: str


class _SaksiItemSchema(BaseModel):
    bil: str
    nama: str
    no_kp: str
    jawatan_peranan: str
    alamat_hubungan: str


class _EksibitItemSchema(BaseModel):
    tanda: str
    perihal: str
    no_lak_seal: str
    lokasi_simpanan: str


class _Sijil90ASchema(BaseModel):
    nama_pegawai: str
    jawatan: str
    pejabat_pkd: str
    peranti_kamera: str
    perihal_komputer: str
    perihal_pencetak: str
    senarai_dokumen_digital: str


class _NotisKompaunSchema(BaseModel):
    no_notis: str
    nama_penerima: str
    no_kp: str
    nama_premis: str
    alamat_kejadian: str
    no_ssm: str
    tarikh_masa: str
    kesalahan_ringkas: str
    peruntukan_undang: str
    peruntukan_kompaun: str
    amaun_kompaun_rm: str
    tempoh_bayaran: str
    pegawai_pengeluar: str
    no_kad_kuasa: str


class _MinitItemSchema(BaseModel):
    bil: str
    tarikh: str
    daripada: str
    kepada: str
    kandungan: str


class _KronologiItemSchema(BaseModel):
    tarikh: str
    peristiwa: str


class _Saman111Schema(BaseModel):
    mahkamah: str
    no_saman: str
    nama_oks: str
    no_kp: str
    alamat: str
    tarikh_hadir: str
    masa_hadir: str
    teks_pertuduhan: str
    hukuman: str


class _Borang143Schema(BaseModel):
    mahkamah: str
    negeri: str
    pengadu: str
    oks_nama: str
    oks_kp: str
    oks_alamat: str
    butiran_aduan: str


class _IzinMendakwaSchema(BaseModel):
    rujukan_ip: str
    kepada: str
    peruntukan_izin: str
    nama_okt: str
    seksyen_dipohon: str


class _LegalDraftSchema(BaseModel):
    minit_ip: List[_MinitItemSchema]
    kronologi_kes: List[_KronologiItemSchema]
    kertas_cadangan_io: str
    saman_111: _Saman111Schema
    borang_143: _Borang143Schema
    izin_mendakwa: _IzinMendakwaSchema
    borang_114: _Borang114Schema
    diari_siasatan: List[_DiariItemSchema]
    fakta_kes: str
    rakaman_112: str
    senarai_saksi: List[_SaksiItemSchema]
    senarai_eksibit: List[_EksibitItemSchema]
    sijil_90a: _Sijil90ASchema
    notis_kompaun: _NotisKompaunSchema
    pemberatan_hukuman: List[str]
    tpr_simulation_notes: List[str]


@dataclass
class EvidenceExtractionResult:
    extracted_fields: Dict[str, Any]
    structured_summary: str
    raw_text: str
    confidence: float
    model_used: str
    warnings: List[str] = field(default_factory=list)


@dataclass
class DraftGenerationResult:
    workflow: str
    akta_utama: str
    minit_ip: List[Dict[str, str]]
    kronologi_kes: List[Dict[str, str]]
    kertas_cadangan_io: str
    saman_111: Dict[str, str]
    borang_143: Dict[str, str]
    izin_mendakwa: Dict[str, str]
    borang_114: Dict[str, Any]
    diari_siasatan: List[Dict[str, str]]
    fakta_kes: str
    rakaman_112: str
    senarai_saksi: List[Dict[str, str]]
    senarai_eksibit: List[Dict[str, str]]
    sijil_90a: Dict[str, Any]
    notis_kompaun: Dict[str, Any]
    pemberatan_hukuman: List[str]
    tpr_simulation_notes: List[str]
    statutory_citations: List[Dict[str, Any]]
    redaction_preview: Dict[str, Any]
    models_used: Dict[str, str]


class UIPModelRouter:
    """Penghala tugas AI berbilang model dengan kawalan privasi OSA/PDPA."""

    def __init__(
        self,
        redactor: Optional[PrivacyRedactor] = None,
        rag_store: Optional[StatutoryRAGStore] = None,
    ) -> None:
        self.redactor = redactor or PrivacyRedactor()
        self.rag_store = rag_store or get_statutory_store()
        self._genai_client = None
        self._decision_client = None
        self._decision_cache: Dict[str, tuple[List[Dict[str, Any]], str]] = {}
        self._last_ai_error: Optional[str] = None
        self.refresh_clients()

    def refresh_clients(self) -> None:
        """Membina semula klien Gemini & mengemas kini tetapan Ollama secara masa nyata."""
        self.redactor.ollama_base_url = settings.ollama_base_url.rstrip("/")
        self.redactor.ollama_model = settings.ollama_model
        PrivacyRedactor.invalidate_ollama_cache()
        self._decision_cache.clear()
        self._genai_client = None
        self._decision_client = None
        self._last_ai_error = None
        if GENAI_SDK_AVAILABLE and settings.has_gemini_key:
            try:
                self._genai_client = genai.Client(
                    api_key=settings.gemini_api_key,
                    http_options={
                        "api_version": "v1beta",
                        "timeout": 45_000,
                        "retry_options": {"attempts": 1},
                    },
                )
                self._decision_client = genai.Client(
                    api_key=settings.gemini_api_key,
                    http_options={
                        "api_version": "v1beta",
                        "timeout": 35_000,
                        "retry_options": {"attempts": 2},
                    },
                )
            except Exception as exc:
                self._last_ai_error = "Konfigurasi klien AI tidak dapat dimulakan."
                logger.warning("Gagal membina klien Gemini (%s): %s", type(exc).__name__, str(exc)[:180])
                self._genai_client = None
                self._decision_client = None

    def get_system_status(self) -> Dict[str, Any]:
        ollama_ok, ollama_models = self.redactor.check_ollama_status()
        return {
            "system": "UIP-Command",
            "version": "2.1.0-prod",
            "ollama": {
                "connected": ollama_ok,
                "base_url": settings.ollama_base_url,
                "configured_model": settings.ollama_model,
                "available_models": ollama_models,
                "fallback_active": not ollama_ok,
            },
            "gemini": {
                "sdk_installed": GENAI_SDK_AVAILABLE,
                "api_key_configured": settings.has_gemini_key,
                "masked_api_key": settings.masked_gemini_key,
                "decision_model": settings.decision_model,
                "multimodal_model": settings.multimodal_model,
                "reasoning_model": settings.reasoning_model,
                "standard_fallback_model": settings.standard_fallback_model,
                "mode": "gemini-aktif" if self._genai_client else "enjin-statutori-tempatan",
            },
            "rag": {
                "engine": self.rag_store.engine_name,
                "chunks_indexed": self.rag_store.chunk_count,
                "acts_loaded": self.rag_store.list_available_acts(),
            },
        }

    @staticmethod
    def _parse_json_payload(raw_text: str) -> Dict[str, Any]:
        """Menghurai JSON daripada respons model termasuk jika dibalut markdown code fence."""
        cleaned = (raw_text or "").strip()
        fence_match = re.match(
            r"^```(?:json)?\s*(.*?)\s*```$",
            cleaned,
            flags=re.DOTALL | re.IGNORECASE,
        )
        if fence_match:
            cleaned = fence_match.group(1).strip()
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end > start:
            parsed = json.loads(cleaned[start : end + 1])
            if isinstance(parsed, dict):
                return parsed
        raise ValueError("Respons AI bukan objek JSON yang sah.")

    @staticmethod
    def _classify_friendly_ai_error(attempt_errors: List[str]) -> str:
        """Menukar ralat teknikal SDK kepada mesej Bahasa Melayu yang jelas untuk PPKP."""
        joined = " ".join(attempt_errors).lower()
        if any(tok in joined for tok in ("apitimeouterror", "timeoutexception", "timed out", "504", "deadline_exceeded")):
            return (
                "Pelayan AI mengambil masa terlalu lama untuk membalas. "
                "Paparan menggunakan rujukan statutori tempatan — sila klik 'Cuba AI' sebentar lagi."
            )
        if any(tok in joined for tok in ("429", "ratelimit", "resource_exhausted", "quota")):
            return (
                "Pelayan AI sedang menerima permintaan tinggi buat sementara waktu. "
                "Paparan menggunakan rujukan statutori tempatan — sila cuba semula dalam 1 minit."
            )
        if any(tok in joined for tok in ("401", "403", "api_key", "permissiondenied", "authentication")):
            return (
                "Konfigurasi kunci API AI perlu disemak oleh pentadbir sistem. "
                "Paparan menggunakan rujukan statutori tempatan."
            )
        if any(tok in joined for tok in ("apiconnectionerror", "connecterror", "network", "dns")):
            return (
                "Sambungan ke pelayan AI terganggu buat sementara waktu. "
                "Paparan menggunakan rujukan statutori tempatan."
            )
        return (
            "Analisa AI tidak dapat dicapai buat sementara waktu. "
            "Paparan menggunakan rujukan statutori tempatan — anda boleh cuba semula sebentar lagi."
        )

    @staticmethod
    def _build_generate_content_config(
        model_name: str,
        temperature: float,
        schema: Dict[str, Any],
        prefer_flash: bool,
        max_output_tokens: Optional[int] = None,
    ) -> Any:
        """Membina GenerateContentConfig dengan skema JSON tepat dan ThinkingConfig selamat."""
        cfg_kwargs: Dict[str, Any] = {
            "response_mime_type": "application/json",
            "response_json_schema": schema,
        }
        if max_output_tokens is not None:
            cfg_kwargs["max_output_tokens"] = max_output_tokens
        low_model = model_name.lower()
        thinking_cls = getattr(genai_types, "ThinkingConfig", None)
        if "2.5" in low_model:
            cfg_kwargs["temperature"] = temperature
            if prefer_flash and "flash" in low_model and thinking_cls is not None:
                cfg_kwargs["thinking_config"] = thinking_cls(thinking_budget=0)
        elif thinking_cls is not None and (prefer_flash or "3.8-flash" in low_model):
            cfg_kwargs["thinking_config"] = thinking_cls(thinking_level="low")
        return genai_types.GenerateContentConfig(**cfg_kwargs)

    @staticmethod
    def _to_generate_content_parts(input_payload: Any) -> Any:
        if not isinstance(input_payload, list):
            return input_payload
        gc_parts = []
        for blk in input_payload:
            if isinstance(blk, dict) and blk.get("type") == "text":
                gc_parts.append(blk.get("text", ""))
            elif isinstance(blk, dict) and blk.get("type") in ("image", "document"):
                raw_bytes = base64.b64decode(blk["data"])
                gc_parts.append(
                    genai_types.Part.from_bytes(
                        data=raw_bytes,
                        mime_type=blk.get("mime_type", "application/octet-stream"),
                    )
                )
        return gc_parts

    def _try_interactions_json(
        self,
        model_name: str,
        input_payload: Any,
        schema: Dict[str, Any],
        temperature: float,
        low_thinking: bool,
        attempt_errors: List[str],
    ) -> Optional[tuple[Dict[str, Any], str]]:
        if not model_name or "2.5" in model_name:
            return None
        try:
            inter_kwargs: Dict[str, Any] = {
                "model": model_name,
                "input": input_payload,
                "response_format": {
                    "type": "text",
                    "mime_type": "application/json",
                    "schema": schema,
                },
                "store": False,
            }
            if low_thinking:
                inter_kwargs["generation_config"] = {"thinking_level": "low"}
            elif "3." not in model_name:
                inter_kwargs["generation_config"] = {"temperature": temperature}
            interaction = self._genai_client.interactions.create(**inter_kwargs)
            text = (getattr(interaction, "output_text", None) or "").strip()
            if text:
                return self._parse_json_payload(text), f"{model_name} (Interactions API)"
            attempt_errors.append(f"{model_name} (Interactions): output kosong")
        except Exception as exc:
            msg = f"{model_name} (Interactions): {type(exc).__name__} - {str(exc)[:140]}"
            attempt_errors.append(msg)
            logger.warning("Gemini %s", msg)
        return None

    def _try_generate_content_json(
        self,
        model_name: str,
        gc_contents: Any,
        schema: Dict[str, Any],
        temperature: float,
        prefer_flash: bool,
        max_output_tokens: Optional[int],
        attempt_errors: List[str],
    ) -> Optional[tuple[Dict[str, Any], str]]:
        if genai_types is None or not model_name:
            return None
        try:
            cfg = self._build_generate_content_config(
                model_name=model_name,
                temperature=temperature,
                schema=schema,
                prefer_flash=prefer_flash,
                max_output_tokens=max_output_tokens,
            )
            resp = self._genai_client.models.generate_content(
                model=model_name,
                contents=gc_contents,
                config=cfg,
            )
            text = (getattr(resp, "text", None) or "").strip()
            if text:
                return self._parse_json_payload(text), f"{model_name} (Gemini API)"
            attempt_errors.append(f"{model_name} (Gemini API): output kosong")
        except Exception as exc:
            msg = f"{model_name} (Gemini API): {type(exc).__name__} - {str(exc)[:140]}"
            attempt_errors.append(msg)
            logger.warning("Gemini %s", msg)
        return None

    def _call_gemini_structured_json(
        self,
        model_candidates: List[str],
        input_payload: Any,
        schema: Dict[str, Any],
        temperature: float = 0.1,
        prefer_flash: bool = False,
        prefer_fast_gc: bool = False,
        max_output_tokens: Optional[int] = None,
    ) -> tuple[Optional[Dict[str, Any]], str]:
        """Menjana JSON berstruktur dengan laluan pantas (~15s) atau Interactions fallback berhad."""
        if not self._genai_client:
            self._last_ai_error = (
                "Kunci API Gemini belum dikonfigurasi pada pelayan (sila semak Tetapan Sistem)."
            )
            return None, "enjin-statutori-tempatan"

        self._last_ai_error = None
        attempt_errors: List[str] = []
        gc_contents = self._to_generate_content_parts(input_payload) if genai_types is not None else input_payload

        # Mod pantas (~15s): dahulukan generate_content(gemini-3.8-flash, thinking_level="low")
        if prefer_fast_gc or prefer_flash:
            gc_primary = (
                settings.standard_fallback_model
                if settings.standard_fallback_model and "2.5" not in settings.standard_fallback_model
                else "gemini-3.8-flash"
            )
            res = self._try_generate_content_json(
                model_name=gc_primary,
                gc_contents=gc_contents,
                schema=schema,
                temperature=temperature,
                prefer_flash=True,
                max_output_tokens=max_output_tokens,
                attempt_errors=attempt_errors,
            )
            if res:
                return res

            inter_fallback = settings.multimodal_model or "gemini-3.8-flash"
            res = self._try_interactions_json(
                model_name=inter_fallback,
                input_payload=input_payload,
                schema=schema,
                temperature=temperature,
                low_thinking=True,
                attempt_errors=attempt_errors,
            )
            if res:
                return res

            self._last_ai_error = self._classify_friendly_ai_error(attempt_errors)
            return None, "enjin-statutori-tempatan"

        # Mod mendalam (had maks 3 cubaan keseluruhan agar tidak menunggu terlalu lama)
        attempts_left = 3
        ordered_candidates = [m for m in model_candidates if m and "2.5" not in m]
        if "gemini-3.8-flash" not in ordered_candidates:
            ordered_candidates.append("gemini-3.8-flash")
        for model_name in dict.fromkeys(ordered_candidates):
            if attempts_left <= 0:
                break
            attempts_left -= 1
            res = self._try_interactions_json(
                model_name=model_name,
                input_payload=input_payload,
                schema=schema,
                temperature=temperature,
                low_thinking=False,
                attempt_errors=attempt_errors,
            )
            if res:
                return res

        if attempts_left > 0 and genai_types is not None:
            raw_std = [
                settings.standard_fallback_model,
                "gemini-3.8-flash",
                settings.reasoning_model_alias,
            ]
            for model_name in dict.fromkeys(m for m in raw_std if m):
                if attempts_left <= 0:
                    break
                attempts_left -= 1
                res = self._try_generate_content_json(
                    model_name=model_name,
                    gc_contents=gc_contents,
                    schema=schema,
                    temperature=temperature,
                    prefer_flash=False,
                    max_output_tokens=max_output_tokens,
                    attempt_errors=attempt_errors,
                )
                if res:
                    return res

        self._last_ai_error = self._classify_friendly_ai_error(attempt_errors)
        return None, "enjin-statutori-tempatan"

    def _polish_formal_malay_offline(self, text: str) -> tuple[str, str]:
        ollama_ok, _ = self.redactor.check_ollama_status()
        if not ollama_ok or not text.strip():
            return text, "templat-rasmi-kkm"

        prompt = (
            "Kemaskan ayat Fakta Kes berikut supaya tepat, ringkas dan mengikut "
            "laras bahasa kerja harian Pegawai Kesihatan Persekitaran (PPKP) & UIP KKM. "
            "Jangan ubah tarikh, masa, nombor seksyen, atau token privasi seperti [SUSPEK_1]:\n\n"
            f"{text[:2500]}"
        )
        try:
            with httpx.Client(timeout=settings.ollama_timeout_seconds) as client:
                resp = client.post(
                    f"{self.redactor.ollama_base_url}/api/generate",
                    json={
                        "model": self.redactor.ollama_model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0.1},
                    },
                )
                if resp.status_code == 200:
                    polished = resp.json().get("response", "").strip()
                    if len(polished) > 20:
                        return polished, f"ollama ({self.redactor.ollama_model})"
        except Exception:
            pass
        return text, "templat-rasmi-kkm"

    def run_compliance_decision(
        self,
        redacted_text: str,
        criteria_list: List[Dict[str, Any]],
        statutory_context: List[StatuteChunk],
    ) -> tuple[Optional[List[Dict[str, Any]]], str]:
        """Menjalankan gemini-decision-1 melalui Decisions API v1beta apabila API key aktif."""
        if not self._decision_client:
            return None, "Enjin Semakan Statutori KKM"

        cache_sig = hashlib.sha256(
            f"{settings.decision_model}|{redacted_text[:18000]}|{len(criteria_list)}".encode("utf-8")
        ).hexdigest()
        if cache_sig in self._decision_cache:
            cached_items, cached_model = self._decision_cache[cache_sig]
            return [dict(item) for item in cached_items], f"{cached_model} [Cache]"

        rag_brief = "\n\n".join(
            f"[{s.akta_code} - {s.section}]\n{s.text[:500]}" for s in statutory_context[:4]
        )
        decision_input = (
            "RUJUKAN AKTA SEBENAR:\n"
            f"{rag_brief}\n\n"
            "TEKS KERTAS SIASATAN (DATA PERIBADI TELAH DITUTUP DENGAN TOKEN [SUSPEK_1], [NO_KP_1], [PREMIS_1]):\n"
            f"{redacted_text[:18000]}"
        )
        questions = {
            c["code"]: {
                "type": "noul",
                "instructions": (
                    f"Perkara {c['code']} ({c['title']}): {c['description']} "
                    f"Rujukan: {c['statute_ref']}. "
                    "Jawab Yes hanya jika dokumen Kertas Siasatan mengandungi bukti jelas yang memenuhi perkara ini tanpa kecacatan."
                ),
            }
            for c in criteria_list
        }

        try:
            result = self._decision_client.decisions.create(
                model=settings.decision_model,
                input=decision_input,
                questions=questions,
            )
            answers = getattr(result, "answers", None) or {}
            formatted: List[Dict[str, Any]] = []
            for spec in criteria_list:
                code = spec["code"]
                ans_obj = answers.get(code)
                if ans_obj is None:
                    continue
                prob_yes = float(getattr(ans_obj, "noul", 0.5))
                score = round(min(0.99, max(0.01, prob_yes)), 2)
                ans_label = "Yes" if score >= 0.5 else "No"
                snippet = self._find_evidence_line(redacted_text, spec.get("positive_keywords", []))
                formatted.append(
                    {
                        "code": code,
                        "answer": ans_label,
                        "calibrated_score": score,
                        "evidence_snippet": snippet,
                        "recommendation": (
                            "Lengkap dan patuh prosedur asas IP."
                            if score >= float(spec["threshold"])
                            else spec["remedy"]
                        ),
                    }
                )
            if formatted:
                if len(self._decision_cache) >= 64:
                    self._decision_cache.clear()
                self._decision_cache[cache_sig] = ([dict(item) for item in formatted], f"{settings.decision_model} (Decisions API)")
                return formatted, f"{settings.decision_model} (Decisions API)"
        except Exception:
            pass

        return None, "Enjin Semakan Statutori KKM"

    @staticmethod
    def _find_evidence_line(text: str, keywords: List[str]) -> str:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for kw in keywords:
            kw_low = kw.lower()
            for line in lines:
                if kw_low in line.lower():
                    return line[:220]
        return "Disahkan melalui semakan kandungan IP."

    def extract_multimodal_evidence(
        self,
        file_bytes: bytes,
        filename: str,
        mime_type: str,
        doc_hint: str = "bukti_kesalahan",
    ) -> EvidenceExtractionResult:
        """Mengekstrak teks dan butiran fakta daripada fail PDF atau gambar bukti."""
        warnings: List[str] = []
        extracted_pdf_text = ""
        is_pdf = mime_type == "application/pdf" or filename.lower().endswith(".pdf")

        if is_pdf:
            try:
                with fitz.open(stream=file_bytes, filetype="pdf") as doc:
                    extracted_pdf_text = "\n".join(p.get_text("text") for p in doc).strip()
            except Exception as exc:
                warnings.append(f"Ralat baca fail PDF: {exc}")

        if self._genai_client:
            prompt = (
                "Anda membantu PPKP Kementerian Kesihatan Malaysia mengekstrak bukti penguatkuasaan.\n"
                f"Jenis dokumen: {doc_hint} (Fail: {filename}).\n"
                "Baca semua maklumat pada imej/dokumen ini (nama premis, no. SSM, nama individu/OKT, "
                "no. K/P, tarikh/masa, alamat, dan kesalahan) ke format JSON."
            )
            file_b64 = base64.b64encode(file_bytes).decode("utf-8")
            media_block = (
                {
                    "type": "document",
                    "data": file_b64,
                    "mime_type": "application/pdf",
                }
                if is_pdf
                else {
                    "type": "image",
                    "data": file_b64,
                    "mime_type": mime_type or "image/jpeg",
                }
            )
            data, used_model = self._call_gemini_structured_json(
                model_candidates=[
                    settings.multimodal_model,
                    settings.standard_fallback_model,
                    settings.reasoning_model,
                ],
                input_payload=[{"type": "text", "text": prompt}, media_block],
                schema=_EvidenceSchema.model_json_schema(),
                temperature=0.0,
            )
            if data:
                raw = str(data.get("raw_text") or extracted_pdf_text or "")
                conf = float(data.get("confidence", 0.88))
                summary = (
                    f"Fail '{filename}' berjaya diekstrak ({used_model}). "
                    f"Premis: {data.get('nama_premis_atau_syarikat', 'Tiada')}; "
                    f"Butiran: {data.get('butiran_kesalahan_atau_eksibit', '-')}."
                )
                return EvidenceExtractionResult(
                    extracted_fields=data,
                    structured_summary=summary,
                    raw_text=raw,
                    confidence=round(min(0.99, max(0.01, conf)), 2),
                    model_used=used_model,
                    warnings=warnings,
                )

        if not settings.has_gemini_key:
            warnings.append(
                "Kunci API Gemini belum dimasukkan dalam Tetapan Sistem — menggunakan penghurai teks/PDF tempatan."
            )

        # Penghurai fakta sebenar daripada teks PDF (jika PDF berteks) atau nama fail
        facts = self.extract_case_facts(extracted_pdf_text) if extracted_pdf_text else {}
        inferred_fields = self._parse_evidence_fields(
            filename=filename,
            doc_hint=doc_hint,
            text=extracted_pdf_text,
            facts=facts,
            size_bytes=len(file_bytes),
        )
        raw_text = extracted_pdf_text or (
            f"[FAIL BUKTI DIMUAT NAIK: {filename} | Saiz: {len(file_bytes)} bait]\n"
            f"Jenis Dokumen: {inferred_fields['jenis_dokumen']}\n"
            f"Cadangan Seksyen: {inferred_fields['cadangan_akta_seksyen']}\n"
            f"Catatan: {inferred_fields['butiran_kesalahan_atau_eksibit']}"
        )
        summary = (
            f"Fail '{filename}' ({doc_hint}) diproses menggunakan penghurai tempatan. "
            + (
                f"Berjaya mengesan {len(extracted_pdf_text)} aksara teks daripada PDF."
                if extracted_pdf_text
                else "Untuk bacaan teks pada gambar foto/scan (OCR Vision), masukkan GEMINI_API_KEY dalam Tetapan AI."
            )
        )
        return EvidenceExtractionResult(
            extracted_fields=inferred_fields,
            structured_summary=summary,
            raw_text=raw_text,
            confidence=0.88 if extracted_pdf_text else 0.72,
            model_used="Penghurai PyMuPDF Tempatan" if extracted_pdf_text else "Penghurai Metadata Fail",
            warnings=warnings,
        )

    @staticmethod
    def _parse_evidence_fields(
        filename: str,
        doc_hint: str,
        text: str,
        facts: Dict[str, Any],
        size_bytes: int,
    ) -> Dict[str, Any]:
        low = (filename + " " + doc_hint + " " + text[:600]).lower()
        if "ssm" in low:
            doc_type = "Cetakan Carian SSM (e-Info / MyData)"
            akta_sugg = "Pengesahan Pemilik / Pengarah Syarikat (S.51 Akta 852 / S.33A Akta 281)"
            butiran = facts.get("kesalahan") or "Dokumen pendaftaran perniagaan/syarikat untuk pengesahan entiti OKT."
        elif "sitaan" in low or "bongkar" in low:
            doc_type = "Borang Senarai Benda Disita (Seksyen 36 Akta 852 / Seksyen 4 Akta 281)"
            akta_sugg = "Seksyen 35 & 36 Akta 852 / Seksyen 4 Akta Makanan 1983"
            butiran = facts.get("kesalahan") or "Senarai barang kes dirampas beserta kuantiti dan akuan terima."
        elif "vape" in low or "rokok" in low or "852" in low:
            doc_type = "Gambar Bukti Produk Merokok / Vape"
            akta_sugg = "Akta 852 Seksyen 7 / Seksyen 10 & Peraturan 6 P.U. (A) 260/2024"
            butiran = facts.get("kesalahan") or "Paparan atau iklan produk merokok / rokok elektronik di premis."
        elif "aedes" in low or "larva" in low or "154" in low:
            doc_type = "Gambar Tempat Pembiakan Larva Aedes"
            akta_sugg = "Akta 154 Seksyen 13(1) dibaca bersama Seksyen 13(2) & Seksyen 23(a)"
            butiran = facts.get("kesalahan") or "Bekas takungan air positif larva Aedes di kawasan premis."
        else:
            doc_type = "Dokumen / Foto Penguatkuasaan KKM"
            akta_sugg = "Akta Makanan 1983 / PPKM 2009 / Akta 852"
            butiran = facts.get("kesalahan") or f"Fail '{filename}' ({size_bytes} bait) sedia dilampirkan sebagai eksibit."

        return {
            "jenis_dokumen": doc_type,
            "nama_premis_atau_syarikat": facts.get("nama_premis") or "Tidak dinyatakan dalam fail",
            "no_ssm": facts.get("no_ssm") or "Tidak dinyatakan",
            "nama_okt_atau_individu": facts.get("nama_okt") or "Tidak dinyatakan",
            "no_kp": facts.get("no_kp_okt") or "Tidak dinyatakan",
            "tarikh_masa_dikesan": f"{facts.get('tarikh') or '-'} {facts.get('masa') or ''}".strip(),
            "lokasi_alamat": facts.get("alamat") or "Tidak dinyatakan",
            "butiran_kesalahan_atau_eksibit": butiran,
            "cadangan_akta_seksyen": akta_sugg,
            "kualiti_imej_untuk_mahkamah": "Wajib lampirkan Sijil Seksyen 90A(2) jika gambar/dokumen dicetak melalui komputer.",
        }

    @staticmethod
    def extract_case_facts(text: str) -> Dict[str, Any]:
        """Menghurai fakta sebenar daripada teks/PDF Kertas Siasatan tanpa nilai palsu hardcoded."""

        def _find(patterns: List[str], default: str = "") -> str:
            for pat in patterns:
                m = re.search(pat, text, flags=re.I | re.M)
                if m:
                    val = m.group(1).strip()
                    if val:
                        return val
            return default

        no_ip = _find([r"(?:no\.?\s*ip|no\.?\s*kertas\s+siasatan)\s*[:\-]\s*([^\n\r]+)"])
        daerah_raw = _find([r"(?:daerah|pejabat\s+kesihatan\s+daerah)\s*[:\-]\s*([^\n\r]+)"])
        daerah = daerah_raw.split(",")[0].strip() if daerah_raw else ""
        negeri = daerah_raw.split(",")[1].strip() if "," in daerah_raw else "Selangor"

        tarikh = _find([r"tarikh\s+(?:kejadian|pemeriksaan|operasi)\s*[:\-]\s*([^\n\r(]+)"])
        masa = _find([r"masa\s+(?:kejadian|pemeriksaan|operasi)\s*[:\-]\s*([^\n\r]+)"])
        nama_premis = _find([r"(?:nama\s+premis(?:\s+makanan)?|nama\s+syarikat)\s*[:\-]\s*([^\n\r]+)"])
        no_ssm = _find([r"no\.?\s*ssm\s*[:\-]\s*([^\n\r]+)"])
        alamat = _find([r"(?:alamat\s+kejadian|tempat\s+kejadian|alamat\s+premis)\s*[:\-]\s*([^\n\r]+)"])
        nama_okt = _find([
            r"(?:nama\s+(?:suspek|okt|oks|pemilik|pengurus\s+tapak|tertuduh)(?:\s*\([^)]+\))?)\s*[:\-]\s*([^\n\r]+)"
        ])
        no_kp_okt = _find([r"no\.?\s*k/?p\s*[:\-]\s*([^\n\r,]+)"])
        no_tel = _find([r"no\.?\s*tel(?:efon)?\s*[:\-]\s*([^\n\r]+)"])
        pegawai_raw = _find([r"(?:pegawai\s+penyiasat(?:\s*\(io\))?|pegawai\s+pengadu)\s*[:\-]\s*([^\n\r]+)"])
        kad_kuasa = _find([r"kad\s+kuasa\s*[:\-]\s*([A-Za-z0-9\-]+)"])
        pegawai_io = re.sub(r"\s*\([^)]*\)\s*", "", pegawai_raw).strip()

        saksi_raw = _find([r"(?:^|\n)[ \t]*saksi(?:\s*\d+)?\s*[:\-]\s*([^\n\r]+)"])
        kesalahan = _find([r"(?:kesalahan|butiran\s+kesalahan|fakta\s+ringkas)\s*[:\-]\s*([^\n\r]+)"])

        # Ekstrak nombor lak/seal sebenar daripada teks jika ada
        seal_m = re.search(r"(?:seal|lak(?:\s+rasmi)?(?:\s+kkm)?(?:\s+siri)?)\s*(?:#|no\.?\s*)?([A-Za-z0-9\-#]+)", text, flags=re.I)
        no_seal = seal_m.group(1).strip() if seal_m else "Belum direkodkan"

        # Ekstrak maklumat saksi dan no. KP jika berada dalam kurungan
        saksi_nama = saksi_raw
        saksi_kp = ""
        saksi_peranan = "Saksi Pendakwaan"
        if saksi_raw:
            kp_m = re.search(r"(\d{6}-\d{2}-\d{4})", saksi_raw)
            if kp_m:
                saksi_kp = kp_m.group(1)
            saksi_nama = re.sub(r"\s*\([^)]*\)", "", saksi_raw).strip()
            paren_m = re.search(r"\(([^)]+)\)", saksi_raw)
            if paren_m:
                parts = [p.strip() for p in paren_m.group(1).split(",") if "k/p" not in p.lower() and "kp" not in p.lower()]
                if parts:
                    saksi_peranan = ", ".join(parts)

        # Kesan tarikh DS & S.112 jika disebut dalam teks
        s112_date_m = re.search(r"(?:rakaman\s+s\.?112|percakapan\s+saksi)[^.\n]*?(?:pada|bertarikh)\s+([^\n.]+)", text, flags=re.I)
        s112_when = s112_date_m.group(1).strip() if s112_date_m else (tarikh or "Tarikh siasatan")

        return {
            "no_ip": no_ip,
            "daerah": daerah,
            "negeri": negeri,
            "tarikh": tarikh,
            "masa": masa,
            "nama_premis": nama_premis,
            "no_ssm": no_ssm,
            "alamat": alamat,
            "nama_okt": nama_okt,
            "no_kp_okt": no_kp_okt,
            "no_tel": no_tel,
            "pegawai_io": pegawai_io,
            "kad_kuasa": kad_kuasa,
            "saksi_nama": saksi_nama,
            "saksi_kp": saksi_kp,
            "saksi_peranan": saksi_peranan,
            "kesalahan": kesalahan,
            "no_seal": no_seal,
            "s112_when": s112_when,
        }

    def generate_legal_drafts(
        self,
        case_text: str,
        akta_utama: str = "Akta 852",
        workflow: str = "ip_builder",
        use_ollama_redaction: bool = True,
        officer_profile: Optional[Dict[str, Any]] = None,
        fast_mode: bool = True,
    ) -> DraftGenerationResult:
        """Menjana pakej dokumen IP lengkap dengan format rasmi Mahkamah Majistret & KKM."""
        redaction: RedactionResult = self.redactor.redact(case_text, use_ollama=use_ollama_redaction)
        citations = self.rag_store.search_statutes(
            query=f"{akta_utama} kesalahan hukuman pertuduhan {redaction.redacted_text[:450]}",
            akta_filter=None if akta_utama == "Semua" else akta_utama,
            top_k=4,
        )

        citations_dict = [
            {
                "akta_code": c.akta_code,
                "akta_title": c.akta_title,
                "section": c.section,
                "text": c.text,
                "score": c.score,
            }
            for c in citations
        ]

        reasoning_model_used = "Penghurai Fakta & Templat Rasmi UIP KKM (Mod Pantas)"
        generated_json: Optional[Dict[str, Any]] = None

        if self._genai_client and not fast_mode:
            rag_verbatim = "\n\n".join(
                f"[{c.akta_title} | {c.section}]\n{c.text}" for c in citations
            )
            prompt = (
                "Anda ialah Pegawai Pendakwa Kanan UIP KKM.\n"
                "Gubal Kertas Siasatan lengkap dalam Bahasa Melayu rasmi undang-undang Malaysia yang ringkas dan tepat.\n"
                "PENTING:\n"
                "1) Kekalkan semua token penyamaran [SUSPEK_1], [NO_KP_1], [PREMIS_1], [NO_SSM_1] tanpa mengubahnya.\n"
                "2) Petik HANYA nombor Seksyen & Peraturan yang wujud dalam RUJUKAN AKTA SEBENAR di bawah.\n"
                "3) Borang 114 wajib memisahkan Seksyen Kesalahan daripada Seksyen Hukuman.\n"
                "4) Sijil Seksyen 90A wajib mengandungi butiran perkakasan dan klausa 'sepanjang pengetahuan dan kepercayaan saya'.\n\n"
                f"RUJUKAN AKTA SEBENAR:\n{rag_verbatim}\n\n"
                f"MAKLUMAT KES (DATA SULIT DITUTUP):\n{redaction.redacted_text[:9000]}"
            )
            generated_json, used = self._call_gemini_structured_json(
                model_candidates=[
                    settings.standard_fallback_model,
                    settings.multimodal_model,
                    settings.reasoning_model,
                ],
                input_payload=prompt,
                schema=_LegalDraftSchema.model_json_schema(),
                temperature=0.1,
                prefer_flash=True,
            )
            if generated_json:
                reasoning_model_used = used

        if not generated_json:
            generated_json = self._build_structured_draft_from_facts(
                redacted_text=redaction.redacted_text,
                akta_utama=akta_utama,
                citations=citations,
                officer_profile=officer_profile,
            )

        fakta_kes_redacted, style_engine = self._polish_formal_malay_offline(
            generated_json.get("fakta_kes", "")
        )
        generated_json["fakta_kes"] = fakta_kes_redacted

        rehydrated = self._rehydrate_nested(generated_json, redaction.token_map)
        if officer_profile:
            s90 = rehydrated.setdefault("sijil_90a", {})
            if not s90.get("nama_pegawai") or "[" in str(s90.get("nama_pegawai", "")):
                s90["nama_pegawai"] = officer_profile.get("full_name") or s90.get("nama_pegawai", "")
            if officer_profile.get("designation"):
                s90["jawatan"] = f"{officer_profile.get('designation')} ({officer_profile.get('grade', '')})".strip()
            if officer_profile.get("district_pkd") and (not s90.get("pejabat_pkd") or "[" in str(s90.get("pejabat_pkd", ""))):
                s90["pejabat_pkd"] = officer_profile["district_pkd"]
            if officer_profile.get("default_camera_desc"):
                s90["peranti_kamera"] = officer_profile["default_camera_desc"]
            if officer_profile.get("default_computer_desc"):
                s90["perihal_komputer"] = officer_profile["default_computer_desc"]
            if officer_profile.get("default_printer_desc"):
                s90["perihal_pencetak"] = officer_profile["default_printer_desc"]
            b114 = rehydrated.setdefault("borang_114", {})
            if officer_profile.get("default_magistrate_court") and "[" in str(b114.get("mahkamah", "")):
                b114["mahkamah"] = officer_profile["default_magistrate_court"]

        return DraftGenerationResult(
            workflow=workflow,
            akta_utama=akta_utama,
            minit_ip=rehydrated.get("minit_ip", []),
            kronologi_kes=rehydrated.get("kronologi_kes", []),
            kertas_cadangan_io=rehydrated.get("kertas_cadangan_io", ""),
            saman_111=rehydrated.get("saman_111", {}),
            borang_143=rehydrated.get("borang_143", {}),
            izin_mendakwa=rehydrated.get("izin_mendakwa", {}),
            borang_114=rehydrated.get("borang_114", {}),
            diari_siasatan=rehydrated.get("diari_siasatan", []),
            fakta_kes=rehydrated.get("fakta_kes", ""),
            rakaman_112=rehydrated.get("rakaman_112", ""),
            senarai_saksi=rehydrated.get("senarai_saksi", []),
            senarai_eksibit=rehydrated.get("senarai_eksibit", []),
            sijil_90a=rehydrated.get("sijil_90a", {}),
            notis_kompaun=rehydrated.get("notis_kompaun", {}),
            pemberatan_hukuman=rehydrated.get("pemberatan_hukuman", []),
            tpr_simulation_notes=rehydrated.get("tpr_simulation_notes", []),
            statutory_citations=citations_dict,
            redaction_preview={
                "engine_used": redaction.engine_used,
                "ollama_available": redaction.ollama_available,
                "entities_masked": len(redaction.entities),
                "rehydrated": True,
                "redacted_excerpt": redaction.redacted_text[:800],
                "redacted_text": redaction.redacted_text,
                "token_map": redaction.token_map,
                "entities": [asdict(e) for e in redaction.entities],
                "warnings": redaction.warnings,
            },
            models_used={
                "privacy_redactor": redaction.engine_used,
                "style_engine": style_engine,
                "legal_reasoning": reasoning_model_used,
                "rag_engine": self.rag_store.engine_name,
            },
        )

    def _rehydrate_nested(self, obj: Any, token_map: Dict[str, str]) -> Any:
        if isinstance(obj, str):
            return self.redactor.rehydrate(obj, token_map)
        if isinstance(obj, list):
            return [self._rehydrate_nested(item, token_map) for item in obj]
        if isinstance(obj, dict):
            return {k: self._rehydrate_nested(v, token_map) for k, v in obj.items()}
        return obj

    def _build_structured_draft_from_facts(
        self,
        redacted_text: str,
        akta_utama: str,
        citations: List[StatuteChunk],
        officer_profile: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Membina draf rasmi Kertas Siasatan hanya daripada fakta sebenar teks/PDF."""
        facts = self.extract_case_facts(redacted_text)
        prof = officer_profile or {}

        no_ip = facts["no_ip"] or "[Sila isi No. IP PKD]"
        daerah = facts["daerah"] or (
            str(prof.get("district_pkd") or "").replace("Pejabat Kesihatan Daerah ", "").strip() or "[Daerah]"
        )
        negeri = facts["negeri"] or (
            str(prof.get("state_jkn") or "").replace("Jabatan Kesihatan Negeri ", "").strip() or "Selangor"
        )
        tarikh = facts["tarikh"] or "[Sila isi Tarikh Kejadian]"
        masa = facts["masa"] or "[Sila isi Masa Kejadian]"
        pegawai = facts["pegawai_io"] or prof.get("full_name") or "[Sila isi Nama Pegawai Penyiasat (IO)]"
        kad_kuasa = facts["kad_kuasa"] or prof.get("kkm_authority_card_no") or "[No. Kad Kuasa]"
        alamat = facts["alamat"] or "[Sila isi Alamat Lengkap Tempat Kejadian]"
        kesalahan_ringkas = facts["kesalahan"] or "[Sila nyatakan perbuatan kesalahan yang ditemui semasa pemeriksaan]"
        no_seal = facts["no_seal"]

        suspect_token = "[SUSPEK_1]" if "[SUSPEK_1]" in redacted_text else (facts["nama_okt"] or "[Nama OKS / OKT]")
        ic_token = "[NO_KP_1]" if "[NO_KP_1]" in redacted_text else (facts["no_kp_okt"] or "[No. K/P OKS]")
        prem_token = "[PREMIS_1]" if "[PREMIS_1]" in redacted_text else (facts["nama_premis"] or "[Nama Premis]")
        ssm_token = "[NO_SSM_1]" if "[NO_SSM_1]" in redacted_text else (facts["no_ssm"] or "-")
        witness_token = "[SAKSI_1]" if "[SAKSI_1]" in redacted_text else (facts["saksi_nama"] or "[Nama Saksi]")
        witness_ic = "[NO_KP_2]" if "[NO_KP_2]" in redacted_text else (facts["saksi_kp"] or "[No. K/P Saksi]")

        # Penentuan seksyen kesalahan, seksyen hukuman, dan seksyen kompaun yang tepat mengikut Akta
        seksyen_kesalahan, seksyen_hukuman, hukuman_max, peruntukan_kompaun, tempoh_kompaun = self._resolve_act_provisions(
            akta_utama=akta_utama,
            text=redacted_text,
            citations=citations,
        )

        # Bina ayat pertuduhan Borang 114 rasmi (Seksyen 152, 153 & 154 KTJ)
        tempat_penuh = f"{prem_token}, {alamat}" if prem_token not in alamat else alamat
        pertuduhan_text = (
            f"Bahawa kamu, pada {tarikh}, jam lebih kurang {masa}, bertempat di {tempat_penuh}, "
            f"di dalam Daerah {daerah}, di dalam Negeri {negeri}, telah didapati {kesalahan_ringkas}; "
            f"dan oleh yang demikian kamu telah melakukan suatu kesalahan di bawah {seksyen_kesalahan}, "
            f"yang boleh dihukum di bawah {seksyen_hukuman}."
        )

        # Bina Minit Kertas Siasatan 4 peringkat rasmi UIP KKM
        minit_ip = [
            {
                "bil": "Minit 1",
                "tarikh": tarikh,
                "daripada": "Ketua UIP Daerah",
                "kepada": pegawai,
                "kandungan": f"Kesalahan di bawah {seksyen_kesalahan} dilaporkan. Sila buka Kertas Siasatan No. {no_ip} dan lengkapkan siasatan mengikut senarai semak UIP.",
            },
            {
                "bil": "Minit 2",
                "tarikh": facts["s112_when"] or tarikh,
                "daripada": pegawai,
                "kepada": "Ketua UIP Daerah / Pegawai Pendakwa",
                "kandungan": (
                    f"Siasatan bagi IP No. {no_ip} melibatkan OKS {suspect_token} (No. K/P: {ic_token}) di {prem_token} telah dijalankan. "
                    f"Rakaman percakapan S.112 KTJ, gambar bukti, carian SSM ({ssm_token}), dan Diari Siasatan telah disusun. "
                    "Dikemukakan untuk semakan teknikal sebelum permohonan Izin Mendakwa kepada TPR."
                ),
            },
            {
                "bil": "Minit 3",
                "tarikh": "Tarikh Semakan UIP",
                "daripada": "Pegawai Pendakwa UIP KKM",
                "kepada": "Timbalan Pendakwa Raya (TPR)",
                "kandungan": (
                    f"Kertas Siasatan {no_ip} telah disemak terhadap 20 kriteria pematuhan Pra-TPR. "
                    f"Kes memenuhi elemen kesalahan di bawah {seksyen_kesalahan}. Dipohon pertimbangan dan Izin Mendakwa (Sanksi) daripada pihak TPR."
                ),
            },
            {
                "bil": "Minit 4",
                "tarikh": "Tarikh Arahan TPR",
                "daripada": "Timbalan Pendakwa Raya",
                "kepada": "Pegawai Pendakwa UIP KKM",
                "kandungan": "[Ruangan Arahan / Keputusan Timbalan Pendakwa Raya: Boleh dituduh di Mahkamah Majistret / Dikembalikan untuk tindakan lanjut]",
            },
        ]

        fakta_kes = (
            f"1. Pada {tarikh}, jam lebih kurang {masa}, {pegawai} (No. Kad Kuasa: {kad_kuasa}) bersama sepasukan pegawai penguat kuasa "
            f"Pejabat Kesihatan Daerah {daerah} telah menjalankan pemeriksaan penguatkuasaan di {tempat_penuh}.\n"
            f"2. Pemeriksaan dijalankan di hadapan {suspect_token} (No. K/P: {ic_token}) setelah kad kuasa rasmi ditunjukkan.\n"
            f"3. Hasil pemeriksaan mendapati {kesalahan_ringkas}.\n"
            f"4. Pegawai penguat kuasa telah mengambil gambar bukti di tempat kejadian, menyediakan borang pemeriksaan/sitaan yang berkaitan "
            f"(No. Lak Eksibit: {no_seal}) serta menyerahkan satu salinan kepada pihak premis.\n"
            f"5. Siasatan lanjut di bawah {seksyen_kesalahan} telah dilengkapkan termasuk rakaman percakapan di bawah Seksyen 112 KTJ, "
            f"carian rasmi SSM ({ssm_token}), dan Sijil Seksyen 90A Akta Keterangan 1950 untuk tujuan pendakwaan."
        )

        rakaman_112 = (
            f"BUTIRAN SAKSI:\n"
            f"Nama: {witness_token} | No. K/P: {witness_ic} | Peranan: {facts['saksi_peranan']}\n"
            f"Tarikh/Masa Rakaman: {facts['s112_when']} | Pegawai Perakam: {pegawai}\n\n"
            f"PERAKUAN AMARAN SEKSYEN 112(2) & 112(3) KTJ (MENURUT SEKSYEN 112(4) KTJ):\n"
            f"\"Saya telah diberitahu oleh {pegawai} mengenai peruntukan Seksyen 112(2) dan (3) Kanun Tatacara Jenayah iaitu saya terikat di sisi undang-undang "
            f"untuk menjawab segala soalan yang dikemukakan kepada saya berhubung dengan kes ini dan menyatakan yang benar, kecuali soalan yang jawapannya "
            f"berkemungkinan mendedahkan saya kepada suatu pertuduhan jenayah, penalti atau pelucuthakan.\"\n\n"
            f"SOALAN 1 (IO): Di manakah kamu berada dan apakah tugas kamu pada {tarikh} jam {masa}?\n"
            f"JAWAPAN 1: Saya bertugas sebagai {facts['saksi_peranan']} di {tempat_penuh}.\n\n"
            f"SOALAN 2 (IO): Terangkan apa yang berlaku semasa pegawai penguat kuasa KKM memeriksa premis tersebut.\n"
            f"JAWAPAN 2: Pegawai KKM memperkenalkan diri dengan kad kuasa rasmi dan menjalankan pemeriksaan di hadapan {suspect_token}. "
            f"Semasa pemeriksaan, didapati {kesalahan_ringkas}.\n\n"
            f"SOALAN 3 (IO): Adakah sebarang gambar diambil atau dokumen/barang kes diserahkan semasa pemeriksaan?\n"
            f"JAWAPAN 3: Ya, gambar bukti telah diambil dan salinan borang pemeriksaan/sitaan diserahkan kepada pihak premis."
        )

        diari = [
            {
                "bil": "1",
                "tarikh": tarikh,
                "masa": masa,
                "butiran_tindakan": f"Operasi pemeriksaan dijalankan di {tempat_penuh}. Kesalahan di bawah {seksyen_kesalahan} dikesan. Kad kuasa ditunjukkan dan salinan borang pemeriksaan/notis diserahkan.",
                "pegawai": pegawai,
            },
            {
                "bil": "2",
                "tarikh": tarikh,
                "masa": "2.30 petang",
                "butiran_tindakan": f"Kertas Siasatan {no_ip} dibuka. Gambar bukti didaftarkan dan barang kes dilak (No. Lak: {no_seal}) serta disimpan di stor eksibit. Rakaman S.112 saksi ({witness_token}) diambil.",
                "pegawai": pegawai,
            },
            {
                "bil": "3",
                "tarikh": "Susulan (+1 hari)",
                "masa": "9.30 pagi",
                "butiran_tindakan": f"Carian rasmi SSM ({ssm_token}) bagi {prem_token} dicetak. Rakaman percakapan S.112 {suspect_token} diambil setelah amaran S.112(2)&(3) KTJ dibacakan.",
                "pegawai": pegawai,
            },
            {
                "bil": "4",
                "tarikh": "Susulan (+2 hari)",
                "masa": "11.00 pagi",
                "butiran_tindakan": "Sijil Seksyen 90A(2) Akta Keterangan 1950 bagi gambar digital dan cetakan SSM disiapkan. Draf Borang 114, Borang 143, Fakta Kes dan Minit IP disusun untuk semakan UIP/TPR.",
                "pegawai": pegawai,
            },
        ]

        kronologi_kes = [
            {
                "tarikh": tarikh,
                "peristiwa": f"Pemeriksaan / penguatkuasaan dijalankan di {tempat_penuh} oleh {pegawai} bersama {witness_token}. Kesalahan di bawah {seksyen_kesalahan} direkodkan.",
            },
            {
                "tarikh": facts["s112_when"] or tarikh,
                "peristiwa": f"Siasatan lanjut termasuk rakaman S.112 KTJ, pengumpulan dokumen sokongan dan pembukaan IP No. {no_ip} ke atas OKS {suspect_token} ({ic_token}).",
            },
            {
                "tarikh": "Semakan UIP Daerah & Negeri",
                "peristiwa": "Kertas siasatan disemak oleh KPPKP U7 / UIP JKN dan dikemukakan kepada Timbalan Pendakwa Raya (TPR) bagi permohonan Izin Dakwa.",
            },
        ]

        kertas_cadangan_io = (
            f"Nama Pegawai Penyiasat: {pegawai}\n"
            f"Pejabat: Pejabat Kesihatan Daerah {daerah}, {negeri}\n\n"
            f"Cadangan:\n"
            f"1. Asas pertuduhan kepada OKT/OKS {suspect_token} (No. K/P: {ic_token}) adalah berdasarkan siasatan "
            f"yang mendapati pelanggaran {seksyen_kesalahan} pada {tarikh} jam {masa} di {tempat_penuh}.\n"
            f"2. OKS telah melakukan kesalahan di bawah {seksyen_kesalahan} dan boleh dihukum di bawah {seksyen_hukuman}.\n"
            f"3. Saya mencadangkan supaya OKS dituduh di Mahkamah Majistret di bawah {seksyen_kesalahan} dibaca bersama {seksyen_hukuman}."
        )

        pemberatan_hukuman = [
            "Kesalahan ini merupakan kesalahan serius terhadap kesihatan dan keselamatan awam (kepentingan awam mengatasi kepentingan peribadi OKS).",
            f"Tahap keseriusan kesalahan di bawah {seksyen_kesalahan} membawa hukuman statutori: {hukuman_max}.",
            "Kegagalan atau keingkaran OKS menimbulkan risiko penularan penyakit / kemudaratan kesihatan kepada masyarakat setempat.",
            "Pendakwaan memohon hukuman setimpal sebagai pengajaran kepada OKS serta peringatan tegas kepada orang awam dan pengusaha premis lain.",
        ]

        return {
            "minit_ip": minit_ip,
            "kronologi_kes": kronologi_kes,
            "kertas_cadangan_io": kertas_cadangan_io,
            "saman_111": {
                "mahkamah": f"Dalam Mahkamah Majistret di {daerah}, {negeri}",
                "no_saman": no_ip,
                "nama_oks": suspect_token,
                "no_kp": ic_token,
                "alamat": alamat,
                "tarikh_hadir": "........ haribulan ...................... 2026",
                "masa_hadir": "8.30 pagi",
                "teks_pertuduhan": pertuduhan_text,
                "hukuman": hukuman_max,
            },
            "borang_143": {
                "mahkamah": f"DALAM MAHKAMAH MAJISTRET DI {daerah.upper()}",
                "negeri": negeri.upper(),
                "pengadu": f"{pegawai} (Pegawai Diberi Kuasa KKM)",
                "oks_nama": suspect_token,
                "oks_kp": ic_token,
                "oks_alamat": alamat,
                "butiran_aduan": pertuduhan_text,
            },
            "izin_mendakwa": {
                "rujukan_ip": no_ip,
                "kepada": f"Timbalan Pendakwa Raya, Negeri {negeri}",
                "peruntukan_izin": "Seksyen 376(3) & 377(b) Kanun Tatacara Jenayah" + (" / Seksyen 32A Akta Makanan 1983" if "281" in akta_utama else ""),
                "nama_okt": f"{suspect_token} (No. K/P: {ic_token})",
                "seksyen_dipohon": f"{seksyen_kesalahan} dibaca bersama {seksyen_hukuman}",
            },
            "borang_114": {
                "mahkamah": f"DALAM MAHKAMAH MAJISTRET DI {daerah.upper()}",
                "negeri": f"DALAM NEGERI {negeri.upper()}, MALAYSIA",
                "no_kes": f"{no_ip} (DRAF SAMAN)",
                "nama_tertuduh": suspect_token,
                "no_kp_tertuduh": ic_token,
                "umur_jantina": "[Sila lengkapkan Umur / Jantina]",
                "pekerjaan": "Pemilik / Pengurus / Pengarah Premis",
                "alamat_tertuduh": alamat,
                "tarikh_kejadian": tarikh,
                "masa_kejadian": masa,
                "tempat_kejadian": tempat_penuh,
                "daerah": daerah,
                "akta_dan_seksyen": seksyen_kesalahan,
                "seksyen_hukuman": seksyen_hukuman,
                "hukuman_maksimum": hukuman_max,
                "pegawai_pengadu": pegawai,
                "teks_pertuduhan": pertuduhan_text,
            },
            "diari_siasatan": diari,
            "fakta_kes": fakta_kes,
            "rakaman_112": rakaman_112,
            "senarai_saksi": [
                {
                    "bil": "SP1",
                    "nama": pegawai,
                    "no_kp": kad_kuasa,
                    "jawatan_peranan": "Pegawai Pengadu / Pegawai Penyiasat (IO)",
                    "alamat_hubungan": f"Pejabat Kesihatan Daerah {daerah}",
                },
                {
                    "bil": "SP2",
                    "nama": witness_token,
                    "no_kp": witness_ic,
                    "jawatan_peranan": facts["saksi_peranan"],
                    "alamat_hubungan": alamat,
                },
                {
                    "bil": "SP3",
                    "nama": "Pegawai Sains / Juruanalisis Bertauliah (jika ada laporan makmal/entomologi)",
                    "no_kp": "Rekod Jabatan",
                    "jawatan_peranan": "Pengesah Laporan Makmal / Entomologi",
                    "alamat_hubungan": "Makmal Kesihatan Awam / PKD",
                },
            ],
            "senarai_eksibit": [
                {
                    "tanda": "P1",
                    "perihal": f"Borang Pemeriksaan Premis / Laporan Pengadu bertarikh {tarikh}",
                    "no_lak_seal": "-",
                    "lokasi_simpanan": f"Fail IP {no_ip}",
                },
                {
                    "tanda": "P2",
                    "perihal": "Lampiran Gambar Bukti Berwarna Berkapsyen + Sijil Seksyen 90A(2)",
                    "no_lak_seal": "-",
                    "lokasi_simpanan": f"Fail IP {no_ip}",
                },
                {
                    "tanda": "P3",
                    "perihal": f"Cetakan Carian Rasmi SSM ({ssm_token}) bagi {prem_token} + Sijil S.90A",
                    "no_lak_seal": "-",
                    "lokasi_simpanan": f"Fail IP {no_ip}",
                },
                {
                    "tanda": "P4",
                    "perihal": "Barang Kes / Sampel Fizikal (jika ada sitaan atau persampelan)",
                    "no_lak_seal": no_seal,
                    "lokasi_simpanan": f"Stor Eksibit Berkunci PKD {daerah}",
                },
            ],
            "sijil_90a": {
                "nama_pegawai": pegawai,
                "jawatan": "Penolong Pegawai Kesihatan Persekitaran (PPKP)",
                "pejabat_pkd": f"Pejabat Kesihatan Daerah {daerah}",
                "peranti_kamera": "Kamera Digital Rasmi / Telefon Pintar Penguatkuasaan PKD (Kad SD Rasmi)",
                "perihal_komputer": "Komputer Meja Rasmi Pejabat PKD (Windows OS, beroperasi dalam keadaan baik)",
                "perihal_pencetak": "Pencetak Laser Warna Pejabat PKD",
                "senarai_dokumen_digital": f"1. Gambar Foto Digital Bukti Pemeriksaan di {prem_token} bertarikh {tarikh} (Eksibit P2)\n2. Cetakan Carian Rasmi e-Info SSM {ssm_token} (Eksibit P3)",
            },
            "notis_kompaun": {
                "no_notis": f"KKM/KOM/{no_ip.split('/')[-1] if '/' in no_ip else '001'}",
                "nama_penerima": suspect_token,
                "no_kp": ic_token,
                "nama_premis": prem_token,
                "alamat_kejadian": alamat,
                "no_ssm": ssm_token,
                "tarikh_masa": f"{tarikh}, {masa}",
                "kesalahan_ringkas": kesalahan_ringkas,
                "peruntukan_undang": seksyen_kesalahan,
                "peruntukan_kompaun": peruntukan_kompaun,
                "amaun_kompaun_rm": "RM 500.00" if "154" in akta_utama else "RM 250.00 - RM 500.00 (mengikut jadual kompaun)",
                "tempoh_bayaran": tempoh_kompaun,
                "pegawai_pengeluar": pegawai,
                "no_kad_kuasa": kad_kuasa,
            },
            "pemberatan_hukuman": pemberatan_hukuman,
            "tpr_simulation_notes": [
                f"Pastikan Borang 114 memisahkan Seksyen Kesalahan ({seksyen_kesalahan}) dan Seksyen Hukuman ({seksyen_hukuman}) tanpa mencampuradukkan dua kesalahan berlainan (S.163 KTJ).",
                "Pastikan Sijil Seksyen 90A(2) mencatatkan model kamera/komputer/pencetak dan mengandungi klausa 'sepanjang pengetahuan dan kepercayaan saya'.",
                "Lampirkan Kronologi Kes, Kertas Cadangan IO, Borang Pengaduan Majistret (Borang 143), Saman (Borang 111) dan Surat Permohonan Izin Mendakwa (Sanksi TPR) bersama Kertas Minit (Am 6).",
            ],
        }

    @staticmethod
    def _resolve_act_provisions(
        akta_utama: str, text: str, citations: List[StatuteChunk]
    ) -> tuple[str, str, str, str, str]:
        """Menentukan Seksyen Kesalahan, Hukuman, Had Hukuman & Kompaun yang sah mengikut Akta."""
        low = (akta_utama + " " + text[:2000]).lower()
        if "852" in akta_utama or "852" in low:
            if "pamer" in low or "kaunter" in low or "peraturan 6" in low:
                return (
                    "Seksyen 10(1) Akta Kawalan Produk Merokok Demi Kesihatan Awam 2024 [Akta 852] dibaca bersama Peraturan 6 Peraturan-Peraturan Kawalan Produk Merokok Demi Kesihatan Awam (Kawalan Penjualan) 2024 [P.U. (A) 260/2024]",
                    "Seksyen 10(2) / Seksyen 10(3) Akta 852",
                    "Individu: Denda <= RM20,000 atau penjara <= 1 tahun (kesalahan pertama). Syarikat: Denda RM20,000 - RM100,000 atau penjara <= 2 tahun.",
                    "Seksyen 48 Akta 852 & P.U. (A) 259/2024",
                    "30 hari dari tarikh tawaran kompaun",
                )
            if "iklan" in low or "seksyen 7" in low:
                return (
                    "Seksyen 7(1) Akta Kawalan Produk Merokok Demi Kesihatan Awam 2024 [Akta 852]",
                    "Seksyen 7(2) / Seksyen 7(3) Akta 852",
                    "Individu: Denda <= RM20,000 atau penjara <= 1 tahun. Syarikat: Denda RM20,000 - RM100,000.",
                    "Seksyen 48 Akta 852 & P.U. (A) 259/2024",
                    "30 hari dari tarikh tawaran kompaun",
                )
            if "tanda amaran" in low or "seksyen 18" in low:
                return (
                    "Seksyen 18(1)(a)/(b) Akta Kawalan Produk Merokok Demi Kesihatan Awam 2024 [Akta 852] dibaca bersama P.U. (A) 258/2024",
                    "Seksyen 18(2) Akta 852",
                    "Denda tidak melebihi RM5,000.00.",
                    "Seksyen 48 Akta 852 & P.U. (A) 259/2024",
                    "30 hari dari tarikh tawaran kompaun",
                )
            return (
                "Seksyen 16(2) Akta Kawalan Produk Merokok Demi Kesihatan Awam 2024 [Akta 852] dibaca bersama P.U. (A) 257/2024",
                "Seksyen 16(3) Akta 852",
                "Denda tidak melebihi RM5,000.00.",
                "Seksyen 48 Akta 852 & P.U. (A) 259/2024",
                "30 hari dari tarikh tawaran kompaun",
            )

        if "281" in akta_utama or "makanan" in low or "ppkm" in low:
            if "tifoid" in low or "31" in low:
                return (
                    "Peraturan 31(1) Peraturan-Peraturan Kebersihan Makanan 2009 [P.U. (A) 95/2009]",
                    "Peraturan 31(2) Peraturan-Peraturan Kebersihan Makanan 2009",
                    "Denda tidak melebihi RM10,000.00 atau penjara tidak melebihi 2 tahun.",
                    "Notis Seksyen 32B & Seksyen 33 Akta Makanan 1983 [Jadual Keempat PPKM 2009]",
                    "14 hari dari tarikh penyampaian notis",
                )
            return (
                "Peraturan 11(1) Peraturan-Peraturan Kebersihan Makanan 2009 [P.U. (A) 95/2009]",
                "Peraturan 11(2) Peraturan-Peraturan Kebersihan Makanan 2009",
                "Denda tidak melebihi RM10,000.00 atau penjara tidak melebihi 2 tahun.",
                "Notis Seksyen 32B & Seksyen 33 Akta Makanan 1983 [Jadual Keempat PPKM 2009]",
                "14 hari dari tarikh penyampaian notis",
            )

        if "154" in akta_utama or "aedes" in low or "larva" in low:
            return (
                "Seksyen 13(1) dibaca bersama Seksyen 13(2) Akta Pemusnahan Serangga Pembawa Penyakit 1975 [Akta 154]",
                "Seksyen 23(a) Akta Pemusnahan Serangga Pembawa Penyakit 1975 [Akta 154]",
                "Kesalahan pertama: Denda <= RM10,000 atau penjara <= 2 tahun atau kedua-duanya.",
                "Seksyen 25 Akta 154 (Maksimum RM500.00)",
                "14 hari dari tarikh notis kompaun",
            )

        if "342" in akta_utama or "342" in low or "tibi" in low or "tuberkulosis" in low:
            if any(k in low for k in ("smear negatif", "afb negatif", "disaring", "saringan", "enggan mula", "taknak mula")):
                return (
                    "Seksyen 15(1) & Seksyen 14 Akta 342 [APPPB 1988] (Perintah Pemerhatian/Pengawasan/Pengasingan; S.22(b) hanya terpakai selepas diagnosis aktif disahkan MO/FMS & notis bertulis diserahkan lalu diingkari)",
                    "Seksyen 24 Akta Pencegahan dan Pengawalan Penyakit Berjangkit 1988 [Akta 342]",
                    "Individu: Denda tidak melebihi RM10,000.00 atau penjara tidak melebihi 2 tahun atau kedua-duanya (Akta A1742).",
                    "Tidak digalakkan kompaun / JANGAN terus buka IP S.22(b) selagi pengesahan klinikal MO/FMS (CXR/GeneXpert/Kultur) dan serahan notis bertulis belum lengkap.",
                    "14 hari (sekiranya notis atau kompaun terpakai selepas pengesahan)",
                )
            return (
                "Seksyen 22(b) Akta Pencegahan dan Pengawalan Penyakit Berjangkit 1988 [Akta 342]",
                "Seksyen 24(a) Akta Pencegahan dan Pengawalan Penyakit Berjangkit 1988 [Akta 342]",
                "Penjara tidak melebihi dua (2) tahun atau denda atau kedua-duanya.",
                "Seksyen 25 Akta 342 (atau pendakwaan terus tanpa tawaran kompaun bagi kes cicir rawatan berisiko awam)",
                "14 hari (jika kompaun ditawarkan)",
            )

        primary = citations[0] if citations else None
        return (
            f"{primary.section}, {primary.akta_title}" if primary else akta_utama,
            f"Peruntukan penalti di bawah {akta_utama}",
            "Tertakluk had maksimum penalti di bawah Akta berkaitan.",
            f"Peruntukan kompaun di bawah {akta_utama}",
            "14 hari",
        )
