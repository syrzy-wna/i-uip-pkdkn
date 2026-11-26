"""Enjin Perundangan Tertutup 2-Lapisan & Pengesah Petikan Deterministik (Zero-Hallucination Legal Engine).

Melaksanakan:
- FASA 1: Skema Pangkalan Data Perundangan 2-Lapisan (`statutes_registry`, `statute_sections_verbatim`,
  `master_offences_matrix`, `repealed_and_blocked_provisions`).
- FASA 2: Saluran Penghuraian PDF Warta Rasmi AGC (`ingest_statute_bytes` / `ingest_statute_file`)
  mengikut sempadan Bahagian, Seksyen, Peraturan, Subseksyen & Jadual + Imbasan Kesalahan Seksyen-demi-Seksyen.
- FASA 3: Enjin Analisis Closed-Book, Semakan Unsur Mandatori & Pengecualian (`evaluate_offence_elements`),
  serta Pengesah Kod Pasca-Penjanaan (`validate_legal_output` / `validateLegalOutput`).
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pymupdf as fitz

from backend.core.config import settings

INITIAL_STATUTE_LIBRARY_VERSION = "2.6.0-closed-book-agc-pdf"
PARSER_VERSION = "3.5-agc-gazette-pdf"

TOKEN_RE = re.compile(r"[a-zA-Z0-9]+")

# Senarai 13 akta/peraturan penguatkuasaan teras untuk sapuan penuh master_offences_matrix
CORE_ENFORCEMENT_SWEEP_STATUTE_IDS: Tuple[str, ...] = (
    "AKTA_852",
    "AKTA_852_PERATURAN_JUALAN_2024",
    "AKTA_852_PERATURAN_TANDA_2024",
    "AKTA_852_PERATURAN_PEMBUNGKUSAN_2024",
    "AKTA_852_PERATURAN_PENDAFTARAN_2024",
    "AKTA_852_PERATURAN_KOMPAUN_2024",
    "AKTA_281",
    "AKTA_281_PINDAAN_2024",
    "PPKM_2009",
    "AKTA_154",
    "AKTA_342",
    "AKTA_342_PINDAAN_2025",
    "AKTA_342_PERATURAN_KOMPAUN_2025",
)

# Pemetaan pautan wajib Akta Induk <-> Akta Pindaan & Peraturan Kompaun Terkini
AMENDMENT_COMPANIONS: Dict[str, Dict[str, Any]] = {
    "AKTA_342": {
        "companion_statute_ids": (
            "AKTA_342_PINDAAN_2025",
            "AKTA_342_PERATURAN_KOMPAUN_2025",
        ),
        "priority_sections": {
            "AKTA_342_PINDAAN_2025": ("24", "25", "22A", "21A", "14A", "15A"),
            "AKTA_342_PERATURAN_KOMPAUN_2025": ("Peraturan 2", "Peraturan 1"),
        },
        "mandatory_directive_bm": (
            "ARAHAN KERAS PINDAAN STATUTORI (AKTA 342 <-> AKTA A1742 & P.U.(A) 139/2025): "
            "Apabila merujuk Akta Pencegahan dan Pengawalan Penyakit Berjangkit 1988 [Akta 342], "
            "ANDA WAJIB MENGUTAMAKAN teks pindaan terkini Akta A1742 (berkuat kuasa 1 Mei 2025) dan kadar kompaun "
            "P.U. (A) 139/2025: Penalti Am Seksyen 24(a) individu maks RM10,000 atau penjara maks 2 tahun atau kedua-duanya "
            "& Seksyen 24(b) pertubuhan perbadanan maks RM100,000; had kompaun Seksyen 25 individu maks RM5,000 / pertubuhan perbadanan maks RM50,000 "
            "HANYA bagi kesalahan Jadual Pertama P.U.(A) 139/2025 dengan keizinan bertulis Pendakwa Raya; Seksyen 22A liabiliti korporat "
            "(BERBANDING kadar lama cetakan 1988 RM1,000 / 2 tahun)."
        ),
    },
    "AKTA_281": {
        "companion_statute_ids": ("AKTA_281_PINDAAN_2024",),
        "priority_sections": {
            "AKTA_281_PINDAAN_2024": ("2", "3", "4"),
        },
        "mandatory_directive_bm": (
            "ARAHAN KERAS PINDAAN STATUTORI (AKTA 281 <-> AKTA A1702): "
            "Apabila merujuk Akta Makanan 1983 [Akta 281], ANDA WAJIB MENYEMAK DAN MENGUTAMAKAN "
            "pindaan terkini Akta Makanan (Pindaan) 2024 [Akta A1702] (berkuat kuasa 1 Oktober 2024 — termasuk "
            "pemotongan takrif tembakau/hasil tembakau di Seksyen 2 serta pemotongan Seksyen 36 yang dipindahkan ke Akta 852) "
            "BERBANDING teks asal Akta 281 sebelum pindaan 2024."
        ),
    },
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")


def compute_deterministic_embedding(text: str, dim: int = 64) -> List[float]:
    """Menjana vektor embedding deterministik bagi carian hibrid semantik + kata kunci tepat."""
    vec = [0.0] * dim
    tokens = [t.lower() for t in TOKEN_RE.findall((text or "").lower()) if len(t) >= 2]
    terms = tokens + [f"{tokens[i]}_{tokens[i + 1]}" for i in range(len(tokens) - 1)]
    for term in terms:
        digest = hashlib.sha256(term.encode("utf-8")).digest()
        idx = int.from_bytes(digest[:4], "little") % dim
        sign = 1.0 if (digest[4] & 1) == 0 else -1.0
        vec[idx] += sign
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [round(v / norm, 5) for v in vec]


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    return sum(a * b for a, b in zip(vec_a, vec_b))


# =====================================================================
# 1. SENARAI HITAM UNDANG-UNDANG LAPUK / SALAH PETIK (repealed_and_blocked_provisions)
# =====================================================================

DEFAULT_REPEALED_AND_BLOCKED_PROVISIONS: List[Dict[str, Any]] = [
    {
        "provision_id": "REPEALED_PPKHT_2004_ALL",
        "repealed_statute_or_section": "Peraturan-Peraturan Kawalan Hasil Tembakau 2004 (PPKHT 2004) [P.U. (A) 324/2004] — Keseluruhan Peraturan (termasuk Peraturan 8, 9, 10, 11, 12, 13, 13(1), 14)",
        "match_patterns": [
            r"\bppkht\s*2004\b",
            r"\bp\.?u\.?\s*\(a\)\s*324/2004\b",
            r"\bkawalan\s+hasil\s+tembakau\s+2004\b",
            r"\bperaturan\s+(?:8|8a|9|10|11|12|13|14)(?:\(\d+\))?\s+ppkht\b",
        ],
        "status": "DIMANSUHKAN",
        "replacement_statute_id": "AKTA_852",
        "replacement_section": "Akta Kawalan Produk Merokok Demi Kesihatan Awam 2024 [Akta 852] & Peraturan/Perintah Subsidiari P.U. (A) 257–264/2024",
        "warning_message_bm": (
            "DISEKAT (UNDANG-UNDANG DIMANSUHKAN): Peraturan-Peraturan Kawalan Hasil Tembakau 2004 (PPKHT 2004) "
            "telah DIMANSUHKAN sepenuhnya mulai 1 Oktober 2024. Gunakan Akta Kawalan Produk Merokok Demi Kesihatan Awam 2024 [Akta 852]."
        ),
        "key_differences_note": (
            "PERBEZAAN KRITIKAL AKTA 852 vs PPKHT 2004: "
            "(1) Kawasan larangan merokok kini di bawah Seksyen 16(2) Akta 852 & P.U. (A) 257/2024 (bukan Peraturan 11 PPKHT 2004). "
            "(2) Kewajipan pemilik premis pamer tanda amaran/tiada ashtray kini Seksyen 18(1)(a)/(b) Akta 852 & P.U. (A) 258/2024 (bukan Peraturan 12 PPKHT 2004). "
            "(3) Kesalahan Orang Belum Dewasa (OBD < 18 tahun) di bawah Seksyen 17(1) Akta 852 HANYA merangkumi perbuatan 'merokok, mengunyah atau menggunakan' "
            "(serta 'membeli' di bawah Seksyen 13(3)); kesalahan 'MEMILIKI' semata-mata oleh OBD dalam Peraturan 13(1) PPKHT 2004 TIDAK lagi wujud dalam Seksyen 17(1) Akta 852!"
        ),
    },
    {
        "provision_id": "EXPIRED_ORDINAN_DARURAT_342_2021",
        "repealed_statute_or_section": "Ordinan Darurat (Pencegahan dan Pengawalan Penyakit Berjangkit) (Pindaan) 2021 [P.U. (A) 82/2021] — Kompaun RM10,000 / RM50,000",
        "match_patterns": [
            r"\bordinan\s+darurat\b.*?(?:2021|342|penyakit\s+berjangkit|kompaun)",
            r"\bp\.?u\.?\s*\(a\)\s*82/2021\b",
            r"\bkompaun\s+rm\s*10,?000\b.*?\bakta\s*342\b",
        ],
        "status": "TAMAT_TEMPOH",
        "replacement_statute_id": "AKTA_342",
        "replacement_section": "Seksyen 24 & Seksyen 25 Akta 342 (Pindaan Akta A1742 berkuat kuasa 1 Mei 2025) & P.U. (A) 139/2025",
        "warning_message_bm": (
            "DISEKAT (ORDINAN TAMAT TEMPOH / TIDAK SAH): Ordinan Darurat (Pencegahan dan Pengawalan Penyakit Berjangkit) (Pindaan) 2021 "
            "(kompaun RM10,000 individu / RM50,000 syarikat) telah DIBATALKAN & TAMAT TEMPOH. "
            "Rujuk Seksyen 25 Akta 342 (Pindaan Akta A1742 berkuat kuasa 1 Mei 2025) & P.U. (A) 139/2025."
        ),
        "key_differences_note": (
            "Di bawah Seksyen 25 Akta 342 (Pindaan Akta A1742) & P.U. (A) 139/2025: had kompaun maksimum ialah RM5,000 (individu) / RM50,000 (pertubuhan perbadanan), "
            "WAJIB dengan keizinan bertulis Pendakwa Raya, dan HANYA bagi seksyen dalam Jadual Pertama P.U. (A) 139/2025 (S.10(2), S.11(5), S.21A(3), S.22(b)/(c)/(d))."
        ),
    },
    {
        "provision_id": "BLOCKED_AKTA_852_S38_AS_SEIZURE",
        "repealed_statute_or_section": "Salah Petik: Seksyen 38 Akta 852 sebagai kuasa penyitaan / Borang Senarai Benda Disita",
        "match_patterns": [
            r"\bsitaan\s+seksyen\s+38\b",
            r"\bborang\s+sitaan\s+seksyen\s+38\b",
            r"\bdisita\s+di\s+bawah\s+seksyen\s+38\s+akta\s+852\b",
        ],
        "status": "SALAH_PETIK_SEKSYEN",
        "replacement_statute_id": "AKTA_852",
        "replacement_section": "Seksyen 35 (Kuasa Menyita) & Seksyen 36 (Senarai Benda Disita) Akta 852",
        "warning_message_bm": (
            "DISEKAT (SALAH PETIK SEKSYEN): Seksyen 38 Akta 852 ialah kos memegang barang disita, BUKAN kuasa penyitaan. "
            "Kuasa menyita ialah Seksyen 35 dan Borang Senarai Benda Disita ialah Seksyen 36 Akta 852."
        ),
        "key_differences_note": "Gunakan Seksyen 35 & Seksyen 36 Akta 852 pada Borang Senarai Benda Disita.",
    },
    {
        "provision_id": "BLOCKED_AKTA_852_S44_AS_COMPOUND",
        "repealed_statute_or_section": "Salah Petik: Seksyen 44 Akta 852 sebagai kuasa mengkompaun",
        "match_patterns": [
            r"\bkompaun\s+seksyen\s+44\b",
            r"\bdikompaun\s+di\s+bawah\s+seksyen\s+44\s+akta\s+852\b",
        ],
        "status": "SALAH_PETIK_SEKSYEN",
        "replacement_statute_id": "AKTA_852",
        "replacement_section": "Seksyen 48 Akta 852 & P.U. (A) 259/2024",
        "warning_message_bm": (
            "DISEKAT (SALAH PETIK SEKSYEN): Seksyen 44 Akta 852 ialah perlindungan pemberi maklumat. "
            "Kuasa mengkompaun kesalahan ialah Seksyen 48 Akta 852 dibaca bersama P.U. (A) 259/2024."
        ),
        "key_differences_note": "Gunakan Seksyen 48 Akta 852 [P.U. (A) 259/2024] untuk tawaran kompaun.",
    },
    {
        "provision_id": "BLOCKED_AKTA_514_FOR_TB",
        "repealed_statute_or_section": "Salah Petik: Seksyen 22(b) Akta 514 untuk kes ingkar rawatan Tibi / Penyakit Berjangkit",
        "match_patterns": [
            r"\bseksyen\s+22\(b\)\s+akta\s+514\b",
        ],
        "status": "SALAH_PETIK_SEKSYEN",
        "replacement_statute_id": "AKTA_342",
        "replacement_section": "Seksyen 22(b) Akta Pencegahan dan Pengawalan Penyakit Berjangkit 1988 [Akta 342]",
        "warning_message_bm": (
            "DISEKAT (SALAH PETIK AKTA): Akta 514 ialah Akta Keselamatan dan Kesihatan Pekerjaan 1994 (OSHA). "
            "Kes ingkar perintah rawatan Tibi / penyakit berjangkit ialah di bawah Seksyen 22(b) Akta 342 [APPPB 1988]."
        ),
        "key_differences_note": "Gunakan Seksyen 22(b) & Seksyen 24 Akta 342 bagi kes ingkar perintah sah penyakit berjangkit.",
    },
    {
        "provision_id": "REPEALED_KTJ_S113",
        "repealed_statute_or_section": "Seksyen 113 Kanun Tatacara Jenayah [Akta 593] — Pernyataan Beramaran Lama",
        "match_patterns": [
            r"\bpernyataan\s+beramaran\s+seksyen\s+113\b",
            r"\brakaman\s+seksyen\s+113\s+ktj\b",
        ],
        "status": "DIMANSUHKAN",
        "replacement_statute_id": "AKTA_593",
        "replacement_section": "Seksyen 112 Kanun Tatacara Jenayah [Akta 593] (dengan pematuhan subseksyen (2) hingga (5))",
        "warning_message_bm": (
            "DISEKAT (PERUNTUKAN LAMA DIGANTI): Pernyataan beramaran lama di bawah Seksyen 113 KTJ telah diganti melalui Akta A1274 (2007). "
            "Semua rakaman percakapan saksi dan OYDS wajib diambil di bawah Seksyen 112 KTJ."
        ),
        "key_differences_note": "Seksyen 113 KTJ terkini menyekat kebolehterimaan pernyataan kepada pegawai penyiasat sebagai keterangan pendakwaan kecuali bagi tujuan tertentu; rakaman percakapan wajib mematuhi Seksyen 112(2)–(5) KTJ.",
    },
]


# =====================================================================
# 2. METADATA AKTA & PERATURAN (statutes_registry)
# =====================================================================

DEFAULT_STATUTES_REGISTRY_META: List[Dict[str, Any]] = [
    {
        "statute_id": "AKTA_852",
        "canonical_akta_code": "Akta 852",
        "official_title_bm": "Akta Kawalan Produk Merokok Demi Kesihatan Awam 2024",
        "official_title_en": "Control of Smoking Products for Public Health Act 2024",
        "act_number_or_pu": "Akta 852",
        "status": "BERKUAT_KUASA",
        "repealed_by": None,
        "effective_date": "2024-10-01",
        "source_pdf_filename": "AKTA_852.pdf",
        "verified_by_admin": False,
    },
    {
        "statute_id": "AKTA_852_PERINTAH_LARANGAN_2024",
        "canonical_akta_code": "Akta 852",
        "official_title_bm": "Perintah Kawalan Produk Merokok Demi Kesihatan Awam (Pengisytiharan Kawasan atau Tempat Larangan Merokok) 2024",
        "official_title_en": "Control of Smoking Products for Public Health (Declaration of Non-Smoking Area or Place) Order 2024",
        "act_number_or_pu": "P.U. (A) 257/2024",
        "status": "BERKUAT_KUASA",
        "repealed_by": None,
        "effective_date": "2024-10-01",
        "source_pdf_filename": "AKTA_852_PERINTAH_LARANGAN_2024.pdf",
        "verified_by_admin": False,
    },
    {
        "statute_id": "AKTA_852_PERATURAN_TANDA_2024",
        "canonical_akta_code": "Akta 852",
        "official_title_bm": "Peraturan-Peraturan Kawalan Produk Merokok Demi Kesihatan Awam (Tanda Amaran Larangan Merokok) 2024",
        "official_title_en": "Control of Smoking Products for Public Health (No-Smoking Warning Sign) Regulations 2024",
        "act_number_or_pu": "P.U. (A) 258/2024",
        "status": "BERKUAT_KUASA",
        "repealed_by": None,
        "effective_date": "2024-10-01",
        "source_pdf_filename": "AKTA_852_PERATURAN_TANDA_2024.pdf",
        "verified_by_admin": False,
    },
    {
        "statute_id": "AKTA_852_PERATURAN_KOMPAUN_2024",
        "canonical_akta_code": "Akta 852",
        "official_title_bm": "Peraturan-Peraturan Kawalan Produk Merokok Demi Kesihatan Awam (Pengkompaunan Kesalahan) 2024",
        "official_title_en": "Control of Smoking Products for Public Health (Compounding of Offences) Regulations 2024",
        "act_number_or_pu": "P.U. (A) 259/2024",
        "status": "BERKUAT_KUASA",
        "repealed_by": None,
        "effective_date": "2024-10-01",
        "source_pdf_filename": "AKTA_852_PERATURAN_KOMPAUN_2024.pdf",
        "verified_by_admin": False,
    },
    {
        "statute_id": "AKTA_852_PERATURAN_JUALAN_2024",
        "canonical_akta_code": "Akta 852",
        "official_title_bm": "Peraturan-Peraturan Kawalan Produk Merokok Demi Kesihatan Awam (Kawalan Penjualan) 2024",
        "official_title_en": "Control of Smoking Products for Public Health (Control of Sale) Regulations 2024",
        "act_number_or_pu": "P.U. (A) 260/2024",
        "status": "BERKUAT_KUASA",
        "repealed_by": None,
        "effective_date": "2024-10-01",
        "source_pdf_filename": "AKTA_852_PERATURAN_JUALAN_2024.pdf",
        "verified_by_admin": False,
    },
    {
        "statute_id": "AKTA_852_PERATURAN_PEMBUNGKUSAN_2024",
        "canonical_akta_code": "Akta 852",
        "official_title_bm": "Peraturan-Peraturan Kawalan Produk Merokok Demi Kesihatan Awam (Pembungkusan dan Pelabelan) 2024",
        "official_title_en": "Control of Smoking Products for Public Health (Packaging and Labelling) Regulations 2024",
        "act_number_or_pu": "P.U. (A) 261/2024",
        "status": "BERKUAT_KUASA",
        "repealed_by": None,
        "effective_date": "2024-10-01",
        "source_pdf_filename": "AKTA_852_PERATURAN_PEMBUNGKUSAN_2024.pdf",
        "verified_by_admin": False,
    },
    {
        "statute_id": "AKTA_852_PERATURAN_PENDAFTARAN_2024",
        "canonical_akta_code": "Akta 852",
        "official_title_bm": "Peraturan-Peraturan Kawalan Produk Merokok Demi Kesihatan Awam (Pendaftaran Produk Tembakau, Bahan Merokok atau Produk Pengganti Tembakau) 2024",
        "official_title_en": "Control of Smoking Products for Public Health (Registration of Tobacco Product, Smoking Substance or Substitute Tobacco Product) Regulations 2024",
        "act_number_or_pu": "P.U. (A) 262/2024",
        "status": "BERKUAT_KUASA",
        "repealed_by": None,
        "effective_date": "2024-10-01",
        "source_pdf_filename": "AKTA_852_PERATURAN_PENDAFTARAN_2024.pdf",
        "verified_by_admin": False,
    },
    {
        "statute_id": "AKTA_852_PERINTAH_MAKMAL_2024",
        "canonical_akta_code": "Akta 852",
        "official_title_bm": "Perintah Makmal yang Diluluskan 2024",
        "official_title_en": "Approved Laboratories Order 2024",
        "act_number_or_pu": "P.U. (A) 263/2024",
        "status": "BERKUAT_KUASA",
        "repealed_by": None,
        "effective_date": "2024-10-01",
        "source_pdf_filename": "AKTA_852_PERINTAH_MAKMAL_2024.pdf",
        "verified_by_admin": False,
    },
    {
        "statute_id": "AKTA_852_PERATURAN_NOTIS_S47_2024",
        "canonical_akta_code": "Akta 852",
        "official_title_bm": "Peraturan-Peraturan Kawalan Produk Merokok Demi Kesihatan Awam (Notis di Bawah Seksyen 47) 2024",
        "official_title_en": "Control of Smoking Products for Public Health (Notice Under Section 47) Regulations 2024",
        "act_number_or_pu": "P.U. (A) 264/2024",
        "status": "BERKUAT_KUASA",
        "repealed_by": None,
        "effective_date": "2024-10-01",
        "source_pdf_filename": "AKTA_852_PERATURAN_NOTIS_S47_2024.pdf",
        "verified_by_admin": False,
    },
    {
        "statute_id": "AKTA_281",
        "canonical_akta_code": "Akta 281",
        "official_title_bm": "Akta Makanan 1983",
        "official_title_en": "Food Act 1983",
        "act_number_or_pu": "Akta 281",
        "status": "BERKUAT_KUASA",
        "repealed_by": None,
        "effective_date": "1985-10-01",
        "source_pdf_filename": "AKTA_281.pdf",
        "verified_by_admin": False,
    },
    {
        "statute_id": "AKTA_281_PINDAAN_2024",
        "canonical_akta_code": "Akta 281",
        "official_title_bm": "Akta Makanan (Pindaan) 2024",
        "official_title_en": "Food (Amendment) Act 2024",
        "act_number_or_pu": "Akta A1702",
        "status": "BERKUAT_KUASA",
        "repealed_by": None,
        "effective_date": "2024-10-01",
        "source_pdf_filename": "AKTA_281_PINDAAN_A1702_2024.pdf",
        "verified_by_admin": False,
    },
    {
        "statute_id": "PPKM_2009",
        "canonical_akta_code": "Akta 281",
        "official_title_bm": "Peraturan-Peraturan Kebersihan Makanan 2009 (Kemaskini 19 Mac 2024)",
        "official_title_en": "Food Hygiene Regulations 2009",
        "act_number_or_pu": "P.U. (A) 95/2009",
        "status": "BERKUAT_KUASA",
        "repealed_by": None,
        "effective_date": "2009-02-28",
        "source_pdf_filename": "PPKM_2009.pdf",
        "verified_by_admin": False,
    },
    {
        "statute_id": "PPM_1985",
        "canonical_akta_code": "Akta 281",
        "official_title_bm": "Peraturan-Peraturan Makanan 1985 (Kemaskini Ogos 2026 P.U. (A) 48/2026)",
        "official_title_en": "Food Regulations 1985",
        "act_number_or_pu": "P.U. (A) 437/1985",
        "status": "BERKUAT_KUASA",
        "repealed_by": None,
        "effective_date": "1985-10-01",
        "source_pdf_filename": "PPM_1985.pdf",
        "verified_by_admin": False,
    },
    {
        "statute_id": "AKTA_154",
        "canonical_akta_code": "Akta 154",
        "official_title_bm": "Akta Pemusnahan Serangga Pembawa Penyakit 1975",
        "official_title_en": "Destruction of Disease-Bearing Insects Act 1975",
        "act_number_or_pu": "Akta 154",
        "status": "BERKUAT_KUASA",
        "repealed_by": None,
        "effective_date": "1982-08-15",
        "source_pdf_filename": "AKTA_154.pdf",
        "verified_by_admin": False,
    },
    {
        "statute_id": "AKTA_342",
        "canonical_akta_code": "Akta 342",
        "official_title_bm": "Akta Pencegahan dan Pengawalan Penyakit Berjangkit 1988",
        "official_title_en": "Prevention and Control of Infectious Diseases Act 1988",
        "act_number_or_pu": "Akta 342",
        "status": "BERKUAT_KUASA",
        "repealed_by": None,
        "effective_date": "1989-04-01",
        "source_pdf_filename": "AKTA_342.pdf",
        "verified_by_admin": False,
    },
    {
        "statute_id": "AKTA_342_PINDAAN_2025",
        "canonical_akta_code": "Akta 342",
        "official_title_bm": "Akta Pencegahan dan Pengawalan Penyakit Berjangkit (Pindaan) 2025",
        "official_title_en": "Prevention and Control of Infectious Diseases (Amendment) Act 2025",
        "act_number_or_pu": "Akta A1742",
        "status": "BERKUAT_KUASA",
        "repealed_by": None,
        "effective_date": "2025-05-01",
        "source_pdf_filename": "AKTA_342_PINDAAN_A1742_2025.pdf",
        "verified_by_admin": False,
    },
    {
        "statute_id": "AKTA_342_PERATURAN_KOMPAUN_2025",
        "canonical_akta_code": "Akta 342",
        "official_title_bm": "Peraturan-Peraturan Pencegahan dan Pengawalan Penyakit Berjangkit (Pengkompaunan Kesalahan-Kesalahan) (Pindaan) 2025",
        "official_title_en": "Prevention and Control of Infectious Diseases (Compounding of Offences) (Amendment) Regulations 2025",
        "act_number_or_pu": "P.U. (A) 139/2025",
        "status": "BERKUAT_KUASA",
        "repealed_by": None,
        "effective_date": "2025-05-01",
        "source_pdf_filename": "AKTA_342_PERATURAN_KOMPAUN_2025.pdf",
        "verified_by_admin": False,
    },
    {
        "statute_id": "AKTA_593",
        "canonical_akta_code": "Akta 593",
        "official_title_bm": "Kanun Tatacara Jenayah (Criminal Procedure Code - Teks Sahih BI AGC)",
        "official_title_en": "Criminal Procedure Code",
        "act_number_or_pu": "Akta 593",
        "status": "BERKUAT_KUASA",
        "repealed_by": None,
        "effective_date": "1999-01-07",
        "source_pdf_filename": "AKTA_593.pdf",
        "verified_by_admin": False,
    },
    {
        "statute_id": "AKTA_56",
        "canonical_akta_code": "Akta 56",
        "official_title_bm": "Akta Keterangan 1950 (Evidence Act 1950 — Cetakan Semula Rasmi AGC 1 Disember 2012, termasuk Seksyen 90A–90C & 114A)",
        "official_title_en": "Evidence Act 1950 (Reprint as at 1 December 2012, Act A1432)",
        "act_number_or_pu": "Akta 56",
        "status": "BERKUAT_KUASA",
        "repealed_by": None,
        "effective_date": "1950-05-23",
        "source_pdf_filename": "AKTA_56.pdf",
        "verified_by_admin": False,
    },
    {
        "statute_id": "AKTA_611",
        "canonical_akta_code": "Akta 611",
        "official_title_bm": "Akta Kanak-Kanak 2001 (Cetakan Semula 1 Julai 2023)",
        "official_title_en": "Child Act 2001",
        "act_number_or_pu": "Akta 611",
        "status": "BERKUAT_KUASA",
        "repealed_by": None,
        "effective_date": "2002-08-01",
        "source_pdf_filename": "AKTA_611.pdf",
        "verified_by_admin": False,
    },
    {
        "statute_id": "AKTA_574",
        "canonical_akta_code": "Akta 574",
        "official_title_bm": "Kanun Keseksaan (Penal Code — Teks Kemaskini Rasmi AGC 30 November 2022)",
        "official_title_en": "Penal Code (Online Updated Text as at 30 November 2022)",
        "act_number_or_pu": "Akta 574",
        "status": "BERKUAT_KUASA",
        "repealed_by": None,
        "effective_date": "1997-08-07",
        "source_pdf_filename": "AKTA_574.pdf",
        "verified_by_admin": False,
    },
    {
        "statute_id": "AKTA_344",
        "canonical_akta_code": "Akta 344",
        "official_title_bm": "Akta Polis 1967 (Teks Rasmi AGC 1 Jun 2016)",
        "official_title_en": "Police Act 1967 (as at 1 June 2016)",
        "act_number_or_pu": "Akta 344",
        "status": "BERKUAT_KUASA",
        "repealed_by": None,
        "effective_date": "1967-08-29",
        "source_pdf_filename": "AKTA_344.pdf",
        "verified_by_admin": False,
    },
    {
        "statute_id": "AKTA_388",
        "canonical_akta_code": "Akta 388",
        "official_title_bm": "Akta Tafsiran 1948 dan 1967 (Interpretation Acts 1948 and 1967 — Cetakan Semula Rasmi AGC 1 Januari 2006)",
        "official_title_en": "Interpretation Acts 1948 and 1967 (Reprint as at 1 January 2006)",
        "act_number_or_pu": "Akta 388",
        "status": "BERKUAT_KUASA",
        "repealed_by": None,
        "effective_date": "1967-05-18",
        "source_pdf_filename": "AKTA_388.pdf",
        "verified_by_admin": False,
    },
    {
        "statute_id": "AKTA_92",
        "canonical_akta_code": "Akta 92",
        "official_title_bm": "Akta Mahkamah Rendah 1948 (Subordinate Courts Act 1948 — Teks Kemaskini Rasmi AGC 1 Januari 2023)",
        "official_title_en": "Subordinate Courts Act 1948 (Online Updated Text as at 1 January 2023)",
        "act_number_or_pu": "Akta 92",
        "status": "BERKUAT_KUASA",
        "repealed_by": None,
        "effective_date": "1949-01-01",
        "source_pdf_filename": "AKTA_92.pdf",
        "verified_by_admin": False,
    },
    {
        "statute_id": "PPKHT_2004",
        "canonical_akta_code": "PPKHT 2004 (Dimansuhkan)",
        "official_title_bm": "Peraturan-Peraturan Kawalan Hasil Tembakau 2004 (DIMANSUHKAN)",
        "official_title_en": "Control of Tobacco Product Regulations 2004 (REPEALED)",
        "act_number_or_pu": "P.U. (A) 324/2004",
        "status": "DIMANSUHKAN",
        "repealed_by": "AKTA_852",
        "effective_date": "2004-09-23",
        "source_pdf_filename": "DIMANSUHKAN_OLEH_AKTA_852",
        "verified_by_admin": False,
    },
    {
        "statute_id": "ORDINAN_DARURAT_342_2021",
        "canonical_akta_code": "Ordinan Darurat 2021 (Tamat Tempoh)",
        "official_title_bm": "Ordinan Darurat (Pencegahan dan Pengawalan Penyakit Berjangkit) (Pindaan) 2021 (TAMAT TEMPOH)",
        "official_title_en": "Emergency (Prevention and Control of Infectious Diseases) (Amendment) Ordinance 2021 (REVOKED)",
        "act_number_or_pu": "P.U. (A) 82/2021",
        "status": "DIMANSUHKAN",
        "repealed_by": "AKTA_342",
        "effective_date": "2021-03-11",
        "source_pdf_filename": "TAMAT_TEMPOH_RUJUK_AKTA_A1742",
        "verified_by_admin": False,
    },
]


# =====================================================================
# 3. DAFTAR KESALAHAN MENYELURUH (master_offences_matrix)
# =====================================================================

DEFAULT_MASTER_OFFENCES_MATRIX: List[Dict[str, Any]] = [
    # ---------------- AKTA 852 ----------------
    {
        "offence_id": "AKTA_852_S3_1",
        "statute_id": "AKTA_852",
        "offence_section": "Seksyen 3(1)",
        "read_together_with": ["P.U. (A) 262/2024"],
        "offence_title": "Mengimport, mengilang atau mengedarkan produk tembakau / bahan merokok / produk pengganti tembakau yang tidak berdaftar",
        "target_offender": "PENJUAL_PENGILANG",
        "mandatory_elements": [
            {
                "element_no": 1,
                "description": "Perbuatan mengimport, mengilang atau mengedarkan produk tembakau, bahan merokok atau produk pengganti tembakau.",
                "must_prove": "Invois pengedaran, rekod pengilangan/import, atau stok pukal yang disita melalui Borang Seksyen 36 Akta 852.",
            },
            {
                "element_no": 2,
                "description": "Produk tersebut tidak didaftarkan dengan Ketua Pengarah Kesihatan di bawah Akta 852 & P.U. (A) 262/2024.",
                "must_prove": "Surat pengesahan rasmi Bahagian Kawalan Penyakit (Sektor Tembakau/Akta 852) KKM bahawa produk tiada dalam daftar rasmi.",
            },
        ],
        "explicit_exclusions_and_traps": [
            "Produk yang masih berada dalam tempoh peralihan pendaftaran statutori yang sah mengikut jadual kuat kuasa P.U. (A) 262/2024 tidak boleh dituduh tanpa semakan tarikh kuat kuasa fasa pendaftaran.",
            "Jangan kelirukan kesalahan pengedaran tanpa daftar (S.3) dengan kesalahan pameran terbuka di kedai runcit (S.10(1) + Peraturan 6 P.U. (A) 260/2024).",
        ],
        "penalty_section": "Seksyen 3(2)(a) [Bukan Pertubuhan Perbadanan] / Seksyen 3(2)(b) [Pertubuhan Perbadanan] Akta 852",
        "penalty_first_offence": {
            "max_fine_rm": 20000,
            "max_jail_months": 12,
            "other_orders": "Bagi Pertubuhan Perbadanan: Denda RM20,000 hingga RM100,000 atau penjara maks 2 tahun",
            "verbatim_penalty": "Bukan Pertubuhan Perbadanan: Denda tidak melebihi RM20,000 atau penjara tidak melebihi 1 tahun atau kedua-duanya | Pertubuhan Perbadanan: Denda tidak kurang RM20,000 dan tidak melebihi RM100,000 atau penjara tidak melebihi 2 tahun.",
        },
        "penalty_subsequent_offence": {
            "max_fine_rm": 30000,
            "max_jail_months": 24,
            "other_orders": "Pertubuhan Perbadanan: Denda RM50,000 hingga RM300,000 atau penjara maks 3 tahun",
            "verbatim_penalty": "Bukan Pertubuhan Perbadanan: Denda tidak melebihi RM30,000 atau penjara tidak melebihi 2 tahun | Pertubuhan Perbadanan: Denda RM50,000 hingga RM300,000 atau penjara tidak melebihi 3 tahun.",
        },
        "compound_info": {
            "is_compoundable": False,
            "compound_authority_section": None,
            "compound_regulation_ref": "P.U. (A) 259/2024",
            "compound_amount_or_limit": "TIDAK BOLEH KOMPAUN — Wajib Sita (S.35/S.36) & Buka IP Terus",
            "max_compound_rm": None,
            "payment_days": None,
            "notice_section": "Seksyen 47 Akta 852 [P.U. (A) 264/2024] (Notis Hadir Mahkamah)",
        },
        "special_legal_requirements": [
            "Borang Senarai Benda Disita Seksyen 36 Akta 852",
            "Sijil Seksyen 90A(2) Akta Keterangan 1950",
            "Seksyen 49 Akta 852 jika melibatkan Pertubuhan Perbadanan (Sdn. Bhd.)",
        ],
        "mandatory_exhibits": [
            "Produk merokok tidak berdaftar yang disita & dilak KKM + Borang Seksyen 36 Akta 852",
            "Pengesahan bertulis KKM mengenai status ketiadaan pendaftaran produk di bawah P.U. (A) 262/2024",
            "Gambar foto berwarna bertarikh + Sijil Seksyen 90A(2) & Carian Rasmi SSM",
        ],
        "charge_sheet_template_bm": (
            "Bahawa kamu, pada [TARIKH], jam lebih kurang [MASA], bertempat di [TEMPAT_KEJADIAN], "
            "di dalam Daerah [DAERAH], di dalam Negeri [NEGERI], telah didapati mengedarkan produk pengganti tembakau / bahan merokok "
            "yang tidak didaftarkan di bawah Akta Kawalan Produk Merokok Demi Kesihatan Awam 2024 [Akta 852] dan P.U. (A) 262/2024; "
            "dan oleh yang demikian kamu telah melakukan suatu kesalahan di bawah Seksyen 3(1) Akta 852 yang boleh dihukum di bawah Seksyen 3(2)(a)/(b) Akta yang sama."
        ),
        "source_section_doc_ids": ["AKTA_852__S3", "AKTA_852_PERATURAN_PENDAFTARAN_2024__P3", "AKTA_852__S49"],
        "verified_status": "DRAFT_PENDING_REVIEW",
    },
    {
        "offence_id": "AKTA_852_S7_1",
        "statute_id": "AKTA_852",
        "offence_section": "Seksyen 7(1)",
        "read_together_with": ["Seksyen 49 Akta 852 (jika pertubuhan perbadanan)", "Seksyen 114A Akta Keterangan 1950 (jika iklan digital/media sosial)"],
        "offence_title": "Menyiarkan, menyebabkan disiarkan atau memudahkan penyiaran iklan produk tembakau / bahan merokok / produk pengganti tembakau (vape)",
        "target_offender": "PENJUAL_PENGILANG",
        "mandatory_elements": [
            {
                "element_no": 1,
                "description": "OKT menyiarkan, menyebabkan disiarkan atau memudahkan penyiaran suatu iklan (poster, bunting, papan tanda, skrin LED atau hantaran media sosial).",
                "must_prove": "Bahan iklan fizikal yang disita (Borang S.36) atau cetakan tangkapan skrin digital bersama Sijil S.90A(2) & anggapan penerbitan S.114A Akta 56 serta bukti kawalan premis/akaun (SSM).",
            },
            {
                "element_no": 2,
                "description": "Iklan tersebut mengandungi representasi nyata atau tersirat yang menggalakkan atau mempromosikan penggunaan produk merokok atau rokok elektronik.",
                "must_prove": "Gambar jelas kandungan visual/teks iklan yang memaparkan jenama, gambar peranti vape/rokok atau ajakan membeli/menggunakan.",
            },
        ],
        "explicit_exclusions_and_traps": [
            "Senarai harga bertulis yang mematuhi spesifikasi tertutup di bawah P.U. (A) 260/2024 (hanya ditunjukkan atas permintaan pelanggan dewasa) BUKAN iklan haram S.7(1).",
            "JANGAN campurkan kesalahan iklan S.7(1) dengan kesalahan pameran produk S.10(1) dalam satu Borang 114 yang sama (Pertindihan Pertuduhan di bawah Seksyen 163 KTJ).",
        ],
        "penalty_section": "Seksyen 7(2)(a) [Bukan Pertubuhan Perbadanan] / Seksyen 7(2)(b) [Pertubuhan Perbadanan] Akta 852",
        "penalty_first_offence": {
            "max_fine_rm": 20000,
            "max_jail_months": 12,
            "other_orders": "Pertubuhan Perbadanan: Denda RM20,000 hingga RM100,000 atau penjara maks 2 tahun",
            "verbatim_penalty": "Bukan Pertubuhan Perbadanan: Denda tidak melebihi RM20,000 atau penjara tidak melebihi 1 tahun atau kedua-duanya | Pertubuhan Perbadanan: Denda tidak kurang RM20,000 dan tidak melebihi RM100,000 atau penjara tidak melebihi 2 tahun.",
        },
        "penalty_subsequent_offence": {
            "max_fine_rm": 30000,
            "max_jail_months": 24,
            "other_orders": "Pertubuhan Perbadanan: Denda RM50,000 hingga RM300,000 atau penjara maks 3 tahun",
            "verbatim_penalty": "Bukan Pertubuhan Perbadanan: Denda tidak melebihi RM30,000 atau penjara tidak melebihi 2 tahun | Pertubuhan Perbadanan: Denda RM50,000 hingga RM300,000 atau penjara tidak melebihi 3 tahun.",
        },
        "compound_info": {
            "is_compoundable": False,
            "compound_authority_section": None,
            "compound_regulation_ref": "P.U. (A) 259/2024",
            "compound_amount_or_limit": "TIDAK BOLEH KOMPAUN di bawah Jadual Pertama P.U. (A) 259/2024 — Wajib Sita (S.35/S.36) & Buka IP Terus",
            "max_compound_rm": None,
            "payment_days": None,
            "notice_section": "Seksyen 47 Akta 852 [P.U. (A) 264/2024] (Notis Hadir Mahkamah)",
        },
        "special_legal_requirements": [
            "Borang Senarai Benda Disita Seksyen 36 Akta 852 (bukan Seksyen 38)",
            "Sijil Seksyen 90A(2) & Seksyen 114A Akta Keterangan 1950 (jika iklan digital/media sosial)",
            "Seksyen 49 Akta 852 jika pertubuhan perbadanan",
        ],
        "mandatory_exhibits": [
            "Poster / bunting / bahan iklan fizikal yang disita & dilak KKM + Borang Seksyen 36 Akta 852",
            "Gambar foto bukti & cetakan paparan iklan digital + Sijil Seksyen 90A(2)",
            "Cetakan Carian Rasmi SSM + Sijil S.90A & Pelan Lakar premis",
        ],
        "charge_sheet_template_bm": (
            "Bahawa kamu, pada [TARIKH], jam lebih kurang [MASA], bertempat di [TEMPAT_KEJADIAN], "
            "di dalam Daerah [DAERAH], di dalam Negeri [NEGERI], telah didapati menyiarkan iklan yang menggalakkan atau mempromosikan "
            "penggunaan produk pengganti tembakau (rokok elektronik / vape); dan oleh yang demikian kamu telah melakukan suatu kesalahan "
            "di bawah Seksyen 7(1) Akta Kawalan Produk Merokok Demi Kesihatan Awam 2024 [Akta 852] yang boleh dihukum di bawah Seksyen 7(2)(a)/(b) Akta yang sama."
        ),
        "source_section_doc_ids": ["AKTA_852__S7", "AKTA_852__S26", "AKTA_852__S49", "AKTA_56__S114A"],
        "verified_status": "DRAFT_PENDING_REVIEW",
    },
    {
        "offence_id": "AKTA_852_S9_1",
        "statute_id": "AKTA_852",
        "offence_section": "Seksyen 9(1)",
        "read_together_with": ["Seksyen 49 Akta 852 (jika pertubuhan perbadanan)"],
        "offence_title": "Mempromosikan atau menaja acara, aktiviti atau pemberian diskaun/hadiah berkaitan produk merokok",
        "target_offender": "PENJUAL_PENGILANG",
        "mandatory_elements": [
            {
                "element_no": 1,
                "description": "OKT mempromosikan atau menaja sesuatu acara, aktiviti atau orang.",
                "must_prove": "Bahan promosi, baucar diskaun, pemberian sampel percuma atau rekod tajaan.",
            },
            {
                "element_no": 2,
                "description": "Menggunakan nama dagangan, cap dagangan atau imej yang berkaitan dengan produk tembakau, bahan merokok atau produk pengganti tembakau.",
                "must_prove": "Gambar foto bahan promosi/jenama produk merokok + Sijil S.90A(2) & Borang Sitaan S.36.",
            },
        ],
        "explicit_exclusions_and_traps": [
            "Tajaan atau aktiviti tanggungjawab sosial korporat (CSR) yang TIDAK menggunakan jenama/cap dagangan/imej produk merokok dan tidak mempromosikan produk merokok perlu disemak fakta elemen cap dagangannya.",
        ],
        "penalty_section": "Seksyen 9(3)(a) [Bukan Pertubuhan Perbadanan] / Seksyen 9(3)(b) [Pertubuhan Perbadanan] Akta 852",
        "penalty_first_offence": {
            "max_fine_rm": 20000,
            "max_jail_months": 12,
            "other_orders": "Pertubuhan Perbadanan: Denda RM20,000 hingga RM100,000 atau penjara maks 2 tahun",
            "verbatim_penalty": "Bukan Pertubuhan Perbadanan: Denda tidak melebihi RM20,000 atau penjara tidak melebihi 1 tahun | Pertubuhan Perbadanan: Denda RM20,000 hingga RM100,000 atau penjara tidak melebihi 2 tahun.",
        },
        "penalty_subsequent_offence": {
            "max_fine_rm": 30000,
            "max_jail_months": 24,
            "other_orders": "Pertubuhan Perbadanan: Denda RM50,000 hingga RM300,000 atau penjara maks 3 tahun",
            "verbatim_penalty": "Bukan Pertubuhan Perbadanan: Denda tidak melebihi RM30,000 atau penjara tidak melebihi 2 tahun | Pertubuhan Perbadanan: Denda RM50,000 hingga RM300,000.",
        },
        "compound_info": {
            "is_compoundable": False,
            "compound_authority_section": None,
            "compound_regulation_ref": "P.U. (A) 259/2024",
            "compound_amount_or_limit": "TIDAK BOLEH KOMPAUN — Wajib Sita (S.35/S.36) & Buka IP Terus",
            "max_compound_rm": None,
            "payment_days": None,
            "notice_section": "Seksyen 47 Akta 852 [P.U. (A) 264/2024] (Notis Hadir Mahkamah)",
        },
        "special_legal_requirements": ["Borang Senarai Benda Disita Seksyen 36 Akta 852", "Sijil Seksyen 90A(2)"],
        "mandatory_exhibits": [
            "Bahan promosi / sampel / gegantung tajaan yang disita + Borang Seksyen 36 Akta 852",
            "Gambar foto bukti berwarna + Sijil Seksyen 90A(2) & Carian SSM",
        ],
        "charge_sheet_template_bm": (
            "Bahawa kamu, pada [TARIKH], jam lebih kurang [MASA], bertempat di [TEMPAT_KEJADIAN], "
            "di dalam Daerah [DAERAH], di dalam Negeri [NEGERI], telah didapati mempromosikan atau menaja [BUTIRAN_PROMOSI] "
            "dengan menggunakan cap dagangan berkaitan produk merokok; dan oleh yang demikian kamu telah melakukan suatu kesalahan "
            "di bawah Seksyen 9(1) Akta Kawalan Produk Merokok Demi Kesihatan Awam 2024 [Akta 852] yang boleh dihukum di bawah Seksyen 9(3)(a)/(b) Akta yang sama."
        ),
        "source_section_doc_ids": ["AKTA_852__S9", "AKTA_852__S49"],
        "verified_status": "DRAFT_PENDING_REVIEW",
    },
    {
        "offence_id": "AKTA_852_S10_1",
        "statute_id": "AKTA_852",
        "offence_section": "Seksyen 10(1)",
        "read_together_with": ["Peraturan 6 P.U. (A) 260/2024", "Seksyen 49 Akta 852 (jika pertubuhan perbadanan)"],
        "offence_title": "Menjual atau mempamerkan secara terbuka produk tembakau, bahan merokok atau produk pengganti tembakau (vape) di tempat jualan",
        "target_offender": "PENJUAL_PENGILANG",
        "mandatory_elements": [
            {
                "element_no": 1,
                "description": "OKT ialah penjual, pemunya, penghuni atau pertubuhan perbadanan yang mengendalikan tempat jualan.",
                "must_prove": "Cetakan Carian Rasmi SSM (e-Info/MyData) + Lesen Perniagaan PBT + Rakaman S.112 KTJ.",
            },
            {
                "element_no": 2,
                "description": "Menjual atau mempamerkan bagi maksud penjualan produk tembakau, bahan merokok atau produk pengganti tembakau (vape).",
                "must_prove": "Produk merokok/vape fizikal yang disita di kaunter/rak pameran melalui Borang Senarai Benda Disita Seksyen 36 Akta 852.",
            },
            {
                "element_no": 3,
                "description": "Pameran dibuat secara terbuka / boleh dilihat dari luar atau dalam premis, melanggar syarat kabinet tertutup Peraturan 6 P.U. (A) 260/2024.",
                "must_prove": "Gambar foto sudut jauh dan dekat menunjukkan produk vape/rokok terdedah kepada pandangan pelanggan sebelum disita + Sijil S.90A(2) + Pelan Lakar.",
            },
        ],
        "explicit_exclusions_and_traps": [
            "Produk merokok yang disimpan di dalam kabinet tertutup legap (opaque) yang mematuhi Peraturan 6 P.U. (A) 260/2024 dan hanya dibuka seketika semasa mengambil stok untuk pelanggan dewasa BUKAN kesalahan pameran terbuka S.10(1).",
            "JANGAN petik 'Borang Sitaan Seksyen 38' — Seksyen 38 ialah kos memegang barang disita; borang sitaan sah ialah Seksyen 36 Akta 852.",
        ],
        "penalty_section": "Seksyen 10(2)(a) [Bukan Pertubuhan Perbadanan] / Seksyen 10(2)(b) [Pertubuhan Perbadanan] Akta 852",
        "penalty_first_offence": {
            "max_fine_rm": 20000,
            "max_jail_months": 12,
            "other_orders": "Pertubuhan Perbadanan: Denda RM20,000 hingga RM100,000 atau penjara maks 2 tahun",
            "verbatim_penalty": "Bukan Pertubuhan Perbadanan: Denda tidak melebihi RM20,000 atau penjara tidak melebihi 1 tahun atau kedua-duanya | Pertubuhan Perbadanan: Denda tidak kurang RM20,000 dan tidak melebihi RM100,000 atau penjara tidak melebihi 2 tahun.",
        },
        "penalty_subsequent_offence": {
            "max_fine_rm": 30000,
            "max_jail_months": 24,
            "other_orders": "Pertubuhan Perbadanan: Denda RM50,000 hingga RM300,000 atau penjara maks 3 tahun",
            "verbatim_penalty": "Bukan Pertubuhan Perbadanan: Denda tidak melebihi RM30,000 atau penjara tidak melebihi 2 tahun | Pertubuhan Perbadanan: Denda RM50,000 hingga RM300,000 atau penjara tidak melebihi 3 tahun.",
        },
        "compound_info": {
            "is_compoundable": False,
            "compound_authority_section": None,
            "compound_regulation_ref": "P.U. (A) 259/2024",
            "compound_amount_or_limit": "TIDAK BOLEH KOMPAUN (Seksyen 10(1) tiada dalam Jadual Pertama P.U. (A) 259/2024) — Wajib Sita (S.35/S.36) & Buka IP Terus",
            "max_compound_rm": None,
            "payment_days": None,
            "notice_section": "Seksyen 47 Akta 852 [P.U. (A) 264/2024] (Notis Hadir Mahkamah)",
        },
        "special_legal_requirements": [
            "Penyitaan di bawah Seksyen 35 & Borang Senarai Benda Disita Seksyen 36 Akta 852",
            "Sijil Seksyen 90A(2) Akta Keterangan 1950",
            "Seksyen 49 Akta 852 jika Pertubuhan Perbadanan",
        ],
        "mandatory_exhibits": [
            "Produk vape/rokok yang disita & dilak (P1–Pn)",
            "Borang Senarai Benda Disita Seksyen 36 Akta 852 bertandatangan terima",
            "Gambar foto berwarna bertarikh + Sijil Seksyen 90A(2) Akta Keterangan 1950",
            "Cetakan Carian Rasmi SSM (e-Info/MyData) + Sijil S.90A & Lesen PBT",
            "Pelan Lakar kedudukan rak/kaunter pameran bertandatangan IO",
        ],
        "charge_sheet_template_bm": (
            "Bahawa kamu, pada [TARIKH], jam lebih kurang [MASA], bertempat di [TEMPAT_KEJADIAN], "
            "di dalam Daerah [DAERAH], di dalam Negeri [NEGERI], telah didapati mempamerkan bagi maksud penjualan produk pengganti tembakau / bahan merokok "
            "secara terbuka di kaunter jualan yang melanggar Peraturan 6 Peraturan-Peraturan Kawalan Produk Merokok Demi Kesihatan Awam (Kawalan Penjualan) 2024 [P.U. (A) 260/2024]; "
            "dan oleh yang demikian kamu telah melakukan suatu kesalahan di bawah Seksyen 10(1) Akta Kawalan Produk Merokok Demi Kesihatan Awam 2024 [Akta 852] "
            "yang boleh dihukum di bawah Seksyen 10(2)(a)/(b) Akta yang sama."
        ),
        "source_section_doc_ids": ["AKTA_852__S10", "AKTA_852_PERATURAN_JUALAN_2024__P6", "AKTA_852__S26", "AKTA_852__S49"],
        "verified_status": "DRAFT_PENDING_REVIEW",
    },
    {
        "offence_id": "AKTA_852_S13_1",
        "statute_id": "AKTA_852",
        "offence_section": "Seksyen 13(1)",
        "read_together_with": ["Seksyen 49 Akta 852 (jika pertubuhan perbadanan)"],
        "offence_title": "Penjual: Menjual atau memberikan produk tembakau, bahan merokok atau produk pengganti tembakau kepada Orang Belum Dewasa (OBD < 18 tahun)",
        "target_offender": "PENJUAL_PENGILANG",
        "mandatory_elements": [
            {
                "element_no": 1,
                "description": "OKT menjual atau memberikan apa-apa produk tembakau, bahan merokok atau produk pengganti tembakau.",
                "must_prove": "Saksi transaksi jualan (PPKP atau rakaman S.112 OBD), resit bayaran/QR, atau rakaman CCTV + produk yang disita melalui Borang S.36.",
            },
            {
                "element_no": 2,
                "description": "Penerima/pembeli produk tersebut ialah seorang Orang Belum Dewasa (berumur di bawah 18 tahun pada tarikh kejadian).",
                "must_prove": "Salinan MyKad / Sijil Kelahiran / Pengesahan JPN pembeli yang membuktikan tarikh lahir belum mencapai umur 18 tahun pada tarikh kejadian.",
            },
        ],
        "explicit_exclusions_and_traps": [
            "Jika pembeli telah berumur 18 tahun ke atas pada tarikh kejadian mengikut tarikh lahir MyKad, kesalahan S.13(1) TIDAK wujud.",
            "Gagal melampirkan bukti rasmi tarikh lahir OBD (MyKad/JPN) akan menyebabkan pertuduhan S.13(1) gugur di mahkamah.",
        ],
        "penalty_section": "Seksyen 13(2)(a) [Bukan Pertubuhan Perbadanan] / Seksyen 13(2)(b) [Pertubuhan Perbadanan] Akta 852",
        "penalty_first_offence": {
            "max_fine_rm": 20000,
            "max_jail_months": 12,
            "other_orders": "Pertubuhan Perbadanan: Denda RM20,000 hingga RM100,000 atau penjara maks 2 tahun",
            "verbatim_penalty": "Bukan Pertubuhan Perbadanan: Denda tidak melebihi RM20,000 atau penjara tidak melebihi 1 tahun | Pertubuhan Perbadanan: Denda RM20,000 hingga RM100,000 atau penjara tidak melebihi 2 tahun.",
        },
        "penalty_subsequent_offence": {
            "max_fine_rm": 30000,
            "max_jail_months": 24,
            "other_orders": "Pertubuhan Perbadanan: Denda RM50,000 hingga RM300,000 atau penjara maks 3 tahun",
            "verbatim_penalty": "Bukan Pertubuhan Perbadanan: Denda tidak melebihi RM30,000 atau penjara tidak melebihi 2 tahun | Pertubuhan Perbadanan: Denda RM50,000 hingga RM300,000.",
        },
        "compound_info": {
            "is_compoundable": False,
            "compound_authority_section": None,
            "compound_regulation_ref": "P.U. (A) 259/2024",
            "compound_amount_or_limit": "TIDAK BOLEH KOMPAUN (S.13(1) tiada dalam Jadual Pertama P.U.(A) 259/2024) — Wajib Buka IP Terus untuk pendakwaan mahkamah",
            "max_compound_rm": None,
            "payment_days": None,
            "notice_section": "Seksyen 47 Akta 852 [P.U. (A) 264/2024] (Notis Hadir Mahkamah)",
        },
        "special_legal_requirements": [
            "Bukti rasmi umur OBD < 18 tahun (MyKad / Sijil Lahir / JPN)",
            "Borang Senarai Benda Disita Seksyen 36 Akta 852",
            "Rakaman S.112 KTJ OBD dengan kehadiran ibu bapa/penjaga (Akta 611)",
        ],
        "mandatory_exhibits": [
            "Salinan MyKad / Pengesahan JPN OBD (membuktikan umur di bawah 18 tahun pada tarikh kejadian)",
            "Produk rokok/vape yang dibeli & resit pembelian berlak KKM + Borang S.36",
            "Rakaman percakapan S.112 OBD dan PPKP saksi kejadian",
            "Gambar premis / kaunter jualan + Sijil Seksyen 90A(2)",
        ],
        "charge_sheet_template_bm": (
            "Bahawa kamu, pada [TARIKH], jam lebih kurang [MASA], bertempat di [TEMPAT_KEJADIAN], "
            "di dalam Daerah [DAERAH], di dalam Negeri [NEGERI], telah didapati menjual produk merokok kepada seorang Orang Belum Dewasa "
            "berumur di bawah 18 tahun; dan oleh yang demikian kamu telah melakukan suatu kesalahan di bawah Seksyen 13(1) Akta Kawalan Produk Merokok Demi Kesihatan Awam 2024 [Akta 852] "
            "yang boleh dihukum di bawah Seksyen 13(2)(a)/(b) Akta yang sama."
        ),
        "source_section_doc_ids": ["AKTA_852__S13", "AKTA_852__S49", "AKTA_611__S83"],
        "verified_status": "DRAFT_PENDING_REVIEW",
    },
    {
        "offence_id": "AKTA_852_S13_3",
        "statute_id": "AKTA_852",
        "offence_section": "Seksyen 13(3)",
        "read_together_with": ["Akta Kanak-Kanak 2001 [Akta 611]", "Seksyen 48 Akta 852"],
        "offence_title": "Orang Belum Dewasa (OBD < 18 tahun): Membeli produk tembakau, bahan merokok atau produk pengganti tembakau (vape)",
        "target_offender": "OBD_BAWAH_18",
        "mandatory_elements": [
            {
                "element_no": 1,
                "description": "Pembeli ialah seorang Orang Belum Dewasa (berumur di bawah 18 tahun pada tarikh kejadian).",
                "must_prove": "Salinan MyKad / Kad Pelajar / Sijil Lahir / Pengesahan JPN yang membuktikan umur < 18 tahun.",
            },
            {
                "element_no": 2,
                "description": "OBD benar-benar MEMBELI apa-apa produk tembakau, bahan merokok atau produk pengganti tembakau (vape) — bukan sekadar memiliki di dalam beg.",
                "must_prove": "Saksi transaksi pembelian, resit bayaran/QR, rakaman CCTV kedai atau pengakuan bertulis + produk yang dibeli.",
            },
        ],
        "explicit_exclusions_and_traps": [
            "Jika pelajar/OBD hanya memiliki vape di dalam beg sekolah TANPA sebarang bukti transaksi pembelian olehnya atau perbuatan menghisap/menggunakan, kesalahan S.13(3) dan S.17(1) TIDAK terbentuk.",
            "Siasat dan tuduh penjual di bawah Seksyen 13(1) (hukuman S.13(2)) jika kedai dikenal pasti menjual kepada OBD.",
        ],
        "penalty_section": "Seksyen 13(4) Akta 852",
        "penalty_first_offence": {
            "max_fine_rm": 500,
            "max_jail_months": None,
            "other_orders": "Perintah Khidmat Masyarakat (Akta 611 / Akta 593)",
            "verbatim_penalty": "Didenda tidak melebihi lima ratus ringgit (RM500.00) atau diperintahkan melaksanakan khidmat masyarakat.",
        },
        "penalty_subsequent_offence": None,
        "compound_info": {
            "is_compoundable": True,
            "compound_authority_section": "Seksyen 48(2) Akta 852",
            "compound_regulation_ref": "Jadual Pertama & Kedua P.U. (A) 259/2024",
            "compound_amount_or_limit": "Boleh dikompaun sehingga 50% daripada denda maks RM500 (= maks RM250.00, tawaran lazim RM50.00) dengan keizinan bertulis Pendakwa Raya (Borang 1 & Borang 2 P.U.(A) 259/2024) — tempoh 30 hari",
            "max_compound_rm": 250,
            "payment_days": 30,
            "notice_section": "Tawaran Kompaun Borang 2 P.U.(A) 259/2024 & Notis Hadir Mahkamah S.47 [P.U.(A) 264/2024]",
        },
        "special_legal_requirements": [
            "Akta Kanak-Kanak 2001 [Akta 611] — Makluman ibu bapa/penjaga, sekatan siaran media S.15 & tatacara S.83",
            "Keizinan bertulis Pendakwa Raya (Borang 1 P.U.(A) 259/2024) bagi Tawaran Kompaun S.48(2)",
        ],
        "mandatory_exhibits": [
            "Salinan MyKad / Pengesahan JPN OBD (< 18 tahun)",
            "Resit bayaran / CCTV transaksi pembelian & produk vape/rokok yang dibeli",
            "Rakaman percakapan S.112 saksi transaksi & OBD (dihadiri ibu bapa/penjaga)",
        ],
        "charge_sheet_template_bm": (
            "Bahawa kamu (seorang Orang Belum Dewasa berumur di bawah 18 tahun), pada [TARIKH], jam lebih kurang [MASA], bertempat di [TEMPAT_KEJADIAN], "
            "di dalam Daerah [DAERAH], di dalam Negeri [NEGERI], telah didapati membeli suatu produk pengganti tembakau (rokok elektronik / vape); "
            "dan oleh yang demikian kamu telah melakukan suatu kesalahan di bawah Seksyen 13(3) Akta Kawalan Produk Merokok Demi Kesihatan Awam 2024 [Akta 852] "
            "yang boleh dihukum di bawah Seksyen 13(4) Akta yang sama."
        ),
        "source_section_doc_ids": ["AKTA_852__S13", "AKTA_852__S48", "AKTA_852_PERATURAN_KOMPAUN_2024__P2", "AKTA_611__S83"],
        "verified_status": "DRAFT_PENDING_REVIEW",
    },
    {
        "offence_id": "AKTA_852_S16_2",
        "statute_id": "AKTA_852",
        "offence_section": "Seksyen 16(2)",
        "read_together_with": ["Perintah Kawalan Produk Merokok Demi Kesihatan Awam (Pengisytiharan Kawasan atau Tempat Larangan Merokok) 2024 [P.U. (A) 257/2024]"],
        "offence_title": "Merokok atau menggunakan produk pengganti tembakau (vape) di dalam kawasan atau tempat larangan merokok",
        "target_offender": "INDIVIDU",
        "mandatory_elements": [
            {
                "element_no": 1,
                "description": "Individu tersebut sedang merokok atau menggunakan produk merokok / rokok elektronik (memegang produk bernyala/aktif atau menghembus asap/wap).",
                "must_prove": "Pemerhatian langsung PPKP saksi + gambar foto kejadian + puntung rokok/peranti vape.",
            },
            {
                "element_no": 2,
                "description": "Lokasi kejadian ialah kawasan atau tempat larangan merokok yang diisytiharkan di bawah Seksyen 16(1) & Jadual P.U. (A) 257/2024 (cth. tempat makan, hospital, kompleks membeli-belah, termasuk jarak 3 meter dari sempadan tempat makan).",
                "must_prove": "Alamat tepat premis/kawasan larangan dalam P.U. (A) 257/2024 & gambar lokasi kejadian.",
            },
        ],
        "explicit_exclusions_and_traps": [
            "JANGAN tulis pertuduhan 'melanggar Seksyen 16(1) Akta 852' — Seksyen 16(1) hanyalah kuasa Menteri mewartakan tempat larangan; kesalahan perokok ialah Seksyen 16(2)!",
            "Merokok oleh orang dewasa di tepi jalan awam terbuka yang berada di luar radius 3 meter dari tempat makan dan BUKAN kawasan larangan dalam Jadual P.U. (A) 257/2024 BUKAN kesalahan di bawah Seksyen 16(2).",
        ],
        "penalty_section": "Seksyen 16(3) Akta 852",
        "penalty_first_offence": {
            "max_fine_rm": 5000,
            "max_jail_months": None,
            "other_orders": None,
            "verbatim_penalty": "Didenda tidak melebihi lima ribu ringgit (RM5,000.00).",
        },
        "penalty_subsequent_offence": None,
        "compound_info": {
            "is_compoundable": True,
            "compound_authority_section": "Seksyen 48(2) Akta 852",
            "compound_regulation_ref": "Jadual Pertama & Kedua P.U. (A) 259/2024",
            "compound_amount_or_limit": "Boleh dikompaun RM250.00 (had maks 50% daripada RM5,000 = RM2,500) dengan keizinan bertulis Pendakwa Raya (Borang 1 & Borang 2 P.U.(A) 259/2024) — tempoh bayaran 30 hari",
            "max_compound_rm": 2500,
            "payment_days": 30,
            "notice_section": "Tawaran Kompaun Borang 2 P.U.(A) 259/2024 & Notis Hadir Mahkamah S.47 [P.U.(A) 264/2024]",
        },
        "special_legal_requirements": [
            "Keizinan bertulis Pendakwa Raya (Borang 1) & Tawaran Kompaun (Borang 2) di bawah P.U. (A) 259/2024; Notis S.47 [P.U. (A) 264/2024] ialah Notis Hadir Mahkamah",
            "Tunggu tempoh kompaun 30 hari tamat & Sijil Unit Hasil PKD sebelum daftar mahkamah",
        ],
        "mandatory_exhibits": [
            "Salinan pendua Tawaran Kompaun / Notis Seksyen 47 bertandatangan terima / catatan saksi enggan tandatangan",
            "Gambar foto bukti perokok di kawasan larangan + Sijil Seksyen 90A(2)",
            "Sijil Pengesahan Unit Hasil PKD bahawa kompaun tidak dibayar selepas tamat 30 hari",
        ],
        "charge_sheet_template_bm": (
            "Bahawa kamu, pada [TARIKH], jam lebih kurang [MASA], bertempat di [TEMPAT_KEJADIAN], "
            "di dalam Daerah [DAERAH], di dalam Negeri [NEGERI], iaitu suatu tempat makan yang diisytiharkan sebagai kawasan larangan merokok "
            "di bawah Perintah Kawalan Produk Merokok Demi Kesihatan Awam (Pengisytiharan Kawasan atau Tempat Larangan Merokok) 2024 [P.U. (A) 257/2024], "
            "telah didapati merokok / menggunakan produk pengganti tembakau; dan oleh yang demikian kamu telah melakukan suatu kesalahan "
            "di bawah Seksyen 16(2) Akta Kawalan Produk Merokok Demi Kesihatan Awam 2024 [Akta 852] yang boleh dihukum di bawah Seksyen 16(3) Akta yang sama."
        ),
        "source_section_doc_ids": ["AKTA_852__S16", "AKTA_852_PERINTAH_LARANGAN_2024__P3", "AKTA_852__S47", "AKTA_852__S48", "AKTA_852_PERATURAN_KOMPAUN_2024__P2"],
        "verified_status": "DRAFT_PENDING_REVIEW",
    },
    {
        "offence_id": "AKTA_852_S17_1",
        "statute_id": "AKTA_852",
        "offence_section": "Seksyen 17(1)",
        "read_together_with": ["Akta Kanak-Kanak 2001 [Akta 611]"],
        "offence_title": "Orang Belum Dewasa (OBD < 18 tahun) merokok, mengunyah atau menggunakan produk tembakau atau produk pengganti tembakau (vape)",
        "target_offender": "OBD_BAWAH_18",
        "mandatory_elements": [
            {
                "element_no": 1,
                "description": "Pelaku ialah seorang Orang Belum Dewasa (berumur di bawah 18 tahun pada tarikh kejadian).",
                "must_prove": "Salinan MyKad / Kad Pelajar / Sijil Lahir / Pengesahan JPN yang membuktikan umur < 18 tahun.",
            },
            {
                "element_no": 2,
                "description": "Perbuatan aktif MEROKOK, MENGUNYAH atau MENGGUNAKAN dengan apa-apa cara apa-apa produk tembakau atau produk pengganti tembakau (vape).",
                "must_prove": "Keterangan saksi mata PPKP & gambar foto yang membuktikan OBD sedang menghisap, mengunyah atau menggunakan rokok/vape semasa kejadian (BUKAN sekadar dijumpai di dalam beg/poket).",
            },
        ],
        "explicit_exclusions_and_traps": [
            "PEMILIKAN SEMATA-MATA BUKAN KESALAHAN S.17(1) AKTA 852: Pemilikan pasif produk rokok/vape (contohnya vape dijumpai di dalam beg sekolah, poket atau loker semasa pemeriksaan guru/warden) TANPA bukti perbuatan menghisap, merokok, mengunyah, menggunakan (S.17(1)) atau membeli (S.13(3)) BUKAN suatu kesalahan di bawah Seksyen 17(1) Akta 852! WAJIB TOLAK pengeluaran Notis S.47 / Kompaun S.48 terhadap pelajar bagi pemilikan semata-mata.",
            "JANGAN gunakan Peraturan 13(1) PPKHT 2004 (kesalahan memiliki hasil tembakau oleh OBD) kerana PPKHT 2004 telah DIMANSUHKAN sepenuhnya oleh Akta 852.",
            "JANGAN tuduh OBD di bawah Seksyen 16(2) jika kejadian berlaku di tepi jalan terbuka yang bukan kawasan larangan P.U. (A) 257/2024.",
        ],
        "penalty_section": "Seksyen 17(2) Akta 852",
        "penalty_first_offence": {
            "max_fine_rm": 500,
            "max_jail_months": None,
            "other_orders": "Perintah Khidmat Masyarakat mengikut Akta Kanak-Kanak 2001 [Akta 611] atau KTJ [Akta 593]",
            "verbatim_penalty": "Didenda tidak melebihi lima ratus ringgit (RM500.00) atau diperintahkan untuk melaksanakan khidmat masyarakat.",
        },
        "penalty_subsequent_offence": None,
        "compound_info": {
            "is_compoundable": True,
            "compound_authority_section": "Seksyen 48(2) Akta 852",
            "compound_regulation_ref": "Jadual Pertama & Kedua P.U. (A) 259/2024",
            "compound_amount_or_limit": "Kompaun RM50.00 (had maks 50% daripada RM500 = RM250) dengan keizinan bertulis Pendakwa Raya (Borang 1 & Borang 2 P.U.(A) 259/2024) — tempoh 30 hari dengan pemakluman ibu bapa/penjaga",
            "max_compound_rm": 250,
            "payment_days": 30,
            "notice_section": "Tawaran Kompaun Borang 2 P.U.(A) 259/2024 & Notis Hadir Mahkamah S.47 [P.U.(A) 264/2024]",
        },
        "special_legal_requirements": [
            "Akta Kanak-Kanak 2001 [Akta 611] — Pemakluman & kehadiran ibu bapa/penjaga; sekatan media S.15; prosiding Mahkamah Bagi Kanak-Kanak",
            "Keizinan bertulis Pendakwa Raya (Borang 1 P.U.(A) 259/2024) bagi Tawaran Kompaun S.48(2); Notis S.47 ialah Notis Hadir Mahkamah",
            "Bukti rasmi tarikh lahir OBD (< 18 tahun)",
        ],
        "mandatory_exhibits": [
            "Salinan MyKad / Pengesahan JPN OBD (membuktikan umur di bawah 18 tahun)",
            "Salinan pendua Tawaran Kompaun / Notis Seksyen 47 bertandatangan terima / saksi + rekod makluman ibu bapa/penjaga",
            "Puntung rokok / peranti vape yang sedang dihisap/digunakan + Borang S.36 (jika disita)",
            "Gambar foto kejadian OBD sedang menghisap/menggunakan + Sijil Seksyen 90A(2)",
        ],
        "charge_sheet_template_bm": (
            "Bahawa kamu (seorang Orang Belum Dewasa berumur di bawah 18 tahun), pada [TARIKH], jam lebih kurang [MASA], bertempat di [TEMPAT_KEJADIAN], "
            "di dalam Daerah [DAERAH], di dalam Negeri [NEGERI], telah didapati merokok / menggunakan produk pengganti tembakau (rokok elektronik); "
            "dan oleh yang demikian kamu telah melakukan suatu kesalahan di bawah Seksyen 17(1) Akta Kawalan Produk Merokok Demi Kesihatan Awam 2024 [Akta 852] "
            "yang boleh dihukum di bawah Seksyen 17(2) Akta yang sama."
        ),
        "source_section_doc_ids": ["AKTA_852__S17", "AKTA_611__S11", "AKTA_611__S83", "AKTA_611__S91"],
        "verified_status": "DRAFT_PENDING_REVIEW",
    },
    {
        "offence_id": "AKTA_852_S18_1",
        "statute_id": "AKTA_852",
        "offence_section": "Seksyen 18(1)(a) / Seksyen 18(1)(b) / Seksyen 18(1)(c)",
        "read_together_with": ["P.U. (A) 258/2024"],
        "offence_title": "Pemunya atau penghuni kawasan larangan merokok gagal mempamerkan tanda amaran Kod QR [S.18(1)(a)], menyediakan bekas abu rokok/kemudahan merokok [S.18(1)(b)], atau gagal menghalang orang merokok [S.18(1)(c)]",
        "target_offender": "TUAN_PUNYA_PREMIS",
        "mandatory_elements": [
            {
                "element_no": 1,
                "description": "OKT ialah pemunya atau penghuni sesuatu premis yang diisytiharkan sebagai kawasan larangan merokok (P.U. (A) 257/2024).",
                "must_prove": "Lesen PBT / Carian SSM / bil utiliti atau pengakuan pemunya/penghuni premis.",
            },
            {
                "element_no": 2,
                "description": "Gagal mempamerkan tanda amaran larangan merokok mengikut spesifikasi Kod QR P.U. (A) 258/2024 [S.18(1)(a)], ATAU menyediakan bekas abu rokok/shisha [S.18(1)(b)].",
                "must_prove": "Gambar foto dinding/kaunter premis tanpa tanda amaran sah atau gambar bekas abu rokok di atas meja + Sijil S.90A(2).",
            },
        ],
        "explicit_exclusions_and_traps": [
            "Jangan campurkan kesalahan S.18(1)(a) [Tiada tanda amaran] dan S.18(1)(b) [Sedia bekas abu rokok] dalam satu pertuduhan Borang 114 yang sama (asingkan mengikut S.163 KTJ).",
        ],
        "penalty_section": "Seksyen 18(2) Akta 852",
        "penalty_first_offence": {
            "max_fine_rm": 5000,
            "max_jail_months": None,
            "other_orders": None,
            "verbatim_penalty": "Didenda tidak melebihi lima ribu ringgit (RM5,000.00).",
        },
        "penalty_subsequent_offence": None,
        "compound_info": {
            "is_compoundable": True,
            "compound_authority_section": "Seksyen 48(2) Akta 852",
            "compound_regulation_ref": "Jadual Pertama & Kedua P.U. (A) 259/2024",
            "compound_amount_or_limit": "Boleh dikompaun RM250.00 – RM2,500.00 (maks 50% daripada RM5,000) dengan keizinan bertulis Pendakwa Raya (Borang 1 & Borang 2 P.U.(A) 259/2024) — tempoh bayaran 30 hari",
            "max_compound_rm": 2500,
            "payment_days": 30,
            "notice_section": "Tawaran Kompaun Borang 2 P.U.(A) 259/2024 & Notis Hadir Mahkamah S.47 [P.U.(A) 264/2024]",
        },
        "special_legal_requirements": ["Keizinan bertulis Pendakwa Raya (Borang 1 & Borang 2 P.U.(A) 259/2024); Notis Hadir Mahkamah S.47", "Sijil Seksyen 90A(2)"],
        "mandatory_exhibits": [
            "Salinan pendua Tawaran Kompaun / Notis Seksyen 47 bertandatangan terima / saksi",
            "Gambar foto dinding tanpa tanda amaran Kod QR atau bekas abu rokok + Sijil S.90A(2)",
            "Carian SSM / Lesen PBT premis & Sijil Unit Hasil PKD (jika gagal bayar kompaun 30 hari)",
        ],
        "charge_sheet_template_bm": (
            "Bahawa kamu, sebagai pemunya/penghuni premis kawasan larangan merokok, pada [TARIKH], jam lebih kurang [MASA], bertempat di [TEMPAT_KEJADIAN], "
            "di dalam Daerah [DAERAH], di dalam Negeri [NEGERI], telah didapati gagal mempamerkan tanda amaran larangan merokok mengikut spesifikasi P.U. (A) 258/2024 "
            "[atau menyediakan kemudahan merokok iaitu bekas abu rokok]; dan oleh yang demikian kamu telah melakukan suatu kesalahan "
            "di bawah Seksyen 18(1)(a)/(b) Akta Kawalan Produk Merokok Demi Kesihatan Awam 2024 [Akta 852] yang boleh dihukum di bawah Seksyen 18(2) Akta yang sama."
        ),
        "source_section_doc_ids": [
            "AKTA_852__S18",
            "AKTA_852_PERATURAN_TANDA_2024__P2",
            "AKTA_852_PERATURAN_TANDA_2024__JADUAL_PERTAMA",
            "AKTA_852_PERINTAH_LARANGAN_2024__JADUAL_PERTAMA",
            "AKTA_852_PERINTAH_LARANGAN_2024__P2",
            "AKTA_852__S47",
            "AKTA_852__S48",
            "AKTA_852_PERATURAN_KOMPAUN_2024__P2",
        ],
        "verified_status": "DRAFT_PENDING_REVIEW",
    },
    # ---------------- AKTA 281 & PPKM 2009 & PPM 1985 ----------------
    {
        "offence_id": "AKTA_281_S11_2",
        "statute_id": "AKTA_281",
        "offence_section": "Seksyen 11",
        "read_together_with": ["Seksyen 33A Akta Makanan 1983 (jika syarikat)", "Seksyen 32A Akta Makanan 1983 (Izin Mendakwa TPR)"],
        "offence_title": "Gagal mematuhi Perintah Penutupan Premis Makanan Tidak Suci di bawah Seksyen 11 Akta Makanan 1983 [Akta 281]",
        "target_offender": "TUAN_PUNYA_PREMIS",
        "mandatory_elements": [
            {
                "element_no": 1,
                "description": "Perintah Penutupan Premis Makanan Tidak Suci di bawah Seksyen 11 Akta Makanan 1983 telah dikeluarkan secara sah dan diserahkan kepada tuan punya/pemunya/penghuni premis.",
                "must_prove": "Salinan asal Perintah Penutupan Seksyen 11 bertandatangan terima & gambar tampalan notis penutupan.",
            },
            {
                "element_no": 2,
                "description": "OKT mengingkari perintah tersebut dengan terus membuka atau menjalankan operasi premis makanan dalam tempoh penutupan berkuat kuasa.",
                "must_prove": "Gambar pemeriksaan susulan yang menunjukkan premis masih beroperasi/menjual makanan semasa tempoh perintah penutupan + rakaman S.112 saksi.",
            },
        ],
        "explicit_exclusions_and_traps": [
            "SEKSYEN 11 TIADA SUBSEKSYEN (1) ATAU (2): Kedua-dua kuasa perintah penutupan (maks 14 hari) dan hukuman keingkaran berada dalam satu seksyen tunggal iaitu Seksyen 11 Akta Makanan 1983 [Akta 281].",
            "JANGAN tuduh pemilik di bawah Seksyen 11 Akta 281 jika pemilik PATUH menutup premis! Kesalahan kebersihan premis itu sendiri didakwa di bawah Peraturan 11(1)(a) dibaca bersama Peraturan 15/16 PPKM 2009.",
            "Pemilik/pekerja masuk ke dalam premis semata-mata untuk menjalankan kerja pembersihan tanpa menjual/menyediakan makanan kepada pelanggan BUKAN kesalahan mengingkari perintah tutup Seksyen 11.",
        ],
        "penalty_section": "Seksyen 11 Akta Makanan 1983 [Akta 281]",
        "penalty_first_offence": {
            "max_fine_rm": None,
            "max_jail_months": 60,
            "other_orders": "Penjara tidak melebihi 5 tahun atau denda atau kedua-duanya",
            "verbatim_penalty": "Dipenjarakan selama tempoh tidak melebihi lima (5) tahun atau didenda atau kedua-duanya.",
        },
        "penalty_subsequent_offence": None,
        "compound_info": {
            "is_compoundable": False,
            "compound_authority_section": None,
            "compound_regulation_ref": None,
            "compound_amount_or_limit": "TIDAK BOLEH KOMPAUN — Wajib Buka IP Terus & Izin Mendakwa TPR Seksyen 32A",
            "max_compound_rm": None,
            "payment_days": None,
            "notice_section": None,
        },
        "special_legal_requirements": [
            "Izin Mendakwa Bertulis Pendakwa Raya di bawah Seksyen 32A Akta Makanan 1983",
            "Bukti serahan sah Perintah Penutupan Seksyen 11 Akta Makanan 1983",
        ],
        "mandatory_exhibits": [
            "Borang Pemeriksaan Premis Makanan (KMM) & Perintah Penutupan Seksyen 11 bertandatangan terima",
            "Gambar foto tampalan Notis Tutup & gambar bukti premis masih beroperasi semasa tempoh tutup + Sijil S.90A(2)",
            "Carian Rasmi SSM + Sijil S.90A & Izin Mendakwa TPR S.32A",
        ],
        "charge_sheet_template_bm": (
            "Bahawa kamu, pada [TARIKH], jam lebih kurang [MASA], bertempat di [TEMPAT_KEJADIAN], "
            "di dalam Daerah [DAERAH], di dalam Negeri [NEGERI], telah didapati gagal mematuhi Perintah Penutupan Premis Makanan Tidak Suci "
            "yang dikeluarkan di bawah Seksyen 11 Akta Makanan 1983; dan oleh yang demikian kamu telah melakukan suatu kesalahan "
            "di bawah Seksyen 11 Akta Makanan 1983 [Akta 281] dan boleh dihukum di bawah seksyen yang sama."
        ),
        "source_section_doc_ids": ["AKTA_281__S11", "AKTA_281__S32A"],
        "verified_status": "DRAFT_PENDING_REVIEW",
    },
    {
        "offence_id": "AKTA_281_S13_1",
        "statute_id": "AKTA_281",
        "offence_section": "Seksyen 13(1)",
        "read_together_with": ["Seksyen 19 & Seksyen 20 Akta Makanan 1983", "Seksyen 33A Akta Makanan 1983 (jika syarikat)"],
        "offence_title": "Menyediakan atau menjual makanan yang mengandungi bahan beracun, berbahaya atau memudaratkan kesihatan",
        "target_offender": "PENJUAL_PENGILANG",
        "mandatory_elements": [
            {
                "element_no": 1,
                "description": "OKT menyediakan atau menjual apa-apa makanan.",
                "must_prove": "Resit pembelian, sampel makanan yang diambil mengikut tatacara Seksyen 4–6 Akta 281, atau keterangan saksi pembeli/mangsa.",
            },
            {
                "element_no": 2,
                "description": "Makanan itu ada dalam atau padanya apa-apa bahan yang beracun, berbahaya atau selainnya memudaratkan kesihatan.",
                "must_prove": "Perakuan Juruanalisis Makanan Bertauliah di bawah Seksyen 19 Akta Makanan 1983 (dan laporan perubatan mangsa jika keracunan).",
            },
        ],
        "explicit_exclusions_and_traps": [
            "3 HAD MASA MANDATORI AKTA 281: (1) Perakuan Juruanalisis wajib dikeluarkan dalam 90 hari [Seksyen 19(1A)]; (2) Pendakwaan WAJIB dimulakan dalam had masa 150 hari dari tarikh sampel diambil [Seksyen 19(2)]; (3) Salinan Perakuan Juruanalisis WAJIB diserahkan kepada OKS sekurang-kurangnya 10 HARI GENAP sebelum tarikh perbicaraan [Seksyen 20(ii)]!",
            "Kes Seksyen 13(1) TIDAK BOLEH ditawarkan kompaun.",
        ],
        "penalty_section": "Seksyen 13(1) Akta Makanan 1983 [Akta 281]",
        "penalty_first_offence": {
            "max_fine_rm": 100000,
            "max_jail_months": 120,
            "other_orders": None,
            "verbatim_penalty": "Didenda tidak melebihi satu ratus ribu ringgit (RM100,000.00) atau dipenjarakan selama tempoh tidak melebihi sepuluh (10) tahun atau kedua-duanya.",
        },
        "penalty_subsequent_offence": None,
        "compound_info": {
            "is_compoundable": False,
            "compound_authority_section": None,
            "compound_regulation_ref": None,
            "compound_amount_or_limit": "TIDAK BOLEH DIKOMPAUN — Pendakwaan Terus Mahkamah Majistret (Sanksi TPR S.32A)",
            "max_compound_rm": None,
            "payment_days": None,
            "notice_section": None,
        },
        "special_legal_requirements": [
            "Perakuan Juruanalisis Makanan S.19 (dalam 90 hari S.19(1A)), Had Masa Pendakwaan 150 hari [S.19(2)] & Serahan ≥10 hari genap sebelum bicara [S.20(ii)]",
            "Izin Mendakwa Bertulis Pendakwa Raya di bawah Seksyen 32A Akta 281",
        ],
        "mandatory_exhibits": [
            "Sampel makanan berlak rasmi KKM + rekod rantaian stor",
            "Perakuan Juruanalisis Makanan Seksyen 19 Akta 281 + bukti serahan 10 hari genap S.20(ii) kepada OKS",
            "Resit pembelian, Laporan Pengadu (FIR), laporan perubatan mangsa & Izin Mendakwa TPR S.32A",
        ],
        "charge_sheet_template_bm": (
            "Bahawa kamu, pada [TARIKH], jam lebih kurang [MASA], bertempat di [TEMPAT_KEJADIAN], "
            "di dalam Daerah [DAERAH], di dalam Negeri [NEGERI], telah didapati menjual/menyediakan makanan iaitu [NAMA_MAKANAN] "
            "yang mengandungi bahan yang memudaratkan kesihatan; dan oleh yang demikian kamu telah melakukan suatu kesalahan "
            "di bawah Seksyen 13(1) Akta Makanan 1983 [Akta 281] dan boleh dihukum di bawah seksyen yang sama."
        ),
        "source_section_doc_ids": ["AKTA_281__S13", "AKTA_281__S19", "AKTA_281__S20", "AKTA_281__S32A"],
        "verified_status": "DRAFT_PENDING_REVIEW",
    },
    {
        "offence_id": "AKTA_281_S13A_2",
        "statute_id": "AKTA_281",
        "offence_section": "Seksyen 13A(2) / Seksyen 13A(1)",
        "read_together_with": ["Seksyen 19 & Seksyen 20 Akta Makanan 1983", "Seksyen 32A Akta Makanan 1983"],
        "offence_title": "Menyediakan atau menjual makanan yang mengandungi benda/jirim asing (paku, kaca, dawai, bangkai lipas) [S.13A(2)] atau bahan kotor/busuk/reput [S.13A(1)]",
        "target_offender": "PENJUAL_PENGILANG",
        "mandatory_elements": [
            {
                "element_no": 1,
                "description": "OKT menyediakan atau menjual apa-apa makanan.",
                "must_prove": "Sampel makanan, resit pembelian dan rakaman S.112 pengadu/pembeli.",
            },
            {
                "element_no": 2,
                "description": "Makanan mengandungi jirim asing (benda asing seperti paku, kaca, bangkai lipas) atau tidak layak dimakan manusia [S.13A(2)], ATAU mengandungi bahan berpenyakit, kotor, busuk atau reput [S.13A(1)].",
                "must_prove": "Eksibit fizikal makanan & benda asing berlak KKM + Perakuan Juruanalisis Makanan S.19 + gambar foto + Sijil S.90A(2).",
            },
        ],
        "explicit_exclusions_and_traps": [
            "BEZAKAN S.13A vs S.13B: Benda asing (paku/kaca/lipas) ialah Seksyen 13A(2) [maks RM30,000 / 5 tahun]; makanan busuk/kotor/reput ialah Seksyen 13A(1) [maks RM50,000 / 8 tahun]; manakala S.13B(1) adalah untuk makanan diaduk / bahan tambah terlarang / tidak ikut piawaian!",
            "Patuhi had masa 150 hari pendakwaan [S.19(2)] & serahan Perakuan Juruanalisis ≥10 hari genap sebelum bicara [S.20(ii)].",
        ],
        "penalty_section": "Seksyen 13A(2) [RM30,000 / 5 tahun] atau Seksyen 13A(1) [RM50,000 / 8 tahun] Akta Makanan 1983 [Akta 281]",
        "penalty_first_offence": {
            "max_fine_rm": 30000,
            "max_jail_months": 60,
            "other_orders": "Seksyen 13A(1) (kotor/busuk/reput): denda maks RM50,000 atau penjara maks 8 tahun atau kedua-duanya",
            "verbatim_penalty": "S.13A(2): Denda tidak melebihi RM30,000 atau penjara tidak melebihi 5 tahun atau kedua-duanya | S.13A(1): Denda tidak melebihi RM50,000 atau penjara tidak melebihi 8 tahun atau kedua-duanya.",
        },
        "penalty_subsequent_offence": None,
        "compound_info": {
            "is_compoundable": False,
            "compound_authority_section": None,
            "compound_regulation_ref": None,
            "compound_amount_or_limit": "TIDAK BOLEH DIKOMPAUN — Wajib Buka IP Terus & Izin Mendakwa TPR Seksyen 32A",
            "max_compound_rm": None,
            "payment_days": None,
            "notice_section": None,
        },
        "special_legal_requirements": [
            "Perakuan Juruanalisis Makanan S.19 (90 hari S.19(1A)), Had Masa 150 hari [S.19(2)] & Serahan ≥10 hari genap sebelum bicara [S.20(ii)]",
            "Izin Mendakwa Bertulis Pendakwa Raya di bawah Seksyen 32A Akta 281",
        ],
        "mandatory_exhibits": [
            "Eksibit fizikal makanan & benda asing (lipas/paku/kaca) dilak KKM",
            "Perakuan Juruanalisis Makanan Seksyen 19 Akta 281 + bukti serahan S.20(ii)",
            "Gambar foto berwarna + Sijil S.90A(2), Resit Pembelian & Rakaman S.112 Pengadu",
        ],
        "charge_sheet_template_bm": (
            "Bahawa kamu, pada [TARIKH], jam lebih kurang [MASA], bertempat di [TEMPAT_KEJADIAN], "
            "di dalam Daerah [DAERAH], di dalam Negeri [NEGERI], telah didapati menjual/menyediakan makanan iaitu [NAMA_MAKANAN] "
            "yang mengandungi jirim yang asing dan tidak layak dimakan oleh manusia; dan oleh yang demikian kamu telah melakukan suatu kesalahan "
            "di bawah Seksyen 13A(2) Akta Makanan 1983 [Akta 281] dan boleh dihukum di bawah seksyen yang sama."
        ),
        "source_section_doc_ids": ["AKTA_281__S13A", "AKTA_281__S19", "AKTA_281__S20", "AKTA_281__S32A"],
        "verified_status": "DRAFT_PENDING_REVIEW",
    },
    {
        "offence_id": "AKTA_281_S13B_1",
        "statute_id": "AKTA_281",
        "offence_section": "Seksyen 13B(1)",
        "read_together_with": ["Seksyen 13B(2)(d)/(e) Akta Makanan 1983", "Seksyen 19 & Seksyen 20 Akta Makanan 1983"],
        "offence_title": "Menyediakan atau menjual makanan yang diaduk (mengandungi bahan tambah terlarang atau tidak mematuhi piawaian makanan)",
        "target_offender": "PENJUAL_PENGILANG",
        "mandatory_elements": [
            {
                "element_no": 1,
                "description": "OKT menyediakan atau menjual apa-apa makanan.",
                "must_prove": "Sampel makanan, resit pembelian dan rakaman S.112 pengadu/pembeli.",
            },
            {
                "element_no": 2,
                "description": "Makanan tersebut diaduk mengikut Seksyen 13B(2) (cth. mengandungi bahan tambah makanan tidak dibenarkan [S.13B(2)(d)] atau tidak mematuhi piawaian ditetapkan [S.13B(2)(e)]).",
                "must_prove": "Sampel makanan berlak KKM + Perakuan Juruanalisis Makanan S.19 + gambar foto + Sijil S.90A(2).",
            },
        ],
        "explicit_exclusions_and_traps": [
            "Kes Seksyen 13B(1) TIDAK BOLEH ditawarkan kompaun — wajib buka IP dan dapatkan Izin Mendakwa TPR Seksyen 32A.",
            "Bagi kes benda asing (paku/kaca/lipas) atau makanan busuk/kotor, gunakan Seksyen 13A(2) atau Seksyen 13A(1) (BUKAN S.13B).",
            "Wajib patuhi had masa 150 hari [S.19(2)] & serahan Perakuan Juruanalisis ≥10 hari genap sebelum bicara [Seksyen 20(ii)].",
        ],
        "penalty_section": "Seksyen 13B(4) Akta Makanan 1983 [Akta 281]",
        "penalty_first_offence": {
            "max_fine_rm": 20000,
            "max_jail_months": 60,
            "other_orders": None,
            "verbatim_penalty": "Didenda tidak melebihi dua puluh ribu ringgit (RM20,000.00) atau dipenjarakan selama tempoh tidak melebihi lima (5) tahun atau kedua-duanya.",
        },
        "penalty_subsequent_offence": None,
        "compound_info": {
            "is_compoundable": False,
            "compound_authority_section": None,
            "compound_regulation_ref": None,
            "compound_amount_or_limit": "TIDAK BOLEH DIKOMPAUN — Wajib Buka IP Terus (Sanksi TPR S.32A)",
            "max_compound_rm": None,
            "payment_days": None,
            "notice_section": None,
        },
        "special_legal_requirements": [
            "Perakuan Juruanalisis Makanan S.19 (90 hari S.19(1A)), Had Masa 150 hari [S.19(2)] & Serahan ≥10 hari genap sebelum bicara [S.20(ii)]",
            "Izin Mendakwa Bertulis Pendakwa Raya di bawah Seksyen 32A Akta 281",
        ],
        "mandatory_exhibits": [
            "Sampel makanan yang dilak KKM",
            "Perakuan Juruanalisis Makanan Seksyen 19 Akta 281 + bukti serahan 10 hari genap S.20(ii) kepada OKS",
            "Gambar foto berwarna + Sijil S.90A(2), Resit Pembelian & Rakaman S.112 Pengadu",
        ],
        "charge_sheet_template_bm": (
            "Bahawa kamu, pada [TARIKH], jam lebih kurang [MASA], bertempat di [TEMPAT_KEJADIAN], "
            "di dalam Daerah [DAERAH], di dalam Negeri [NEGERI], telah didapati menjual makanan yang diaduk iaitu [NAMA_MAKANAN] "
            "yang tidak mematuhi piawaian ditetapkan; dan oleh yang demikian kamu telah melakukan suatu kesalahan "
            "di bawah Seksyen 13B(1) dibaca bersama Seksyen 13B(2)(e) Akta Makanan 1983 [Akta 281] yang boleh dihukum di bawah Seksyen 13B(4) Akta yang sama."
        ),
        "source_section_doc_ids": ["AKTA_281__S13B", "AKTA_281__S19", "AKTA_281__S20", "AKTA_281__S32A"],
        "verified_status": "DRAFT_PENDING_REVIEW",
    },
    {
        "offence_id": "PPKM_2009_P3_1",
        "statute_id": "PPKM_2009",
        "offence_section": "Peraturan 3(1) PPKM 2009",
        "read_together_with": ["P.U. (A) 95/2009"],
        "offence_title": "Menjalankan atau menggunakan premis makanan yang tidak berdaftar dengan KKM (FoSIM)",
        "target_offender": "TUAN_PUNYA_PREMIS",
        "mandatory_elements": [
            {
                "element_no": 1,
                "description": "OKT ialah tuan punya, pemunya atau penghuni yang menggunakan atau menjalankan premis makanan.",
                "must_prove": "Pemeriksaan operasi premis, Carian SSM / Lesen PBT.",
            },
            {
                "element_no": 2,
                "description": "Premis makanan tersebut tidak didaftarkan dengan KKM (FoSIM) di bawah Peraturan 3(1) PPKM 2009.",
                "must_prove": "Semakan sistem FoSIM KKM & gambar ketiadaan perakuan pendaftaran.",
            },
        ],
        "explicit_exclusions_and_traps": [
            "Jika premis sudah berdaftar dalam FoSIM tetapi gagal mempamerkan sijil di tempat mudah dilihat, caj di bawah Peraturan 8(1) PPKM 2009, BUKAN Peraturan 3(1).",
        ],
        "penalty_section": "Peraturan 3(2) PPKM 2009 [P.U. (A) 95/2009]",
        "penalty_first_offence": {
            "max_fine_rm": 10000,
            "max_jail_months": 24,
            "other_orders": None,
            "verbatim_penalty": "Didenda tidak melebihi sepuluh ribu ringgit (RM10,000.00) atau dipenjarakan selama tempoh tidak melebihi dua (2) tahun.",
        },
        "penalty_subsequent_offence": None,
        "compound_info": {
            "is_compoundable": True,
            "compound_authority_section": "Seksyen 33 Akta Makanan 1983",
            "compound_regulation_ref": "Jadual Keempat PPKM 2009 [P.U. (A) 95/2009]",
            "compound_amount_or_limit": "Boleh dikompaun melalui Notis Seksyen 32B Akta 281 (maksimum 50% denda) — tempoh 14 hari",
            "max_compound_rm": 5000,
            "payment_days": 14,
            "notice_section": "Seksyen 32B Akta Makanan 1983",
        },
        "special_legal_requirements": ["Notis Seksyen 32B Akta Makanan 1983", "Izin Mendakwa TPR S.32A jika dibawa ke mahkamah"],
        "mandatory_exhibits": [
            "Salinan Notis Seksyen 32B bertandatangan terima",
            "Cetakan semakan pendaftaran FoSIM + Sijil S.90A(2)",
            "Gambar premis beroperasi + Sijil S.90A(2) & Carian SSM",
        ],
        "charge_sheet_template_bm": (
            "Bahawa kamu, sebagai pemunya/penghuni premis makanan, pada [TARIKH], jam lebih kurang [MASA], bertempat di [TEMPAT_KEJADIAN], "
            "di dalam Daerah [DAERAH], di dalam Negeri [NEGERI], telah didapati menggunakan premis makanan yang tidak didaftarkan di bawah Peraturan-Peraturan Kebersihan Makanan 2009; "
            "dan oleh yang demikian kamu telah melakukan suatu kesalahan di bawah Peraturan 3(1) Peraturan-Peraturan Kebersihan Makanan 2009 [P.U. (A) 95/2009] "
            "yang boleh dihukum di bawah Peraturan 3(2) Peraturan yang sama."
        ),
        "source_section_doc_ids": ["PPKM_2009__P3", "AKTA_281__S32B", "AKTA_281__S33"],
        "verified_status": "DRAFT_PENDING_REVIEW",
    },
    {
        "offence_id": "PPKM_2009_P11_1",
        "statute_id": "PPKM_2009",
        "offence_section": "Peraturan 11(1)(a) dibaca bersama Peraturan 15 / 16 PPKM 2009",
        "read_together_with": ["P.U. (A) 95/2009", "Seksyen 11 Akta Makanan 1983 (Perintah Tutup jika <70% / tidak suci)"],
        "offence_title": "Tuan punya / pemunya / penghuni premis makanan gagal menyelenggara premis makanan dalam keadaan bersih dan bebas makhluk perosak (LILATI / najis tikus / lipas)",
        "target_offender": "TUAN_PUNYA_PREMIS",
        "mandatory_elements": [
            {
                "element_no": 1,
                "description": "OKT ialah tuan punya, pemunya atau penghuni premis makanan.",
                "must_prove": "Carian Rasmi SSM / Lesen PBT & Borang Pemeriksaan Premis Makanan (KMM).",
            },
            {
                "element_no": 2,
                "description": "Gagal menyelenggara atau mengekalkan premis makanan dalam keadaan bersih, kemas dan bebas daripada makhluk perosak (lipas, lalat, tikus) mengikut Peraturan 11(1)(a) dibaca bersama Peraturan 15/16 PPKM 2009.",
                "must_prove": "Gambar foto bukti kekotoran/najis tikus/lipas hidup di kawasan penyediaan/stor makanan + Sijil S.90A(2) + Pelan Lakar.",
            },
        ],
        "explicit_exclusions_and_traps": [
            "BEZAKAN SASARAN OKT: Peraturan 11(1)(a) dibaca bersama Peraturan 15/16 PPKM 2009 adalah terhadap TUAN PUNYA / PEMUNYA / PENGHUNI premis, manakala Peraturan 34(1) PPKM 2009 adalah kewajipan PENGENDALI MAKANAN — JANGAN campurkan kedua-duanya dalam satu pertuduhan!",
            "JANGAN hantar najis tikus ke makmal MKAK untuk analisis kimia — najis tikus dibuktikan dengan gambar foto berkapsyen + keterangan pemerhatian pegawai pemeriksa!",
            "Bagi kes wabak HFMD di Taska/Tadika (bukan premis makanan), JANGAN guna Seksyen 11 Akta 281 atau Peraturan 11 PPKM 2009 — gunakan Seksyen 18(1)(d) Akta 342!",
        ],
        "penalty_section": "Peraturan 11(2) PPKM 2009 [P.U. (A) 95/2009]",
        "penalty_first_offence": {
            "max_fine_rm": 10000,
            "max_jail_months": 24,
            "other_orders": "Serentak dengan Perintah Penutupan Premis Tidak Suci Seksyen 11 Akta Makanan 1983 (maks 14 hari)",
            "verbatim_penalty": "Didenda tidak melebihi sepuluh ribu ringgit (RM10,000.00) atau dipenjarakan selama tempoh tidak melebihi dua (2) tahun.",
        },
        "penalty_subsequent_offence": None,
        "compound_info": {
            "is_compoundable": True,
            "compound_authority_section": "Seksyen 33 Akta Makanan 1983",
            "compound_regulation_ref": "Jadual Keempat PPKM 2009 [P.U. (A) 95/2009]",
            "compound_amount_or_limit": "Boleh dikompaun melalui Notis Seksyen 32B & Seksyen 33 Akta Makanan 1983 (maks RM5,000) — tempoh 14 hari",
            "max_compound_rm": 5000,
            "payment_days": 14,
            "notice_section": "Seksyen 32B Akta Makanan 1983",
        },
        "special_legal_requirements": [
            "Notis Seksyen 32B Akta Makanan 1983",
            "Perintah Penutupan Premis Seksyen 11 Akta 281 (jika markah < 70% atau ada urungan LILATI aktif)",
            "Sijil Seksyen 90A(2) Akta Keterangan 1950",
        ],
        "mandatory_exhibits": [
            "Borang Pemeriksaan Premis Makanan (KMM) bertandatangan pemeriksa",
            "Salinan Perintah Penutupan Seksyen 11 & Notis Seksyen 32B bertandatangan terima",
            "Gambar foto bukti kekotoran/perosak + Sijil Seksyen 90A(2) & Pelan Lakar dapur",
        ],
        "charge_sheet_template_bm": (
            "Bahawa kamu, sebagai tuan punya/pemunya/penghuni premis makanan, pada [TARIKH], jam lebih kurang [MASA], bertempat di [TEMPAT_KEJADIAN], "
            "di dalam Daerah [DAERAH], di dalam Negeri [NEGERI], telah didapati gagal mengekalkan premis makanan tersebut dalam keadaan bersih dan bebas daripada makhluk perosak; "
            "dan oleh yang demikian kamu telah melakukan suatu kesalahan di bawah Peraturan 11(1)(a) dibaca bersama Peraturan 15 Peraturan-Peraturan Kebersihan Makanan 2009 [P.U. (A) 95/2009] "
            "yang boleh dihukum di bawah Peraturan 11(2) Peraturan yang sama."
        ),
        "source_section_doc_ids": ["PPKM_2009__P11", "PPKM_2009__P15", "PPKM_2009__P16", "AKTA_281__S11", "AKTA_281__S32B", "AKTA_281__S33"],
        "verified_status": "DRAFT_PENDING_REVIEW",
    },
    {
        "offence_id": "PPKM_2009_P30_1",
        "statute_id": "PPKM_2009",
        "offence_section": "Peraturan 30(1) PPKM 2009",
        "read_together_with": ["P.U. (A) 95/2009"],
        "offence_title": "Pengendali makanan bekerja tanpa menjalani Latihan Pengendali Makanan / tiada Sijil Latihan Pengendali Makanan (SLPM)",
        "target_offender": "PENGENDALI_MAKANAN",
        "mandatory_elements": [
            {
                "element_no": 1,
                "description": "OKT sedang bekerja secara aktif sebagai pengendali makanan (menyentuh, memasak, menyediakan atau menghidang makanan).",
                "must_prove": "Gambar foto OKT sedang aktif mengendalikan makanan semasa pemeriksaan + Sijil S.90A(2).",
            },
            {
                "element_no": 2,
                "description": "Gagal menjalani Latihan Pengendali Makanan atau tidak memiliki Sijil Latihan Pengendali Makanan (SLPM) daripada institusi diiktiraf KKM.",
                "must_prove": "Pemeriksaan rekod pekerja & pengakuan ketiadaan Sijil SLPM.",
            },
        ],
        "explicit_exclusions_and_traps": [
            "JANGAN keliru Peraturan 30(1) [Latihan SLPM] dengan Peraturan 31(1) [Suntikan Vaksin Anti-Tifoid]!",
            "Individu di premis yang tidak terlibat langsung dengan pengendalian makanan atau permukaan sentuhan makanan (cth. juruwang/pelanggan/penghantar stok luar yang tidak menyentuh makanan terbuka) bukan pengendali makanan.",
        ],
        "penalty_section": "Peraturan 30(3) PPKM 2009 [P.U. (A) 95/2009]",
        "penalty_first_offence": {
            "max_fine_rm": 10000,
            "max_jail_months": 24,
            "other_orders": None,
            "verbatim_penalty": "Didenda tidak melebihi sepuluh ribu ringgit (RM10,000.00) atau dipenjarakan selama tempoh tidak melebihi dua (2) tahun.",
        },
        "penalty_subsequent_offence": None,
        "compound_info": {
            "is_compoundable": True,
            "compound_authority_section": "Seksyen 33 Akta Makanan 1983",
            "compound_regulation_ref": "Jadual Keempat PPKM 2009 [P.U. (A) 95/2009]",
            "compound_amount_or_limit": "Boleh dikompaun melalui Notis Seksyen 32B Akta Makanan 1983 — tempoh 14 hari",
            "max_compound_rm": 5000,
            "payment_days": 14,
            "notice_section": "Seksyen 32B Akta Makanan 1983",
        },
        "special_legal_requirements": ["Notis Seksyen 32B Akta Makanan 1983", "Sijil Seksyen 90A(2)"],
        "mandatory_exhibits": [
            "Gambar foto pekerja sedang aktif mengendalikan makanan + Sijil Seksyen 90A(2)",
            "Salinan Notis Seksyen 32B bertandatangan terima / saksi",
            "Salinan MyKad / Pasport pekerja",
        ],
        "charge_sheet_template_bm": (
            "Bahawa kamu, sebagai seorang pengendali makanan, pada [TARIKH], jam lebih kurang [MASA], bertempat di [TEMPAT_KEJADIAN], "
            "di dalam Daerah [DAERAH], di dalam Negeri [NEGERI], telah didapati bekerja sebagai pengendali makanan tanpa menjalani latihan pengendali makanan "
            "dan memperolehi Sijil Latihan Pengendali Makanan yang diiktiraf; dan oleh yang demikian kamu telah melakukan suatu kesalahan "
            "di bawah Peraturan 30(1) Peraturan-Peraturan Kebersihan Makanan 2009 [P.U. (A) 95/2009] yang boleh dihukum di bawah Peraturan 30(3) Peraturan yang sama."
        ),
        "source_section_doc_ids": ["PPKM_2009__P30", "AKTA_281__S32B", "AKTA_281__S33"],
        "verified_status": "DRAFT_PENDING_REVIEW",
    },
    {
        "offence_id": "PPKM_2009_P31_1",
        "statute_id": "PPKM_2009",
        "offence_section": "Peraturan 31(1) PPKM 2009",
        "read_together_with": ["P.U. (A) 95/2009"],
        "offence_title": "Pengendali makanan bekerja tanpa pemeriksaan perubatan dan vaksinasi suntikan anti-tifoid yang sah",
        "target_offender": "PENGENDALI_MAKANAN",
        "mandatory_elements": [
            {
                "element_no": 1,
                "description": "OKT sedang bekerja secara aktif sebagai pengendali makanan di premis makanan.",
                "must_prove": "Gambar foto OKT sedang memasak/menyediakan/menghidang makanan + Sijil S.90A(2).",
            },
            {
                "element_no": 2,
                "description": "Tiada vaksinasi suntikan anti-tifoid yang sah (atau kad suntikan anti-tifoid telah tamat tempoh 3 tahun) oleh pengamal perubatan berdaftar.",
                "must_prove": "Semakan kad/rekod vaksinasi tifoid semasa pemeriksaan & rakaman S.112.",
            },
        ],
        "explicit_exclusions_and_traps": [
            "PERANGKAP NOMBOR PERATURAN: Kesalahan tiada suntikan anti-tifoid ialah Peraturan 31(1) PPKM 2009, BUKAN Peraturan 30(1) (Peraturan 30 ialah Sijil Latihan Pengendali Makanan SLPM)!",
            "Jika mahu menuduh majikan/pemunya premis kerana menggajikan pekerja tanpa suntikan anti-tifoid, gunakan Peraturan 11(1)(b) PPKM 2009 (hukuman Peraturan 11(2)) — BUKAN Peraturan 31(2) (Peraturan 31(2) ialah larangan pekerja berpenyakit berjangkit/luka terbuka bekerja, bukan kesalahan majikan tiada vaksin).",
        ],
        "penalty_section": "Peraturan 31(3) PPKM 2009 [P.U. (A) 95/2009]",
        "penalty_first_offence": {
            "max_fine_rm": 10000,
            "max_jail_months": 24,
            "other_orders": None,
            "verbatim_penalty": "Didenda tidak melebihi sepuluh ribu ringgit (RM10,000.00) atau dipenjarakan selama tempoh tidak melebihi dua (2) tahun.",
        },
        "penalty_subsequent_offence": None,
        "compound_info": {
            "is_compoundable": True,
            "compound_authority_section": "Seksyen 33 Akta Makanan 1983",
            "compound_regulation_ref": "Jadual Keempat PPKM 2009 [P.U. (A) 95/2009]",
            "compound_amount_or_limit": "Boleh dikompaun melalui Notis Seksyen 32B Akta Makanan 1983 — tempoh 14 hari",
            "max_compound_rm": 5000,
            "payment_days": 14,
            "notice_section": "Seksyen 32B Akta Makanan 1983",
        },
        "special_legal_requirements": ["Notis Seksyen 32B Akta Makanan 1983", "Sijil Seksyen 90A(2)"],
        "mandatory_exhibits": [
            "Gambar pekerja sedang aktif mengendalikan makanan + Sijil Seksyen 90A(2)",
            "Salinan Notis Seksyen 32B bertandatangan terima / saksi enggan tandatangan",
            "Salinan MyKad / Pasport pekerja & rekod semakan kad suntikan tifoid",
        ],
        "charge_sheet_template_bm": (
            "Bahawa kamu, sebagai seorang pengendali makanan, pada [TARIKH], jam lebih kurang [MASA], bertempat di [TEMPAT_KEJADIAN], "
            "di dalam Daerah [DAERAH], di dalam Negeri [NEGERI], telah didapati bekerja sebagai pengendali makanan tanpa diperiksa secara perubatan "
            "dan diberi vaksinasi anti-tifoid oleh pengamal perubatan berdaftar; dan oleh yang demikian kamu telah melakukan suatu kesalahan "
            "di bawah Peraturan 31(1) Peraturan-Peraturan Kebersihan Makanan 2009 [P.U. (A) 95/2009] yang boleh dihukum di bawah Peraturan 31(3) Peraturan yang sama."
        ),
        "source_section_doc_ids": ["PPKM_2009__P31", "AKTA_281__S32B", "AKTA_281__S33"],
        "verified_status": "DRAFT_PENDING_REVIEW",
    },
    {
        "offence_id": "PPKM_2009_P32_1",
        "statute_id": "PPKM_2009",
        "offence_section": "Peraturan 32(1) PPKM 2009",
        "read_together_with": ["P.U. (A) 95/2009"],
        "offence_title": "Pengendali makanan gagal memakai pakaian bersih, apron berwarna cerah, penutup kepala atau kasut bertutup",
        "target_offender": "PENGENDALI_MAKANAN",
        "mandatory_elements": [
            {
                "element_no": 1,
                "description": "OKT sedang aktif mengendalikan makanan di premis makanan.",
                "must_prove": "Gambar foto OKT sedang mengendalikan makanan + Sijil S.90A(2).",
            },
            {
                "element_no": 2,
                "description": "Tidak memakai apron berwarna cerah, penutup kepala atau kasut bertutup mengikut Peraturan 32(1) PPKM 2009.",
                "must_prove": "Gambar jelas pakaian/kasut/kepala pengendali semasa mengendalikan makanan.",
            },
        ],
        "explicit_exclusions_and_traps": [
            "PERANGKAP HAD DENDA: Denda maksimum bagi Peraturan 32(3) PPKM 2009 hanyalah RM1,000.00 (tiada hukuman penjara), berbeza dengan Peraturan 30/31/33 yang membawa denda RM10,000!",
        ],
        "penalty_section": "Peraturan 32(3) PPKM 2009 [P.U. (A) 95/2009]",
        "penalty_first_offence": {
            "max_fine_rm": 1000,
            "max_jail_months": None,
            "other_orders": None,
            "verbatim_penalty": "Didenda tidak melebihi satu ribu ringgit (RM1,000.00).",
        },
        "penalty_subsequent_offence": None,
        "compound_info": {
            "is_compoundable": True,
            "compound_authority_section": "Seksyen 33 Akta Makanan 1983",
            "compound_regulation_ref": "Jadual Keempat PPKM 2009 [P.U. (A) 95/2009]",
            "compound_amount_or_limit": "Boleh dikompaun melalui Notis Seksyen 32B Akta 281 (maksimum 50% daripada RM1,000 = RM500) — tempoh 14 hari",
            "max_compound_rm": 500,
            "payment_days": 14,
            "notice_section": "Seksyen 32B Akta Makanan 1983",
        },
        "special_legal_requirements": ["Notis Seksyen 32B Akta Makanan 1983"],
        "mandatory_exhibits": [
            "Gambar foto pengendali makanan tanpa apron/penutup kepala/kasut bertutup + Sijil S.90A(2)",
            "Salinan Notis Seksyen 32B bertandatangan terima",
        ],
        "charge_sheet_template_bm": (
            "Bahawa kamu, sebagai seorang pengendali makanan, pada [TARIKH], jam lebih kurang [MASA], bertempat di [TEMPAT_KEJADIAN], "
            "di dalam Daerah [DAERAH], di dalam Negeri [NEGERI], telah didapati tidak memakai apron berwarna cerah / penutup kepala / kasut bertutup "
            "semasa mengendalikan makanan; dan oleh yang demikian kamu telah melakukan suatu kesalahan di bawah Peraturan 32(1) Peraturan-Peraturan Kebersihan Makanan 2009 [P.U. (A) 95/2009] "
            "yang boleh dihukum di bawah Peraturan 32(3) Peraturan yang sama."
        ),
        "source_section_doc_ids": ["PPKM_2009__P32", "AKTA_281__S32B", "AKTA_281__S33"],
        "verified_status": "DRAFT_PENDING_REVIEW",
    },
    {
        "offence_id": "PPKM_2009_P33_1",
        "statute_id": "PPKM_2009",
        "offence_section": "Peraturan 33(1) PPKM 2009",
        "read_together_with": ["P.U. (A) 95/2009"],
        "offence_title": "Pengendali makanan gagal menjaga kebersihan diri (berkuku panjang/kotor, memakai cincin/barang kemas/jam tangan atau merokok semasa mengendalikan makanan)",
        "target_offender": "PENGENDALI_MAKANAN",
        "mandatory_elements": [
            {
                "element_no": 1,
                "description": "OKT sedang mengendalikan makanan di premis makanan.",
                "must_prove": "Gambar foto OKT sedang mengendalikan makanan + Sijil S.90A(2).",
            },
            {
                "element_no": 2,
                "description": "Tidak memastikan kuku pendek dan bersih, atau memakai barang kemas/cincin/jam tangan semasa mengendalikan makanan.",
                "must_prove": "Gambar jarak dekat tangan/kuku/cincin pengendali semasa menyentuh makanan.",
            },
        ],
        "explicit_exclusions_and_traps": [
            "Jangan campurkan kesalahan pakaian (Peraturan 32) dengan kebersihan diri/kuku/cincin (Peraturan 33) dalam satu pertuduhan.",
        ],
        "penalty_section": "Peraturan 33(2) PPKM 2009 [P.U. (A) 95/2009]",
        "penalty_first_offence": {
            "max_fine_rm": 10000,
            "max_jail_months": 24,
            "other_orders": None,
            "verbatim_penalty": "Didenda tidak melebihi sepuluh ribu ringgit (RM10,000.00) atau dipenjarakan selama tempoh tidak melebihi dua (2) tahun.",
        },
        "penalty_subsequent_offence": None,
        "compound_info": {
            "is_compoundable": True,
            "compound_authority_section": "Seksyen 33 Akta Makanan 1983",
            "compound_regulation_ref": "Jadual Keempat PPKM 2009 [P.U. (A) 95/2009]",
            "compound_amount_or_limit": "Boleh dikompaun melalui Notis Seksyen 32B Akta 281 — tempoh 14 hari",
            "max_compound_rm": 5000,
            "payment_days": 14,
            "notice_section": "Seksyen 32B Akta Makanan 1983",
        },
        "special_legal_requirements": ["Notis Seksyen 32B Akta Makanan 1983"],
        "mandatory_exhibits": [
            "Gambar foto jarak dekat kuku/barang kemas pengendali semasa mengendalikan makanan + Sijil S.90A(2)",
            "Salinan Notis Seksyen 32B bertandatangan terima",
        ],
        "charge_sheet_template_bm": (
            "Bahawa kamu, sebagai seorang pengendali makanan, pada [TARIKH], jam lebih kurang [MASA], bertempat di [TEMPAT_KEJADIAN], "
            "di dalam Daerah [DAERAH], di dalam Negeri [NEGERI], telah didapati tidak mengekalkan kebersihan diri iaitu menyimpan kuku panjang / memakai perhiasan diri "
            "semasa mengendalikan makanan; dan oleh yang demikian kamu telah melakukan suatu kesalahan di bawah Peraturan 33(1) Peraturan-Peraturan Kebersihan Makanan 2009 [P.U. (A) 95/2009] "
            "yang boleh dihukum di bawah Peraturan 33(2) Peraturan yang sama."
        ),
        "source_section_doc_ids": ["PPKM_2009__P33", "AKTA_281__S32B", "AKTA_281__S33"],
        "verified_status": "DRAFT_PENDING_REVIEW",
    },
    {
        "offence_id": "PPM_1985_P14_9",
        "statute_id": "PPM_1985",
        "offence_section": "Peraturan 14(9)(b) [Luput] / Peraturan 14(9)(a) [Ubah Tarikh] / Peraturan 14(7) [Tiada Tarikh] PPM 1985",
        "read_together_with": ["Seksyen 4(1)(f) Akta Makanan 1983", "Peraturan 397(2) PPM 1985"],
        "offence_title": "Menjual atau mendedahkan untuk jualan makanan yang telah tamat tarikh luput [P.14(9)(b)], mengubah/memadam tarikh luput [P.14(9)(a)], atau tanpa penandaan tarikh [P.14(7)]",
        "target_offender": "PENJUAL_PENGILANG",
        "mandatory_elements": [
            {
                "element_no": 1,
                "description": "OKT menjual, mengimport atau mendedahkan untuk jualan bungkusan makanan berlabel penandaan tarikh.",
                "must_prove": "Bungkusan makanan yang disita di rak jualan melalui Seksyen 4(1)(f) Akta Makanan 1983.",
            },
            {
                "element_no": 2,
                "description": "Tarikh akhir penggunaan pada bungkusan makanan telah luput pada tarikh pemeriksaan [P.14(9)(b)], ATAU penandaan tarikh telah diubah/dipadam/dipalsukan [P.14(9)(a)], ATAU bungkusan tiada penandaan tarikh wajib [P.14(7)].",
                "must_prove": "Gambar jarak dekat cetakan tarikh luput/kesan ubahan pada bungkusan berbanding tarikh pemeriksaan + Sijil S.90A(2).",
            },
        ],
        "explicit_exclusions_and_traps": [
            "BEZAKAN PERATURAN SUB-PERENGGAN: Menjual makanan luput ialah Peraturan 14(9)(b); mengubah/memadam/mengelirukan tarikh ialah Peraturan 14(9)(a); manakala menjual makanan berjadual tanpa penandaan tarikh ialah Peraturan 14(7) PPM 1985.",
            "Stok makanan tamat tempoh yang telah diasingkan di dalam stor pelupusan khas berlabel jelas 'UNTUK PELUPUSAN / TIDAK UNTUK DIJUAL' dan tidak didedahkan di ruang jualan tidak memenuhi unsur mendedahkan untuk jualan.",
        ],
        "penalty_section": "Peraturan 397(2) Peraturan-Peraturan Makanan 1985",
        "penalty_first_offence": {
            "max_fine_rm": 10000,
            "max_jail_months": 24,
            "other_orders": None,
            "verbatim_penalty": "Didenda tidak melebihi sepuluh ribu ringgit (RM10,000.00) atau dipenjarakan selama tempoh tidak melebihi dua (2) tahun.",
        },
        "penalty_subsequent_offence": None,
        "compound_info": {
            "is_compoundable": True,
            "compound_authority_section": "Seksyen 33 Akta Makanan 1983",
            "compound_regulation_ref": "Peraturan-Peraturan Makanan 1985",
            "compound_amount_or_limit": "Sita stok di bawah S.4(1)(f) Akta 281 + Notis S.32B atau Buka IP (kes ubah tarikh P.14(9)(a) digalakkan Buka IP)",
            "max_compound_rm": 5000,
            "payment_days": 14,
            "notice_section": "Seksyen 32B Akta Makanan 1983",
        },
        "special_legal_requirements": ["Senarai Sitaan Seksyen 4(1)(f) Akta Makanan 1983", "Sijil Seksyen 90A(2)"],
        "mandatory_exhibits": [
            "Bungkusan makanan tamat tarikh luput / diubah tarikh yang disita & dilak KKM + Borang Sitaan S.4(1)(f)",
            "Gambar foto jarak dekat tarikh luput pada bungkusan + Sijil S.90A(2) & Carian SSM",
        ],
        "charge_sheet_template_bm": (
            "Bahawa kamu, pada [TARIKH], jam lebih kurang [MASA], bertempat di [TEMPAT_KEJADIAN], "
            "di dalam Daerah [DAERAH], di dalam Negeri [NEGERI], telah didapati mendedahkan untuk jualan makanan berbungkus yang telah melampaui tarikh akhir penggunaan; "
            "dan oleh yang demikian kamu telah melakukan suatu kesalahan di bawah Peraturan 14(9)(b) Peraturan-Peraturan Makanan 1985 "
            "yang boleh dihukum di bawah Peraturan 397(2) Peraturan yang sama."
        ),
        "source_section_doc_ids": ["PPM_1985__P14", "PPM_1985__P397", "AKTA_281__S4"],
        "verified_status": "DRAFT_PENDING_REVIEW",
    },
    # ---------------- AKTA 154 ----------------
    {
        "offence_id": "AKTA_154_S13_1",
        "statute_id": "AKTA_154",
        "offence_section": "Seksyen 13(1)",
        "read_together_with": ["Seksyen 13(2) Akta 154", "Seksyen 22 Akta 154"],
        "offence_title": "Melakukan perbuatan atau membiarkan keadaan yang membiakkan serangga pembawa penyakit (larva/pupa nyamuk Aedes aegypti / Aedes albopictus)",
        "target_offender": "TUAN_PUNYA_PREMIS",
        "mandatory_elements": [
            {
                "element_no": 1,
                "description": "OKT ialah pemunya, penduduk atau orang yang melakukan/membiarkan keadaan pembiakan di premis/tapak pembinaan (tanggungan bersama S.22(1) Akta 154).",
                "must_prove": "Bil utiliti / Carian SSM / Lesen PBT / Pendaftaran CIDB atau Surat Setuju Terima (SST) kontraktor utama.",
            },
            {
                "element_no": 2,
                "description": "Wujud takungan air atau keadaan di premis yang mengandungi larva atau pupa serangga hidup semasa pemeriksaan.",
                "must_prove": "Botol spesimen larva yang dikutip di hadapan penghuni, dilabel dan dilak dengan nombor siri lak KKM + Borang Mengambil Larva + Pelan Lakar.",
            },
            {
                "element_no": 3,
                "description": "Spesimen larva/pupa tersebut disahkan sebagai serangga pembawa penyakit (Aedes aegypti / Aedes albopictus).",
                "must_prove": "Sijil / Laporan Perakuan Pengecaman Spesies Entomologi dengan nombor siri lak botol yang 100% sepadan.",
            },
        ],
        "explicit_exclusions_and_traps": [
            "Takungan air kosong yang TIADA penemuan larva/pupa hidup atau keputusan Makmal Entomologi mengesahkan spesies BUKAN serangga pembawa penyakit tidak boleh dikompaun/dituduh di bawah Seksyen 13(1) (hanya boleh dikeluarkan Perintah Pencegahan Seksyen 8(1)).",
            "Kesalahan pembiakan di kawasan luar kawalan pemunya/penduduk (S.22(1): dibuktikan dilakukan tanpa pengetahuan, persetujuan & pembiaran serta segala usaha wajar telah diambil) perlu disiasat terhadap pihak yang bertanggungjawab.",
            "HAD MUTLAK KOMPAUN S.25 AKTA 154: Amaun kompaun Seksyen 25 Akta 154 TIDAK BOLEH melebihi RM500.00. Sebarang notis kompaun > RM500 di bawah Akta 154 adalah TIDAK SAH.",
            "Bagi tapak pembinaan atau kesalahan berulang S.23(b): TIADA tawaran kompaun RM500 — wajib keluarkan Perintah Seksyen 8(1) dan Buka IP Terus ke mahkamah.",
        ],
        "penalty_section": "Seksyen 23(a) [Kesalahan Pertama] / Seksyen 23(b) [Kesalahan Kedua/Berikutnya] Akta 154",
        "penalty_first_offence": {
            "max_fine_rm": 10000,
            "max_jail_months": 24,
            "other_orders": "Kesalahan berterusan: Denda selanjutnya maks RM500 sehari [Seksyen 23(c)]",
            "verbatim_penalty": "Didenda tidak melebihi sepuluh ribu ringgit (RM10,000.00) atau dipenjarakan selama tempoh tidak melebihi dua (2) tahun atau kedua-duanya.",
        },
        "penalty_subsequent_offence": {
            "max_fine_rm": 50000,
            "max_jail_months": 60,
            "other_orders": "Denda selanjutnya maks RM500 sehari bagi kesalahan berterusan",
            "verbatim_penalty": "Didenda tidak melebihi lima puluh ribu ringgit (RM50,000.00) atau dipenjarakan selama tempoh tidak melebihi lima (5) tahun atau kedua-duanya.",
        },
        "compound_info": {
            "is_compoundable": True,
            "compound_authority_section": "Seksyen 25 Akta 154",
            "compound_regulation_ref": "Peraturan-Peraturan Pemusnahan Serangga Pembawa Penyakit (Mengkompaun Kesalahan) 1975",
            "compound_amount_or_limit": "Maksimum RM500.00 (had mutlak S.25 Akta 154 — tempoh 14 hari) bagi premis biasa kesalahan pertama; TIADA kompaun bagi tapak pembinaan atau kes berulang S.23(b) (Buka IP Terus)",
            "max_compound_rm": 500,
            "payment_days": 14,
            "notice_section": "Seksyen 25 Akta 154",
        },
        "special_legal_requirements": [
            "Sijil Perakuan Pengecaman Spesies Entomologi (nombor lak botol wajib sepadan 100%)",
            "Sijil Seksyen 90A(2) Akta Keterangan 1950",
            "Izin Bertulis Pendakwa Raya",
        ],
        "mandatory_exhibits": [
            "Botol spesimen larva berlak KKM + Borang Kutipan Larva bertandatangan penghuni",
            "Sijil Perakuan Entomologi yang mengesahkan spesies Aedes aegypti / Aedes albopictus",
            "Gambar foto bukti bekas pembiakan & lokasi + Sijil Seksyen 90A(2)",
            "Pelan Lakar kedudukan bekas bertandatangan IO & bukti hakmilik/penghuni (bil/SSM/CIDB)",
        ],
        "charge_sheet_template_bm": (
            "Bahawa kamu, sebagai pemunya/penghuni premis, pada [TARIKH], jam lebih kurang [MASA], bertempat di [TEMPAT_KEJADIAN], "
            "di dalam Daerah [DAERAH], di dalam Negeri [NEGERI], telah didapati membiarkan air bertakung di dalam bekas yang mewujudkan keadaan "
            "membiakkan serangga pembawa penyakit iaitu larva nyamuk Aedes aegypti; dan oleh yang demikian kamu telah melakukan suatu kesalahan "
            "di bawah Seksyen 13(1) dibaca bersama Seksyen 13(2) Akta Pemusnahan Serangga Pembawa Penyakit 1975 [Akta 154] "
            "yang boleh dihukum di bawah Seksyen 23(a) Akta yang sama."
        ),
        "source_section_doc_ids": ["AKTA_154__S13", "AKTA_154__S23", "AKTA_154__S25"],
        "verified_status": "DRAFT_PENDING_REVIEW",
    },
    {
        "offence_id": "AKTA_154_S8_8",
        "statute_id": "AKTA_154",
        "offence_section": "Seksyen 8(8)",
        "read_together_with": ["Seksyen 8(1) Akta 154", "Seksyen 23 Akta 154"],
        "offence_title": "Gagal mematuhi kehendak Perintah Bertulis Seksyen 8(1) Akta 154 (langkah pemusnahan / penutupan sementara tapak binaan)",
        "target_offender": "TUAN_PUNYA_PREMIS",
        "mandatory_elements": [
            {
                "element_no": 1,
                "description": "Perintah bertulis di bawah Seksyen 8(1) Akta 154 telah dikeluarkan dan disampaikan secara sah kepada pemunya/penghuni/kontraktor.",
                "must_prove": "Salinan asal Perintah Seksyen 8(1) bertandatangan terima atau bukti penampalan rasmi di premis.",
            },
            {
                "element_no": 2,
                "description": "OKT gagal mematuhi kehendak perintah tersebut selepas tamat tempoh atau terus menjalankan kerja di tapak yang ditutup.",
                "must_prove": "Laporan pemeriksaan ulangan + gambar foto bertarikh + rakaman S.112 saksi PPKP.",
            },
        ],
        "explicit_exclusions_and_traps": [
            "JANGAN tulis pertuduhan 'ingkar perintah di bawah Seksyen 8(2) Akta 154' — kesalahan ingkar perintah Seksyen 8(1) ialah di bawah Seksyen 8(8) Akta 154!",
            "Jangan campurkan pertuduhan Seksyen 8(8) [Ingkar Perintah] dan Seksyen 13(1) [Pembiakan] dalam satu Borang 114 (Duplicity S.163 KTJ).",
        ],
        "penalty_section": "Seksyen 23(a)/(b)/(c) Akta 154",
        "penalty_first_offence": {
            "max_fine_rm": 10000,
            "max_jail_months": 24,
            "other_orders": "Denda selanjutnya maks RM500 sehari bagi kesalahan berterusan",
            "verbatim_penalty": "Didenda tidak melebihi sepuluh ribu ringgit (RM10,000.00) atau dipenjarakan selama tempoh tidak melebihi dua (2) tahun atau kedua-duanya.",
        },
        "penalty_subsequent_offence": {
            "max_fine_rm": 50000,
            "max_jail_months": 60,
            "other_orders": None,
            "verbatim_penalty": "Didenda tidak melebihi lima puluh ribu ringgit (RM50,000.00) atau dipenjarakan selama tempoh tidak melebihi lima (5) tahun atau kedua-duanya.",
        },
        "compound_info": {
            "is_compoundable": False,
            "compound_authority_section": None,
            "compound_regulation_ref": None,
            "compound_amount_or_limit": "Buka IP Terus (Kes ingkar perintah S.8(1))",
            "max_compound_rm": None,
            "payment_days": None,
            "notice_section": "Seksyen 8(1) Akta 154",
        },
        "special_legal_requirements": ["Bukti penyampaian sah Perintah Seksyen 8(1) Akta 154", "Sijil Seksyen 90A(2)"],
        "mandatory_exhibits": [
            "Salinan Perintah Seksyen 8(1) bertandatangan terima / bukti tampalan",
            "Gambar foto pemeriksaan ulangan selepas tempoh perintah + Sijil S.90A(2)",
            "Carian SSM / CIDB & Rakaman S.112 saksi PPKP",
        ],
        "charge_sheet_template_bm": (
            "Bahawa kamu, pada [TARIKH], jam lebih kurang [MASA], bertempat di [TEMPAT_KEJADIAN], "
            "di dalam Daerah [DAERAH], di dalam Negeri [NEGERI], telah didapati gagal mematuhi kehendak perintah bertulis "
            "yang disampaikan kepada kamu di bawah Seksyen 8(1) Akta Pemusnahan Serangga Pembawa Penyakit 1975; "
            "dan oleh yang demikian kamu telah melakukan suatu kesalahan di bawah Seksyen 8(8) Akta 154 yang boleh dihukum di bawah Seksyen 23(a) Akta yang sama."
        ),
        "source_section_doc_ids": ["AKTA_154__S8", "AKTA_154__S23"],
        "verified_status": "DRAFT_PENDING_REVIEW",
    },
    {
        "offence_id": "AKTA_154_S21",
        "statute_id": "AKTA_154",
        "offence_section": "Seksyen 21",
        "read_together_with": ["Seksyen 5 & Seksyen 22A Akta 154"],
        "offence_title": "Menghalang atau menggertak pegawai diberi kuasa dalam menjalankan pemeriksaan atau semburan kabus (fogging) kawalan vektor",
        "target_offender": "INDIVIDU",
        "mandatory_elements": [
            {
                "element_no": 1,
                "description": "Pegawai diberi kuasa telah memperkenalkan diri dengan Kad Kuasa Rasmi KKM untuk menjalankan tugas sah di bawah Akta 154.",
                "must_prove": "Salinan Kad Kuasa KKM, jadual operasi kawalan vektor/wabak denggi, & Diari Siasatan.",
            },
            {
                "element_no": 2,
                "description": "OKT secara sengaja menghalang, menggalang atau menggertak pegawai daripada memasuki atau menjalankan pemeriksaan/semburan.",
                "must_prove": "Laporan Polis, rakaman S.112 pasukan vektor/PPKP saksi, dan gambar/video lokasi.",
            },
        ],
        "explicit_exclusions_and_traps": [
            "Premis berkunci tanpa penghuni di dalam rumah pada waktu lawatan BUKAN kesalahan menghalang pegawai di bawah Seksyen 21.",
            "SEKSYEN 21 MEMPUNYAI HUKUMAN SENDIRI: Jangan rujuk Seksyen 23(a)/(b) bagi kesalahan menghalang di bawah Seksyen 21 Akta 154 — Seksyen 21 memperuntukkan hukumannya sendiri (denda maks RM10,000 atau penjara maks 2 tahun atau kedua-duanya).",
        ],
        "penalty_section": "Seksyen 21 Akta 154",
        "penalty_first_offence": {
            "max_fine_rm": 10000,
            "max_jail_months": 24,
            "other_orders": None,
            "verbatim_penalty": "Didenda tidak melebihi sepuluh ribu ringgit (RM10,000.00) atau dipenjarakan selama tempoh tidak melebihi dua (2) tahun atau kedua-duanya.",
        },
        "penalty_subsequent_offence": None,
        "compound_info": {
            "is_compoundable": False,
            "compound_authority_section": None,
            "compound_regulation_ref": None,
            "compound_amount_or_limit": "TIDAK BOLEH DIKOMPAUN (Kes menghalang penjawat awam) — Buka IP Terus & Laporan Polis",
            "max_compound_rm": None,
            "payment_days": None,
            "notice_section": None,
        },
        "special_legal_requirements": ["Laporan Polis", "Rakaman S.112 KTJ saksi pasukan penguat kuasa", "Izin Mendakwa Pendakwa Raya Seksyen 22A Akta 154"],
        "mandatory_exhibits": [
            "Laporan Polis & Diari Siasatan pasukan kawalan vektor",
            "Gambar lokasi kejadian + Sijil S.90A(2) & Salinan Kad Kuasa PPKP",
            "Rakaman percakapan S.112 KTJ PPKP & Pembantu Kesihatan Awam",
        ],
        "charge_sheet_template_bm": (
            "Bahawa kamu, pada [TARIKH], jam lebih kurang [MASA], bertempat di [TEMPAT_KEJADIAN], "
            "di dalam Daerah [DAERAH], di dalam Negeri [NEGERI], telah didapati menghalang seorang pegawai diberi kuasa daripada menjalankan tugasnya "
            "di bawah Akta Pemusnahan Serangga Pembawa Penyakit 1975; dan oleh yang demikian kamu telah melakukan suatu kesalahan "
            "di bawah Seksyen 21 Akta 154 dan boleh dihukum di bawah seksyen yang sama."
        ),
        "source_section_doc_ids": ["AKTA_154__S21"],
        "verified_status": "DRAFT_PENDING_REVIEW",
    },
    # ---------------- AKTA 342 ----------------
    {
        "offence_id": "AKTA_342_S10_2",
        "statute_id": "AKTA_342",
        "offence_section": "Seksyen 10(2)",
        "read_together_with": ["Peraturan-Peraturan Pencegahan dan Pengawalan Penyakit Berjangkit (Borang Notis) 2005"],
        "offence_title": "Pengamal perubatan gagal memberi notifikasi penyakit berjangkit (Borang Notis / e-Notifikasi) kepada Pegawai Kesihatan dalam tempoh ditetapkan",
        "target_offender": "INDIVIDU",
        "mandatory_elements": [
            {
                "element_no": 1,
                "description": "OKT ialah seorang pengamal perubatan berdaftar yang merawat atau mengetahui kewujudan sesuatu penyakit berjangkit dalam Jadual Pertama Akta 342.",
                "must_prove": "Rekod pendaftaran klinikal pesakit, keputusan makmal diagnostik & Sijil APC doktor.",
            },
            {
                "element_no": 2,
                "description": "Gagal memberi notis dengan serta-merta / dalam tempoh statutori kepada Pegawai Kesihatan terdekat mengikut Peraturan Borang Notis 2005.",
                "must_prove": "Cetakan log masa penghantaran e-Notifikasi berbanding tarikh/masa diagnosis klinikal + Sijil S.90A(2).",
            },
        ],
        "explicit_exclusions_and_traps": [
            "Kes yang masih dalam siasatan awal dan belum mempunyai diagnosis klinikal/makmal yang menimbulkan sebab munasabah untuk mempercayai wujud penyakit berjangkit perlu disahkan masa diagnosisnya.",
        ],
        "penalty_section": "Seksyen 24 Akta 342 (Pindaan Akta A1742)",
        "penalty_first_offence": {
            "max_fine_rm": 10000,
            "max_jail_months": 24,
            "other_orders": "Pertubuhan Perbadanan: Denda maks RM100,000",
            "verbatim_penalty": "Individu: Didenda tidak melebihi RM10,000.00 atau dipenjarakan tidak melebihi dua (2) tahun atau kedua-duanya.",
        },
        "penalty_subsequent_offence": None,
        "compound_info": {
            "is_compoundable": True,
            "compound_authority_section": "Seksyen 25 Akta 342 (Pindaan Akta A1742)",
            "compound_regulation_ref": "Jadual Pertama P.U. (A) 139/2025",
            "compound_amount_or_limit": "Boleh dikompaun dengan keizinan bertulis Pendakwa Raya: maks RM5,000 (individu) / RM50,000 (pertubuhan perbadanan)",
            "max_compound_rm": 5000,
            "payment_days": 14,
            "notice_section": "Seksyen 25 Akta 342",
        },
        "special_legal_requirements": [
            "Keizinan Bertulis Pendakwa Raya wajib diperoleh sebelum mengeluarkan tawaran kompaun Seksyen 25 Akta 342 (Akta A1742)",
            "Sijil Seksyen 90A(2) bagi cetakan e-Notifikasi",
        ],
        "mandatory_exhibits": [
            "Cetakan e-Notifikasi & log masa pendaftaran + Sijil S.90A(2)",
            "Salinan rekod perubatan/makmal pesakit & Rakaman S.112 pengamal perubatan",
        ],
        "charge_sheet_template_bm": (
            "Bahawa kamu, sebagai seorang pengamal perubatan yang merawat seorang pesakit yang menghidap penyakit berjangkit, "
            "pada [TARIKH], jam lebih kurang [MASA], bertempat di [TEMPAT_KEJADIAN], di dalam Daerah [DAERAH], di dalam Negeri [NEGERI], "
            "telah didapati gagal memberi notis mengenai kewujudan penyakit berjangkit tersebut kepada Pegawai Kesihatan dalam tempoh yang ditetapkan; "
            "dan oleh yang demikian kamu telah melakukan suatu kesalahan di bawah Seksyen 10(2) Akta Pencegahan dan Pengawalan Penyakit Berjangkit 1988 [Akta 342] "
            "yang boleh dihukum di bawah Seksyen 24 Akta yang sama."
        ),
        "source_section_doc_ids": ["AKTA_342__S10", "AKTA_342__S24", "AKTA_342__S25"],
        "verified_status": "DRAFT_PENDING_REVIEW",
    },
    {
        "offence_id": "AKTA_342_S12_1",
        "statute_id": "AKTA_342",
        "offence_section": "Seksyen 12(1)",
        "read_together_with": ["Seksyen 12(3) Akta 342"],
        "offence_title": "Orang yang mengetahui dirinya menghidap penyakit berjangkit mendedahkan orang lain kepada risiko jangkitan melalui kehadiran atau kelakuannya di tempat awam",
        "target_offender": "INDIVIDU",
        "mandatory_elements": [
            {
                "element_no": 1,
                "description": "OKT disahkan menghidap penyakit berjangkit melalui ujian makmal/klinikal rasmi DAN mengetahui atau mempunyai sebab mempercayai dirinya dijangkiti.",
                "must_prove": "Keputusan makmal rasmi fasiliti kesihatan, e-Notifikasi S.10, dan bukti pemakluman keputusan kepada OKT sebelum kejadian.",
            },
            {
                "element_no": 2,
                "description": "OKT hadir atau berkelakuan di tempat awam / tempat dikongsi bersama selain ahli keluarga dengan cara yang mendedahkan orang lain kepada risiko jangkitan.",
                "must_prove": "Bukti kehadiran aktif di tempat awam tanpa langkah perlindungan/arahan perubatan.",
            },
        ],
        "explicit_exclusions_and_traps": [
            "Seksyen 12(4) Akta 342: Orang yang melalui tempat awam bagi maksud mendapatkan rawatan perubatan mengikut arahan pegawai diberi kuasa BUKAN melakukan kesalahan di bawah Seksyen 12(1).",
            "TIDAK BOLEH DIKOMPAUN: Seksyen 12(1)/(3) TIDAK disenaraikan dalam Jadual Pertama P.U. (A) 139/2025! Sebarang notis kompaun di bawah Seksyen 12(1) adalah TIDAK SAH (Ultra Vires).",
            "Bagi kes COVID-19 pasca 15 Julai 2024 (tiada HSO mandatori), ujian RTK-Ag kendiri di rumah BUKAN pengesahan rasmi dan kes kehadiran kerja diurus melalui polisi HR majikan / penilaian klinikal MC melainkan wujud pelanggaran perintah bertulis S.15(1)/S.14.",
        ],
        "penalty_section": "Seksyen 24 Akta 342 (Pindaan Akta A1742)",
        "penalty_first_offence": {
            "max_fine_rm": 10000,
            "max_jail_months": 24,
            "other_orders": None,
            "verbatim_penalty": "Didenda tidak melebihi sepuluh ribu ringgit (RM10,000.00) atau dipenjarakan selama tempoh tidak melebihi dua (2) tahun atau kedua-duanya.",
        },
        "penalty_subsequent_offence": None,
        "compound_info": {
            "is_compoundable": False,
            "compound_authority_section": None,
            "compound_regulation_ref": "P.U. (A) 139/2025",
            "compound_amount_or_limit": "TIDAK BOLEH DIKOMPAUN (Tiada dalam Jadual Pertama P.U. (A) 139/2025) — Hanya melalui Kertas Siasatan (IP) bagi kes keterlaluan",
            "max_compound_rm": None,
            "payment_days": None,
            "notice_section": None,
        },
        "special_legal_requirements": [
            "Pengesahan makmal rasmi fasiliti kesihatan & e-Notifikasi S.10",
            "Bukti pengetahuan (mens rea) sebelum hadir di tempat awam",
        ],
        "mandatory_exhibits": [
            "Keputusan Ujian Makmal Rasmi & Cetakan e-Notifikasi Seksyen 10 + Sijil S.90A(2)",
            "Rakaman percakapan S.112 KTJ Pegawai Perubatan & saksi lokasi",
        ],
        "charge_sheet_template_bm": (
            "Bahawa kamu, seorang yang mengetahui bahawa kamu menghidap suatu penyakit berjangkit iaitu [NAMA_PENYAKIT], "
            "pada [TARIKH], jam lebih kurang [MASA], bertempat di [TEMPAT_KEJADIAN], di dalam Daerah [DAERAH], di dalam Negeri [NEGERI], "
            "telah didapati mendedahkan orang lain kepada risiko jangkitan melalui kehadiran kamu di tempat tersebut; "
            "dan oleh yang demikian kamu telah melakukan suatu kesalahan di bawah Seksyen 12(1) dibaca bersama Seksyen 12(3) Akta Pencegahan dan Pengawalan Penyakit Berjangkit 1988 [Akta 342] "
            "yang boleh dihukum di bawah Seksyen 24 Akta yang sama."
        ),
        "source_section_doc_ids": ["AKTA_342__S12", "AKTA_342__S24", "AKTA_342__S25"],
        "verified_status": "DRAFT_PENDING_REVIEW",
    },
    {
        "offence_id": "AKTA_342_S22_A",
        "statute_id": "AKTA_342",
        "offence_section": "Seksyen 22(a)",
        "read_together_with": ["Seksyen 24 Akta 342"],
        "offence_title": "Menghalang atau menggalang mana-mana pegawai diberi kuasa dalam menjalankan tugasnya di bawah Akta 342",
        "target_offender": "INDIVIDU",
        "mandatory_elements": [
            {
                "element_no": 1,
                "description": "Pegawai diberi kuasa sedang menjalankan tugas rasmi di bawah Akta 342 setelah menunjukkan Kad Kuasa.",
                "must_prove": "Salinan Kad Kuasa KKM & Diari Siasatan.",
            },
            {
                "element_no": 2,
                "description": "OKT menghalang atau menggalang pegawai tersebut daripada melaksanakan tugasnya.",
                "must_prove": "Laporan Polis & rakaman S.112 KTJ saksi kejadian.",
            },
        ],
        "explicit_exclusions_and_traps": [
            "Seksyen 22(a) BUKAN kesalahan boleh kompaun di bawah Jadual Pertama P.U. (A) 139/2025 — wajib buka IP jika berlaku halangan.",
        ],
        "penalty_section": "Seksyen 24 Akta 342 (Pindaan Akta A1742)",
        "penalty_first_offence": {
            "max_fine_rm": 10000,
            "max_jail_months": 24,
            "other_orders": None,
            "verbatim_penalty": "Didenda tidak melebihi sepuluh ribu ringgit (RM10,000.00) atau dipenjarakan selama tempoh tidak melebihi dua (2) tahun atau kedua-duanya.",
        },
        "penalty_subsequent_offence": None,
        "compound_info": {
            "is_compoundable": False,
            "compound_authority_section": None,
            "compound_regulation_ref": "P.U. (A) 139/2025",
            "compound_amount_or_limit": "TIDAK BOLEH DIKOMPAUN (S.22(a) tiada dalam Jadual Pertama P.U. (A) 139/2025) — Wajib Buka IP",
            "max_compound_rm": None,
            "payment_days": None,
            "notice_section": None,
        },
        "special_legal_requirements": ["Laporan Polis", "Rakaman S.112 KTJ saksi"],
        "mandatory_exhibits": [
            "Laporan Polis, Diari Siasatan & Salinan Kad Kuasa PPKP",
            "Rakaman percakapan S.112 KTJ saksi pengiring",
        ],
        "charge_sheet_template_bm": (
            "Bahawa kamu, pada [TARIKH], jam lebih kurang [MASA], bertempat di [TEMPAT_KEJADIAN], "
            "di dalam Daerah [DAERAH], di dalam Negeri [NEGERI], telah didapati menghalang seorang pegawai diberi kuasa dalam menjalankan tugasnya "
            "di bawah Akta Pencegahan dan Pengawalan Penyakit Berjangkit 1988; dan oleh yang demikian kamu telah melakukan suatu kesalahan "
            "di bawah Seksyen 22(a) Akta 342 yang boleh dihukum di bawah Seksyen 24 Akta yang sama."
        ),
        "source_section_doc_ids": ["AKTA_342__S22", "AKTA_342__S24", "AKTA_342__S25"],
        "verified_status": "DRAFT_PENDING_REVIEW",
    },
    {
        "offence_id": "AKTA_342_S22_B",
        "statute_id": "AKTA_342",
        "offence_section": "Seksyen 22(b)",
        "read_together_with": ["Seksyen 24(a) / Seksyen 24 Akta 342", "Seksyen 14 / Seksyen 15(1) / Seksyen 18(1)(d) Akta 342"],
        "offence_title": "Tidak mematuhi perintah yang sah yang dikeluarkan oleh pegawai diberi kuasa (cth. Notis Arahan Menjalani Rawatan Tibi PTB Smear Positif / Perintah Pengawasan S.15(1) / Perintah Tutup Premis Wabak S.18(1)(d))",
        "target_offender": "INDIVIDU",
        "mandatory_elements": [
            {
                "element_no": 1,
                "description": "Diagnosis penyakit berjangkit aktif telah disahkan secara klinikal/makmal (cth. TBIS 20C PTB Smear Positif & e-Notifikasi S.10) atau wujud wabak yang sah.",
                "must_prove": "Borang Keputusan Makmal TBIS 20C (PTB Smear Positif / GeneXpert / Kultur) & Cetakan e-Notifikasi Seksyen 10 + Sijil S.90A(2).",
            },
            {
                "element_no": 2,
                "description": "Suatu perintah bertulis yang sah (Notis Arahan Menjalani Rawatan / Perintah Pengasingan S.14 / Perintah Pengawasan S.15(1) / Perintah Tutup S.18(1)(d)) telah dikeluarkan oleh Pegawai Diberi Kuasa dan DISERAHKAN SECARA SAH kepada OKT.",
                "must_prove": "Salinan asal Notis Arahan / Perintah bertulis bertandatangan terima oleh OKT dan saksi PPKP.",
            },
            {
                "element_no": 3,
                "description": "OKT gagal atau enggan mematuhi perintah bertulis tersebut selepas tarikh yang ditetapkan (cth. cicir rawatan TBIS 10D & gagal hadir walaupun lawatan pengesanan TBIS 10Da telah dijalankan).",
                "must_prove": "Borang TBIS 10A-1, TBIS 10-I, TBIS 10D, TBIS 10Da, Kronologi Kes & Diari Siasatan.",
            },
        ],
        "explicit_exclusions_and_traps": [
            "PENGECUALIAN KES PTB SMEAR NEGATIF / SARINGAN AWAL: Jika pesakit masih di peringkat saringan atau keputusan kahak PTB Smear Negatif (AFB Negatif) belum disahkan aktif oleh MO/FMS (CXR/GeneXpert/Kultur TBIS 20C) dan TIADA perintah bertulis yang telah diserahkan secara tangan lalu diingkari, kesalahan Seksyen 22(b) BELUM wujud — JANGAN buka IP S.22(b)!",
            "PENGECUALIAN COVID-19 PASCA 15 JULAI 2024: Sejak pemansuhan HSO mandatori MySejahtera pada 15 Julai 2024, pekerja positif COVID-19 yang hadir bekerja TANPA Perintah Pengawasan bertulis Seksyen 15(1) atau Pengasingan Seksyen 14 yang diserahkan secara sah TIDAK melakukan kesalahan Seksyen 22(b) dan TIDAK BOLEH dikompaun serta-merta!",
            "JANGAN sesekali tulis 'Seksyen 22(b) Akta 514' (Akta 514 ialah OSHA 1994!). Akta Penyakit Berjangkit ialah Akta 342.",
        ],
        "penalty_section": "Seksyen 24(a) [Individu] / Seksyen 24(b) [Pertubuhan Perbadanan] Akta 342 (Pindaan Akta A1742)",
        "penalty_first_offence": {
            "max_fine_rm": 10000,
            "max_jail_months": 24,
            "other_orders": "Pertubuhan Perbadanan [Seksyen 24(b)]: Denda tidak melebihi RM100,000.00 (Akta A1742)",
            "verbatim_penalty": "Individu [S.24(a)]: Denda tidak melebihi RM10,000.00 atau penjara tidak melebihi dua (2) tahun atau kedua-duanya | Pertubuhan Perbadanan [S.24(b)]: Denda tidak melebihi RM100,000.00.",
        },
        "penalty_subsequent_offence": None,
        "compound_info": {
            "is_compoundable": True,
            "compound_authority_section": "Seksyen 25 Akta 342 (Pindaan Akta A1742)",
            "compound_regulation_ref": "Jadual Pertama P.U. (A) 139/2025",
            "compound_amount_or_limit": "Bagi kes Tibi cicir rawatan (berisiko MDR-TB): Buka IP Terus Tanpa Kompaun. Bagi kes lain S.22(b): Boleh dikompaun HANYA dengan keizinan bertulis Pendakwa Raya (maks RM5,000 individu / RM50,000 syarikat)",
            "max_compound_rm": 5000,
            "payment_days": 14,
            "notice_section": "Notis Arahan Menjalani Rawatan / Perintah Seksyen 14 / 15(1) / 18(1)(d) Akta 342",
        },
        "special_legal_requirements": [
            "Bukti serahan tangan Notis Arahan Rawatan / Perintah bertulis asal bertandatangan terima & saksi",
            "Keputusan Makmal TBIS 20C & e-Notifikasi S.10 + Sijil S.90A(2)",
            "Keizinan Bertulis Pendakwa Raya wajib jika menawarkan kompaun S.25 (Akta A1742)",
        ],
        "mandatory_exhibits": [
            "Borang Notifikasi (e-Notifikasi / Peraturan Borang Notis 2005) + Sijil S.90A",
            "Salinan Keputusan Makmal Tibi TBIS 20C (mengesahkan kahak PTB Smear Positif)",
            "Notis Arahan Menjalani Rawatan Penyakit Berjangkit bertandatangan terima pesakit & saksi",
            "Borang TBIS 10A-1, Kad Rawatan TBIS 10-I, TBIS 10A-3, TBIS 10D & TBIS 10Da",
            "Jadual Kronologi Kes, Diari Siasatan lengkap & 6 Poin Hujahan Pemberatan Hukuman",
        ],
        "charge_sheet_template_bm": (
            "Bahawa kamu, pada [TARIKH], jam lebih kurang [MASA], bertempat di [TEMPAT_KEJADIAN], "
            "di dalam Daerah [DAERAH], di dalam Negeri [NEGERI], telah didapati tidak mematuhi suatu perintah yang sah yang dikeluarkan "
            "oleh pegawai diberi kuasa iaitu enggan menjalani dan menyambung semula rawatan penyakit Tuberkulosis (PTB Smear Positif) "
            "sebagaimana diarahkan di bawah Notis Arahan Menjalani Rawatan Penyakit Berjangkit; dan oleh yang demikian kamu telah melakukan suatu kesalahan "
            "di bawah Seksyen 22(b) Akta Pencegahan dan Pengawalan Penyakit Berjangkit 1988 [Akta 342] yang boleh dihukum di bawah Seksyen 24(a) Akta yang sama."
        ),
        "source_section_doc_ids": ["AKTA_342__S22", "AKTA_342__S24", "AKTA_342__S25", "AKTA_342__S15", "AKTA_342__S18", "AKTA_342_PERATURAN_KOMPAUN_2025__P2"],
        "verified_status": "DRAFT_PENDING_REVIEW",
    },
    # ---------------- AKTA 574 (KANUN KESEKSAAN — RUJUKAN SILANG PDRM / TPR) ----------------
    {
        "offence_id": "AKTA_574_S186",
        "statute_id": "AKTA_574",
        "offence_section": "Seksyen 186",
        "read_together_with": [
            "Seksyen 21 Kanun Keseksaan [Akta 574] (Penjawat Awam)",
            "Seksyen 24(3) Akta 852 / Seksyen 3 Akta 281 / Seksyen 4 Akta 154 / Seksyen 3(2) Akta 342",
            "Seksyen 107 Kanun Tatacara Jenayah [Akta 593] (Laporan Polis)",
        ],
        "offence_title": "Dengan sengaja menghalang penjawat awam (PPKP) menjalankan fungsi jawatan awam — rujukan silang utama apabila Akta KKM (khususnya Akta 852) tiada seksyen halangan sendiri",
        "target_offender": "INDIVIDU_AWAM",
        "mandatory_elements": [
            {
                "element_no": 1,
                "description": "PPKP bertindak sebagai penjawat awam yang sah (disifatkan di bawah S.24(3) Akta 852 / S.3 Akta 281 / S.4 Akta 154 / S.3(2) Akta 342) dengan Kad Kuasa rasmi KKM.",
                "must_prove": "Salinan Kad Kuasa KKM, surat arahan operasi, dan keterangan bahawa PPKP memperkenalkan diri secara sah.",
            },
            {
                "element_no": 2,
                "description": "Suspek dengan sengaja menghalang secara fizikal/aktif (cth: kunci pintu, rampas semula ekshibit, halang laluan masuk) ketika PPKP menjalankan tugas rasmi.",
                "must_prove": "Laporan Polis S.107 KTJ oleh PPKP, rakaman video/gambar (disokong Sijil S.90A), dan percakapan saksi pasukan operasi.",
            },
        ],
        "explicit_exclusions_and_traps": [
            "BATASAN BIDANG KUASA PPKP: PPKP TIDAK mempunyai kuasa menyiasat, mengkompaun atau mendakwa di bawah Kanun Keseksaan [Akta 574]. PPKP WAJIB membuat Laporan Polis di bawah Seksyen 107 KTJ supaya PDRM menyiasat dan TPR mendakwa (Kesalahan Boleh Tangkap / Seizable di bawah Jadual Pertama KTJ).",
            "PRINSIP LEX SPECIALIS: Jika halangan berlaku di bawah Akta 281 (S.4(3)-(4)), Akta 154 (S.21) atau Akta 342 (S.22(a)), PPKP boleh bertindak di bawah seksyen khusus Akta KKM tersebut; namun bagi Akta 852 (tiada seksyen halangan tersendiri) atau halangan agresif, rujuk S.186 Akta 574 melalui PDRM.",
        ],
        "penalty_section": "Seksyen 186 Kanun Keseksaan [Akta 574]",
        "penalty_first_offence": {
            "max_fine_rm": 10000,
            "max_jail_months": 24,
            "verbatim_penalty": "Penjara sehingga dua (2) tahun, atau denda sehingga RM10,000.00, atau kedua-duanya (Kesalahan Boleh Tangkap / Seizable; Tidak Boleh Dijamin / Non-Bailable).",
        },
        "penalty_subsequent_offence": None,
        "compound_info": {
            "is_compoundable": False,
            "compound_authority_section": None,
            "compound_regulation_ref": None,
            "compound_amount_or_limit": "TIDAK BOLEH DIKOMPAUN — Kuasa siasatan PDRM & pendakwaan TPR. PPKP wajib buat Laporan Polis Seksyen 107 KTJ.",
            "max_compound_rm": None,
            "payment_days": None,
            "notice_section": "Laporan Polis Seksyen 107 KTJ [Akta 593]",
        },
        "special_legal_requirements": [
            "Laporan Polis (FIR) segera oleh PPKP di balai polis berhampiran di bawah Seksyen 107 KTJ",
            "PPKP & anggota pasukan operasi hadir memberi percakapan saksi kepada Pegawai Penyiasat PDRM di bawah Seksyen 112 KTJ",
            "Serahkan rakaman video/foto (beserta Sijil Seksyen 90A Akta 56) & salinan Kad Kuasa sebagai ekshibit polis",
        ],
        "mandatory_exhibits": [
            "Salinan Laporan Polis (FIR S.107 KTJ) oleh PPKP",
            "Salinan Kad Kuasa PPKP & Surat Arahan Operasi PKD",
            "Rakaman Video/Gambar kejadian + Sijil Seksyen 90A Akta Keterangan 1950 [Akta 56]",
            "Diari Rasmi / Buku Catatan Operasi PPKP & Senarai Saksi Pasukan",
        ],
        "charge_sheet_template_bm": (
            "RUJUKAN PDRM / TPR SAHAJA (PPKP TIDAK MENDRAF PERTUDUHAN AKTA 574): "
            "Siasatan dan pendakwaan Seksyen 186 Kanun Keseksaan [Akta 574] adalah di bawah bidang kuasa PDRM dan Timbalan Pendakwa Raya (TPR) selepas Laporan Polis Seksyen 107 KTJ dibuat."
        ),
        "source_section_doc_ids": ["AKTA_574__S186", "AKTA_574__S21", "AKTA_593__S107"],
        "verified_status": "DRAFT_PENDING_REVIEW",
    },
    {
        "offence_id": "AKTA_574_S183",
        "statute_id": "AKTA_574",
        "offence_section": "Seksyen 183",
        "read_together_with": [
            "Seksyen 35 Akta 852 / Seksyen 4(1)(f) Akta 281 (Kuasa Penyitaan)",
            "Seksyen 107 & Seksyen 108(2) KTJ [Akta 593] (OTI TPR bagi kesalahan tidak boleh tangkap)",
        ],
        "offence_title": "Menentang pengambilan harta (rampasan/sitaan ekshibit) oleh penjawat awam yang bertindak di bawah kuasa sah undang-undang",
        "target_offender": "PENIAGA_PEMILIK",
        "mandatory_elements": [
            {
                "element_no": 1,
                "description": "PPKP sedang melaksanakan penyitaan sah di bawah Akta KKM (cth: S.35 Akta 852 / S.4(1)(f) Akta 281).",
                "must_prove": "Borang Senarai Benda Disita, Kad Kuasa, dan bukti asas syak munasabah penyitaan.",
            },
            {
                "element_no": 2,
                "description": "Suspek menentang, merampas balik atau menghalang pengambilan barang kes tersebut.",
                "must_prove": "Laporan Polis S.107 KTJ, keterangan saksi pasukan dan rakaman kejadian.",
            },
        ],
        "explicit_exclusions_and_traps": [
            "BATASAN BIDANG KUASA: Kesalahan TIDAK BOLEH TANGKAP (Non-Seizable) di bawah Jadual Pertama KTJ — PDRM memerlukan Perintah Untuk Menyiasat (OTI) daripada TPR di bawah Seksyen 108(2) KTJ. PPKP TIDAK boleh kompaun; buat Laporan Polis S.107 KTJ.",
        ],
        "penalty_section": "Seksyen 183 Kanun Keseksaan [Akta 574]",
        "penalty_first_offence": {
            "max_fine_rm": 2000,
            "max_jail_months": 6,
            "verbatim_penalty": "Penjara sehingga enam (6) bulan, atau denda sehingga RM2,000.00, atau kedua-duanya (Non-Seizable; PDRM perlukan OTI S.108(2) KTJ).",
        },
        "penalty_subsequent_offence": None,
        "compound_info": {
            "is_compoundable": False,
            "compound_authority_section": None,
            "compound_regulation_ref": None,
            "compound_amount_or_limit": "TIDAK BOLEH DIKOMPAUN — Rujuk PDRM melalui Laporan Polis S.107 KTJ (OTI S.108(2) KTJ).",
            "max_compound_rm": None,
            "payment_days": None,
            "notice_section": "Laporan Polis Seksyen 107 KTJ [Akta 593]",
        },
        "special_legal_requirements": [
            "Buat Laporan Polis S.107 KTJ; PDRM memohon OTI daripada TPR di bawah S.108(2) KTJ",
            "Jika suspek turut merempuh/menghalang secara fizikal, polis boleh menyiasat serentak di bawah S.186 atau S.353 Akta 574 (Seizable)",
        ],
        "mandatory_exhibits": [
            "Laporan Polis S.107 KTJ & salinan Borang Senarai Benda Disita",
            "Rakaman video/gambar kejadian + Sijil S.90A Akta 56",
        ],
        "charge_sheet_template_bm": "RUJUKAN PDRM / TPR SAHAJA — Siasatan di bawah Seksyen 183 Kanun Keseksaan [Akta 574] adalah bidang kuasa PDRM (OTI S.108(2) KTJ) & TPR.",
        "source_section_doc_ids": ["AKTA_574__S183", "AKTA_574__S186", "AKTA_593__S107", "AKTA_593__S108"],
        "verified_status": "DRAFT_PENDING_REVIEW",
    },
    {
        "offence_id": "AKTA_574_S189",
        "statute_id": "AKTA_574",
        "offence_section": "Seksyen 189",
        "read_together_with": [
            "Seksyen 506 Kanun Keseksaan [Akta 574] (Ugutan Jenayah)",
            "Seksyen 107 & Seksyen 108(2) KTJ [Akta 593]",
        ],
        "offence_title": "Ugutan bencana (threat of injury) terhadap penjawat awam (PPKP) bagi mendorong PPKP menangguhkan atau tidak melaksanakan tugas rasmi",
        "target_offender": "INDIVIDU_AWAM",
        "mandatory_elements": [
            {
                "element_no": 1,
                "description": "Suspek mengeluarkan ugutan bencana terhadap PPKP atau mana-mana orang yang PPKP mempunyai kepentingan.",
                "must_prove": "Perkataan tepat ugutan yang direkod segera dalam Diari/Laporan Polis, rakaman audio/video & keterangan saksi.",
            },
            {
                "element_no": 2,
                "description": "Niat untuk mendorong PPKP melakukan, menahan diri atau melengahkan pelaksanaan fungsi awam (cth: supaya tidak keluarkan kompaun/tutup premis).",
                "must_prove": "Konteks kejadian operasi rasmi yang sedang dijalankan.",
            },
        ],
        "explicit_exclusions_and_traps": [
            "BATASAN BIDANG KUASA: S.189 adalah Non-Seizable (perlukan OTI S.108(2) KTJ), manakala jika terdapat ugutan bunuh/cedera/bakar/kecederaan parah ia jatuh di bawah Seksyen 506 Akta 574 (SEIZABLE — polis boleh tangkap serta-merta tanpa waran). PPKP WAJIB undur ke lokasi selamat & buat Laporan Polis S.107 KTJ!",
        ],
        "penalty_section": "Seksyen 189 Kanun Keseksaan [Akta 574]",
        "penalty_first_offence": {
            "max_fine_rm": None,
            "max_jail_months": 24,
            "verbatim_penalty": "Penjara sehingga dua (2) tahun, atau denda, atau kedua-duanya (S.189 Non-Seizable; jika ugutan jenayah berat rujuk S.506 sehingga 7 tahun, Seizable).",
        },
        "penalty_subsequent_offence": None,
        "compound_info": {
            "is_compoundable": False,
            "compound_authority_section": None,
            "compound_regulation_ref": None,
            "compound_amount_or_limit": "TIDAK BOLEH DIKOMPAUN — Utamakan keselamatan PPKP dan buat Laporan Polis S.107 KTJ segera.",
            "max_compound_rm": None,
            "payment_days": None,
            "notice_section": "Laporan Polis Seksyen 107 KTJ [Akta 593]",
        },
        "special_legal_requirements": [
            "Utamakan keselamatan diri pasukan — tarik diri dari premis berisiko dan hubungi balai polis (999) / buat Laporan Polis S.107 KTJ",
            "Catat verbatim kata-kata ugutan suspek secepat mungkin",
        ],
        "mandatory_exhibits": [
            "Laporan Polis S.107 KTJ dengan transkrip tepat kata-kata ugutan",
            "Rakaman video/audio (Sijil S.90A Akta 56) & saksi pasukan",
        ],
        "charge_sheet_template_bm": "RUJUKAN PDRM / TPR SAHAJA — Siasatan & pendakwaan Seksyen 189 / Seksyen 506 Kanun Keseksaan [Akta 574] adalah bidang kuasa PDRM & TPR.",
        "source_section_doc_ids": ["AKTA_574__S189", "AKTA_574__S506", "AKTA_593__S107"],
        "verified_status": "DRAFT_PENDING_REVIEW",
    },
    {
        "offence_id": "AKTA_574_S353",
        "statute_id": "AKTA_574",
        "offence_section": "Seksyen 353",
        "read_together_with": [
            "Seksyen 186 & Seksyen 506 Kanun Keseksaan [Akta 574]",
            "Seksyen 107 KTJ [Akta 593]",
        ],
        "offence_title": "Menyerang atau menggunakan kekerasan jenayah (menolak, menumbuk, memukul, meludah, mencampak barang) terhadap penjawat awam (PPKP) semasa menjalankan tugas",
        "target_offender": "INDIVIDU_AWAM",
        "mandatory_elements": [
            {
                "element_no": 1,
                "description": "PPKP sedang melaksanakan kewajipan rasmi yang sah di sisi undang-undang.",
                "must_prove": "Kad Kuasa KKM, surat arahan operasi dan saksi pasukan.",
            },
            {
                "element_no": 2,
                "description": "Suspek menyerang atau menggunakan kekerasan jenayah terhadap PPKP bagi menghalang/menakutkan PPKP menjalankan kewajipan.",
                "must_prove": "Laporan Polis S.107 KTJ, laporan pemeriksaan perubatan (jika cedera), gambar kecederaan/pakaian & rakaman video (Sijil S.90A).",
            },
        ],
        "explicit_exclusions_and_traps": [
            "BATASAN BIDANG KUASA: Kesalahan BOLEH TANGKAP (Seizable) di bawah bidang kuasa PDRM & TPR. PPKP TIDAK boleh kompaun; segera hubungi polis (999), dapatkan rawatan perubatan rasmi di hospital/klinik kerajaan (rekod kecederaan) dan buat Laporan Polis S.107 KTJ.",
        ],
        "penalty_section": "Seksyen 353 Kanun Keseksaan [Akta 574]",
        "penalty_first_offence": {
            "max_fine_rm": None,
            "max_jail_months": 24,
            "verbatim_penalty": "Penjara sehingga dua (2) tahun, atau denda, atau kedua-duanya (Kesalahan Boleh Tangkap / Seizable).",
        },
        "penalty_subsequent_offence": None,
        "compound_info": {
            "is_compoundable": False,
            "compound_authority_section": None,
            "compound_regulation_ref": None,
            "compound_amount_or_limit": "TIDAK BOLEH DIKOMPAUN — Siasatan jenayah oleh PDRM & pendakwaan oleh TPR.",
            "max_compound_rm": None,
            "payment_days": None,
            "notice_section": "Laporan Polis Seksyen 107 KTJ [Akta 593]",
        },
        "special_legal_requirements": [
            "Dapatkan pemeriksaan doktor kerajaan (rekod kecederaan/Laporan Perubatan) segera selepas kejadian",
            "Buat Laporan Polis S.107 KTJ & maklumkan Pegawai Kesihatan Daerah (PKD)",
        ],
        "mandatory_exhibits": [
            "Laporan Polis S.107 KTJ & Laporan Perubatan Hospital/Klinik Kerajaan",
            "Gambar kecederaan/pakaian terkoyak & rakaman video (Sijil S.90A Akta 56)",
        ],
        "charge_sheet_template_bm": "RUJUKAN PDRM / TPR SAHAJA — Siasatan & pendakwaan Seksyen 353 Kanun Keseksaan [Akta 574] adalah bidang kuasa PDRM & TPR.",
        "source_section_doc_ids": ["AKTA_574__S353", "AKTA_574__S186", "AKTA_593__S107"],
        "verified_status": "DRAFT_PENDING_REVIEW",
    },
    {
        "offence_id": "AKTA_574_S506",
        "statute_id": "AKTA_574",
        "offence_section": "Seksyen 506",
        "read_together_with": [
            "Seksyen 503 Kanun Keseksaan [Akta 574] (Takrif Menakutkan Secara Jenayah)",
            "Seksyen 189 Kanun Keseksaan [Akta 574]",
        ],
        "offence_title": "Menakutkan secara jenayah (ugutan bunuh, cedera parah, bakar premis/kenderaan, atau acu senjata terhadap PPKP)",
        "target_offender": "INDIVIDU_AWAM",
        "mandatory_elements": [
            {
                "element_no": 1,
                "description": "Suspek mengugut untuk mendatangkan bencana terhadap tubuh badan, nama baik atau harta PPKP (termasuk ugutan bunuh/cedera parah/bakar/senjata).",
                "must_prove": "Laporan Polis S.107 KTJ, transkrip perkataan ugutan, rakaman video/audio (Sijil S.90A) & keterangan saksi.",
            },
            {
                "element_no": 2,
                "description": "Niat menyebabkan ketakutan (alarm) kepada PPKP atau memaksa PPKP tidak melakukan tindakan penguatkuasaan.",
                "must_prove": "Keterangan mangsa (PPKP) bahawa ugutan tersebut menimbulkan rasa takut/ancaman keselamatan sebenar.",
            },
        ],
        "explicit_exclusions_and_traps": [
            "BATASAN BIDANG KUASA: Kesalahan BOLEH TANGKAP (Seizable) dan TIDAK BOLEH DIJAMIN (Non-Bailable) jika ugutan menyebabkan kematian/cedera parah/kebakaran. PPKP WAJIB segera keluar ke kawasan selamat, hubungi PDRM (999) dan buat Laporan Polis S.107 KTJ.",
        ],
        "penalty_section": "Seksyen 506 Kanun Keseksaan [Akta 574]",
        "penalty_first_offence": {
            "max_fine_rm": None,
            "max_jail_months": 84,
            "verbatim_penalty": "Penjara sehingga dua (2) tahun atau denda atau kedua-duanya; dan jika ugutan menyebabkan kematian/cedera parah/kebakaran: penjara sehingga tujuh (7) tahun, atau denda, atau kedua-duanya (Seizable, Non-Bailable).",
        },
        "penalty_subsequent_offence": None,
        "compound_info": {
            "is_compoundable": False,
            "compound_authority_section": None,
            "compound_regulation_ref": None,
            "compound_amount_or_limit": "TIDAK BOLEH DIKOMPAUN — Siasatan jenayah berat oleh PDRM & TPR.",
            "max_compound_rm": None,
            "payment_days": None,
            "notice_section": "Laporan Polis Seksyen 107 KTJ [Akta 593]",
        },
        "special_legal_requirements": [
            "Panggilan kecemasan PDRM 999 & Laporan Polis S.107 KTJ serta-merta",
            "Lindungi rakaman CCTV/video premis atau telefon bimbit untuk diserahkan kepada PDRM beserta Sijil S.90A Akta 56",
        ],
        "mandatory_exhibits": [
            "Laporan Polis S.107 KTJ & rakaman video/audio (Sijil S.90A Akta 56)",
            "Senarai saksi kejadian dan catatan verbatim kata-kata ugutan",
        ],
        "charge_sheet_template_bm": "RUJUKAN PDRM / TPR SAHAJA — Siasatan & pendakwaan Seksyen 506 Kanun Keseksaan [Akta 574] adalah bidang kuasa PDRM & TPR.",
        "source_section_doc_ids": ["AKTA_574__S506", "AKTA_574__S503", "AKTA_574__S189"],
        "verified_status": "DRAFT_PENDING_REVIEW",
    },
    {
        "offence_id": "AKTA_574_S170",
        "statute_id": "AKTA_574",
        "offence_section": "Seksyen 170",
        "read_together_with": [
            "Seksyen 420 Kanun Keseksaan [Akta 574] (jika turut memeras/menipu wang peniaga)",
            "Seksyen 107 KTJ [Akta 593]",
        ],
        "offence_title": "Menyamar sebagai penjawat awam (individu palsu menyamar sebagai PPKP / Pegawai Kesihatan KKM untuk memeriksa premis atau mengutip bayaran)",
        "target_offender": "INDIVIDU_AWAM",
        "mandatory_elements": [
            {
                "element_no": 1,
                "description": "Suspek berpura-pura memegang jawatan awam sebagai PPKP / Pegawai KKM sedangkan beliau bukan pegawai sah.",
                "must_prove": "Pengesahan rasmi Bahagian Sumber Manusia / PKD bahawa suspek bukan kakitangan KKM, kad kuasa palsu/vest palsu.",
            },
            {
                "element_no": 2,
                "description": "Suspek melakukan atau cuba melakukan tindakan atas sifat jawatan palsu itu (cth: memeriksa premis, mengeluarkan notis/resit palsu).",
                "must_prove": "Keterangan pengadu/peniaga, CCTV premis, dokumen/notis palsu yang dikeluarkan.",
            },
        ],
        "explicit_exclusions_and_traps": [
            "BATASAN BIDANG KUASA: Kesalahan BOLEH TANGKAP (Seizable) di bawah bidang kuasa PDRM & TPR. PKD/PPKP hendaklah membuat Laporan Polis S.107 KTJ dan mengesahkan status rasmi perjawatan KKM secara bertulis kepada PDRM. Jika melibatkan tipu wang/kompaun palsu, rujuk serentak Seksyen 420 Akta 574.",
        ],
        "penalty_section": "Seksyen 170 Kanun Keseksaan [Akta 574]",
        "penalty_first_offence": {
            "max_fine_rm": None,
            "max_jail_months": 24,
            "verbatim_penalty": "Penjara sehingga dua (2) tahun, atau denda, atau kedua-duanya (Seizable; jika menipu wang rujuk S.420 penjara 1–10 tahun + sebatan + denda).",
        },
        "penalty_subsequent_offence": None,
        "compound_info": {
            "is_compoundable": False,
            "compound_authority_section": None,
            "compound_regulation_ref": None,
            "compound_amount_or_limit": "TIDAK BOLEH DIKOMPAUN — Siasatan jenayah oleh PDRM & pendakwaan TPR.",
            "max_compound_rm": None,
            "payment_days": None,
            "notice_section": "Laporan Polis Seksyen 107 KTJ [Akta 593]",
        },
        "special_legal_requirements": [
            "Laporan Polis S.107 KTJ oleh PKD/PPKP bersama pengadu premis",
            "Surat pengesahan rasmi PKD/JKN bahawa suspek bukan pegawai KKM & tiada kuasa statutori",
        ],
        "mandatory_exhibits": [
            "Laporan Polis S.107 KTJ & surat pengesahan bukan kakitangan KKM",
            "Salinan kad kuasa palsu / notis kompaun palsu / rakaman CCTV premis",
        ],
        "charge_sheet_template_bm": "RUJUKAN PDRM / TPR SAHAJA — Siasatan & pendakwaan Seksyen 170 / Seksyen 420 Kanun Keseksaan [Akta 574] adalah bidang kuasa PDRM & TPR.",
        "source_section_doc_ids": ["AKTA_574__S170", "AKTA_574__S420"],
        "verified_status": "DRAFT_PENDING_REVIEW",
    },
    {
        "offence_id": "AKTA_574_S177",
        "statute_id": "AKTA_574",
        "offence_section": "Seksyen 177",
        "read_together_with": [
            "Seksyen 182 Kanun Keseksaan [Akta 574] (Aduan Palsu/Fitnah Premis)",
            "Seksyen 107 & Seksyen 108(2) KTJ [Akta 593]",
        ],
        "offence_title": "Memberi maklumat palsu kepada penjawat awam (butiran identiti/nama/alamat palsu atau maklumat palsu semasa siasatan KKM)",
        "target_offender": "INDIVIDU_AWAM",
        "mandatory_elements": [
            {
                "element_no": 1,
                "description": "Suspek terikat di sisi undang-undang untuk memberi maklumat mengenai sesuatu perkara kepada PPKP.",
                "must_prove": "Punca kuasa menuntut maklumat (cth: S.30/S.31 Akta 852, S.112 KTJ, S.4 Akta 281, S.22(c) Akta 342).",
            },
            {
                "element_no": 2,
                "description": "Suspek memberi maklumat yang diketahui atau dipercayainya adalah palsu.",
                "must_prove": "Semakan rasmi JPN/SSM/rekod sebenar yang membuktikan maklumat diberi adalah palsu.",
            },
        ],
        "explicit_exclusions_and_traps": [
            "PRINSIP LEX SPECIALIS: Jika berlaku di bawah Akta 281 (S.4(6)) atau Akta 342 (S.22(c)), gunakan seksyen khusus Akta KKM terlebih dahulu. Jika berlaku di bawah Akta 852 (tiada seksyen maklumat palsu am) atau aduan palsu bagi memudaratkan premis lain (S.182 Akta 574), rujuk PDRM melalui Laporan Polis S.107 KTJ (Non-Seizable, perlukan OTI S.108(2) KTJ).",
        ],
        "penalty_section": "Seksyen 177 Kanun Keseksaan [Akta 574]",
        "penalty_first_offence": {
            "max_fine_rm": 2000,
            "max_jail_months": 24,
            "verbatim_penalty": "Penjara sehingga enam (6) bulan atau denda sehingga RM2,000.00 atau kedua-duanya; atau penjara sehingga dua (2) tahun atau denda atau kedua-duanya jika maklumat palsu berkenaan pelakuan sesuatu kesalahan.",
        },
        "penalty_subsequent_offence": None,
        "compound_info": {
            "is_compoundable": False,
            "compound_authority_section": None,
            "compound_regulation_ref": None,
            "compound_amount_or_limit": "TIDAK BOLEH DIKOMPAUN — Siasatan oleh PDRM (OTI S.108(2) KTJ) & TPR.",
            "max_compound_rm": None,
            "payment_days": None,
            "notice_section": "Laporan Polis Seksyen 107 KTJ [Akta 593]",
        },
        "special_legal_requirements": [
            "Semak dahulu sama ada seksyen khusus Akta KKM terpakai (S.4(6) Akta 281 / S.22(c) Akta 342)",
            "Bagi rujukan Akta 574 (S.177 / S.182), buat Laporan Polis S.107 KTJ dengan bukti kepalsuan maklumat",
        ],
        "mandatory_exhibits": [
            "Dokumen/borang/percakapan yang mengandungi maklumat palsu",
            "Rekod pengesahan rasmi (JPN/SSM/rekod PKD) yang membuktikan kepalsuan",
        ],
        "charge_sheet_template_bm": "RUJUKAN PDRM / TPR SAHAJA — Siasatan Seksyen 177 / Seksyen 182 Kanun Keseksaan [Akta 574] adalah bidang kuasa PDRM & TPR.",
        "source_section_doc_ids": ["AKTA_574__S177", "AKTA_574__S182"],
        "verified_status": "DRAFT_PENDING_REVIEW",
    },
    {
        "offence_id": "AKTA_574_S465",
        "statute_id": "AKTA_574",
        "offence_section": "Seksyen 465 / Seksyen 468 / Seksyen 471",
        "read_together_with": [
            "Seksyen 463 & Seksyen 464 Kanun Keseksaan [Akta 574] (Takrif Pemalsuan)",
            "Peraturan 30 / Peraturan 31 PPKM 2009 (kesalahan KKM berasingan jika tiada sijil SLPM/tifoid sah)",
        ],
        "offence_title": "Pemalsuan dokumen / menggunakan dokumen palsu sebagai tulen (cth: Sijil Suntikan Tifoid palsu, Sijil SLPM palsu, Perakuan FoSIM/Halal/Kesihatan palsu)",
        "target_offender": "PENIAGA_PEMILIK",
        "mandatory_elements": [
            {
                "element_no": 1,
                "description": "Dokumen yang dikemukakan kepada PPKP (sijil tifoid, sijil SLPM, sijil FoSIM, surat klinik/makmal) adalah dokumen palsu yang dibuat atau diubah secara tidak sah.",
                "must_prove": "Pengesahan bertulis daripada klinik/hospital/institusi latihan/BKKM bahawa sijil/no. siri tersebut tidak pernah dikeluarkan atau telah dipinda.",
            },
            {
                "element_no": 2,
                "description": "Suspek dengan curang atau dengan niat menipu menggunakan dokumen palsu tersebut seolah-olah tulen (S.471) atau memalsukannya untuk tujuan menipu (S.468).",
                "must_prove": "Dokumen asal yang dirampas/salinan diperakui, pengesahan kepalsuan daripada pengeluar asal, dan Laporan Polis S.107 KTJ.",
            },
        ],
        "explicit_exclusions_and_traps": [
            "TINDAKAN SERENTAK 2 LANDASAN: (1) PPKP kekal mengambil tindakan KKM di bawah PPKM 2009 (cth: P.31(1) tiada suntikan tifoid sah / P.30(1) tiada latihan SLPM sah / P.3 tiada pendaftaran sah) kerana sijil palsu dianggap tiada sijil sah. (2) Bagi jenayah PEMALSUAN DOKUMEN (S.465 / S.468 / S.471 Akta 574), PPKP TIDAK boleh kompaun — WAJIB buat Laporan Polis S.107 KTJ dan serahkan dokumen palsu bersama surat pengesahan kepalsuan kepada PDRM.",
        ],
        "penalty_section": "Seksyen 465 / Seksyen 468 / Seksyen 471 Kanun Keseksaan [Akta 574]",
        "penalty_first_offence": {
            "max_fine_rm": None,
            "max_jail_months": 84,
            "verbatim_penalty": "S.465 (Pemalsuan am): Penjara sehingga 2 tahun atau denda atau kedua-duanya | S.468 (Pemalsuan bagi maksud menipu): Penjara sehingga 7 tahun dan denda (Non-Bailable) | S.471 (Menggunakan dokumen palsu sebagai tulen): Dihukum sama seperti pemalsuan.",
        },
        "penalty_subsequent_offence": None,
        "compound_info": {
            "is_compoundable": False,
            "compound_authority_section": None,
            "compound_regulation_ref": None,
            "compound_amount_or_limit": "TIDAK BOLEH DIKOMPAUN (Akta 574) — Rujuk PDRM melalui Laporan Polis S.107 KTJ (tindakan KKM PPKM 2009 boleh berjalan serentak).",
            "max_compound_rm": None,
            "payment_days": None,
            "notice_section": "Laporan Polis Seksyen 107 KTJ [Akta 593]",
        },
        "special_legal_requirements": [
            "Dapatkan pengesahan bertulis daripada pengeluar asal (klinik/hospital/SLPM/FoSIM) bahawa sijil adalah palsu",
            "Buat Laporan Polis S.107 KTJ dan serahkan dokumen palsu asal dengan rantaian jagaan (chain of custody) kepada PDRM",
        ],
        "mandatory_exhibits": [
            "Dokumen/Sijil palsu asal (sijil tifoid / SLPM / FoSIM) yang diambil semasa pemeriksaan",
            "Surat pengesahan rasmi daripada klinik/institusi/BKKM bahawa sijil tidak tulen",
            "Laporan Polis S.107 KTJ & gambar premis/pengendali",
        ],
        "charge_sheet_template_bm": "RUJUKAN PDRM / TPR SAHAJA — Siasatan & pendakwaan Seksyen 465 / 468 / 471 Kanun Keseksaan [Akta 574] adalah bidang kuasa PDRM & TPR.",
        "source_section_doc_ids": ["AKTA_574__S465", "AKTA_574__S468", "AKTA_574__S471", "AKTA_574__S463"],
        "verified_status": "DRAFT_PENDING_REVIEW",
    },
    {
        "offence_id": "AKTA_574_S269",
        "statute_id": "AKTA_574",
        "offence_section": "Seksyen 269 / Seksyen 270",
        "read_together_with": [
            "Seksyen 12(1) & Seksyen 22(b) Akta 342 [APPPB 1988] (Utamakan Akta 342 dahulu)",
            "Seksyen 107 KTJ [Akta 593]",
        ],
        "offence_title": "Perbuatan cuai (S.269) atau perbuatan jahat/sengaja (S.270) yang mungkin merebakkan jangkitan apa-apa penyakit yang berbahaya kepada nyawa",
        "target_offender": "INDIVIDU_AWAM",
        "mandatory_elements": [
            {
                "element_no": 1,
                "description": "Suspek melakukan perbuatan yang menyalahi undang-undang atau cuai (S.269) atau jahat/sengaja (S.270).",
                "must_prove": "Bukti perbuatan disengajakan/cuai melampau (cth: meludah kepada orang awam dalam keadaan tahu dijangkiti penyakit berbahaya).",
            },
            {
                "element_no": 2,
                "description": "Suspek tahu atau ada sebab untuk mempercayai perbuatan itu mungkin merebakkan jangkitan penyakit berbahaya kepada nyawa.",
                "must_prove": "Rekod diagnostik klinikal/makmal yang sah & pengesahan pegawai perubatan.",
            },
        ],
        "explicit_exclusions_and_traps": [
            "PRINSIP LEX SPECIALIS: Bagi kes biasa penyakit berjangkit / ingkar perintah kuarantin atau rawatan Tibi, UTAMAKAN Akta 342 (S.12(1) / S.22(b) / S.24 — denda sehingga RM10,000 / 2 tahun atau korporat RM100,000 di bawah Akta A1742). Rujuk PDRM di bawah S.269/S.270 Akta 574 (Seizable) hanya bagi perbuatan cuai/jahat jenayah berat yang memerlukan tangkapan polis serta-merta.",
        ],
        "penalty_section": "Seksyen 269 / Seksyen 270 Kanun Keseksaan [Akta 574]",
        "penalty_first_offence": {
            "max_fine_rm": None,
            "max_jail_months": 24,
            "verbatim_penalty": "S.269 (Cuai): Penjara sehingga 6 bulan atau denda atau kedua-duanya | S.270 (Jahat/Sengaja): Penjara sehingga 2 tahun atau denda atau kedua-duanya (Kedua-duanya Seizable).",
        },
        "penalty_subsequent_offence": None,
        "compound_info": {
            "is_compoundable": False,
            "compound_authority_section": None,
            "compound_regulation_ref": None,
            "compound_amount_or_limit": "TIDAK BOLEH DIKOMPAUN — Siasatan jenayah oleh PDRM & TPR.",
            "max_compound_rm": None,
            "payment_days": None,
            "notice_section": "Laporan Polis Seksyen 107 KTJ [Akta 593]",
        },
        "special_legal_requirements": [
            "Utamakan tindakan di bawah Akta 342 (S.12(1) / S.22(b)) terlebih dahulu; buat Laporan Polis S.107 KTJ bagi perbuatan jenayah jahat/cuai melampau",
            "Perhatian Seksyen 59 Akta Tafsiran [Akta 388]: Pesalah tidak boleh dihukum dua kali atas perbuatan sama di bawah dua akta berbeza",
        ],
        "mandatory_exhibits": [
            "Keputusan makmal sah penyakit berjangkit & pengesahan pegawai perubatan",
            "Laporan Polis S.107 KTJ & bukti perbuatan cuai/jahat",
        ],
        "charge_sheet_template_bm": "RUJUKAN PDRM / TPR SAHAJA — Siasatan Seksyen 269 / Seksyen 270 Kanun Keseksaan [Akta 574] adalah bidang kuasa PDRM & TPR.",
        "source_section_doc_ids": ["AKTA_574__S269", "AKTA_574__S270", "AKTA_388__S59"],
        "verified_status": "DRAFT_PENDING_REVIEW",
    },
    {
        "offence_id": "AKTA_574_S272",
        "statute_id": "AKTA_574",
        "offence_section": "Seksyen 272 / Seksyen 273",
        "read_together_with": [
            "Seksyen 13(1), Seksyen 13A & Seksyen 13B Akta Makanan 1983 [Akta 281] (WAJIB UTAMAKAN AKTA 281)",
        ],
        "offence_title": "Mencampuradukkan makanan atau minuman untuk jualan (S.272) atau menjual makanan/minuman mudarat (S.273) — RUJUKAN SILANG SAHAJA (UTAMAKAN AKTA 281)",
        "target_offender": "PENIAGA_PEMILIK",
        "mandatory_elements": [
            {
                "element_no": 1,
                "description": "Suspek mencampuradukkan makanan/minuman sehingga menjadi mudarat (S.272) atau menjual makanan/minuman yang diketahui mudarat/tidak layak dimakan (S.273).",
                "must_prove": "Sijil Juruanalisis dan bukti penjualan/niat jual.",
            },
        ],
        "explicit_exclusions_and_traps": [
            "AMARAN KERAS LEX SPECIALIS: JANGAN sesekali merendahkan kes keselamatan makanan kepada S.272/S.273 Akta 574 (penalti rendah: 6 bulan / RM2,000, Non-Seizable) apabila Akta Makanan 1983 [Akta 281] menyediakan penalti jauh lebih berat dan kuasa penyiasatan penuh PPKP: S.13(1) (denda RM100,000 / 10 tahun), S.13A(1) (RM50,000 / 8 tahun), S.13A(2) (RM30,000 / 5 tahun), S.13B (RM20,000 / 5 tahun)! Rujuk S.272/273 hanya sebagai maklumat perbandingan/rujukan silang.",
        ],
        "penalty_section": "Seksyen 272 / Seksyen 273 Kanun Keseksaan [Akta 574]",
        "penalty_first_offence": {
            "max_fine_rm": 2000,
            "max_jail_months": 6,
            "verbatim_penalty": "Penjara sehingga enam (6) bulan, atau denda sehingga RM2,000.00, atau kedua-duanya (Non-Seizable) — jauh lebih rendah daripada Akta 281 S.13(1) RM100,000 / 10 tahun!",
        },
        "penalty_subsequent_offence": None,
        "compound_info": {
            "is_compoundable": False,
            "compound_authority_section": None,
            "compound_regulation_ref": None,
            "compound_amount_or_limit": "TIDAK BOLEH DIKOMPAUN — Utamakan penyiasatan & pendakwaan PPKP di bawah Akta Makanan 1983 [Akta 281].",
            "max_compound_rm": None,
            "payment_days": None,
            "notice_section": None,
        },
        "special_legal_requirements": [
            "Gunakan Akta Makanan 1983 [Akta 281] S.13 / S.13A / S.13B sebagai tindakan utama KKM",
            "Rujuk S.63 & S.64 Akta Mahkamah Rendah 1948 [Akta 92] (Mahkamah Sesyen) bagi kes S.13(1) Akta 281 yang memohon hukuman melebihi had RM10,000 / 5 tahun Mahkamah Majistret (S.87 Akta 92)",
        ],
        "mandatory_exhibits": [
            "Sampel rasmi makanan & Sijil Juruanalisis (S.20(ii) Akta 281 — serah 10 hari bersih sebelum bicara)",
        ],
        "charge_sheet_template_bm": "UTAMAKAN AKTA MAKANAN 1983 [AKTA 281] — Gunakan draf pertuduhan S.13(1) / S.13A / S.13B Akta 281 dan bukan S.272/273 Akta 574.",
        "source_section_doc_ids": ["AKTA_574__S272", "AKTA_574__S273", "AKTA_281__S13"],
        "verified_status": "DRAFT_PENDING_REVIEW",
    },
    # ---------------- AKTA 344 (AKTA POLIS 1967 — BANTUAN POLIS & HALANGAN POLIS) ----------------
    {
        "offence_id": "AKTA_344_S90",
        "statute_id": "AKTA_344",
        "offence_section": "Seksyen 90",
        "read_together_with": [
            "Seksyen 20(3)(c) Akta Polis 1967 [Akta 344] (Kewajipan polis membantu pelaksanaan undang-undang kebersihan & kuarantin)",
            "Seksyen 186 Kanun Keseksaan [Akta 574] (bagi halangan terhadap PPKP)",
        ],
        "offence_title": "Menghalang, menentang atau menyerang pegawai polis yang sedang menjalankan tugas (termasuk semasa mengiringi operasi penguatkuasaan KKM)",
        "target_offender": "INDIVIDU_AWAM",
        "mandatory_elements": [
            {
                "element_no": 1,
                "description": "Mangsa halangan/penentangan ialah seorang PEGAWAI POLIS yang sedang menjalankan tugas rasmi (cth: bantuan iringan operasi KKM di bawah S.20(3)(c) Akta 344).",
                "must_prove": "Pengesahan tugas rasmi pegawai polis yang mengiringi operasi dan laporan polis kejadian.",
            },
        ],
        "explicit_exclusions_and_traps": [
            "AMARAN KRITIKAL: Seksyen 90 Akta Polis 1967 [Akta 344] HANYA terpakai bagi halangan terhadap PEGAWAI POLIS, BUKAN PPKP! Jika mangsa halangan ialah PPKP sendiri, rujuk seksyen halangan khusus Akta KKM (S.4(3) Akta 281 / S.21 Akta 154 / S.22(a) Akta 342) atau Seksyen 186 / S.353 Kanun Keseksaan [Akta 574] melalui Laporan Polis S.107 KTJ. PPKP juga TIDAK mempunyai kuasa polis di bawah Akta 344 — PPKP hanya memohon bantuan/iringan PDRM berpandukan S.20(3)(c) Akta 344.",
        ],
        "penalty_section": "Seksyen 90 Akta Polis 1967 [Akta 344]",
        "penalty_first_offence": {
            "max_fine_rm": 500,
            "max_jail_months": 6,
            "verbatim_penalty": "Denda tidak melebihi RM500.00 atau penjara selama tempoh tidak melebihi enam (6) bulan atau kedua-duanya (Bidang kuasa PDRM & TPR sahaja).",
        },
        "penalty_subsequent_offence": None,
        "compound_info": {
            "is_compoundable": False,
            "compound_authority_section": None,
            "compound_regulation_ref": None,
            "compound_amount_or_limit": "TIDAK BOLEH DIKOMPAUN — Kuasa tindakan sepenuhnya oleh PDRM & TPR.",
            "max_compound_rm": None,
            "payment_days": None,
            "notice_section": "Laporan Polis Seksyen 107 KTJ [Akta 593]",
        },
        "special_legal_requirements": [
            "Hanya terpakai jika halangan dilakukan terhadap pegawai polis; tindakan dan siasatan dijalankan oleh PDRM",
            "Bagi permohonan iringan polis ke operasi berisiko tinggi KKM (kebersihan/kuarantin/sitaan), rujuk S.20(3)(c) Akta 344 & S.24 Akta 154",
        ],
        "mandatory_exhibits": [
            "Surat permohonan bantuan iringan polis daripada PKD kepada OCPD/KPD",
            "Laporan Polis S.107 KTJ oleh pegawai polis / PPKP yang terlibat",
        ],
        "charge_sheet_template_bm": "RUJUKAN PDRM / TPR SAHAJA — Seksyen 90 Akta Polis 1967 [Akta 344] adalah di bawah bidang kuasa PDRM & TPR.",
        "source_section_doc_ids": ["AKTA_344__S90", "AKTA_344__S20", "AKTA_574__S186"],
        "verified_status": "DRAFT_PENDING_REVIEW",
    },
]


# =====================================================================
# 4. PENGHURAI DETERMINISTIK PDF WARTA & TEKS AKTA (FASA 2)
# =====================================================================

OFFENCE_KEYWORDS_RE = re.compile(
    r"\b(?:"
    r"melakukan\s+suatu\s+kesalahan|apabila\s+disabitkan|boleh\s+didenda|dipenjarakan|dilarang|tidak\s+boleh|tiada\s+seorang\s+pun\s+boleh"
    r"|commits\s+an\s+offence|liable\s+on\s+conviction|guilty\s+of\s+an\s+offence|shall\s+not"
    r")\b",
    re.I,
)
PENALTY_KEYWORDS_RE = re.compile(
    r"\b(?:"
    r"didenda|denda|dipenjarakan|penjara|penalti|hukuman|khidmat\s+masyarakat|RM\s?[\d,]+|ringgit"
    r"|fine\s+not\s+exceeding|imprisonment\s+for\s+a\s+term|punishable|penalty"
    r")\b",
    re.I,
)
PROCEDURE_KEYWORDS_RE = re.compile(
    r"\b(?:"
    r"kuasa|pegawai\s+diberi\s+kuasa|menyita|sitaan|memasuki|memeriksa|perakuan|mengkompaun|kompaun|notis|saman|pertuduhan|diari\s+siasatan|mahkamah"
    r"|search\s+warrant|arrest|investigation|diary|statement|magistrate|compound|seize|prosecution"
    r")\b",
    re.I,
)
CROSS_REF_RE = re.compile(
    r"(?:Seksyen\s+\d+[A-Za-z]?(?:\(\d+\))?(?:\([a-z]\))?"
    r"|Peraturan\s+\d+[A-Za-z]?(?:\(\d+\))?"
    r"|Section\s+\d+[A-Za-z]?(?:\(\d+\))?"
    r"|subseksyen\s+\(\d+\)|subsection\s+\(\d+\)"
    r"|Jadual\s+(?:Pertama|Kedua|Ketiga|Keempat|Kelima|Keenam)"
    r"|(?:First|Second|Third|Fourth)\s+Schedule"
    r"|P\.U\.\s*\([AB]\)\s*\d+/\d{4}|Akta\s+[A]?\d+|Act\s+[A]?\d+)",
    re.I,
)

REGULATION_STATUTE_IDS = {
    "PPKM_2009",
    "PPM_1985",
    "AKTA_852_PERINTAH_LARANGAN_2024",
    "AKTA_852_PERATURAN_TANDA_2024",
    "AKTA_852_PERATURAN_KOMPAUN_2024",
    "AKTA_852_PERATURAN_JUALAN_2024",
    "AKTA_852_PERATURAN_PEMBUNGKUSAN_2024",
    "AKTA_852_PERATURAN_PENDAFTARAN_2024",
    "AKTA_852_PERINTAH_MAKMAL_2024",
    "AKTA_852_PERATURAN_NOTIS_S47_2024",
    "AKTA_342_PERATURAN_KOMPAUN_2025",
}


def infer_statute_id_from_filename_or_text(
    filename: str,
    text: str = "",
    explicit_statute_id: Optional[str] = None,
) -> str:
    if explicit_statute_id and explicit_statute_id.strip():
        raw = explicit_statute_id.strip().upper().replace(" ", "_").replace("-", "_")
        if raw in ("852", "AKTA852"):
            return "AKTA_852"
        if raw in ("281", "AKTA281"):
            return "AKTA_281"
        if raw in ("154", "AKTA154"):
            return "AKTA_154"
        if raw in ("342", "AKTA342"):
            return "AKTA_342"
        if raw in ("593", "AKTA593", "KTJ", "CPC"):
            return "AKTA_593"
        if raw in ("56", "AKTA56"):
            return "AKTA_56"
        if raw in ("611", "AKTA611"):
            return "AKTA_611"
        if raw in ("574", "AKTA574", "KK", "PENAL_CODE", "KANUN_KESEKSAAN"):
            return "AKTA_574"
        if raw in ("344", "AKTA344", "POLIS", "POLICE_ACT"):
            return "AKTA_344"
        if raw in ("388", "AKTA388", "TAFSIRAN", "TAFSIRAN_1948", "TAFSIRAN_1967", "INTERPRETATION_ACTS"):
            return "AKTA_388"
        if raw in ("92", "AKTA92", "MAHKAMAH_RENDAH", "SUBORDINATE_COURTS"):
            return "AKTA_92"
        return raw

    stem_up = Path(filename).stem.upper()
    # Padanan tepat nama fail rasmi Warta AGC
    exact_stem_map = {
        "AKTA_852": "AKTA_852",
        "AKTA_852_PERINTAH_LARANGAN_2024": "AKTA_852_PERINTAH_LARANGAN_2024",
        "AKTA_852_PERATURAN_TANDA_2024": "AKTA_852_PERATURAN_TANDA_2024",
        "AKTA_852_PERATURAN_KOMPAUN_2024": "AKTA_852_PERATURAN_KOMPAUN_2024",
        "AKTA_852_PERATURAN_JUALAN_2024": "AKTA_852_PERATURAN_JUALAN_2024",
        "AKTA_852_PERATURAN_PEMBUNGKUSAN_2024": "AKTA_852_PERATURAN_PEMBUNGKUSAN_2024",
        "AKTA_852_PERATURAN_PENDAFTARAN_2024": "AKTA_852_PERATURAN_PENDAFTARAN_2024",
        "AKTA_852_PERINTAH_MAKMAL_2024": "AKTA_852_PERINTAH_MAKMAL_2024",
        "AKTA_852_PERATURAN_NOTIS_S47_2024": "AKTA_852_PERATURAN_NOTIS_S47_2024",
        "AKTA_281": "AKTA_281",
        "AKTA_281_PINDAAN_A1702_2024": "AKTA_281_PINDAAN_2024",
        "PPKM_2009": "PPKM_2009",
        "PPM_1985": "PPM_1985",
        "AKTA_154": "AKTA_154",
        "AKTA_342": "AKTA_342",
        "AKTA_342_PINDAAN_A1742_2025": "AKTA_342_PINDAAN_2025",
        "AKTA_342_PERATURAN_KOMPAUN_2025": "AKTA_342_PERATURAN_KOMPAUN_2025",
        "AKTA_593": "AKTA_593",
        "AKTA_56": "AKTA_56",
        "AKTA_611": "AKTA_611",
        "AKTA_574": "AKTA_574",
        "AKTA_344": "AKTA_344",
        "AKTA_388": "AKTA_388",
        "AKTA_92": "AKTA_92",
    }
    if stem_up in exact_stem_map:
        return exact_stem_map[stem_up]

    low_stem = Path(filename).stem.lower()
    low = (low_stem + " " + (text or "")[:900]).lower()
    if "257/2024" in low or ("larangan" in low_stem and "852" in low):
        return "AKTA_852_PERINTAH_LARANGAN_2024"
    if "258/2024" in low or ("tanda" in low_stem and "852" in low):
        return "AKTA_852_PERATURAN_TANDA_2024"
    if "259/2024" in low or ("kompaun" in low_stem and "852" in low):
        return "AKTA_852_PERATURAN_KOMPAUN_2024"
    if "260/2024" in low or ("jualan" in low_stem and "852" in low):
        return "AKTA_852_PERATURAN_JUALAN_2024"
    if "261/2024" in low or ("pembungkusan" in low_stem and "852" in low):
        return "AKTA_852_PERATURAN_PEMBUNGKUSAN_2024"
    if "262/2024" in low or ("pendaftaran" in low_stem and "852" in low):
        return "AKTA_852_PERATURAN_PENDAFTARAN_2024"
    if "263/2024" in low or ("makmal" in low_stem and "852" in low):
        return "AKTA_852_PERINTAH_MAKMAL_2024"
    if "264/2024" in low or ("notis" in low_stem and "852" in low):
        return "AKTA_852_PERATURAN_NOTIS_S47_2024"
    if "139/2025" in low or ("kompaun" in low_stem and "342" in low):
        return "AKTA_342_PERATURAN_KOMPAUN_2025"
    if "a1742" in low:
        return "AKTA_342_PINDAAN_2025"
    if "a1702" in low:
        return "AKTA_281_PINDAAN_2024"
    if "852" in low or "produk merokok" in low:
        return "AKTA_852"
    if "ppkm" in low or "95/2009" in low or "kebersihan makanan 2009" in low:
        return "PPKM_2009"
    if "ppm 1985" in low or "ppm_1985" in low or "437/1985" in low or "peraturan-peraturan makanan 1985" in low:
        return "PPM_1985"
    if "281" in low or "akta makanan" in low:
        return "AKTA_281"
    if "154" in low or "serangga pembawa penyakit" in low:
        return "AKTA_154"
    if "342" in low or "penyakit berjangkit" in low:
        return "AKTA_342"
    if "593" in low or "tatacara jenayah" in low or "criminal procedure code" in low:
        return "AKTA_593"
    if "90a" in low or re.search(r"\b(?:akta|act)[\s_]*56\b", low) or "keterangan 1950" in low or "evidence act 1950" in low:
        return "AKTA_56"
    if "611" in low or "kanak-kanak 2001" in low or "child act 2001" in low:
        return "AKTA_611"
    if re.search(r"\b(?:akta|act)[\s_]*574\b", low) or "kanun keseksaan" in low or "penal code" in low:
        return "AKTA_574"
    if re.search(r"\b(?:akta|act)[\s_]*344\b", low) or "akta polis" in low or "police act 1967" in low:
        return "AKTA_344"
    if re.search(r"\b(?:akta|act)[\s_]*388\b", low) or "akta tafsiran" in low or "interpretation acts" in low:
        return "AKTA_388"
    if re.search(r"\b(?:akta|act)[\s_]*92\b", low) or "mahkamah rendah 1948" in low or "subordinate courts act" in low:
        return "AKTA_92"
    clean_stem = re.sub(r"[^A-Z0-9_]+", "_", Path(filename).stem.upper()).strip("_")
    return clean_stem or "AKTA_UMUM"


def canonical_akta_code_for_statute(statute_id: str) -> str:
    sid = (statute_id or "").upper().strip()
    if re.search(r"\b852\b|AKTA_852", sid):
        return "Akta 852"
    if re.search(r"\b281\b|AKTA_281|PPKM|PPM", sid):
        return "Akta 281"
    if re.search(r"\b154\b|AKTA_154", sid):
        return "Akta 154"
    if re.search(r"\b342\b|AKTA_342|APPPB", sid):
        return "Akta 342"
    if re.search(r"\b593\b|AKTA_593|\bKTJ\b|\bCPC\b|TATACARA\s+JENAYAH", sid):
        return "Akta 593"
    if re.search(r"\b574\b|AKTA_574|KANUN\s+KESEKSAAN|PENAL\s+CODE", sid):
        return "Akta 574"
    if re.search(r"\b344\b|AKTA_344|AKTA\s+POLIS|POLICE\s+ACT", sid):
        return "Akta 344"
    if re.search(r"\b388\b|AKTA_388|AKTA\s+TAFSIRAN|TAFSIRAN\s+1948|INTERPRETATION\s+ACT", sid):
        return "Akta 388"
    if re.search(r"(?:^|[^0-9])(?:AKTA[\s_]*)?92(?:[^0-9]|$)|MAHKAMAH\s+RENDAH|SUBORDINATE\s+COURTS", sid):
        return "Akta 92"
    if re.search(r"(?:^|[^0-9])(?:AKTA[\s_]*)?56(?:[^0-9]|$)|AKTA\s+KETERANGAN|EVIDENCE\s+ACT", sid):
        return "Akta 56"
    if re.search(r"\b611\b|AKTA_611|KANAK-KANAK", sid):
        return "Akta 611"
    return statute_id


def _clean_agc_pdf_text(raw_text: str) -> str:
    """Menyingkirkan Jadual Kandungan (TOC), pengulangan header halaman AGC, dan salinan BI dwibahasa tanpa mengubah satu pun perkataan teks statutori."""
    text = (raw_text or "").replace("\r\n", "\n")

    # 1. Jika fail ialah Warta P.U.(A) dwibahasa (BM penuh diikuti "IN exercise of the powers conferred"),
    #    kekalkan bahagian BM lengkap (termasuk semua peraturan & jadual BM) supaya seksyen tidak berganda.
    m_bm_enact = re.search(r"(?:^|\n)\s*PADA\s+menjalankan\s+kuasa\b", text, re.I)
    m_en_enact = re.search(r"(?:^|\n)\s*IN\s+exercise\s+of\s+the\s+powers\s+conferred\b", text, re.I)
    if m_bm_enact and m_en_enact and m_en_enact.start() > m_bm_enact.start():
        bm_slice = text[: m_en_enact.start()]
        m_end_bm = list(
            re.finditer(
                r"Dibuat\s+\d{1,2}\s+[A-Za-z]+\s+\d{4}.*?(?:Menteri[^\n]*)",
                bm_slice,
                re.I | re.S,
            )
        )
        if m_end_bm:
            text = bm_slice[: m_end_bm[-1].end()]
        else:
            cut_idx = max(bm_slice.rfind("\n\n\n"), bm_slice.rfind("\nP.U. (A)"))
            text = bm_slice[:cut_idx] if cut_idx > m_bm_enact.start() else bm_slice

    # 2. Langkau Jadual Kandungan (SUSUNAN SEKSYEN / SUSUNAN PERATURAN / ARRANGEMENT OF SECTIONS)
    m_toc = re.search(
        r"SUSUNAN\s+(?:SEKSYEN|PERATURAN)|ARRANGEMENT\s+OF\s+SECTIONS",
        text,
        re.I,
    )
    if m_toc:
        window_limit = min(len(text), m_toc.end() + int(len(text) * 0.45) + 25000)
        search_window = text[m_toc.end() : window_limit]
        # Pilih penanda permulaan badan akta PALING AWAL selepas Jadual Kandungan
        body_candidates = [
            m
            for pat in (
                r"(?:^|\n)\s*MAKA\s+INILAH\s+DIPERBUAT\b",
                r"(?:^|\n)\s*DIPERBUAT\s+oleh\s+Parlimen\b",
                r"(?:^|\n)\s*PADA\s+menjalankan\s+kuasa\b",
                r"(?:^|\n)\s*BE\s+IT\s+ENACTED\b",
                r"(?:^|\n)\s*ENACTED\s+by\s+the\s+Parliament\b",
                r"(?:^|\n)\s*Suatu\s+Akta\s+(?:bagi|untuk)\s+",
                r"(?:^|\n)\s*An\s+Act\s+(?:relating\s+to|to)\s+",
            )
            for m in [re.search(pat, search_window, re.I)]
            if m is not None
        ]
        if body_candidates:
            earliest = min(body_candidates, key=lambda m: m.start())
            text = text[m_toc.end() + earliest.start() :]
    elif m_bm_enact:
        text = text[m_bm_enact.start() :]

    # 2b. Buang lampiran editorial cetakan semula di penghujung PDF ("SENARAI PINDAAN" / "LIST OF AMENDMENTS")
    m_amend = re.search(
        r"(?:^|\n)\s*(?:SENARAI\s+PINDAAN|LIST\s+OF\s+AMENDMENTS|SENARAI\s+SEKSYEN\s+YANG\s+DIPINDA|LIST\s+OF\s+SECTIONS\s+AMENDED)\b",
        text,
        re.I,
    )
    if m_amend and m_amend.start() > int(len(text) * 0.55):
        text = text[: m_amend.start()]

    # 3. Buang running header/footer halaman rasmi AGC tanpa menyentuh teks peruntukan
    cleaned_lines: List[str] = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            cleaned_lines.append("")
            continue
        if re.fullmatch(r"\d{1,3}", s):
            continue
        if re.fullmatch(
            r"(?:Undang-Undang\s+Malaysia|Laws\s+of\s+Malaysia|AKTA\s+[A]?\d+|Akta\s+[A]?\d+|ACT\s+[A]?\d+|Act\s+[A]?\d+|P\.U\.\s*\([AB]\)\s*\d+)",
            s,
            re.I,
        ):
            continue
        if re.match(r"^\d{1,3}\s+(?:Undang-Undang\s+Malaysia|Laws\s+of\s+Malaysia)\b", s, re.I):
            continue
        if re.match(r"^(?:Undang-Undang\s+Malaysia|Laws\s+of\s+Malaysia)\s+\d{1,3}$", s, re.I):
            continue
        if re.match(r"^Kemaskini\s+sehingga\s+", s, re.I):
            continue
        if re.match(
            r"^(?:Kawalan\s+Produk\s+Merokok\s+Demi\s+Kesihatan\s+Awam"
            r"|Pemusnahan\s+Serangga\s+Pembawa\s+Penyakit"
            r"|Pencegahan\s+dan\s+Pengawalan(?:\s+Penyakit\s+Berjangkit(?:\s+\(Pindaan\))?)?"
            r"|Penyakit\s+Berjangkit"
            r"|Makanan(?:\s+\(Pindaan\))?|Kanak-Kanak|Keterangan|Criminal\s+Procedure\s+Code|Evidence"
            r"|Penal\s+Code|Kanun\s+Keseksaan|Police|Polis|Interpretation(?:\s+Acts)?|Tafsiran"
            r"|Subordinate\s+Courts|Mahkamah\s+Rendah)(?:\s+\d{1,3})?$",
            s,
            re.I,
        ):
            continue
        cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


def parse_statute_verbatim_sections(
    raw_text: str,
    default_statute_id: str,
    source_filename: str = "",
) -> Tuple[List[Dict[str, Any]], int]:
    """Menghurai teks Warta Kerajaan (PDF/TXT) secara deterministik tanpa mengubah walau satu perkataan."""
    raw_norm = (raw_text or "").replace("\r\n", "\n").strip()
    if not raw_norm:
        return [], 0

    is_pdf_src = str(source_filename or "").lower().endswith(".pdf")
    is_agc_pdf = is_pdf_src and (
        len(raw_norm) > 1500
        or bool(
            re.search(
                r"UNDANG-UNDANG\s+MALAYSIA|LAWS\s+OF\s+MALAYSIA|WARTA\s+KERAJAAN\s+PERSEKUTUAN|SUSUNAN\s+(?:SEKSYEN|PERATURAN)|PADA\s+menjalankan\s+kuasa",
                raw_norm[:3500],
                re.I,
            )
        )
    )
    text = _clean_agc_pdf_text(raw_norm) if is_agc_pdf else raw_norm
    lines = text.splitlines()
    total_lines = len(lines)

    part_header_re = re.compile(
        r"^\s*(BAHAGIAN\s+[IVXLCDM0-9]+[A-Za-z]?|PART\s+[IVXLCDM0-9]+[A-Za-z]?|CHAPTER\s+[IVXLCDM0-9]+[A-Za-z]?|BAB\s+[IVXLCDM0-9]+[A-Za-z]?)\s*(?:[-–—:]\s*(.*))?$",
        re.I,
    )
    schedule_header_re = re.compile(
        r"^\s*(JADUAL(?:\s+(?:PERTAMA|KEDUA|KETIGA|KEEMPAT|KELIMA|KEENAM|KETUJUH|KELAPAN|KESEMBILAN|KESEPULUH|[A-Z0-9]+))?"
        r"|(?:FIRST|SECOND|THIRD|FOURTH|FIFTH|SIXTH)\s+SCHEDULE|SCHEDULE)\s*$",
        re.I,
    )
    named_sec_re = re.compile(
        r"^\s*(?:-\s*)?(Seksyen|Peraturan|Jadual|Section)\s+([0-9A-Za-z\(\),\s&/]+?)(?:\s+(?:Akta|PPKM|PPM|KTJ)[^-–—:\n]*)?(?:\s*[-–—:\.]\s*(.*))?$",
        re.I,
    )
    strict_pdf_named_sec_re = re.compile(
        r"^\s*(Seksyen|Peraturan|Section|Regulation)\s+(\d+[A-Za-z]{0,2}(?:\(\d+\))?)\s*(?:[-–—:\.]\s*(.*))?$"
    )
    num_inline_re = re.compile(r"^\s*(\*{0,3})\s*(\d+[A-Za-z]{0,2})\s*\.(?:\s+|(?=\())(.+)$")
    num_alone_re = re.compile(r"^\s*(\*{0,3})\s*(\d+[A-Za-z]{0,2})\s*\.\s*$")
    prev_ref_tail_re = re.compile(
        r"\b(?:seksyen|peraturan|section|regulation|akta|act|no|bahagian|bab|perenggan|subseksyen|subperaturan|jadual|schedule)\s*$",
        re.I,
    )
    is_reg_statute = (
        default_statute_id in REGULATION_STATUTE_IDS
        or "PERATURAN" in default_statute_id
        or "PERINTAH" in default_statute_id
    )

    def _next_nonempty(idx: int) -> str:
        for j in range(idx + 1, min(total_lines, idx + 5)):
            st = lines[j].strip()
            if st:
                return st
        return ""

    def _prev_nonempty(idx: int) -> str:
        for j in range(idx - 1, max(-1, idx - 5), -1):
            st = lines[j].strip()
            if st:
                return st
        return ""

    # Setiap item: [part_num, part_title, sec_code, sec_heading, body_lines]
    raw_blocks: List[List[Any]] = []
    cur: Optional[List[Any]] = None
    pending_heading_lines: List[str] = []
    current_part_num = "BAHAGIAN I"
    current_part_title = "Peruntukan Statutori & Penguatkuasaan"
    in_schedule = False
    last_sec_int = 0
    part_just_changed = False

    def _pop_marginal_heading() -> List[str]:
        nonlocal pending_heading_lines
        if cur is not None:
            body_l: List[str] = cur[4]
            while body_l and not body_l[-1].strip():
                body_l.pop()
            cand: List[str] = []
            while body_l and len(cand) < 4:
                tail = body_l[-1].strip()
                if not tail:
                    break
                if (
                    tail.endswith((".", ";", ":", "—", "”", '"'))
                    or re.match(r"^(?:\([a-z0-9]+\)|\[|\d+\.|Bahagian|Part|Chapter|Bab|Jadual|Schedule)", tail, re.I)
                    or len(tail) > 105
                ):
                    break
                cand.append(body_l.pop().strip())
            return list(reversed(cand))
        if pending_heading_lines:
            res = pending_heading_lines[-3:]
            pending_heading_lines = []
            return res
        return []

    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            if cur is not None:
                cur[4].append("")
            continue

        # 1. Semak sempadan Jadual / Schedule (sekali masuk Jadual, kekal in_schedule supaya item bernombor dalam Jadual tidak dianggap Seksyen baharu)
        if is_agc_pdf:
            sm = schedule_header_re.match(stripped)
            if sm:
                if cur is not None:
                    raw_blocks.append(cur)
                in_schedule = True
                sched_name = re.sub(r"\s+", " ", sm.group(1).strip()).title()
                cur = [current_part_num, current_part_title, sched_name, sched_name, [stripped]]
                pending_heading_lines = []
                continue

        # 2. Semak sempadan Bahagian / Part / Chapter / Bab (kecuali Bahagian dalam Jadual)
        pm = part_header_re.match(stripped)
        if pm and not in_schedule and not stripped.endswith((".", ";", ",")):
            if cur is not None and not is_agc_pdf:
                raw_blocks.append(cur)
                cur = None
            current_part_num = re.sub(r"\s+", " ", pm.group(1).strip().upper())
            inline_title = (pm.group(2) or "").strip()
            if not inline_title:
                nxt = _next_nonempty(idx)
                if nxt and len(nxt) < 105 and not named_sec_re.match(nxt) and not num_inline_re.match(nxt) and not num_alone_re.match(nxt):
                    inline_title = nxt
            current_part_title = inline_title or current_part_title
            pending_heading_lines = []
            part_just_changed = True
            continue

        # 3. Semak permulaan Seksyen / Peraturan / Item bernombor AGC
        if not in_schedule:
            m_named = strict_pdf_named_sec_re.match(stripped) if is_agc_pdf else named_sec_re.match(stripped)
            if m_named:
                kind = m_named.group(1).strip().capitalize()
                num_part = re.sub(r"\s+", " ", m_named.group(2).strip()).rstrip(".")
                tail_head = (m_named.group(3) or "").strip()
                if cur is not None:
                    raw_blocks.append(cur)
                sec_code = f"{kind} {num_part}" if kind not in ("Seksyen", "Section") else num_part
                sec_head = tail_head if tail_head else stripped[:140]
                m_int = re.match(r"^(\d+)", num_part)
                if m_int:
                    last_sec_int = int(m_int.group(1))
                part_just_changed = False
                cur = [current_part_num, current_part_title, sec_code, sec_head[:160], [stripped]]
                pending_heading_lines = []
                continue

            # Format nombor Warta AGC: "17. (1) Tiada...", "*88. ...", "31.(1)...", "17.\n(1)...", atau "5 . Pengarah..."
            m_in = num_inline_re.match(stripped)
            m_al = num_alone_re.match(stripped) if not m_in else None
            matched_num: Optional[str] = None
            rest_text = ""
            if m_in:
                stars = m_in.group(1) or ""
                num_str = m_in.group(2)
                rest_text = m_in.group(3).strip()
                base_int = int(re.match(r"^\d+", num_str).group(0))  # type: ignore[union-attr]
                star_ok = (not stars) or (last_sec_int == 0) or part_just_changed or (base_int >= last_sec_int)
                if 1 <= base_int <= 550 and star_ok and re.match(r"^(?:\(\d+[A-Za-z]?\)|[A-Z“\"])", rest_text):
                    matched_num = num_str.upper()
                    last_sec_int = base_int
                    part_just_changed = False
            elif m_al and is_agc_pdf:
                stars = m_al.group(1) or ""
                num_str = m_al.group(2)
                base_int = int(re.match(r"^\d+", num_str).group(0))  # type: ignore[union-attr]
                nxt = _next_nonempty(idx)
                prv = _prev_nonempty(idx)
                jump_ok = (last_sec_int == 0) or part_just_changed or (base_int <= last_sec_int + 80)
                star_ok = (not stars) or (last_sec_int == 0) or part_just_changed or (base_int >= last_sec_int)
                is_marginal_act_heading = bool(re.search(r"\b(?:of|this|the)\s+(?:act|akta)\s*$", prv, re.I))
                if (
                    1 <= base_int <= 550
                    and jump_ok
                    and star_ok
                    and (not prev_ref_tail_re.search(prv) or is_marginal_act_heading)
                    and re.match(r"^(?:\(\d+[A-Za-z]?\)|[A-Z“\"])", nxt)
                ):
                    matched_num = num_str.upper()
                    last_sec_int = base_int
                    part_just_changed = False

            if matched_num is not None:
                heading_lines = _pop_marginal_heading() if is_agc_pdf else []
                if cur is not None:
                    raw_blocks.append(cur)
                heading_str = " ".join(heading_lines).strip()
                if not heading_str:
                    heading_str = rest_text[:140] if rest_text else f"{'Peraturan' if is_reg_statute else 'Seksyen'} {matched_num}"
                sec_code_lbl = f"Peraturan {matched_num}" if is_reg_statute else matched_num
                body_init = (heading_lines + [stripped]) if heading_lines else [stripped]
                cur = [current_part_num, current_part_title, sec_code_lbl, heading_str[:160], body_init]
                pending_heading_lines = []
                continue

            # Sokongan fail teks rujukan ringkas ("Keperluan ...", "- Akta ...")
            if not is_agc_pdf and re.match(r"^\s*(?:-\s*)?(?:Keperluan|Dokumen\s+Wajib|Akta)\s+", stripped, re.I):
                if cur is not None:
                    raw_blocks.append(cur)
                cur = [current_part_num, current_part_title, f"BLOK_{len(raw_blocks) + 1}", stripped.lstrip("- ")[:140], [stripped]]
                continue

        if cur is not None:
            cur[4].append(stripped)
        else:
            if len(stripped) < 105 and not stripped.endswith((".", ";")):
                pending_heading_lines.append(stripped)

    if cur is not None:
        raw_blocks.append(cur)

    sections_out: List[Dict[str, Any]] = []
    seen_doc_ids: set[str] = set()
    is_multi_file = "lain_rujukan" in (source_filename or "").lower()

    for b_idx, (p_num, p_title, sec_code, sec_heading, body_lines) in enumerate(raw_blocks):
        clean_blk = "\n".join(body_lines).strip()
        # Buang baris kosong berturut-turut berlebihan sambil mengekalkan susunan verbatim
        clean_blk = re.sub(r"\n{3,}", "\n\n", clean_blk)
        if len(clean_blk) < 25:
            continue

        first_line = clean_blk.splitlines()[0].lstrip("- ").strip()
        blk_statute_id = default_statute_id
        if not is_agc_pdf:
            low_first = first_line.lower()
            if "ppkm 2009" in low_first or "kebersihan makanan 2009" in low_first or (
                default_statute_id == "AKTA_281" and low_first.startswith("peraturan")
            ):
                blk_statute_id = "PPKM_2009"
            elif "ppm 1985" in low_first or "kebersihan makanan 1985" in low_first:
                blk_statute_id = "PPM_1985"
            elif is_multi_file:
                blk_statute_id = infer_statute_id_from_filename_or_text(source_filename, clean_blk)

        # Normalisasikan kod untuk doc_id unik (cth: AKTA_852__S17, PPKM_2009__P31, AKTA_56__S90A)
        norm_code_slug = re.sub(r"[^A-Za-z0-9]+", "_", str(sec_code)).strip("_").upper()
        if not norm_code_slug:
            norm_code_slug = f"SEC_{b_idx + 1}"
        if norm_code_slug[0].isdigit():
            prefix = "P" if (blk_statute_id in REGULATION_STATUTE_IDS or "PERATURAN" in blk_statute_id or "PERINTAH" in blk_statute_id) else "S"
            norm_code_slug = f"{prefix}{norm_code_slug}"
        elif norm_code_slug.startswith("PERATURAN_"):
            norm_code_slug = "P" + norm_code_slug[len("PERATURAN_") :]
        elif norm_code_slug.startswith("SEKSYEN_"):
            norm_code_slug = "S" + norm_code_slug[len("SEKSYEN_") :]

        doc_id = f"{blk_statute_id}__{norm_code_slug}"
        if doc_id in seen_doc_ids:
            doc_id = f"{doc_id}_{b_idx + 1}"
        seen_doc_ids.add(doc_id)

        # Ekstrak subseksyen (1), (2), (a), (b)
        subsections: List[Dict[str, str]] = []
        sub_matches = list(
            re.finditer(
                r"(?:^|\n)\s*(\(\d+[A-Za-z]?\)|\([a-z]\)|-\s*Seksyen\s+\d+[A-Za-z\(\)]*|-\s*Peraturan\s+\d+[A-Za-z\(\)]*)\s*(.+?)(?=(?:\n\s*(?:\(\d+[A-Za-z]?\)|\([a-z]\)|-\s*(?:Seksyen|Peraturan)))|\Z)",
                clean_blk,
                flags=re.S,
            )
        )
        for sm in sub_matches[:40]:
            sub_code = sm.group(1).lstrip("- ").strip()
            sub_txt = sm.group(2).strip()
            if sub_txt:
                subsections.append({"sub_code": sub_code, "verbatim_text": sub_txt})

        cross_refs = list(dict.fromkeys(m.group(0).strip() for m in CROSS_REF_RE.finditer(clean_blk)))

        is_offence = bool(OFFENCE_KEYWORDS_RE.search(clean_blk))
        is_penalty = bool(PENALTY_KEYWORDS_RE.search(clean_blk))
        is_proc = bool(PROCEDURE_KEYWORDS_RE.search(clean_blk))

        sections_out.append(
            {
                "doc_id": doc_id,
                "statute_id": blk_statute_id,
                "part_number": p_num,
                "part_title": p_title,
                "section_code": str(sec_code),
                "section_heading": str(sec_heading)[:160],
                "verbatim_text_bm": clean_blk,
                "subsections": subsections,
                "cross_references": cross_refs,
                "is_offence_provision": is_offence,
                "is_penalty_provision": is_penalty,
                "is_procedure_or_power": is_proc,
                "embedding_vector": compute_deterministic_embedding(
                    f"{blk_statute_id} {sec_code} {sec_heading} {clean_blk[:1200]}"
                ),
            }
        )

    return sections_out, len(sections_out)


def sweep_sections_for_offences(
    sections: List[Dict[str, Any]],
    statute_id: str,
    existing_offences: List[Dict[str, Any]],
    verified_by_admin: bool = False,
) -> List[Dict[str, Any]]:
    """FASA 2.3: Imbasan Seksyen-demi-Seksyen (Section-by-Section Sweep) untuk mengekstrak semua kesalahan."""
    existing_by_sec: Dict[Tuple[str, str], Dict[str, Any]] = {}
    existing_off_ids: set[str] = set()
    for off in existing_offences:
        oid = str(off.get("offence_id") or "").strip().upper()
        if oid:
            existing_off_ids.add(oid)
        sid = str(off.get("statute_id") or "")
        sec_num = re.findall(r"\d+[A-Za-z]{0,2}", str(off.get("offence_section") or ""))
        if sid and sec_num:
            existing_by_sec[(sid, sec_num[0].upper())] = off

    explicit_offence_phrases = (
        "melakukan suatu kesalahan",
        "melakukan kesalahan",
        "apabila disabitkan",
        "boleh didenda",
        "dikenakan penalti",
        "adalah suatu kesalahan",
        "tiada seorang pun boleh",
        "tidak boleh menjual",
        "tidak boleh mempamerkan",
        "tidak boleh mengimport",
        "tidak boleh mengilang",
        "tidak boleh membungkus",
        "tidak boleh merokok",
        "tidak boleh dihalang",
        "tidak boleh dipindahkan",
        "tiada pembungkusan",
        "hendaklah, pada setiap masa mempamerkan",
        "commits an offence",
        "liable to a fine",
    )
    bm_fine_words: Tuple[Tuple[str, int], ...] = (
        ("dua juta ringgit", 2000000),
        ("satu juta ringgit", 1000000),
        ("lima ratus ribu ringgit", 500000),
        ("tiga ratus ribu ringgit", 300000),
        ("dua ratus ribu ringgit", 200000),
        ("seratus ribu ringgit", 100000),
        ("satu ratus ribu ringgit", 100000),
        ("lima puluh ribu ringgit", 50000),
        ("tiga puluh ribu ringgit", 30000),
        ("dua puluh lima ribu ringgit", 25000),
        ("dua puluh ribu ringgit", 20000),
        ("sepuluh ribu ringgit", 10000),
        ("lima ribu ringgit", 5000),
        ("tiga ribu ringgit", 3000),
        ("dua ribu ringgit", 2000),
        ("satu ribu ringgit", 1000),
        ("seribu ringgit", 1000),
        ("lima ratus ringgit", 500),
    )
    bm_jail_words: Tuple[Tuple[str, int], ...] = (
        ("sepuluh tahun", 120),
        ("tujuh tahun", 84),
        ("lima tahun", 60),
        ("tiga tahun", 36),
        ("dua tahun", 24),
        ("satu tahun", 12),
        ("setahun", 12),
        ("enam bulan", 6),
    )

    non_offence_admin_keys = {
        ("AKTA_852", "2"), ("AKTA_852", "24"), ("AKTA_852", "25"), ("AKTA_852", "27"),
        ("AKTA_852", "31"), ("AKTA_852", "35"), ("AKTA_852", "36"), ("AKTA_852", "38"),
        ("AKTA_852", "44"), ("AKTA_852", "47"), ("AKTA_852", "48"), ("AKTA_852", "49"), ("AKTA_852", "51"),
        ("AKTA_281", "2"), ("AKTA_281", "3"), ("AKTA_281", "4"), ("AKTA_281", "5"),
        ("AKTA_281", "8"), ("AKTA_281", "9"), ("AKTA_281", "25"), ("AKTA_281", "32A"),
        ("AKTA_281", "32B"), ("AKTA_281", "33"), ("AKTA_281", "33A"),
        ("AKTA_154", "2"), ("AKTA_154", "3"), ("AKTA_154", "10A"), ("AKTA_154", "23"), ("AKTA_154", "25"),
        ("AKTA_342", "2"), ("AKTA_342", "3"), ("AKTA_342", "24"), ("AKTA_342", "25"),
        ("AKTA_342_PINDAAN_2025", "22A"), ("AKTA_342_PINDAAN_2025", "24"), ("AKTA_342_PINDAAN_2025", "25"),
        ("PPKM_2009", "58"), ("PPKM_2009", "59"), ("PPKM_2009", "60"),
    }
    ppkm_2009_compoundable_nums = {
        "3", "7", "8", "9", "10", "11",
        "30", "31", "32", "33", "34", "35", "36", "37", "38", "39", "40",
        "41", "42", "43", "44", "45", "46", "47", "48", "49", "50", "51",
        "52", "53", "54", "55", "56",
    }
    akta_342_compoundable_nums = {"10", "11", "21A", "22"}

    discovered: List[Dict[str, Any]] = []
    seen_swept_keys: set[Tuple[str, str]] = set()
    for sec in sections:
        sec_code = str(sec.get("section_code") or "").strip()
        if not sec_code or sec_code.lower().startswith(("jadual", "schedule")):
            continue

        sid = str(sec.get("statute_id") or statute_id)
        # Peraturan prosedur kompaun/notis bukan akta kesalahan substantif
        if sid in ("AKTA_852_PERATURAN_KOMPAUN_2024", "AKTA_342_PERATURAN_KOMPAUN_2025", "AKTA_852_PERATURAN_NOTIS_S47_2024"):
            continue

        text = str(sec.get("verbatim_text_bm") or "")
        low = text.lower()
        heading_low = str(sec.get("section_heading") or "").lower()

        sec_nums = re.findall(r"\d+[A-Za-z]{0,2}", sec_code)
        primary_num = sec_nums[0].upper() if sec_nums else ""
        if primary_num and (sid, primary_num) in non_offence_admin_keys:
            continue

        # Abaikan seksyen tajuk ringkas/tafsiran/pelantikan/kuasa pentadbiran semata-mata
        is_explicit_offence = any(k in low for k in explicit_offence_phrases)
        is_reg_prohibition = (
            sid in REGULATION_STATUTE_IDS
            and sec_code.lower() not in ("1", "peraturan 1")
            and any(k in low for k in ("dilarang", "tidak boleh", "hendaklah mematuhi", "hendaklah memenuhi"))
        )
        if not is_explicit_offence and not is_reg_prohibition:
            continue
        admin_heading_terms = (
            "tajuk ringkas",
            "tafsiran",
            "pelantikan pegawai",
            "perakuan pemberian kuasa",
            "perakuan juruanalisis",
            "ejen provokasi",
            "bidang kuasa untuk membicarakan",
            "pendakwaan",
            "pengkompaunan kesalahan",
            "tatacara mengkompaun",
            "penyetujuterimaan kompaun",
            "pembayaran kompaun",
            "kuasa untuk mengkompaun",
            "kuasa mengkompaun",
            "liabiliti pertubuhan perbadanan",
            "kesalahan oleh pertubuhan perbadanan",
            "penalti am",
            "tanggung rugi",
            "perlindungan pemberi maklumat",
            "kuasa untuk memerintahkan kehadiran",
            "kuasa untuk mengambil sampel",
            "kuasa mengambil sampel",
            "kuasa pegawai diberi kuasa",
            "kuasa penyiasatan",
            "penggeledahan dan penyitaan",
            "senarai benda yang disita",
            "kuasa untuk memberhentikan",
            "kuasa meminta maklumat",
            "kuasa ketua pengarah",
        )
        if any(admin_h in heading_low for admin_h in admin_heading_terms):
            continue

        if primary_num and (sid, primary_num) in existing_by_sec:
            # Sudah wujud dalam matriks teras; pastikan source_section_doc_ids dipautkan
            matched_off = existing_by_sec[(sid, primary_num)]
            doc_ids = list(matched_off.get("source_section_doc_ids") or [])
            if sec["doc_id"] not in doc_ids:
                doc_ids.append(sec["doc_id"])
                matched_off["source_section_doc_ids"] = doc_ids
            continue
        if primary_num and (sid, primary_num) in seen_swept_keys:
            continue

        # Ekstrak nilai denda & penjara daripada teks verbatim secara deterministik
        fine_rm: Optional[int] = None
        fine_m = re.search(r"RM\s?([\d,]+)", text, flags=re.I)
        if fine_m:
            try:
                fine_rm = int(fine_m.group(1).replace(",", ""))
            except ValueError:
                fine_rm = None
        if fine_rm is None:
            for phrase, amount in bm_fine_words:
                if phrase in low:
                    fine_rm = amount
                    break

        jail_months: Optional[int] = None
        jail_yr = re.search(r"penjara[^.;\n]*?(\d+)\s*tahun", low)
        jail_mo = re.search(r"penjara[^.;\n]*?(\d+)\s*bulan", low)
        if jail_yr:
            jail_months = int(jail_yr.group(1)) * 12
        elif jail_mo:
            jail_months = int(jail_mo.group(1))
        elif "penjara" in low:
            for phrase, months in bm_jail_words:
                if phrase in low:
                    jail_months = months
                    break

        # Semak kebolehan kompaun secara deterministik berdasarkan Jadual Kompaun rasmi Warta
        if sid == "PPKM_2009":
            is_comp = primary_num in ppkm_2009_compoundable_nums
        elif sid in ("AKTA_342", "AKTA_342_PINDAAN_2025"):
            is_comp = primary_num in akta_342_compoundable_nums
        elif sid.startswith("AKTA_852"):
            # Hanya S.13(3), S.16(2), S.17(1), S.18(1) Akta 852 boleh dikompaun di bawah Jadual Pertama P.U.(A) 259/2024
            is_comp = sid == "AKTA_852" and primary_num in ("16", "17", "18")
        elif sid == "AKTA_154":
            is_comp = primary_num == "13"
        else:
            is_comp = False

        is_reg_sid = sid in REGULATION_STATUTE_IDS or "PERATURAN" in sid or "PERINTAH" in sid
        label_prefix = "Peraturan" if is_reg_sid or "peraturan" in sec_code.lower() else "Seksyen"
        clean_sec_label = sec_code if sec_code.lower().startswith(("seksyen", "peraturan")) else f"{label_prefix} {sec_code}"

        slug = re.sub(r"[^A-Z0-9]+", "_", sec_code.upper()).strip("_")
        off_id = f"{sid}_{slug}"
        if off_id.upper() in existing_off_ids:
            continue
        existing_off_ids.add(off_id.upper())
        if primary_num:
            seen_swept_keys.add((sid, primary_num))

        discovered.append(
            {
                "offence_id": off_id,
                "statute_id": sid,
                "offence_section": clean_sec_label,
                "read_together_with": list(sec.get("cross_references") or [])[:3],
                "offence_title": str(sec.get("section_heading") or f"Kesalahan di bawah {clean_sec_label}"),
                "target_offender": (
                    "OBD_BAWAH_18"
                    if "belum dewasa" in low
                    else (
                        "PERTUBUHAN_PERBADANAN"
                        if "pertubuhan perbadanan" in low
                        else (
                            "PENGENDALI_MAKANAN"
                            if "pengendali makanan" in low
                            else ("TUAN_PUNYA_PREMIS" if "pemunya atau penghuni" in low or "tuan punya atau penghuni" in low else "INDIVIDU")
                        )
                    )
                ),
                "mandatory_elements": [
                    {
                        "element_no": 1,
                        "description": f"Pematuhan intipati perbuatan di bawah {clean_sec_label} ({sec.get('section_heading', '')}).",
                        "must_prove": "Keterangan saksi PPKP, gambar foto bertarikh + Sijil S.90A(2) & barang kes berkaitan.",
                    }
                ],
                "explicit_exclusions_and_traps": [
                    f"Sahkan semua unsur dalam {clean_sec_label} dipenuhi sebelum mengeluarkan notis atau membuka IP."
                ],
                "penalty_section": clean_sec_label,
                "penalty_first_offence": {
                    "max_fine_rm": fine_rm,
                    "max_jail_months": jail_months,
                    "other_orders": None,
                    "verbatim_penalty": text[:280],
                },
                "penalty_subsequent_offence": None,
                "compound_info": {
                    "is_compoundable": is_comp,
                    "compound_authority_section": (
                        "Seksyen 25 Akta 342 (Pindaan Akta A1742)"
                        if "342" in sid and is_comp
                        else ("Peraturan 58 PPKM 2009 / Seksyen 33 Akta 281" if sid == "PPKM_2009" and is_comp else None)
                    ),
                    "compound_regulation_ref": (
                        "Jadual Pertama P.U. (A) 139/2025"
                        if "342" in sid and is_comp
                        else ("Jadual Keempat PPKM 2009" if sid == "PPKM_2009" and is_comp else None)
                    ),
                    "compound_amount_or_limit": (
                        "Boleh dikompaun mengikut jadual kompaun (dengan keizinan bertulis Pendakwa Raya)"
                        if is_comp
                        else "TIDAK BOLEH KOMPAUN — Sita (jika berkenaan) & Buka IP Terus"
                    ),
                    "max_compound_rm": (fine_rm // 2) if (is_comp and fine_rm) else None,
                    "payment_days": (30 if "852" in sid else 14) if is_comp else None,
                    "notice_section": None,
                },
                "special_legal_requirements": ["Sijil Seksyen 90A(2) Akta Keterangan 1950"],
                "mandatory_exhibits": [
                    "Gambar foto lokasi/kejadian berwarna bertarikh + Sijil Seksyen 90A(2)",
                    "Diari Siasatan (S.119 KTJ) & Rakaman Percakapan S.112 KTJ",
                ],
                "charge_sheet_template_bm": (
                    f"Bahawa kamu, pada [TARIKH], jam lebih kurang [MASA], bertempat di [TEMPAT_KEJADIAN], "
                    f"di dalam Daerah [DAERAH], di dalam Negeri [NEGERI], telah didapati melakukan kesalahan "
                    f"di bawah {clean_sec_label} [{sid}]; dan oleh yang demikian kamu boleh dihukum di bawah peruntukan penalti akta yang sama."
                ),
                "source_section_doc_ids": [sec["doc_id"]],
                "verified_status": "VERIFIED_AGC" if verified_by_admin else "DRAFT_PENDING_REVIEW",
            }
        )

    return discovered


# =====================================================================
# 5. SEMAKAN UNSUR MANDATORI & PENGESAH KOD PASCA-PENJANAAN (FASA 3)
# =====================================================================

_GROUNDING_STOPWORDS: set[str] = {
    "yang", "dan", "atau", "di", "ke", "dari", "daripada", "pada", "dalam",
    "untuk", "dengan", "oleh", "adalah", "ialah", "apa", "mana", "suatu",
    "jika", "boleh", "hendaklah", "telah", "ini", "itu",
    "kepada", "ada", "akan", "sudah", "sedang", "masih", "sahaja", "saja",
    "nak", "bolehkah", "adakah", "apakah", "bagaimana", "kenapa", "kalau",
    "bila", "apabila", "tersebut", "secara", "terhadap", "mengenai", "tentang",
    "juga", "lagi", "hanya", "pernah", "kerana", "sebab", "tetapi",
    "tapi", "namun", "supaya", "agar", "semasa", "seorang", "orang", "guru",
    "cikgu", "maklum", "ppkp", "kkm", "pkd", "uip", "kes", "tindakan", "perlu",
    "wajib", "check", "checking", "bag", "the", "and", "for", "with", "that",
    "bawah", "atas", "serta", "bagi", "sebagai", "antara", "lain", "satu",
    "mana2", "sekiranya", "sebarang", "seseorang", "individu", "pihak",
    "dah", "sebuah", "kena", "buat", "kat", "dekat", "masa", "tengah", "punya",
}

_PPKP_COLLOQUIAL_REPLACEMENTS: Tuple[Tuple[str, str], ...] = (
    (r"\btakde\b|\btiade\b|\bxde\b|\btak\s+ada\b", "tiada"),
    (r"\bxleh\b|\btakleh\b|\bx\s*boleh\b|\btak\s+boleh\b", "tidak boleh"),
    (r"\btaknak\b|\bxnak\b|\btak\s+nak\b", "enggan tidak mahu"),
    (r"\bblh\b", "boleh"),
    (r"\bnk\b", "hendak"),
    (r"\bdlm\b", "dalam"),
    (r"\bskrg\b", "sekarang"),
    (r"\bcamne\b|\bcmne\b|\bmcm\s*mana\b", "bagaimana"),
    (r"\bknp\b", "kenapa"),
    (r"\bskolah\b", "sekolah"),
    (r"\bbodycam\b|\bbody\s+cam\b|\bbwc\b", "kamera badan bwc"),
    (r"\bk/s\b", "kertas siasatan"),
    (r"\bpma\b", "pintu masuk antarabangsa"),
    (r"\buipd\b", "unit inspektorat perundangan daerah uipd"),
    (r"\buipn\b", "unit inspektorat perundangan negeri uipn"),
    (r"\bdslr\b", "kamera digital fotografi forensik"),
    (r"\b(?:cd|cdr|cd-r)\b", "cdr gambar digital"),
    (r"\b(?:tutup|penutupan)\s+(?:taska|tadika|kantin|restoran|kedai|kilang|dewan)\b", "tutup premis penutupan premis"),
    (r"\b(?:tangkap|ambik|ambil)\s+(?:gambar|foto)\b", "mengambil gambar fotografi forensik"),
)


def normalize_ppkp_query(text: str) -> str:
    """Menormalkan singkatan SMS/kolokial BM & akronim lapangan PPKP sambil mengekalkan kata nafi (tidak/tiada/belum/tak)."""
    out = (text or "").strip()
    if not out:
        return ""
    for pat, repl in _PPKP_COLLOQUIAL_REPLACEMENTS:
        out = re.sub(pat, lambda _m, r=repl: r, out, flags=re.I)
    return re.sub(r"\s{2,}", " ", out).strip()


_PPKP_SYNONYM_MAP: Dict[str, Tuple[str, ...]] = {
    "cafetaria": ("tempat", "makan", "kafeteria", "premis", "makanan"),
    "kafeteria": ("tempat", "makan", "premis", "makanan"),
    "cafe": ("tempat", "makan", "premis", "makanan"),
    "kafe": ("tempat", "makan", "premis", "makanan"),
    "kantin": ("tempat", "makan", "premis", "makanan"),
    "kopitiam": ("tempat", "makan", "premis", "makanan"),
    "gerai": ("tempat", "makan", "premis", "makanan"),
    "warung": ("tempat", "makan", "premis", "makanan"),
    "restoran": ("tempat", "makan", "premis", "makanan"),
    "universiti": ("institusi", "pendidikan", "tinggi"),
    "university": ("institusi", "pendidikan", "tinggi"),
    "kolej": ("institusi", "pendidikan", "tinggi"),
    "kampus": ("institusi", "pendidikan", "tinggi"),
    "ipt": ("institusi", "pendidikan", "tinggi"),
    "ipta": ("institusi", "pendidikan", "tinggi"),
    "ipts": ("institusi", "pendidikan", "tinggi"),
    "peniaga": ("tuan", "punya", "penghuni", "pemunya", "premis"),
    "pengusaha": ("tuan", "punya", "penghuni", "pemunya", "premis"),
    "tauke": ("tuan", "punya", "penghuni", "pemunya", "premis"),
    "pemilik": ("tuan", "punya", "penghuni", "pemunya", "premis"),
    "owner": ("tuan", "punya", "penghuni", "pemunya", "premis"),
    "pasang": ("mempamerkan", "pamer", "tanda", "amaran"),
    "dipasang": ("mempamerkan", "pamer", "tanda", "amaran"),
    "tampal": ("mempamerkan", "pamer", "tanda", "perakuan"),
    "signboard": ("tanda", "amaran", "larangan", "merokok", "258/2024"),
    "sticker": ("tanda", "amaran", "larangan", "merokok", "kod", "qr"),
    "ashtray": ("bekas", "abu", "rokok", "kemudahan", "merokok"),
    "mall": ("kompleks", "membeli-belah", "bangunan"),
    "shopping": ("kompleks", "membeli-belah", "bangunan"),
    "parking": ("tempat", "letak", "kereta", "bangunan"),
    "parkir": ("tempat", "letak", "kereta", "bangunan"),
    "expired": ("tarikh", "akhir", "luput", "14(9)"),
    "luput": ("tarikh", "akhir", "tamat", "tempoh", "14(9)"),
    "kotor": ("tidak", "bersih", "suci", "perosak", "lilati"),
    "lipas": ("makhluk", "perosak", "lilati", "benda", "asing"),
    "tikus": ("makhluk", "perosak", "lilati", "najis"),
    "lalat": ("makhluk", "perosak", "lilati"),
    "apron": ("pakaian", "pengendali", "makanan", "penutup", "kepala", "32(1)"),
    "tifoid": ("suntikan", "vaksin", "antitifoid", "pemeriksaan", "perubatan", "31(1)"),
    "typhoid": ("suntikan", "vaksin", "antitifoid", "31(1)"),
    "slpm": ("latihan", "pengendali", "makanan", "sijil", "30(1)"),
    "kursus": ("latihan", "pengendali", "makanan", "sijil", "30(1)"),
    "fosim": ("pendaftaran", "perakuan", "premis", "makanan"),
    "vape": ("produk", "pengganti", "tembakau", "rokok", "elektronik", "merokok"),
    "pod": ("produk", "pengganti", "tembakau", "rokok", "elektronik"),
    "nicotine": ("nikotin", "produk", "pengganti", "tembakau"),
    "nikotin": ("produk", "pengganti", "tembakau"),
    "aedes": ("serangga", "pembawa", "penyakit", "larva", "pembiakan"),
    "denggi": ("serangga", "pembawa", "penyakit", "aedes", "larva"),
    "jentik": ("larva", "pupa", "aedes", "pembiakan"),
    "fogging": ("semburan", "kabus", "menghalang", "pegawai"),
    "tibi": ("tuberkulosis", "penyakit", "berjangkit", "rawatan", "perintah"),
    "tb": ("tuberkulosis", "penyakit", "berjangkit", "rawatan", "perintah"),
    "hfmd": ("penyakit", "berjangkit", "penutupan", "premis", "18(1)"),
    "taska": ("taman", "asuhan", "kanak-kanak", "premis"),
    "campak": ("measles", "penyakit", "berjangkit", "notifikasi", "e-notifikasi"),
    "notifikasi": ("notification", "e-notifikasi", "borang", "notis", "10(2)"),
    "saman": ("summons", "attendance", "magistrate", "111", "34", "35"),
    "pertuduhan": ("charge", "particulars", "duplicity", "152", "153", "163"),
    "diari": ("diary", "investigation", "119"),
    "rakaman": ("statement", "examination", "witness", "112", "113"),
    "waran": ("warrant", "search", "arrest", "54", "56", "57", "62"),
    "geledah": ("search", "warrant", "premises", "54", "56", "62", "63", "64", "65"),
    "tangkap": ("arrest", "seizable", "15", "23", "24", "28", "28a"),
    "tangkapan": ("arrest", "seizable", "15", "23", "28", "28a"),
    "reman": ("remand", "detention", "117", "28"),
    "jamin": ("bail", "bailable", "bond", "387", "388"),
    "pelupusan": ("disposal", "forfeiture", "property", "407", "407a", "413"),
    "ekshibit": ("property", "seized", "disposal", "407", "407a", "413"),
    "penzahiran": ("delivery", "documents", "disclosure", "51a"),
    "juruanalisis": ("chemist", "analyst", "report", "certificate", "399"),
    "oti": ("order", "investigate", "non-seizable", "108"),
    "fir": ("first", "information", "report", "107"),
    "halang": ("obstruct", "obstructing", "public", "servant", "186", "90"),
    "menghalang": ("obstruct", "obstructing", "public", "servant", "186", "90"),
    "halangan": ("obstruct", "obstructing", "public", "servant", "186", "90"),
    "ugut": ("threat", "intimidation", "criminal", "injury", "189", "503", "506"),
    "ugutan": ("threat", "intimidation", "criminal", "injury", "189", "503", "506"),
    "serang": ("assault", "criminal", "force", "public", "servant", "353"),
    "pukul": ("assault", "criminal", "force", "hurt", "353"),
    "kekerasan": ("criminal", "force", "assault", "353"),
    "menyamar": ("personating", "public", "servant", "170"),
    "samar": ("personating", "public", "servant", "170"),
    "palsu": ("forgery", "forged", "false", "information", "document", "465", "468", "471", "177", "182"),
    "pemalsuan": ("forgery", "forged", "document", "genuine", "463", "464", "465", "468", "471"),
    "tipu": ("cheating", "dishonestly", "fraud", "415", "420", "468"),
    "menipu": ("cheating", "dishonestly", "fraud", "415", "420"),
    "fitnah": ("false", "information", "lawful", "power", "182"),
    "penentangan": ("resistance", "taking", "property", "lawful", "authority", "183"),
    "polis": ("police", "duties", "assistance", "sanitary", "quarantine", "20", "24", "90", "344"),
    "pdrm": ("police", "duties", "assistance", "sanitary", "quarantine", "20", "107", "344"),
    "iringan": ("police", "assistance", "duties", "sanitary", "quarantine", "20", "344"),
    "tafsiran": ("interpretation", "construction", "purpose", "computation", "time", "388", "3", "17a", "54"),
    "pemansuhan": ("repeal", "saving", "accrued", "liability", "30", "388"),
    "mansuh": ("repeal", "saving", "liability", "30", "388"),
    "serahan": ("service", "registered", "post", "12", "388", "35"),
    "kelepasan": ("holiday", "weekly", "public", "computation", "time", "54", "388"),
    "majistret": ("magistrate", "first", "class", "second", "jurisdiction", "sentence", "85", "87", "88", "92"),
    "sesyen": ("sessions", "court", "jurisdiction", "sentence", "63", "64", "65", "92"),
    "mahkamah": ("court", "subordinate", "magistrate", "sessions", "jurisdiction", "92"),
    "90a": ("computer", "document", "certificate", "admissibility", "90a"),
    "pembungkusan": ("packaging", "labelling", "amaran", "bergambar", "261/2024", "15(1)"),
}

_MALAY_PREFIXES: Tuple[str, ...] = ("meng", "meny", "mem", "men", "ter", "ber", "per", "pen", "pem", "di", "me", "pe")
_MALAY_SUFFIXES: Tuple[str, ...] = ("kan", "nya", "an", "i")


def _stem_malay_token(tok: str) -> str:
    """Pemangkasan imbuhan Melayu ringan untuk memadankan variasi kata kerja/nama (cth: dipasang -> pasang, mempamerkan -> pamer)."""
    w = tok.lower().strip()
    if len(w) <= 4 or any(ch.isdigit() for ch in w):
        return w
    for pref in _MALAY_PREFIXES:
        if w.startswith(pref) and len(w) - len(pref) >= 4:
            w = w[len(pref):]
            break
    for suf in _MALAY_SUFFIXES:
        if w.endswith(suf) and len(w) - len(suf) >= 4:
            w = w[:-len(suf)]
            break
    return w


def expand_query_for_grounding(question: str) -> Tuple[set[str], set[str]]:
    """Menjana set token tepat (+ kata dasar Melayu) dan set token padanan sinonim dwibahasa PPKP."""
    q_orig_low = (question or "").lower()
    q_low = normalize_ppkp_query(question or "").lower()
    raw_toks = [t.lower() for t in TOKEN_RE.findall(f"{q_orig_low} {q_low}") if len(t) >= 2]
    exact_tokens: set[str] = set()
    expanded_tokens: set[str] = set()

    for t in raw_toks:
        if t in _GROUNDING_STOPWORDS:
            continue
        exact_tokens.add(t)
        stem = _stem_malay_token(t)
        if len(stem) >= 3 and stem not in _GROUNDING_STOPWORDS:
            exact_tokens.add(stem)
        for syn in _PPKP_SYNONYM_MAP.get(t, ()):
            expanded_tokens.add(syn)
        if stem != t:
            for syn in _PPKP_SYNONYM_MAP.get(stem, ()):
                expanded_tokens.add(syn)

    # Frasa berbilang perkataan lazim PPKP (termasuk padanan BM <-> BI bagi Akta 593, 574, 344, 388, 92 & 56)
    phrase_expansions: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
        ("papan tanda", ("tanda", "amaran", "larangan", "merokok", "mempamerkan", "258/2024")),
        ("no smoking", ("tanda", "amaran", "larangan", "merokok", "258/2024")),
        ("tanda larangan", ("tanda", "amaran", "mempamerkan", "kod", "qr", "258/2024", "18(1)")),
        ("tiada tanda", ("gagal", "mempamerkan", "tanda", "amaran", "18(1)", "258/2024")),
        ("tidak pasang tanda", ("gagal", "mempamerkan", "tanda", "amaran", "18(1)", "258/2024")),
        ("tak pasang tanda", ("gagal", "mempamerkan", "tanda", "amaran", "18(1)", "258/2024")),
        ("pintu masuk", ("laluan", "masuk", "mudah", "dilihat", "bangunan")),
        ("bekas abu", ("kelengkapan", "kemudahan", "merokok", "18(1)")),
        ("tamat tempoh", ("tarikh", "akhir", "luput", "14(9)")),
        ("tempat letak kereta", ("bangunan", "kawasan", "terbuka", "257/2024")),
        ("open car park", ("tempat", "letak", "kereta", "awam", "terbuka")),
        ("open air", ("terbuka", "luar", "bangunan")),
        ("kabinet bertutup", ("pameran", "tertutup", "legap", "260/2024")),
        ("benda asing", ("jirim", "asing", "tidak", "layak", "13a")),
        ("bangkai lipas", ("jirim", "asing", "kotor", "tidak", "layak", "13a")),
        ("perintah tutup", ("penutupan", "premis", "ingkar")),
        ("tutup premis", ("penutupan", "premis", "perintah")),
        ("ingkar perintah", ("mematuhi", "perintah", "arahan", "disobedience", "188")),
        ("tidak pakai apron", ("pakaian", "pengendali", "makanan", "32(1)")),
        ("tak pakai apron", ("pakaian", "pengendali", "makanan", "32(1)")),
        ("penutup kepala", ("pakaian", "pengendali", "makanan", "32(1)")),
        ("rakaman percakapan", ("examination", "witness", "statement", "112", "113", "criminal", "procedure")),
        ("diari siasatan", ("diary", "proceedings", "investigation", "119")),
        ("izin mendakwa", ("consent", "public", "prosecutor", "376", "377")),
        ("laporan polis", ("first", "information", "report", "107", "108", "seizable")),
        ("waran geledah", ("search", "warrant", "54", "56", "57", "62", "64", "65")),
        ("tanpa waran", ("without", "warrant", "search", "arrest", "23", "62", "62a")),
        ("pelupusan barang", ("disposal", "property", "407", "407a", "413")),
        ("barang kes", ("property", "seized", "disposal", "407", "407a", "413")),
        ("penzahiran dokumen", ("delivery", "documents", "51a", "prosecution")),
        ("penjawat awam", ("public", "servant", "21", "186", "189", "353", "170")),
        ("ugutan jenayah", ("criminal", "intimidation", "threat", "503", "506", "189")),
        ("dokumen palsu", ("forgery", "forged", "document", "genuine", "465", "468", "471")),
        ("sijil palsu", ("forgery", "forged", "document", "genuine", "465", "468", "471")),
        ("maklumat palsu", ("false", "information", "public", "servant", "177", "182")),
        ("aduan palsu", ("false", "information", "lawful", "power", "182")),
        ("bantuan polis", ("police", "duties", "assistance", "sanitary", "quarantine", "20", "344")),
        ("iringan polis", ("police", "duties", "assistance", "sanitary", "quarantine", "20", "344")),
        ("hari bersih", ("clear", "days", "computation", "time", "exclusive", "holiday", "54")),
        ("kiraan hari", ("computation", "time", "excluded", "holiday", "days", "54")),
        ("pengiraan", ("computation", "computing", "time", "days", "54")),
        ("cuti umum", ("public", "holiday", "weekly", "excluded", "computation", "time", "54")),
        ("hujung minggu", ("weekly", "holiday", "excluded", "computation", "time", "54")),
        ("had masa", ("computation", "time", "days", "month", "54")),
        ("pos berdaftar", ("service", "registered", "post", "prepaying", "letter", "12")),
        ("serahan pos", ("service", "registered", "post", "document", "12")),
        ("batal perintah", ("revoke", "vary", "amend", "order", "47")),
        ("hukuman berganda", ("punished", "twice", "same", "offence", "59")),
        ("akta tafsiran", ("interpretation", "written", "law", "computation", "service", "purposive", "17a", "30", "54")),
        ("mahkamah majistret", ("magistrate", "first", "class", "criminal", "jurisdiction", "sentences", "85", "87", "88")),
        ("mahkamah sesyen", ("sessions", "court", "criminal", "jurisdiction", "sentences", "63", "64")),
        ("had hukuman", ("jurisdiction", "sentences", "competence", "magistrate", "sessions", "64", "87", "88")),
        ("bidang kuasa mahkamah", ("criminal", "jurisdiction", "sentences", "magistrate", "sessions", "court", "63", "64", "85", "87")),
        ("sijil 90a", ("document", "produced", "computer", "certificate", "90a")),
        ("gambar digital", ("document", "produced", "computer", "certificate", "90a")),
        ("cetakan komputer", ("document", "produced", "computer", "certificate", "90a")),
        ("media sosial", ("publication", "presumption", "fact", "114a", "computer", "90a")),
        ("amaran kesihatan bergambar", ("pembungkusan", "pelabelan", "15(1)", "261/2024")),
        ("e-notifikasi", ("notifikasi", "penyakit", "berjangkit", "10(2)", "borang", "notis")),
        ("klinik swasta", ("pengamal", "perubatan", "notifikasi", "10(2)", "penyakit", "berjangkit")),
    )
    for phrase, syns in phrase_expansions:
        if phrase in q_low:
            expanded_tokens.update(syns)

    expanded_tokens -= exact_tokens
    return exact_tokens, expanded_tokens


_NON_OFFENCE_HEADING_MARKERS: Tuple[str, ...] = (
    "tafsiran",
    "tajuk ringkas",
    "permulaan kuat kuasa",
    "pemakaian",
    "interpretation",
    "short title",
    "commencement",
    "citation and commencement",
)

_NEGATED_ACTIVE_SMOKING_RE = re.compile(
    r"\b(?:tanpa|tiada|tidak|tak|bukan)\s+(?:bukti\s+|saksi\s+(?:mata\s+)?(?:yang\s+)?(?:nampak\s+|melihat\s+)?)?"
    r"(?:orang\s+|individu\s+|sesiapa\s+|pelanggan\s+|pekerja\s+|peniaga\s+|pelajar\s+|murid\s+|budak\s+|obd\s+)?(?:sedang\s+)?"
    r"(?:menghisap|hisap|merokok|mengunyah|menggunakan|guna|membeli|beli)"
    r"(?:\s*(?:,|atau|dan|/)\s*(?:menghisap|hisap|merokok|mengunyah|menggunakan|guna|membeli|beli))*",
    re.I,
)

# Frasa kata nama yang mengandungi perkataan 'merokok' tetapi BUKAN bermaksud seseorang sedang merokok!
_NON_ACTION_SMOKING_PHRASES_RE = re.compile(
    r"\b(?:"
    r"(?:papan\s+)?tanda\s+(?:amaran\s+)?larangan\s+merokok|"
    r"(?:kawasan|tempat|zon|premis|dasar|perintah|akta|peraturan)\s+(?:atau\s+tempat\s+)?larangan\s+merokok|"
    r"larangan\s+merokok\s+(?:dipasang|dipamer|dipamerkan|di\s+dinding|di\s+pintu|di\s+premis)|"
    r"(?:produk|bahan|kemudahan|kelengkapan|bilik|zon)\s+merokok|"
    r"kawalan\s+produk\s+merokok"
    r")\b",
    re.I,
)


def is_non_offence_or_definition_section(sec: Dict[str, Any]) -> bool:
    """Mengenal pasti seksyen tafsiran/tajuk ringkas/bukan kesalahan agar tidak pernah dicalonkan sebagai kesalahan."""
    # Kecualikan Akta Tafsiran 1948 & 1967 [Akta 388] kerana seksyen pemakaian/tafsiran (S.2, S.3, S.66, S.67) ialah isi substantifnya
    if str(sec.get("statute_id") or "").upper() == "AKTA_388":
        return False
    heading_low = str(sec.get("section_heading") or "").strip().lower()
    code_low = str(sec.get("section_code") or "").strip().lower()
    if any(marker in heading_low for marker in _NON_OFFENCE_HEADING_MARKERS):
        return True
    if code_low in ("1", "2", "seksyen 1", "seksyen 2", "section 1", "section 2"):
        if not bool(sec.get("is_offence_provision")):
            return True
    return False


def _strip_negated_active_smoking(text_low: str) -> str:
    cleaned = _NON_ACTION_SMOKING_PHRASES_RE.sub(" ", text_low or "")
    return _NEGATED_ACTIVE_SMOKING_RE.sub(" ", cleaned)


def _has_active_smoking_action(text: str) -> bool:
    """Mengesan sama ada teks benar-benar menggambarkan perbuatan seseorang sedang merokok/menghisap (bukan sekadar menyebut 'tanda larangan merokok')."""
    cleaned = _strip_negated_active_smoking((text or "").lower())
    return bool(
        re.search(
            r"\b(?:"
            r"sedang\s+(?:menghisap|hisap|merokok)|"
            r"(?:menghisap|hisap)\s+(?:vape|pod|rokok|shisha|tembakau|e-?rokok)|"
            r"merokok\s+(?:di|dalam|kat|dekat|tepi|depan|berhampiran)\b|"
            r"(?:pelajar|murid|budak|obd|lelaki|pelanggan|individu|pekerja|orang|pemandu|suspek)\s+(?:\w+\s+){0,3}(?:merokok|hisap|menghisap)|"
            r"(?:dilihat|ditangkap|nampak|tangkap)\s+(?:\w+\s+){0,3}(?:merokok|hisap|menghisap)"
            r")",
            cleaned,
            re.I,
        )
    )


def _has_signage_or_premise_smoking_duty_signal(text: str) -> bool:
    """Mengesan soalan berkaitan kewajipan tuan punya/penghuni premis di bawah Seksyen 18(1) Akta 852 & P.U. (A) 258/2024."""
    q_low = (text or "").lower()
    if re.search(
        r"\b(?:"
        r"(?:papan\s+)?tanda\s+(?:amaran\s+)?larangan\s+merokok|"
        r"tanda\s+amaran|"
        r"tanda\s+larangan|"
        r"signboard\s+(?:larangan|no\s+smoking)|"
        r"no\s+smoking\s+(?:sign|signboard|sticker|tanda)|"
        r"kod\s+qr|"
        r"bekas\s+abu\s+rokok|"
        r"ashtray|"
        r"kemudahan\s+merokok|"
        r"258/2024|"
        r"seksyen\s+18|"
        r"s\.?\s*18\(1\)|"
        r"(?:tiada|tak|tidak|gagal)\s+(?:pasang|pamer|mempamerkan|tampal|ada)\s+(?:papan\s+)?tanda"
        r")\b",
        q_low,
        re.I,
    ):
        return True
    has_owner = bool(
        re.search(r"\b(?:tuan\s+punya|penghuni|pemunya|peniaga|pengusaha|tauke|pemilik|owner)\b", q_low)
    )
    has_duty = bool(
        re.search(r"\b(?:tanda|papan|qr|pasang|dipasang|pamer|dipamer|halang|menghalang|abu\s+rokok)\b", q_low)
    )
    return has_owner and has_duty


def is_passive_vape_possession_question(text: str) -> bool:
    """Mengesan situasi pemilikan pasif vape/rokok oleh pelajar/OBD (beg/checking bag/spotcheck) tanpa bukti menghisap/menggunakan/membeli."""
    q_low = (text or "").lower()
    has_tobacco_vape = any(
        k in q_low
        for k in ("vape", "pod", "rokok", "tembakau", "e-rokok", "17(1)")
    )
    has_minor_or_school = any(
        k in q_low
        for k in (
            "pelajar", "murid", "budak", "obd", "sekolah", "tingkatan",
            "bawah 18", "bawah umur", "kanak-kanak", "guru", "cikgu",
        )
    )
    if not (has_tobacco_vape and has_minor_or_school):
        return False

    has_passive_signal = any(
        k in q_low
        for k in (
            "dalam beg", "checking bag", "check bag", "periksa beg", "pemeriksaan beg",
            "spotcheck", "spot check", "dalam poket", "dalam loker", "rampas dari beg",
            "simpan vape", "simpan rokok", "bawa vape", "bawa rokok",
            "memiliki vape", "memiliki rokok", "miliki vape", "miliki rokok",
            "pemilikan semata", "hanya memiliki", "pemilikan vape", "pemilikan pasif",
            "ada vape dalam", "jumpa vape", "dijumpai vape", "jumpa pod", "dijumpai pod",
            "pegang vape sahaja",
        )
    )
    if not has_passive_signal:
        return False

    # Buang frasa penafian dahulu (cth: "tiada saksi nampak pelajar menghisap atau membeli") sebelum semak bukti aktif
    non_negated = _strip_negated_active_smoking(q_low)
    has_active_use_or_buy = any(
        k in non_negated
        for k in (
            "sedang hisap", "sedang menghisap", "sedang merokok", "dilihat menghisap",
            "nampak hisap", "nampak menghisap", "tangkap pelajar sedang", "ditangkap hisap",
            "ditangkap menghisap", "hisap vape", "menghisap vape", "hisap rokok",
            "menghisap rokok", "sedang menggunakan", "mengunyah",
            "membeli vape", "membeli rokok", "beli vape", "beli rokok",
            "kedai jual", "pekedai jual", "menjual kepada", "jual kepada obd",
        )
    )
    return not has_active_use_or_buy


def infer_domain_statute_ids(question: str, akta_hint: str = "Semua") -> Optional[set[str]]:
    """Penghala domain Akta berketepatan tinggi (v4 — Sokongan Rujukan Silang 3-Lapisan):
    - Mengutamakan prinsip *lex specialis* (Akta KKM 852/281/154/342) dan menyambung akta sokongan/rujukan silang
      (Akta 593 KTJ, Akta 574 Kanun Keseksaan, Akta 344 Polis, Akta 388 Tafsiran 1948 & 1967, Akta 92 Mahkamah Rendah,
      Akta 56 Keterangan, Akta 611 Kanak-Kanak) apabila sesuatu kesalahan/prosedur tiada dalam akta spesifik.
    """
    q_low = (question or "").lower()
    hint = (akta_hint or "").strip()
    hint_low = hint.lower()

    def _has_any(terms: Tuple[str, ...]) -> bool:
        return any(re.search(rf"(?<!\w){re.escape(t)}(?!\w)", q_low) for t in terms)

    has_minor_signal = _has_any((
        "pelajar", "murid", "budak", "sekolah", "obd", "bawah 18", "bawah umur", "kanak-kanak", "remaja",
    ))
    has_evidence_signal = _has_any((
        "90a", "90b", "90c", "114a", "73aa", "akta 56", "akta keterangan", "evidence act",
        "keterangan digital", "cetakan komputer", "gambar digital", "media sosial",
    ))
    has_ktj_signal = _has_any((
        "107", "108", "111", "112", "113", "117", "119", "128", "152", "153", "163", "173",
        "376", "377", "387", "388", "399", "407", "407a", "413", "51a", "28a",
        "ktj", "cpc", "akta 593", "593", "kanun tatacara", "criminal procedure",
        "diari siasatan", "rakaman percakapan", "izin mendakwa", "laporan polis",
        "waran geledah", "tanpa waran", "pelupusan barang", "barang kes", "penzahiran", "reman", "oti", "seizable",
    ))
    has_penal_strong_signal = _has_any((
        "574", "akta 574", "kanun keseksaan", "penal code",
        "170", "177", "182", "183", "186", "188", "189", "269", "270", "272", "273",
        "353", "420", "465", "468", "471", "506",
        "ugut", "mengugut", "ugutan", "serang", "menyerang", "serangan", "pukul", "memukul", "tumbuk",
        "tolak", "ludah", "meludah", "kekerasan", "senjata", "parang", "pisau",
        "menyamar", "penyamaran", "ppkp palsu", "pegawai palsu",
        "palsu", "pemalsuan", "dokumen palsu", "sijil palsu", "maklumat palsu", "aduan palsu",
        "tipu", "menipu", "penipuan", "fitnah", "rampas balik", "rampas semula", "penjawat awam",
    ))
    has_obstruction_generic = _has_any((
        "halang", "menghalang", "halangan", "dihalang", "halang tugas", "kunci pintu",
    ))
    has_police_signal = _has_any((
        "344", "akta 344", "akta polis", "police act", "bantuan polis", "iringan polis",
        "polis bantuan", "iringi operasi", "operasi bersama polis", "halang polis", "pegawai polis",
        "seksyen 20(3)", "20(3)(c)", "seksyen 90", "ocpd", "kpd",
    )) or (_has_any(("polis", "pdrm")) and _has_any(("bantu", "membantu", "bantuan", "iring", "iringan", "operasi", "kuasa polis", "wajib", "halang")))
    has_interp_signal = _has_any((
        "388", "akta 388", "akta tafsiran", "tafsiran 1948", "tafsiran 1967", "interpretation act", "interpretation acts",
        "17a", "hari bersih", "10 hari bersih", "kiraan hari", "tempoh hari", "hari kelepasan", "cuti umum",
        "pos berdaftar", "a.r. berdaftar", "ar berdaftar", "serahan pos",
        "kesan pemansuhan", "pemansuhan akta", "batal perintah", "ubah perintah", "kuasa tersirat",
        "hukuman berganda", "double punishment", "dihukum dua kali", "pertubuhan perbadanan",
        "seksyen 54", "seksyen 30", "seksyen 47", "seksyen 59", "seksyen 12",
    ))
    has_court_signal = _has_any((
        "akta 92", "act 92", "mahkamah rendah", "subordinate courts",
        "mahkamah majistret", "majistret kelas pertama", "majistret kelas kedua",
        "mahkamah sesyen", "bidang kuasa mahkamah", "had hukuman", "kuasa menjatuhkan hukuman",
        "seksyen 63", "seksyen 64", "seksyen 85", "seksyen 87", "seksyen 88",
        "s.63", "s.64", "s.85", "s.87", "s.88",
    )) or bool(re.search(r"\b(?:akta|act)\s*92\b", q_low))

    akta_852_family = {
        "AKTA_852",
        "AKTA_852_PERINTAH_LARANGAN_2024",
        "AKTA_852_PERATURAN_TANDA_2024",
        "AKTA_852_PERATURAN_KOMPAUN_2024",
        "AKTA_852_PERATURAN_JUALAN_2024",
        "AKTA_852_PERATURAN_PEMBUNGKUSAN_2024",
        "AKTA_852_PERATURAN_PENDAFTARAN_2024",
        "AKTA_852_PERATURAN_NOTIS_S47_2024",
    }
    akta_281_core = {"AKTA_281", "AKTA_281_PINDAAN_2024", "PPKM_2009"}
    akta_281_full = {"AKTA_281", "AKTA_281_PINDAAN_2024", "PPKM_2009", "PPM_1985"}
    akta_154_family = {"AKTA_154"}
    akta_342_family = {"AKTA_342", "AKTA_342_PINDAAN_2025", "AKTA_342_PERATURAN_KOMPAUN_2025"}

    def _attach_support_acts(allowed: set[str], *, has_kkm_obstruction_act: bool = False) -> set[str]:
        if has_minor_signal:
            allowed.add("AKTA_611")
        if has_evidence_signal:
            allowed.add("AKTA_56")
        if has_ktj_signal:
            allowed.add("AKTA_593")
        if has_penal_strong_signal or (has_obstruction_generic and not has_kkm_obstruction_act):
            allowed.add("AKTA_574")
            allowed.add("AKTA_593")
        if has_police_signal:
            allowed.add("AKTA_344")
        if has_interp_signal:
            allowed.add("AKTA_388")
        if has_court_signal:
            allowed.add("AKTA_92")
        return allowed

    if hint and hint_low not in ("semua", "all"):
        if "852" in hint_low:
            # Akta 852 tiada seksyen halangan sendiri -> izinkan Akta 574 apabila ada isyarat halang/ugut/serang
            return _attach_support_acts(set(akta_852_family), has_kkm_obstruction_act=False)
        if "ppkm" in hint_low:
            return _attach_support_acts({"PPKM_2009", "AKTA_281", "AKTA_281_PINDAAN_2024"}, has_kkm_obstruction_act=True)
        if "ppm" in hint_low:
            return _attach_support_acts({"PPM_1985", "AKTA_281", "AKTA_281_PINDAAN_2024"}, has_kkm_obstruction_act=True)
        if "281" in hint_low or "makanan" in hint_low:
            return _attach_support_acts(set(akta_281_full), has_kkm_obstruction_act=True)
        if "154" in hint_low:
            return _attach_support_acts(set(akta_154_family), has_kkm_obstruction_act=True)
        if "342" in hint_low or "apppb" in hint_low:
            return _attach_support_acts(set(akta_342_family), has_kkm_obstruction_act=True)
        if "574" in hint_low or "kanun keseksaan" in hint_low or "penal" in hint_low:
            return _attach_support_acts({"AKTA_574"}, has_kkm_obstruction_act=False)
        if "344" in hint_low or "polis" in hint_low or "police" in hint_low:
            return _attach_support_acts({"AKTA_344"}, has_kkm_obstruction_act=False)
        if "388" in hint_low or "tafsiran" in hint_low or "interpretation" in hint_low:
            return _attach_support_acts({"AKTA_388"}, has_kkm_obstruction_act=False)
        if re.search(r"\b92\b", hint_low) or "mahkamah rendah" in hint_low or "subordinate" in hint_low:
            return _attach_support_acts({"AKTA_92"}, has_kkm_obstruction_act=False)
        if "611" in hint_low:
            return _attach_support_acts({"AKTA_611"}, has_kkm_obstruction_act=False)
        if "593" in hint_low or "ktj" in hint_low or "cpc" in hint_low or "tatacara" in hint_low:
            return _attach_support_acts({"AKTA_593"}, has_kkm_obstruction_act=False)
        if re.search(r"\b56\b", hint_low) or "keterangan" in hint_low:
            return _attach_support_acts({"AKTA_56"}, has_kkm_obstruction_act=False)
        return {hint.upper()}

    has_tobacco_explicit = _has_any((
        "vape", "rokok", "e-rokok", "e-cigarette", "pod", "shisha", "tembakau",
        "nikotin", "nicotine", "merokok", "no smoking", "smoking", "hisap", "menghisap",
        "ashtray", "bekas abu", "tanda larangan", "tanda amaran", "papan tanda",
        "kod qr", "obd", "ppkht", "852", "amaran kesihatan bergambar", "pembungkusan rokok",
        "pelabelan rokok", "pembungkusan vape",
        "257/2024", "258/2024", "259/2024", "260/2024", "261/2024", "262/2024", "264/2024",
    )) or bool(re.search(r"\b(?:17\(1\)|16\(2\)|16\(3\))(?=\W|$)", q_low))

    has_food_strong = _has_any((
        "makanan", "tifoid", "typhoid", "antitifoid", "lpm", "slpm",
        "kursus pengendali", "fosim", "najis tikus", "tikus",
        "lipas", "lalat", "lilati", "apron", "penutup kepala", "benda asing",
        "diaduk", "luput", "expired", "tamat tempoh", "tarikh akhir",
        "ppkm", "ppm", "mja", "pengendali makanan",
        "13a", "13b", "281", "a1702", "mee goreng", "nasi", "kicap", "sardin",
    )) or (
        _has_any(("keracunan", "kotor", "suntikan", "perintah tutup", "tutup premis"))
        and not _has_any(("342", "apppb", "18(1)(d)", "18(1)(f)", "18(1)(c)", "hfmd", "taska", "tadika", "wabak"))
    )
    has_food_venue_only = _has_any((
        "restoran", "kedai makan", "dapur", "gerai", "warung", "kantin",
        "cafetaria", "kafeteria", "cafe", "kafe", "kopitiam", "pasar mini", "pasaraya",
    ))
    has_ppm_signal = _has_any((
        "ppm", "1985", "luput", "expired", "tamat tempoh", "tarikh akhir",
        "best before", "ketahanan minimum", "label", "pelabelan", "tin", "bungkusan",
        "bahan tambah", "komposisi", "standard makanan", "14(9)", "14(7)",
    ))
    has_notification_signal = _has_any((
        "e-notifikasi", "enotifikasi", "notifikasi", "borang notis", "klinik swasta",
        "pengamal perubatan", "doktor swasta", "hospital swasta", "lapor kes", "gagal lapor",
    ))
    has_vector_field_signal = _has_any((
        "aedes", "jentik", "jentik-jentik", "larva", "pupa", "nyamuk",
        "takungan", "fogging", "semburan kabus", "entomologi", "vektor",
        "tapak bina", "tapak pembinaan", "154",
    ))
    has_aedes = has_vector_field_signal or (_has_any(("denggi",)) and not has_notification_signal)
    has_cdc = _has_any((
        "covid", "tibi", "tb", "tuberkulosis", "ptb", "afb", "tbis", "dots",
        "hfmd", "taska", "tadika", "leptospirosis", "kencing tikus", "measles", "campak",
        "wabak", "hso", "kuarantin", "pengasingan", "unit cdc", "penyakit berjangkit",
        "342", "a1742", "139/2025", "18(1)(d)", "18(1)(f)", "18(1)(c)", "18(1)(e)",
    )) or has_notification_signal

    # Subseksyen generik (18(1), 15(1), 13(1), 10(1)) hanya mencetuskan Akta 852 jika TIADA isyarat dominan Akta 281/154/342
    has_tobacco = has_tobacco_explicit or (
        bool(re.search(r"\b(?:18\(1\)|10\(1\)|13\(1\)|15\(1\))(?=\W|$)", q_low))
        and not (has_cdc or has_aedes or has_food_strong)
    )

    # Jika soalan jelas tentang Akta 342 (cth: S.18(1)(d) keracunan makanan / HFMD) tanpa menyebut Akta 281/PPKM/PPM/S.11,
    # kekalkan Akta 342 sahaja agar tidak tercemar oleh Akta 281.
    has_food = has_food_strong or (has_food_venue_only and not has_tobacco and not has_cdc)
    if has_cdc and not _has_any(("281", "ppkm", "ppm", "tifoid", "slpm", "lipas", "luput", "expired", "seksyen 11", "s.11", "a1702")):
        if _has_any(("342", "apppb", "18(1)(d)", "18(1)(f)", "18(1)(c)", "hfmd", "taska", "tadika", "tibi", "covid")):
            has_food = False
        elif not has_food_venue_only and not _has_any(("makanan", "restoran")):
            has_food = False

    locked: set[str] = set()
    if has_tobacco:
        locked |= akta_852_family
    if has_food:
        locked |= akta_281_full if has_ppm_signal else akta_281_core
    if has_aedes:
        locked |= akta_154_family
    if has_cdc:
        locked |= akta_342_family

    has_kkm_obstruction_act = has_food or has_aedes or has_cdc
    if locked:
        return _attach_support_acts(locked, has_kkm_obstruction_act=has_kkm_obstruction_act)
    # Jangan sekali-kali kunci secara eksklusif kepada Akta 611 semata-mata jika tiada akta teras/sokongan lain dikesan!
    if (
        has_evidence_signal
        or has_ktj_signal
        or has_penal_strong_signal
        or has_obstruction_generic
        or has_police_signal
        or has_interp_signal
        or has_court_signal
        or _has_any(("akta 611", "kanak-kanak 2001"))
    ):
        return _attach_support_acts(set(), has_kkm_obstruction_act=False)
    return None


def evaluate_offence_elements_against_facts(
    question_or_facts: str,
    offence: Dict[str, Any],
) -> Dict[str, Any]:
    """Menilai setiap mandatory_elements & explicit_exclusions_and_traps terhadap fakta kes/soalan.

    Prinsip ketat:
    - Unsur yang tiada bukti eksplisit dalam soalan WAJIB berstatus `PERLU BUKTI TAMBAHAN` atau `TIDAK TERPENUHI`
      (JANGAN sesekali menetapkan lalai kepada `TERPENUHI`).
    - Apabila perangkap pengecualian tercetus (`action_blocked = True`), tiada unsur bertanda hijau palsu `TERPENUHI`
      yang bercanggah dengan keputusan utama `TIADA_KESALAHAN`.
    """
    q_low = (question_or_facts or "").lower()
    non_negated_q = _strip_negated_active_smoking(q_low)
    off_id = str(offence.get("offence_id") or "")
    evaluations: List[Dict[str, Any]] = []
    trap_triggered: Optional[str] = None
    blocked_action = False

    # 1. Perangkap Khusus #1: Akta 852 Seksyen 17(1) / 13(3) — Pemilikan pasif vape/rokok oleh pelajar/OBD tanpa bukti menghisap/menggunakan/membeli
    is_passive_possession_trap = is_passive_vape_possession_question(q_low)

    # 2. Perangkap Khusus #2: Akta 342 Seksyen 22(b) — Kes COVID-19 datang kerja pasca 15 Julai 2024 tanpa perintah bertulis S.15(1)/S.14
    is_covid_no_order_trap = bool(
        "covid" in q_low
        and any(k in q_low for k in ("datang kerja", "datng kerja", "hadir bekerja", "masuk kerja", "unit cdc"))
        and not any(k in q_low for k in ("ingkar perintah bertulis seksyen 15", "telah diserahkan perintah seksyen 15"))
    )

    # 3. Perangkap Khusus #3: Akta 342 Seksyen 22(b) — Kes PTB Smear Negatif (AFB Negatif) / saringan belum disahkan aktif
    is_tb_smear_neg_trap = bool(
        any(k in q_low for k in ("smear negatif", "afb negatif", "disaring tibi", "saringan tibi"))
        and any(k in q_low for k in ("enggan mula", "taknak mula", "taknak mulakan", "belum mula"))
    )

    # 4. Perangkap Khusus #4: PPM 1985 P.14(9) — Stok luput diasingkan dalam stor pelupusan khas / bukan untuk dijual
    is_food_disposal_trap = bool(
        any(k in q_low for k in ("luput", "expired", "tamat tempoh"))
        and any(
            k in q_low
            for k in (
                "untuk pelupusan", "tidak untuk dijual", "bukan untuk dijual",
                "stor pelupusan", "diasingkan dalam stor", "tarikh ketahanan minimum", "best before",
            )
        )
        and not any(k in q_low for k in ("di rak jualan", "dijual kepada pelanggan", "dipamer untuk jualan"))
    )

    # 5. Perangkap Khusus #5: Akta 154 S.13(1) — Takungan kosong tiada larva/pupa atau di luar sempadan kawalan pemunya
    is_aedes_no_larva_trap = bool(
        any(k in q_low for k in ("aedes", "takungan", "jentik", "larva", "154"))
        and any(
            k in q_low
            for k in (
                "tiada larva", "tiada jentik", "takungan kosong", "bukan aedes",
                "bukan serangga pembawa", "luar sempadan", "tanah rizab awam", "parit majlis",
            )
        )
    )

    # 6. Perangkap Khusus #6: Akta 852 S.10(1) — Kabinet bertutup legap / senarai harga tertutup (Peraturan 6 P.U.(A) 260/2024)
    is_closed_cabinet_trap = bool(
        re.search(r"\b(?:kabinet\s+bertutup|kabinet\s+legap|almari\s+bertutup|opaque|senarai\s+harga\s+tertutup)\b", q_low, re.I)
        and not re.search(r"\b(?:pamer\s+terbuka|dipamer\s+secara\s+terbuka|kaunter\s+terbuka|rak\s+terbuka)\b", q_low, re.I)
    )

    # 7. Perangkap Khusus #7: Akta 281 S.11 — Masuk premis semata-mata untuk kerja pembersihan semasa tempoh tutup
    is_s11_cleaning_only_trap = bool(
        re.search(r"\b(?:perintah\s+tutup|penutupan\s+premis|seksyen\s+11|s\.?\s*11)\b", q_low, re.I)
        and re.search(r"\b(?:pembersihan|mencuci|cuci\s+dapur|kemas\s+dapur|bersih(?:kan)?\s+premis)\b", q_low, re.I)
        and re.search(r"\b(?:tanpa\s+(?:menjual|jual|operasi|beroperasi|pelanggan)|tidak\s+(?:menjual|jual|beroperasi|buka\s+kepada\s+pelanggan)|semata-mata\s+untuk\s+(?:pembersihan|mencuci|membersih))\b", q_low, re.I)
    )

    # 8. Perangkap Khusus #8: PPKM 2009 P.30/P.31 — Juruwang / staf pejabat bukan pengendali makanan
    is_non_food_handler_trap = bool(
        re.search(r"\b(?:juruwang|cashier|kerani|akauntan|pengawal\s+keselamatan|penghantar\s+stok\s+luar)\b", q_low, re.I)
        and re.search(r"\b(?:tidak\s+(?:menyentuh|sentuh|mengendali|kendali|memasak|masak|menghidang)|bukan\s+pengendali\s+makanan|kaunter\s+bayaran\s+sahaja|hanya\s+jaga\s+kaunter)\b", q_low, re.I)
    )

    # 9. Perangkap Khusus #9: Akta 154 S.21 — Pintu/pagar berkunci tanpa penghuni di dalam rumah
    is_locked_empty_gate_trap = bool(
        re.search(r"\b(?:pagar\s+berkunci|pintu\s+berkunci|rumah\s+berkunci|premis\s+berkunci|bermangga)\b", q_low, re.I)
        and re.search(r"\b(?:tiada\s+penghuni|tiada\s+orang|kosong|tidak\s+berpenghuni|penghuni\s+tiada|keluar\s+bekerja)\b", q_low, re.I)
        and not re.search(r"\b(?:halau|mengugut|ugut|gertak|enggan\s+buka\s+walaupun\s+ada\s+di\s+dalam|marah\s+pegawai)\b", q_low, re.I)
    )

    # 10. Perangkap Khusus #10: Akta 342 S.12(4) — Pengecualian keluar untuk rawatan perubatan mengikut arahan
    is_medical_travel_s12_4_trap = bool(
        re.search(r"\b(?:rawatan\s+perubatan|ke\s+klinik|ke\s+hospital|mendapatkan\s+rawatan|janji\s+temu\s+doktor)\b", q_low, re.I)
        and re.search(r"\b(?:seksyen\s+12|12\(1\)|12\(4\)|penyakit\s+berjangkit|tibi|covid|campak|hfmd|positif)\b", q_low, re.I)
        and not re.search(r"\b(?:bersiar-siar|membeli-belah|kedai\s+makan|restoran|kenduri|berkumpul)\b", q_low, re.I)
    )

    # Semak sama ada kesalahan ini disekat oleh mana-mana perangkap sebelum menilai unsur individu
    if off_id == "AKTA_852_S17_1" and is_passive_possession_trap:
        blocked_action = True
        trap_triggered = (
            offence.get("explicit_exclusions_and_traps")
            or [
                "Seksyen 17(1) Akta 852 hanya terpakai bagi perbuatan merokok, mengunyah atau menggunakan — pemilikan dalam beg semata-mata BUKAN kesalahan."
            ]
        )[0]
    elif off_id == "AKTA_852_S13_3" and is_passive_possession_trap:
        blocked_action = True
        trap_triggered = "Tiada bukti transaksi pembelian oleh OBD dalam fakta soalan — Seksyen 13(3) tidak boleh dikenakan tanpa bukti pembelian."
    elif off_id == "AKTA_852_S10_1" and is_closed_cabinet_trap:
        blocked_action = True
        trap_triggered = "Penyimpanan produk merokok di dalam kabinet bertutup legap (tanpa pameran terbuka) mematuhi Peraturan 6 P.U. (A) 260/2024 dan BUKAN kesalahan Seksyen 10(1) Akta 852."
    elif off_id == "AKTA_281_S11_2" and is_s11_cleaning_only_trap:
        blocked_action = True
        trap_triggered = "Pemilik/pekerja memasuki premis semata-mata untuk menjalankan kerja pembersihan tanpa menjual atau menyediakan makanan kepada pelanggan BUKAN kesalahan mengingkari Perintah Penutupan Seksyen 11 Akta 281."
    elif off_id in ("PPKM_2009_P30_1", "PPKM_2009_P31_1") and is_non_food_handler_trap:
        blocked_action = True
        trap_triggered = "Individu yang hanya menjaga kaunter bayaran (juruwang) atau tidak menyentuh/mengendalikan makanan atau permukaan sentuhan makanan bukan 'pengendali makanan' di bawah Peraturan 30/31 PPKM 2009."
    elif off_id == "AKTA_154_S21" and is_locked_empty_gate_trap:
        blocked_action = True
        trap_triggered = "Premis/pagar berkunci tanpa penghuni di dalam rumah pada waktu lawatan BUKAN kesalahan menghalang pegawai di bawah Seksyen 21 Akta 154."
    elif off_id == "AKTA_342_S12_1" and is_medical_travel_s12_4_trap:
        blocked_action = True
        trap_triggered = "Pengecualian Seksyen 12(4) Akta 342: Individu yang melalui tempat awam bagi maksud mendapatkan rawatan perubatan mengikut arahan pegawai diberi kuasa BUKAN melakukan kesalahan di bawah Seksyen 12(1)."
    elif off_id == "AKTA_342_S22_B" and is_covid_no_order_trap:
        blocked_action = True
        trap_triggered = "Tiada perintah bertulis S.15(1)/S.14 yang diingkari — kompaun S.22(b) tidak boleh dikeluarkan."
    elif off_id == "AKTA_342_S22_B" and is_tb_smear_neg_trap:
        blocked_action = True
        trap_triggered = "Kes PTB Smear Negatif belum memenuhi unsur ingkar perintah sah Seksyen 22(b) Akta 342."
    elif off_id == "PPM_1985_P14_9" and is_food_disposal_trap:
        blocked_action = True
        trap_triggered = "Stok makanan yang telah diasingkan untuk pelupusan (tidak didedahkan untuk jualan) tidak memenuhi unsur pendedahan untuk jualan di bawah Peraturan 14(9) PPM 1985."
    elif off_id == "AKTA_154_S13_1" and is_aedes_no_larva_trap:
        blocked_action = True
        trap_triggered = "Tiada larva/pupa spesies pembawa penyakit yang disahkan atau lokasi di luar kawalan pemunya (S.13(1)/S.22(1) Akta 154) — kompaun S.25 tidak boleh dikeluarkan."

    has_active_smoking_fact = _has_active_smoking_action(q_low)
    has_signage_missing = bool(
        re.search(
            r"\b(?:tiada|tak|tidak|gagal|belum)\s+(?:\w+\s+){0,2}(?:papan\s+)?tanda\b|"
            r"\btanda\s+(?:amaran\s+)?larangan\s+merokok\s+(?:tiada|tidak|tak)\b|"
            r"\b(?:tiada|tak|tidak)\s+(?:tanda\s+larangan|tanda\s+amaran|papan\s+tanda|kod\s+qr)\b|"
            r"\b(?:bekas\s+abu\s+rokok|ashtray)\b",
            q_low,
            re.I,
        )
    )
    has_declared_nonsmoking_venue = bool(
        re.search(
            r"\b(?:restoran|tempat\s+makan|kedai\s+makan|cafetaria|kafeteria|cafe|kafe|kantin|kopitiam|gerai|warung|medan\s+selera|"
            r"universiti|university|kolej|kampus|ipt|ipta|ipts|institusi\s+pendidikan|sekolah|tadika|taska|"
            r"mall|kompleks\s+membeli-belah|pusat\s+beli-belah|pusat\s+membeli-belah|parking\s+bertingkat|parkir\s+bertingkat|"
            r"hospital|klinik|lif|tandas\s+awam|dobi|stesen\s+minyak|lapangan\s+terbang|kenderaan\s+awam|bas\s+sekolah|"
            r"kedai\s+berhawa\s+dingin|bangunan\s+tempat\s+kerja|stadium|perpustakaan|kompleks\s+sukan)\b",
            q_low,
            re.I,
        )
    )

    for el in offence.get("mandatory_elements") or []:
        el_no = int(el.get("element_no") or 1)
        desc = str(el.get("description") or "")
        desc_low = desc.lower()
        must_prove = str(el.get("must_prove") or "")
        status = "PERLU BUKTI TAMBAHAN"
        reason = must_prove or "Perlu dibuktikan di lapangan dengan keterangan saksi, gambar atau dokumen rasmi."

        # Kes disekat (TIADA_KESALAHAN): unsur gagal ditanda TIDAK TERPENUHI, unsur lain TIDAK pernah ditanda hijau TERPENUHI
        if off_id == "AKTA_852_S17_1" and is_passive_possession_trap:
            if el_no == 2 or any(w in desc_low for w in ("merokok", "mengunyah", "menggunakan")):
                status = "TIDAK TERPENUHI"
                reason = (
                    "Tiada bukti pelajar merokok, mengunyah atau menggunakan vape/rokok. "
                    "Pemilikan dalam beg semata-mata BUKAN kesalahan di bawah Seksyen 17(1) Akta 852."
                )
            elif any(w in desc_low for w in ("belum dewasa", "bawah 18", "umur")):
                status = "PERLU BUKTI TAMBAHAN"
                reason = "Pelajar sekolah dinyatakan, namun umur < 18 tahun hanya relevan jika wujud kesalahan aktif dan perlu disahkan melalui MyKad/Kad Pelajar."
            else:
                status = "PERLU BUKTI TAMBAHAN"
                reason = "Peranti vape ditemui dalam beg, namun tanpa perbuatan menghisap/menggunakan ia tidak membentuk kesalahan S.17(1)."
        elif off_id == "AKTA_852_S13_3" and is_passive_possession_trap:
            if any(w in desc_low for w in ("membeli", "beli", "transaksi")):
                status = "TIDAK TERPENUHI"
                reason = "Tiada bukti transaksi pembelian produk merokok oleh pelajar dinyatakan dalam situasi ini."
            else:
                status = "PERLU BUKTI TAMBAHAN"
                reason = "Perlu siasatan sumber pembelian & pengesahan umur (MyKad) sebelum mempertimbangkan S.13(3)."
        elif off_id == "AKTA_342_S22_B" and is_covid_no_order_trap:
            if el_no == 2 or any(w in desc_low for w in ("perintah", "arahan", "notis", "ingkar")):
                status = "TIDAK TERPENUHI"
                reason = (
                    "Tiada Perintah Pengawasan Seksyen 15(1) atau Pengasingan Seksyen 14 Akta 342 bertulis yang diserahkan "
                    "(HSO mandatori MySejahtera telah dimansuhkan sejak 15 Julai 2024)."
                )
            else:
                status = "PERLU BUKTI TAMBAHAN"
                reason = "Perlu semakan e-Notifikasi & penilaian risiko kluster Unit CDC terlebih dahulu."
        elif off_id == "AKTA_342_S22_B" and is_tb_smear_neg_trap:
            if el_no in (1, 2):
                status = "TIDAK TERPENUHI"
                reason = (
                    "Kes PTB Smear Negatif peringkat saringan belum mempunyai pengesahan diagnosis aktif MO/FMS "
                    "(CXR/GeneXpert/Kultur TBIS 20C) dan belum ada Notis Arahan Rawatan bertulis serahan tangan."
                )
            else:
                status = "PERLU BUKTI TAMBAHAN"
                reason = "Perlu laporan pengesahan klinikal MO/FMS dan serahan tangan notis bertulis dahulu."
        elif off_id == "PPM_1985_P14_9" and is_food_disposal_trap:
            if el_no == 1 or any(w in desc_low for w in ("menjual", "jualan", "mendedahkan")):
                status = "TIDAK TERPENUHI"
                reason = "Produk dinyatakan diasingkan dalam stor pelupusan / bukan untuk dijual — unsur mendedahkan untuk jualan tidak dipenuhi."
            else:
                status = "PERLU BUKTI TAMBAHAN"
                reason = "Sahkan sama ada produk dilabel 'tarikh akhir' (use by) atau 'tarikh ketahanan minimum' (best before) serta pastikan ia dilupuskan segera."
        elif off_id == "AKTA_154_S13_1" and is_aedes_no_larva_trap:
            if el_no in (2, 3) or any(w in desc_low for w in ("larva", "spesies", "aedes")):
                status = "TIDAK TERPENUHI"
                reason = "Tiada larva/pupa hidup spesies Aedes disahkan atau takungan berada di luar sempadan kawalan pemunya."
            else:
                status = "PERLU BUKTI TAMBAHAN"
                reason = "Gunakan Perintah Pencegahan Seksyen 8(1) Akta 154 jika wujud potensi pembiakan dalam premis atau rujuk PBT jika tanah rizab awam."
        elif off_id == "AKTA_852_S10_1" and is_closed_cabinet_trap:
            if el_no == 1 or any(w in desc_low for w in ("pamer", "pameran", "terbuka")):
                status = "TIDAK TERPENUHI"
                reason = "Produk disimpan di dalam kabinet bertutup legap (mematuhi Peraturan 6 P.U. (A) 260/2024) — unsur pameran terbuka tidak dipenuhi."
            else:
                status = "PERLU BUKTI TAMBAHAN"
                reason = "Pastikan tiada poster/tanda harga terbuka atau pameran terbuka selain kabinet legap yang dibenarkan."
        elif off_id == "AKTA_281_S11_2" and is_s11_cleaning_only_trap:
            if el_no == 2 or any(w in desc_low for w in ("mengingkari", "operasi", "menjual")):
                status = "TIDAK TERPENUHI"
                reason = "Premis tidak beroperasi atau menjual makanan kepada pelanggan — kemasukan semata-mata untuk pembersihan BUKAN pelanggaran Perintah Penutupan Seksyen 11."
            else:
                status = "PERLU BUKTI TAMBAHAN"
                reason = "Jalankan pemeriksaan semula kebersihan sebelum membenarkan premis dibuka semula."
        elif off_id in ("PPKM_2009_P30_1", "PPKM_2009_P31_1") and is_non_food_handler_trap:
            if el_no == 1 or any(w in desc_low for w in ("pengendali makanan", "menyentuh", "memasak")):
                status = "TIDAK TERPENUHI"
                reason = "Juruwang/staf pejabat yang tidak menyentuh atau mengendalikan makanan atau permukaan sentuhan makanan bukan pengendali makanan di bawah PPKM 2009."
            else:
                status = "PERLU BUKTI TAMBAHAN"
                reason = "Sahkan tugas sebenar pekerja di lapangan — hanya pekerja yang mengendalikan makanan wajib mempunyai SLPM dan suntikan anti-tifoid."
        elif off_id == "AKTA_154_S21" and is_locked_empty_gate_trap:
            if el_no == 2 or any(w in desc_low for w in ("menghalang", "menggalang", "menggertak")):
                status = "TIDAK TERPENUHI"
                reason = "Tiada perbuatan sengaja menghalang atau menggertak pegawai — rumah berkunci kerana tiada penghuni di dalam premis."
            else:
                status = "PERLU BUKTI TAMBAHAN"
                reason = "Rekodkan lawatan dalam Diari Siasatan, tinggalkan notis temujanji / jalankan lawatan ulangan atau guna tatacara kemasukan sah Akta 154."
        elif off_id == "AKTA_342_S12_1" and is_medical_travel_s12_4_trap:
            if el_no == 2 or any(w in desc_low for w in ("tempat awam", "mendedahkan", "risiko")):
                status = "TIDAK TERPENUHI"
                reason = "Dikecualikan di bawah Seksyen 12(4) Akta 342 kerana melalui tempat awam bagi maksud mendapatkan rawatan perubatan mengikut arahan."
            else:
                status = "PERLU BUKTI TAMBAHAN"
                reason = "Sahkan arahan perubatan/rujukan klinik dan pematuhan langkah kawalan jangkitan."
        # --- PENILAIAN KHUSUS MENGIKUT OFFENCE_ID (ELAK PERTEMBUNGAN SUBSTRING SILANG-KESALAHAN) ---
        elif off_id == "AKTA_852_S18_1":
            if el_no == 1:
                if has_declared_nonsmoking_venue and re.search(
                    r"\b(?:tuan\s+punya|penghuni|pemunya|peniaga|pengusaha|tauke|pemilik|owner|kafe|cafe|cafetaria|kafeteria|restoran|kedai)\b",
                    q_low,
                    re.I,
                ):
                    status = "TERPENUHI"
                    reason = (
                        "Premis (tempat makan / kawasan larangan di bawah Jadual Pertama P.U. (A) 257/2024) dan status tuan punya/penghuni "
                        "dinyatakan; sahkan dengan perjanjian sewaan/tender, lesen PBT atau carian SSM."
                    )
                else:
                    status = "PERLU BUKTI TAMBAHAN"
                    reason = must_prove or "Sahkan status tuan punya/penghuni premis (SSM/lesen PBT/perjanjian sewa) dan kategori kawasan larangan P.U. (A) 257/2024."
            else:
                if has_signage_missing:
                    status = "TERPENUHI"
                    reason = (
                        "Ketiadaan tanda amaran larangan merokok mengikut spesifikasi P.U. (A) 258/2024 (atau penyediaan bekas abu rokok) "
                        "dinyatakan; dokumentasikan dengan gambar dinding/laluan masuk premis + Sijil Seksyen 90A(2)."
                    )
                else:
                    status = "PERLU BUKTI TAMBAHAN"
                    reason = must_prove or "Ambil gambar foto membuktikan tiada tanda amaran Kod QR P.U. (A) 258/2024 yang mudah dilihat."
        elif off_id == "AKTA_852_S16_2":
            if el_no == 1:
                if has_active_smoking_fact:
                    status = "TERPENUHI"
                    reason = "Perbuatan merokok/menghisap dinyatakan dalam laporan kes; kukuhkan dengan pemerhatian langsung PPKP/saksi, gambar kejadian & bukti asap/peranti."
                else:
                    status = "TIDAK TERPENUHI" if has_signage_missing else "PERLU BUKTI TAMBAHAN"
                    reason = (
                        "Tiada individu yang sedang merokok dinyatakan dalam situasi ini (soalan merujuk kewajipan premis/tanda larangan, bukan perokok individu)."
                        if has_signage_missing
                        else "Perlu bukti pemerhatian langsung PPKP, saksi mata, foto/CCTV atau pengakuan menunjukkan suspek benar-benar sedang merokok."
                    )
            else:
                if re.search(r"\b(?:tempat\s+letak\s+kereta\s+awam\s+terbuka|open\s+car\s+park|parkir\s+terbuka|parking\s+terbuka)\b", q_low, re.I):
                    status = "TIDAK TERPENUHI"
                    reason = "Tempat letak kereta awam terbuka (cth. R&R Bil. 24 / Taman Awam Bil. 25 atau di luar jarak 3 meter bangunan) dikecualikan daripada kawasan larangan merokok P.U. (A) 257/2024."
                elif re.search(r"\b(?:mall|kompleks|pusat\s+beli|pusat\s+membeli|parking\s+bertingkat|parkir\s+bertingkat|tempat\s+letak\s+kereta\s+bertingkat)\b", q_low, re.I):
                    status = "TERPENUHI"
                    reason = (
                        "Kompleks membeli-belah (Bil. 15 Jadual Pertama P.U. (A) 257/2024) dan keseluruhan kawasan di dalam struktur "
                        "bangunannya — termasuk parkir bertingkat berbumbung / bumbung kekal bersambung atau jarak 3 meter dari garisan bangunan "
                        "(Perenggan 1(b)) — ialah kawasan larangan merokok; sahkan dengan gambar struktur & papan tanda aras parkir mall."
                    )
                elif has_declared_nonsmoking_venue:
                    status = "TERPENUHI"
                    reason = "Lokasi termasuk dalam kawasan/tempat larangan merokok yang diisytiharkan di bawah Jadual Pertama P.U. (A) 257/2024."
                else:
                    status = "PERLU BUKTI TAMBAHAN"
                    reason = "Sahkan lokasi kejadian tersenarai dalam Jadual Pertama P.U. (A) 257/2024 (bukan tempat letak kereta awam terbuka di luar garisan 3 meter bangunan)."
        elif off_id == "AKTA_852_S3_1":
            if re.search(r"\b(?:import|mengimport|kilang|mengilang|edar|mengedar|pengedar|tidak\s+berdaftar|belum\s+daftar)\b", q_low, re.I):
                status = "PERLU BUKTI TAMBAHAN"
                reason = must_prove or "Perlu invois/rekod pengedaran, barang kes disita (S.36) dan surat pengesahan pendaftaran KKM."
            else:
                status = "TIDAK TERPENUHI"
                reason = "Tiada aktiviti mengimport, mengilang atau mengedarkan produk tidak berdaftar dinyatakan dalam situasi ini."
        elif off_id == "AKTA_852_S10_1":
            if el_no == 1 and re.search(r"\b(?:kabinet\s+bertutup|kabinet\s+legap|opaque|senarai\s+harga\s+tertutup)\b", q_low, re.I):
                status = "TIDAK TERPENUHI"
                reason = "Penyimpanan dalam kabinet bertutup legap yang dibuka seketika semasa transaksi dewasa mematuhi Peraturan 6 P.U. (A) 260/2024 dan BUKAN pameran terbuka S.10(1)."
            elif re.search(r"\b(?:pamer|mempamer|mempamerkan|pameran|kaunter\s+terbuka|secara\s+terbuka)\b", q_low, re.I):
                status = "TERPENUHI"
                reason = "Fakta pameran terbuka dinyatakan; ambil gambar sudut jauh & dekat sebelum sitaan S.35/S.36."
            else:
                status = "PERLU BUKTI TAMBAHAN"
                reason = must_prove or "Perlu bukti gambar foto produk dipamerkan secara terbuka di tempat jualan."
        elif off_id == "PPKM_2009_P31_1":
            if re.search(r"\b(?:tiada|belum|tidak|tak|tamat\s+tempoh|luput)\s+(?:\w+\s+){0,3}(?:suntikan|vaksin|tifoid|typhoid|antitifoid)\b", q_low, re.I):
                status = "TERPENUHI"
                reason = "Ketiadaan suntikan anti-tifoid dinyatakan; sahkan rekod suntikan & ambil gambar pekerja sedang mengendali makanan."
            else:
                status = "PERLU BUKTI TAMBAHAN"
                reason = must_prove or "Sahkan kad/rekod vaksinasi anti-tifoid pengendali makanan yang sedang bertugas."
        elif off_id == "PPKM_2009_P30_1":
            if re.search(r"\b(?:tiada|belum|tidak|tak)\s+(?:\w+\s+){0,3}(?:sijil\s+lpm|slpm|latihan\s+pengendali|kursus\s+pengendali)\b", q_low, re.I):
                status = "TERPENUHI"
                reason = "Ketiadaan Sijil Latihan Pengendali Makanan (SLPM) dinyatakan; sahkan dengan senarai pekerja premis."
            else:
                status = "PERLU BUKTI TAMBAHAN"
                reason = must_prove or "Sahkan sijil SLPM yang diiktiraf KKM bagi setiap pengendali makanan."
        else:
            # Penilaian am bersempadan kata (word-boundary) bagi kesalahan lain
            if any(w in desc_low for w in ("belum dewasa", "bawah 18", "bawah umur")):
                if re.search(r"\b(?:bawah\s+18|tingkatan\s+[1-5]|umur\s+1[0-7]|berumur\s+1[0-7]|belum\s+cukup\s+18)\b", q_low, re.I):
                    status = "TERPENUHI"
                    reason = "Status umur bawah 18 tahun (OBD) dinyatakan dalam fakta; pastikan salinan MyKad/Kad Pelajar dilampirkan."
                else:
                    status = "PERLU BUKTI TAMBAHAN"
                    reason = "Umur sebenar (< 18 tahun pada tarikh kejadian) wajib disahkan dengan MyKad atau Kad Pelajar."
            elif any(w in desc_low for w in ("sedang merokok", "mengunyah", "menggunakan produk", "menghisap")):
                if has_active_smoking_fact:
                    status = "TERPENUHI"
                    reason = "Perbuatan merokok/menghisap dinyatakan dalam laporan kes; kukuhkan dengan pemerhatian langsung PPKP/saksi & gambar kejadian."
                else:
                    status = "PERLU BUKTI TAMBAHAN"
                    reason = "Perlu bukti pemerhatian langsung PPKP, saksi mata atau rakaman menunjukkan suspek benar-benar sedang merokok/menggunakan."
            elif any(w in desc_low.replace("membeli-belah", "") for w in ("menjual", "membeli", "transaksi jualan")):
                if re.search(r"\b(?:menjual|jual|membeli|beli|resit|transaksi)\b", q_low.replace("membeli-belah", ""), re.I):
                    status = "TERPENUHI"
                    reason = "Transaksi jualan/belian dinyatakan; lengkapkan resit pembelian, barang kes & percakapan S.112 saksi."
                else:
                    status = "PERLU BUKTI TAMBAHAN"
                    reason = "Perlu bukti transaksi jualan (resit, saksi pembelian atau CCTV kedai)."
            elif any(w in desc_low for w in ("mengiklankan", "iklan", "promosi")):
                if re.search(r"\b(?:iklan|mengiklan|poster|bunting|gegantung|promosi)\b", q_low, re.I):
                    status = "TERPENUHI"
                    reason = "Bahan iklan/promosi dinyatakan; ambil gambar sebelum sitaan atau cetak paparan digital dengan Sijil S.90A."
            elif any(w in desc_low for w in ("tidak bersih", "kotor", "perosak", "tikus", "lipas")) and not off_id.startswith("AKTA_281_S13B"):
                if re.search(r"\b(?:kotor|najis\s+tikus|lipas|lalat|lilati)\b", q_low, re.I) and "kencing tikus" not in q_low:
                    status = "TERPENUHI"
                    reason = "Keadaan premis tidak bersih / perosak dinyatakan; dokumentasikan dengan Borang KMM & foto + Sijil S.90A."
            elif any(w in desc_low for w in ("jentik", "larva", "aedes", "pembiakan")):
                if re.search(r"\b(?:disahkan\s+(?:makmal\s+entomologi|aedes)|keputusan\s+entomologi\s+positif|larva\s+aedes\s+aegypti)\b", q_low, re.I):
                    status = "TERPENUHI"
                    reason = "Pengesahan spesies Aedes dinyatakan; lampirkan Sijil Makmal Entomologi rasmi."
                else:
                    status = "PERLU BUKTI TAMBAHAN"
                    reason = "Penemuan jentik-jentik/takungan wajib disahkan spesies Aedes melalui Sijil Makmal Entomologi sebelum kompaun/pendakwaan."
            elif any(w in desc_low for w in ("perintah", "notis", "s.15", "s.14", "s.8")):
                if re.search(r"\b(?:ingkar\s+perintah|telah\s+diserahkan|notis\s+arahan|perintah\s+tutup)\b", q_low, re.I):
                    status = "PERLU BUKTI TAMBAHAN"
                    reason = "Wajib lampirkan salinan asal notis/perintah bertulis bertandatangan terima & saksi serahan tangan."

        evaluations.append(
            {
                "element_no": el_no,
                "description": desc,
                "must_prove": must_prove,
                "status": status,
                "notes": reason,
            }
        )

    all_sat = (
        not blocked_action
        and bool(evaluations)
        and all(ev["status"] == "TERPENUHI" for ev in evaluations)
    )
    return {
        "offence_id": off_id,
        "offence_section": offence.get("offence_section"),
        "statute_id": offence.get("statute_id"),
        "all_elements_satisfied": all_sat,
        "action_blocked": blocked_action,
        "trap_triggered": trap_triggered,
        "element_evaluations": evaluations,
    }


def extract_legal_citations_from_text(text: str) -> List[Dict[str, str]]:
    """Mengekstrak semua petikan Seksyen, Subseksyen, Perenggan, Peraturan dan Akta daripada teks output AI."""
    if not text:
        return []

    citations: List[Dict[str, str]] = []
    seen: set[str] = set()

    act_ref_pat = (
        r"Akta\s+A?\d+|Act\s+A?\d+|Akta\s+Kerja\s*1955|OSHA\s*1994|PPKM\s*2009|PPM\s*1985|PPKHT\s*2004|"
        r"Akta\s+Makanan(?:\s*1983)?|Food\s+Act(?:\s*1983)?|"
        r"Akta\s+Kawalan\s+Produk\s+Merokok(?:\s+Demi\s+Kesihatan\s+Awam)?(?:\s*2024)?|"
        r"Akta\s+Pemusnahan\s+Serangga\s+Pembawa\s+Penyakit(?:\s*1975)?|APSPP(?:\s*1975)?|"
        r"Akta\s+Pencegahan\s+dan\s+Pengawalan\s+Penyakit\s+Berjangkit(?:\s*1988)?|APPPB(?:\s*1988)?|"
        r"Peraturan-Peraturan\s+Kebersihan\s+Makanan(?:\s*2009)?|"
        r"Peraturan-Peraturan\s+Makanan(?:\s*1985)?|"
        r"Akta\s+Kanak-Kanak(?:\s*2001)?|Child\s+Act(?:\s*2001)?|"
        r"KTJ|CPC|Kanun\s+Keseksaan|Penal\s+Code|Kanun\s+Tatacara\s+Jenayah|"
        r"Akta\s+Polis(?:\s*1967)?|Police\s+Act(?:\s*1967)?|"
        r"Akta\s+Tafsiran(?:\s*1948(?:\s+dan\s+1967)?)?|Interpretation\s+Acts?(?:\s*1948(?:\s+and\s+1967)?)?|"
        r"Akta\s+Mahkamah\s+Rendah(?:\s*1948)?|Subordinate\s+Courts\s+Act(?:\s*1948)?|"
        r"Akta\s+Keterangan(?:\s*1950)?|P\.U\.\s*\(A\)\s*\d+/\d{4}"
    )

    # 1. Pasangan eksplisit & singkatan: "Seksyen X(Y)", "Subseksyen X(Y)", "Perenggan X(Y)(z)", "S.X(Y)", "Sek. X", "Peraturan X", "P.X"
    paired_re = re.compile(
        r"(?<!\w)(Seksyen|Subseksyen|Perenggan|Peraturan|Subperaturan|Section|Regulation|Sek\.|Per\.|S\.|P\.)\s*"
        r"(\d+[A-Za-z]{0,2}(?:\(\d+[A-Za-z]?\))?(?:\([a-z]+\))?)"
        r"(?:\s+(?:dibaca\s+bersama\s+[^,\n.;]{1,40}\s+)?)?"
        rf"(?:\s*(?:di\s+bawah\s+)?({act_ref_pat}))?",
        re.I,
    )
    tail_act_re = re.compile(rf"\b({act_ref_pat})\b", re.I)

    for m in paired_re.finditer(text):
        raw_kind = m.group(1).strip().lower()
        # Elak padanan palsu pada "P.U." atau "B.P.1" atau "K/S"
        if raw_kind in ("s.", "p."):
            prev_ch = text[m.start() - 1] if m.start() > 0 else " "
            if prev_ch in ("/", "-", "."):
                continue
        if raw_kind in ("peraturan", "subperaturan", "regulation", "per.", "p."):
            kind = "Peraturan"
        else:
            kind = "Seksyen"
        num = m.group(2).strip()
        act_raw = (m.group(3) or "").strip()
        inferred_from_tail = False
        # Cuba kesan Akta dalam klausa yang sama sahaja (berhenti pada tanda baca atau petikan Seksyen/Peraturan baharu)
        if not act_raw:
            raw_tail = text[m.end() : m.end() + 90]
            clause_stop = re.search(
                r"[.;\n]|(?<!\w)(?:Seksyen|Subseksyen|Perenggan|Peraturan|Subperaturan|Section|Sek\.|Per\.|S\.|P\.)\s*\d+",
                raw_tail,
                re.I,
            )
            tail = raw_tail[: clause_stop.start()] if clause_stop else raw_tail
            tail_m = tail_act_re.search(tail)
            if tail_m:
                act_raw = tail_m.group(1).strip()
                inferred_from_tail = True
        key = f"{kind.upper()}:{num.upper()}:{act_raw.upper()}"
        if key not in seen:
            seen.add(key)
            citations.append(
                {
                    "kind": kind,
                    "number": num,
                    "base_number": re.findall(r"^\d+[A-Za-z]{0,2}", num)[0].upper(),
                    "act_ref": act_raw,
                    "inferred_from_tail": "1" if inferred_from_tail else "",
                    "raw_citation": m.group(0).strip(),
                    "match_start": str(m.start()),
                    "match_end": str(m.end()),
                }
            )

    return citations


def _build_valid_sections_index(
    sections_list: List[Dict[str, Any]],
    offences_list: List[Dict[str, Any]],
) -> Tuple[Dict[str, set[str]], set[str]]:
    """Membina indeks ketat nombor seksyen/peraturan sah mengikut `statute_id` dan Akta Kanonik (tanpa mengutip tahun/teks badan)."""
    valid_sections_by_act: Dict[str, set[str]] = {}
    all_valid_section_nums: set[str] = set()
    code_num_re = re.compile(r"^(?:Peraturan\s+|Seksyen\s+|Section\s+|Regulation\s+)?(\d+[A-Za-z]{0,2})\b", re.I)
    curated_sec_re = re.compile(r"(?:Seksyen|Peraturan|Section|Regulation|S\.|P\.)\s*(\d+[A-Za-z]{0,2})\b", re.I)

    # Pemetaan akta pindaan kepada akta induknya
    amendment_parent_map = {
        "AKTA_342_PINDAAN_2025": "AKTA_342",
        "AKTA_281_PINDAAN_2024": "AKTA_281",
    }

    for sec in sections_list:
        sid = str(sec.get("statute_id") or "")
        sid_key = sid.upper()
        act_key = canonical_akta_code_for_statute(sid).upper()
        act_set = valid_sections_by_act.setdefault(act_key, set())
        sid_set = valid_sections_by_act.setdefault(sid_key, set())

        m2 = code_num_re.match(str(sec.get("section_code") or "").strip())
        if m2:
            num2 = m2.group(1).upper()
            sid_set.add(num2)
            # Hanya gabungkan seksyen ke indeks Akta Kanonik jika ia akta induk/pindaan (elak 438 peraturan PPM mencemari AKTA_281)
            if sid_key not in REGULATION_STATUTE_IDS:
                act_set.add(num2)
            parent_sid = amendment_parent_map.get(sid_key)
            if parent_sid:
                valid_sections_by_act.setdefault(parent_sid, set()).add(num2)
            all_valid_section_nums.add(num2)

    for off in offences_list:
        sid = str(off.get("statute_id") or "")
        sid_key = sid.upper()
        act_key = canonical_akta_code_for_statute(sid).upper()
        sid_set = valid_sections_by_act.setdefault(sid_key, set())
        act_set = valid_sections_by_act.setdefault(act_key, set())
        # Indeks hanya nombor berawalan Seksyen/Peraturan daripada medan kesalahan & hukuman milik statut itu sendiri
        for field_val in (
            off.get("offence_section", ""),
            off.get("penalty_section", ""),
        ):
            for m_num in curated_sec_re.finditer(str(field_val)):
                num = m_num.group(1).upper()
                sid_set.add(num)
                if sid_key not in REGULATION_STATUTE_IDS:
                    act_set.add(num)
                all_valid_section_nums.add(num)

    # Pastikan seksyen teras yang sah mengikut pindaan terkini sentiasa terindeks bagi akta induk & rujukan silang
    for k_act, extras in (
        ("AKTA_852", {"3", "7", "9", "10", "13", "15", "16", "17", "18", "24", "25", "30", "31", "35", "36", "43", "47", "48", "49", "51"}),
        ("AKTA_281", {"3", "4", "5", "6", "11", "13", "13A", "13B", "13C", "14", "15", "16", "17", "19", "20", "32A", "32B", "33", "33A"}),
        ("AKTA_154", {"4", "5", "8", "13", "20", "21", "22", "22A", "23", "23A", "24", "25"}),
        ("AKTA_342", {"3", "10", "11", "12", "14", "14A", "15", "18", "21A", "22", "22A", "23", "24", "24A", "25"}),
        ("AKTA_56", {"73AA", "90A", "90B", "90C", "114A"}),
        (
            "AKTA_593",
            {
                "15", "20", "23", "24", "28", "28A", "34", "35", "36", "37",
                "51", "51A", "54", "56", "57", "62", "62A", "63", "64", "65",
                "107", "108", "109", "110", "111", "112", "113", "116", "117", "118", "119", "120",
                "128", "133", "152", "153", "154", "163", "164", "165", "173", "173A", "294",
                "376", "377", "380", "387", "388", "399", "407", "407A", "413",
            },
        ),
        (
            "AKTA_574",
            {
                "21", "34", "107", "109", "170", "173", "174", "175", "176", "177", "179",
                "182", "183", "186", "188", "189", "269", "270", "272", "273", "353",
                "415", "420", "463", "464", "465", "468", "471", "503", "506", "511",
            },
        ),
        ("AKTA_344", {"2", "3", "19", "20", "21", "24", "25", "27", "90", "94"}),
        ("AKTA_388", {"2", "3", "12", "17A", "18", "20", "23", "24", "30", "31", "40", "47", "54", "59", "65", "66", "67"}),
        ("AKTA_92", {"2", "3", "59", "63", "64", "65", "76", "78", "82", "85", "87", "88", "89", "90", "92", "93"}),
        ("AKTA_611", {"11", "15", "83", "91"}),
    ):
        valid_sections_by_act.setdefault(k_act, set()).update(extras)
        canon_k = canonical_akta_code_for_statute(k_act).upper()
        valid_sections_by_act.setdefault(canon_k, set()).update(extras)
        all_valid_section_nums.update(extras)

    return valid_sections_by_act, all_valid_section_nums


def validate_legal_output(
    ai_response: Dict[str, Any] | str,
    legal_library: Optional[Dict[str, Any]] = None,
    question_context: str = "",
) -> Dict[str, Any]:
    """FASA 3.3: Pengesah Kod Pasca-Penjanaan Deterministik (`validateLegalOutput`).

    Menyemak:
    1. Setiap petikan Seksyen / Peraturan wujud dalam `statute_sections_verbatim` pada ketepatan statut/peraturan subsidiari dan berstatus `BERKUAT_KUASA`.
    2. Tiada peruntukan dalam `repealed_and_blocked_provisions` dicadangkan sebagai tindakan aktif.
    3. Nilai denda / kompaun serta senarai putih (allowlist) kesalahan boleh kompaun Akta 852 / Akta 342 / Akta 281 / Akta 154 sepadan dengan warta rasmi, serta menghalang kompaun bagi Akta 574 & Akta 344.
    4. Jika unsur mandatori kesalahan berstatus `TIDAK TERPENUHI` berdasarkan `question_context`, sebarang cadangan pertuduhan/kompaun aktif bagi seksyen itu DISEKAT.
    5. Jika akta yang ditanya belum mempunyai sebarang seksyen diindeks (`total_sections_indexed == 0`), pulangkan status `AKTA BELUM DIINDEKS — MUAT NAIK PDF WARTA`.
    """
    if legal_library is None:
        legal_library = get_legal_library().to_snapshot_dict()
    if isinstance(ai_response, str):
        resp_dict: Dict[str, Any] = {
            "keputusan_tindakan": ai_response,
            "alasan_keputusan": ai_response,
            "cadangan_pertuduhan": [],
        }
        combined_text = ai_response
    else:
        resp_dict = ai_response or {}
        charges_txt = " ".join(
            f"{c.get('perihal', '')} {c.get('seksyen_kesalahan', '')} {c.get('seksyen_hukuman', '')} "
            f"{c.get('hukuman_maksimum', '')} {c.get('boleh_kompaun', '')}"
            for c in (resp_dict.get("cadangan_pertuduhan") or [])
            if isinstance(c, dict)
        )
        def _join_str_list(val: Any) -> str:
            if isinstance(val, list):
                return " ".join(str(x or "") for x in val)
            return str(val or "")

        saman_111 = resp_dict.get("saman_111") if isinstance(resp_dict.get("saman_111"), dict) else {}
        izin_mdk = resp_dict.get("izin_mendakwa") if isinstance(resp_dict.get("izin_mendakwa"), dict) else {}
        notis_kmp = resp_dict.get("notis_kompaun") if isinstance(resp_dict.get("notis_kompaun"), dict) else {}
        combined_text = " ".join(
            [
                str(resp_dict.get("akta_disyorkan") or ""),
                str(resp_dict.get("tajuk_nasihat") or ""),
                str(resp_dict.get("ringkasan_eksekutif") or ""),
                str(resp_dict.get("ringkasan_keputusan") or ""),
                str(resp_dict.get("keputusan_tindakan") or ""),
                str(resp_dict.get("alasan_keputusan") or ""),
                str(resp_dict.get("sebab_tidak_menyalahi") or ""),
                _join_str_list(resp_dict.get("langkah_susulan_ppkp")),
                _join_str_list(resp_dict.get("sop_lapangan")),
                _join_str_list(resp_dict.get("eksibit_wajib")),
                str(resp_dict.get("templat_ringkas") or ""),
                str(resp_dict.get("nota_pindaan") or ""),
                str(resp_dict.get("jawapan_4_lapisan_sop") or ""),
                charges_txt,
                str((resp_dict.get("borang_114") or {}).get("akta_dan_seksyen") or ""),
                str((resp_dict.get("borang_114") or {}).get("seksyen_hukuman") or ""),
                str((resp_dict.get("borang_114") or {}).get("teks_pertuduhan") or ""),
                str(saman_111.get("teks_pertuduhan") or ""),
                str(izin_mdk.get("peruntukan_izin") or ""),
                str(izin_mdk.get("seksyen_dipohon") or ""),
                str(notis_kmp.get("peruntukan_undang") or ""),
                str(notis_kmp.get("peruntukan_kompaun") or ""),
                str(resp_dict.get("fakta_kes") or ""),
                str(resp_dict.get("kertas_cadangan_io") or ""),
                str(resp_dict.get("peruntukan_undang") or ""),
            ]
        ).strip()

    statutes_reg: List[Dict[str, Any]] = legal_library.get("statutes_registry") or []
    sections_list: List[Dict[str, Any]] = legal_library.get("statute_sections_verbatim") or []
    offences_list: List[Dict[str, Any]] = legal_library.get("master_offences_matrix") or []
    repealed_list: List[Dict[str, Any]] = legal_library.get("repealed_and_blocked_provisions") or []
    lib_version = str(legal_library.get("statute_library_version") or INITIAL_STATUTE_LIBRARY_VERSION)

    # Indeks teks verbatim mengikut (statute_id, base_number) bagi pengesahan subseksyen (cth: tolak S.11(2) Akta 281, S.16(9) Akta 852, S.5(1) Akta 342)
    sec_text_by_sid_num: Dict[Tuple[str, str], str] = {}
    _sec_code_re = re.compile(r"^(?:Peraturan\s+|Seksyen\s+|Section\s+|Regulation\s+)?(\d+[A-Za-z]{0,2})\b", re.I)
    _amend_parents = {"AKTA_342_PINDAAN_2025": "AKTA_342", "AKTA_281_PINDAAN_2024": "AKTA_281"}
    for _s in sections_list:
        _sid = str(_s.get("statute_id") or "").upper()
        _m = _sec_code_re.match(str(_s.get("section_code") or "").strip())
        if _sid and _m:
            _bn = _m.group(1).upper()
            _txt = str(_s.get("verbatim_text_bm") or "")
            sec_text_by_sid_num[(_sid, _bn)] = (sec_text_by_sid_num.get((_sid, _bn), "") + "\n" + _txt).strip()
            if _sid in _amend_parents:
                _p = _amend_parents[_sid]
                sec_text_by_sid_num[(_p, _bn)] = (sec_text_by_sid_num.get((_p, _bn), "") + "\n" + _txt).strip()

    # Bina atau guna indeks nombor seksyen sah yang telah dicache mengikut statute_id & Akta Kanonik
    cached_idx = legal_library.get("_valid_sections_cache")
    if isinstance(cached_idx, tuple) and len(cached_idx) == 2:
        valid_sections_by_act, all_valid_section_nums = cached_idx
    else:
        valid_sections_by_act, all_valid_section_nums = _build_valid_sections_index(
            sections_list, offences_list
        )

    # Semak sama ada akta yang diminta belum diindeks langsung (total_sections_indexed == 0)
    unindexed_statutes: List[str] = []
    target_act_str = f"{question_context} {resp_dict.get('akta_disyorkan', '')}".strip()
    target_act_low = target_act_str.lower()
    for s in statutes_reg:
        if s.get("status") == "DIMANSUHKAN":
            continue
        sid = str(s.get("statute_id") or "")
        act_num = str(s.get("act_number_or_pu") or "")
        if int(s.get("total_sections_indexed") or 0) == 0:
            sid_hit = bool(sid and re.search(rf"(?<!\w){re.escape(sid.lower())}(?!\w)", target_act_low))
            act_hit = bool(act_num and re.search(rf"(?<!\w){re.escape(act_num.lower())}(?!\w)", target_act_low))
            if sid_hit or act_hit:
                unindexed_statutes.append(f"{sid} ({s.get('official_title_bm', '')})")

    # 1. Semak petikan seksyen/peraturan yang diekstrak
    extracted_citations = extract_legal_citations_from_text(combined_text)
    verified_citations: List[str] = []
    invalid_citations: List[str] = []

    # Akta rujukan silang luaran (tidak diindeks dalam Pustaka Akta) yang sah disebut dalam konteks rujukan agensi.
    # NOTA: AKTA 574 kini DIINDEKS PENUH dalam Pustaka Akta — ia DISAHKAN ketat dan TIDAK lagi dikecualikan!
    cross_agency_acts = {
        "AKTA 171", "AKTA 366", "AKTA 368", "AKTA 290", "AKTA 586", "AKTA 260",
        "AKTA 127", "AKTA 655", "AKTA 265", "AKTA 514", "AKTA 550",
        "AKTA 50", "AKTA 804", "AKTA KERJA 1955", "OSHA 1994",
    }
    akta_disyorkan_up = str(resp_dict.get("akta_disyorkan") or "").upper()
    default_act = canonical_akta_code_for_statute(akta_disyorkan_up).upper()

    # Sokong respons berbilang Akta (guna sempadan kata bagi elak perlanggaran '92'/'56')
    default_lookup_keys: List[str] = []
    for token_re_pat, key_name in (
        (r"\b852\b|PRODUK\s+MEROKOK", "AKTA_852"),
        (r"\bPPKM\b|KEBERSIHAN\s+MAKANAN", "PPKM_2009"),
        (r"\bPPM\b|PERATURAN-PERATURAN\s+MAKANAN", "PPM_1985"),
        (r"\b281\b|AKTA\s+MAKANAN|FOOD\s+ACT", "AKTA_281"),
        (r"\b154\b|\bAPSPP\b|SERANGGA\s+PEMBAWA", "AKTA_154"),
        (r"\b342\b|\bAPPPB\b|PENYAKIT\s+BERJANGKIT", "AKTA_342"),
        (r"\b593\b|\bKTJ\b|\bCPC\b|TATACARA\s+JENAYAH", "AKTA_593"),
        (r"\b574\b|KANUN\s+KESEKSAAN|PENAL\s+CODE", "AKTA_574"),
        (r"\b344\b|AKTA\s+POLIS|POLICE\s+ACT", "AKTA_344"),
        (r"\b388\b|AKTA\s+TAFSIRAN|TAFSIRAN\s+1948|INTERPRETATION\s+ACT", "AKTA_388"),
        (r"\b(?:AKTA|ACT)[\s_]*92\b|MAHKAMAH\s+RENDAH|SUBORDINATE\s+COURTS", "AKTA_92"),
        (r"\b(?:AKTA|ACT)[\s_]*56\b|AKTA\s+KETERANGAN|EVIDENCE\s+ACT", "AKTA_56"),
        (r"\b611\b|KANAK-KANAK", "AKTA_611"),
    ):
        if re.search(token_re_pat, akta_disyorkan_up, re.I) and key_name in valid_sections_by_act and key_name not in default_lookup_keys:
            default_lookup_keys.append(key_name)
    if default_act in valid_sections_by_act and default_act not in default_lookup_keys:
        default_lookup_keys.append(default_act)

    charges_sec_only_check = " ".join(
        f"{c.get('seksyen_kesalahan', '')} {c.get('seksyen_hukuman', '')}"
        for c in (resp_dict.get("cadangan_pertuduhan") or [])
        if isinstance(c, dict)
    ).lower()

    procedural_support_nums = {
        "90A", "90B", "90C", "114", "114A", "73AA",
        "107", "108", "111", "112", "113", "117", "119", "128",
        "152", "153", "154", "163", "172A", "173", "376", "377", "399", "407", "407A", "51A",
        "15", "83", "91",
    }

    pu_to_sid = (
        ("257/2024", "AKTA_852_PERINTAH_LARANGAN_2024"),
        ("258/2024", "AKTA_852_PERATURAN_TANDA_2024"),
        ("259/2024", "AKTA_852_PERATURAN_KOMPAUN_2024"),
        ("260/2024", "AKTA_852_PERATURAN_JUALAN_2024"),
        ("261/2024", "AKTA_852_PERATURAN_PEMBUNGKUSAN_2024"),
        ("262/2024", "AKTA_852_PERATURAN_PENDAFTARAN_2024"),
        ("263/2024", "AKTA_852_PERINTAH_MAKMAL_2024"),
        ("264/2024", "AKTA_852_PERATURAN_NOTIS_S47_2024"),
        ("139/2025", "AKTA_342_PERATURAN_KOMPAUN_2025"),
        ("95/2009", "PPKM_2009"),
        ("437/1985", "PPM_1985"),
    )

    _warn_ctx_words = (
        "dimansuhkan", "digugurkan", "diganti", "mansuh", "berbeza dengan",
        "jangan", "tidak sah", "bukan ", "salah petik", "adalah salah", "ralat cetak", "tiada subseksyen",
        "kod lama", "silap cetak", "sebaliknya",
    )

    def _is_cit_in_warning_context(cit_item: Dict[str, str]) -> bool:
        try:
            ms = int(cit_item.get("match_start") or -1)
            me = int(cit_item.get("match_end") or -1)
        except ValueError:
            return False
        if ms < 0:
            return False
        win = combined_text[max(0, ms - 75) : min(len(combined_text), me + 85)].lower()
        return any(w in win for w in _warn_ctx_words)

    def _subsection_missing_in_keys(cit_num: str, b_num: str, keys: List[str]) -> Optional[str]:
        """Sahkan kewujudan subseksyen `(Y)` dalam teks verbatim seksyen (cth: S.11(2) Akta 281, S.16(9) Akta 852, S.5(1) Akta 342)."""
        sub_m = re.match(r"^\d+[A-Za-z]{0,2}\((\d+[A-Za-z]?)\)", cit_num)
        if not sub_m:
            return None
        sub_code = sub_m.group(1)
        sub_token = f"({sub_code})"
        checked_any_text = False
        for k in keys:
            vtxt = sec_text_by_sid_num.get((k.upper(), b_num.upper()))
            if not vtxt:
                continue
            checked_any_text = True
            if sub_token.lower() in vtxt.lower():
                return None
        if checked_any_text:
            return sub_token
        return None

    for cit in extracted_citations:
        base_num = cit["base_number"].upper()
        act_ref = cit["act_ref"].upper().strip()
        kind = cit["kind"].capitalize()
        inferred_tail = bool(cit.get("inferred_from_tail"))
        raw_cit = cit["raw_citation"]

        if "PPKHT" in act_ref:
            if "ppkht" in charges_sec_only_check or not _is_cit_in_warning_context(cit):
                invalid_citations.append(f"{raw_cit} (PPKHT 2004 telah dimansuhkan oleh Akta 852)")
            continue

        # Jika menyebut Akta 514 untuk Seksyen 22(b) (kesilapan Tibi), gagal
        if act_ref == "AKTA 514" and base_num == "22":
            invalid_citations.append(f"{raw_cit} (Akta 514 ialah OSHA 1994; kes Tibi ialah Seksyen 22(b) Akta 342)")
            continue

        if act_ref in cross_agency_acts:
            verified_citations.append(raw_cit)
            continue

        # Petakan kepada statute_id tepat (termasuk nama penuh BM, peraturan subsidiari & 5 akta rujukan silang)
        explicit_keys: List[str] = []
        for pu_code, mapped_sid in pu_to_sid:
            if pu_code in act_ref and mapped_sid in valid_sections_by_act:
                explicit_keys.append(mapped_sid)
                break
        if not explicit_keys and act_ref:
            if "PPKM" in act_ref or "KEBERSIHAN MAKANAN" in act_ref:
                explicit_keys.append("PPKM_2009")
            elif "PPM" in act_ref or "PERATURAN-PERATURAN MAKANAN" in act_ref:
                explicit_keys.append("PPM_1985")
            elif re.search(r"\b852\b|PRODUK\s+MEROKOK", act_ref):
                explicit_keys.append("AKTA_852")
            elif re.search(r"\b281\b|A1702|AKTA\s+MAKANAN|FOOD\s+ACT", act_ref):
                if kind == "Peraturan":
                    explicit_keys.extend(["PPKM_2009", "PPM_1985"])
                else:
                    explicit_keys.append("AKTA_281")
            elif re.search(r"\b154\b|\bAPSPP\b|SERANGGA\s+PEMBAWA", act_ref):
                explicit_keys.append("AKTA_154")
            elif re.search(r"\b342\b|A1742|APPPB|PENYAKIT\s+BERJANGKIT", act_ref):
                explicit_keys.append("AKTA_342")
            elif re.search(r"\b593\b|\bKTJ\b|\bCPC\b|TATACARA\s+JENAYAH", act_ref):
                explicit_keys.append("AKTA_593")
            elif re.search(r"\b574\b|KANUN\s+KESEKSAAN|PENAL\s+CODE", act_ref):
                explicit_keys.append("AKTA_574")
            elif re.search(r"\b344\b|AKTA\s+POLIS|POLICE\s+ACT", act_ref):
                explicit_keys.append("AKTA_344")
            elif re.search(r"\b388\b|TAFSIRAN|INTERPRETATION", act_ref):
                explicit_keys.append("AKTA_388")
            elif re.search(r"\b(?:AKTA|ACT)[\s_]*92\b|MAHKAMAH\s+RENDAH|SUBORDINATE\s+COURTS", act_ref):
                explicit_keys.append("AKTA_92")
            elif re.search(r"\b(?:AKTA|ACT)[\s_]*56\b|KETERANGAN|EVIDENCE", act_ref):
                explicit_keys.append("AKTA_56")
            elif re.search(r"\b611\b|KANAK-KANAK|CHILD\s+ACT", act_ref):
                explicit_keys.append("AKTA_611")

        valid_explicit_keys = [k for k in explicit_keys if k in valid_sections_by_act]

        if valid_explicit_keys:
            matched_explicit = any(base_num in valid_sections_by_act[k] for k in valid_explicit_keys)
            if matched_explicit:
                # Semak kewujudan subseksyen (cth: S.11(2) Akta 281, S.16(9) Akta 852, Subseksyen 5(1) Akta 342) jika bukan konteks amaran
                missing_sub = (
                    None
                    if (inferred_tail or _is_cit_in_warning_context(cit))
                    else _subsection_missing_in_keys(cit["number"], base_num, valid_explicit_keys)
                )
                if missing_sub:
                    invalid_citations.append(
                        f"{raw_cit} — Subseksyen {missing_sub} TIDAK WUJUD dalam teks verbatim {base_num} ({' / '.join(valid_explicit_keys)})."
                    )
                else:
                    verified_citations.append(raw_cit)
            elif inferred_tail and base_num in procedural_support_nums:
                verified_citations.append(raw_cit)
            elif _is_cit_in_warning_context(cit) and raw_cit.lower() not in charges_sec_only_check:
                verified_citations.append(raw_cit)
            else:
                invalid_citations.append(
                    f"{raw_cit} — Seksyen/Peraturan {cit['number']} TIDAK WUJUD dalam indeks {' / '.join(valid_explicit_keys)}."
                )
        elif default_lookup_keys:
            if kind == "Peraturan" and ("AKTA_281" in default_lookup_keys):
                check_keys = list(dict.fromkeys(default_lookup_keys + ["PPKM_2009", "PPM_1985"]))
            elif kind == "Peraturan" and ("AKTA_852" in default_lookup_keys):
                check_keys = list(dict.fromkeys(default_lookup_keys + [
                    "AKTA_852_PERINTAH_LARANGAN_2024",
                    "AKTA_852_PERATURAN_TANDA_2024",
                    "AKTA_852_PERATURAN_KOMPAUN_2024",
                    "AKTA_852_PERATURAN_JUALAN_2024",
                    "AKTA_852_PERATURAN_PEMBUNGKUSAN_2024",
                    "AKTA_852_PERATURAN_PENDAFTARAN_2024",
                    "AKTA_852_PERATURAN_NOTIS_S47_2024",
                ]))
            else:
                check_keys = default_lookup_keys
            if any(base_num in valid_sections_by_act.get(k, set()) for k in check_keys):
                missing_sub = (
                    None
                    if _is_cit_in_warning_context(cit)
                    else _subsection_missing_in_keys(cit["number"], base_num, check_keys)
                )
                if missing_sub and base_num not in procedural_support_nums:
                    invalid_citations.append(
                        f"{raw_cit} — Subseksyen {missing_sub} TIDAK WUJUD dalam teks verbatim {base_num} ({' / '.join(check_keys)})."
                    )
                else:
                    verified_citations.append(raw_cit)
            elif base_num in procedural_support_nums or (_is_cit_in_warning_context(cit) and raw_cit.lower() not in charges_sec_only_check):
                verified_citations.append(raw_cit)
            else:
                invalid_citations.append(
                    f"{raw_cit} — Seksyen/Peraturan {cit['number']} TIDAK WUJUD dalam indeks {' / '.join(default_lookup_keys)}."
                )
        else:
            if base_num in all_valid_section_nums or base_num in procedural_support_nums:
                verified_citations.append(raw_cit)
            elif _is_cit_in_warning_context(cit):
                verified_citations.append(raw_cit)
            else:
                invalid_citations.append(
                    f"{raw_cit} — Seksyen/Peraturan {cit['number']} TIDAK WUJUD dalam Pustaka Akta."
                )

    # 1B. Pengesah Deterministik Kod SOP KKM 2024 (sekat UIP-PPKHT-* mansuh, kod silap cetak & kod SOP rekaan)
    _deprecated_or_typo_sops = {
        "UIP-UMUM-01-23": "Kod silap cetak — guna kod rasmi UIP-UMUM-01-22 (PINDAAN 2024)",
        "UIP-APPPB-01-20": "Kod silap cetak — guna kod rasmi UIP-APPPB-06-20 (PINDAAN 2024)",
        "UIP-APSPP-03-07": "Kod lama mansuh — guna kod aktif UIP-UMUM-01-24",
    }
    _active_sop_stems: set[str] = set()
    try:
        from backend.services.sop_brain import get_sop_brain as _get_sb

        _active_sop_stems = {str(r.get("file_stem") or "").upper() for r in _get_sb().active_index}
    except Exception:
        _active_sop_stems = set()

    for sop_m in re.finditer(r"\b(UIP-[A-Z]+-\d{2}-\d{2})\b", combined_text, re.I):
        sop_code = sop_m.group(1).upper()
        sop_win = combined_text[max(0, sop_m.start() - 70) : min(len(combined_text), sop_m.end() + 85)].lower()
        in_sop_warn = any(w in sop_win for w in _warn_ctx_words)
        if "PPKHT" in sop_code:
            if not in_sop_warn:
                invalid_citations.append(f"{sop_code} — SOP PPKHT 2004 telah DIMANSUHKAN dan dilarang dipetik.")
        elif sop_code in _deprecated_or_typo_sops:
            if not in_sop_warn:
                invalid_citations.append(f"{sop_code} — {_deprecated_or_typo_sops[sop_code]}.")
        elif _active_sop_stems and sop_code not in _active_sop_stems:
            if not in_sop_warn:
                invalid_citations.append(f"{sop_code} — Kod SOP TIDAK WUJUD dalam indeks 22 SOP KKM Pindaan 2024.")

    # 2. Semak senarai hitam `repealed_and_blocked_provisions`
    repealed_hits: List[Dict[str, str]] = []
    low_combined = combined_text.lower()
    for rep in repealed_list:
        for pat in rep.get("match_patterns") or []:
            m = re.search(pat, low_combined, flags=re.I)
            if not m:
                continue
            window_start = max(0, m.start() - 75)
            window_end = min(len(low_combined), m.end() + 100)
            ctx_window = low_combined[window_start:window_end]
            is_warning_context = any(
                w in ctx_window
                for w in (
                    "dimansuhkan",
                    "digugurkan",
                    "diganti",
                    "mansuh",
                    "terbatal",
                    "dibatalkan",
                    "tamat tempoh",
                    "tidak sah",
                    "jangan",
                    "bukan ",
                    "berbeza dengan",
                    "disekat",
                    "ralat",
                    "salah petik",
                    "adalah salah",
                )
            )
            charges_sec_only = " ".join(
                f"{c.get('seksyen_kesalahan', '')} {c.get('seksyen_hukuman', '')}"
                for c in (resp_dict.get("cadangan_pertuduhan") or [])
                if isinstance(c, dict)
            ).lower()
            in_active_charge = bool(re.search(pat, charges_sec_only, flags=re.I))
            if in_active_charge or not is_warning_context:
                repealed_hits.append(
                    {
                        "provision_id": str(rep.get("provision_id") or ""),
                        "matched_text": m.group(0),
                        "status": str(rep.get("status") or "DIMANSUHKAN"),
                        "replacement_section": str(rep.get("replacement_section") or ""),
                        "warning_message_bm": str(rep.get("warning_message_bm") or ""),
                    }
                )
                break

    # 3. Semak kesepadanan nilai denda & had kompaun dengan `master_offences_matrix` dan Jadual Kompaun Rasmi
    penalty_mismatches: List[str] = []
    # Semak had kompaun Akta 154 (maksimum mutlak RM500) — tangkap "kompaun sebanyak RM 1,500" / "kompaun RM1,500"
    if re.search(r"\bakta\s+154\b", low_combined):
        for comp_m in re.finditer(r"kompaun(?:\s+(?:sebanyak|maksimum|sehingga|berjumlah))?\s+rm\s?([\d,]+(?:\.\d{1,2})?)", low_combined):
            try:
                val = float(comp_m.group(1).replace(",", ""))
                if val > 500.0:
                    ctx_win = low_combined[max(0, comp_m.start() - 55) : min(len(low_combined), comp_m.end() + 55)]
                    is_warn_154 = any(
                        w in ctx_win for w in ("jangan", "bukan ", "salah petik", "adalah salah", "ultra vires", "tidak sah", "dilarang", "melebihi had", "ditolak")
                    )
                    if not is_warn_154:
                        penalty_mismatches.append(
                            f"Had kompaun Seksyen 25 Akta 154 ialah maksimum RM500.00 (nilai RM{val:,.2f} melebihi had undang-undang)."
                        )
            except ValueError:
                pass

    # Semak had kompaun Akta 342 Pindaan Akta A1742 / P.U.(A) 139/2025 (Individu maks RM5,000 / Korporat maks RM50,000)
    if re.search(r"\bakta\s+342\b", low_combined):
        for comp_m in re.finditer(r"kompaun(?:\s+(?:individu|sebanyak|maksimum|sehingga))?\s+rm\s?([\d,]+(?:\.\d{1,2})?)", low_combined):
            try:
                val = float(comp_m.group(1).replace(",", ""))
                ctx_both = low_combined[max(0, comp_m.start() - 65) : min(len(low_combined), comp_m.end() + 55)]
                is_corp_ctx = any(k in ctx_both for k in ("syarikat", "korporat", "pertubuhan perbadanan"))
                limit = 50000.0 if is_corp_ctx else 5000.0
                if val > limit:
                    penalty_mismatches.append(
                        f"Had kompaun Seksyen 25 Akta 342 (Akta A1742) ialah maksimum RM{limit:,.0f} (nilai RM{val:,.2f} melebihi had)."
                    )
            except ValueError:
                pass

    # Semak kesilapan menawarkan kompaun bagi kesalahan TIDAK BOLEH KOMPAUN (termasuk Kanun Keseksaan Akta 574, Akta Polis 344 & S.4(4) Akta 281)
    ak852_compoundable_re = re.compile(r"\b(?:13\(3\)|16\(2\)|17\(1\)|18\(1\))(?=\W|$)", re.I)
    ak342_compoundable_re = re.compile(r"\b(?:10\(2\)|11\(5\)|21a\(3\)|22\([bcd]\))(?=\W|$)", re.I)
    ak281_non_comp_re = re.compile(r"\b(?:seksyen|s\.)\s*(?:4\(4\)|11(?:\(\d+\))?|13(?:\(1\))?|13a(?:\(\d+\))?|13b(?:\(\d+\))?|13c(?:\(\d+\))?|14|15|16|17)(?=\W|$)", re.I)
    ak154_non_comp_re = re.compile(r"\b(?:seksyen|s\.)\s*(?:8\(8\)|20|21)(?=\W|$)", re.I)

    for c in resp_dict.get("cadangan_pertuduhan") or []:
        if not isinstance(c, dict):
            continue
        sec_low = str(c.get("seksyen_kesalahan") or "").lower()
        comp_low = str(c.get("boleh_kompaun") or "").lower()
        claims_compoundable = (
            ("boleh kompaun" in comp_low or "boleh dikompaun" in comp_low)
            and not any(neg in comp_low for neg in ("tidak boleh", "tiada kompaun", "buka ip terus", "rujuk pdrm"))
        )
        if claims_compoundable:
            # Tentukan Akta milik pertuduhan itu sendiri dahulu sebelum jatuh ke default_act
            charge_acts_found = [d for d in ("852", "281", "154", "342", "574", "344") if re.search(rf"\b{d}\b", sec_low)]
            if not charge_acts_found and ("kanun keseksaan" in sec_low or "penal code" in sec_low):
                charge_acts_found.append("574")
            if not charge_acts_found and ("akta polis" in sec_low or "police act" in sec_low):
                charge_acts_found.append("344")
            if not charge_acts_found and ("akta makanan" in sec_low):
                charge_acts_found.append("281")
            eff_charge_acts = charge_acts_found if charge_acts_found else [d for d in ("852", "281", "154", "342", "574", "344") if d in default_act.lower()]
            if "574" in eff_charge_acts or "344" in eff_charge_acts:
                penalty_mismatches.append(
                    f"Kesalahan {c.get('seksyen_kesalahan')} di bawah Kanun Keseksaan [Akta 574] / Akta Polis [Akta 344] TIDAK BOLEH DIKOMPAUN oleh PPKP — wajib rujuk PDRM melalui Laporan Polis Seksyen 107 KTJ."
                )
            elif "852" in eff_charge_acts and re.search(r"\b(?:seksyen|s\.)\s*\d+", sec_low) and not ak852_compoundable_re.search(sec_low):
                penalty_mismatches.append(
                    f"Kesalahan {c.get('seksyen_kesalahan')} TIDAK BOLEH DIKOMPAUN di bawah Jadual Pertama P.U. (A) 259/2024 (hanya S.13(3), S.16(2), S.17(1) & S.18(1) boleh kompaun) — wajib Buka IP Terus."
                )
            elif "342" in eff_charge_acts and re.search(r"\b(?:seksyen|s\.)\s*\d+", sec_low) and not ak342_compoundable_re.search(sec_low):
                penalty_mismatches.append(
                    f"Kesalahan {c.get('seksyen_kesalahan')} TIDAK BOLEH DIKOMPAUN di bawah Jadual Pertama P.U. (A) 139/2025 (hanya S.10(2), S.11(5), S.21A(3), S.22(b)/(c)/(d) boleh kompaun) — wajib Buka IP Terus."
                )
            elif "281" in eff_charge_acts and "peraturan" not in sec_low and ak281_non_comp_re.search(sec_low):
                penalty_mismatches.append(
                    f"Kesalahan {c.get('seksyen_kesalahan')} TIDAK BOLEH DIKOMPAUN di bawah Akta Makanan 1983 — wajib Buka IP Terus."
                )
            elif "154" in eff_charge_acts and ak154_non_comp_re.search(sec_low):
                penalty_mismatches.append(
                    f"Kesalahan {c.get('seksyen_kesalahan')} TIDAK BOLEH DIKOMPAUN di bawah Akta 154 — wajib Buka IP Terus."
                )

    # Semak teks prosa (bukan cadangan_pertuduhan sahaja) jika ada dakwaan mengkompaun Akta 574, Akta 344, atau S.4(4) Akta 281 tanpa kata nafi
    for act_num, act_name in (
        ("574", "Kanun Keseksaan [Akta 574]"),
        ("344", "Akta Polis 1967 [Akta 344]"),
        ("281_4_4", "Seksyen 4(4) Akta Makanan 1983 [Akta 281]"),
    ):
        act_pat = (
            r"\b(?:akta\s+574|kanun\s+keseksaan|penal\s+code)\b"
            if act_num == "574"
            else (
                r"\b(?:akta\s+344|akta\s+polis|police\s+act)\b"
                if act_num == "344"
                else r"\b(?:seksyen|s\.)\s*4\(4\)(?=\W|$)"
            )
        )
        if re.search(act_pat, low_combined):
            for cm in re.finditer(
                r"\b(?:boleh\s+(?:di)?kompaun|tawar(?:kan)?\s+kompaun|menawarkan\s+kompaun|keluarkan\s+kompaun|mengkompaun)\b",
                low_combined,
            ):
                ctx_w = low_combined[max(0, cm.start() - 60) : min(len(low_combined), cm.end() + 80)]
                has_neg = any(
                    n in ctx_w
                    for n in ("tidak boleh", "tiada kompaun", "bukan", "jangan", "dilarang", "tiada kuasa", "bukan kesalahan kompaun")
                )
                near_act = bool(re.search(act_pat, ctx_w)) or (
                    act_num in ("574", "344") and not re.search(r"\bakta\s+(?:852|281|154|342)\b", low_combined)
                )
                if not has_neg and near_act:
                    penalty_mismatches.append(
                        f"Kesalahan di bawah {act_name} TIDAK BOLEH DIKOMPAUN oleh PPKP."
                    )
                    break

    # Semak had denda Seksyen 17(2) Akta 852 (OBD maks RM500) dan Seksyen 16(3) Akta 852 (maks RM5,000, tiada penjara)
    if "17(1)" in low_combined or "17(2)" in low_combined:
        for c in resp_dict.get("cadangan_pertuduhan") or []:
            sec_c = str(c.get("seksyen_kesalahan") or "").lower() if isinstance(c, dict) else ""
            if isinstance(c, dict) and re.search(r"\b17\([12]\)", sec_c) and ("852" in sec_c or "852" in default_act.lower()):
                huk = str(c.get("hukuman_maksimum") or "")
                for rm_m in re.finditer(r"RM\s?([\d,]+)", huk, flags=re.I):
                    val = int(rm_m.group(1).replace(",", ""))
                    if val > 500:
                        penalty_mismatches.append(
                            f"Hukuman denda maksimum Seksyen 17(2) Akta 852 bagi OBD ialah RM500.00 (dipetik RM{val:,})."
                        )
    if "16(3)" in low_combined and ("852" in low_combined or "852" in default_act.lower()):
        for c in resp_dict.get("cadangan_pertuduhan") or []:
            if not isinstance(c, dict):
                continue
            sec_huk = f"{c.get('seksyen_kesalahan', '')} {c.get('seksyen_hukuman', '')}".lower()
            if "16(3)" in sec_huk:
                huk = str(c.get("hukuman_maksimum") or "")
                for rm_m in re.finditer(r"RM\s?([\d,]+)", huk, flags=re.I):
                    val = int(rm_m.group(1).replace(",", ""))
                    if val > 5000:
                        penalty_mismatches.append(
                            f"Hukuman denda maksimum Seksyen 16(3) Akta 852 ialah RM5,000.00 sahaja tanpa penjara (dipetik RM{val:,})."
                        )
        # Semak juga teks prosa terus apabila Seksyen 16(3) Akta 852 disebut bersama denda > RM5,000
        for m16 in re.finditer(r"16\(3\)", low_combined):
            win16 = low_combined[max(0, m16.start() - 60) : min(len(low_combined), m16.end() + 90)]
            if any(w in win16 for w in ("jangan", "bukan ", "salah petik", "adalah salah")):
                continue
            for rm_m in re.finditer(r"denda(?:\s+maksimum)?\s+rm\s?([\d,]+)", win16, flags=re.I):
                val = int(rm_m.group(1).replace(",", ""))
                if val > 5000:
                    penalty_mismatches.append(
                        f"Hukuman denda maksimum Seksyen 16(3) Akta 852 ialah RM5,000.00 sahaja tanpa penjara (dipetik RM{val:,})."
                    )
                    break

    # 4. Semak Unsur Mandatori Kesalahan — nilai perangkap fakta pada `question_context` SAHAJA (supaya nasihat berhati-hati AI tidak mencetuskan perangkap kendiri!)
    element_evaluations: List[Dict[str, Any]] = []
    unfulfilled_element_errors: List[str] = []
    eval_context = question_context.strip() if (question_context or "").strip() else combined_text
    eval_low = eval_context.lower()
    declared_no_offence = str(resp_dict.get("status_kesalahan") or "").upper() == "TIADA_KESALAHAN"
    keputusan_low = str(resp_dict.get("keputusan_tindakan") or "").lower()
    keputusan_is_rejection = any(
        neg in keputusan_low
        for neg in ("tiada kesalahan", "tidak boleh", "ditolak", "bukan kesalahan", "unsur tidak terpenuhi", "unsur tidak dipenuhi", "jangan keluarkan", "belum")
    )

    trap_charge_patterns: Dict[str, Tuple[str, str]] = {
        "AKTA_852_S17_1": ("852", r"\b17\(1\)"),
        "AKTA_852_S13_3": ("852", r"\b13\(3\)"),
        "AKTA_852_S10_1": ("852", r"\b10\(1\)"),
        "AKTA_281_S11_2": ("281", r"\bseksyen\s+11\b|\bs\.?\s*11\b"),
        "PPKM_2009_P30_1": ("2009", r"\b30\(1\)"),
        "PPKM_2009_P31_1": ("2009", r"\b31\(1\)"),
        "AKTA_154_S21": ("154", r"\b(?:seksyen|s\.)\s*21\b"),
        "AKTA_342_S12_1": ("342", r"\b12\(1\)"),
        "AKTA_342_S22_B": ("342", r"\b22\(b\)"),
        "PPM_1985_P14_9": ("1985", r"\b14\(9\)"),
        "AKTA_154_S13_1": ("154", r"\b13\(1\)"),
    }

    for off in offences_list:
        off_id = str(off.get("offence_id") or "")
        should_eval = False
        if off_id == "AKTA_852_S17_1" and (
            is_passive_vape_possession_question(eval_context)
            or ("17(1)" in low_combined and "pelajar" in eval_low and "vape" in eval_low)
        ):
            should_eval = True
        elif off_id == "AKTA_852_S13_3" and ("13(3)" in low_combined and is_passive_vape_possession_question(eval_context)):
            should_eval = True
        elif off_id == "AKTA_852_S10_1" and any(k in eval_low for k in ("kabinet bertutup", "kabinet legap", "opaque", "senarai harga tertutup")):
            should_eval = True
        elif off_id == "AKTA_281_S11_2" and ("pembersihan" in eval_low or "mencuci" in eval_low) and ("tutup" in eval_low or "seksyen 11" in eval_low):
            should_eval = True
        elif off_id in ("PPKM_2009_P30_1", "PPKM_2009_P31_1") and any(k in eval_low for k in ("juruwang", "cashier", "bukan pengendali")):
            should_eval = True
        elif off_id == "AKTA_154_S21" and any(k in eval_low for k in ("pagar berkunci", "pintu berkunci", "rumah berkunci", "bermangga")):
            should_eval = True
        elif off_id == "AKTA_342_S12_1" and any(k in eval_low for k in ("rawatan perubatan", "ke klinik", "ke hospital")):
            should_eval = True
        elif off_id == "AKTA_342_S22_B" and (
            ("covid" in eval_low and "kerja" in eval_low) or "smear negatif" in eval_low
        ):
            should_eval = True
        elif off_id == "PPM_1985_P14_9" and ("untuk pelupusan" in eval_low or "tidak untuk dijual" in eval_low or "bukan untuk dijual" in eval_low):
            should_eval = True
        elif off_id == "AKTA_154_S13_1" and any(k in eval_low for k in ("tiada larva", "tiada jentik", "takungan kosong", "luar sempadan", "bukan aedes")):
            should_eval = True

        if not should_eval:
            continue

        ev = evaluate_offence_elements_against_facts(eval_context, off)
        element_evaluations.append(ev)
        if not ev["action_blocked"]:
            continue

        act_tok, sec_re_pat = trap_charge_patterns.get(off_id, ("", r"$^"))
        active_in_charges = (not declared_no_offence) and any(
            bool(re.search(sec_re_pat, str(c.get("seksyen_kesalahan") or "").lower()))
            and (act_tok in str(c.get("seksyen_kesalahan") or "").lower() or act_tok in default_act.lower() or act_tok == "1985")
            and not any(
                neg in str(c.get("perihal") or "").lower() + " " + str(c.get("boleh_kompaun") or "").lower()
                for neg in ("tiada kesalahan", "bukan kesalahan", "ditolak", "tidak boleh", "fasa ", "jika ", "hanya jika", "sekiranya", "tertakluk")
            )
            for c in (resp_dict.get("cadangan_pertuduhan") or [])
            if isinstance(c, dict)
        )
        actively_charging = active_in_charges or (
            not declared_no_offence
            and not keputusan_is_rejection
            and any(k in keputusan_low for k in ("kompaun", "notis s.47", "tuduh", "buka ip", "s.17(1)"))
        )
        if actively_charging:
            if off_id == "AKTA_852_S17_1":
                unfulfilled_element_errors.append(
                    "UNSUR MANDATORI TIDAK TERPENUHI (Seksyen 17(1) Akta 852): Pelajar memiliki vape di dalam beg tanpa bukti menghisap, "
                    "mengunyah, menggunakan (S.17(1)) atau membeli (S.13(3)) BUKAN kesalahan di bawah Seksyen 17(1) Akta 852. "
                    "Cadangan mengeluarkan Notis S.47 / Kompaun / Pertuduhan S.17(1) WAJIB DITOLAK!"
                )
            else:
                unfulfilled_element_errors.append(
                    f"UNSUR MANDATORI TIDAK DIPENUHI ({off.get('offence_section')}): {ev.get('trap_triggered') or 'Unsur kesalahan tidak dipenuhi berdasarkan fakta kes.'}"
                )

    passed = (
        len(invalid_citations) == 0
        and len(repealed_hits) == 0
        and len(penalty_mismatches) == 0
        and len(unfulfilled_element_errors) == 0
        and len(unindexed_statutes) == 0
    )

    if unindexed_statutes:
        status_code = "AKTA BELUM DIINDEKS — MUAT NAIK PDF WARTA"
        warning_banner = (
            f"AKTA BELUM DIINDEKS — MUAT NAIK PDF WARTA: Peruntukan bagi {', '.join(unindexed_statutes)} "
            "belum dimuat naik ke dalam Pustaka Akta Verbatim. Sistem enggan meneka di luar teks warta rasmi."
        )
    elif not passed:
        status_code = "GAGAL_VALIDASI_PUSTAKA_AKTA"
        reasons = (
            invalid_citations
            + [r["warning_message_bm"] for r in repealed_hits]
            + penalty_mismatches
            + unfulfilled_element_errors
        )
        warning_banner = (
            "Amaran Sistem: Cadangan petikan undang-undang gagal pengesahan Pustaka Akta. "
            + " | ".join(reasons)
        )
    else:
        status_code = "DISAHKAN_VERBATIM_AGC"
        warning_banner = None

    return {
        "passed": passed,
        "status": status_code,
        "statute_library_version": lib_version,
        "extracted_citations": [c["raw_citation"] for c in extracted_citations],
        "verified_citations": verified_citations,
        "invalid_citations": invalid_citations,
        "repealed_hits": repealed_hits,
        "penalty_mismatches": penalty_mismatches,
        "unfulfilled_element_errors": unfulfilled_element_errors,
        "element_evaluations": element_evaluations,
        "unindexed_statutes": unindexed_statutes,
        "warning_banner": warning_banner,
    }


# Alias nama fungsi serasi spesifikasi TypeScript/Python
validateLegalOutput = validate_legal_output


# =====================================================================
# 6. PENGURUS PUSTAKA PERUNDANGAN TERTUTUP 2-LAPISAN (ClosedBookLegalLibrary)
# =====================================================================


class ClosedBookLegalLibrary:
    """Menguruskan 4 koleksi utama Pustaka Akta Verbatim & Daftar Kesalahan Menyeluruh."""

    def __init__(
        self,
        akta_dir: Optional[Path] = None,
        library_dir: Optional[Path] = None,
    ) -> None:
        self.akta_dir = Path(akta_dir or settings.akta_dir)
        self.library_dir = Path(library_dir or (self.akta_dir.parent / "legal_library"))
        self.akta_dir.mkdir(parents=True, exist_ok=True)
        self.library_dir.mkdir(parents=True, exist_ok=True)

        self.statute_library_version: str = INITIAL_STATUTE_LIBRARY_VERSION
        self.statutes_registry: List[Dict[str, Any]] = []
        self.statute_sections_verbatim: List[Dict[str, Any]] = []
        self.master_offences_matrix: List[Dict[str, Any]] = []
        self.repealed_and_blocked_provisions: List[Dict[str, Any]] = []
        self._akta_dir_fingerprint: str = ""
        self._valid_sections_cache: Tuple[Dict[str, set[str]], set[str]] = ({}, set())
        self._section_token_cache: Dict[str, set[str]] = {}

        self._bootstrap_library()

    def _compute_akta_dir_fingerprint(self) -> Tuple[str, Dict[str, str]]:
        """Menghitung cap jari SHA-256 bagi semua fail .pdf/.txt dalam data/akta/."""
        file_hashes: Dict[str, str] = {}
        parts: List[str] = [PARSER_VERSION, str(len(DEFAULT_STATUTES_REGISTRY_META)), str(len(DEFAULT_MASTER_OFFENCES_MATRIX))]
        for path in sorted(self.akta_dir.glob("*")):
            if path.suffix.lower() not in (".txt", ".pdf"):
                continue
            if path.name.upper().startswith("PANDUAN_"):
                continue
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            file_hashes[path.name] = digest
            parts.append(f"{path.name}:{digest}")
        fp = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
        return fp, file_hashes

    def _rebuild_runtime_caches(self) -> None:
        """Menyegarkan cache indeks seksyen sah, token penuh (tanpa pemotongan 2400 aksara) & bobot IDF bagi carian tepat."""
        # Selaraskan entri kurasi autoritatif terkini dalam memori supaya snapshot JSON prahurai sentiasa tepat mengikut warta rasmi
        curated_sync_ids = {
            "AKTA_281_S11_2",
            "AKTA_281_S13_1",
            "AKTA_281_S13A_2",
            "AKTA_281_S13B_1",
            "PPKM_2009_P11_1",
            "PPKM_2009_P31_1",
            "PPM_1985_P14_9",
            "AKTA_154_S21",
        }
        curated_by_id = {
            str(item.get("offence_id")): item
            for item in DEFAULT_MASTER_OFFENCES_MATRIX
            if str(item.get("offence_id")) in curated_sync_ids
        }
        existing_oids: set[str] = set()
        for off in self.master_offences_matrix:
            oid = str(off.get("offence_id") or "")
            existing_oids.add(oid)
            if oid in curated_by_id:
                src = curated_by_id[oid]
                for sync_k in (
                    "offence_section",
                    "read_together_with",
                    "offence_title",
                    "mandatory_elements",
                    "explicit_exclusions_and_traps",
                    "penalty_section",
                    "penalty_first_offence",
                    "penalty_subsequent_offence",
                    "compound_info",
                    "special_legal_requirements",
                    "mandatory_exhibits",
                    "charge_sheet_template_bm",
                ):
                    off[sync_k] = json.loads(json.dumps(src[sync_k]))
            elif oid == "AKTA_281_13A":
                off["compound_info"] = {
                    "is_compoundable": False,
                    "compound_authority_section": None,
                    "compound_regulation_ref": None,
                    "compound_amount_or_limit": "TIDAK BOLEH DIKOMPAUN — Wajib Buka IP Terus & Izin Mendakwa TPR Seksyen 32A",
                    "max_compound_rm": None,
                    "payment_days": None,
                    "notice_section": None,
                }
            elif oid == "AKTA_342_PINDAAN_2025_21A":
                off["compound_info"] = {
                    "is_compoundable": True,
                    "compound_authority_section": "Seksyen 25 Akta 342 (Pindaan Akta A1742)",
                    "compound_regulation_ref": "Jadual Pertama P.U. (A) 139/2025",
                    "compound_amount_or_limit": "Hanya Seksyen 21A(3) boleh dikompaun dengan keizinan bertulis Pendakwa Raya (maks RM5,000 individu / RM50,000 perbadanan — tempoh 14 hari)",
                    "max_compound_rm": 5000,
                    "payment_days": 14,
                    "notice_section": "Seksyen 25 Akta 342 [P.U. (A) 139/2025]",
                }
            elif oid == "AKTA_852_PERATURAN_TANDA_2024_PERATURAN_2":
                # Baiki percanggahan entri auto-sweep Peraturan 2 P.U. (A) 258/2024 dalam memori:
                # P.U. (A) 258/2024 dibaca bersama Seksyen 18(1)(a) Akta 852 yang BOLEH DIKOMPAUN di bawah S.48(2) & P.U. (A) 259/2024.
                off["read_together_with"] = [
                    "Seksyen 18(1)(a) & Seksyen 18(2) Akta 852",
                    "Perintah Kawalan Produk Merokok Demi Kesihatan Awam (Pengisytiharan Kawasan atau Tempat Larangan Merokok) 2024 [P.U. (A) 257/2024]",
                ]
                off["compound_info"] = {
                    "is_compoundable": True,
                    "compound_authority_section": "Seksyen 48(2) Akta 852",
                    "compound_regulation_ref": "Jadual Pertama(d) P.U. (A) 259/2024",
                    "compound_amount_or_limit": (
                        "Boleh dikompaun di bawah Seksyen 18(1)(a) & Seksyen 48(2) Akta 852 "
                        "(RM250.00 – RM2,500.00; tempoh bayaran 30 hari — pertuduhan/kompaun wajib dibuat di bawah Seksyen 18(1)(a) Akta 852 dibaca bersama Peraturan 2 P.U. (A) 258/2024)"
                    ),
                    "max_compound_rm": 2500,
                    "payment_days": 30,
                    "notice_section": "Tawaran Kompaun Borang 2 P.U.(A) 259/2024 & Notis Hadir Mahkamah S.47 [P.U.(A) 264/2024]",
                }
            elif oid == "AKTA_852_S18_1":
                sids_18 = list(off.get("source_section_doc_ids") or [])
                for extra_18 in (
                    "AKTA_852_PERATURAN_TANDA_2024__JADUAL_PERTAMA",
                    "AKTA_852_PERINTAH_LARANGAN_2024__JADUAL_PERTAMA",
                    "AKTA_852_PERINTAH_LARANGAN_2024__P2",
                ):
                    if extra_18 not in sids_18:
                        sids_18.append(extra_18)
                off["source_section_doc_ids"] = sids_18

        if "AKTA_281_S13A_2" not in existing_oids and "AKTA_281_S13A_2" in curated_by_id:
            self.master_offences_matrix.append(json.loads(json.dumps(curated_by_id["AKTA_281_S13A_2"])))

        self._valid_sections_cache = _build_valid_sections_index(
            self.statute_sections_verbatim,
            self.master_offences_matrix,
        )

        # Indeks PENUH teks verbatim (bukan [:2400]!) + kata dasar Melayu supaya Bil. 9-28 Jadual Pertama P.U. (A) 257/2024 dapat dicari
        sec_map: Dict[str, Dict[str, Any]] = {}
        tok_cache: Dict[str, set[str]] = {}
        sec_df: Dict[str, int] = {}
        for sec in self.statute_sections_verbatim:
            did = str(sec.get("doc_id") or "")
            sec_map[did] = sec
            raw = f"{sec.get('section_code', '')} {sec.get('section_heading', '')} {str(sec.get('verbatim_text_bm', ''))}".lower()
            toks: set[str] = set()
            for t in TOKEN_RE.findall(raw):
                if len(t) >= 2 and t not in _GROUNDING_STOPWORDS:
                    toks.add(t)
                    st = _stem_malay_token(t)
                    if len(st) >= 3 and st not in _GROUNDING_STOPWORDS:
                        toks.add(st)
            tok_cache[did] = toks
            for tk in toks:
                sec_df[tk] = sec_df.get(tk, 0) + 1
        n_secs = max(1, len(self.statute_sections_verbatim))
        self._section_token_cache = tok_cache
        self._section_idf = {
            tk: math.log(1.0 + (n_secs - df + 0.5) / (df + 0.5))
            for tk, df in sec_df.items()
        }

        # Indeks kaya bagi setiap kesalahan dalam master_offences_matrix (tajuk + unsur + perangkap + teks pautan)
        off_tok_cache: Dict[str, set[str]] = {}
        off_df: Dict[str, int] = {}
        for off in self.master_offences_matrix:
            oid = str(off.get("offence_id") or "")
            el_txt = " ".join(str(e.get("description") or "") for e in (off.get("mandatory_elements") or []))
            trap_txt = " ".join(str(x) for x in (off.get("explicit_exclusions_and_traps") or []))
            linked_txt = ""
            for ldid in (off.get("source_section_doc_ids") or [])[:2]:
                if ldid in sec_map:
                    linked_txt += " " + str(sec_map[ldid].get("verbatim_text_bm") or "")[:700]
            raw_off = (
                f"{off.get('offence_section', '')} {off.get('offence_title', '')} "
                f"{off.get('target_offender', '')} {' '.join(off.get('read_together_with') or [])} "
                f"{el_txt} {trap_txt} {linked_txt}"
            ).lower()
            otoks: set[str] = set()
            for t in TOKEN_RE.findall(raw_off):
                if len(t) >= 2 and t not in _GROUNDING_STOPWORDS:
                    otoks.add(t)
                    st = _stem_malay_token(t)
                    if len(st) >= 3 and st not in _GROUNDING_STOPWORDS:
                        otoks.add(st)
            off_tok_cache[oid] = otoks
            for tk in otoks:
                off_df[tk] = off_df.get(tk, 0) + 1
        n_offs = max(1, len(self.master_offences_matrix))
        self._offence_token_cache = off_tok_cache
        self._offence_idf = {
            tk: math.log(1.0 + (n_offs - df + 0.5) / (df + 0.5))
            for tk, df in off_df.items()
        }

    def _try_load_cached_snapshots(self, expected_fingerprint: str) -> bool:
        """Muat terus 4 fail JSON prahurai jika cap jari data/akta/ & versi penghurai tidak berubah."""
        reg_file = self.library_dir / "statutes_registry.json"
        sec_file = self.library_dir / "statute_sections_verbatim.json"
        off_file = self.library_dir / "master_offences_matrix.json"
        rep_file = self.library_dir / "repealed_and_blocked_provisions.json"
        if not all(p.exists() for p in (reg_file, sec_file, off_file, rep_file)):
            return False
        try:
            reg_payload = json.loads(reg_file.read_text(encoding="utf-8"))
            if (
                reg_payload.get("akta_dir_fingerprint") != expected_fingerprint
                or reg_payload.get("parser_version") != PARSER_VERSION
            ):
                return False
            statutes_reg = reg_payload.get("statutes_registry")
            sections_ver = json.loads(sec_file.read_text(encoding="utf-8"))
            offences_mat = json.loads(off_file.read_text(encoding="utf-8"))
            repealed_blk = json.loads(rep_file.read_text(encoding="utf-8"))
            if not isinstance(statutes_reg, list) or not isinstance(sections_ver, list) or not sections_ver:
                return False
            self.statute_library_version = str(
                reg_payload.get("statute_library_version") or INITIAL_STATUTE_LIBRARY_VERSION
            )
            self.statutes_registry = statutes_reg
            self.statute_sections_verbatim = sections_ver
            self.master_offences_matrix = offences_mat
            self.repealed_and_blocked_provisions = repealed_blk
            self._akta_dir_fingerprint = expected_fingerprint
            self._rebuild_runtime_caches()
            return True
        except Exception:
            return False

    @staticmethod
    def _get_persistent_db() -> Any:
        try:
            from backend.core.database import get_uip_db

            return get_uip_db()
        except Exception:
            return None

    def _apply_persistent_admin_overrides(self) -> bool:
        """Memuat semula override pengesahan Admin (VERIFIED_AGC & suntingan explicit_exclusions_and_traps) daripada PostgreSQL/SQLite."""
        db = self._get_persistent_db()
        if db is None or not hasattr(db, "list_legal_admin_overrides"):
            return False
        try:
            overrides = db.list_legal_admin_overrides()
        except Exception:
            return False

        statute_ovs: Dict[str, Dict[str, Any]] = overrides.get("statutes") or {}
        offence_ovs: Dict[str, Dict[str, Any]] = overrides.get("offences") or {}
        if not statute_ovs and not offence_ovs:
            return False

        changed = False
        allowed_fields = (
            "offence_title",
            "offence_section",
            "read_together_with",
            "target_offender",
            "mandatory_elements",
            "explicit_exclusions_and_traps",
            "penalty_section",
            "penalty_first_offence",
            "penalty_subsequent_offence",
            "compound_info",
            "special_legal_requirements",
            "mandatory_exhibits",
            "charge_sheet_template_bm",
            "verified_status",
        )

        # 1. Terapkan override pengesahan statut (VERIFIED_AGC) daripada DB kekal
        for r in self.statutes_registry:
            sid_up = str(r.get("statute_id") or "").upper()
            ov = statute_ovs.get(sid_up)
            if not ov:
                continue
            if ov.get("verified_by_admin") is not None:
                r["verified_by_admin"] = bool(ov["verified_by_admin"])
                changed = True
            if ov.get("verified_at"):
                r["verified_at"] = ov["verified_at"]
            if ov.get("updated_by"):
                r["verified_by"] = ov["updated_by"]
            if ov.get("updated_at"):
                r["last_updated"] = ov["updated_at"]

        # 2. Lata pengesahan statut ke matriks kesalahan (melainkan ada override khusus pada kesalahan individu)
        for o in self.master_offences_matrix:
            sid_up = str(o.get("statute_id") or "").upper()
            oid_up = str(o.get("offence_id") or "").upper()
            st_ov = statute_ovs.get(sid_up)
            if st_ov and st_ov.get("verified_by_admin") is not None:
                o["verified_status"] = "VERIFIED_AGC" if st_ov["verified_by_admin"] else "DRAFT_PENDING_REVIEW"
                if st_ov.get("verified_at"):
                    o["verified_at"] = st_ov["verified_at"]
                changed = True

            off_ov = offence_ovs.get(oid_up)
            if off_ov:
                upd_fields = off_ov.get("updates") or {}
                for k in allowed_fields:
                    if k in upd_fields and upd_fields[k] is not None:
                        o[k] = upd_fields[k]
                        changed = True
                if off_ov.get("verified_status"):
                    o["verified_status"] = str(off_ov["verified_status"])
                    changed = True
                if off_ov.get("verified_at"):
                    o["verified_at"] = off_ov["verified_at"]

        return changed

    def _bootstrap_library(self, force_rebuild: bool = False) -> None:
        """Memuatkan 4 koleksi utama daripada fail warta/teks verbatim rasmi dan mengemas kini indeks JSON."""
        current_fp, file_hashes = self._compute_akta_dir_fingerprint()
        if not force_rebuild and self._try_load_cached_snapshots(current_fp):
            if self._apply_persistent_admin_overrides():
                self._rebuild_runtime_caches()
            return

        now = _utc_now_iso()
        self.statute_library_version = INITIAL_STATUTE_LIBRARY_VERSION
        self.repealed_and_blocked_provisions = [
            dict(item) for item in DEFAULT_REPEALED_AND_BLOCKED_PROVISIONS
        ]
        self.master_offences_matrix = [
            json.loads(json.dumps(item)) for item in DEFAULT_MASTER_OFFENCES_MATRIX
        ]

        # Huraikan semua fail .pdf Warta rasmi TERLEBIH DAHULU, diikuti .txt (hanya untuk akta rujukan silang tanpa PDF)
        all_paths = [
            p
            for p in sorted(self.akta_dir.glob("*"))
            if p.suffix.lower() in (".pdf", ".txt") and not p.name.upper().startswith("PANDUAN_")
        ]
        ordered_paths = [p for p in all_paths if p.suffix.lower() == ".pdf"] + [
            p for p in all_paths if p.suffix.lower() == ".txt"
        ]

        all_sections: List[Dict[str, Any]] = []
        file_sec_counts: Dict[str, int] = {}
        pdf_covered_statute_ids: set[str] = set()

        for path in ordered_paths:
            raw_bytes = path.read_bytes()
            is_pdf = path.suffix.lower() == ".pdf"

            if is_pdf:
                pages: List[str] = []
                with fitz.open(path) as doc:
                    for page in doc:
                        pages.append(page.get_text("text"))
                content = "\n".join(pages)
            else:
                content = raw_bytes.decode("utf-8", errors="ignore")

            if not content.strip():
                continue

            sid = infer_statute_id_from_filename_or_text(path.name, content)
            parsed_secs, pdf_sec_total = parse_statute_verbatim_sections(
                raw_text=content,
                default_statute_id=sid,
                source_filename=path.name,
            )
            if is_pdf:
                for sec in parsed_secs:
                    pdf_covered_statute_ids.add(sec["statute_id"])
                all_sections.extend(parsed_secs)
                file_sec_counts[path.name] = pdf_sec_total
            else:
                # Jangan timpa atau gandakan akta yang sudah mempunyai PDF Warta rasmi AGC
                filtered_secs = [s for s in parsed_secs if s["statute_id"] not in pdf_covered_statute_ids]
                all_sections.extend(filtered_secs)
                file_sec_counts[path.name] = len(filtered_secs)

        self.statute_sections_verbatim = all_sections

        # Pastikan setiap source_section_doc_ids dalam master_offences_matrix merujuk doc_id sebenar dalam statute_sections_verbatim
        sections_by_statute: Dict[str, List[Dict[str, Any]]] = {}
        all_doc_ids = {s["doc_id"] for s in self.statute_sections_verbatim}
        for s in self.statute_sections_verbatim:
            sections_by_statute.setdefault(s["statute_id"], []).append(s)

        for off in self.master_offences_matrix:
            sid = str(off.get("statute_id") or "")
            candidate_secs = sections_by_statute.get(sid, [])
            if not candidate_secs and sid == "PPKM_2009":
                candidate_secs = sections_by_statute.get("AKTA_281", [])
            sec_num_matches = re.findall(r"\d+[A-Za-z]{0,2}", str(off.get("offence_section") or ""))
            primary_num = sec_num_matches[0].upper() if sec_num_matches else ""

            linked_ids: List[str] = [
                did for did in (off.get("source_section_doc_ids") or []) if did in all_doc_ids
            ]
            if primary_num:
                exact_pat = re.compile(
                    rf"^(?:Peraturan\s+|Seksyen\s+|Section\s+)?{re.escape(primary_num)}$",
                    re.I,
                )
                for cs in candidate_secs:
                    if exact_pat.match(str(cs.get("section_code") or "").strip()):
                        if cs["doc_id"] not in linked_ids:
                            linked_ids.insert(0, cs["doc_id"])
            if not linked_ids and candidate_secs:
                linked_ids.append(candidate_secs[0]["doc_id"])
            off["source_section_doc_ids"] = linked_ids

        # Sapuan penuh kesalahan bagi kesemua 13 akta/peraturan penguatkuasaan teras tanpa menimpa 25 entri teras sedia ada
        for sweep_sid in CORE_ENFORCEMENT_SWEEP_STATUTE_IDS:
            statute_secs = sections_by_statute.get(sweep_sid, [])
            if not statute_secs:
                continue
            swept_offences = sweep_sections_for_offences(
                sections=statute_secs,
                statute_id=sweep_sid,
                existing_offences=self.master_offences_matrix,
                verified_by_admin=False,
            )
            for new_off in swept_offences:
                valid_dids = [d for d in (new_off.get("source_section_doc_ids") or []) if d in all_doc_ids]
                if not valid_dids:
                    continue
                new_off["source_section_doc_ids"] = valid_dids
                new_off["verified_status"] = "DRAFT_PENDING_REVIEW"
                self.master_offences_matrix.append(new_off)

        # Bina statutes_registry lengkap dengan kiraan seksyen & kesalahan sebenar
        registry: List[Dict[str, Any]] = []
        for meta in DEFAULT_STATUTES_REGISTRY_META:
            sid = meta["statute_id"]
            src_fname = meta["source_pdf_filename"]
            sec_cnt = sum(1 for s in self.statute_sections_verbatim if s["statute_id"] == sid)
            off_cnt = sum(1 for o in self.master_offences_matrix if o["statute_id"] == sid)
            is_pdf_src = str(src_fname).lower().endswith(".pdf")
            registry.append(
                {
                    **meta,
                    "verified_by_admin": bool(meta.get("verified_by_admin")) and is_pdf_src,
                    "source_pdf_hash": file_hashes.get(src_fname, hashlib.sha256(sid.encode("utf-8")).hexdigest()),
                    "total_sections_indexed": sec_cnt,
                    "total_sections_in_pdf": max(sec_cnt, file_sec_counts.get(src_fname, sec_cnt)),
                    "total_offences_indexed": off_cnt,
                    "last_updated": now,
                }
            )

        # Pastikan tiada entri kesalahan hardcoded/teks .txt bertanda VERIFIED_AGC secara lalai sebelum pengesahan Admin
        verified_pdf_statutes = {
            r["statute_id"] for r in registry if r.get("verified_by_admin") and str(r.get("source_pdf_filename") or "").lower().endswith(".pdf")
        }
        for off in self.master_offences_matrix:
            if off.get("statute_id") not in verified_pdf_statutes:
                off["verified_status"] = "DRAFT_PENDING_REVIEW"

        self.statutes_registry = registry
        self._akta_dir_fingerprint = current_fp
        # Muat semula pengesahan & suntingan Admin daripada pangkalan data kekal supaya tidak pernah ditimpa
        self._apply_persistent_admin_overrides()
        self._rebuild_runtime_caches()
        self._persist_json_snapshots()

    def _persist_json_snapshots(self) -> None:
        """Menyimpan 4 koleksi utama ke data/legal_library/*.json untuk audit dan kegunaan luar talian."""
        try:
            (self.library_dir / "statutes_registry.json").write_text(
                json.dumps(
                    {
                        "statute_library_version": self.statute_library_version,
                        "parser_version": PARSER_VERSION,
                        "akta_dir_fingerprint": self._akta_dir_fingerprint,
                        "statutes_registry": self.statutes_registry,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            (self.library_dir / "statute_sections_verbatim.json").write_text(
                json.dumps(self.statute_sections_verbatim, ensure_ascii=False),
                encoding="utf-8",
            )
            (self.library_dir / "master_offences_matrix.json").write_text(
                json.dumps(self.master_offences_matrix, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            (self.library_dir / "repealed_and_blocked_provisions.json").write_text(
                json.dumps(self.repealed_and_blocked_provisions, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    def bump_version(self, tag: str = "ingest") -> str:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        self.statute_library_version = f"2.6.0-{tag}-{ts}"
        self._akta_dir_fingerprint = f"MUTATED_{tag}_{ts}"
        self._rebuild_runtime_caches()
        self._persist_json_snapshots()
        return self.statute_library_version

    def to_snapshot_dict(self) -> Dict[str, Any]:
        return {
            "statute_library_version": self.statute_library_version,
            "statutes_registry": self.statutes_registry,
            "statute_sections_verbatim": self.statute_sections_verbatim,
            "master_offences_matrix": self.master_offences_matrix,
            "repealed_and_blocked_provisions": self.repealed_and_blocked_provisions,
            "_valid_sections_cache": self._valid_sections_cache,
        }

    def register_unindexed_statute(
        self,
        statute_id: str,
        official_title_bm: str,
        act_number_or_pu: str,
        official_title_en: str = "",
    ) -> Dict[str, Any]:
        """Mendaftarkan metadata akta yang belum dimuat naik PDF Warta (total_sections_indexed = 0)."""
        sid = statute_id.strip().upper().replace(" ", "_")
        now = _utc_now_iso()
        existing = next((s for s in self.statutes_registry if s["statute_id"] == sid), None)
        entry = {
            "statute_id": sid,
            "canonical_akta_code": canonical_akta_code_for_statute(sid),
            "official_title_bm": official_title_bm,
            "official_title_en": official_title_en or official_title_bm,
            "act_number_or_pu": act_number_or_pu,
            "status": "BERKUAT_KUASA",
            "repealed_by": None,
            "effective_date": now[:10],
            "source_pdf_filename": "BELUM_DIMUAT_NAIK",
            "source_pdf_hash": "",
            "total_sections_indexed": 0,
            "total_sections_in_pdf": 0,
            "total_offences_indexed": 0,
            "verified_by_admin": False,
            "last_updated": now,
        }
        if existing:
            existing.update(entry)
        else:
            self.statutes_registry.append(entry)
        self._akta_dir_fingerprint = f"MUTATED_REG_{sid}"
        self._persist_json_snapshots()
        return entry

    def ingest_statute_bytes(
        self,
        filename: str,
        raw_bytes: bytes,
        *,
        statute_id: Optional[str] = None,
        official_title_bm: Optional[str] = None,
        official_title_en: Optional[str] = None,
        act_number_or_pu: Optional[str] = None,
        effective_date: Optional[str] = None,
        verified_by_admin: bool = False,
    ) -> Dict[str, Any]:
        """FASA 2: Menghurai fail PDF/TXT Warta Kerajaan Rasmi secara deterministik & imbasan kesalahan."""
        safe_name = Path(filename).name
        sha256 = hashlib.sha256(raw_bytes).hexdigest()
        is_official_pdf = safe_name.lower().endswith(".pdf")
        # Hanya fail PDF Warta rasmi dibenarkan ditandakan verified_by_admin semasa muat naik; fail .txt wajib DRAFT_PENDING_REVIEW
        effective_verified = bool(verified_by_admin) and is_official_pdf

        if is_official_pdf:
            if not raw_bytes or not raw_bytes.lstrip()[:5].startswith(b"%PDF-"):
                raise ValueError("Fail yang dimuat naik bukan fail PDF Warta yang sah (header %PDF tiada).")
            pages: List[str] = []
            try:
                with fitz.open(stream=raw_bytes, filetype="pdf") as doc:
                    if getattr(doc, "needs_pass", False):
                        raise ValueError("Fail PDF Warta ini dikunci kata laluan dan tidak dapat diindeks.")
                    for page in doc:
                        pages.append(page.get_text("text"))
            except ValueError:
                raise
            except Exception as exc:
                raise ValueError(f"Fail PDF Warta rosak atau tidak dapat dibaca: {exc}") from exc
            raw_text = "\n".join(pages)
        else:
            raw_text = raw_bytes.decode("utf-8", errors="ignore")

        if not raw_text.strip():
            raise ValueError("Fail PDF/teks akta yang dimuat naik tidak mengandungi teks yang boleh dibaca.")

        sid = infer_statute_id_from_filename_or_text(safe_name, raw_text, explicit_statute_id=statute_id)
        parsed_secs, pdf_sec_count = parse_statute_verbatim_sections(
            raw_text=raw_text,
            default_statute_id=sid,
            source_filename=safe_name,
        )

        # Gantikan atau tambah seksyen verbatim bagi statute_id tersebut
        new_doc_ids = {s["doc_id"] for s in parsed_secs}
        self.statute_sections_verbatim = [
            s for s in self.statute_sections_verbatim if s["doc_id"] not in new_doc_ids
        ] + parsed_secs

        # Jalankan Section-by-Section Offence Sweep
        discovered_offences = sweep_sections_for_offences(
            sections=parsed_secs,
            statute_id=sid,
            existing_offences=self.master_offences_matrix,
            verified_by_admin=effective_verified,
        )
        new_off_ids = {o["offence_id"] for o in discovered_offences}
        self.master_offences_matrix = [
            o for o in self.master_offences_matrix if o["offence_id"] not in new_off_ids
        ] + discovered_offences

        # Kemas kini statutes_registry
        now = _utc_now_iso()
        total_sec_for_sid = sum(1 for s in self.statute_sections_verbatim if s["statute_id"] == sid)
        total_off_for_sid = sum(1 for o in self.master_offences_matrix if o["statute_id"] == sid)
        existing_reg = next((r for r in self.statutes_registry if r["statute_id"] == sid), None)

        if existing_reg:
            existing_reg["source_pdf_filename"] = safe_name
            existing_reg["source_pdf_hash"] = sha256
            existing_reg["total_sections_indexed"] = total_sec_for_sid
            existing_reg["total_sections_in_pdf"] = max(total_sec_for_sid, pdf_sec_count)
            existing_reg["total_offences_indexed"] = total_off_for_sid
            existing_reg["verified_by_admin"] = effective_verified
            existing_reg["last_updated"] = now
            if official_title_bm:
                existing_reg["official_title_bm"] = official_title_bm
            if official_title_en:
                existing_reg["official_title_en"] = official_title_en
            if act_number_or_pu:
                existing_reg["act_number_or_pu"] = act_number_or_pu
            if effective_date:
                existing_reg["effective_date"] = effective_date
            reg_record = existing_reg
        else:
            reg_record = {
                "statute_id": sid,
                "canonical_akta_code": canonical_akta_code_for_statute(sid),
                "official_title_bm": official_title_bm or safe_name.replace("_", " "),
                "official_title_en": official_title_en or official_title_bm or safe_name,
                "act_number_or_pu": act_number_or_pu or sid.replace("_", " "),
                "status": "BERKUAT_KUASA",
                "repealed_by": None,
                "effective_date": effective_date or now[:10],
                "source_pdf_filename": safe_name,
                "source_pdf_hash": sha256,
                "total_sections_indexed": total_sec_for_sid,
                "total_sections_in_pdf": max(total_sec_for_sid, pdf_sec_count),
                "total_offences_indexed": total_off_for_sid,
                "verified_by_admin": effective_verified,
                "last_updated": now,
            }
            self.statutes_registry.append(reg_record)

        if effective_verified:
            db = self._get_persistent_db()
            if db is not None and hasattr(db, "upsert_legal_statute_override"):
                try:
                    db.upsert_legal_statute_override(
                        sid,
                        verified_by_admin=True,
                        verified_at=now,
                    )
                except Exception:
                    pass

        new_ver = self.bump_version(tag=sid.lower())
        return {
            "status": "berjaya",
            "statute_id": sid,
            "canonical_akta_code": canonical_akta_code_for_statute(sid),
            "filename": safe_name,
            "source_pdf_hash": sha256,
            "sections_extracted": len(parsed_secs),
            "new_offences_swept": len(discovered_offences),
            "total_sections_indexed": total_sec_for_sid,
            "total_offences_indexed": total_off_for_sid,
            "verified_by_admin": effective_verified,
            "statute_library_version": new_ver,
            "registry_record": reg_record,
            "discovered_offences": discovered_offences,
        }

    def verify_statute_or_offence(
        self,
        *,
        statute_id: Optional[str] = None,
        offence_id: Optional[str] = None,
        verified: bool = True,
        updated_by: str = "",
    ) -> Dict[str, Any]:
        """Menandakan akta atau rekod kesalahan sebagai VERIFIED_AGC ('Sahkan Warta') dan menyimpannya ke DB kekal."""
        now = _utc_now_iso()
        updated_statutes = 0
        updated_offences = 0
        db = self._get_persistent_db()

        if statute_id:
            sid = statute_id.strip().upper()
            for r in self.statutes_registry:
                if r["statute_id"].upper() == sid:
                    r["verified_by_admin"] = verified
                    r["verified_at"] = now if verified else None
                    if updated_by:
                        r["verified_by"] = updated_by
                    r["last_updated"] = now
                    updated_statutes += 1
            for o in self.master_offences_matrix:
                if o["statute_id"].upper() == sid:
                    o["verified_status"] = "VERIFIED_AGC" if verified else "DRAFT_PENDING_REVIEW"
                    o["verified_at"] = now if verified else None
                    updated_offences += 1
            if updated_statutes > 0 and db is not None and hasattr(db, "upsert_legal_statute_override"):
                try:
                    db.upsert_legal_statute_override(
                        sid,
                        verified_by_admin=verified,
                        verified_at=now if verified else None,
                        updated_by=updated_by,
                    )
                except Exception:
                    pass

        if offence_id:
            oid = offence_id.strip().upper()
            new_status = "VERIFIED_AGC" if verified else "DRAFT_PENDING_REVIEW"
            for o in self.master_offences_matrix:
                if o["offence_id"].upper() == oid:
                    o["verified_status"] = new_status
                    o["verified_at"] = now if verified else None
                    updated_offences += 1
            if updated_offences > 0 and db is not None and hasattr(db, "upsert_legal_offence_override"):
                try:
                    db.upsert_legal_offence_override(
                        oid,
                        verified_status=new_status,
                        verified_at=now if verified else None,
                        updated_by=updated_by,
                    )
                except Exception:
                    pass

        self._persist_json_snapshots()
        return {
            "updated_statutes": updated_statutes,
            "updated_offences": updated_offences,
            "verified_at": now if verified else None,
            "persisted_to_db": db is not None,
            "statute_library_version": self.statute_library_version,
        }

    def update_offence(
        self,
        offence_id: str,
        updates: Dict[str, Any],
        *,
        updated_by: str = "",
    ) -> Optional[Dict[str, Any]]:
        """Membolehkan Admin menyunting explicit_exclusions_and_traps, mandatory_elements, dsb. secara kekal di DB."""
        target = next(
            (o for o in self.master_offences_matrix if o["offence_id"].upper() == offence_id.strip().upper()),
            None,
        )
        if not target:
            return None

        allowed_fields = (
            "offence_title",
            "offence_section",
            "read_together_with",
            "target_offender",
            "mandatory_elements",
            "explicit_exclusions_and_traps",
            "penalty_section",
            "penalty_first_offence",
            "penalty_subsequent_offence",
            "compound_info",
            "special_legal_requirements",
            "mandatory_exhibits",
            "charge_sheet_template_bm",
            "verified_status",
        )
        applied_updates: Dict[str, Any] = {}
        for k in allowed_fields:
            if k in updates and updates[k] is not None:
                target[k] = updates[k]
                applied_updates[k] = updates[k]

        if applied_updates:
            db = self._get_persistent_db()
            if db is not None and hasattr(db, "upsert_legal_offence_override"):
                try:
                    ver_st = applied_updates.get("verified_status")
                    db.upsert_legal_offence_override(
                        target["offence_id"],
                        verified_status=str(ver_st) if ver_st is not None else None,
                        updates=applied_updates,
                        updated_by=updated_by,
                    )
                except Exception:
                    pass

        self.bump_version(tag="edit-offence")
        return target

    def get_coverage_audit_report(self) -> Dict[str, Any]:
        """FASA 2.4: Laporan Liputan 100% (Coverage Audit Dashboard)."""
        active_statutes = [s for s in self.statutes_registry if s["status"] == "BERKUAT_KUASA"]
        unverified_statutes = [
            s["statute_id"]
            for s in active_statutes
            if not s.get("verified_by_admin") or int(s.get("total_sections_indexed") or 0) == 0
        ]
        unindexed_statutes = [
            s["statute_id"]
            for s in active_statutes
            if int(s.get("total_sections_indexed") or 0) == 0
        ]
        pending_offences = [
            o["offence_id"]
            for o in self.master_offences_matrix
            if o.get("verified_status") != "VERIFIED_AGC"
        ]
        return {
            "statute_library_version": self.statute_library_version,
            "total_statutes": len(self.statutes_registry),
            "active_statutes_count": len(active_statutes),
            "total_verbatim_sections": len(self.statute_sections_verbatim),
            "total_master_offences": len(self.master_offences_matrix),
            "total_repealed_blocked": len(self.repealed_and_blocked_provisions),
            "unverified_statutes": unverified_statutes,
            "unindexed_statutes": unindexed_statutes,
            "pending_review_offences": pending_offences,
            "has_coverage_warning": bool(unverified_statutes or unindexed_statutes or pending_offences),
            "statutes_registry": self.statutes_registry,
        }

    def list_verbatim_sections(
        self,
        *,
        statute_id: Optional[str] = None,
        akta_code: Optional[str] = None,
        q: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Menyenaraikan teks penuh verbatim mengikut Bahagian & Seksyen (atau amaran jika akta belum diindeks)."""
        if statute_id:
            sid_up = statute_id.strip().upper()
            reg = next((r for r in self.statutes_registry if r["statute_id"].upper() == sid_up), None)
            if reg and int(reg.get("total_sections_indexed") or 0) == 0 and reg.get("status") != "DIMANSUHKAN":
                return {
                    "status": "AKTA BELUM DIINDEKS — MUAT NAIK PDF WARTA",
                    "statute_id": sid_up,
                    "unindexed": True,
                    "statute_library_version": self.statute_library_version,
                    "total": 0,
                    "message": f"AKTA BELUM DIINDEKS — MUAT NAIK PDF WARTA ({reg.get('official_title_bm', sid_up)})",
                    "sections": [],
                }

        results: List[Dict[str, Any]] = []
        q_raw_s = (q or "").strip()
        q_low = q_raw_s.lower()
        q_norm_low = normalize_ppkp_query(q_raw_s).lower() if q_raw_s else ""
        q_exact_toks, q_exp_toks = expand_query_for_grounding(q_raw_s) if q_raw_s else (set(), set())
        # Token bermakna sahaja untuk padanan sinonim direktori supaya carian kata rawak tidak menghasilkan bunyi bising
        q_meaningful_exp = {t for t in q_exp_toks if len(t) >= 3}
        q_sec_num_m = re.match(
            r"^(?:seksyen|peraturan|section|regulation|s\.?|p\.?)\s*(\d+[a-z]{0,2})(?:\([a-z0-9]+\))*$",
            q_low,
            flags=re.I,
        )
        q_sec_num = q_sec_num_m.group(1).lower() if q_sec_num_m else ""

        scored_results: List[Tuple[int, Dict[str, Any]]] = []
        for sec in self.statute_sections_verbatim:
            if statute_id and statute_id.lower() != "semua":
                if sec["statute_id"].upper() != statute_id.strip().upper():
                    continue
            if akta_code and akta_code.lower() != "semua":
                c_act = canonical_akta_code_for_statute(sec["statute_id"])
                ac_canon = canonical_akta_code_for_statute(akta_code)
                if (
                    akta_code.lower() != c_act.lower()
                    and ac_canon.lower() != c_act.lower()
                    and not re.search(rf"(?<!\w){re.escape(akta_code.lower())}(?!\w)", sec["statute_id"].lower())
                ):
                    continue
            match_rank = 0
            if q_low:
                sc_code_l = str(sec.get("section_code") or "").lower()
                hay = f"{sec['statute_id']} {sc_code_l} {sec['section_heading']} {sec['verbatim_text_bm']}".lower()
                if q_low in hay or (q_norm_low and q_norm_low in hay):
                    match_rank = 3
                elif q_sec_num and re.search(rf"(?<!\w){re.escape(q_sec_num)}(?!\w)", sc_code_l):
                    match_rank = 3
                else:
                    s_toks = self._section_token_cache.get(sec["doc_id"])
                    if s_toks is None:
                        s_toks = {t.lower() for t in TOKEN_RE.findall(hay) if len(t) >= 2}
                    exact_hits = len(q_exact_toks & s_toks)
                    exp_hits = len(q_meaningful_exp & s_toks)
                    if q_exact_toks and exact_hits == len(q_exact_toks):
                        match_rank = 2
                    elif exp_hits >= 2 or (exact_hits >= 1 and exp_hits >= 1):
                        match_rank = 1
                    else:
                        continue
            # Jangan pulangkan embedding_vector 64-float pada senarai UI bagi menjimatkan lebar jalur
            scored_results.append((match_rank, {k: v for k, v in sec.items() if k != "embedding_vector"}))

        if q_low:
            scored_results.sort(key=lambda item: item[0], reverse=True)
        results = [item[1] for item in scored_results]

        return {
            "status": "OK",
            "unindexed": False,
            "statute_library_version": self.statute_library_version,
            "total": len(results),
            "sections": results,
        }

    def list_master_offences(
        self,
        *,
        statute_id: Optional[str] = None,
        akta_code: Optional[str] = None,
        target_offender: Optional[str] = None,
        is_compoundable: Optional[bool] = None,
        verified_status: Optional[str] = None,
        q: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        sec_map = {s["doc_id"]: s for s in self.statute_sections_verbatim}
        q_raw_s = (q or "").strip()
        q_low = q_raw_s.lower()
        q_norm_low = normalize_ppkp_query(q_raw_s).lower() if q_raw_s else ""
        q_exact_toks, q_exp_toks = expand_query_for_grounding(q_raw_s) if q_raw_s else (set(), set())
        q_meaningful_exp = {t for t in q_exp_toks if len(t) >= 3}
        scored_out: List[Tuple[int, Dict[str, Any]]] = []

        for off in self.master_offences_matrix:
            sid = str(off.get("statute_id") or "")
            c_act = canonical_akta_code_for_statute(sid)
            if statute_id and statute_id.lower() != "semua":
                if sid.upper() != statute_id.strip().upper():
                    continue
            if akta_code and akta_code.lower() != "semua":
                ac_canon = canonical_akta_code_for_statute(akta_code)
                if (
                    akta_code.lower() != c_act.lower()
                    and ac_canon.lower() != c_act.lower()
                    and not re.search(rf"(?<!\w){re.escape(akta_code.lower())}(?!\w)", sid.lower())
                ):
                    continue
            if target_offender and target_offender.upper() != "SEMUA":
                if str(off.get("target_offender") or "").upper() != target_offender.strip().upper():
                    continue
            if is_compoundable is not None:
                comp_flag = bool((off.get("compound_info") or {}).get("is_compoundable"))
                if comp_flag != is_compoundable:
                    continue
            if verified_status and verified_status.upper() != "SEMUA":
                if str(off.get("verified_status") or "").upper() != verified_status.strip().upper():
                    continue
            match_rank = 0
            if q_low:
                # Cari hanya pada medan boleh dibaca manusia (bukan json.dumps supaya "true"/"false" tidak sepadan nilai boolean)
                comp_info = off.get("compound_info") if isinstance(off.get("compound_info"), dict) else {}
                readable_parts = [
                    str(off.get("offence_id") or ""),
                    sid,
                    c_act,
                    str(off.get("offence_section") or ""),
                    str(off.get("offence_title") or ""),
                    " ".join(str(x) for x in (off.get("read_together_with") or [])),
                    str(off.get("target_offender") or ""),
                    str(off.get("penalty_first_offence") or ""),
                    str(off.get("penalty_subsequent_offence") or ""),
                    str(off.get("charge_sheet_template_bm") or ""),
                    " ".join(str(x) for x in (off.get("special_legal_requirements") or [])),
                    " ".join(str(x) for x in (off.get("mandatory_exhibits") or [])),
                    str(comp_info.get("max_compound_rm") or ""),
                    str(comp_info.get("notes") or ""),
                ]
                hay = " ".join(readable_parts).lower()
                if q_low in hay or (q_norm_low and q_norm_low in hay):
                    match_rank = 3
                else:
                    hay_toks = {t.lower() for t in TOKEN_RE.findall(hay) if len(t) >= 2}
                    exact_hits = len(q_exact_toks & hay_toks)
                    exp_hits = len(q_meaningful_exp & hay_toks)
                    if q_exact_toks and exact_hits == len(q_exact_toks):
                        match_rank = 2
                    elif exp_hits >= 2 or (exact_hits >= 1 and exp_hits >= 1):
                        match_rank = 1
                    else:
                        continue

            # Sertakan teks penuh verbatim bagi source_section_doc_ids
            linked_verbatim = [
                {
                    "doc_id": did,
                    "statute_id": sec_map[did]["statute_id"],
                    "section_code": sec_map[did]["section_code"],
                    "section_heading": sec_map[did]["section_heading"],
                    "verbatim_text_bm": sec_map[did]["verbatim_text_bm"],
                }
                for did in (off.get("source_section_doc_ids") or [])
                if did in sec_map
            ]
            scored_out.append(
                (
                    match_rank,
                    {
                        **off,
                        "canonical_akta_code": c_act,
                        "linked_verbatim_sections": linked_verbatim,
                    },
                )
            )
        if q_low:
            scored_out.sort(key=lambda item: item[0], reverse=True)
        return [item[1] for item in scored_out]

    def search_closed_book_grounding(
        self,
        question: str,
        akta_hint: str = "Semua",
        top_k: int = 4,
    ) -> Dict[str, Any]:
        """FASA 3.1 (v3): Carian Hibrid IDF + Rujukan Silang Akta + Katalog Penuh Domain Sebelum Menjawab.

        Mencari:
        a) Padanan dalam `repealed_and_blocked_provisions`.
        b) 1–4 calon kesalahan utama dalam `master_offences_matrix` (IDF-weighted + perluasan sinonim dwibahasa + sempadan kata tepat).
        c) Teks penuh verbatim daripada `statute_sections_verbatim` menggunakan 2 slot berasingan (Slot A pautan kesalahan + Slot B carian bebas IDF + bonus padanan nombor seksyen tepat +8.0).
        d) Katalog ringkas 1-baris bagi SEMUA kesalahan dalam domain Akta aktif supaya AI tidak pernah "buta" terhadap seksyen sebenar.
        """
        q_raw = (question or "").strip()
        q_norm = normalize_ppkp_query(q_raw)
        q_low = q_norm.lower()
        exact_tokens, expanded_tokens = expand_query_for_grounding(q_raw)
        q_tokens = exact_tokens | expanded_tokens
        asks_definition = any(
            k in q_low for k in ("tafsiran", "definisi", "maksud ", "seksyen 2", "sek. 2", "s.2 ", "akta 388")
        )
        allowed_sids = infer_domain_statute_ids(q_norm or q_raw, akta_hint)
        support_sids = {"AKTA_593", "AKTA_574", "AKTA_344", "AKTA_388", "AKTA_92", "AKTA_56", "AKTA_611"}
        is_passive_vape = is_passive_vape_possession_question(q_norm or q_raw)
        has_minor_signal = any(
            re.search(rf"(?<!\w){re.escape(k)}(?!\w)", q_low)
            for k in ("pelajar", "murid", "budak", "sekolah", "obd", "bawah 18", "bawah umur", "kanak-kanak")
        )
        has_signage_duty = _has_signage_or_premise_smoking_duty_signal(q_norm or q_raw)
        has_active_smoker = _has_active_smoking_action(q_norm or q_raw)

        # 0. Semak sama ada soalan/akta_hint merujuk akta yang belum diindeks (total_sections_indexed == 0)
        unindexed_hit: Optional[Dict[str, Any]] = None
        for reg in self.statutes_registry:
            if reg.get("status") == "DIMANSUHKAN":
                continue
            if int(reg.get("total_sections_indexed") or 0) == 0:
                sid = str(reg.get("statute_id") or "")
                act_num = str(reg.get("act_number_or_pu") or "")
                if (
                    (akta_hint and akta_hint.upper() == sid.upper())
                    or (sid and re.search(rf"(?<!\w){re.escape(sid.lower())}(?!\w)", q_low))
                    or (act_num and re.search(rf"(?<!\w){re.escape(act_num.lower())}(?!\w)", q_low))
                ):
                    unindexed_hit = reg
                    break

        # a) Padanan dalam `repealed_and_blocked_provisions`
        repealed_matches: List[Dict[str, Any]] = []
        for rep in self.repealed_and_blocked_provisions:
            for pat in rep.get("match_patterns") or []:
                if re.search(pat, q_low, flags=re.I):
                    repealed_matches.append(rep)
                    break

        off_idf: Dict[str, float] = getattr(self, "_offence_idf", {})
        off_tok_cache: Dict[str, set[str]] = getattr(self, "_offence_token_cache", {})
        sec_idf: Dict[str, float] = getattr(self, "_section_idf", {})

        # b) Calon kesalahan dalam `master_offences_matrix`
        scored_offences: List[Tuple[float, Dict[str, Any], Dict[str, Any]]] = []
        if is_passive_vape:
            target_oids = ["AKTA_852_S17_1"]
            if any(k in q_low for k in ("beli", "membeli", "13(3)", "kedai", "penjual")):
                target_oids.append("AKTA_852_S13_3")
            for oid in target_oids:
                matched_off = next(
                    (o for o in self.master_offences_matrix if o.get("offence_id") == oid),
                    None,
                )
                if matched_off:
                    ev = evaluate_offence_elements_against_facts(q_norm or q_raw, matched_off)
                    scored_offences.append((10.0 if oid == "AKTA_852_S17_1" else 6.0, matched_off, ev))
        else:
            for off in self.master_offences_matrix:
                oid = str(off.get("offence_id") or "")
                sid = str(off.get("statute_id") or "")
                c_act = canonical_akta_code_for_statute(sid)
                if allowed_sids is not None and sid not in allowed_sids:
                    continue
                if akta_hint and akta_hint not in ("", "Semua"):
                    hint_canon = canonical_akta_code_for_statute(akta_hint)
                    is_attached_support = allowed_sids is not None and sid in allowed_sids and sid in support_sids
                    if (
                        akta_hint.lower() != c_act.lower()
                        and hint_canon.lower() != c_act.lower()
                        and not re.search(rf"(?<!\w){re.escape(akta_hint.lower())}(?!\w)", sid.lower())
                        and not is_attached_support
                    ):
                        continue

                off_tokens = off_tok_cache.get(oid)
                if off_tokens is None:
                    off_text = (
                        f"{off.get('offence_section', '')} {off.get('offence_title', '')} "
                        f"{' '.join(off.get('read_together_with') or [])}"
                    ).lower()
                    off_tokens = {
                        t for t in TOKEN_RE.findall(off_text)
                        if len(t) >= 2 and t not in _GROUNDING_STOPWORDS
                    }

                # Skor IDF: token tepat (berat 1.0) + token padanan sinonim dwibahasa (berat 0.55)
                score = sum(off_idf.get(t, 1.0) for t in (exact_tokens & off_tokens))
                score += 0.55 * sum(off_idf.get(t, 1.0) for t in (expanded_tokens & off_tokens))

                # Utamakan entri kurasi utama berbanding entri auto-sweep bertajuk generik
                title_len = len(str(off.get("offence_title") or "").strip())
                if title_len < 24:
                    score *= 0.6
                if oid == "AKTA_852_PERATURAN_TANDA_2024_PERATURAN_2":
                    # Seksyen 18(1)(a) Akta 852 ialah punca kuasa pertuduhan/kompaun utama, bukan Peraturan 2 secara bersendirian
                    score *= 0.65

                # Bonus padanan nombor seksyen tepat (cth: "18(1)", "16(2)", "13b", "8(8)", "186", "465")
                # Gunakan (?!\w) bukannya \b supaya seksyen berakhir dengan ')' seperti 18(1) sentiasa padan
                sec_nums = re.findall(r"\d+[A-Za-z]?(?:\(\d+\))?", str(off.get("offence_section") or ""))
                if sec_nums and any(
                    re.search(rf"(?<!\w)(?:seksyen|peraturan|section|s\.?|p\.?)\s*{re.escape(sn)}(?!\w)", q_low, re.I)
                    for sn in sec_nums[:3]
                ):
                    score += 6.0

                # Isyarat niat khusus bersempadan kata (word-boundary — TIADA lagi 'merokok di' kena 'merokok dipasang'!)
                if oid == "AKTA_852_S18_1" and has_signage_duty:
                    score += 9.5
                if oid == "AKTA_852_S17_1" and has_minor_signal and (
                    has_active_smoker or bool(re.search(r"(?<!\w)(?:vape|rokok|pod|17\(1\))(?!\w)", q_low))
                ):
                    score += 8.0
                if oid == "AKTA_852_S13_1" and has_minor_signal and bool(
                    re.search(r"\b(?:jual|menjual|pekedai|penjual|kedai|staf\s+kedai)\b", q_low)
                ):
                    score += 7.5
                if oid == "AKTA_852_S10_1" and bool(
                    re.search(r"\b(?:pamer|mempamer|pameran|kaunter|kabinet\s+bertutup|opaque|online|dalam\s+talian|tiktok|shopee|lazada|facebook|whatsapp|vending)\b", q_low)
                ) and not has_signage_duty:
                    score += 7.5
                if oid == "AKTA_852_S16_2" and not has_minor_signal:
                    # Hanya naikkan S.16(2) jika ada perbuatan merokok/menghisap (ATAU bukan soalan tanda larangan/ashtray semata-mata)
                    if has_active_smoker or (
                        not has_signage_duty
                        and bool(
                            re.search(
                                r"\b(?:restoran|tempat\s+makan|mall|kompleks|pusat\s+beli|pusat\s+membeli|"
                                r"parking|parkir|letak\s+kereta|kereta|kenderaan\s+awam|bas\s+sekolah|"
                                r"hospital|klinik|lif|tandas\s+awam|dobi|lapangan\s+terbang|stesen\s+minyak|"
                                r"bangunan|tempat\s+kerja|taman\s+awam|r&r|stadium|perpustakaan|kafe|cafe|cafetaria|kafeteria)\b",
                                q_low,
                                re.I,
                            )
                        )
                    ):
                        score += 8.0
                if oid == "AKTA_852_S3_1" and not bool(
                    re.search(
                        r"(?<!\w)(?:import|mengimport|kilang|mengilang|edar|mengedar|pengedar|daftar|pendaftaran|tidak\s+berdaftar|262/2024|s\.?\s*3(?:\(1\))?|seksyen\s+3(?:\(1\))?)(?!\w)",
                        q_low,
                        re.I,
                    )
                ):
                    score = 0.0
                # Isyarat tepat bagi Akta 281 / PPKM 2009 / Akta 154 / Akta 342
                if oid == "PPKM_2009_P8_1" and bool(re.search(r"\b(?:fosim|perakuan\s+pendaftaran|sijil\s+pendaftaran)\b", q_low)) and bool(
                    re.search(r"\b(?:tampal|pamer|dinding|phone|telefon|sah\s+berdaftar|memang\s+berdaftar)\b", q_low)
                ):
                    score += 7.5
                if oid == "PPKM_2009_P31_1" and bool(re.search(r"\b(?:tifoid|typhoid|antitifoid|suntikan)\b", q_low)):
                    score += 6.0
                if oid == "PPKM_2009_P32_1" and bool(re.search(r"\b(?:apron|penutup\s+kepala|pakaian\s+pengendali|kasut)\b", q_low)):
                    score += 6.0
                if oid == "AKTA_281_S13A_2" and bool(re.search(r"\b(?:bangkai\s+lipas|benda\s+asing|jirim\s+asing|paku|kaca|dawai|busuk|reput|13a)\b", q_low)):
                    score += 8.5
                if oid == "AKTA_281_S13B_1" and bool(re.search(r"\b(?:diaduk|bahan\s+tambah|piawaian\s+makanan|13b)\b", q_low)):
                    score += 7.5
                if oid == "AKTA_281_S11_2" and bool(re.search(r"(?<!\w)(?:perintah\s+tutup|penutupan\s+premis|seksyen\s+11|s\.?\s*11|11\(1\)|11\(2\))(?!\w)", q_low)) and not bool(
                    re.search(r"(?<!\w)(?:hfmd|taska|342|18\(1\)\(d\))(?!\w)", q_low)
                ):
                    score += 7.0
                if oid == "AKTA_154_S8_8" and bool(re.search(r"(?<!\w)(?:ingkar\s+perintah|perintah\s+bertulis\s+seksyen\s+8|s\.?\s*8\(1\)|s\.?\s*8\(8\)|s\.?\s*8\(2\))(?!\w)", q_low)):
                    score += 7.0
                if oid == "AKTA_154_S21" and bool(re.search(r"\b(?:menghalang|halang|fogging|semburan\s+kabus|berkunci|mangga|seksyen\s+21)\b", q_low)):
                    score += 8.5
                if oid == "AKTA_342_S12_1" and bool(re.search(r"(?<!\w)(?:bersiar-siar|mendedahkan\s+orang\s+awam|seksyen\s+12|12\(1\))(?!\w)", q_low)):
                    score += 7.5
                if oid == "AKTA_342_S22_B" and bool(re.search(r"(?<!\w)(?:ingkar\s+perintah|perintah\s+tutup|18\(1\)\(d\)|hfmd|cicir\s+rawatan|22\(b\))(?!\w)", q_low)):
                    score += 7.0
                # Isyarat rujukan silang Akta 574 (Kanun Keseksaan) & Akta 344 (Akta Polis)
                if oid == "AKTA_574_S186" and bool(re.search(r"\b(?:menghalang|halang|halangan|kunci\s+pintu|186)\b", q_low)) and not bool(
                    re.search(r"\b(?:fogging|aedes|denggi|154)\b", q_low)
                ):
                    score += 8.0
                if oid == "AKTA_574_S183" and bool(re.search(r"\b(?:rampas\s+balik|rampas\s+semula|menentang\s+sitaan|183)\b", q_low)):
                    score += 8.0
                if oid == "AKTA_574_S189" and bool(re.search(r"\b(?:ugut|ugutan|mengugut|189)\b", q_low)):
                    score += 7.5
                if oid == "AKTA_574_S506" and bool(re.search(r"\b(?:ugut\s+bunuh|ugutan\s+jenayah|parang|pisau|senjata|bakar|506)\b", q_low)):
                    score += 8.5
                if oid == "AKTA_574_S353" and bool(re.search(r"\b(?:serang|menyerang|pukul|tumbuk|tolak|ludah|kekerasan|353)\b", q_low)):
                    score += 8.5
                if oid == "AKTA_574_S170" and bool(re.search(r"\b(?:menyamar|penyamaran|ppkp\s+palsu|pegawai\s+palsu|170)\b", q_low)):
                    score += 9.0
                if oid == "AKTA_574_S177" and bool(re.search(r"\b(?:maklumat\s+palsu|aduan\s+palsu|nama\s+palsu|fitnah|177|182)\b", q_low)):
                    score += 8.0
                if oid == "AKTA_574_S465" and bool(re.search(r"\b(?:sijil\s+palsu|dokumen\s+palsu|tifoid\s+palsu|slpm\s+palsu|fosim\s+palsu|pemalsuan|465|468|471)\b", q_low)):
                    score += 9.0
                if oid == "AKTA_574_S269" and bool(re.search(r"\b(?:269|270|cuai\s+merebak|jahat\s+merebak|meludah\s+penyakit)\b", q_low)):
                    score += 7.5
                if oid == "AKTA_574_S272" and bool(re.search(r"\b(?:272|273|kanun\s+keseksaan.*makanan|penal\s+code.*food)\b", q_low)):
                    score += 7.0
                if oid == "AKTA_344_S90" and bool(re.search(r"\b(?:halang\s+polis|menghalang\s+polis|seksyen\s+90\s+akta\s+344|akta\s+344.*90)\b", q_low)):
                    score += 8.5

                if score >= 1.2:
                    eval_res = evaluate_offence_elements_against_facts(q_raw, off)
                    scored_offences.append((score, off, eval_res))

        scored_offences.sort(key=lambda x: x[0], reverse=True)
        # Benarkan sehingga 4 calon kesalahan paling relevan (dengan ambang 0.35 supaya kesalahan bersebelahan tidak terbuang)
        max_offences = 2 if is_passive_vape else max(top_k, 4)
        if scored_offences:
            top_score = scored_offences[0][0]
            focused_offences = [
                item
                for idx, item in enumerate(scored_offences[:max_offences])
                if idx == 0 or (item[0] >= 1.8 and item[0] >= top_score * 0.35)
            ]
        else:
            focused_offences = []

        top_offences = [
            {
                **off,
                "canonical_akta_code": canonical_akta_code_for_statute(off["statute_id"]),
                "match_score": round(sc, 2),
                "element_evaluation": ev,
            }
            for sc, off, ev in focused_offences
        ]

        # c) Teks penuh verbatim daripada `statute_sections_verbatim` — 2 SLOT BERASINGAN (TIDAK LAGI SALING MEMBUNUH!)
        sec_map = {s["doc_id"]: s for s in self.statute_sections_verbatim}
        verbatim_hits: List[Dict[str, Any]] = []
        seen_doc_ids: set[str] = set()
        allowed_scope_defs = {
            "AKTA_852_PERINTAH_LARANGAN_2024__JADUAL_PERTAMA",
            "AKTA_852_PERINTAH_LARANGAN_2024__P2",
            "AKTA_852_PERATURAN_TANDA_2024__JADUAL_PERTAMA",
            "AKTA_852_PERATURAN_TANDA_2024__P2",
        }

        # SLOT A: Seksyen verbatim yang dipautkan terus oleh 3 kesalahan calon teratas
        for off in top_offences[:3]:
            linked_doc_ids = list(off.get("source_section_doc_ids") or [])
            if off.get("offence_id") in ("AKTA_852_S16_2", "AKTA_852_S18_1"):
                for extra_did in (
                    "AKTA_852_PERINTAH_LARANGAN_2024__JADUAL_PERTAMA",
                    "AKTA_852_PERINTAH_LARANGAN_2024__P2",
                ):
                    if extra_did not in linked_doc_ids:
                        linked_doc_ids.append(extra_did)
            if off.get("offence_id") == "AKTA_852_S18_1":
                for extra_18 in (
                    "AKTA_852_PERATURAN_TANDA_2024__P2",
                    "AKTA_852_PERATURAN_TANDA_2024__JADUAL_PERTAMA",
                ):
                    if extra_18 not in linked_doc_ids:
                        linked_doc_ids.append(extra_18)

            for did in linked_doc_ids:
                if did in sec_map and did not in seen_doc_ids:
                    s_obj = sec_map[did]
                    if not asks_definition and did not in allowed_scope_defs and is_non_offence_or_definition_section(s_obj):
                        continue
                    seen_doc_ids.add(did)
                    verbatim_hits.append(
                        {
                            "doc_id": s_obj["doc_id"],
                            "statute_id": s_obj["statute_id"],
                            "akta_code": canonical_akta_code_for_statute(s_obj["statute_id"]),
                            "section_code": s_obj["section_code"],
                            "section_heading": s_obj["section_heading"],
                            "verbatim_text_bm": s_obj["verbatim_text_bm"],
                            "is_offence_provision": bool(s_obj.get("is_offence_provision")),
                            "score": 0.96,
                        }
                    )

        # Jika kes pelajar/OBD di bawah Akta 852, masukkan rujukan Akta 611 (S.83 & S.15) jika tersedia
        if has_minor_signal and allowed_sids and "AKTA_611" in allowed_sids and not is_passive_vape:
            for ak611_did in ("AKTA_611__S83", "AKTA_611__S15"):
                if ak611_did in sec_map and ak611_did not in seen_doc_ids:
                    s_obj = sec_map[ak611_did]
                    seen_doc_ids.add(ak611_did)
                    verbatim_hits.append(
                        {
                            "doc_id": s_obj["doc_id"],
                            "statute_id": s_obj["statute_id"],
                            "akta_code": canonical_akta_code_for_statute(s_obj["statute_id"]),
                            "section_code": s_obj["section_code"],
                            "section_heading": s_obj["section_heading"],
                            "verbatim_text_bm": s_obj["verbatim_text_bm"],
                            "is_offence_provision": bool(s_obj.get("is_offence_provision")),
                            "score": 0.90,
                        }
                    )

        # SLOT B (DIJAMIN SENTIASA AKTIF): Carian bebas berasaskan IDF + bonus padanan nombor seksyen tepat (+8.0) + bonus niat rujukan silang
        explicit_sec_mentions = {
            m.upper()
            for m in re.findall(r"\b(?:seksyen|peraturan|section|regulation|s\.|p\.)\s*(\d+[A-Za-z]{0,2})\b", q_raw, re.I)
        }
        cross_statute_intent_boosts: Dict[str, float] = {}
        # Akta 388 (Akta Tafsiran 1948 dan 1967) — pastikan peruntukan substantif mengatasi tajuk/jadual
        if re.search(r"\b(?:hari\s+bersih|kiraan\s+hari|pengiraan.*hari|kira.*hari|cuti\s+umum|hujung\s+minggu|had\s+masa|tempoh\s+\d+\s+hari|computation\s+of\s+time)\b", q_low):
            cross_statute_intent_boosts["AKTA_388__S54"] = 9.5
        if re.search(r"\b(?:pos\s+berdaftar|serahan\s+(?:notis|dokumen|sijil|melalui\s+pos|pos)|registered\s+post|service\s+by\s+post)\b", q_low):
            cross_statute_intent_boosts["AKTA_388__S12"] = 9.5
        if re.search(r"\b(?:tafsiran\s+bermaksud|tujuan\s+akta|maksud\s+akta|purposive|17a)\b", q_low):
            cross_statute_intent_boosts["AKTA_388__S17A"] = 9.0
        if re.search(r"\b(?:mansuh|dimansuhkan|pemansuhan|repeal|saving|ppkht\s+2004)\b", q_low):
            cross_statute_intent_boosts["AKTA_388__S30"] = 8.5
        if re.search(r"\b(?:batal\s+perintah|ubah\s+perintah|pinda\s+perintah|tarik\s+balik\s+perintah|revoke|vary)\b", q_low):
            cross_statute_intent_boosts["AKTA_388__S47"] = 9.0
        if re.search(r"\b(?:hukuman\s+berganda|dihukum\s+dua\s+kali|double\s+jeopardy|punished\s+twice)\b", q_low):
            cross_statute_intent_boosts["AKTA_388__S59"] = 9.0
        # Akta 92 (Akta Mahkamah Rendah 1948) — pastikan S.63, S.64, S.85, S.87, S.88 mengatasi Jadual/sivil
        if re.search(r"\b(?:mahkamah\s+majistret|mahkamah\s+sesyen|bidang\s+kuasa\s+mahkamah|had\s+hukuman|had\s+denda|mahkamah\s+mana|sessions\s+court|first\s+class\s+magistrate)\b", q_low):
            cross_statute_intent_boosts["AKTA_92__S63"] = 9.0
            cross_statute_intent_boosts["AKTA_92__S64"] = 9.0
            cross_statute_intent_boosts["AKTA_92__S85"] = 8.5
            cross_statute_intent_boosts["AKTA_92__S87"] = 9.5
            if re.search(r"\b(?:kelas\s+kedua|second\s+class|majistret\s+2)\b", q_low):
                cross_statute_intent_boosts["AKTA_92__S88"] = 9.5
        # Akta 344 (Akta Polis 1967) — bantuan/iringan operasi kebersihan & kuarantin
        if re.search(r"\b(?:bantuan\s+polis|iringan\s+polis|bantuan\s+pdrm|iringan\s+pdrm|operasi\s+kuarantin|sanitary\s+law|police\s+assistance)\b", q_low):
            cross_statute_intent_boosts["AKTA_344__S20"] = 9.5
        # Akta 593 (KTJ) — seksyen prosedur teras PPKP
        if re.search(r"\b(?:laporan\s+polis|repot\s+polis|seizable|lazim\s+tangkap|first\s+information)\b", q_low):
            cross_statute_intent_boosts["AKTA_593__S107"] = 8.5
            cross_statute_intent_boosts["AKTA_593__S108"] = 8.0
        if re.search(r"\b(?:pelupusan\s+barang|lupus\s+sitaan|lelong\s+barang|barang\s+kes\s+mudah\s+rosak|407a)\b", q_low):
            cross_statute_intent_boosts["AKTA_593__S407"] = 8.5
            cross_statute_intent_boosts["AKTA_593__S407A"] = 9.0
        if re.search(r"\b(?:penzahiran\s+dokumen|serah.*dokumen.*tertuduh|51a)\b", q_low):
            cross_statute_intent_boosts["AKTA_593__S51A"] = 9.0

        scored_secs: List[Tuple[float, Dict[str, Any]]] = []
        for s_obj in self.statute_sections_verbatim:
            did = s_obj["doc_id"]
            if did in seen_doc_ids:
                continue
            if not asks_definition and did not in allowed_scope_defs and is_non_offence_or_definition_section(s_obj):
                continue
            sid = s_obj["statute_id"]
            c_act = canonical_akta_code_for_statute(sid)
            if allowed_sids is not None and sid not in allowed_sids:
                continue
            if akta_hint and akta_hint not in ("", "Semua"):
                hint_canon = canonical_akta_code_for_statute(akta_hint)
                is_attached_support = allowed_sids is not None and sid in allowed_sids and sid in support_sids
                if (
                    akta_hint.lower() != c_act.lower()
                    and hint_canon.lower() != c_act.lower()
                    and not re.search(rf"(?<!\w){re.escape(akta_hint.lower())}(?!\w)", sid.lower())
                    and not is_attached_support
                ):
                    continue
            s_toks = self._section_token_cache.get(did)
            if s_toks is None:
                s_toks = {t.lower() for t in TOKEN_RE.findall(s_obj["verbatim_text_bm"].lower()) if len(t) >= 2}
            idf_exact = sum(sec_idf.get(t, 1.0) for t in (exact_tokens & s_toks))
            idf_exp = 0.55 * sum(sec_idf.get(t, 1.0) for t in (expanded_tokens & s_toks))
            offence_bonus = 0.5 if s_obj.get("is_offence_provision") else 0.0
            sc_code_clean = re.sub(r"^(?:Peraturan|Seksyen|Section|Regulation)\s+", "", str(s_obj.get("section_code") or "").strip(), flags=re.I).upper()
            sec_exact_boost = 8.0 if (sc_code_clean and sc_code_clean in explicit_sec_mentions) else 0.0
            intent_boost = cross_statute_intent_boosts.get(did, 0.0)
            combined_sc = idf_exact + idf_exp + offence_bonus + sec_exact_boost + intent_boost
            if combined_sc >= 1.5:
                scored_secs.append((combined_sc, s_obj))

        scored_secs.sort(key=lambda x: x[0], reverse=True)
        # Sentiasa tambah sehingga 6 seksyen terbaik daripada carian bebas supaya soalan rujukan silang mendapat kedua-dua akta KKM & sokongan
        min_free_slots = 2 if is_passive_vape else 6
        for sc, s_obj in scored_secs[:min_free_slots]:
            seen_doc_ids.add(s_obj["doc_id"])
            verbatim_hits.append(
                {
                    "doc_id": s_obj["doc_id"],
                    "statute_id": s_obj["statute_id"],
                    "akta_code": canonical_akta_code_for_statute(s_obj["statute_id"]),
                    "section_code": s_obj["section_code"],
                    "section_heading": s_obj["section_heading"],
                    "verbatim_text_bm": s_obj["verbatim_text_bm"],
                    "is_offence_provision": bool(s_obj.get("is_offence_provision")),
                    "score": round(min(0.95, max(0.35, sc / 15.0)), 4),
                }
            )

        # d) Pautan Wajib Akta Induk <-> Akta Pindaan & Peraturan Kompaun Terkini (AMENDMENT_COMPANIONS)
        triggered_parents: List[str] = []
        active_sids = {str(o.get("statute_id") or "") for o in top_offences} | {
            str(v.get("statute_id") or "") for v in verbatim_hits
        }
        hint_low = (akta_hint or "").strip().lower()
        if (
            "AKTA_342" in active_sids
            or any(s.startswith("AKTA_342") for s in active_sids)
            or "342" in hint_low
            or "akta 342" in q_low
            or "penyakit berjangkit" in q_low
            or "apppb" in q_low
            or "a1742" in q_low
            or "139/2025" in q_low
        ):
            triggered_parents.append("AKTA_342")
        if (
            "AKTA_281" in active_sids
            or "PPKM_2009" in active_sids
            or "PPM_1985" in active_sids
            or "281" in hint_low
            or "akta 281" in q_low
            or "akta makanan" in q_low
            or "a1702" in q_low
        ):
            triggered_parents.append("AKTA_281")

        # Kumpulkan nombor seksyen rujukan dalam soalan & konteks induk untuk pilih seksyen pindaan paling relevan
        referenced_sec_nums = {
            m.upper() for m in re.findall(r"\b(\d+[A-Za-z]{0,2})\b", q_raw)
        } | {
            str(v.get("section_code") or "").strip().upper() for v in verbatim_hits
        }

        amendment_companions_applied: List[str] = []
        amendment_directives: List[str] = []
        for parent_sid in triggered_parents:
            comp_cfg = AMENDMENT_COMPANIONS.get(parent_sid)
            if not comp_cfg:
                continue
            directive = str(comp_cfg.get("mandatory_directive_bm") or "").strip()
            if directive and directive not in amendment_directives:
                amendment_directives.append(directive)

            priority_map: Dict[str, Tuple[str, ...]] = comp_cfg.get("priority_sections") or {}
            for comp_sid in comp_cfg.get("companion_statute_ids") or ():
                comp_secs = [s for s in self.statute_sections_verbatim if s["statute_id"] == comp_sid]
                if not comp_secs:
                    continue
                if comp_sid not in amendment_companions_applied:
                    amendment_companions_applied.append(comp_sid)

                prio_codes = [c.upper() for c in priority_map.get(comp_sid, ())]
                scored_comp: List[Tuple[float, Dict[str, Any]]] = []
                for cs in comp_secs:
                    sc_code_up = str(cs.get("section_code") or "").strip().upper()
                    heading_up = str(cs.get("section_heading") or "").upper()
                    s_toks = self._section_token_cache.get(cs["doc_id"])
                    if s_toks is None:
                        s_toks = {
                            t.lower()
                            for t in TOKEN_RE.findall(cs["verbatim_text_bm"].lower())
                            if len(t) >= 2
                        }
                    c_score = float(len(q_tokens & s_toks)) * 0.4
                    if sc_code_up in prio_codes:
                        c_score += 3.0 + (len(prio_codes) - prio_codes.index(sc_code_up)) * 0.25
                    for ref_n in referenced_sec_nums:
                        if ref_n and (sc_code_up == ref_n or f"SEKSYEN {ref_n}" in heading_up):
                            c_score += 4.5
                            break
                    if comp_sid == "AKTA_342_PINDAAN_2025" and any(
                        kw in q_low for kw in ("kompaun", "denda", "penalti", "hukuman", "maksimum", "korporat", "syarikat")
                    ):
                        if sc_code_up in ("24", "25", "22A"):
                            c_score += 5.0
                    scored_comp.append((c_score, cs))

                scored_comp.sort(key=lambda x: x[0], reverse=True)
                max_take = 3 if comp_sid.endswith("_2025") or comp_sid.endswith("_2024") else 2
                if comp_sid == "AKTA_342_PERATURAN_KOMPAUN_2025":
                    max_take = 2
                for c_sc, cs in scored_comp[:max_take]:
                    if cs["doc_id"] in seen_doc_ids:
                        continue
                    seen_doc_ids.add(cs["doc_id"])
                    verbatim_hits.append(
                        {
                            "doc_id": cs["doc_id"],
                            "statute_id": cs["statute_id"],
                            "akta_code": canonical_akta_code_for_statute(cs["statute_id"]),
                            "section_code": cs["section_code"],
                            "section_heading": cs["section_heading"],
                            "verbatim_text_bm": cs["verbatim_text_bm"],
                            "score": round(min(0.98, max(0.88, 0.88 + c_sc * 0.01)), 4),
                            "is_amendment_companion": True,
                        }
                    )

        # Bina katalog ringkas 1-baris semua kesalahan dalam domain aktif supaya AI sentiasa nampak pilihan penuh Akta
        domain_catalog_lines: List[str] = []
        catalog_sids = allowed_sids or active_sids
        if catalog_sids:
            for off in self.master_offences_matrix:
                if str(off.get("statute_id") or "") not in catalog_sids:
                    continue
                if len(str(off.get("offence_title") or "").strip()) < 16:
                    continue
                c_act = canonical_akta_code_for_statute(str(off.get("statute_id") or ""))
                comp_i = off.get("compound_info") or {}
                comp_tag = (
                    f"BOLEH KOMPAUN (maks RM{comp_i.get('max_compound_rm')})"
                    if comp_i.get("is_compoundable") and comp_i.get("max_compound_rm")
                    else ("BOLEH KOMPAUN" if comp_i.get("is_compoundable") else "TIDAK BOLEH KOMPAUN / BUKA IP")
                )
                domain_catalog_lines.append(
                    f"- [{off['offence_id']}] {off['offence_section']} ({c_act}) | Sasaran: {off.get('target_offender')} | "
                    f"{comp_tag} | {str(off.get('offence_title') or '')[:140]}"
                )
                if len(domain_catalog_lines) >= 42:
                    break

        # Bina blok <STATUTORY_CONTEXT> untuk LLM Closed-Book
        ctx_parts: List[str] = ["<STATUTORY_CONTEXT>"]
        ctx_parts.append(f"STATUTE_LIBRARY_VERSION: {self.statute_library_version}")
        if amendment_directives:
            ctx_parts.append("\n[ARAHAN KERAS PINDAAN STATUTORI — WAJIB UTAMAKAN TEKS PINDAAN TERKINI]:")
            for directive in amendment_directives:
                ctx_parts.append(f"- {directive}")
        if repealed_matches:
            ctx_parts.append("\n[SENARAI HITAM PERUNTUKAN DIMANSUHKAN / DISEKAT]:")
            for rm in repealed_matches:
                ctx_parts.append(
                    f"- {rm['repealed_statute_or_section']}: {rm['warning_message_bm']} ({rm['key_differences_note']})"
                )
        if domain_catalog_lines:
            ctx_parts.append("\n[KATALOG RINGKAS SEMUA KESALAHAN DOMAIN — PILIH SEKSYEN YANG PALING TEPAT DENGAN FAKTA SOALAN]:")
            ctx_parts.extend(domain_catalog_lines)
        if top_offences:
            ctx_parts.append("\n[MATRIKS KESALAHAN CALON UTAMA & UNSUR MANDATORI (master_offences_matrix)]:")
            for off in top_offences:
                els = "; ".join(
                    f"Unsur #{e['element_no']}: {e['description']} [Status: {e['status']}]"
                    for e in (off["element_evaluation"].get("element_evaluations") or [])
                )
                traps = " | ".join(off.get("explicit_exclusions_and_traps") or [])
                ctx_parts.append(
                    f"- [{off['offence_id']}] {off['offence_section']} ({off['canonical_akta_code']}): {off['offence_title']}\n"
                    f"  Hukuman: {off['penalty_section']} -> {off['penalty_first_offence']['verbatim_penalty']}\n"
                    f"  Kompaun: {off['compound_info']['compound_amount_or_limit']}\n"
                    f"  Semakan Unsur: {els}\n"
                    f"  Pengecualian & Perangkap (BUKAN Kesalahan): {traps}"
                )
        if verbatim_hits:
            ctx_parts.append("\n[TEKS PENUH VERBATIM WARTA (statute_sections_verbatim)]:")
            total_v_chars = 0
            for vh in verbatim_hits:
                comp_tag = " [PINDAAN TERKINI — UTAMAKAN]" if vh.get("is_amendment_companion") else ""
                v_body = str(vh["verbatim_text_bm"])
                # Kekalkan penuh bagi semua seksyen penting (termasuk Jadual Pertama P.U. (A) 257/2024 & 258/2024)
                if len(v_body) > 5500 and total_v_chars > 18000:
                    v_body = v_body[:5500] + "\n... [ringkasan teks panjang dipendekkan bagi ruang konteks]"
                total_v_chars += len(v_body)
                ctx_parts.append(
                    f"--- {vh['doc_id']} ({vh['akta_code']} | {vh['section_code']} - {vh['section_heading']}){comp_tag} ---\n"
                    f"{v_body}"
                )
        ctx_parts.append("</STATUTORY_CONTEXT>")

        return {
            "statute_library_version": self.statute_library_version,
            "unindexed_statute": unindexed_hit,
            "repealed_matches": repealed_matches,
            "candidate_offences": top_offences,
            "verbatim_sections": verbatim_hits,
            "amendment_companions_applied": amendment_companions_applied,
            "amendment_directives": amendment_directives,
            "statutory_context_block": "\n".join(ctx_parts),
        }


_legal_library_instance: Optional[ClosedBookLegalLibrary] = None


def get_legal_library() -> ClosedBookLegalLibrary:
    global _legal_library_instance
    if _legal_library_instance is None:
        _legal_library_instance = ClosedBookLegalLibrary()
    return _legal_library_instance
