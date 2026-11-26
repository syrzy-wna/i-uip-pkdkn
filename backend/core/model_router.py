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
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger("uip.model_router")

import httpx
import pymupdf as fitz
from pydantic import BaseModel

from backend.core.config import settings
from backend.core.malaysia_offices import (
    infer_state_from_text,
    normalize_malaysia_health_office,
)
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
        self._client_lock = threading.RLock()
        self._thread_state = threading.local()
        self._genai_client = None
        self._decision_client = None
        self._decision_cache: Dict[str, tuple[List[Dict[str, Any]], str]] = {}
        self.refresh_clients()

    @property
    def _last_ai_error(self) -> Optional[str]:
        return getattr(self._thread_state, "last_ai_error", None)

    @_last_ai_error.setter
    def _last_ai_error(self, val: Optional[str]) -> None:
        self._thread_state.last_ai_error = val

    def refresh_clients(self) -> None:
        """Membina semula klien Gemini & mengemas kini tetapan Ollama secara atomik dan selamat berbilang utas."""
        self.redactor.ollama_base_url = settings.ollama_base_url.rstrip("/")
        self.redactor.ollama_model = settings.ollama_model
        PrivacyRedactor.invalidate_ollama_cache()

        new_genai = None
        new_decision = None
        init_err: Optional[str] = None
        if GENAI_SDK_AVAILABLE and settings.has_gemini_key:
            try:
                new_genai = genai.Client(
                    api_key=settings.gemini_api_key,
                    http_options={
                        "api_version": "v1beta",
                        "timeout": 30_000,
                        "retry_options": {"attempts": 1},
                    },
                )
                new_decision = genai.Client(
                    api_key=settings.gemini_api_key,
                    http_options={
                        "api_version": "v1beta",
                        "timeout": 28_000,
                        "retry_options": {"attempts": 2},
                    },
                )
            except Exception as exc:
                init_err = "Konfigurasi klien AI tidak dapat dimulakan."
                logger.warning("Gagal membina klien Gemini (%s): %s", type(exc).__name__, str(exc)[:180])

        with self._client_lock:
            self._decision_cache.clear()
            self._genai_client = new_genai
            self._decision_client = new_decision
            self._last_ai_error = init_err

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
        """Menukar ralat teknikal kepada mesej Bahasa Melayu yang jelas untuk PPKP."""
        joined = " ".join(attempt_errors).lower()
        if any(tok in joined for tok in ("apitimeouterror", "timeoutexception", "timed out", "504", "deadline_exceeded")):
            return (
                "Pelayan AI mengambil masa terlalu lama untuk membalas. "
                "Jawapan dipaparkan mengikut Panduan Akta Rasmi — sila tekan 'Cuba Semula AI' sebentar lagi."
            )
        if any(tok in joined for tok in ("429", "ratelimit", "resource_exhausted", "quota")):
            return (
                "Perkhidmatan AI sedang sibuk buat sementara waktu. "
                "Jawapan dipaparkan mengikut Panduan Akta Rasmi — sila cuba semula dalam 1 minit."
            )
        if any(tok in joined for tok in ("401", "403", "api_key", "permissiondenied", "authentication")):
            return (
                "Tetapan semakan AI perlu disemak oleh pentadbir sistem. "
                "Buat masa ini, jawapan dipaparkan mengikut Panduan Akta Rasmi."
            )
        if any(tok in joined for tok in ("apiconnectionerror", "connecterror", "network", "dns")):
            return (
                "Sambungan ke perkhidmatan AI terganggu buat sementara waktu. "
                "Jawapan dipaparkan mengikut Panduan Akta Rasmi."
            )
        return (
            "Semakan mendalam AI tidak dapat dicapai buat sementara waktu. "
            "Jawapan dipaparkan mengikut Panduan Akta Rasmi — anda boleh cuba semula sebentar lagi."
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
        client = self._genai_client
        if not client or not model_name or "2.5" in model_name:
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
            interaction = client.interactions.create(**inter_kwargs)
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
        client = self._genai_client
        if client is None or genai_types is None or not model_name:
            return None
        try:
            cfg = self._build_generate_content_config(
                model_name=model_name,
                temperature=temperature,
                schema=schema,
                prefer_flash=prefer_flash,
                max_output_tokens=max_output_tokens,
            )
            resp = client.models.generate_content(
                model=model_name,
                contents=gc_contents,
                config=cfg,
            )
            text = (getattr(resp, "text", None) or "").strip()
            candidates = getattr(resp, "candidates", None) or []
            finish_reason = str(getattr(candidates[0], "finish_reason", "") or "").upper() if candidates else ""
            if text:
                try:
                    return self._parse_json_payload(text), f"{model_name} (Gemini API)"
                except ValueError:
                    if "MAX_TOKENS" in finish_reason and (max_output_tokens or 0) < 4096:
                        retry_cfg = self._build_generate_content_config(
                            model_name=model_name,
                            temperature=temperature,
                            schema=schema,
                            prefer_flash=prefer_flash,
                            max_output_tokens=4096,
                        )
                        resp2 = client.models.generate_content(
                            model=model_name,
                            contents=gc_contents,
                            config=retry_cfg,
                        )
                        text2 = (getattr(resp2, "text", None) or "").strip()
                        if text2:
                            return self._parse_json_payload(text2), f"{model_name} (Gemini API)"
                    raise
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
        """Menjana JSON berstruktur dengan laluan pantas (~15s) atau fallback berhad yang tahan ralat."""
        if not self._genai_client:
            self._last_ai_error = (
                "Tetapan semakan mendalam AI belum diaktifkan oleh pentadbir sistem. Buat masa ini, jawapan dipaparkan mengikut Panduan Akta Rasmi."
            )
            return None, "enjin-statutori-tempatan"

        self._last_ai_error = None
        attempt_errors: List[str] = []
        gc_contents = self._to_generate_content_parts(input_payload) if genai_types is not None else input_payload

        if prefer_fast_gc or prefer_flash:
            gc_list: List[str] = []
            if model_candidates:
                if prefer_flash:
                    # Utamakan model flash daripada senarai pemanggil dahulu, kemudian model lain
                    gc_list.extend(m for m in model_candidates if m and "flash" in m.lower())
                    gc_list.extend(m for m in model_candidates if m and "flash" not in m.lower())
                else:
                    gc_list.extend(m for m in model_candidates if m)
            if settings.standard_fallback_model:
                gc_list.append(settings.standard_fallback_model)
            if settings.multimodal_model:
                gc_list.append(settings.multimodal_model)
            gc_list.append("gemini-2.5-flash")

            gc_unique = list(dict.fromkeys(gc_list))
            for idx, m_name in enumerate(gc_unique[:3]):
                res = self._try_generate_content_json(
                    model_name=m_name,
                    gc_contents=gc_contents,
                    schema=schema,
                    temperature=temperature,
                    prefer_flash=prefer_flash or idx > 0,
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

            if "gemini-2.5-flash" not in gc_unique[:2]:
                res = self._try_generate_content_json(
                    model_name="gemini-2.5-flash",
                    gc_contents=gc_contents,
                    schema=schema,
                    temperature=temperature,
                    prefer_flash=True,
                    max_output_tokens=max_output_tokens,
                    attempt_errors=attempt_errors,
                )
                if res:
                    return res

            self._last_ai_error = self._classify_friendly_ai_error(attempt_errors)
            return None, "enjin-statutori-tempatan"

        attempts_left = 3
        ordered_candidates = [m for m in model_candidates if m and "2.5" not in m]
        if settings.standard_fallback_model and "2.5" not in settings.standard_fallback_model and settings.standard_fallback_model not in ordered_candidates:
            ordered_candidates.append(settings.standard_fallback_model)
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
                *model_candidates,
                settings.standard_fallback_model,
                "gemini-2.5-flash",
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
        decision_client = self._decision_client
        if not decision_client:
            return None, "Enjin Semakan Statutori KKM"

        cache_sig = hashlib.sha256(
            f"{settings.decision_model}|{redacted_text}|{len(criteria_list)}".encode("utf-8")
        ).hexdigest()
        with self._client_lock:
            if cache_sig in self._decision_cache:
                cached_items, cached_model = self._decision_cache[cache_sig]
                return [dict(item) for item in cached_items], f"{cached_model} [Cache]"

        if len(redacted_text) > 24000:
            doc_slice = f"{redacted_text[:13000]}\n\n[... bahagian tengah dipendekkan ...]\n\n{redacted_text[-11000:]}"
        else:
            doc_slice = redacted_text

        rag_brief = "\n\n".join(
            f"[{s.akta_code} - {s.section}]\n{s.text[:500]}" for s in statutory_context[:4]
        )
        decision_input = (
            "RUJUKAN AKTA SEBENAR:\n"
            f"{rag_brief}\n\n"
            "TEKS KERTAS SIASATAN (DATA PERIBADI TELAH DITUTUP DENGAN TOKEN [SUSPEK_1], [NO_KP_1], [PREMIS_1]):\n"
            f"{doc_slice}"
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
            result = decision_client.decisions.create(
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
                with self._client_lock:
                    if len(self._decision_cache) >= 64:
                        self._decision_cache.clear()
                    self._decision_cache[cache_sig] = ([dict(item) for item in formatted], f"{settings.decision_model} (Decisions API)")
                return formatted, f"{settings.decision_model} (Decisions API)"
        except Exception as exc:
            logger.warning("Decisions API fallback ke enjin tempatan (%s): %s", type(exc).__name__, str(exc)[:140])

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
        """Mengekstrak teks dan butiran fakta daripada fail PDF, Word (.docx), teks (.txt), atau gambar bukti."""
        warnings: List[str] = []
        extracted_local_text = ""
        low_fname = (filename or "").strip().lower()
        is_pdf = mime_type == "application/pdf" or low_fname.endswith(".pdf")
        is_docx = (
            low_fname.endswith(".docx")
            or mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        is_txt = low_fname.endswith((".txt", ".md")) or (mime_type or "").startswith("text/")
        is_image = (mime_type or "").startswith("image/") or low_fname.endswith(
            (".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".gif", ".bmp")
        )

        if is_docx or is_txt:
            from backend.services.ip_auditor import extract_text_from_upload

            try:
                extracted_local_text = extract_text_from_upload(file_bytes, filename or "dokumen.txt")
            except ValueError as exc:
                raise exc
            except Exception:
                raise ValueError("Fail dokumen tidak dapat dibaca atau rosak. Sila semak fail dan cuba semula.")
        elif is_pdf:
            try:
                with fitz.open(stream=file_bytes, filetype="pdf") as doc:
                    if getattr(doc, "is_encrypted", False) and not doc.authenticate(""):
                        raise ValueError("Fail PDF berkunci kata laluan. Sila buka kunci PDF terlebih dahulu.")
                    extracted_local_text = "\n".join(p.get_text("text") for p in doc).strip()
            except ValueError:
                raise
            except Exception:
                warnings.append("Fail PDF sukar dihuraikan secara tempatan; cubaan bacaan alternatif sedang dijalankan.")

        # Elak menghantar fail .docx/.txt sebagai `type: "image"` ke Gemini; bagi PDF yang sudah kaya teks tempatan, guna teks tempatan terus (lebih cepat & patuh PDPA!)
        should_call_vision = bool(
            self._genai_client
            and (is_image or (is_pdf and len(extracted_local_text) < 120))
        )
        if should_call_vision:
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
                raw = str(data.get("raw_text") or extracted_local_text or "")
                try:
                    conf = float(data.get("confidence") if data.get("confidence") is not None else 0.88)
                except (TypeError, ValueError):
                    conf = 0.88
                summary = (
                    f"Fail '{filename}' berjaya dibaca. "
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

        if not settings.has_gemini_key and is_image:
            warnings.append(
                "Fungsi bacaan teks daripada gambar tidak tersedia buat sementara. Sila taip atau salin butiran penting daripada gambar di ruangan bawah."
            )

        facts = self.extract_case_facts(extracted_local_text) if extracted_local_text else {}
        inferred_fields = self._parse_evidence_fields(
            filename=filename,
            doc_hint=doc_hint,
            text=extracted_local_text,
            facts=facts,
            size_bytes=len(file_bytes),
        )
        size_kb = max(1, round(len(file_bytes) / 1024))
        raw_text = extracted_local_text or (
            f"[FAIL BUKTI DIMUAT NAIK: {filename} | Saiz: {size_kb} KB]\n"
            f"Jenis Dokumen: {inferred_fields['jenis_dokumen']}\n"
            f"Cadangan Seksyen: {inferred_fields['cadangan_akta_seksyen']}\n"
            f"Catatan: {inferred_fields['butiran_kesalahan_atau_eksibit']}"
        )
        doc_hint_labels = {
            "kertas_siasatan_pdf": "Kertas Siasatan",
            "sijil_ssm": "Sijil SSM",
            "bukti_kesalahan": "Dokumen Bukti",
            "gambar_premis": "Foto Premis",
        }
        hint_label = doc_hint_labels.get((doc_hint or "").lower(), "Dokumen Kes")
        doc_kind_label = "Word (.docx)" if is_docx else ("teks (.txt)" if is_txt else "PDF")
        summary = (
            f"Fail '{filename}' ({hint_label}) berjaya dibaca oleh sistem. "
            + (
                f"Berjaya membaca {len(extracted_local_text)} aksara teks daripada dokumen {doc_kind_label}."
                if extracted_local_text
                else "Gambar telah dilampirkan. Jika teks pada gambar tidak terbaca automatik, sila taip butiran ringkas di ruangan catatan kes."
            )
        )
        local_engine_name = (
            "Pembaca Dokumen Word (.docx) Sistem"
            if is_docx and extracted_local_text
            else ("Pembaca Fail Teks Sistem" if is_txt and extracted_local_text else ("Pembaca Dokumen PDF Sistem" if extracted_local_text else "Pembaca Maklumat Fail"))
        )
        return EvidenceExtractionResult(
            extracted_fields=inferred_fields,
            structured_summary=summary,
            raw_text=raw_text,
            confidence=0.90 if extracted_local_text else 0.72,
            model_used=local_engine_name,
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
            akta_sugg = "Pengesahan Pemilik / Pengarah Syarikat (S.49 Akta 852 / S.33A Akta 281 / S.22(2) Akta 154)"
            butiran = facts.get("kesalahan") or "Dokumen pendaftaran perniagaan/syarikat untuk pengesahan entiti OKT."
        elif "sitaan" in low or "bongkar" in low:
            doc_type = "Borang Senarai Benda Disita (Seksyen 36 Akta 852 / Seksyen 4 Akta 281)"
            akta_sugg = "Seksyen 35 & 36 Akta 852 / Seksyen 4 Akta Makanan 1983"
            butiran = facts.get("kesalahan") or "Senarai barang kes dirampas berserta kuantiti dan akuan terima."
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
        """Menghurai fakta sebenar daripada teks/PDF Kertas Siasatan tanpa nilai negeri palsu hardcoded."""

        def _find(patterns: List[str], default: str = "") -> str:
            for pat in patterns:
                m = re.search(pat, text, flags=re.I | re.M)
                if m:
                    val = m.group(1).strip()
                    if val:
                        return val
            return default

        no_ip = _find([r"(?:no\.?\s*ip|no\.?\s*kertas\s+siasatan)\s*[:\-]\s*([^\n\r]+)"])
        daerah_raw = _find([
            r"(?:daerah|pejabat\s+kesihatan\s+(?:daerah|kawasan|bahagian)|pejabat\s+kesihatan)\s*[:\-]\s*([^\n\r]+)"
        ])
        daerah = daerah_raw.split(",")[0].strip() if daerah_raw else ""
        alamat = _find([r"(?:alamat\s+kejadian|tempat\s+kejadian|alamat\s+premis)\s*[:\-]\s*([^\n\r]+)"])
        negeri = daerah_raw.split(",")[1].strip() if "," in daerah_raw else infer_state_from_text(alamat)

        tarikh = _find([r"tarikh\s+(?:kejadian|pemeriksaan|operasi)\s*[:\-]\s*([^\n\r(]+)"])
        masa = _find([r"masa\s+(?:kejadian|pemeriksaan|operasi)\s*[:\-]\s*([^\n\r]+)"])
        nama_premis = _find([r"(?:nama\s+premis(?:\s+makanan)?|nama\s+syarikat)\s*[:\-]\s*([^\n\r]+)"])
        no_ssm = _find([r"no\.?\s*ssm\s*[:\-]\s*([^\n\r]+)"])
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

        seal_m = re.search(r"(?:seal|lak(?:\s+rasmi)?(?:\s+kkm)?(?:\s+siri)?)\s*(?:#|no\.?\s*)?([A-Za-z0-9\-#]+)", text, flags=re.I)
        no_seal = seal_m.group(1).strip() if seal_m else "Belum direkodkan"

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
        """Menjana pakej dokumen IP lengkap dengan format rasmi Mahkamah Majistret & KKM seluruh Malaysia."""
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
        prof = officer_profile or {}

        if self._genai_client and not fast_mode:
            rag_verbatim = "\n\n".join(
                f"[{c.akta_title} | {c.section}]\n{c.text}" for c in citations
            )
            office_ctx = normalize_malaysia_health_office(
                district_pkd=str(prof.get("district_pkd") or ""),
                state_jkn=str(prof.get("state_jkn") or ""),
            )
            office_hint_lines = "\n".join(
                ln for ln in (
                    f"- Pejabat Kesihatan Pegawai: {office_ctx['pejabat_rasmi']}" if prof.get("district_pkd") else "",
                    f"- Negeri / JKN: {office_ctx['negeri']}" if office_ctx["negeri"] else "",
                    f"- Mahkamah Majistret Bidang Kuasa: {prof.get('default_magistrate_court')}" if prof.get("default_magistrate_court") else "",
                )
                if ln
            )
            prompt = (
                "Anda ialah Pegawai Pendakwa Kanan UIP KKM.\n"
                "Gubal Kertas Siasatan lengkap dalam Bahasa Melayu rasmi undang-undang Malaysia yang ringkas dan tepat.\n"
                "PENTING:\n"
                "1) Kekalkan semua token penyamaran [SUSPEK_1], [NO_KP_1], [PREMIS_1], [NO_SSM_1] tanpa mengubahnya.\n"
                "2) Petik HANYA nombor Seksyen & Peraturan yang wujud dalam RUJUKAN AKTA SEBENAR di bawah.\n"
                "3) Borang 114 wajib memisahkan Seksyen Kesalahan daripada Seksyen Hukuman.\n"
                "4) Sijil Seksyen 90A(2) & (3)(a) wajib mengandungi butiran perkakasan dan klausa 'sepanjang pengetahuan dan kepercayaan saya'.\n"
                + (f"\nKONTEKS PEJABAT PEGAWAI (BUKAN PII):\n{office_hint_lines}\n" if office_hint_lines else "")
                + f"\nRUJUKAN AKTA SEBENAR:\n{rag_verbatim}\n\n"
                + f"MAKLUMAT KES (DATA SULIT DITUTUP):\n{redaction.redacted_text[:9000]}"
            )
            ai_json, used = self._call_gemini_structured_json(
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
            if isinstance(ai_json, dict) and isinstance(ai_json.get("borang_114"), dict):
                # Sahkan SEMUA artifak draf AI (Borang 114, Saman 111, Izin Mendakwa, Notis Kompaun, Fakta Kes, Kertas Cadangan IO) terhadap Pustaka Akta Verbatim AGC
                from backend.rag.legal_engine import get_legal_library, validate_legal_output

                val_draft = validate_legal_output(
                    {**ai_json, "akta_disyorkan": akta_utama},
                    get_legal_library().to_snapshot_dict(),
                    question_context=redaction.redacted_text[:800],
                )
                if val_draft.get("passed", True):
                    generated_json = ai_json
                    reasoning_model_used = used
                else:
                    logger.warning(
                        "Draf AI gagal semakan Pustaka Akta (%s) — jatuh semula ke templat fakta tempatan.",
                        val_draft.get("warning_banner"),
                    )

        if not generated_json:
            generated_json = self._build_structured_draft_from_facts(
                redacted_text=redaction.redacted_text,
                akta_utama=akta_utama,
                citations=citations,
                officer_profile=officer_profile,
            )

        fakta_kes_redacted, style_engine = self._polish_formal_malay_offline(
            str(generated_json.get("fakta_kes") or "")
        )
        generated_json["fakta_kes"] = fakta_kes_redacted

        rehydrated = self._rehydrate_nested(generated_json, redaction.token_map)
        if not isinstance(rehydrated, dict):
            rehydrated = {}

        # Pastikan semua sub-objek adalah dict/list sah dan selaraskan profil pegawai seluruh Malaysia
        for dict_key in ("borang_114", "borang_143", "saman_111", "izin_mendakwa", "sijil_90a", "notis_kompaun"):
            if not isinstance(rehydrated.get(dict_key), dict):
                rehydrated[dict_key] = {}
        for list_key in ("minit_ip", "kronologi_kes", "diari_siasatan", "senarai_saksi", "senarai_eksibit", "pemberatan_hukuman", "tpr_simulation_notes"):
            if not isinstance(rehydrated.get(list_key), list):
                rehydrated[list_key] = []

        if officer_profile:
            office_p = normalize_malaysia_health_office(
                district_pkd=str(prof.get("district_pkd") or ""),
                state_jkn=str(prof.get("state_jkn") or ""),
            )
            s90 = rehydrated["sijil_90a"]
            if not s90.get("nama_pegawai") or "[" in str(s90.get("nama_pegawai", "")):
                s90["nama_pegawai"] = prof.get("full_name") or s90.get("nama_pegawai", "")
            if prof.get("designation"):
                s90["jawatan"] = f"{prof.get('designation')} ({prof.get('grade', '')})".strip()
            if prof.get("district_pkd") and (not s90.get("pejabat_pkd") or "[" in str(s90.get("pejabat_pkd", ""))):
                s90["pejabat_pkd"] = office_p["pejabat_rasmi"]
            if prof.get("default_camera_desc"):
                s90["peranti_kamera"] = prof["default_camera_desc"]
            if prof.get("default_computer_desc"):
                s90["perihal_komputer"] = prof["default_computer_desc"]
            if prof.get("default_printer_desc"):
                s90["perihal_pencetak"] = prof["default_printer_desc"]

            b114 = rehydrated["borang_114"]
            b143 = rehydrated["borang_143"]
            sam111 = rehydrated["saman_111"]
            komp = rehydrated["notis_kompaun"]
            if prof.get("district_pkd") and not b114.get("pejabat_pkd"):
                b114["pejabat_pkd"] = office_p["pejabat_rasmi"]
            if prof.get("full_name") and (not b114.get("pegawai_pengadu") or "[" in str(b114.get("pegawai_pengadu", ""))):
                b114["pegawai_pengadu"] = prof["full_name"]
            if prof.get("default_magistrate_court"):
                court_pref = str(prof["default_magistrate_court"]).strip()
                if not b114.get("mahkamah") or "[" in str(b114.get("mahkamah", "")):
                    b114["mahkamah"] = court_pref
                if not b143.get("mahkamah") or "[" in str(b143.get("mahkamah", "")):
                    b143["mahkamah"] = court_pref
                if not sam111.get("mahkamah") or "[" in str(sam111.get("mahkamah", "")):
                    sam111["mahkamah"] = court_pref
            if prof.get("full_name") and (not komp.get("pegawai_pengeluar") or "[" in str(komp.get("pegawai_pengeluar", ""))):
                komp["pegawai_pengeluar"] = prof["full_name"]
            if prof.get("kkm_authority_card_no") and (not komp.get("no_kad_kuasa") or "[" in str(komp.get("no_kad_kuasa", ""))):
                komp["no_kad_kuasa"] = prof["kkm_authority_card_no"]
            if prof.get("district_pkd") and not komp.get("pejabat_pkd"):
                komp["pejabat_pkd"] = office_p["pejabat_rasmi"]
            if prof.get("state_jkn") and not komp.get("state_jkn"):
                komp["state_jkn"] = str(prof["state_jkn"])

        return DraftGenerationResult(
            workflow=workflow,
            akta_utama=akta_utama,
            minit_ip=rehydrated["minit_ip"],
            kronologi_kes=rehydrated["kronologi_kes"],
            kertas_cadangan_io=str(rehydrated.get("kertas_cadangan_io") or ""),
            saman_111=rehydrated["saman_111"],
            borang_143=rehydrated["borang_143"],
            izin_mendakwa=rehydrated["izin_mendakwa"],
            borang_114=rehydrated["borang_114"],
            diari_siasatan=rehydrated["diari_siasatan"],
            fakta_kes=str(rehydrated.get("fakta_kes") or ""),
            rakaman_112=str(rehydrated.get("rakaman_112") or ""),
            senarai_saksi=rehydrated["senarai_saksi"],
            senarai_eksibit=rehydrated["senarai_eksibit"],
            sijil_90a=rehydrated["sijil_90a"],
            notis_kompaun=rehydrated["notis_kompaun"],
            pemberatan_hukuman=rehydrated["pemberatan_hukuman"],
            tpr_simulation_notes=rehydrated["tpr_simulation_notes"],
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
        """Membina draf rasmi Kertas Siasatan hanya daripada fakta sebenar teks/PDF dan profil pejabat seluruh Malaysia."""
        facts = self.extract_case_facts(redacted_text)
        prof = officer_profile or {}
        current_year = datetime.now().year

        office = normalize_malaysia_health_office(
            district_pkd=str(prof.get("district_pkd") or ""),
            state_jkn=str(prof.get("state_jkn") or ""),
            daerah_override=facts["daerah"],
            negeri_override=facts["negeri"],
        )

        no_ip = facts["no_ip"] or f"PKD/UIP/{current_year}/[Sila isi No. Siri]"
        daerah = office["daerah"] or "[Daerah / Kawasan / Bahagian]"
        negeri = office["negeri"] or "[Negeri]"
        pejabat_rasmi = office["pejabat_rasmi"]
        negeri_mahkamah = office["negeri_mahkamah"]

        # Hormati Mahkamah Majistret lalai pegawai sekiranya kes dalam daerah pegawai sendiri atau daerah tidak dinyatakan
        prof_daerah = normalize_malaysia_health_office(district_pkd=str(prof.get("district_pkd") or ""))["daerah"]
        use_prof_court = bool(
            prof.get("default_magistrate_court")
            and (not facts["daerah"] or facts["daerah"].lower() == prof_daerah.lower())
        )
        mahkamah_rasmi = (
            str(prof["default_magistrate_court"]).strip()
            if use_prof_court
            else f"DALAM MAHKAMAH MAJISTRET DI {daerah.upper()}"
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

        seksyen_kesalahan, seksyen_hukuman, hukuman_max, peruntukan_kompaun, tempoh_kompaun, amaun_default = (
            self._resolve_act_provisions(
                akta_utama=akta_utama,
                text=redacted_text,
                citations=citations,
            )
        )

        # Pemetaan mandatori Izin Mendakwa (Keizinan Bertulis Pendakwa Raya) bagi kesemua 4 Akta KKM
        low_act = f"{akta_utama} {seksyen_kesalahan}".lower()
        if "852" in low_act:
            act_consent = "Seksyen 41 Akta 852"
        elif "281" in low_act or "makanan" in low_act or "ppkm" in low_act or "ppm" in low_act:
            act_consent = "Seksyen 32A Akta Makanan 1983 [Akta 281]"
        elif "154" in low_act:
            act_consent = "Seksyen 22A Akta Pemusnahan Serangga Pembawa Penyakit 1975 [Akta 154]"
        elif "342" in low_act:
            act_consent = "Seksyen 23 Akta Pencegahan dan Pengawalan Penyakit Berjangkit 1988 [Akta 342]"
        else:
            act_consent = ""
        peruntukan_izin = (
            "Perkara 145(3) Perlembagaan Persekutuan, Seksyen 376(3) Kanun Tatacara Jenayah"
            + (f" & {act_consent}" if act_consent else "")
            + " (serta Seksyen 377(b) KTJ bagi kuasa menjalankan pendakwaan)"
        )

        tempat_penuh = f"{prem_token}, {alamat}" if prem_token not in alamat else alamat
        negeri_phrase = (
            f"di {negeri}" if "wilayah persekutuan" in negeri.lower() else f"di dalam Negeri {negeri}"
        )
        pertuduhan_text = (
            f"Bahawa kamu, pada {tarikh}, jam lebih kurang {masa}, bertempat di {tempat_penuh}, "
            f"di dalam Daerah/Kawasan {daerah}, {negeri_phrase}, telah didapati {kesalahan_ringkas}; "
            f"dan oleh yang demikian kamu telah melakukan suatu kesalahan di bawah {seksyen_kesalahan}, "
            f"yang boleh dihukum di bawah {seksyen_hukuman}."
        )

        minit_ip = [
            {
                "bil": "Minit 1",
                "tarikh": tarikh,
                "daripada": "Ketua UIP Daerah / Kawasan / Bahagian",
                "kepada": pegawai,
                "kandungan": f"Kesalahan di bawah {seksyen_kesalahan} dilaporkan. Sila buka Kertas Siasatan No. {no_ip} dan lengkapkan siasatan mengikut senarai semak UIP.",
            },
            {
                "bil": "Minit 2",
                "tarikh": facts["s112_when"] or tarikh,
                "daripada": pegawai,
                "kepada": "Ketua UIP / Pegawai Pendakwa",
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
                    f"Kes memenuhi elemen kesalahan di bawah {seksyen_kesalahan}. Dipohon pertimbangan dan Izin Mendakwa (Keizinan Bertulis Pendakwa Raya) daripada pihak TPR."
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
            f"{pejabat_rasmi} telah menjalankan pemeriksaan penguatkuasaan di {tempat_penuh}.\n"
            f"2. Pemeriksaan dijalankan di hadapan {suspect_token} (No. K/P: {ic_token}) setelah kad kuasa rasmi ditunjukkan.\n"
            f"3. Hasil pemeriksaan mendapati {kesalahan_ringkas}.\n"
            f"4. Pegawai penguat kuasa telah mengambil gambar bukti di tempat kejadian, menyediakan borang pemeriksaan/sitaan yang berkaitan "
            f"(No. Lak Eksibit: {no_seal}) serta menyerahkan satu salinan kepada pihak premis.\n"
            f"5. Siasatan lanjut di bawah {seksyen_kesalahan} telah dilengkapkan termasuk rakaman percakapan di bawah Seksyen 112 KTJ, "
            f"carian rasmi SSM ({ssm_token}), dan Sijil Seksyen 90A(2) & (3)(a) Akta Keterangan 1950 untuk tujuan pendakwaan."
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
                "butiran_tindakan": "Sijil Seksyen 90A(2) & (3)(a) Akta Keterangan 1950 bagi gambar digital dan cetakan SSM disiapkan. Draf Borang 114, Borang 143, Fakta Kes dan Minit IP disusun untuk semakan UIP/TPR.",
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
            f"Pejabat: {pejabat_rasmi}, {negeri}\n\n"
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

        tpr_kepada = (
            f"Timbalan Pendakwa Raya, {negeri}"
            if "wilayah persekutuan" in negeri.lower()
            else f"Timbalan Pendakwa Raya, Negeri {negeri}"
        )

        return {
            "minit_ip": minit_ip,
            "kronologi_kes": kronologi_kes,
            "kertas_cadangan_io": kertas_cadangan_io,
            "saman_111": {
                "mahkamah": mahkamah_rasmi,
                "no_saman": no_ip,
                "nama_oks": suspect_token,
                "no_kp": ic_token,
                "alamat": alamat,
                "tarikh_hadir": f"........ haribulan ...................... {current_year}",
                "masa_hadir": "8.30 pagi",
                "teks_pertuduhan": pertuduhan_text,
                "hukuman": hukuman_max,
            },
            "borang_143": {
                "mahkamah": mahkamah_rasmi,
                "negeri": negeri.upper(),
                "pengadu": f"{pegawai} (Pegawai Diberi Kuasa KKM)",
                "oks_nama": suspect_token,
                "oks_kp": ic_token,
                "oks_alamat": alamat,
                "butiran_aduan": pertuduhan_text,
            },
            "izin_mendakwa": {
                "rujukan_ip": no_ip,
                "kepada": tpr_kepada,
                "peruntukan_izin": peruntukan_izin,
                "nama_okt": f"{suspect_token} (No. K/P: {ic_token})",
                "seksyen_dipohon": f"{seksyen_kesalahan} dibaca bersama {seksyen_hukuman}",
            },
            "borang_114": {
                "mahkamah": mahkamah_rasmi,
                "negeri": negeri_mahkamah,
                "pejabat_pkd": pejabat_rasmi,
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
                    "alamat_hubungan": pejabat_rasmi,
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
                    "alamat_hubungan": "Makmal Kesihatan Awam / Pejabat Kesihatan",
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
                    "lokasi_simpanan": f"Stor Eksibit Berkunci {pejabat_rasmi}",
                },
            ],
            "sijil_90a": {
                "nama_pegawai": pegawai,
                "jawatan": str(prof.get("designation") or "Penolong Pegawai Kesihatan Persekitaran (PPKP)"),
                "pejabat_pkd": pejabat_rasmi,
                "peranti_kamera": str(prof.get("default_camera_desc") or "Kamera Digital Rasmi Penguatkuasaan KKM"),
                "perihal_komputer": str(prof.get("default_computer_desc") or "Komputer Meja Rasmi Pejabat KKM (beroperasi dalam keadaan baik)"),
                "perihal_pencetak": str(prof.get("default_printer_desc") or "Pencetak Laser Warna Pejabat KKM"),
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
                "amaun_kompaun_rm": amaun_default,
                "tempoh_bayaran": tempoh_kompaun,
                "pegawai_pengeluar": pegawai,
                "no_kad_kuasa": kad_kuasa,
                "pejabat_pkd": pejabat_rasmi,
                "state_jkn": str(prof.get("state_jkn") or negeri),
            },
            "pemberatan_hukuman": pemberatan_hukuman,
            "tpr_simulation_notes": [
                f"Pastikan Borang 114 memisahkan Seksyen Kesalahan ({seksyen_kesalahan}) dan Seksyen Hukuman ({seksyen_hukuman}) tanpa mencampuradukkan dua kesalahan berlainan (S.163 KTJ).",
                "Pastikan Sijil Seksyen 90A(2) & (3)(a) mencatatkan model kamera/komputer/pencetak serta KEW.PA dan mengandungi klausa 'sepanjang pengetahuan dan kepercayaan saya'.",
                f"Lampirkan Kronologi Kes, Kertas Cadangan IO, Borang Pengaduan Majistret (Borang 143), Saman (Borang 111) dan Surat Permohonan Izin Mendakwa ({peruntukan_izin}) bersama Kertas Minit (Am 6).",
            ],
        }

    @staticmethod
    def _resolve_act_provisions(
        akta_utama: str, text: str, citations: List[StatuteChunk]
    ) -> tuple[str, str, str, str, str, str]:
        """Menentukan Seksyen Kesalahan, Hukuman, Had Hukuman, Status Kompaun, Tempoh & Amaun lalai yang sah mengikut Akta."""
        low = (akta_utama + " " + text[:3000]).lower()
        akta_low = (akta_utama or "").lower()

        def _has_pat(pat: str) -> bool:
            return bool(re.search(pat, low, flags=re.I))

        # --- AKTA 852 (Produk Merokok 2024) ---
        if "852" in akta_low or ("852" in low and not any(a in akta_low for a in ("281", "154", "342"))):
            if _has_pat(r"(?<!\w)(?:seksyen\s+3\(1\)|s\.?\s*3\(1\)|seksyen\s+3\b|tidak\s+berdaftar|tanpa\s+pendaftaran|262/2024|mengimport\s+produk\s+merokok|mengilang\s+produk\s+merokok)(?!\w)"):
                return (
                    "Seksyen 3(1) Akta Kawalan Produk Merokok Demi Kesihatan Awam 2024 [Akta 852] dibaca bersama Peraturan-Peraturan Kawalan Produk Merokok Demi Kesihatan Awam (Pendaftaran Produk Tembakau, Bahan Merokok atau Produk Pengganti Tembakau) 2024 [P.U. (A) 262/2024]",
                    "Seksyen 3(2)(a) [Individu] atau Seksyen 3(2)(b) [Pertubuhan Perbadanan] Akta 852",
                    "Individu: Denda tidak melebihi RM20,000 atau penjara tidak melebihi 1 tahun (kesalahan pertama). Syarikat: Denda RM20,000 – RM100,000 atau penjara tidak melebihi 2 tahun.",
                    "TIDAK BOLEH DIKOMPAUN (tiada dalam Jadual Pertama P.U. (A) 259/2024) — Wajib Sita (S.35/S.36) & Buka IP Terus",
                    "Tiada tawaran kompaun (Buka IP Terus)",
                    "Tidak Berkenaan (Buka IP Terus)",
                )
            if _has_pat(r"(?<!\w)(?:seksyen\s+13\(1\)|s\.?\s*13\(1\)|jual(?:an)?\s+(?:rokok|vape|produk\s+merokok)\s+kepada\s+(?:obd|pelajar|kanak-kanak|bawah\s+umur|bawah\s+18)|menjual\s+.*\b(?:obd|pelajar|bawah\s+18|bawah\s+umur))(?!\w)"):
                return (
                    "Seksyen 13(1) Akta Kawalan Produk Merokok Demi Kesihatan Awam 2024 [Akta 852]",
                    "Seksyen 13(2)(a) [Individu] atau Seksyen 13(2)(b) [Pertubuhan Perbadanan] Akta 852",
                    "Individu: Denda tidak melebihi RM20,000 atau penjara tidak melebihi 1 tahun (kesalahan pertama). Syarikat: Denda RM20,000 – RM100,000 atau penjara tidak melebihi 2 tahun.",
                    "TIDAK BOLEH DIKOMPAUN (tiada dalam Jadual Pertama P.U. (A) 259/2024) — Wajib Sita (S.35/S.36) & Buka IP Terus",
                    "Tiada tawaran kompaun (Buka IP Terus)",
                    "Tidak Berkenaan (Buka IP Terus)",
                )
            if _has_pat(r"(?<!\w)(?:seksyen\s+13\(3\)|s\.?\s*13\(3\)|(?:obd|pelajar|bawah\s+18|bawah\s+umur)\s+membeli\s+(?:rokok|vape|produk\s+merokok))(?!\w)"):
                return (
                    "Seksyen 13(3) Akta Kawalan Produk Merokok Demi Kesihatan Awam 2024 [Akta 852]",
                    "Seksyen 13(4) Akta 852",
                    "Denda tidak melebihi RM500.00 atau perintah khidmat masyarakat (patuhi Akta Kanak-Kanak 2001 [Akta 611]).",
                    "Seksyen 48(2) Akta 852 & Jadual Pertama(a) P.U. (A) 259/2024 (had kompaun maks RM250.00)",
                    "30 hari dari tarikh tawaran kompaun",
                    "RM 50.00",
                )
            if _has_pat(r"(?<!\w)(?:seksyen\s+17\(1\)|s\.?\s*17\(1\)|(?:obd|pelajar|murid|budak\s+sekolah|bawah\s+18|bawah\s+umur).{0,50}(?:merokok|hisap|menghisap|menggunakan|vape|rokok))(?!\w)"):
                return (
                    "Seksyen 17(1) Akta Kawalan Produk Merokok Demi Kesihatan Awam 2024 [Akta 852]",
                    "Seksyen 17(2) Akta 852",
                    "Denda tidak melebihi RM500.00 atau perintah khidmat masyarakat (patuhi Akta Kanak-Kanak 2001 [Akta 611]).",
                    "Seksyen 48(2) Akta 852 & Jadual Pertama(c) P.U. (A) 259/2024 (had kompaun maks RM250.00)",
                    "30 hari dari tarikh tawaran kompaun",
                    "RM 50.00",
                )
            if _has_pat(r"(?<!\w)(?:seksyen\s+10\(1\)|s\.?\s*10\(1\)|pamer|mempamer(?:kan)?\s+(?:rokok|vape|produk)|kaunter\s+terbuka|peraturan\s+6|260/2024|jualan\s+dalam\s+talian|jual\s+online|tiktok|shopee|vending|mesin\s+layan\s+diri)(?!\w)"):
                return (
                    "Seksyen 10(1) Akta Kawalan Produk Merokok Demi Kesihatan Awam 2024 [Akta 852] dibaca bersama Peraturan-Peraturan Kawalan Produk Merokok Demi Kesihatan Awam (Kawalan Penjualan) 2024 [P.U. (A) 260/2024]",
                    "Seksyen 10(2)(a) [Bukan Pertubuhan Perbadanan] atau Seksyen 10(2)(b) [Pertubuhan Perbadanan] Akta 852",
                    "Individu: Denda tidak melebihi RM20,000 atau penjara tidak melebihi 1 tahun (kesalahan pertama). Syarikat: Denda RM20,000 – RM100,000 atau penjara tidak melebihi 2 tahun.",
                    "TIDAK BOLEH DIKOMPAUN (tiada dalam Jadual Pertama P.U. (A) 259/2024) — Wajib Sita (S.35/S.36) & Buka IP Terus",
                    "Tiada tawaran kompaun (Buka IP Terus)",
                    "Tidak Berkenaan (Buka IP Terus)",
                )
            if _has_pat(r"(?<!\w)(?:iklan|mengiklankan|promosi|tajaan|seksyen\s+7\(1\)|s\.?\s*7\(1\)|seksyen\s+7\b)(?!\w)"):
                return (
                    "Seksyen 7(1) Akta Kawalan Produk Merokok Demi Kesihatan Awam 2024 [Akta 852]",
                    "Seksyen 7(2)(a) [Bukan Pertubuhan Perbadanan] atau Seksyen 7(2)(b) [Pertubuhan Perbadanan] Akta 852",
                    "Individu: Denda tidak melebihi RM20,000 atau penjara tidak melebihi 1 tahun. Syarikat: Denda RM20,000 – RM100,000 atau penjara tidak melebihi 2 tahun.",
                    "TIDAK BOLEH DIKOMPAUN (tiada dalam Jadual Pertama P.U. (A) 259/2024) — Wajib Buka IP Terus",
                    "Tiada tawaran kompaun (Buka IP Terus)",
                    "Tidak Berkenaan (Buka IP Terus)",
                )
            if _has_pat(r"(?<!\w)(?:seksyen\s+15\(1\)|s\.?\s*15\(1\)|pembungkusan|amaran\s+kesihatan\s+bergambar|261/2024)(?!\w)"):
                return (
                    "Seksyen 15(1) Akta Kawalan Produk Merokok Demi Kesihatan Awam 2024 [Akta 852] dibaca bersama Peraturan-Peraturan Kawalan Produk Merokok Demi Kesihatan Awam (Pembungkusan dan Pelabelan) 2024 [P.U. (A) 261/2024]",
                    "Seksyen 15(2)(a) [Individu] atau Seksyen 15(2)(b) [Pertubuhan Perbadanan] Akta 852",
                    "Individu: Denda tidak melebihi RM20,000 atau penjara tidak melebihi 1 tahun. Syarikat: Denda RM20,000 – RM100,000 atau penjara tidak melebihi 2 tahun.",
                    "TIDAK BOLEH DIKOMPAUN (tiada dalam Jadual Pertama P.U. (A) 259/2024) — Wajib Sita (S.35/S.36) & Buka IP Terus",
                    "Tiada tawaran kompaun (Buka IP Terus)",
                    "Tidak Berkenaan (Buka IP Terus)",
                )
            if _has_pat(r"(?<!\w)(?:tanda\s+amaran|tanda\s+larangan|papan\s+tanda|bekas\s+abu|ashtray|258/2024|seksyen\s+18|s\.?\s*18\(1\))(?!\w)"):
                return (
                    "Seksyen 18(1)(a) Akta Kawalan Produk Merokok Demi Kesihatan Awam 2024 [Akta 852] dibaca bersama Peraturan 2(1) & 2(2) P.U. (A) 258/2024",
                    "Seksyen 18(2) Akta 852",
                    "Denda tidak melebihi RM5,000.00.",
                    "Seksyen 48(2) Akta 852 & Jadual Pertama(d) P.U. (A) 259/2024",
                    "30 hari dari tarikh tawaran kompaun",
                    "RM 250.00",
                )
            return (
                "Seksyen 16(2) Akta Kawalan Produk Merokok Demi Kesihatan Awam 2024 [Akta 852] dibaca bersama P.U. (A) 257/2024",
                "Seksyen 16(3) Akta 852",
                "Denda tidak melebihi RM5,000.00.",
                "Seksyen 48(2) Akta 852 & Jadual Pertama(b) P.U. (A) 259/2024",
                "30 hari dari tarikh tawaran kompaun",
                "RM 250.00",
            )

        # --- AKTA 281 (Akta Makanan 1983 / PPKM 2009 / PPM 1985) ---
        if "281" in akta_low or ("makanan" in low and not any(a in akta_low for a in ("852", "154", "342"))) or "ppkm" in low or "ppm 1985" in low:
            if _has_pat(r"(?<!\w)(?:seksyen\s+13a\(2\)|s\.?\s*13a\(2\)|seksyen\s+13a|bangkai\s+lipas|jirim\s+asing|benda\s+asing|busuk|reput|tidak\s+layak\s+dimakan)(?!\w)"):
                return (
                    "Seksyen 13A(2) Akta Makanan 1983 [Akta 281]",
                    "Seksyen 13A(2) Akta Makanan 1983 [Akta 281]",
                    "Denda tidak melebihi RM30,000.00 atau penjara tidak melebihi 5 tahun atau kedua-duanya (Perbicaraan di Mahkamah Sesyen mengikut S.63/64 Akta 92).",
                    "TIDAK BOLEH DIKOMPAUN — Wajib Buka IP Terus ke Mahkamah Sesyen",
                    "Tiada tawaran kompaun (Buka IP Terus)",
                    "Tidak Berkenaan (Buka IP Terus)",
                )
            if _has_pat(r"(?<!\w)(?:seksyen\s+13\(1\)|s\.?\s*13\(1\)|memudaratkan\s+kesihatan|bahan\s+beracun|keracunan\s+makanan\s+seksyen\s+13)(?!\w)"):
                return (
                    "Seksyen 13(1) Akta Makanan 1983 [Akta 281]",
                    "Seksyen 13(1) Akta Makanan 1983 [Akta 281]",
                    "Denda tidak melebihi RM100,000.00 atau penjara tidak melebihi 10 tahun atau kedua-duanya (Perbicaraan di Mahkamah Sesyen mengikut S.63/64 Akta 92).",
                    "TIDAK BOLEH DIKOMPAUN — Wajib Buka IP Terus ke Mahkamah Sesyen",
                    "Tiada tawaran kompaun (Buka IP Terus)",
                    "Tidak Berkenaan (Buka IP Terus)",
                )
            if _has_pat(r"(?<!\w)(?:seksyen\s+13b|s\.?\s*13b|diaduk|adulterated|bahan\s+tambah\s+dilarang)(?!\w)"):
                return (
                    "Seksyen 13B(1) Akta Makanan 1983 [Akta 281]",
                    "Seksyen 13B(4) Akta Makanan 1983 [Akta 281]",
                    "Denda tidak melebihi RM20,000.00 atau penjara tidak melebihi 5 tahun atau kedua-duanya (Perbicaraan di Mahkamah Sesyen mengikut S.63/64 Akta 92).",
                    "TIDAK BOLEH DIKOMPAUN — Wajib Buka IP Terus ke Mahkamah Sesyen",
                    "Tiada tawaran kompaun (Buka IP Terus)",
                    "Tidak Berkenaan (Buka IP Terus)",
                )
            if _has_pat(r"(?<!\w)(?:seksyen\s+11(?:\([12]\))?|s\.?\s*11(?:\([12]\))?|perintah\s+tutup|penutupan\s+premis\s+makanan|ingkar\s+arahan\s+penutupan)(?!\w)"):
                return (
                    "Seksyen 11 Akta Makanan 1983 [Akta 281] (Ingkar Perintah Penutupan Premis Tidak Suci)",
                    "Seksyen 11 Akta Makanan 1983 [Akta 281]",
                    "Penjara tidak melebihi 5 tahun atau denda atau kedua-duanya (Perbicaraan di Mahkamah Sesyen jika hukuman melebihi had Majistret S.87 Akta 92).",
                    "TIDAK BOLEH DIKOMPAUN — Wajib Buka IP Terus ke Mahkamah",
                    "Tiada tawaran kompaun (Buka IP Terus)",
                    "Tidak Berkenaan (Buka IP Terus)",
                )
            if _has_pat(r"(?<!\w)(?:seksyen\s+4\(4\)|s\.?\s*4\(4\)|menghalang\s+pegawai\s+diberi\s+kuasa)(?!\w)"):
                return (
                    "Seksyen 4(4) Akta Makanan 1983 [Akta 281]",
                    "Seksyen 4(4) Akta Makanan 1983 [Akta 281]",
                    "Penjara tidak melebihi 1 tahun atau denda atau kedua-duanya.",
                    "TIDAK BOLEH DIKOMPAUN — Wajib Buka IP Terus ke Mahkamah",
                    "Tiada tawaran kompaun (Buka IP Terus)",
                    "Tidak Berkenaan (Buka IP Terus)",
                )
            if _has_pat(r"(?<!\w)(?:14\(9\)|peraturan\s+14\(9\)|tarikh\s+akhir|tamat\s+tempoh|luput\s+tarikh|expired|ppm\s*1985)(?!\w)"):
                return (
                    "Peraturan 14(9)(b) Peraturan-Peraturan Makanan 1985 [P.U. (A) 437/1985]",
                    "Peraturan 397(2) Peraturan-Peraturan Makanan 1985 [P.U. (A) 437/1985]",
                    "Denda tidak melebihi RM10,000.00 atau penjara tidak melebihi 2 tahun.",
                    "Notis Seksyen 32B & Seksyen 33 Akta Makanan 1983 (Boleh kompaun bagi kesalahan tersenarai dalam Jadual Peraturan Makanan)",
                    "14 hari dari tarikh penyampaian notis",
                    "RM 2,500.00",
                )
            if _has_pat(r"(?<!\w)(?:tifoid|typhoid|antitifoid|31\(1\)|peraturan\s+31)(?!\w)"):
                return (
                    "Peraturan 31(1) Peraturan-Peraturan Kebersihan Makanan 2009 [P.U. (A) 95/2009]",
                    "Peraturan 31(3) Peraturan-Peraturan Kebersihan Makanan 2009 [P.U. (A) 95/2009]",
                    "Denda tidak melebihi RM10,000.00 atau penjara tidak melebihi 2 tahun.",
                    "Notis Seksyen 32B & Seksyen 33 Akta Makanan 1983 [Jadual Keempat PPKM 2009]",
                    "14 hari dari tarikh penyampaian notis",
                    "RM 250.00",
                )
            if _has_pat(r"(?<!\w)(?:slpm|latihan\s+pengendali|kursus\s+pengendali|30\(1\)|peraturan\s+30)(?!\w)"):
                return (
                    "Peraturan 30(1) Peraturan-Peraturan Kebersihan Makanan 2009 [P.U. (A) 95/2009]",
                    "Peraturan 30(3) Peraturan-Peraturan Kebersihan Makanan 2009 [P.U. (A) 95/2009]",
                    "Denda tidak melebihi RM10,000.00 atau penjara tidak melebihi 2 tahun.",
                    "Notis Seksyen 32B & Seksyen 33 Akta Makanan 1983 [Jadual Keempat PPKM 2009]",
                    "14 hari dari tarikh penyampaian notis",
                    "RM 250.00",
                )
            if _has_pat(r"(?<!\w)(?:apron|penutup\s+kepala|kasut\s+bertutup|pakaian\s+pengendali|32\(1\)|peraturan\s+32)(?!\w)"):
                return (
                    "Peraturan 32(1) Peraturan-Peraturan Kebersihan Makanan 2009 [P.U. (A) 95/2009]",
                    "Peraturan 32(3) Peraturan-Peraturan Kebersihan Makanan 2009 [P.U. (A) 95/2009]",
                    "Denda tidak melebihi RM1,000.00 (had kompaun maks RM500.00).",
                    "Notis Seksyen 32B & Seksyen 33 Akta Makanan 1983 [Jadual Keempat PPKM 2009]",
                    "14 hari dari tarikh penyampaian notis",
                    "RM 100.00",
                )
            if _has_pat(r"(?<!\w)(?:fosim|perakuan\s+pendaftaran|peraturan\s+8|8\(1\)|p\.?\s*8\(1\))(?!\w)"):
                return (
                    "Peraturan 8(1) Peraturan-Peraturan Kebersihan Makanan 2009 [P.U. (A) 95/2009]",
                    "Peraturan 8(2) Peraturan-Peraturan Kebersihan Makanan 2009 [P.U. (A) 95/2009]",
                    "Denda tidak melebihi RM10,000.00 atau penjara tidak melebihi 2 tahun.",
                    "Notis Seksyen 32B & Seksyen 33 Akta Makanan 1983 [Jadual Keempat PPKM 2009]",
                    "14 hari dari tarikh penyampaian notis",
                    "RM 250.00",
                )
            return (
                "Peraturan 11(1)(a) Peraturan-Peraturan Kebersihan Makanan 2009 [P.U. (A) 95/2009]",
                "Peraturan 11(2) Peraturan-Peraturan Kebersihan Makanan 2009 [P.U. (A) 95/2009]",
                "Denda tidak melebihi RM10,000.00 atau penjara tidak melebihi 2 tahun.",
                "Notis Seksyen 32B & Seksyen 33 Akta Makanan 1983 [Jadual Keempat PPKM 2009]",
                "14 hari dari tarikh penyampaian notis",
                "RM 500.00",
            )

        # --- AKTA 154 (APSPP 1975) ---
        if "154" in akta_low or "aedes" in low or "larva" in low or "apspp" in low:
            if _has_pat(r"(?<!\w)(?:seksyen\s+21|s\.?\s*21|menghalang|halang\s+fogging|halang\s+semburan|semburan\s+kabus)(?!\w)"):
                return (
                    "Seksyen 21 Akta Pemusnahan Serangga Pembawa Penyakit 1975 [Akta 154]",
                    "Seksyen 23(a) [Kesalahan Pertama] / Seksyen 23(b) [Ulangan] Akta 154",
                    "Kesalahan pertama: Denda tidak melebihi RM10,000 atau penjara tidak melebihi 2 tahun atau kedua-duanya. Kesalahan kedua/ulangan: Denda tidak melebihi RM50,000 atau penjara tidak melebihi 5 tahun.",
                    "TIDAK BOLEH DIKOMPAUN — Wajib Buka IP Terus ke Mahkamah",
                    "Tiada tawaran kompaun (Buka IP Terus)",
                    "Tidak Berkenaan (Buka IP Terus)",
                )
            if _has_pat(r"(?<!\w)(?:seksyen\s+8\(8\)|s\.?\s*8\(8\)|ingkar\s+perintah\s+(?:bertulis\s+)?seksyen\s+8|perintah\s+bertulis\s+seksyen\s+8|notis\s+seksyen\s+8)(?!\w)"):
                return (
                    "Seksyen 8(8) Akta Pemusnahan Serangga Pembawa Penyakit 1975 [Akta 154]",
                    "Seksyen 23(a) [Kesalahan Pertama] / Seksyen 23(b) [Ulangan] Akta 154",
                    "Kesalahan pertama: Denda tidak melebihi RM10,000 atau penjara tidak melebihi 2 tahun atau kedua-duanya. Kesalahan kedua/ulangan: Denda tidak melebihi RM50,000 atau penjara tidak melebihi 5 tahun.",
                    "TIDAK BOLEH DIKOMPAUN — Wajib Buka IP Terus ke Mahkamah",
                    "Tiada tawaran kompaun (Buka IP Terus)",
                    "Tidak Berkenaan (Buka IP Terus)",
                )
            return (
                "Seksyen 13(1) dibaca bersama Seksyen 13(2) Akta Pemusnahan Serangga Pembawa Penyakit 1975 [Akta 154]",
                "Seksyen 23(a) Akta Pemusnahan Serangga Pembawa Penyakit 1975 [Akta 154]",
                "Kesalahan pertama: Denda tidak melebihi RM10,000 atau penjara tidak melebihi 2 tahun atau kedua-duanya.",
                "Seksyen 25 Akta 154 (Maksimum RM500.00)",
                "14 hari dari tarikh notis kompaun",
                "RM 500.00",
            )

        # --- AKTA 342 (APPPB 1988 + Pindaan Akta A1742) ---
        if "342" in akta_low or "342" in low or "tibi" in low or "tuberkulosis" in low or "apppb" in low:
            if not _has_pat(r"(?<!\w)(?:seksyen\s+22\(b\)|s\.?\s*22\(b\)|cicir\s+rawatan)(?!\w)") and _has_pat(
                r"(?<!\w)(?:seksyen\s+10\(2\)|s\.?\s*10\(2\)|gagal\s+(?:membuat\s+)?notifikasi|tidak\s+(?:membuat\s+)?notifikasi|gagal\s+melapor(?:kan)?\s+penyakit|pengamal\s+perubatan\s+(?:gagal|tidak))(?!\w)"
            ):
                return (
                    "Seksyen 10(2) Akta Pencegahan dan Pengawalan Penyakit Berjangkit 1988 [Akta 342]",
                    "Seksyen 24(a) [Individu] / Seksyen 24(b) [Pertubuhan Perbadanan] Akta 342 (Pindaan Akta A1742)",
                    "Individu: Denda tidak melebihi RM10,000.00 atau penjara tidak melebihi 2 tahun atau kedua-duanya | Syarikat: Denda tidak melebihi RM100,000.00.",
                    "Seksyen 25 Akta 342 [P.U. (A) 139/2025] (dengan keizinan bertulis Pendakwa Raya)",
                    "14 hari dari tarikh tawaran kompaun",
                    "RM 1,000.00",
                )
            if _has_pat(r"(?<!\w)(?:seksyen\s+12\(1\)|s\.?\s*12\(1\)|bersiar-siar|mendedahkan\s+orang\s+awam)(?!\w)"):
                return (
                    "Seksyen 12(1) Akta Pencegahan dan Pengawalan Penyakit Berjangkit 1988 [Akta 342]",
                    "Seksyen 24(a) Akta 342 (Pindaan Akta A1742)",
                    "Denda tidak melebihi RM10,000.00 atau penjara tidak melebihi 2 tahun atau kedua-duanya.",
                    "TIDAK BOLEH DIKOMPAUN (tiada dalam Jadual Pertama P.U. (A) 139/2025) — Wajib Buka IP Terus ke Mahkamah",
                    "Tiada tawaran kompaun (Buka IP Terus)",
                    "Tidak Berkenaan (Buka IP Terus)",
                )
            if _has_pat(r"(?<!\w)(?:seksyen\s+22\(a\)|s\.?\s*22\(a\)|menghalang\s+pegawai\s+diberi\s+kuasa)(?!\w)"):
                return (
                    "Seksyen 22(a) Akta Pencegahan dan Pengawalan Penyakit Berjangkit 1988 [Akta 342]",
                    "Seksyen 24(a) [Individu] / Seksyen 24(b) [Pertubuhan Perbadanan] Akta 342 (Pindaan Akta A1742)",
                    "Individu: Denda tidak melebihi RM10,000.00 atau penjara tidak melebihi 2 tahun atau kedua-duanya | Syarikat: Denda tidak melebihi RM100,000.00.",
                    "TIDAK BOLEH DIKOMPAUN (tiada dalam Jadual Pertama P.U. (A) 139/2025) — Wajib Buka IP Terus ke Mahkamah",
                    "Tiada tawaran kompaun (Buka IP Terus)",
                    "Tidak Berkenaan (Buka IP Terus)",
                )
            if any(k in low for k in ("smear negatif", "afb negatif", "disaring", "saringan", "enggan mula", "taknak mula")):
                return (
                    "Seksyen 14A(1) & Seksyen 14 Akta 342 [Pindaan Akta A1742] (Perintah Pengasingan/Pengawasan; S.22(b) hanya terpakai selepas diagnosis aktif disahkan MO/FMS & notis bertulis diserahkan lalu diingkari)",
                    "Seksyen 24(a) [Individu] / Seksyen 24(b) [Pertubuhan Perbadanan] Akta 342 (Pindaan Akta A1742)",
                    "Individu: Denda tidak melebihi RM10,000.00 atau penjara tidak melebihi 2 tahun atau kedua-duanya | Syarikat: Denda tidak melebihi RM100,000.00.",
                    "JANGAN keluarkan kompaun atau buka IP S.22(b) selagi pengesahan klinikal MO/FMS (CXR/GeneXpert/Kultur) dan serahan notis bertulis belum lengkap.",
                    "14 hari (sekiranya notis atau kompaun terpakai selepas pengesahan)",
                    "Tidak Berkenaan (Sahkan Klinikal Dahulu)",
                )
            return (
                "Seksyen 22(b) Akta Pencegahan dan Pengawalan Penyakit Berjangkit 1988 [Akta 342]",
                "Seksyen 24(a) [Individu] / Seksyen 24(b) [Pertubuhan Perbadanan] Akta 342 (Pindaan Akta A1742)",
                "Individu: Denda tidak melebihi RM10,000.00 atau penjara tidak melebihi 2 tahun atau kedua-duanya | Pertubuhan Perbadanan [S.24(b)]: Denda tidak melebihi RM100,000.00.",
                "Seksyen 25 Akta 342 [P.U. (A) 139/2025] (atau pendakwaan terus tanpa tawaran kompaun bagi kes Tibi cicir rawatan berisiko awam)",
                "14 hari (jika kompaun ditawarkan)",
                "RM 1,000.00",
            )

        # Fallback dinamik daripada matriks kesalahan AGC (ClosedBookLegalLibrary)
        try:
            from backend.rag.legal_engine import get_legal_library

            grounding = get_legal_library().search_closed_book_grounding(text[:600], akta_hint=akta_utama, top_k=1)
            cands = grounding.get("candidate_offences") or []
            if cands:
                top_o = cands[0]
                comp_i = top_o.get("compound_info") or {}
                pen_i = top_o.get("penalty_first_offence") or {}
                is_comp = bool(comp_i.get("is_compoundable"))
                return (
                    f"{top_o.get('offence_section')} ({top_o.get('canonical_akta_code') or akta_utama})",
                    str(top_o.get("penalty_section") or f"Peruntukan penalti di bawah {akta_utama}"),
                    str(pen_i.get("verbatim_penalty") or "Tertakluk had maksimum penalti di bawah Akta berkaitan."),
                    str(comp_i.get("compound_amount_or_limit") or ("Boleh dikompaun mengikut jadual Akta" if is_comp else "TIDAK BOLEH DIKOMPAUN — Rujuk PDRM/TPR")),
                    f"{comp_i.get('payment_days') or 14} hari" if is_comp else "Tiada tawaran kompaun",
                    str(comp_i.get("max_compound_rm") or "RM 250.00") if is_comp else "Tidak Berkenaan",
                )
        except Exception:
            pass

        primary = citations[0] if citations else None
        return (
            f"{primary.section}, {primary.akta_title}" if primary else akta_utama,
            f"Peruntukan penalti di bawah {akta_utama}",
            "Tertakluk had maksimum penalti di bawah Akta berkaitan.",
            f"Peruntukan kompaun di bawah {akta_utama}",
            "14 hari",
            "RM 250.00",
        )
