"""
i-UIP Nerus — Enjin Otak Perundangan & SOP KKM (Zero-Hallucination Architecture)
Menyokong 2 mod pengeluaran menggunakan Google GenAI SDK (`google-genai`):
  1. Mod Two-Stage Router + Full-SOP Injection (Paling jimat untuk trafik rendah/sederhana)
  2. Mod Gemini Context Caching (Paling pantas & konsisten untuk trafik tinggi Cloud Run)

Disambungkan dengan Seni Bina Dual Knowledge Store:
  - Lapisan 1: Pustaka Statut Verbatim AGC/KKM sedia ada (`backend.rag.legal_engine`)
  - Lapisan 2: 22 SOP Aktif KKM Pindaan 15 Februari 2024 (`data/sop_kkm_2024/sops_aktif/`)
  - Larangan Keras: 5 SOP PPKHT 2004 mansuh (`sops_arkib_deprecated/`) TIDAK sesekali dimuatkan atau diindeks.

Keperluan env var:
  GEMINI_API_KEY=<api_key_anda>
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

try:
    from google import genai
    from google.genai import types
except Exception:  # pragma: no cover
    genai = None  # type: ignore
    types = None  # type: ignore

try:
    from backend.services.sop_brain.system_prompts import (
        AUDIT_PRA_TPR_SYSTEM_PROMPT,
        PAKAR_UIP_SYSTEM_PROMPT,
        ROUTER_SYSTEM_PROMPT,
    )
except ImportError:  # pragma: no cover - sokongan import terus standalone
    from system_prompts import (  # type: ignore
        AUDIT_PRA_TPR_SYSTEM_PROMPT,
        PAKAR_UIP_SYSTEM_PROMPT,
        ROUTER_SYSTEM_PROMPT,
    )

logger = logging.getLogger("uip.sop_brain")

DEFAULT_PACKAGE_ROOT = Path(__file__).resolve().parents[3]

# Pemetaan rasmi Lampiran Senarai Semak K/S dalam UIP-UMUM-02-07 (PINDAAN 2024)
LAMPIRAN_KS_BY_ACT: Dict[str, Dict[str, str]] = {
    "Akta 281": {
        "lampiran": "Lampiran A (UIP-UMUM-02-07)",
        "butiran": "Senarai Semak Kertas Siasatan — Akta Makanan 1983 [Akta 281]",
    },
    "Akta 154": {
        "lampiran": "Lampiran B (UIP-UMUM-02-07)",
        "butiran": "Senarai Semak Kertas Siasatan — Akta Pemusnahan Serangga Pembawa Penyakit 1975 [Akta 154]",
    },
    "Akta 852": {
        "lampiran": "[NOTA PINDAAN] Lampiran C (PPKHT 2004) DIMANSUHKAN — Guna Senarai Semak Akta 852",
        "butiran": (
            "Lampiran C dalam UIP-UMUM-02-07 (15 Feb 2024) merujuk PPKHT 2004 yang telah MANSUH pada 1 Okt 2024. "
            "Sediakan K/S mengikut Folio A–D UIP-UMUM-02-07 dengan punca kuasa Akta 852 (Notis S.47, Sitaan S.35/S.36, "
            "Izin Dakwa S.41 & Liabiliti Syarikat S.49)."
        ),
    },
    "PPKM 2009": {
        "lampiran": "Lampiran D (UIP-UMUM-02-07)",
        "butiran": "Senarai Semak Kertas Siasatan — Peraturan-Peraturan Kebersihan Makanan 2009 [PPKM 2009]",
    },
    "PPM 1985": {
        "lampiran": "Lampiran E (UIP-UMUM-02-07)",
        "butiran": "Senarai Semak Kertas Siasatan — Peraturan-Peraturan Makanan 1985 [PPM 1985]",
    },
    "Akta 342": {
        "lampiran": "Lampiran F (UIP-UMUM-02-07)",
        "butiran": "Senarai Semak Kertas Siasatan — Akta Pencegahan dan Pengawalan Penyakit Berjangkit 1988 [Akta 342]",
    },
}


class RouteDecision(BaseModel):
    """Output berstruktur dari Stage 1 Router."""

    akta_terlibat: List[str] = Field(
        description="Senarai akta terlibat, cth: ['Akta 154', 'Akta 852', 'Akta 281', 'Akta 342']"
    )
    selected_sop_ids: List[str] = Field(
        description="0 hingga 3 sop_id tepat daripada sop_index_active_router.json"
    )
    melibatkan_akta_852: bool = Field(
        description="True jika kes melibatkan produk merokok, vape, shisha, OBD, atau kawasan larangan merokok"
    )
    sebab_pilihan: str = Field(
        description="Justifikasi ringkas mengapa SOP tersebut dipilih"
    )
    amaran_statut_mansuh: Optional[str] = Field(
        default=None,
        description="Isi amaran jika soalan pengguna memetik PPKHT 2004 atau kod SOP lama",
    )


def _resolve_sop_data_dir(package_root: Path) -> Path:
    """Selesaikan folder data SOP aktif daripada `package_root` tanpa merosakkan struktur asal pakej."""
    candidates = [
        package_root / "data" / "sop_kkm_2024",
        package_root / "data",
        package_root,
    ]
    for cand in candidates:
        if (cand / "sop_index_active_router.json").exists():
            return cand
    return package_root / "data" / "sop_kkm_2024"


def _extract_pdf_pages_from_frontmatter(md_path: Path) -> str:
    """Ekstrak julat muka surat PDF daripada frontmatter YAML fail SOP aktif."""
    if not md_path.exists():
        return ""
    try:
        head = md_path.read_text(encoding="utf-8")[:1200]
        m = re.search(r'^muka_surat_pdf:\s*"?([^"\n]+)"?', head, flags=re.M)
        if m:
            return m.group(1).strip()
    except Exception:
        pass
    return ""


def _resolve_active_md_path(sop_data_dir: Path, fail_md: str) -> Optional[Path]:
    """Pastikan laluan Markdown HANYA berada di dalam `sops_aktif/` dan BUKAN `sops_arkib_deprecated/`."""
    norm = (fail_md or "").replace("\\", "/").strip()
    if not norm:
        return None
    low = norm.lower()
    if "sops_arkib_deprecated" in low or "ppkht" in low:
        return None
    rel = norm[len("data/"):] if low.startswith("data/") else norm
    cand = (sop_data_dir / rel).resolve()
    aktif_root = (sop_data_dir / "sops_aktif").resolve()
    try:
        cand.relative_to(aktif_root)
    except ValueError:
        return None
    return cand


def build_statutory_context_for_question(
    soalan: str,
    akta_hint: str = "Semua",
    top_k: int = 4,
) -> str:
    """Tarik petikan seksyen tepat daripada Pustaka Statut Verbatim sedia ada (`ClosedBookLegalLibrary`)
    untuk disuntik ke dalam `konteks_statut_tambahan` pada Peringkat 2 Otak SOP."""
    try:
        from backend.rag.legal_engine import get_legal_library

        lib = get_legal_library()
        grounding = lib.search_closed_book_grounding(
            question=soalan,
            akta_hint=akta_hint,
            top_k=top_k,
        )
        parts: List[str] = []
        amendments = grounding.get("amendment_directives") or []
        if amendments:
            parts.append(
                "[NOTA PINDAAN STATUT TERKINI — MENGATASI SOP 15 FEB 2024]:\n"
                + "\n".join(f"- {a}" for a in amendments)
            )
        repealed = grounding.get("repealed_matches") or []
        if repealed:
            rep_lines = [
                f"- {r.get('repealed_statute_or_section', '')}: {r.get('warning_message_bm', '')}"
                for r in repealed
            ]
            parts.append("[AMARAN PERUNTUKAN DIMANSUHKAN]:\n" + "\n".join(rep_lines))
        ctx_block = str(grounding.get("statutory_context_block") or "").strip()
        if ctx_block:
            parts.append(ctx_block)
        return "\n\n".join(parts).strip()
    except Exception as exc:
        logger.warning("Gagal menarik konteks statut tambahan daripada legal_engine: %s", exc)
        return ""


QUARANTINED_PPKHT_SOPS_COUNT = 5


class IUIPNerusBrain:
    """Enjin utama rujukan SOP KKM Pindaan 2024 (33 SOP Aktif) + Statut untuk i-UIP Nerus."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        package_root: Path | str = DEFAULT_PACKAGE_ROOT,
        router_model: Optional[str] = None,
        answer_model: Optional[str] = None,
    ) -> None:
        self._api_key_override = (api_key or "").strip() or None
        self.package_root = Path(package_root)
        self.sop_data_dir = _resolve_sop_data_dir(self.package_root)

        cfg_router = "gemini-2.5-flash"
        cfg_answer = "gemini-2.5-pro"
        try:
            from backend.core.config import settings as _settings

            cfg_router = _settings.sop_brain_router_model or cfg_router
            cfg_answer = _settings.sop_brain_answer_model or cfg_answer
        except Exception:
            pass

        self.router_model = (router_model or cfg_router).strip()
        self.answer_model = (answer_model or cfg_answer).strip()

        self._client_lock = threading.RLock()
        self._client: Any = None
        self._client_key_used: Optional[str] = None
        self._active_cache_name: Optional[str] = None
        self._active_cache_expires_at: float = 0.0

        router_index_path = self.sop_data_dir / "sop_index_active_router.json"
        if not router_index_path.exists():
            raise FileNotFoundError(
                f"Indeks SOP aktif tidak dijumpai di {router_index_path}. "
                "Pastikan fail sop_index_active_router.json diekstrak ke data/sop_kkm_2024/."
            )

        with open(router_index_path, "r", encoding="utf-8") as f:
            raw_index: List[dict] = json.load(f)

        # Sekatan keras: JANGAN sesekali muatkan SOP PPKHT 2004 atau fail dari sops_arkib_deprecated/
        self.active_index: List[dict] = []
        self._sop_lookup: dict[str, dict] = {}
        self._pdf_pages_by_stem: dict[str, str] = {}
        self._structured_by_stem: dict[str, Dict[str, Any]] = {}
        self._search_blob_by_stem: dict[str, str] = {}
        self._pekeliling_rujukan: List[Dict[str, Any]] = []

        structured_dir = self.sop_data_dir / "sops_structured"
        for rec in raw_index:
            sop_id = str(rec.get("sop_id") or "")
            fail_md = str(rec.get("fail_md") or "")
            if "PPKHT" in sop_id.upper() or "sops_arkib_deprecated" in fail_md.lower():
                logger.warning("Menyekat SOP mansuh daripada indeks aktif: %s", sop_id)
                continue
            md_path = _resolve_active_md_path(self.sop_data_dir, fail_md)
            if md_path is None:
                logger.warning("Laluan SOP tidak sah / luar sops_aktif disekat: %s", fail_md)
                continue
            self.active_index.append(rec)
            self._sop_lookup[sop_id.upper()] = rec
            stem = str(rec.get("file_stem") or "")
            if stem:
                stem_up = stem.upper()
                self._sop_lookup[stem_up] = rec
                self._pdf_pages_by_stem[stem_up] = _extract_pdf_pages_from_frontmatter(md_path)
                struct_path = structured_dir / f"{stem}.json"
                if struct_path.exists():
                    try:
                        s_obj = json.loads(struct_path.read_text(encoding="utf-8"))
                        if isinstance(s_obj, dict) and "PPKHT" not in str(s_obj.get("sop_id") or "").upper():
                            self._structured_by_stem[stem_up] = s_obj
                            self._search_blob_by_stem[stem_up] = self._build_structured_search_blob(s_obj)
                    except Exception as exc:
                        logger.warning("Gagal memuatkan SOP berstruktur %s: %s", struct_path.name, exc)
            if rec.get("toc_id_alias"):
                alias_full = str(rec["toc_id_alias"]).upper()
                self._sop_lookup[alias_full] = rec
                alias_code = alias_full.split(" ")[0].strip()
                if alias_code and "PPKHT" not in alias_code:
                    self._sop_lookup[alias_code] = rec

        pek_path = self.sop_data_dir / "pekeliling_rujukan.json"
        if pek_path.exists():
            try:
                raw_pek = json.loads(pek_path.read_text(encoding="utf-8"))
                if isinstance(raw_pek, list):
                    self._pekeliling_rujukan = [p for p in raw_pek if isinstance(p, dict)]
                elif isinstance(raw_pek, dict):
                    self._pekeliling_rujukan = [raw_pek]
            except Exception as exc:
                logger.warning("Gagal memuatkan pekeliling_rujukan.json: %s", exc)

    @staticmethod
    def _build_structured_search_blob(s_obj: Dict[str, Any]) -> str:
        """Bina indeks carian teks penuh bagi langkah, lampiran, singkatan & nota pindaan satu SOP."""
        parts: List[str] = [
            str(s_obj.get("tujuan") or ""),
            str(s_obj.get("ringkasan_eksekutif") or ""),
            str(s_obj.get("punca_kuasa") or ""),
            str(s_obj.get("panduan_am") or ""),
        ]
        for ph in s_obj.get("fasa_kerja") or []:
            parts.append(str(ph.get("tajuk_fasa") or ""))
            for st in ph.get("langkah") or []:
                parts.append(str(st.get("ringkas") or ""))
                for act in st.get("tindakan") or []:
                    parts.append(str(act))
                for ref in st.get("rujukan") or []:
                    parts.append(str(ref))
        for lamp in s_obj.get("lampiran") or []:
            parts.append(f"{lamp.get('kod', '')} {lamp.get('tajuk', '')}")
        for sg in s_obj.get("singkatan") or []:
            parts.append(f"{sg.get('kod', '')} {sg.get('maksud', '')}")
        for np in s_obj.get("nota_pindaan") or []:
            parts.append(f"{np.get('tajuk', '')} {np.get('butiran', '')}")
        return re.sub(r"\s+", " ", " ".join(p for p in parts if p)).strip()

    def _resolve_api_key(self) -> Optional[str]:
        if self._api_key_override:
            return self._api_key_override
        try:
            from backend.core.config import settings as _settings

            if _settings.has_gemini_key:
                return _settings.gemini_api_key.strip()
        except Exception:
            pass
        env_key = (os.environ.get("GEMINI_API_KEY") or "").strip()
        if env_key and env_key != "your_gemini_api_key_here":
            return env_key
        return None

    @property
    def has_api_key(self) -> bool:
        return bool(self._resolve_api_key()) and genai is not None and types is not None

    @property
    def client(self) -> Any:
        """Klien `google.genai.Client` dibina secara malas (lazy) supaya import/ujian offline tidak ralat."""
        key = self._resolve_api_key()
        if not key or genai is None:
            return None
        with self._client_lock:
            if self._client is None or self._client_key_used != key:
                self._client = genai.Client(api_key=key)
                self._client_key_used = key
                self._active_cache_name = None
            return self._client

    def refresh_client(self) -> None:
        with self._client_lock:
            self._client = None
            self._client_key_used = None
            self._active_cache_name = None

    def _candidate_models(self, primary: str, role: str) -> List[str]:
        """Senarai calon model Gemini dengan fallback selamat sekiranya model utama tidak tersedia pada tier API."""
        cands: List[str] = [primary]
        try:
            from backend.core.config import settings as _settings

            if role == "router":
                for m in ("gemini-2.5-flash", _settings.standard_fallback_model, _settings.multimodal_model):
                    if m and m not in cands:
                        cands.append(m)
            else:
                for m in ("gemini-2.5-pro", _settings.reasoning_model, _settings.standard_fallback_model, "gemini-2.5-flash"):
                    if m and m not in cands:
                        cands.append(m)
        except Exception:
            if role == "router" and "gemini-2.5-flash" not in cands:
                cands.append("gemini-2.5-flash")
            elif role != "router" and "gemini-2.5-flash" not in cands:
                cands.append("gemini-2.5-flash")
        return [m for m in cands if m]

    def _sanitize_route_decision(self, decision: RouteDecision) -> RouteDecision:
        """Lapisan keselamatan keras: buang sebarang kod PPKHT / tidak sah dan normalkan ke `sop_id` rasmi."""
        clean_sops: List[str] = []
        seen_stems: set[str] = set()
        for raw_id in decision.selected_sop_ids:
            up = str(raw_id or "").strip().upper()
            if not up or "PPKHT" in up:
                continue
            rec = self._sop_lookup.get(up)
            if not rec:
                # Cuba padanan awalan file_stem
                code_head = up.split(" ")[0].strip()
                rec = self._sop_lookup.get(code_head)
            if not rec:
                continue
            stem = str(rec["file_stem"]).upper()
            if stem in seen_stems:
                continue
            seen_stems.add(stem)
            clean_sops.append(rec["sop_id"])
            if len(clean_sops) >= 3:
                break

        akta_clean = list(dict.fromkeys(str(a).strip() for a in decision.akta_terlibat if str(a).strip()))
        if decision.melibatkan_akta_852 and not any("852" in a for a in akta_clean):
            akta_clean.insert(0, "Akta 852")

        return RouteDecision(
            akta_terlibat=akta_clean or ["Akta Kesihatan Awam KKM"],
            selected_sop_ids=clean_sops,
            melibatkan_akta_852=bool(decision.melibatkan_akta_852),
            sebab_pilihan=decision.sebab_pilihan,
            amaran_statut_mansuh=decision.amaran_statut_mansuh,
        )

    def route_question_deterministic(self, soalan: str) -> RouteDecision:
        """Penghala deterministik tempatan mematuhi 100% Peraturan Router (`ROUTER_SYSTEM_PROMPT`).

        Digunakan untuk:
        - Mod Pantas (`use_ai=False`) supaya PPKP tetap menerima rujukan kod SOP aktif & muka surat PDF serta-merta.
        - Fallback selamat apabila `GEMINI_API_KEY` tiada di persekitaran tempatan / luar talian.
        """
        q_orig = (soalan or "").strip()
        try:
            from backend.rag.legal_engine import normalize_ppkp_query

            q = normalize_ppkp_query(q_orig)
        except Exception:
            q = q_orig
        q_low = f"{q_orig.lower()} {q.lower()}".strip()

        akta_terlibat: List[str] = []
        selected: List[str] = []
        reasons: List[str] = []
        amaran_list: List[str] = []

        def _add_sop(sop_key: str, reason: str) -> None:
            rec = self._sop_lookup.get(sop_key.upper())
            if not rec:
                return
            sid = rec["sop_id"]
            if sid not in selected:
                selected.append(sid)
                reasons.append(reason)

        def _add_act(act: str) -> None:
            if act not in akta_terlibat:
                akta_terlibat.append(act)

        # Peraturan 2: Kes merokok / vape / shisha / OBD / PPKHT 2004 -> WAJIB Akta 852 + SOP rasmi UIP-AKPMDKA-01-24..08-24, SIFAR SOP PPKHT
        melibatkan_852 = bool(
            re.search(
                r"\b(?:akta\s*852|akpmdka|uip-akpmdka|ppkht|vape|rokok|merokok|shisha|tembakau|nikotin|obd|orang\s+belum\s+dewasa|"
                r"paket\s+terbuka|sebatang-sebatang|sebatang\s+sebatang|borang\s+4.*23\(2\)|peraturan\s+8\s+dan\s+9|"
                r"kawasan\s+larangan\s+merokok|tanda\s+larangan\s+merokok|produk\s+merokok)(?=\W|$)",
                q_low,
            )
        )
        if melibatkan_852:
            _add_act("Akta 852")
            if re.search(r"\b(?:ppkht|32b|borang\s+4|peraturan\s+8|peraturan\s+9)(?=\W|$)", q_low):
                amaran_list.append(
                    "PPKHT 2004 dan Notis Seksyen 32B Akta Makanan 1983 bagi kes produk merokok/vape telah MANSUH "
                    "sejak 1 Oktober 2024 dan digantikan sepenuhnya oleh Akta 852 (UIP-AKPMDKA-01-24 hingga 08-24)."
                )
            # Pemadanan 8 SOP rasmi Akta 852 (kuat kuasa 1 Okt 2024)
            if re.search(r"\b(?:uip-akpmdka-02-24|seksyen\s+32\s+akta\s*852)\b", q_low) or (
                re.search(r"\b(?:geledah|menggeledah|waran\s+geledah)\b", q_low)
                and re.search(r"\b(?:dengan\s+waran|mohon\s+waran|waran\s+geledah|majistret|seksyen\s+32)\b", q_low)
                and not re.search(r"\btanpa\s+waran\b", q_low)
            ):
                _add_sop("UIP-AKPMDKA-02-24", "Geledah dengan waran Majistret di bawah Seksyen 32 Akta 852")
            if re.search(r"\b(?:uip-akpmdka-03-24|seksyen\s+33\s+akta\s*852)\b", q_low) or (
                re.search(r"\b(?:geledah|menggeledah)\b", q_low) and re.search(r"\b(?:tanpa\s+waran|seksyen\s+33)\b", q_low)
            ):
                _add_sop("UIP-AKPMDKA-03-24", "Geledah tanpa waran di bawah Seksyen 33 Akta 852")
            if re.search(r"\b(?:uip-akpmdka-04-24|persampelan|ambil\s+sampel|sampel\s+produk|seksyen\s+28\(2\)|s\.?28\(2\))\b", q_low):
                _add_sop("UIP-AKPMDKA-04-24", "Prosedur persampelan produk merokok di bawah Seksyen 28(2) Akta 852")
            if re.search(r"\b(?:uip-akpmdka-07-24|pemulangan\s+sementara|pulang(?:kan)?\s+sementara|tuntut\s+barang\s+sita)\b", q_low):
                _add_sop("UIP-AKPMDKA-07-24", "Prosedur pemulangan sementara barang yang disita (S.37 Akta 852)")
            if re.search(r"\b(?:uip-akpmdka-08-24|hantar.*makmal|penghantaran.*makmal|jabatan\s+kimia|analisis\s+makmal)\b", q_low):
                _add_sop("UIP-AKPMDKA-08-24", "Prosedur penghantaran barang kes produk merokok ke makmal")
            if re.search(r"\b(?:uip-akpmdka-06-24|sita|penyitaan|menyita|seksyen\s+35|seksyen\s+36|seksyen\s+37)\b", q_low):
                _add_sop("UIP-AKPMDKA-06-24", "Prosedur penyitaan barang kes di bawah Seksyen 35–37 Akta 852")
            if re.search(
                r"\b(?:uip-akpmdka-05-24|tidak\s+boleh\s+dikompaun|tidak\s+boleh\s+kompaun|jual\s+rokok|jual\s+vape|jualan|"
                r"sebatang-sebatang|sebatang\s+sebatang|paket\s+terbuka|pameran|iklan|promosi|tajaan|mesin\s+layan\s+diri|"
                r"tidak\s+berdaftar|seksyen\s+(?:3|7|8|9|10|11|12|13\(1\)|14|15)(?=\W|$))\b",
                q_low,
            ):
                _add_sop("UIP-AKPMDKA-05-24", "Prosedur penguatkuasaan kesalahan tidak boleh dikompaun Akta 852")
            if re.search(
                r"\b(?:uip-akpmdka-01-24|notis\s+(?:seksyen\s+)?47|seksyen\s+47|seksyen\s+48|kompaun|kawasan\s+larangan|"
                r"hisap\s+vape|menghisap|merokok\s+di|tanda\s+larangan|seksyen\s+(?:13\(3\)|16\(2\)|17\(1\)|18\(1\))|32b|borang\s+4)\b",
                q_low,
            ):
                _add_sop("UIP-AKPMDKA-01-24", "Prosedur Notis S.47 & Kompaun S.48 Akta 852 (kesalahan boleh dikompaun)")

        # Kesan alias / kod lama silap cetak untuk amaran
        if "uip-apspp-03-07" in q_low:
            amaran_list.append("Kod lama UIP-APSPP-03-07 telah digantikan dengan kod aktif UIP-UMUM-01-24.")
        if "uip-umum-01-23" in q_low:
            amaran_list.append("Kod rasmi Kamera Badan (BWC) ialah UIP-UMUM-01-22 (PINDAAN 2024), bukan UIP-UMUM-01-23.")
        if "uip-apppb-01-20" in q_low:
            amaran_list.append("Kod rasmi Penutupan Premis S.18(1)(f) Akta 342 ialah UIP-APPPB-06-20 (PINDAAN 2024).")
        if "subseksyen 5(1)" in q_low and ("342" in q_low or "pengawasan" in q_low or "pemerhatian" in q_low):
            amaran_list.append("Ralat cetak diperbetulkan: Perintah Pemerhatian/Pengawasan Akta 342 ialah Subseksyen 15(1), bukan 5(1).")

        # Peraturan 3: Menghalang tugas / enggan masuk / kasar / cedera / buang barang kes -> WAJIB UIP-UMUM-01-24
        is_halang = bool(
            re.search(
                r"\b(?:menghalang|halang\s+tugas|halang\s+ppkp|enggan\s+benarkan\s+masuk|tidak\s+benarkan\s+masuk|"
                r"tak\s+bagi\s+masuk|menengking|kasar|kekerasan|tolak\s+ppkp|pukul\s+ppkp|cedera|luka\s+di|serang|"
                r"buang\s+barang\s+kes|ugut|seksyen\s+186|s\.?186|seksyen\s+21\s+akta\s+154|4\(4\)\s+akta\s+makanan|"
                r"uip-umum-01-24|uip-apspp-03-07)(?=\W|$)",
                q_low,
            )
        )
        if is_halang:
            _add_sop("UIP-UMUM-01-24", "Melibatkan halangan tugas / kekasaran terhadap PPKP")
            if re.search(r"\b(?:tolak|pukul|cedera|luka|kasar|serang|ugut|186|polis)(?=\W|$)", q_low) or melibatkan_852:
                _add_act("Akta 574")
                _add_act("Akta 593")

        # Peraturan 4: Tapak bina (APSPP 1975 / Akta 154) -> UIP-APSPP-01-24
        is_tapak_bina = bool(
            re.search(r"\b(?:tapak\s+bina|tapak\s+binaan|tapak\s+pembinaan|kontraktor|8\(3\)\(aa\)|uip-apspp-01-24)(?=\W|$)", q_low)
        )
        if is_tapak_bina:
            _add_act("Akta 154")
            _add_sop("UIP-APSPP-01-24", "Pemeriksaan pembiakan Aedes di tapak binaan (Akta 154)")

        # Akta 154 (APSPP 1975) lain
        if re.search(r"\b(?:pecah\s+masuk|kekerasan\s+munasabah|rumah\s+kosong|rumah\s+terbiar|premis\s+berkunci|tuntut\s+kunci|5\(5\)|uip-apspp-01-16)(?=\W|$)", q_low):
            _add_act("Akta 154")
            _add_sop("UIP-APSPP-01-16", "Memasuki premis berkunci/terbiar dengan kekerasan munasabah (S.5(5) Akta 154)")
        if re.search(r"\b(?:izin\s+kompaun|tawaran\s+kompaun.*aedes|kompaun.*akta\s*154|kompaun.*apspp|tawaran\s+kompaun.*okk|16\(1\)\(b\)|uip-apspp-02-16)(?=\W|$)", q_low):
            _add_act("Akta 154")
            _add_sop("UIP-APSPP-02-16", "Prosedur tawaran kompaun di bawah Akta 154")
        if re.search(r"\b(?:identifikasi\s+larva|pemeriksa\s+larva|pspp|spesies\s+aedes|mikroskop|uip-apspp-02-07)(?=\W|$)", q_low):
            _add_act("Akta 154")
            _add_sop("UIP-APSPP-02-07", "Prosedur identifikasi spesies larva serangga pembawa penyakit")
        if (
            not is_tapak_bina
            and re.search(
                r"\b(?:aedes|jentik-jentik|jentik|larva|sampul\s+kecil|uipd|pembiakan\s+nyamuk|apspp|akta\s*154|uip-apspp-01-07)(?=\W|$)",
                q_low,
            )
            and not any(s.startswith("UIP-APSPP-01-16") or s.startswith("UIP-APSPP-02-16") for s in selected)
        ):
            _add_act("Akta 154")
            _add_sop("UIP-APSPP-01-07", "Pemeriksaan serangga pembawa penyakit di lapangan & pungutan larva")

        # Peraturan 5: Penutupan Premis & Perintah Akta 342
        has_18_d = bool(
            re.search(
                r"\b(?:18\(1\)\(d\)|keracunan\s+makanan|dekontaminasi|uip-apppb-01-07)(?=\W|$)",
                q_low,
            )
            or (
                re.search(r"\b(?:tutup|penutupan)(?=\W|$)", q_low)
                and re.search(r"\b(?:basmi\s+kuman|basmi\s+serangga|basmi\s+tikus|kantin)(?=\W|$)", q_low)
            )
        )
        has_18_f = bool(
            re.search(
                r"\b(?:18\(1\)\(f\)|mencegah\s+(?:bermulanya|perebakan|merebak)|uip-apppb-06-20|uip-apppb-01-20)(?=\W|$)",
                q_low,
            )
        )
        if has_18_d:
            _add_act("Akta 342")
            _add_sop("UIP-APPPB-01-07", "Penutupan premis S.18(1)(d) Akta 342 (basmi kuman/dekontaminasi/keracunan makanan)")
        if has_18_f:
            _add_act("Akta 342")
            _add_sop("UIP-APPPB-06-20", "Penutupan premis S.18(1)(f) Akta 342 (mencegah perebakan penyakit berjangkit)")
        if (
            not has_18_d
            and not has_18_f
            and re.search(r"\b(?:tutup\s+premis|penutupan\s+premis|tutup\s+taska|tutup\s+tadika|tutup\s+kantin)(?=\W|$)", q_low)
            and re.search(r"\b(?:akta\s*342|apppb|penyakit\s+berjangkit|hfmd|wabak|taska|tadika)(?=\W|$)", q_low)
        ):
            _add_act("Akta 342")
            _add_sop("UIP-APPPB-01-07", "Perbandingan penutupan premis S.18(1)(d) Akta 342")
            _add_sop("UIP-APPPB-06-20", "Perbandingan penutupan premis S.18(1)(f) Akta 342")

        if re.search(r"\b(?:18\(1\)\(c\)|tanpa\s+penutupan|tanpa\s+tutup\s+premis|uip-apppb-02-07)(?=\W|$)", q_low) or (
            re.search(r"\b(?:basmi\s+kuman|basmi\s+tikus|basmi\s+serangga)(?=\W|$)", q_low)
            and not re.search(r"\b(?:tutup|penutupan|18\(1\)\(d\)|18\(1\)\(f\)|barangan|binatang)(?=\W|$)", q_low)
        ):
            _add_act("Akta 342")
            _add_sop("UIP-APPPB-02-07", "Perintah basmi kuman/serangga/tikus S.18(1)(c) Akta 342 tanpa penutupan")

        if re.search(r"\b(?:18\(1\)\(e\)|barangan\s+tercemar|binatang\s+dijangkiti|musnah\s+barangan|uip-apppb-03-07)(?=\W|$)", q_low):
            _add_act("Akta 342")
            _add_sop("UIP-APPPB-03-07", "Perintah basmi kuman/pemusnahan barangan atau binatang S.18(1)(e) Akta 342")

        if re.search(
            r"\b(?:15\(1\)|perintah\s+pemerhatian|perintah\s+pengawasan|kuarantin|perintah\s+lisan.*24\s+jam|"
            r"pui|kontak\s+rapat|subseksyen\s+5\(1\)|uip-apppb-01-16)(?=\W|$)",
            q_low,
        ):
            _add_act("Akta 342")
            _add_sop("UIP-APPPB-01-16", "Penguatkuasaan Perintah Pemerhatian atau Pengawasan S.15(1) Akta 342")

        if re.search(r"\b(?:pesawat\s+udara|kapal\s+terbang|lapangan\s+terbang|pintu\s+masuk\s+antarabangsa|sanitasi.*kenderaan|7\(1\).*342|uip-apppb-02-16)(?=\W|$)", q_low):
            _add_act("Akta 342")
            _add_sop("UIP-APPPB-02-16", "Pemeriksaan sanitasi vektor pada pesawat udara S.7(1) Akta 342")

        if re.search(
            r"\b(?:10\(2\)|notifikasi.*penyakit|gagal\s+buat\s+notifikasi|gagal\s+notifikasi|22\(c\)|22\(d\)|"
            r"kompaun.*akta\s*342|kompaun.*342|sop\s+kompaun.*342|uip-apppb-01-21)(?=\W|$)",
            q_low,
        ):
            _add_act("Akta 342")
            _add_sop("UIP-APPPB-01-21", "Prosedur mengkompaun kesalahan S.10(2), 22(c), 22(d) Akta 342")

        # Peraturan 6: Akta Makanan 1983 (Geledah & Kompaun S.32B Makanan Sahaja)
        has_geledah = bool(
            re.search(r"\b(?:geledah|menggeledah|waran\s+geledah|uip-umum-02-24|uip-umum-03-24)(?=\W|$)", q_low)
            and (
                not melibatkan_852
                or re.search(r"\b(?:akta\s*281|akta\s+makanan|makanan|uip-umum-02-24|uip-umum-03-24)\b", q_low)
            )
        )
        if has_geledah:
            _add_act("Akta 281")
            _add_act("Akta 593")
            ask_diff = bool(re.search(r"\b(?:beza|perbezaan|banding|kedua-dua)(?=\W|$)", q_low))
            tanpa_waran = bool(re.search(r"\b(?:tanpa\s+waran|uip-umum-02-24|alihkan\s+barang|seksyen\s+62)(?=\W|$)", q_low))
            dengan_waran = bool(
                re.search(r"\b(?:dengan\s+waran|mohon\s+waran|permohonan\s+waran|waran\s+geledah|majistret|seksyen\s+54|uip-umum-03-24)(?=\W|$)", q_low)
                and not tanpa_waran
            )
            if ask_diff:
                _add_sop("UIP-UMUM-02-24", "Geledah tanpa waran Akta Makanan 1983")
                _add_sop("UIP-UMUM-03-24", "Geledah dengan waran Majistret Akta Makanan 1983")
            elif tanpa_waran:
                _add_sop("UIP-UMUM-02-24", "Geledah tanpa waran di bawah Akta Makanan 1983 (S.4(1)(b) & S.62/64 KTJ)")
            elif dengan_waran:
                _add_sop("UIP-UMUM-03-24", "Geledah dengan waran Majistret di bawah Akta Makanan 1983 (S.54 KTJ)")
            else:
                _add_sop("UIP-UMUM-02-24", "Geledah tanpa waran Akta Makanan 1983")
                _add_sop("UIP-UMUM-03-24", "Geledah dengan waran Majistret Akta Makanan 1983")

        # UIP-UMUM-04-24: Kompaun Akta Makanan 1983 / PPKM 2009 / PPM 1985 (HANYA makanan, bukan produk merokok)
        if not melibatkan_852 and (
            "uip-umum-04-24" in q_low
            or (
                re.search(r"\b(?:kompaun|notis\s+32b|seksyen\s+32b|s\.?32b|seksyen\s+33)\b", q_low)
                and re.search(r"\b(?:akta\s*281|akta\s+makanan|ppkm|ppm\s*1985|kebersihan\s+makanan|pengendali\s+makanan|premis\s+makanan|tifoid|apron)\b", q_low)
            )
        ):
            _add_act("Akta 281")
            _add_sop("UIP-UMUM-04-24", "Prosedur pengeluaran Notis S.32B & kompaun Akta Makanan 1983 (PPKM 2009 / PPM 1985)")

        # SOP UMUM lain (BWC, Fotografi Forensik, Serahan Saman, Pendakwaan, Kertas Siasatan, Ops Bersepadu, Gubal Akta, Eksibit, Risikan)
        if re.search(r"\b(?:kamera\s+badan|body\s+worn\s+camera|bodycam|bwc|uip-umum-01-22|uip-umum-01-23|rename.*video|video.*rename)(?=\W|$)", q_low):
            _add_act("Akta 56")
            _add_sop("UIP-UMUM-01-22", "Prosedur penggunaan Kamera Badan (BWC) & Perakuan S.90A(2)")
        if re.search(r"\b(?:fotografi\s+forensik|ambil\s+gambar|mengambil\s+gambar|tangkap\s+gambar|gambar\s+forensik|gambar\s+digital|dslr|overview.*fokus|uip-umum-04-07)(?=\W|$)", q_low):
            _add_act("Akta 56")
            _add_sop("UIP-UMUM-04-07", "Prosedur mengambil gambar forensik & Perakuan S.90A(2) Lampiran C")
        if re.search(r"\b(?:serah\s+saman|serahan\s+saman|penyerah\s+saman|penyampaian\s+gantian|borang\s+252|afidavit\s+saman|seksyen\s+36\s+ktj|3\s+kali.*oks|oks\s+enggan\s+terima|uip-umum-03-07)(?=\W|$)", q_low):
            _add_act("Akta 593")
            _add_sop("UIP-UMUM-03-07", "Prosedur penyerahan saman & penyampaian gantian (S.34–37 KTJ)")
        if re.search(r"\b(?:mengaku\s+(?:tidak\s+)?bersalah|mengaku\s+salah|pra\s+perbicaraan|sapina\s+saksi|172a|51a|pendakwaan\s+di\s+mahkamah|selepas\s+penghakiman|uip-umum-05-07)(?=\W|$)", q_low):
            _add_act("Akta 593")
            _add_sop("UIP-UMUM-05-07", "Prosedur pendakwaan di mahkamah (Pra-Perbicaraan S.172A, S.51A, sapina & rayuan)")
        if re.search(r"\b(?:kertas\s+siasatan|susun\s+fail|buka\s+ip|meminit|minit\s+kertas|folio\s+[abcd]|senarai\s+semak\s+k/?s|diari\s+siasatan|uip-umum-02-07)(?=\W|$)", q_low):
            _add_act("Akta 593")
            _add_sop("UIP-UMUM-02-07", "Prosedur penyediaan, minit & senarai semak Kertas Siasatan (Lampiran A–F)")
        if re.search(r"\b(?:operasi\s+bersepadu|ops\s+bersepadu|antara\s+daerah|antara\s+negeri|uip-umum-01-16)(?=\W|$)", q_low):
            _add_sop("UIP-UMUM-01-16", "Prosedur operasi bersepadu penguatkuasaan kesihatan awam")
        if re.search(r"\b(?:gubal\s+akta|penggubalan\s+undang|kertas\s+jemaah\s+menteri|seranta\s+awam|uip-umum-01-07)(?=\W|$)", q_low):
            _add_sop("UIP-UMUM-01-07", "Prosedur penggubalan undang-undang kesihatan awam")
        if re.search(r"\b(?:pengurusan\s+eksibit|stor\s+barang\s+kes|bilik\s+eksibit|daftar\s+barang\s+kes|pelupusan\s+eksibit|rantaian\s+eksibit|uip-umum-05-24)(?=\W|$)", q_low):
            _add_sop("UIP-UMUM-05-24", "Prosedur pengurusan eksibit dan stor barang kes UIP")
        if re.search(r"\b(?:risikan|unit\s+risikan|maklumat\s+risikan|intipan|operasi\s+risikan|uip-umum-06-24)(?=\W|$)", q_low):
            _add_sop("UIP-UMUM-06-24", "Prosedur risikan undang-undang kesihatan awam")

        # Fallback berasaskan indeks aktif (`sop_index_active_router.json`) jika tiada peraturan langsung yang sepadan
        if not selected:
            scored_idx: List[tuple[int, dict]] = []
            for rec in self.active_index:
                if melibatkan_852 and not (str(rec.get("file_stem") or "").startswith(("UIP-AKPMDKA-", "UIP-UMUM-"))):
                    continue
                hits = 0
                for kw in rec.get("kata_kunci") or []:
                    kw_low = str(kw).strip().lower()
                    if len(kw_low) >= 4 and kw_low in q_low:
                        hits += 2
                for sk in rec.get("seksyen_kunci") or []:
                    sk_low = str(sk).strip().lower()
                    if len(sk_low) >= 4 and sk_low in q_low:
                        hits += 3
                if hits >= 3:
                    scored_idx.append((hits, rec))
            scored_idx.sort(key=lambda x: x[0], reverse=True)
            for _sc, rec in scored_idx[:2]:
                _add_sop(rec["sop_id"], f"Padanan indeks aktif: {rec.get('tajuk', '')}")

        # Padankan akta tambahan dari teks soalan
        if re.search(r"\b(?:akta\s*281|akta\s+makanan|ppkm\s*2009|ppm\s*1985|restoran|premis\s+makanan|kilang\s+makanan)(?=\W|$)", q_low):
            _add_act("Akta 281")
        if re.search(r"\b(?:akta\s*342|apppb|penyakit\s+berjangkit|tibi|hfmd|covid|wabak)(?=\W|$)", q_low):
            _add_act("Akta 342")
        if re.search(r"\b(?:akta\s*154|apspp|aedes|denggi|jentik)(?=\W|$)", q_low):
            _add_act("Akta 154")
        if re.search(r"\b(?:akta\s*574|kanun\s+keseksaan)(?=\W|$)", q_low):
            _add_act("Akta 574")
        if re.search(r"\b(?:akta\s*593|ktj|kanun\s+tatacara\s+jenayah)(?=\W|$)", q_low):
            _add_act("Akta 593")
        if re.search(r"\b(?:akta\s*344|akta\s+polis)(?=\W|$)", q_low):
            _add_act("Akta 344")
        if re.search(r"\b(?:akta\s*388|akta\s+tafsiran)(?=\W|$)", q_low):
            _add_act("Akta 388")
        if re.search(r"\b(?:akta\s*92|mahkamah\s+rendah|mahkamah\s+sesyen|mahkamah\s+majistret)(?=\W|$)", q_low):
            _add_act("Akta 92")
        if re.search(r"\b(?:akta\s*56|90a|akta\s+keterangan)(?=\W|$)", q_low):
            _add_act("Akta 56")

        # Bagi kes Akta 852 TULEN (tanpa akta KKM lain seperti Akta 342/154 dalam soalan berbilang akta),
        # kekalkan hanya SOP rasmi Akta 852 (`UIP-AKPMDKA-*`) & `UIP-UMUM-*` (SIFAR PPKHT).
        has_other_kkm_sop_trigger = any(
            a in akta_terlibat for a in ("Akta 342", "Akta 154")
        )
        if melibatkan_852 and not has_other_kkm_sop_trigger:
            selected = [s for s in selected if s.startswith(("UIP-AKPMDKA-", "UIP-UMUM-"))]

        sebab = (
            "; ".join(reasons[:3])
            if reasons
            else (
                "Kes melibatkan Akta 852 (PPKHT 2004 telah mansuh mulai 1 Okt 2024); rujuk teks Akta 852 & SOP rasmi UIP-AKPMDKA-01-24..08-24."
                if melibatkan_852
                else "Tiada SOP khusus yang sepadan secara langsung; rujuk teks Statut terkini yang disahkan."
            )
        )

        return self._sanitize_route_decision(
            RouteDecision(
                akta_terlibat=akta_terlibat or ["Akta Kesihatan Awam KKM"],
                selected_sop_ids=selected[:3],
                melibatkan_akta_852=melibatkan_852,
                sebab_pilihan=sebab,
                amaran_statut_mansuh=" | ".join(amaran_list) if amaran_list else None,
            )
        )

    def route_question(self, soalan: str, allow_local_fallback: bool = True) -> RouteDecision:
        """Peringkat 1: Kenal pasti Akta & 0-3 SOP aktif tanpa halusinasi (`temperature=0.0`)."""
        client = self.client
        if client is None or types is None:
            if allow_local_fallback:
                return self.route_question_deterministic(soalan)
            raise RuntimeError("GEMINI_API_KEY tidak dikonfigurasi untuk Stage 1 Router Gemini.")

        index_str = json.dumps(self.active_index, ensure_ascii=False)
        prompt = (
            f"INDEKS SOP AKTIF ({len(self.active_index)} SOP KKM AKTIF 2024):\n{index_str}\n\n"
            f"SOALAN PENGGUNA:\n{soalan}"
        )

        last_exc: Optional[Exception] = None
        for model_name in self._candidate_models(self.router_model, role="router"):
            try:
                resp = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=ROUTER_SYSTEM_PROMPT,
                        temperature=0.0,
                        response_mime_type="application/json",
                        response_schema=RouteDecision,
                    ),
                )
                decision = RouteDecision.model_validate_json(resp.text)
                return self._sanitize_route_decision(decision)
            except Exception as exc:
                last_exc = exc
                logger.warning("Stage 1 Router gagal pada model %s: %s", model_name, str(exc)[:160])
                continue

        if allow_local_fallback:
            logger.warning("Stage 1 Router beralih ke penghala deterministik tempatan selepas ralat: %s", last_exc)
            return self.route_question_deterministic(soalan)
        raise RuntimeError(f"Stage 1 Router Gemini gagal: {last_exc}")

    def load_full_sops(self, sop_ids: List[str], max_sops: int = 3) -> str:
        """Muatkan teks penuh Markdown bagi SOP aktif yang dipilih (tanpa chunking pecah; blok PPKHT)."""
        loaded_blocks: List[str] = []
        seen_stems: set[str] = set()

        for raw_id in sop_ids[:max_sops]:
            up = str(raw_id or "").strip().upper()
            if not up or "PPKHT" in up:
                continue
            rec = self._sop_lookup.get(up) or self._sop_lookup.get(up.split(" ")[0].strip())
            if not rec:
                continue
            stem = str(rec["file_stem"])
            if stem in seen_stems:
                continue
            seen_stems.add(stem)
            md_path = _resolve_active_md_path(self.sop_data_dir, str(rec.get("fail_md") or ""))
            if md_path and md_path.exists():
                content = md_path.read_text(encoding="utf-8")
                loaded_blocks.append(f'<SOP id="{rec["sop_id"]}">\n{content}\n</SOP>')

        if not loaded_blocks:
            return (
                "<TIADA_SOP_KHUSUS>\n"
                "Tiada SOP KKM khusus yang aktif dalam koleksi SOP Pindaan 15 Februari 2024 bagi soalan ini. "
                "Rujuk teks Statut terkini yang dibekalkan dan nyatakan ketiadaan SOP khusus secara telus.\n"
                "</TIADA_SOP_KHUSUS>"
            )
        return "\n\n".join(loaded_blocks)

    def get_pekeliling_rujukan(self) -> List[Dict[str, Any]]:
        """Pulangkan senarai pekeliling rujukan tambahan (cth: Pekeliling KPK Bil 18/2024)."""
        return list(self._pekeliling_rujukan)

    @staticmethod
    def _clean_markdown_body(raw_md: str) -> str:
        """Buang blok YAML frontmatter dan penanda halaman teknikal berlebihan untuk bacaan bersih."""
        txt = raw_md or ""
        if txt.startswith("---"):
            parts = txt.split("---", 2)
            if len(parts) == 3:
                txt = parts[2].lstrip("\r\n")
        return txt.strip()

    def get_sop_summaries(self, sop_ids: List[str]) -> List[Dict[str, Any]]:
        """Pulangkan ringkasan berstruktur SOP aktif yang dipilih (untuk paparan UI & metadata jawapan)."""
        out: List[Dict[str, Any]] = []
        seen: set[str] = set()
        for raw_id in sop_ids:
            up = str(raw_id or "").strip().upper()
            if not up or "PPKHT" in up:
                continue
            rec = self._sop_lookup.get(up) or self._sop_lookup.get(up.split(" ")[0].strip())
            if not rec:
                continue
            sid = str(rec["sop_id"])
            if sid in seen:
                continue
            seen.add(sid)
            stem = str(rec.get("file_stem") or "")
            stem_up = stem.upper()
            kat = str(rec.get("kategori") or "").strip()
            struct = self._structured_by_stem.get(stem_up) or {}
            akta_list = list(rec.get("akta_berkaitan") or struct.get("akta_berkaitan") or [])
            seksyen_list = list(rec.get("seksyen_kunci") or [])
            lampiran_list = list(rec.get("lampiran_ringkas") or [])
            if not lampiran_list and struct.get("lampiran"):
                lampiran_list = [
                    f"{lp.get('kod', '')}: {lp.get('tajuk', '')}".strip(": ")
                    for lp in (struct.get("lampiran") or [])
                ]
            kata_kunci_list = list(rec.get("kata_kunci") or [])
            toc_alias = rec.get("toc_id_alias")
            akta_label = (
                "Akta 852 (Produk Merokok)"
                if ("AKPMDKA" in kat.upper() or stem_up.startswith("UIP-AKPMDKA-"))
                else "Akta 154 (APSPP)"
                if "APSPP" in kat.upper()
                else "Akta 342 (APPPB)"
                if "APPPB" in kat.upper()
                else "Akta 281 (Akta Makanan)"
                if (
                    "AKM" in kat.upper()
                    or "MAKANAN" in kat.upper()
                    or stem_up in ("UIP-UMUM-02-24", "UIP-UMUM-03-24", "UIP-UMUM-04-24")
                )
                else "SOP Umum / KTJ"
                if kat.upper() == "UMUM"
                else (akta_list[0] if akta_list else kat or "SOP KKM 2024")
            )
            ringkasan_str = (
                str(struct.get("ringkasan_eksekutif") or "").strip()
                or ("; ".join(str(s) for s in seksyen_list[:4]) if seksyen_list else str(rec.get("tajuk") or ""))
            )
            amaran_konflik = (
                f"Nota Konflik Kod Cetakan: Jadual Kandungan mencetak '{toc_alias}', namun kod rasmi dalam teks SOP ialah '{sid}'."
                if toc_alias
                else None
            )
            nota_pindaan_list = list(struct.get("nota_pindaan") or [])
            tempoh_sla_list = list(struct.get("tempoh_sla") or [])
            anggota_list = list(struct.get("anggota_terlibat") or [])
            bil_langkah = sum(len(ph.get("langkah") or []) for ph in (struct.get("fasa_kerja") or []))
            bil_lampiran = len(struct.get("lampiran") or lampiran_list)
            tarikh_kk = str(
                struct.get("tarikh_kuatkuasa")
                or ("01 Okt 2024" if stem_up.startswith("UIP-AKPMDKA-") else "15 Feb 2024")
            )
            pindaan_no = str(struct.get("pindaan") or ("01" if "PINDAAN" in sid.upper() else "00"))
            out.append(
                {
                    "sop_id": sid,
                    "file_stem": stem,
                    "tajuk": rec.get("tajuk", ""),
                    "kategori": kat,
                    "akta": akta_label,
                    "akta_berkaitan": akta_list,
                    "seksyen_kunci": seksyen_list,
                    "kata_kunci": kata_kunci_list,
                    "lampiran_ringkas": lampiran_list,
                    "borang_lampiran": lampiran_list,
                    "ringkasan": ringkasan_str,
                    "tujuan_ringkas": str(struct.get("tujuan") or ringkasan_str)[:260],
                    "punca_kuasa": str(struct.get("punca_kuasa") or ("; ".join(seksyen_list[:3]) if seksyen_list else "")),
                    "rujukan_silang": list(rec.get("rujukan_silang") or []),
                    "muka_surat_pdf": self._pdf_pages_by_stem.get(stem_up, ""),
                    "toc_id_alias": toc_alias,
                    "tarikh_kuat_kuasa": tarikh_kk,
                    "pindaan": pindaan_no,
                    "status_sop": "AKTIF",
                    "amaran_konflik_kod": amaran_konflik,
                    "has_nota_pindaan": len(nota_pindaan_list) > 0,
                    "nota_pindaan_ringkas": str(nota_pindaan_list[0].get("tajuk") or "") if nota_pindaan_list else None,
                    "nota_pindaan_tahap": str(nota_pindaan_list[0].get("tahap") or "") if nota_pindaan_list else None,
                    "tempoh_sla_ringkas": [
                        f"{t.get('label', '')}: {t.get('tempoh', '')}".strip(": ")
                        for t in tempoh_sla_list[:3]
                    ],
                    "peranan_utama": [str(a.get("kod") or "") for a in anggota_list[:6] if a.get("kod")],
                    "bil_langkah": bil_langkah,
                    "bil_lampiran": bil_lampiran,
                    "structured_ready": bool(struct),
                    "nota_audit": struct.get("nota_audit_kualiti"),
                }
            )
        return out

    def list_all_active_sops(
        self,
        q: Optional[str] = None,
        akta_filter: Optional[str] = None,
        kategori: Optional[str] = None,
        ada_pindaan: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        """Pulangkan senarai lengkap kesemua SOP aktif untuk Direktori SOP KKM 2024 (sifar SOP mansuh)
        dengan sokongan penapisan Akta/Kategori/Nota Pindaan dan carian teks penuh langkah & lampiran."""
        items = self.get_sop_summaries([str(r.get("sop_id") or "") for r in self.active_index])
        if akta_filter and akta_filter.strip() and akta_filter.strip().lower() != "semua":
            af = akta_filter.strip().lower()
            items = [
                it
                for it in items
                if af in str(it.get("akta") or "").lower()
                or af in str(it.get("kategori") or "").lower()
                or af in str(it.get("sop_id") or "").lower()
                or any(af in str(a).lower() for a in (it.get("akta_berkaitan") or []))
            ]
        if kategori and kategori.strip() and kategori.strip().lower() != "semua":
            kf = kategori.strip().lower()
            items = [it for it in items if kf in str(it.get("kategori") or "").lower()]
        if ada_pindaan is not None:
            items = [it for it in items if bool(it.get("has_nota_pindaan")) == bool(ada_pindaan)]
        if q and q.strip():
            ql = q.strip().lower()
            matched_items: List[Dict[str, Any]] = []
            for it in items:
                stem_up = str(it.get("file_stem") or "").upper()
                meta_hit = (
                    ql in str(it.get("sop_id") or "").lower()
                    or ql in stem_up.lower()
                    or ql in str(it.get("tajuk") or "").lower()
                    or ql in str(it.get("ringkasan") or "").lower()
                    or ql in str(it.get("tujuan_ringkas") or "").lower()
                    or ql in str(it.get("akta") or "").lower()
                    or any(ql in str(k).lower() for k in (it.get("kata_kunci") or []))
                    or any(ql in str(k).lower() for k in (it.get("seksyen_kunci") or []))
                    or any(ql in str(k).lower() for k in (it.get("lampiran_ringkas") or []))
                )
                blob = self._search_blob_by_stem.get(stem_up, "")
                blob_idx = blob.lower().find(ql) if blob else -1
                if meta_hit or blob_idx >= 0:
                    enriched = dict(it)
                    if blob_idx >= 0:
                        start = max(0, blob_idx - 55)
                        end = min(len(blob), blob_idx + len(ql) + 95)
                        snippet = blob[start:end].strip()
                        if start > 0:
                            snippet = "…" + snippet
                        if end < len(blob):
                            snippet = snippet + "…"
                        enriched["match_snippet"] = snippet
                    matched_items.append(enriched)
            items = matched_items
        return items

    def get_sop_markdown(self, file_stem_or_id: str) -> Optional[Dict[str, Any]]:
        """Pulangkan kandungan penuh Markdown + struktur v2 JSON bagi satu SOP aktif (menyekat keras PPKHT)."""
        up = (file_stem_or_id or "").strip().upper()
        if not up or "PPKHT" in up:
            return None
        rec = self._sop_lookup.get(up) or self._sop_lookup.get(up.split(" ")[0].strip())
        if not rec:
            return None
        md_path = _resolve_active_md_path(self.sop_data_dir, str(rec.get("fail_md") or ""))
        if not md_path or not md_path.exists():
            return None
        summary = self.get_sop_summaries([str(rec["sop_id"])])[0]
        raw_md = md_path.read_text(encoding="utf-8")
        stem_up = str(rec.get("file_stem") or "").upper()
        return {
            **summary,
            "markdown_content": raw_md,
            "cleaned_markdown": self._clean_markdown_body(raw_md),
            "structured": self._structured_by_stem.get(stem_up),
        }

    def tanya_pakar_uip(
        self,
        soalan: str,
        konteks_statut_tambahan: str = "",
        guna_cache: Optional[bool] = None,
        akta_hint: str = "Semua",
    ) -> dict:
        """Jawapan lengkap dua peringkat (Full-SOP Injection atau Context Cache) dengan `temperature=0.0`
        serta pengesahan pasca-penjanaan `validate_legal_output()`."""
        if guna_cache is None:
            try:
                from backend.core.config import settings as _settings

                guna_cache = bool(_settings.sop_brain_use_context_cache)
            except Exception:
                guna_cache = False

        route = self.route_question(soalan, allow_local_fallback=True)

        effective_statut = (konteks_statut_tambahan or "").strip()
        if not effective_statut:
            effective_statut = build_statutory_context_for_question(soalan, akta_hint=akta_hint)

        statut_block = ""
        if effective_statut:
            statut_block = (
                f"\n\n<STATUT_TERKINI_DISAHKAN>\n{effective_statut}\n</STATUT_TERKINI_DISAHKAN>"
            )

        nota_akta_852 = ""
        if route.melibatkan_akta_852:
            nota_akta_852 = (
                "\n[PERINGATAN SISTEM: Kes ini melibatkan produk merokok/vape/OBD. "
                "PPKHT 2004 telah MANSUH sejak 1 Oktober 2024. WAJIB guna Akta 852 sahaja.]"
            )

        client = self.client
        if client is None or types is None:
            raise RuntimeError("GEMINI_API_KEY tidak dikonfigurasi untuk Peringkat 2 Jawapan Pakar UIP.")

        used_model = self.answer_model
        resp_text = ""
        used_cache_mode = False

        if guna_cache:
            try:
                cache_name = self.ensure_context_cache()
                user_payload = (
                    f"KEPUTUSAN ROUTER: Akta={route.akta_terlibat} | SOP Disyorkan={route.selected_sop_ids}"
                    f"{nota_akta_852}{statut_block}\n\nSOALAN PENGGUNA:\n{soalan}"
                )
                resp = client.models.generate_content(
                    model=self.answer_model,
                    contents=user_payload,
                    config=types.GenerateContentConfig(
                        cached_content=cache_name,
                        temperature=0.0,
                    ),
                )
                resp_text = resp.text or ""
                used_cache_mode = bool(resp_text)
            except Exception as cache_exc:
                logger.warning("Context Cache tamat tempoh/gagal, beralih ke Full-SOP Injection: %s", str(cache_exc)[:160])
                self._active_cache_name = None
                self._active_cache_expires_at = 0.0

        if not resp_text:
            full_sops_xml = self.load_full_sops(route.selected_sop_ids)
            user_payload = (
                f"DOKUMEN SOP KKM PENUH YANG DISUNTIK:\n{full_sops_xml}"
                f"{statut_block}{nota_akta_852}\n\n"
                f"KEPUTUSAN ROUTER: Akta={route.akta_terlibat} | Sebab={route.sebab_pilihan}\n\n"
                f"SOALAN PENGGUNA:\n{soalan}"
            )
            last_exc: Optional[Exception] = None
            for model_name in self._candidate_models(self.answer_model, role="answer"):
                try:
                    resp = client.models.generate_content(
                        model=model_name,
                        contents=user_payload,
                        config=types.GenerateContentConfig(
                            system_instruction=PAKAR_UIP_SYSTEM_PROMPT,
                            temperature=0.0,
                        ),
                    )
                    resp_text = resp.text or ""
                    used_model = model_name
                    break
                except Exception as exc:
                    last_exc = exc
                    logger.warning("Stage 2 Pakar UIP gagal pada model %s: %s", model_name, str(exc)[:160])
                    continue
            if not resp_text and last_exc is not None:
                raise RuntimeError(f"Peringkat 2 Pakar UIP gagal: {last_exc}")

        # Pengesahan Pasca-Penjanaan Wajib (`validate_legal_output`) + 1x Self-Correction (temperature=0.0)
        legal_validation = None
        try:
            from backend.rag.legal_engine import get_legal_library, validate_legal_output

            snap = get_legal_library().to_snapshot_dict()
            legal_validation = validate_legal_output(
                {"akta_disyorkan": ", ".join(route.akta_terlibat), "jawapan_4_lapisan_sop": resp_text},
                snap,
                question_context=soalan,
            )
            if not legal_validation.get("passed"):
                retry_base = user_payload
                if used_cache_mode:
                    retry_sops_xml = self.load_full_sops(route.selected_sop_ids)
                    retry_base = f"DOKUMEN SOP KKM PENUH YANG DISUNTIK:\n{retry_sops_xml}\n\n{user_payload}"
                retry_payload = (
                    f"{retry_base}\n\n"
                    f"AMARAN PENGESAH SISTEM (SILA BETULKAN SERTA-MERTA):\n{legal_validation.get('warning_banner', '')}\n"
                    "Buang semua seksyen/subseksyen/kod SOP tidak wujud atau mansuh dan ulang jawapan 4 lapisan yang tepat."
                )
                try:
                    retry_resp = client.models.generate_content(
                        model=used_model,
                        contents=retry_payload,
                        config=types.GenerateContentConfig(
                            system_instruction=PAKAR_UIP_SYSTEM_PROMPT,
                            temperature=0.0,
                        ),
                    )
                    if retry_resp.text:
                        resp_text = retry_resp.text
                        legal_validation = validate_legal_output(
                            {"akta_disyorkan": ", ".join(route.akta_terlibat), "jawapan_4_lapisan_sop": resp_text},
                            snap,
                            question_context=soalan,
                        )
                except Exception as retry_exc:
                    logger.warning("Self-correction SOP Brain gagal: %s", str(retry_exc)[:140])
        except Exception as val_exc:
            logger.warning("Pengesahan pasca-penjanaan SOP Brain dilangkau: %s", val_exc)

        return {
            "jawapan": resp_text,
            "routing": route.model_dump(),
            "sop_references": self.get_sop_summaries(route.selected_sop_ids),
            "mod": "context_cache" if used_cache_mode else "two_stage_full_sop",
            "model_used": used_model,
            "statut_disuntik": bool(effective_statut),
            "legal_validation": legal_validation,
        }

    def audit_kertas_siasatan(
        self,
        teks_draf_ks: str,
        akta_kes: str,
        konteks_statut_tambahan: str = "",
    ) -> str:
        """Audit draf K/S berdasarkan `AUDIT_PRA_TPR_SYSTEM_PROMPT`, `UIP-UMUM-02-07`, `UIP-UMUM-04-07` & SOP akta (`temperature=0.0`)."""
        client = self.client
        if client is None or types is None:
            raise RuntimeError("GEMINI_API_KEY tidak dikonfigurasi untuk Audit Pra-TPR Gemini.")

        route = self.route_question(f"Audit Kertas Siasatan bagi {akta_kes}: {teks_draf_ks[:500]}")
        wajib_sops = ["UIP-UMUM-02-07", "UIP-UMUM-04-07"] + route.selected_sop_ids
        full_sops_xml = self.load_full_sops(wajib_sops, max_sops=4)

        statut_block = ""
        if (konteks_statut_tambahan or "").strip():
            statut_block = (
                f"\n\n<STATUT_TERKINI_DISAHKAN>\n{konteks_statut_tambahan.strip()}\n</STATUT_TERKINI_DISAHKAN>"
            )

        prompt = (
            f"RUJUKAN SOP RASMI:\n{full_sops_xml}"
            f"{statut_block}\n\n"
            f"AKTA KES: {akta_kes}\n\n"
            f"DRAF KERTAS SIASATAN / NOTIS UNTUK DIAUDIT:\n{teks_draf_ks}"
        )
        last_exc: Optional[Exception] = None
        for model_name in self._candidate_models(self.answer_model, role="answer"):
            try:
                resp = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=AUDIT_PRA_TPR_SYSTEM_PROMPT,
                        temperature=0.0,
                    ),
                )
                return resp.text or ""
            except Exception as exc:
                last_exc = exc
                logger.warning("Audit Pra-TPR gagal pada model %s: %s", model_name, str(exc)[:160])
                continue
        raise RuntimeError(f"Audit Pra-TPR Gemini gagal: {last_exc}")

    def audit_kertas_siasatan_structured(
        self,
        teks_draf_ks_redacted: str,
        akta_kes: str,
        konteks_statut_tambahan: str = "",
        use_ai: bool = True,
    ) -> Dict[str, Any]:
        """Menjalankan semakan SOP KKM Pra-TPR berstruktur (`UIP-UMUM-02-07` + `UIP-UMUM-04-07` + SOP Akta)
        dengan pemeriksaan deterministik serta ulasan AI `AUDIT_PRA_TPR_SYSTEM_PROMPT` (jika aktif)."""
        low = (teks_draf_ks_redacted or "").lower()
        akta_norm = (akta_kes or "Akta 852").strip()
        if "ppkm" in low and "281" in akta_norm:
            lamp_key = "PPKM 2009"
        elif "ppm 1985" in low or "peraturan-peraturan makanan 1985" in low:
            lamp_key = "PPM 1985"
        elif "852" in akta_norm:
            lamp_key = "Akta 852"
        elif "154" in akta_norm:
            lamp_key = "Akta 154"
        elif "342" in akta_norm:
            lamp_key = "Akta 342"
        elif "281" in akta_norm:
            lamp_key = "Akta 281"
        else:
            lamp_key = akta_norm

        lamp_info = LAMPIRAN_KS_BY_ACT.get(
            lamp_key,
            {
                "lampiran": "Folio A–D (UIP-UMUM-02-07)",
                "butiran": f"Senarai Semak Penyediaan Kertas Siasatan mengikut UIP-UMUM-02-07 (PINDAAN 2024) bagi {akta_norm}.",
            },
        )

        # Pilih SOP wajib + SOP khusus akta
        if use_ai and self.has_api_key:
            route = self.route_question(f"Audit Kertas Siasatan bagi {akta_norm}: {teks_draf_ks_redacted[:500]}")
        else:
            route = self.route_question_deterministic(f"Audit Kertas Siasatan bagi {akta_norm}: {teks_draf_ks_redacted[:800]}")

        wajib_ids = ["UIP-UMUM-02-07 (PINDAAN 2024)", "UIP-UMUM-04-07 (PINDAAN 2024)"]
        for sid in route.selected_sop_ids:
            if sid not in wajib_ids and len(wajib_ids) < 4:
                wajib_ids.append(sid)

        dapatan_sop: List[Dict[str, str]] = []

        # 1. Kesahan Statut (Sekatan PPKHT 2004 / Notis 32B bagi kes merokok/vape)
        is_smoking_case = bool(
            "852" in akta_norm
            or re.search(r"\b(?:vape|rokok|merokok|shisha|obd|produk\s+merokok)\b", low)
        )
        if is_smoking_case and re.search(r"\b(?:ppkht\s*2004|peraturan\s+(?:8|9|11|13)\s+ppkht|borang\s+4.*23\(2\)|seksyen\s+32b\s+akta\s+makanan)(?=\W|$)", low):
            dapatan_sop.append(
                {
                    "kategori": "Kesahan Statut [NOTA PINDAAN]",
                    "status": "[KRITIKAL - RISIKO K/S DITOLAK TPR]",
                    "rujukan_sop": "UIP-UMUM-02-07 (PINDAAN 2024) — Nota Audit Lampiran C",
                    "perincian": (
                        "Draf K/S memetik PPKHT 2004 atau Notis Seksyen 32B Akta Makanan 1983 bagi kes produk merokok/vape. "
                        "PPKHT 2004 telah MANSUH sejak 1 Oktober 2024 — wajib pinda sepenuhnya kepada Akta 852 & Notis S.47."
                    ),
                }
            )
        else:
            dapatan_sop.append(
                {
                    "kategori": "Kesahan Statut",
                    "status": "[LULUS]",
                    "rujukan_sop": "UIP-UMUM-02-07 (PINDAAN 2024)",
                    "perincian": f"Tiada rujukan statut mansuh PPKHT 2004 dikesan dalam draf K/S ({akta_norm}).",
                }
            )

        # 2. Kelengkapan Folio & Senarai Semak K/S (Lampiran A–F)
        dapatan_sop.append(
            {
                "kategori": "Senarai Semak K/S (Lampiran Rasmi)",
                "status": "[NOTA PINDAAN]" if "852" in akta_norm else "[LULUS]",
                "rujukan_sop": lamp_info["lampiran"],
                "perincian": lamp_info["butiran"],
            }
        )

        # 3. Rantaian Bahan Bukti, S.90A & BWC
        has_bwc = bool(re.search(r"\b(?:bwc|kamera\s+badan|body\s+worn\s+camera|bodycam)\b", low))
        if has_bwc:
            bwc_renamed = bool(re.search(r"\b(?:rename|di-rename|dinamakan\s+semula|tukar\s+nama\s+fail|edit\s+video|sunting\s+video)\b", low))
            dapatan_sop.append(
                {
                    "kategori": "Kamera Badan (BWC) & S.90A(2)",
                    "status": "[KRITIKAL - RISIKO K/S DITOLAK TPR]" if bwc_renamed else "[LULUS]",
                    "rujukan_sop": "UIP-UMUM-01-22 (PINDAAN 2024) — Lampiran 2",
                    "perincian": (
                        "Fail rakaman BWC DILARANG dinamakan semula (rename) atau disunting; pastikan Perakuan S.90A(2) Lampiran 2 dilampirkan."
                        if bwc_renamed
                        else "Pastikan Perakuan Seksyen 90A(2) (Lampiran 2, UIP-UMUM-01-22) dilampirkan dan fail asal BWC tidak diubah atau dinamakan semula."
                    ),
                }
            )

        has_90a = bool(re.search(r"\b(?:90a|sijil\s+seksyen\s+90a|perakuan\s+seksyen\s+90a)\b", low))
        neg_90a = bool(re.search(r"\b(?:tiada\s+sijil\s+(?:seksyen\s+)?90a|tanpa\s+sijil\s+90a|90a\s+(?:belum|tidak)\s+(?:disediakan|dilampirkan|ditandatangani))\b", low))
        dapatan_sop.append(
            {
                "kategori": "Fotografi Forensik & Perakuan S.90A(2)",
                "status": "[KRITIKAL - RISIKO K/S DITOLAK TPR]" if (neg_90a or not has_90a) else "[LULUS]",
                "rujukan_sop": "UIP-UMUM-04-07 (PINDAAN 2024) — Lampiran C",
                "perincian": (
                    "Perakuan Seksyen 90A(2) (Lampiran C, UIP-UMUM-04-07) belum lengkap/tidak dikesan bagi gambar digital/CDR atau cetakan komputer."
                    if (neg_90a or not has_90a)
                    else "Rujukan Perakuan Seksyen 90A(2) dikesan; sahkan kapsyen 3 teknik fotografi (Overview, Fokus, Zoom) & Borang Akuan Serah/Terima Barang Kes."
                ),
            }
        )

        # 4. Peringatan Tempoh Statutori SOP mengikut Akta (berstatus makluman SOP kecuali pelanggaran dikesan)
        if "154" in akta_norm:
            dapatan_sop.append(
                {
                    "kategori": "Tempoh Statutori SOP Akta 154",
                    "status": "[INFO SOP]",
                    "rujukan_sop": "UIP-APSPP-01-07 & UIP-APSPP-02-16 (PINDAAN 2024)",
                    "perincian": (
                        "Sahkan serahan Sampul Kecil ke PPKP UIPD dalam tempoh 3 hari (UIP-APSPP-01-07) "
                        "dan penyediaan tawaran kompaun dalam 21 hari dari tarikh izin TPR (UIP-APSPP-02-16)."
                    ),
                }
            )
        elif "342" in akta_norm:
            dapatan_sop.append(
                {
                    "kategori": "Tempoh Statutori SOP Akta 342",
                    "status": "[INFO SOP]",
                    "rujukan_sop": "UIP-APPPB-01-16 & UIP-APPPB-01-07 (PINDAAN 2024)",
                    "perincian": (
                        "Jika perintah lisan S.15(1) diberikan, perintah bertulis wajib dikeluarkan dalam 24 jam (UIP-APPPB-01-16); "
                        "bagi penutupan S.18(1)(d), tempoh minimum tidak kurang dari 3 hari / 72 jam (UIP-APPPB-01-07)."
                    ),
                }
            )

        ulasan_ai: Optional[str] = None
        mod = "semakan_sop_deterministik"
        if use_ai and self.has_api_key:
            try:
                ulasan_ai = self.audit_kertas_siasatan(
                    teks_draf_ks=teks_draf_ks_redacted,
                    akta_kes=akta_norm,
                    konteks_statut_tambahan=konteks_statut_tambahan,
                )
                mod = "audit_pra_tpr_gemini_temp_0"
            except Exception as exc:
                logger.warning("Ulasan AI Audit Pra-TPR beralih ke semakan SOP deterministik: %s", exc)

        return {
            "mod": mod,
            "lampiran_ks_wajib": lamp_info["lampiran"],
            "butiran_lampiran_ks": lamp_info["butiran"],
            "sops_dirujuk": self.get_sop_summaries(wajib_ids),
            "dapatan_sop": dapatan_sop,
            "ulasan_pra_tpr": ulasan_ai,
        }

    def ensure_context_cache(self, ttl_seconds: int = 3600) -> str:
        """Cipta Gemini Context Cache untuk kesemua SOP aktif dengan pengesanan tamat tempoh TTL (thread-safe)."""
        import time as _time

        with self._client_lock:
            expires_at = float(getattr(self, "_active_cache_expires_at", 0.0) or 0.0)
            if self._active_cache_name and _time.monotonic() < expires_at:
                return self._active_cache_name

            client = self.client
            if client is None or types is None:
                raise RuntimeError("GEMINI_API_KEY tidak dikonfigurasi untuk mencipta Context Cache.")

            bundle_path = self.sop_data_dir / "sop_bundle_aktif_context_cache.txt"
            bundle_text = bundle_path.read_text(encoding="utf-8")

            cache = client.caches.create(
                model=self.answer_model,
                config=types.CreateCachedContentConfig(
                    display_name="i-uip-nerus-sop-kkm-2024-aktif",
                    system_instruction=PAKAR_UIP_SYSTEM_PROMPT,
                    contents=[bundle_text],
                    ttl=f"{ttl_seconds}s",
                ),
            )
            self._active_cache_name = cache.name
            self._active_cache_expires_at = _time.monotonic() + max(60, ttl_seconds - 60)
            return cache.name

    def get_status_summary(self) -> Dict[str, Any]:
        deprecated_dir = self.sop_data_dir / "sops_arkib_deprecated"
        deprecated_count = len(list(deprecated_dir.glob("*.md"))) if deprecated_dir.exists() else 0
        try:
            from backend.core.config import settings as _settings

            cache_flag = bool(_settings.sop_brain_use_context_cache)
        except Exception:
            cache_flag = False
        return {
            "version": "SOP-KKM-2024-v2",
            "active_sops_indexed": len(self.active_index),
            "structured_sops_ready": len(self._structured_by_stem),
            "pekeliling_rujukan_count": len(self._pekeliling_rujukan),
            "deprecated_sops_quarantined": max(deprecated_count, QUARANTINED_PPKHT_SOPS_COUNT),
            "router_model": self.router_model,
            "answer_model": self.answer_model,
            "temperature": 0.0,
            "context_cache_enabled": cache_flag,
        }


_SOP_BRAIN_SINGLETON: Optional[IUIPNerusBrain] = None
_SOP_BRAIN_LOCK = threading.RLock()


def get_sop_brain() -> IUIPNerusBrain:
    global _SOP_BRAIN_SINGLETON
    with _SOP_BRAIN_LOCK:
        if _SOP_BRAIN_SINGLETON is None:
            _SOP_BRAIN_SINGLETON = IUIPNerusBrain(package_root=DEFAULT_PACKAGE_ROOT)
        return _SOP_BRAIN_SINGLETON


if __name__ == "__main__":
    brain = IUIPNerusBrain()
    contoh = (
        "Semasa pemeriksaan tapak bina, didapati ada 5 tempat pembiakan jentik-jentik besar "
        "dan penyelia enggan benarkan kami masuk. Apa tindakan dan borang perlu keluar?"
    )
    hasil = brain.tanya_pakar_uip(contoh)
    print("=== ROUTING ===")
    print(json.dumps(hasil["routing"], indent=2, ensure_ascii=False))
    print("\n=== JAWAPAN PAKAR UIP ===")
    print(hasil["jawapan"])
