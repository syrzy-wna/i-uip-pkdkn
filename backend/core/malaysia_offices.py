"""Penyeragaman nama Pejabat Kesihatan (PKD / PKK / PKB), Negeri (JKN / JKWP) & Bidang Kuasa Mahkamah seluruh Malaysia.

Menyokong semua 13 Negeri dan 3 Wilayah Persekutuan:
- Semenanjung Malaysia: Pejabat Kesihatan Daerah (PKD) / Jabatan Kesihatan Negeri (JKN)
- Sabah: Pejabat Kesihatan Kawasan (PKK) / Jabatan Kesihatan Negeri Sabah
- Sarawak: Pejabat Kesihatan Bahagian (PKB) / Jabatan Kesihatan Negeri Sarawak
- WP Kuala Lumpur & Putrajaya: Jabatan Kesihatan Wilayah Persekutuan Kuala Lumpur & Putrajaya (JKWPKL&P)
- WP Labuan: Jabatan Kesihatan Wilayah Persekutuan Labuan (JKWPL)
"""

from __future__ import annotations

import re
from typing import Dict

MALAYSIA_STATES_LIST = [
    "Johor",
    "Kedah",
    "Kelantan",
    "Melaka",
    "Negeri Sembilan",
    "Pahang",
    "Perak",
    "Perlis",
    "Pulau Pinang",
    "Sabah",
    "Sarawak",
    "Selangor",
    "Terengganu",
    "Wilayah Persekutuan Kuala Lumpur",
    "Wilayah Persekutuan Putrajaya",
    "Wilayah Persekutuan Labuan",
]

_OFFICE_PREFIX_RE = re.compile(
    r"^(?:pejabat\s+kesihatan\s+(?:daerah|kawasan|bahagian)|pejabat\s+kesihatan|pkd|pkk|pkb)\s+",
    re.I,
)
_STATE_PREFIX_RE = re.compile(
    r"^(?:jabatan\s+kesihatan\s+negeri|jabatan\s+kesihatan\s+wilayah\s+persekutuan|jabatan\s+kesihatan|jkn|jkwpkl&p|jkwpl|jkwp)\s+",
    re.I,
)


def extract_clean_district(district_pkd: str) -> str:
    """Ekstrak nama daerah/kawasan/bahagian bersih daripada nama penuh PKD/PKK/PKB."""
    raw = str(district_pkd or "").strip()
    if not raw:
        return ""
    cleaned = _OFFICE_PREFIX_RE.sub("", raw).strip()
    return cleaned or raw


def extract_clean_state(state_jkn: str) -> str:
    """Ekstrak nama negeri atau Wilayah Persekutuan bersih daripada nama JKN/JKWP."""
    raw = str(state_jkn or "").strip()
    if not raw:
        return ""
    low = raw.lower()
    if "kuala lumpur" in low and "putrajaya" in low:
        return "Wilayah Persekutuan Kuala Lumpur & Putrajaya"
    if "kuala lumpur" in low:
        return "Wilayah Persekutuan Kuala Lumpur"
    if "putrajaya" in low:
        return "Wilayah Persekutuan Putrajaya"
    if "labuan" in low:
        return "Wilayah Persekutuan Labuan"
    cleaned = _STATE_PREFIX_RE.sub("", raw).strip()
    return cleaned or raw


