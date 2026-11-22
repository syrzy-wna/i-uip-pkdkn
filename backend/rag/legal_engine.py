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
PARSER_VERSION = "3.4-agc-gazette-pdf"

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
        "source_section_doc_ids": ["AKTA_852__S18", "AKTA_852_PERATURAN_TANDA_2024__P2", "AKTA_852__S47", "AKTA_852__S48", "AKTA_852_PERATURAN_KOMPAUN_2024__P2"],
        "verified_status": "DRAFT_PENDING_REVIEW",
    },
    # ---------------- AKTA 281 & PPKM 2009 & PPM 1985 ----------------
    {
        "offence_id": "AKTA_281_S11_2",
        "statute_id": "AKTA_281",
        "offence_section": "Seksyen 11(2)",
        "read_together_with": ["Seksyen 11(1) Akta Makanan 1983", "Seksyen 33A Akta Makanan 1983 (jika syarikat)"],
        "offence_title": "Gagal mematuhi Perintah Penutupan Premis Makanan Tidak Suci di bawah Seksyen 11(1) Akta Makanan 1983",
        "target_offender": "TUAN_PUNYA_PREMIS",
        "mandatory_elements": [
            {
                "element_no": 1,
                "description": "Perintah Penutupan Premis Makanan Tidak Suci di bawah Seksyen 11(1) Akta Makanan 1983 telah dikeluarkan secara sah dan diserahkan kepada tuan punya/pemunya/penghuni premis.",
                "must_prove": "Salinan asal Perintah Penutupan Seksyen 11 bertandatangan terima & gambar tampalan notis penutupan.",
            },
            {
                "element_no": 2,
                "description": "OKT mengingkari perintah tersebut dengan terus membuka atau menjalankan operasi premis makanan dalam tempoh penutupan berkuat kuasa.",
                "must_prove": "Gambar pemeriksaan susulan yang menunjukkan premis masih beroperasi/menjual makanan semasa tempoh perintah penutupan + rakaman S.112 saksi.",
            },
        ],
        "explicit_exclusions_and_traps": [
            "JANGAN tuduh pemilik di bawah Seksyen 11(2) Akta 281 jika pemilik PATUH menutup premis! Seksyen 11(1) ialah perintah pentadbiran menutup premis; kesalahan kebersihan premis itu sendiri didakwa di bawah Peraturan 11(1) atau Peraturan 34(1) PPKM 2009.",
            "Pemilik/pekerja masuk ke dalam premis semata-mata untuk menjalankan kerja pembersihan tanpa menjual/menyediakan makanan kepada pelanggan BUKAN kesalahan mengingkari perintah tutup S.11(2).",
        ],
        "penalty_section": "Seksyen 11(2) Akta Makanan 1983 [Akta 281]",
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
            "Bukti serahan sah Perintah Penutupan Seksyen 11(1)",
        ],
        "mandatory_exhibits": [
            "Borang Pemeriksaan Premis Makanan (KMM) & Perintah Penutupan Seksyen 11 bertandatangan terima",
            "Gambar foto tampalan Notis Tutup & gambar bukti premis masih beroperasi semasa tempoh tutup + Sijil S.90A(2)",
            "Carian Rasmi SSM + Sijil S.90A & Izin Mendakwa TPR S.32A",
        ],
        "charge_sheet_template_bm": (
            "Bahawa kamu, pada [TARIKH], jam lebih kurang [MASA], bertempat di [TEMPAT_KEJADIAN], "
            "di dalam Daerah [DAERAH], di dalam Negeri [NEGERI], telah didapati gagal mematuhi Perintah Penutupan Premis Makanan Tidak Suci "
            "yang dikeluarkan di bawah Seksyen 11(1) Akta Makanan 1983; dan oleh yang demikian kamu telah melakukan suatu kesalahan "
            "di bawah Seksyen 11(2) Akta Makanan 1983 [Akta 281] dan boleh dihukum di bawah seksyen yang sama."
        ),
        "source_section_doc_ids": ["AKTA_281__S11", "AKTA_281__S32A"],
        "verified_status": "DRAFT_PENDING_REVIEW",
    },
    {
        "offence_id": "AKTA_281_S13_1",
        "statute_id": "AKTA_281",
        "offence_section": "Seksyen 13(1)",
        "read_together_with": ["Seksyen 19 Akta Makanan 1983", "Seksyen 33A Akta Makanan 1983 (jika syarikat)"],
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
            "WAJIB serahkan salinan Perakuan Juruanalisis Makanan (Seksyen 19) kepada OKS sekurang-kurangnya 10 HARI JELAS sebelum tarikh perbicaraan (Seksyen 19(2) Akta 281) — jika gagal, perakuan makmal tidak boleh diterima!",
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
            "Perakuan Juruanalisis Makanan Seksyen 19 Akta 281 + Serahan 10 hari jelas sebelum bicara [S.19(2)]",
            "Izin Mendakwa Bertulis Pendakwa Raya di bawah Seksyen 32A Akta 281",
        ],
        "mandatory_exhibits": [
            "Sampel makanan berlak rasmi KKM + rekod rantaian stor",
            "Perakuan Juruanalisis Makanan Seksyen 19 Akta 281 + bukti serahan 10 hari jelas kepada OKS",
            "Resit pembelian, Laporan Pengadu (FIR), laporan perubatan mangsa & Izin Mendakwa TPR S.32A",
        ],
        "charge_sheet_template_bm": (
            "Bahawa kamu, pada [TARIKH], jam lebih kurang [MASA], bertempat di [TEMPAT_KEJADIAN], "
            "di dalam Daerah [DAERAH], di dalam Negeri [NEGERI], telah didapati menjual/menyediakan makanan iaitu [NAMA_MAKANAN] "
            "yang mengandungi bahan yang memudaratkan kesihatan; dan oleh yang demikian kamu telah melakukan suatu kesalahan "
            "di bawah Seksyen 13(1) Akta Makanan 1983 [Akta 281] dan boleh dihukum di bawah seksyen yang sama."
        ),
        "source_section_doc_ids": ["AKTA_281__S13", "AKTA_281__S19", "AKTA_281__S32A"],
        "verified_status": "DRAFT_PENDING_REVIEW",
    },
    {
        "offence_id": "AKTA_281_S13B_1",
        "statute_id": "AKTA_281",
        "offence_section": "Seksyen 13B(1)",
        "read_together_with": ["Seksyen 13B(2)(d)/(e) Akta Makanan 1983"],
        "offence_title": "Menyediakan atau menjual makanan yang diaduk (mengandungi benda asing / kotor / busuk / bangkai serangga)",
        "target_offender": "PENJUAL_PENGILANG",
        "mandatory_elements": [
            {
                "element_no": 1,
                "description": "OKT menyediakan atau menjual apa-apa makanan.",
                "must_prove": "Sampel makanan, resit pembelian dan rakaman S.112 pengadu/pembeli.",
            },
            {
                "element_no": 2,
                "description": "Makanan tersebut diaduk mengikut Seksyen 13B(2) (cth. mengandungi benda asing seperti paku, kaca, dawai, bangkai lipas atau bahan kotor/reput).",
                "must_prove": "Eksibit fizikal makanan berlak KKM + Perakuan Juruanalisis Makanan S.19 + gambar foto + Sijil S.90A(2).",
            },
        ],
        "explicit_exclusions_and_traps": [
            "Kes Seksyen 13B(1) TIDAK BOLEH ditawarkan kompaun — wajib buka IP dan dapatkan Izin Mendakwa TPR Seksyen 32A.",
            "Wajib patuhi serahan Perakuan Juruanalisis S.19 sekurang-kurangnya 10 hari jelas sebelum bicara.",
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
            "Perakuan Juruanalisis Makanan Seksyen 19 Akta 281 + Serahan 10 hari jelas [S.19(2)]",
            "Izin Mendakwa Bertulis Pendakwa Raya di bawah Seksyen 32A Akta 281",
        ],
        "mandatory_exhibits": [
            "Sampel makanan & benda asing yang dilak KKM",
            "Perakuan Juruanalisis Makanan Seksyen 19 Akta 281 + bukti serahan 10 hari kepada OKS",
            "Gambar foto berwarna + Sijil S.90A(2), Resit Pembelian & Rakaman S.112 Pengadu",
        ],
        "charge_sheet_template_bm": (
            "Bahawa kamu, pada [TARIKH], jam lebih kurang [MASA], bertempat di [TEMPAT_KEJADIAN], "
            "di dalam Daerah [DAERAH], di dalam Negeri [NEGERI], telah didapati menjual makanan yang diaduk iaitu [NAMA_MAKANAN] "
            "yang mengandungi benda asing; dan oleh yang demikian kamu telah melakukan suatu kesalahan "
            "di bawah Seksyen 13B(1) dibaca bersama Seksyen 13B(2)(e) Akta Makanan 1983 [Akta 281] yang boleh dihukum di bawah Seksyen 13B(4) Akta yang sama."
        ),
        "source_section_doc_ids": ["AKTA_281__S13B", "AKTA_281__S19", "AKTA_281__S32A"],
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
        "offence_section": "Peraturan 11(1) / Peraturan 34(1) PPKM 2009",
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
                "description": "Gagal menyelenggara atau mengekalkan premis makanan dalam keadaan bersih, kemas dan bebas daripada makhluk perosak (lipas, lalat, tikus).",
                "must_prove": "Gambar foto bukti kekotoran/najis tikus/lipas hidup di kawasan penyediaan/stor makanan + Sijil S.90A(2) + Pelan Lakar.",
            },
        ],
        "explicit_exclusions_and_traps": [
            "JANGAN hantar najis tikus ke makmal MKAK untuk analisis kimia — najis tikus dibuktikan dengan gambar foto berkapsyen + keterangan pemerhatian pegawai pemeriksa!",
            "Bagi kes wabak HFMD di Taska/Tadika (bukan premis makanan), JANGAN guna Seksyen 11 Akta 281 atau Peraturan 11 PPKM 2009 — gunakan Seksyen 18(1)(d) Akta 342!",
        ],
        "penalty_section": "Peraturan 11(2) / Peraturan 34(2) PPKM 2009 [P.U. (A) 95/2009]",
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
            "dan oleh yang demikian kamu telah melakukan suatu kesalahan di bawah Peraturan 11(1) [atau Peraturan 34(1)] Peraturan-Peraturan Kebersihan Makanan 2009 [P.U. (A) 95/2009] "
            "yang boleh dihukum di bawah Peraturan 11(2) [atau Peraturan 34(2)] Peraturan yang sama."
        ),
        "source_section_doc_ids": ["PPKM_2009__P11", "PPKM_2009__P34", "AKTA_281__S11", "AKTA_281__S32B", "AKTA_281__S33"],
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
            "Individu di premis yang tidak terlibat langsung dengan pengendalian makanan atau permukaan sentuhan makanan (cth. pelanggan atau penghantar stok luar yang tidak menyentuh makanan terbuka) bukan pengendali makanan.",
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
            "Jika mahu menuduh majikan/pemunya premis kerana membenarkan pekerja tanpa suntikan tifoid bekerja, gunakan Peraturan 11(1)(b) atau Peraturan 31(2) PPKM 2009.",
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
        "offence_section": "Peraturan 14(9) / Peraturan 14(7) PPM 1985",
        "read_together_with": ["Seksyen 4(1)(f) Akta Makanan 1983", "Peraturan 397 PPM 1985"],
        "offence_title": "Menjual atau mendedahkan untuk jualan makanan yang telah tamat tarikh luput (expired) atau mengubah/memadam penandaan tarikh luput",
        "target_offender": "PENJUAL_PENGILANG",
        "mandatory_elements": [
            {
                "element_no": 1,
                "description": "OKT menjual, mengimport atau mendedahkan untuk jualan bungkusan makanan berlabel tarikh akhir penggunaan/tarikh luput.",
                "must_prove": "Bungkusan makanan yang disita di rak jualan melalui Seksyen 4(1)(f) Akta Makanan 1983.",
            },
            {
                "element_no": 2,
                "description": "Tarikh akhir penggunaan pada bungkusan makanan telah luput pada tarikh pemeriksaan, atau penandaan tarikh telah diubah/dipadam.",
                "must_prove": "Gambar jarak dekat cetakan tarikh luput pada bungkusan berbanding tarikh pemeriksaan + Sijil S.90A(2).",
            },
        ],
        "explicit_exclusions_and_traps": [
            "Stok makanan tamat tempoh yang telah diasingkan di dalam stor pelupusan khas berlabel jelas 'UNTUK PELUPUSAN / TIDAK UNTUK DIJUAL' dan tidak didedahkan di ruang jualan perlu disahkan fakta pendedahan untuk jualannya.",
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
            "compound_amount_or_limit": "Sita stok di bawah S.4(1)(f) Akta 281 + Notis S.32B atau Buka IP",
            "max_compound_rm": 5000,
            "payment_days": 14,
            "notice_section": "Seksyen 32B Akta Makanan 1983",
        },
        "special_legal_requirements": ["Senarai Sitaan Seksyen 4(1)(f) Akta Makanan 1983", "Sijil Seksyen 90A(2)"],
        "mandatory_exhibits": [
            "Bungkusan makanan tamat tarikh luput yang disita & dilak KKM + Borang Sitaan S.4(1)(f)",
            "Gambar foto jarak dekat tarikh luput pada bungkusan + Sijil S.90A(2) & Carian SSM",
        ],
        "charge_sheet_template_bm": (
            "Bahawa kamu, pada [TARIKH], jam lebih kurang [MASA], bertempat di [TEMPAT_KEJADIAN], "
            "di dalam Daerah [DAERAH], di dalam Negeri [NEGERI], telah didapati mendedahkan untuk jualan makanan berbungkus yang telah melampaui tarikh akhir penggunaan; "
            "dan oleh yang demikian kamu telah melakukan suatu kesalahan di bawah Peraturan 14(9) Peraturan-Peraturan Makanan 1985 "
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
        "read_together_with": ["Seksyen 23 Akta 154"],
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
        ],
        "penalty_section": "Seksyen 21 dibaca bersama Seksyen 23(a) Akta 154",
        "penalty_first_offence": {
            "max_fine_rm": 10000,
            "max_jail_months": 24,
            "other_orders": None,
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
            "compound_amount_or_limit": "Kes menghalang penjawat awam — Buka IP Terus & Laporan Polis",
            "max_compound_rm": None,
            "payment_days": None,
            "notice_section": None,
        },
        "special_legal_requirements": ["Laporan Polis", "Rakaman S.112 KTJ saksi pasukan penguat kuasa"],
        "mandatory_exhibits": [
            "Laporan Polis & Diari Siasatan pasukan kawalan vektor",
            "Gambar lokasi kejadian + Sijil S.90A(2) & Salinan Kad Kuasa PPKP",
            "Rakaman percakapan S.112 KTJ PPKP & Pembantu Kesihatan Awam",
        ],
        "charge_sheet_template_bm": (
            "Bahawa kamu, pada [TARIKH], jam lebih kurang [MASA], bertempat di [TEMPAT_KEJADIAN], "
            "di dalam Daerah [DAERAH], di dalam Negeri [NEGERI], telah didapati menghalang seorang pegawai diberi kuasa daripada menjalankan tugasnya "
            "di bawah Akta Pemusnahan Serangga Pembawa Penyakit 1975; dan oleh yang demikian kamu telah melakukan suatu kesalahan "
            "di bawah Seksyen 21 Akta 154 yang boleh dihukum di bawah Seksyen 23(a) Akta yang sama."
        ),
        "source_section_doc_ids": ["AKTA_154__S21", "AKTA_154__S23"],
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
        if raw in ("593", "AKTA593", "KTJ"):
            return "AKTA_593"
        if raw in ("56", "AKTA56"):
            return "AKTA_56"
        if raw in ("611", "AKTA611"):
            return "AKTA_611"
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
    if "90a" in low or "akta 56" in low or "keterangan 1950" in low or "evidence act 1950" in low:
        return "AKTA_56"
    if "611" in low or "kanak-kanak 2001" in low or "child act 2001" in low:
        return "AKTA_611"
    clean_stem = re.sub(r"[^A-Z0-9_]+", "_", Path(filename).stem.upper()).strip("_")
    return clean_stem or "AKTA_UMUM"