def normalize_malaysia_health_office(
    district_pkd: str = "",
    state_jkn: str = "",
    daerah_override: str = "",
    negeri_override: str = "",
) -> Dict[str, str]:
    """Memulangkan maklumat pejabat, daerah, negeri dan pengepala bidang kuasa mahkamah yang seragam seluruh Malaysia."""
    raw_office = str(district_pkd or "").strip()
    raw_state = str(state_jkn or "").strip()

    daerah = str(daerah_override or "").strip() or extract_clean_district(raw_office)
    negeri = str(negeri_override or "").strip() or extract_clean_state(raw_state)

    # Kekalkan nama penuh rasmi (PKD / PKK / PKB / Pejabat Kesihatan Cheras, dsb.) tanpa menampal "PKD" dua kali
    if raw_office and not daerah_override:
        pejabat_rasmi = raw_office
    elif daerah:
        low_d = daerah.lower()
        if any(
            low_d.startswith(pref)
            for pref in ("pejabat kesihatan", "pkd ", "pkk ", "pkb ")
        ):
            pejabat_rasmi = daerah
        elif "sabah" in negeri.lower():
            pejabat_rasmi = f"Pejabat Kesihatan Kawasan {daerah}"
        elif "sarawak" in negeri.lower():
            pejabat_rasmi = f"Pejabat Kesihatan Bahagian {daerah}"
        elif "wilayah persekutuan" in negeri.lower():
            pejabat_rasmi = f"Pejabat Kesihatan {daerah}"
        else:
            pejabat_rasmi = f"Pejabat Kesihatan Daerah {daerah}"
    else:
        pejabat_rasmi = "Pejabat Kesihatan Daerah / Kawasan / Bahagian"

    low_n = negeri.lower()
    if not negeri:
        negeri_mahkamah = "MALAYSIA"
        saman_jurisdiction = "MALAYSIA"
    elif "sabah" in low_n:
        negeri_mahkamah = "DALAM NEGERI SABAH, MALAYSIA"
        saman_jurisdiction = "NEGERI SABAH, MALAYSIA"
    elif "sarawak" in low_n:
        negeri_mahkamah = "DALAM NEGERI SARAWAK, MALAYSIA"
        saman_jurisdiction = "NEGERI SARAWAK, MALAYSIA"
    elif "labuan" in low_n:
        negeri_mahkamah = "DI WILAYAH PERSEKUTUAN LABUAN, MALAYSIA"
        saman_jurisdiction = "WILAYAH PERSEKUTUAN LABUAN, MALAYSIA"
    elif "wilayah persekutuan" in low_n or "kuala lumpur" in low_n or "putrajaya" in low_n:
        wp_label = negeri.upper() if "wilayah persekutuan" in low_n else f"WILAYAH PERSEKUTUAN {negeri.upper()}"
        negeri_mahkamah = f"DI {wp_label}, MALAYSIA"
        saman_jurisdiction = "NEGERI-NEGERI TANAH MELAYU"
    else:
        negeri_mahkamah = f"DALAM NEGERI {negeri.upper()}, MALAYSIA"
        saman_jurisdiction = "NEGERI-NEGERI TANAH MELAYU"

    return {
        "pejabat_rasmi": pejabat_rasmi,
        "daerah": daerah,
        "negeri": negeri,
        "negeri_mahkamah": negeri_mahkamah,
        "saman_jurisdiction": saman_jurisdiction,
    }


def resolve_saman_jurisdiction_header(*texts: str) -> str:
    """Menentukan pengepala bidang kuasa Saman Mahkamah 111 mengikut negeri (Semenanjung vs Sabah vs Sarawak vs Labuan)."""
    joined = " ".join(str(t or "") for t in texts).lower()
    if "sabah" in joined or "kota kinabalu" in joined or "sandakan" in joined or "tawau" in joined or "lahad datu" in joined or "keningau" in joined:
        return "NEGERI SABAH, MALAYSIA"
    if "sarawak" in joined or "kuching" in joined or "sibu" in joined or "miri" in joined or "bintulu" in joined or "sri aman" in joined:
        return "NEGERI SARAWAK, MALAYSIA"
    if "labuan" in joined:
        return "WILAYAH PERSEKUTUAN LABUAN, MALAYSIA"
    if any(
        st.lower() in joined
        for st in (
            "johor", "kedah", "kelantan", "melaka", "negeri sembilan",
            "pahang", "perak", "perlis", "pulau pinang", "penang",
            "selangor", "terengganu", "kuala lumpur", "putrajaya",
        )
    ):
        return "NEGERI-NEGERI TANAH MELAYU"
    return "MALAYSIA"


def infer_state_from_text(text: str) -> str:
    """Cuba kesan nama negeri/WP daripada alamat atau teks kes jika medan negeri kosong."""
    low = str(text or "").lower()
    if not low:
        return ""
    for st in (
        "Wilayah Persekutuan Kuala Lumpur",
        "Wilayah Persekutuan Putrajaya",
        "Wilayah Persekutuan Labuan",
        "Negeri Sembilan",
        "Pulau Pinang",
        "Terengganu",
        "Selangor",
        "Kelantan",
        "Sarawak",
        "Sabah",
        "Johor",
        "Pahang",
        "Kedah",
        "Perak",
        "Perlis",
        "Melaka",
    ):
        if st.lower() in low:
            return st
    if "kuala lumpur" in low:
        return "Wilayah Persekutuan Kuala Lumpur"
    if "putrajaya" in low:
        return "Wilayah Persekutuan Putrajaya"
    if "labuan" in low:
        return "Wilayah Persekutuan Labuan"
    if "penang" in low:
        return "Pulau Pinang"
    return ""