def canonical_akta_code_for_statute(statute_id: str) -> str:
    sid = (statute_id or "").upper()
    if "852" in sid:
        return "Akta 852"
    if "281" in sid or "PPKM" in sid or "PPM" in sid:
        return "Akta 281"
    if "154" in sid:
        return "Akta 154"
    if "342" in sid:
        return "Akta 342"
    if "593" in sid or "KTJ" in sid:
        return "Akta 593"
    if "56" in sid:
        return "Akta 56"
    if "611" in sid:
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
            r"|Makanan(?:\s+\(Pindaan\))?|Kanak-Kanak|Keterangan|Criminal\s+Procedure\s+Code|Evidence)(?:\s+\d{1,3})?$",
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
    num_inline_re = re.compile(r"^\s*(\d+[A-Za-z]{0,2})\s*\.(?:\s+|(?=\())(.+)$")
    num_alone_re = re.compile(r"^\s*(\d+[A-Za-z]{0,2})\s*\.\s*$")
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
                cur = [current_part_num, current_part_title, sec_code, sec_head[:160], [stripped]]
                pending_heading_lines = []
                continue

            # Format nombor Warta AGC: "17. (1) Tiada..." atau "31.(1)..." atau "17.\n(1)..." atau "5 . Pengarah..."
            m_in = num_inline_re.match(stripped)
            m_al = num_alone_re.match(stripped) if not m_in else None
            matched_num: Optional[str] = None
            rest_text = ""
            if m_in:
                num_str = m_in.group(1)
                rest_text = m_in.group(2).strip()
                base_int = int(re.match(r"^\d+", num_str).group(0))  # type: ignore[union-attr]
                if 1 <= base_int <= 550 and re.match(r"^(?:\(\d+[A-Za-z]?\)|[A-Z“\"])", rest_text):
                    matched_num = num_str.upper()
                    last_sec_int = base_int
            elif m_al and is_agc_pdf:
                num_str = m_al.group(1)
                base_int = int(re.match(r"^\d+", num_str).group(0))  # type: ignore[union-attr]
                nxt = _next_nonempty(idx)
                prv = _prev_nonempty(idx)
                jump_ok = (last_sec_int == 0) or (base_int <= last_sec_int + 30)
                if (
                    1 <= base_int <= 550
                    and jump_ok
                    and not prev_ref_tail_re.search(prv)
                    and re.match(r"^(?:\(\d+[A-Za-z]?\)|[A-Z“\"])", nxt)
                ):
                    matched_num = num_str.upper()
                    last_sec_int = base_int

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
    "jika", "tidak", "tiada", "boleh", "hendaklah", "telah", "ini", "itu",
    "kepada", "ada", "akan", "sudah", "sedang", "masih", "sahaja", "saja",
    "nak", "bolehkah", "adakah", "apakah", "bagaimana", "kenapa", "kalau",
    "bila", "apabila", "tersebut", "secara", "terhadap", "mengenai", "tentang",
    "juga", "lagi", "hanya", "belum", "pernah", "kerana", "sebab", "tetapi",
    "tapi", "namun", "supaya", "agar", "semasa", "seorang", "orang", "guru",
    "cikgu", "maklum", "ppkp", "kkm", "pkd", "uip", "kes", "tindakan", "perlu",
    "wajib", "check", "checking", "bag", "the", "and", "for", "with", "that",
    "bawah", "atas", "serta", "bagi", "sebagai", "antara", "lain", "satu",
    "mana2", "sekiranya", "sebarang", "seseorang", "individu", "pihak",
}

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
    r"(?:pelajar\s+|murid\s+|budak\s+|obd\s+)?(?:sedang\s+)?"
    r"(?:menghisap|hisap|merokok|mengunyah|menggunakan|guna|membeli|beli)"
    r"(?:\s*(?:,|atau|dan|/)\s*(?:menghisap|hisap|merokok|mengunyah|menggunakan|guna|membeli|beli))*",
    re.I,
)


def is_non_offence_or_definition_section(sec: Dict[str, Any]) -> bool:
    """Mengenal pasti seksyen tafsiran/tajuk ringkas/bukan kesalahan agar tidak pernah dicalonkan sebagai kesalahan."""
    heading_low = str(sec.get("section_heading") or "").strip().lower()
    code_low = str(sec.get("section_code") or "").strip().lower()
    if any(marker in heading_low for marker in _NON_OFFENCE_HEADING_MARKERS):
        return True
    if code_low in ("1", "2", "seksyen 1", "seksyen 2", "section 1", "section 2"):
        if not bool(sec.get("is_offence_provision")):
            return True
    return False


def _strip_negated_active_smoking(text_low: str) -> str:
    return _NEGATED_ACTIVE_SMOKING_RE.sub(" ", text_low or "")


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
    """Kunci penapisan Akta mengikut konteks soalan/akta_hint supaya soalan vape/pelajar tidak menarik Akta 171 / Akta 281 / PPKM 2009,
    sambil membenarkan Akta 56 (Keterangan), Akta 593 (KTJ) dan Akta 611 (Kanak-Kanak) apabila isu keterangan/prosedur/OBD disebut.
    """
    q_low = (question or "").lower()
    hint = (akta_hint or "").strip()
    hint_low = hint.lower()

    has_minor_signal = any(
        k in q_low
        for k in ("pelajar", "murid", "budak", "sekolah", "obd", "bawah 18", "bawah umur", "kanak-kanak", "remaja", "taska", "tadika")
    )
    has_evidence_signal = any(
        k in q_low
        for k in ("90a", "90b", "90c", "114a", "73aa", "akta 56", "akta keterangan", "keterangan digital", "cetakan komputer")
    )
    has_ktj_signal = any(
        k in q_low
        for k in ("112", "113", "119", "128", "152", "163", "376", "377", "ktj", "akta 593", "kanun tatacara", "diari siasatan", "rakaman percakapan")
    )

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
    akta_281_family = {"AKTA_281", "AKTA_281_PINDAAN_2024", "PPKM_2009", "PPM_1985"}
    akta_154_family = {"AKTA_154"}
    akta_342_family = {"AKTA_342", "AKTA_342_PINDAAN_2025", "AKTA_342_PERATURAN_KOMPAUN_2025"}

    def _attach_support_acts(allowed: set[str]) -> set[str]:
        if has_minor_signal:
            allowed.add("AKTA_611")
        if has_evidence_signal:
            allowed.add("AKTA_56")
        if has_ktj_signal:
            allowed.add("AKTA_593")
        return allowed

    if hint and hint_low not in ("semua", "all"):
        if "852" in hint_low:
            return _attach_support_acts(set(akta_852_family))
        if "ppkm" in hint_low:
            return _attach_support_acts({"PPKM_2009", "AKTA_281", "AKTA_281_PINDAAN_2024"})
        if "ppm" in hint_low:
            return _attach_support_acts({"PPM_1985", "AKTA_281", "AKTA_281_PINDAAN_2024"})
        if "281" in hint_low or "makanan" in hint_low:
            return _attach_support_acts(set(akta_281_family))
        if "154" in hint_low:
            return _attach_support_acts(set(akta_154_family))
        if "342" in hint_low or "apppb" in hint_low:
            return _attach_support_acts(set(akta_342_family))
        if "611" in hint_low:
            return {"AKTA_611"}
        if "593" in hint_low or "ktj" in hint_low:
            return {"AKTA_593"}
        if "56" in hint_low:
            return {"AKTA_56"}
        return {hint.upper()}

    def _has_any(terms: Tuple[str, ...]) -> bool:
        return any(re.search(rf"(?<!\w){re.escape(t)}(?!\w)", q_low) for t in terms)

    has_tobacco = _has_any((
        "vape", "rokok", "pod", "shisha", "tembakau", "merokok", "hisap", "menghisap",
        "ashtray", "obd", "ppkht", "852", "257/2024", "259/2024", "260/2024",
    )) or "17(1)" in q_low
    has_food = _has_any((
        "makanan", "restoran", "kedai makan", "dapur", "tifoid", "typhoid", "lpm", "slpm",
        "fosim", "keracunan", "najis tikus", "lipas", "lilati", "luput", "expired",
        "ppkm", "ppm", "mja", "pengendali makanan", "281",
    ))
    has_aedes = _has_any((
        "aedes", "denggi", "jentik", "larva", "nyamuk", "fogging", "entomologi",
        "tapak bina", "tapak pembinaan", "154",
    ))
    has_cdc = _has_any((
        "covid", "tibi", "tuberkulosis", "ptb", "afb", "tbis", "hfmd", "taska",
        "tadika", "leptospirosis", "kencing tikus", "measles", "wabak", "hso",
        "kuarantin", "pengasingan", "unit cdc", "342", "a1742", "139/2025",
    ))

    locked: set[str] = set()
    if has_tobacco:
        locked |= akta_852_family
    if has_food:
        locked |= akta_281_family
    if has_aedes:
        locked |= akta_154_family
    if has_cdc:
        locked |= akta_342_family

    if locked:
        return _attach_support_acts(locked)
    if has_evidence_signal or has_ktj_signal or has_minor_signal:
        return _attach_support_acts(set())
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

    has_active_smoking_fact = any(
        k in non_negated_q
        for k in (
            "sedang hisap", "sedang menghisap", "hisap vape", "menghisap vape",
            "hisap rokok", "menghisap rokok", "sedang merokok", "merokok di",
            "pelajar merokok", "dilihat menghisap", "tangkap pelajar sedang",
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
        else:
            # Penilaian berasaskan bukti fakta sebenar dalam soalan (hanya TERPENUHI jika fakta jelas dinyatakan!)
            if any(w in desc_low for w in ("belum dewasa", "bawah 18", "bawah umur", "umur")):
                if any(k in q_low for k in ("mykad", "sijil lahir", "jpn", "berumur 1", "bawah 18 tahun", "tingkatan")):
                    status = "TERPENUHI"
                    reason = "Status umur bawah 18 tahun (OBD) dinyatakan dalam fakta; pastikan salinan MyKad/Kad Pelajar dilampirkan."
                else:
                    status = "PERLU BUKTI TAMBAHAN"
                    reason = "Pelajar/OBD dinyatakan, tetapi umur sebenar (< 18 tahun pada tarikh kejadian) wajib disahkan dengan MyKad atau Kad Pelajar."
            elif any(w in desc_low for w in ("merokok", "mengunyah", "menggunakan", "menghisap")):
                if has_active_smoking_fact:
                    status = "TERPENUHI"
                    reason = "Perbuatan menghisap/merokok dinyatakan jelas dalam laporan kes; kukuhkan dengan keterangan saksi mata/guru, foto & rakaman S.112."
                else:
                    status = "PERLU BUKTI TAMBAHAN"
                    reason = "Perlu bukti saksi mata, video/CCTV atau pengakuan menunjukkan suspek benar-benar sedang merokok/menggunakan."
            elif any(w in desc_low for w in ("produk tembakau", "pengganti tembakau", "produk merokok", "rokok elektronik", "vape")):
                if any(k in q_low for k in ("vape", "pod", "rokok", "shisha", "tembakau")):
                    status = "TERPENUHI"
                    reason = "Produk merokok/vape dikenal pasti dalam fakta kes; pastikan peranti/cecair dirampas & dilak jika perlu untuk pembuktian."
                else:
                    status = "PERLU BUKTI TAMBAHAN"
                    reason = "Perlu pengesahan fizikal jenis produk merokok/pengganti tembakau."
            elif any(w in desc_low for w in ("mempamerkan", "pameran")):
                if any(k in q_low for k in ("pamer", "mempamer", "pameran", "di kaunter", "terbuka")):
                    status = "TERPENUHI"
                    reason = "Fakta pameran terbuka dinyatakan; ambil gambar sudut jauh & dekat sebelum sitaan S.35/S.36."
                else:
                    status = "PERLU BUKTI TAMBAHAN"
                    reason = "Perlu bukti gambar foto produk dipamerkan secara terbuka di kaunter jualan."
            elif any(w in desc_low for w in ("menjual", "jualan", "pembelian", "membeli")):
                if any(k in q_low for k in ("jual", "menjual", "membeli", "beli", "resit", "transaksi")):
                    status = "TERPENUHI"
                    reason = "Transaksi jualan/belian dinyatakan; lengkapkan resit pembelian, barang kes & percakapan S.112 saksi."
                else:
                    status = "PERLU BUKTI TAMBAHAN"
                    reason = "Perlu bukti transaksi jualan (resit, saksi pembelian atau CCTV kedai)."
            elif any(w in desc_low for w in ("mengiklankan", "iklan", "promosi")):
                if any(k in q_low for k in ("iklan", "poster", "bunting", "promosi", "skrin")):
                    status = "TERPENUHI"
                    reason = "Bahan iklan/promosi dinyatakan; ambil gambar sebelum sitaan atau cetak paparan digital dengan Sijil S.90A."
            elif any(w in desc_low for w in ("kawasan larangan", "tempat larangan", "tempat makan")):
                if any(k in q_low for k in ("restoran", "tempat makan", "sekolah", "tandas sekolah", "hospital", "kawasan larangan")):
                    status = "TERPENUHI"
                    reason = "Lokasi termasuk dalam kawasan/tempat larangan di bawah P.U. (A) 257/2024."
            elif any(w in desc_low for w in ("tifoid", "vaksin", "pemeriksaan perubatan")):
                if any(k in q_low for k in ("tiada tifoid", "tiada suntikan", "belum suntik", "tifoid")):
                    status = "TERPENUHI"
                    reason = "Ketiadaan suntikan anti-tifoid dinyatakan; sahkan kad suntikan & ambil gambar pekerja sedang mengendali makanan."
            elif any(w in desc_low for w in ("latihan pengendali", "slpm", "lpm")):
                if any(k in q_low for k in ("tiada sijil lpm", "tiada slpm", "tiada latihan")):
                    status = "TERPENUHI"
                    reason = "Ketiadaan Sijil Latihan Pengendali Makanan (SLPM) dinyatakan."
            elif any(w in desc_low for w in ("tidak bersih", "kotor", "perosak", "tikus", "lipas")):
                if any(k in q_low for k in ("kotor", "najis tikus", "lipas", "tikus", "lalat", "lilati")):
                    status = "TERPENUHI"
                    reason = "Keadaan premis tidak bersih / perosak dinyatakan; dokumentasikan dengan Borang KMM & foto + Sijil S.90A."
            elif any(w in desc_low for w in ("jentik", "larva", "aedes", "pembiakan")):
                if any(k in q_low for k in ("entomologi", "disahkan aedes")):
                    status = "TERPENUHI"
                    reason = "Pengesahan spesies Aedes dinyatakan."
                else:
                    status = "PERLU BUKTI TAMBAHAN"
                    reason = "Penemuan jentik-jentik/takungan masih wajib disahkan spesies Aedes melalui Sijil Makmal Entomologi sebelum kompaun/pendakwaan."
            elif any(w in desc_low for w in ("perintah", "notis", "s.15", "s.14", "s.8")):
                if any(k in q_low for k in ("ingkar perintah", "telah diserahkan", "notis arahan")):
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
    """Mengekstrak semua petikan Seksyen, Peraturan dan Akta daripada teks output AI."""
    if not text:
        return []

    citations: List[Dict[str, str]] = []
    seen: set[str] = set()

    # 1. Pasangan eksplisit: "Seksyen X(Y) Akta ZZZ" atau "Peraturan X(Y) PPKM 2009 / PPKHT 2004 / PPM 1985"
    paired_re = re.compile(
        r"\b(Seksyen|Peraturan)\s+(\d+[A-Za-z]?(?:\(\d+\))?(?:\([a-z]\))?)"
        r"(?:\s+(?:dibaca\s+bersama\s+[^,\n.;]{1,40}\s+)?)?"
        r"\s*(Akta\s+\d+|Akta\s+Kerja\s*1955|OSHA\s*1994|PPKM\s*2009|PPM\s*1985|PPKHT\s*2004|KTJ|APPPB\s*1988)?",
        re.I,
    )
    for m in paired_re.finditer(text):
        kind = m.group(1).capitalize()
        num = m.group(2).strip()
        act_raw = (m.group(3) or "").strip()
        # Cuba kesan Akta dalam lingkungan 65 aksara selepas petikan jika act_raw kosong
        if not act_raw:
            tail = text[m.end() : m.end() + 75]
            tail_m = re.search(
                r"\b(Akta\s+\d+|Akta\s+Kerja\s*1955|OSHA\s*1994|PPKM\s*2009|PPM\s*1985|PPKHT\s*2004|KTJ|APPPB\s*1988|P\.U\.\s*\(A\)\s*\d+/\d{4})\b",
                tail,
                re.I,
            )
            if tail_m:
                act_raw = tail_m.group(1).strip()
        key = f"{kind.upper()}:{num.upper()}:{act_raw.upper()}"
        if key not in seen:
            seen.add(key)
            citations.append(
                {
                    "kind": kind,
                    "number": num,
                    "base_number": re.findall(r"^\d+[A-Za-z]?", num)[0].upper(),
                    "act_ref": act_raw,
                    "raw_citation": m.group(0).strip(),
                }
            )

    return citations


def _build_valid_sections_index(
    sections_list: List[Dict[str, Any]],
    offences_list: List[Dict[str, Any]],
) -> Tuple[Dict[str, set[str]], set[str]]:
    """Membina indeks nombor seksyen/peraturan sah mengikut Akta Kanonik & statute_id (untuk validasi <2ms)."""
    valid_sections_by_act: Dict[str, set[str]] = {}
    all_valid_section_nums: set[str] = set()
    sec_ref_re = re.compile(r"(?:Seksyen|Peraturan|Section|Regulation)\s+(\d+[A-Za-z]?)", re.I)
    code_num_re = re.compile(r"(?:Peraturan\s+|Seksyen\s+|Section\s+)?(\d+[A-Za-z]?)\b", re.I)

    for sec in sections_list:
        sid = str(sec.get("statute_id") or "")
        act_code = canonical_akta_code_for_statute(sid)
        act_key = act_code.upper()
        sid_key = sid.upper()
        act_set = valid_sections_by_act.setdefault(act_key, set())
        sid_set = valid_sections_by_act.setdefault(sid_key, set())

        m2 = code_num_re.match(str(sec.get("section_code") or "").strip())
        if m2:
            num2 = m2.group(1).upper()
            act_set.add(num2)
            sid_set.add(num2)
            all_valid_section_nums.add(num2)

        raw_sec_text = f"{sec.get('section_heading', '')} {str(sec.get('verbatim_text_bm', ''))[:2000]}"
        for m in sec_ref_re.finditer(raw_sec_text):
            num = m.group(1).upper()
            act_set.add(num)
            sid_set.add(num)
            all_valid_section_nums.add(num)

    for off in offences_list:
        sid = str(off.get("statute_id") or "")
        act_key = canonical_akta_code_for_statute(sid).upper()
        act_set = valid_sections_by_act.setdefault(act_key, set())
        for field_val in (
            off.get("offence_section", ""),
            off.get("penalty_section", ""),
            " ".join(off.get("read_together_with") or []),
            str((off.get("compound_info") or {}).get("compound_authority_section") or ""),
            str((off.get("compound_info") or {}).get("notice_section") or ""),
        ):
            for num in re.findall(r"\b(\d+[A-Za-z]?)\b", str(field_val)):
                act_set.add(num.upper())
                all_valid_section_nums.add(num.upper())

    return valid_sections_by_act, all_valid_section_nums


def validate_legal_output(
    ai_response: Dict[str, Any] | str,
    legal_library: Dict[str, Any],
    question_context: str = "",
) -> Dict[str, Any]:
    """FASA 3.3: Pengesah Kod Pasca-Penjanaan Deterministik (`validateLegalOutput`).

    Menyemak:
    1. Setiap petikan Seksyen / Peraturan wujud dalam `statute_sections_verbatim` dan berstatus `BERKUAT_KUASA`.
    2. Tiada peruntukan dalam `repealed_and_blocked_provisions` dicadangkan sebagai tindakan aktif.
    3. Nilai denda / kompaun sepadan dengan `penalty_first_offence` & `compound_info` dalam `master_offences_matrix`.
    4. Jika unsur mandatori kesalahan berstatus `TIDAK TERPENUHI` (contoh: pelajar ada vape dalam beg tanpa bukti menghisap/membeli -> S.17(1) Akta 852), sebarang cadangan pertuduhan/kompaun aktif bagi seksyen itu DISEKAT.
    5. Jika akta yang ditanya belum mempunyai sebarang seksyen diindeks (`total_sections_indexed == 0`), pulangkan status `AKTA BELUM DIINDEKS — MUAT NAIK PDF WARTA`.
    """
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
        combined_text = " ".join(
            [
                str(resp_dict.get("akta_disyorkan") or ""),
                str(resp_dict.get("tajuk_nasihat") or ""),
                str(resp_dict.get("keputusan_tindakan") or ""),
                str(resp_dict.get("alasan_keputusan") or ""),
                str(resp_dict.get("templat_ringkas") or ""),
                charges_txt,
                str((resp_dict.get("borang_114") or {}).get("akta_dan_seksyen") or ""),
                str((resp_dict.get("borang_114") or {}).get("seksyen_hukuman") or ""),
                str((resp_dict.get("borang_114") or {}).get("teks_pertuduhan") or ""),
                str(resp_dict.get("peruntukan_undang") or ""),
            ]
        ).strip()

    statutes_reg: List[Dict[str, Any]] = legal_library.get("statutes_registry") or []
    sections_list: List[Dict[str, Any]] = legal_library.get("statute_sections_verbatim") or []
    offences_list: List[Dict[str, Any]] = legal_library.get("master_offences_matrix") or []
    repealed_list: List[Dict[str, Any]] = legal_library.get("repealed_and_blocked_provisions") or []
    lib_version = str(legal_library.get("statute_library_version") or INITIAL_STATUTE_LIBRARY_VERSION)

    reg_by_id = {str(s["statute_id"]): s for s in statutes_reg}

    # Bina atau guna indeks nombor seksyen sah yang telah dicache mengikut Akta Kanonik & statute_id
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
    for s in statutes_reg:
        if s.get("status") == "DIMANSUHKAN":
            continue
        sid = str(s.get("statute_id") or "")
        act_num = str(s.get("act_number_or_pu") or "")
        if int(s.get("total_sections_indexed") or 0) == 0:
            if (sid and sid.lower() in target_act_str.lower()) or (
                act_num and act_num.lower() in target_act_str.lower()
            ):
                unindexed_statutes.append(f"{sid} ({s.get('official_title_bm', '')})")

    # 1. Semak petikan seksyen/peraturan yang diekstrak
    extracted_citations = extract_legal_citations_from_text(combined_text)
    verified_citations: List[str] = []
    invalid_citations: List[str] = []

    # Akta rujukan silang luaran yang sah disebut dalam konteks rujukan agensi
    cross_agency_acts = {"AKTA 171", "AKTA 366", "AKTA 368", "AKTA 290", "AKTA 586", "AKTA 260", "AKTA 127", "AKTA 655", "AKTA 265", "AKTA 514", "AKTA 574", "AKTA KERJA 1955", "OSHA 1994"}
    default_act = canonical_akta_code_for_statute(str(resp_dict.get("akta_disyorkan") or "")).upper()

    charges_sec_only_check = " ".join(
        f"{c.get('seksyen_kesalahan', '')} {c.get('seksyen_hukuman', '')}"
        for c in (resp_dict.get("cadangan_pertuduhan") or [])
        if isinstance(c, dict)
    ).lower()

    for cit in extracted_citations:
        base_num = cit["base_number"].upper()
        act_ref = cit["act_ref"].upper().strip()
        raw_cit = cit["raw_citation"]

        if "PPKHT" in act_ref:
            if "ppkht" in charges_sec_only_check or not any(
                w in combined_text.lower()
                for w in ("dimansuhkan", "berbeza dengan", "jangan", "tidak sah", "bukan")
            ):
                invalid_citations.append(f"{raw_cit} (PPKHT 2004 telah dimansuhkan oleh Akta 852)")
            continue

        # Jika menyebut Akta 514 untuk Seksyen 22(b) (kesilapan Tibi), gagal
        if act_ref == "AKTA 514" and base_num == "22":
            invalid_citations.append(f"{raw_cit} (Akta 514 ialah OSHA 1994; kes Tibi ialah Seksyen 22(b) Akta 342)")
            continue

        if act_ref in cross_agency_acts and base_num in ("15", "24", "60F", "80", "81", "82"):
            verified_citations.append(raw_cit)
            continue

        explicit_act_lookup = ""
        if "852" in act_ref:
            explicit_act_lookup = "AKTA 852"
        elif "281" in act_ref or "PPKM" in act_ref or "PPM" in act_ref:
            explicit_act_lookup = "AKTA 281"
        elif "154" in act_ref:
            explicit_act_lookup = "AKTA 154"
        elif "342" in act_ref or "APPPB" in act_ref:
            explicit_act_lookup = "AKTA 342"
        elif "593" in act_ref or "KTJ" in act_ref:
            explicit_act_lookup = "AKTA 593"
        elif "56" in act_ref:
            explicit_act_lookup = "AKTA 56"
        elif "611" in act_ref:
            explicit_act_lookup = "AKTA 611"

        lookup_act = explicit_act_lookup or (default_act if default_act in valid_sections_by_act else "")
        procedural_support_nums = {"90A", "90B", "90C", "114A", "73AA", "112", "113", "119", "128", "152", "153", "154", "163", "376", "377", "15", "83", "91"}

        if explicit_act_lookup and explicit_act_lookup in valid_sections_by_act:
            # Apabila Akta dinyatakan secara jelas (cth: 'Seksyen 99 Akta 852'), WAJIB wujud dalam indeks Akta itu sahaja (tiada pintasan lintas-akta)
            if base_num in valid_sections_by_act[explicit_act_lookup]:
                verified_citations.append(raw_cit)
            else:
                invalid_citations.append(
                    f"{raw_cit} — Seksyen/Peraturan {cit['number']} TIDAK WUJUD dalam indeks {explicit_act_lookup}."
                )
        elif lookup_act and lookup_act in valid_sections_by_act:
            if base_num in valid_sections_by_act[lookup_act] or base_num in procedural_support_nums:
                verified_citations.append(raw_cit)
            else:
                invalid_citations.append(
                    f"{raw_cit} — Seksyen/Peraturan {cit['number']} TIDAK WUJUD dalam indeks {lookup_act}."
                )
        else:
            if base_num in all_valid_section_nums:
                verified_citations.append(raw_cit)
            else:
                invalid_citations.append(
                    f"{raw_cit} — Seksyen/Peraturan {cit['number']} TIDAK WUJUD dalam Pustaka Akta."
                )

    # 2. Semak senarai hitam `repealed_and_blocked_provisions`
    # Hanya sekat jika output mencadangkan peruntukan lapuk sebagai tindakan aktif (bukan sekadar memberi amaran "JANGAN guna PPKHT 2004" atau "telah dimansuhkan")
    repealed_hits: List[Dict[str, str]] = []
    low_combined = combined_text.lower()
    for rep in repealed_list:
        for pat in rep.get("match_patterns") or []:
            m = re.search(pat, low_combined, flags=re.I)
            if not m:
                continue
            # Semak konteks sekitar padanan: adakah ia amaran pemansuhan atau cadangan aktif?
            window_start = max(0, m.start() - 70)
            window_end = min(len(low_combined), m.end() + 95)
            ctx_window = low_combined[window_start:window_end]
            is_warning_context = any(
                w in ctx_window
                for w in (
                    "dimansuhkan",
                    "tamat tempoh",
                    "tidak sah",
                    "jangan",
                    "bukan",
                    "berbeza dengan",
                    "disekat",
                    "ralat",
                    "salah",
                )
            )
            # Tetapi jika ia diletakkan terus sebagai seksyen_kesalahan dalam cadangan_pertuduhan tanpa penafian, ia TETAP disekat!
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
    # Semak had kompaun Akta 154 (maksimum mutlak RM500)
    if "154" in low_combined:
        for comp_m in re.finditer(r"kompaun\s+rm\s?([\d,]+(?:\.\d{1,2})?)", low_combined):
            try:
                val = float(comp_m.group(1).replace(",", ""))
                if val > 500.0:
                    penalty_mismatches.append(
                        f"Had kompaun Seksyen 25 Akta 154 ialah maksimum RM500.00 (nilai RM{val:,.2f} melebihi had undang-undang)."
                    )
            except ValueError:
                pass

    # Semak had kompaun Akta 342 Pindaan Akta A1742 / P.U.(A) 139/2025 (Individu maks RM5,000 / Korporat maks RM50,000)
    if "342" in low_combined:
        for comp_m in re.finditer(r"kompaun(?:\s+individu)?\s+rm\s?([\d,]+(?:\.\d{1,2})?)", low_combined):
            try:
                val = float(comp_m.group(1).replace(",", ""))
                ctx_after = low_combined[comp_m.start() : comp_m.end() + 45]
                is_corp_ctx = any(k in ctx_after for k in ("syarikat", "korporat", "pertubuhan perbadanan"))
                limit = 50000.0 if is_corp_ctx else 5000.0
                if val > limit:
                    penalty_mismatches.append(
                        f"Had kompaun Seksyen 25 Akta 342 (Akta A1742) ialah maksimum RM{limit:,.0f} (nilai RM{val:,.2f} melebihi had)."
                    )
            except ValueError:
                pass

    # Semak kesilapan menawarkan kompaun bagi kesalahan TIDAK BOLEH KOMPAUN dalam `cadangan_pertuduhan`
    non_comp_patterns = (
        ("852", ("seksyen 3(", "seksyen 7(", "seksyen 9(", "seksyen 10(", "seksyen 13(1)", "s.3(", "s.7(", "s.9(", "s.10(", "s.13(1)"), "Jadual Pertama P.U. (A) 259/2024"),
        ("281", ("seksyen 13(1)", "seksyen 13b", "seksyen 11(2)", "s.13(1)", "s.13b", "s.11(2)"), "Akta Makanan 1983 (wajib Buka IP)"),
        ("154", ("seksyen 8(8)", "s.8(8)"), "Akta 154 (wajib Buka IP)"),
        ("342", ("seksyen 12(", "seksyen 22(a)", "s.12(", "s.22(a)"), "Jadual Pertama P.U. (A) 139/2025"),
    )
    for c in resp_dict.get("cadangan_pertuduhan") or []:
        if not isinstance(c, dict):
            continue
        sec_low = str(c.get("seksyen_kesalahan") or "").lower()
        comp_low = str(c.get("boleh_kompaun") or "").lower()
        claims_compoundable = (
            ("boleh kompaun" in comp_low or "boleh dikompaun" in comp_low)
            and not any(neg in comp_low for neg in ("tidak boleh", "tiada kompaun", "buka ip terus"))
        )
        if claims_compoundable:
            for act_digits, sec_pats, sched_ref in non_comp_patterns:
                if (act_digits in sec_low or act_digits in default_act.lower()) and any(p in sec_low for p in sec_pats):
                    penalty_mismatches.append(
                        f"Kesalahan {c.get('seksyen_kesalahan')} TIDAK BOLEH DIKOMPAUN di bawah {sched_ref} — wajib Buka IP Terus."
                    )

    # Semak had denda Seksyen 17(2) Akta 852 (OBD maks RM500)
    if "17(1)" in low_combined or "17(2)" in low_combined:
        for c in resp_dict.get("cadangan_pertuduhan") or []:
            if isinstance(c, dict) and "17" in str(c.get("seksyen_kesalahan") or ""):
                huk = str(c.get("hukuman_maksimum") or "")
                for rm_m in re.finditer(r"RM\s?([\d,]+)", huk, flags=re.I):
                    val = int(rm_m.group(1).replace(",", ""))
                    if val > 500:
                        penalty_mismatches.append(
                            f"Hukuman denda maksimum Seksyen 17(2) Akta 852 bagi OBD ialah RM500.00 (dipetik RM{val:,})."
                        )

    # 4. Semak Unsur Mandatori Kesalahan (Mandatory Elements Guardrail — semua kesalahan berperangkap)
    element_evaluations: List[Dict[str, Any]] = []
    unfulfilled_element_errors: List[str] = []
    eval_context = f"{question_context} {combined_text}".strip()
    eval_low = eval_context.lower()
    declared_no_offence = str(resp_dict.get("status_kesalahan") or "").upper() == "TIADA_KESALAHAN"
    keputusan_low = str(resp_dict.get("keputusan_tindakan") or "").lower()
    keputusan_is_rejection = any(
        neg in keputusan_low
        for neg in ("tiada kesalahan", "tidak boleh", "ditolak", "bukan kesalahan", "unsur tidak terpenuhi", "unsur tidak dipenuhi", "jangan keluarkan", "belum")
    )

    for off in offences_list:
        off_id = str(off.get("offence_id") or "")
        should_eval = False
        if off_id == "AKTA_852_S17_1" and (
            "17(1)" in low_combined
            or is_passive_vape_possession_question(eval_context)
            or ("pelajar" in eval_low and "vape" in eval_low)
        ):
            should_eval = True
        elif off_id == "AKTA_852_S13_3" and ("13(3)" in low_combined and is_passive_vape_possession_question(eval_context)):
            should_eval = True
        elif off_id == "AKTA_342_S22_B" and (
            "22(b)" in low_combined or ("covid" in eval_low and "kerja" in eval_low) or "smear negatif" in eval_low
        ):
            should_eval = True
        elif off_id == "PPM_1985_P14_9" and ("14(9)" in low_combined or "untuk pelupusan" in eval_low or "tidak untuk dijual" in eval_low):
            should_eval = True
        elif off_id == "AKTA_154_S13_1" and ("13(1)" in low_combined and any(k in eval_low for k in ("tiada larva", "takungan kosong", "luar sempadan", "bukan aedes"))):
            should_eval = True

        if not should_eval:
            continue

        ev = evaluate_offence_elements_against_facts(eval_context, off)
        element_evaluations.append(ev)
        if not ev["action_blocked"]:
            continue

        sec_marker = str(off.get("offence_section") or "").lower()
        active_in_charges = any(
            (sec_marker[:10] in str(c.get("seksyen_kesalahan") or "").lower() or off_id.split("_")[-2].lower() in str(c.get("seksyen_kesalahan") or "").lower())
            and not any(
                neg in str(c.get("perihal") or "").lower() + " " + str(c.get("boleh_kompaun") or "").lower()
                for neg in ("tiada kesalahan", "bukan kesalahan", "ditolak", "tidak boleh", "fasa ")
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
        """Menyegarkan cache indeks seksyen sah & token seksyen bagi carian dan validasi pantas."""
        self._valid_sections_cache = _build_valid_sections_index(
            self.statute_sections_verbatim,
            self.master_offences_matrix,
        )
        tok_cache: Dict[str, set[str]] = {}
        for sec in self.statute_sections_verbatim:
            did = str(sec.get("doc_id") or "")
            raw = f"{sec.get('section_code', '')} {sec.get('section_heading', '')} {str(sec.get('verbatim_text_bm', ''))[:2400]}".lower()
            tok_cache[did] = {t for t in TOKEN_RE.findall(raw) if len(t) >= 2}
        self._section_token_cache = tok_cache

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
            pages: List[str] = []
            with fitz.open(stream=raw_bytes, filetype="pdf") as doc:
                for page in doc:
                    pages.append(page.get_text("text"))
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
                    "message": f"AKTA BELUM DIINDEKS — MUAT NAIK PDF WARTA ({reg.get('official_title_bm', sid_up)})",
                    "sections": [],
                }

        results: List[Dict[str, Any]] = []
        q_low = (q or "").strip().lower()
        for sec in self.statute_sections_verbatim:
            if statute_id and statute_id.lower() != "semua":
                if sec["statute_id"].upper() != statute_id.strip().upper():
                    continue
            if akta_code and akta_code.lower() != "semua":
                c_act = canonical_akta_code_for_statute(sec["statute_id"])
                if akta_code.lower() not in c_act.lower() and akta_code.lower() not in sec["statute_id"].lower():
                    continue
            if q_low:
                hay = f"{sec['statute_id']} {sec['section_code']} {sec['section_heading']} {sec['verbatim_text_bm']}".lower()
                if q_low not in hay:
                    continue
            # Jangan pulangkan embedding_vector 64-float pada senarai UI bagi menjimatkan lebar jalur
            results.append({k: v for k, v in sec.items() if k != "embedding_vector"})

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
        q_low = (q or "").strip().lower()
        out: List[Dict[str, Any]] = []

        for off in self.master_offences_matrix:
            sid = str(off.get("statute_id") or "")
            c_act = canonical_akta_code_for_statute(sid)
            if statute_id and statute_id.lower() != "semua":
                if sid.upper() != statute_id.strip().upper():
                    continue
            if akta_code and akta_code.lower() != "semua":
                if akta_code.lower() not in c_act.lower() and akta_code.lower() not in sid.lower():
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
            if q_low:
                hay = json.dumps(off, ensure_ascii=False).lower()
                if q_low not in hay:
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
            out.append(
                {
                    **off,
                    "canonical_akta_code": c_act,
                    "linked_verbatim_sections": linked_verbatim,
                }
            )
        return out

    def search_closed_book_grounding(
        self,
        question: str,
        akta_hint: str = "Semua",
        top_k: int = 4,
    ) -> Dict[str, Any]:
        """FASA 3.1: Carian Hibrid Wajib Sebelum Menjawab (Mandatory Grounding).

        Mencari:
        a) Padanan dalam `repealed_and_blocked_provisions`.
        b) Hanya 1–2 calon kesalahan yang benar-benar berkaitan dalam `master_offences_matrix` (dikunci mengikut domain Akta).
        c) Teks penuh verbatim yang sepadan daripada `statute_sections_verbatim` (menapis keluar Seksyen 1/2 Tafsiran kecuali diminta).
        """
        q_raw = (question or "").strip()
        q_low = q_raw.lower()
        q_vec = compute_deterministic_embedding(q_raw)
        q_tokens = {
            t.lower()
            for t in TOKEN_RE.findall(q_low)
            if len(t) >= 2 and t.lower() not in _GROUNDING_STOPWORDS
        }
        asks_definition = any(
            k in q_low for k in ("tafsiran", "definisi", "maksud ", "seksyen 2", "sek. 2", "s.2 ")
        )
        allowed_sids = infer_domain_statute_ids(q_raw, akta_hint)
        is_passive_vape = is_passive_vape_possession_question(q_raw)
        has_minor_signal = any(
            k in q_low
            for k in ("pelajar", "murid", "budak", "sekolah", "obd", "bawah 18", "bawah umur", "kanak-kanak")
        )

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
                    or (sid and sid.lower() in q_low)
                    or (act_num and act_num.lower() in q_low)
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

        # b) Calon kesalahan dalam `master_offences_matrix` (terhad kepada domain Akta & 1-2 kesalahan paling relevan)
        scored_offences: List[Tuple[float, Dict[str, Any], Dict[str, Any]]] = []
        if is_passive_vape:
            # Bagi kes pemilikan pasif vape/rokok pelajar, nilai HANYA Seksyen 17(1) (dan S.13(3) jika pembelian disebut)
            target_oids = ["AKTA_852_S17_1"]
            if any(k in q_low for k in ("beli", "membeli", "13(3)", "kedai", "penjual")):
                target_oids.append("AKTA_852_S13_3")
            for oid in target_oids:
                matched_off = next(
                    (o for o in self.master_offences_matrix if o.get("offence_id") == oid),
                    None,
                )
                if matched_off:
                    ev = evaluate_offence_elements_against_facts(q_raw, matched_off)
                    scored_offences.append((10.0 if oid == "AKTA_852_S17_1" else 6.0, matched_off, ev))
        else:
            for off in self.master_offences_matrix:
                sid = str(off.get("statute_id") or "")
                c_act = canonical_akta_code_for_statute(sid)
                if allowed_sids is not None and sid not in allowed_sids:
                    continue
                if akta_hint and akta_hint not in ("", "Semua"):
                    if (
                        akta_hint.lower() not in c_act.lower()
                        and akta_hint.lower() not in sid.lower()
                        and not (sid == "AKTA_611" and has_minor_signal)
                    ):
                        continue
                off_text = (
                    f"{off.get('offence_section', '')} {off.get('offence_title', '')} "
                    f"{' '.join(off.get('read_together_with') or [])}"
                ).lower()
                off_tokens = {
                    t.lower()
                    for t in TOKEN_RE.findall(off_text)
                    if len(t) >= 2 and t.lower() not in _GROUNDING_STOPWORDS
                }
                overlap = len(q_tokens & off_tokens)
                score = float(overlap)
                # Bonus padanan nombor seksyen tepat
                sec_nums = re.findall(r"\d+[A-Za-z]?", str(off.get("offence_section") or ""))
                if sec_nums and sec_nums[0].lower() in q_tokens:
                    score += 4.5
                # Bonus tepat untuk OBD merokok/hisap vape (S.17(1) Akta 852)
                if off["offence_id"] == "AKTA_852_S17_1" and has_minor_signal and any(
                    k in q_low for k in ("vape", "rokok", "hisap", "merokok", "17(1)")
                ):
                    score += 8.0
                if off["offence_id"] == "AKTA_852_S13_1" and any(
                    k in q_low for k in ("jual", "menjual", "pekedai", "penjual", "kedai")
                ) and has_minor_signal:
                    score += 6.5
                if off["offence_id"] == "AKTA_852_S10_1" and any(
                    k in q_low for k in ("pamer", "pameran", "kaunter", "terbuka")
                ):
                    score += 6.0
                if off["offence_id"] == "AKTA_852_S16_2" and any(
                    k in q_low for k in ("restoran", "tempat makan", "kawasan larangan", "larangan merokok")
                ) and not has_minor_signal:
                    score += 6.0
                if score >= 1.0:
                    eval_res = evaluate_offence_elements_against_facts(q_raw, off)
                    scored_offences.append((score, off, eval_res))

        scored_offences.sort(key=lambda x: x[0], reverse=True)
        # Hadkan kepada maksimum 1-2 kesalahan yang benar-benar relevan (BUKAN 5 seksyen rawak)
        max_offences = min(top_k, 2)
        if scored_offences:
            top_score = scored_offences[0][0]
            focused_offences = [
                item
                for idx, item in enumerate(scored_offences[:max_offences])
                if idx == 0 or (item[0] >= 2.0 and item[0] >= top_score * 0.55)
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

        # c) Teks penuh verbatim daripada `statute_sections_verbatim`
        sec_map = {s["doc_id"]: s for s in self.statute_sections_verbatim}
        verbatim_hits: List[Dict[str, Any]] = []
        seen_doc_ids: set[str] = set()

        # Utamakan seksyen verbatim yang dipautkan terus oleh top_offences
        for off in top_offences:
            for did in off.get("source_section_doc_ids") or []:
                if did in sec_map and did not in seen_doc_ids:
                    s_obj = sec_map[did]
                    if not asks_definition and is_non_offence_or_definition_section(s_obj):
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

        # Jika kes pelajar/OBD di bawah Akta 852, masukkan rujukan Akta 611 (S.83) jika tersedia
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

        # Tambah carian hibrid BM25/kata kunci + vektor ke atas `statute_sections_verbatim` (dikunci mengikut domain & tapis Tafsiran)
        scored_secs: List[Tuple[float, Dict[str, Any]]] = []
        for s_obj in self.statute_sections_verbatim:
            if s_obj["doc_id"] in seen_doc_ids:
                continue
            if not asks_definition and is_non_offence_or_definition_section(s_obj):
                continue
            sid = s_obj["statute_id"]
            c_act = canonical_akta_code_for_statute(sid)
            if allowed_sids is not None and sid not in allowed_sids:
                continue
            if akta_hint and akta_hint not in ("", "Semua"):
                if (
                    akta_hint.lower() not in c_act.lower()
                    and akta_hint.lower() not in sid.lower()
                    and not (sid == "AKTA_611" and has_minor_signal)
                ):
                    continue
            s_toks = self._section_token_cache.get(s_obj["doc_id"])
            if s_toks is None:
                s_toks = {t.lower() for t in TOKEN_RE.findall(s_obj["verbatim_text_bm"][:2400].lower()) if len(t) >= 2}
            kw_overlap = len(q_tokens & s_toks)
            sem_sim = cosine_similarity(q_vec, s_obj.get("embedding_vector") or [])
            offence_bonus = 0.25 if s_obj.get("is_offence_provision") else 0.0
            combined_sc = (kw_overlap * 0.35) + max(0.0, sem_sim) + offence_bonus
            if combined_sc > 0.20:
                scored_secs.append((combined_sc, s_obj))

        scored_secs.sort(key=lambda x: x[0], reverse=True)
        for sc, s_obj in scored_secs[: max(0, top_k - len(verbatim_hits))]:
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
                    "score": round(min(0.95, max(0.10, sc)), 4),
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
                            for t in TOKEN_RE.findall(cs["verbatim_text_bm"][:2400].lower())
                            if len(t) >= 2
                        }
                    c_score = float(len(q_tokens & s_toks)) * 0.4
                    if sc_code_up in prio_codes:
                        c_score += 3.0 + (len(prio_codes) - prio_codes.index(sc_code_up)) * 0.25
                    # Bonus jika seksyen pindaan ini meminda nombor seksyen yang disebut dalam soalan/konteks induk
                    for ref_n in referenced_sec_nums:
                        if ref_n and (sc_code_up == ref_n or f"SEKSYEN {ref_n}" in heading_up):
                            c_score += 4.5
                            break
                    # Bonus khusus kompaun/denda bagi Akta 342
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
        if top_offences:
            ctx_parts.append("\n[MATRIKS KESALAHAN & UNSUR MANDATORI (master_offences_matrix)]:")
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
            for vh in verbatim_hits:
                comp_tag = " [PINDAAN TERKINI — UTAMAKAN]" if vh.get("is_amendment_companion") else ""
                ctx_parts.append(
                    f"--- {vh['doc_id']} ({vh['akta_code']} | {vh['section_code']} - {vh['section_heading']}){comp_tag} ---\n"
                    f"{vh['verbatim_text_bm']}"
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
