"""Enjin Auto-Redaction (Penyamaran Data Sulit OSA/PDPA) dan Re-hydration.

Menggunakan Ollama tempatan (gemma3:12b) apabila tersedia, dan dilengkapi
enjin Regex + Heuristik Entiti Malaysia yang tepat untuk mengasingkan
Pegawai Penyiasat (IO/PPKP) daripada OKT, Saksi, No. KP, No. Pasport,
Nama Premis/Syarikat, No. SSM, dan No. Telefon.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

import httpx

from backend.core.config import settings

NON_PERSON_STOPWORDS = {
    "pegawai kesihatan persekitaran",
    "penolong pegawai kesihatan persekitaran",
    "pegawai penguatkuasa",
    "pegawai diberi kuasa",
    "timbalan pendakwa raya",
    "kementerian kesihatan malaysia",
    "unit inspektorat dan perundangan",
    "unit perundangan dan pendakwaan",
    "pejabat kesihatan daerah",
    "mahkamah majistret",
    "tiada",
    "tidak diketahui",
    "tidak dinyatakan",
    "belum dikenal pasti",
    "pemilik / pengurus premis",
}

MYKAD_RE = re.compile(r"\b(\d{6}-\d{2}-\d{4})\b")
MYKAD_SPACED_RE = re.compile(r"\b(\d{6}[ \t]+\d{2}[ \t]+\d{4})\b")
MYKAD_COMPACT_RE = re.compile(
    r"(?i)(?:no\.?\s*k/?p|kad\s+pengenalan|mykad|ic\s*no\.?|nric)\s*[:\-]?\s*(\d{12})\b"
)
# 12-digit MyKad tanpa sempang (YYMMDD + kod negeri 01-59/82 + 4 digit) — elak tangkap SSM 19xx/20xx + 01..06
MYKAD_UNLABELED_12_RE = re.compile(r"\b(\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{6})\b")
PASSPORT_RE = re.compile(
    r"(?i)(?:no\.?\s*pasport|passport\s*(?:no\.?|number)?|dokumen\s+perjalanan)\s*[:\-]?\s*([A-Z]{1,3}[-\s]?\d{5,9}|(?=[A-Z0-9]{6,12}\b)(?=[A-Z0-9]*[A-Z])(?=[A-Z0-9]*\d)[A-Z0-9]{6,12})\b"
)
PHONE_RE = re.compile(
    r"(?<!\d)(?:\+?60[-\s]?|0)(?:1[0-9]|3|4|5|6|7|8[2-9]|9)[-\s]?\d{3,4}[-\s]?\d{4}(?!\d)"
)
EMAIL_RE = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)
KKM_CARD_RE = re.compile(
    r"\b(KKM[-/\s]?(?:[A-Z]{2,5}[-/\s]?)?\d{3,8}(?:[-/][A-Z0-9]{1,6})?)\b",
    re.I,
)
RESIDENTIAL_ADDR_RE = re.compile(
    r"(?im)^[ \t]*alamat\s+(?:kediaman|pesakit|rumah|terkini\s+pesakit|okt|oks|tertuduh|surat[\-\s]?menyurat)\s*[:\-]\s*([^\n\r]+)"
)
INCIDENT_ADDR_RE = re.compile(
    r"(?im)^[ \t]*alamat\s+(?:kejadian|premis)\s*[:\-]\s*([^\n\r]+)"
)
SSM_12_RE = re.compile(r"\b((?:19|20)\d{2}0[1-6]\d{6})\b")
SSM_RE = re.compile(
    r"\b(?:\d{12}[ \t]*\(\d{6,7}-[A-Za-z]\)|(?:19|20)\d{2}0[1-6]\d{6}|LLP\d{7}-[A-Za-z]{3}|(?:SA|IP|PG|NS|MA|JM|KT|TR|AS|CA|LA|RA|KT|JR|PG|00)\d{6,7}-[A-Za-z]|\d{6,7}-[A-Za-z])\b"
)

# Label Pegawai KKM (Senarai Putih agar tidak disamarkan sebagai Suspek/OKT)
OFFICER_LABEL_RE = re.compile(
    r"(?im)^[ \t]*(?:pegawai\s+penyiasat(?:\s*\(io\))?|pegawai\s+perakam|pegawai\s+pengadu|jurugambar|ppkp|pkp)\s*[:\-]\s*([^\n\r]+)"
)

# Label Suspek / OKT / Pemilik
SUSPECT_LABEL_RE = re.compile(
    r"(?im)^[ \t]*(?:nama\s+)?(?:suspek|okt|oks|orang\s+kena\s+(?:tuduh|saman)|tertuduh|pemilik(?:\s+premis)?|pemunya|penjaga\s+premis|pengurus\s+tapak|penyelia|wakil\s+syarikat|pengendali\s+makanan|pengarah|pesalah|penerima\s+notis)\s*(?:\([^)]+\))?\s*[:\-]\s*([^\n\r]+)"
)
# Label Saksi / Pengadu / Pekerja
WITNESS_LABEL_RE = re.compile(
    r"(?im)^[ \t]*(?:nama\s+)?(?:saksi(?:\s*\d+)?|pekerja|penerima\s+sampel|s\d+)\s*(?:\([^)]+\))?\s*[:\-]\s*([^\n\r]+)"
)
# Label Premis / Syarikat (TIDAK termasuk Tempat Kejadian / Alamat)
PREMISE_LABEL_RE = re.compile(
    r"(?im)^[ \t]*(?:nama\s+)?(?:premis(?:\s+makanan)?|syarikat|perniagaan|firma|kedai|kilang)\s*[:\-]\s*([^\n\r]+)"
)

COMPANY_PHRASE_RE = re.compile(
    r"\b([A-Z][A-Za-z0-9'&\.\-]*(?:[ \t]+[A-Z0-9][A-Za-z0-9'&\.\-]*){0,5}[ \t]+(?:Sdn\.?[ \t]*Bhd\.?|Bhd\.?|Enterprise|Trading|Resources|Holdings|Ventures|Bistro|Kafe|Cafe|Mart|Minimart))\b"
)
RESTORAN_PHRASE_RE = re.compile(
    r"\b((?:Restoran|Kedai[ \t]+Makan|Kedai[ \t]+Serbaneka|Kedai[ \t]+Runcit|Klinik|Gerai|Warung|Kilang|Pusat[ \t]+Snuker|Kafe)[ \t]+[A-Z][A-Za-z0-9'&\.\-]*(?:[ \t]+[A-Z0-9][A-Za-z0-9'&\.\-]*){0,4})\b"
)
# Nama Malaysia berpatronymik (bin/binti/a/l/a/p/anak/ak) pada satu baris — sokong huruf kecil & besar
MALAYSIAN_NAME_RE = re.compile(
    r"(?i)\b((?:(?!(?:PPKP|PKP|Pegawai|Encik|Puan|Cik|Tuan|Nama|Suspek|OKT|OKS|Saksi|Pengadu|Pelajar|Pekerja)\b)[A-Za-z][a-zA-Z'@\.]{1,})(?:[ \t]+(?:(?!(?:No|Tel|SSM|K/P|bin|binti|bte|b\.|a/l|a/p|s/o|d/o|anak|ak)\b)[A-Za-z][a-zA-Z'@\.]{1,})){0,3}[ \t]+(?:bin|binti|bte|b\.|a/l|a/p|s/o|d/o|anak|ak)[ \t]+[A-Za-z][a-zA-Z'@\.]{1,}(?:[ \t]+(?:(?!(?:No|Tel|SSM|yang|di|pada|telah|adalah|dan|atau|dari|ke|untuk)\b)[A-Za-z][a-zA-Z'@\.]{1,})){0,3})\b"
)


def _is_valid_unlabeled_mykad_12(val: str) -> bool:
    if len(val) != 12 or not val.isdigit():
        return False
    # Abaikan format SSM 12-digit baharu (19xx/20xx + kod entiti 01..06)
    if SSM_12_RE.fullmatch(val):
        return False
    mm = int(val[2:4])
    dd = int(val[4:6])
    pb = int(val[6:8])
    return 1 <= mm <= 12 and 1 <= dd <= 31 and (1 <= pb <= 59 or pb == 82)


@dataclass
class RedactedEntity:
    token: str
    category: str
    original: str
    source: str


@dataclass
class RedactionResult:
    original_text: str
    redacted_text: str
    token_map: Dict[str, str] = field(default_factory=dict)
    entities: List[RedactedEntity] = field(default_factory=list)
    engine_used: str = "regex-kkm"
    ollama_available: bool = False
    warnings: List[str] = field(default_factory=list)


class PrivacyRedactor:
    """Menyamarkan data sulit OSA/PDPA sebelum penghantaran awan dan memulihkannya di PC."""

    _ollama_cache_ts: float = 0.0
    _ollama_cache_up: bool = False
    _ollama_cache_models: List[str] = []
    _ollama_cache_url: str = ""

    def __init__(
        self,
        ollama_base_url: Optional[str] = None,
        ollama_model: Optional[str] = None,
    ) -> None:
        self.ollama_base_url = (ollama_base_url or settings.ollama_base_url).rstrip("/")
        self.ollama_model = ollama_model or settings.ollama_model

    @classmethod
    def invalidate_ollama_cache(cls) -> None:
        cls._ollama_cache_ts = 0.0

    def check_ollama_status(self, force: bool = False) -> Tuple[bool, List[str]]:
        now = time.monotonic()
        ttl = 60.0 if self.__class__._ollama_cache_up else 30.0
        if (
            not force
            and self.__class__._ollama_cache_url == self.ollama_base_url
            and (now - self.__class__._ollama_cache_ts) < ttl
        ):
            return self.__class__._ollama_cache_up, list(self.__class__._ollama_cache_models)

        try:
            with httpx.Client(timeout=0.45) as client:
                resp = client.get(f"{self.ollama_base_url}/api/tags")
                if resp.status_code == 200:
                    data = resp.json()
                    models = [m.get("name", "") for m in data.get("models", [])]
                    self.__class__._ollama_cache_ts = now
                    self.__class__._ollama_cache_up = True
                    self.__class__._ollama_cache_models = models
                    self.__class__._ollama_cache_url = self.ollama_base_url
                    return True, models
        except Exception:
            pass

        self.__class__._ollama_cache_ts = now
        self.__class__._ollama_cache_up = False
        self.__class__._ollama_cache_models = []
        self.__class__._ollama_cache_url = self.ollama_base_url
        return False, []

    def _extract_entities_with_ollama(self, text: str) -> Tuple[Dict[str, List[str]], bool]:
        ollama_up, models = self.check_ollama_status()
        if not ollama_up:
            return {}, False

        chosen_model = self.ollama_model
        if models and chosen_model not in models:
            prefix = chosen_model.split(":")[0]
            matched = [m for m in models if m.startswith(prefix)]
            chosen_model = matched[0] if matched else models[0]

        prompt = (
            "Anda ialah penapis privasi OSA/PDPA untuk KKM Malaysia. "
            "Keluarkan entiti sensitif daripada teks kes di bawah dalam JSON sahaja "
            "dengan kunci: suspects, witnesses, premises, ic_numbers, ssm_numbers, phone_numbers.\n"
            "JANGAN masukkan nama Pegawai Kesihatan / PPKP / PKP dalam suspects atau witnesses.\n"
            "Setiap nilai mesti tepat seperti dalam teks.\n\n"
            f"TEKS:\n{text[:4500]}"
        )

        try:
            with httpx.Client(timeout=settings.ollama_timeout_seconds) as client:
                resp = client.post(
                    f"{self.ollama_base_url}/api/generate",
                    json={
                        "model": chosen_model,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json",
                        "options": {"temperature": 0.0},
                    },
                )
                if resp.status_code != 200:
                    return {}, True
                payload = resp.json()
                parsed = json.loads(payload.get("response", "").strip())
                if isinstance(parsed, dict):
                    cleaned: Dict[str, List[str]] = {}
                    for key in (
                        "suspects",
                        "witnesses",
                        "premises",
                        "ic_numbers",
                        "ssm_numbers",
                        "phone_numbers",
                    ):
                        vals = parsed.get(key, [])
                        if isinstance(vals, list):
                            cleaned[key] = [
                                str(v).strip() for v in vals if isinstance(v, str) and len(v.strip()) >= 3
                            ]
                    return cleaned, True
        except Exception:
            return {}, ollama_up

        return {}, ollama_up

    @staticmethod
    def _clean_candidate(val: str) -> str:
        # Buang maklumat dalam kurungan di hujung (No. K/P: ..., Juruwang Kedai) atau selepas koma
        val = re.sub(r"\s*\([^)]*\)\s*$", "", val).strip()
        val = val.split(",")[0].strip()
        # Buang gelaran kehormat hadapan jika terlekat
        val = re.sub(r"^(?:Encik|Puan|Cik|Tuan|Dr\.?)\s+", "", val, flags=re.I)
        return val.strip(".,;:\"'() ")

    @staticmethod
    def _is_valid_person(candidate: str, officer_whitelist: Set[str]) -> bool:
        if len(candidate) < 3 or len(candidate) > 90:
            return False
        low = candidate.lower()
        if low in NON_PERSON_STOPWORDS:
            return False
        if any(off.lower() in low or low in off.lower() for off in officer_whitelist if len(off) >= 5):
            return False
        if any(low.startswith(prefix) for prefix in ("ppkp ", "pkp ", "pegawai ", "dr. ")):
            return False
        if re.fullmatch(r"[\d\-\s/]+", candidate):
            return False
        if candidate.startswith("[") and candidate.endswith("]"):
            return False
        return True

    def _build_officer_whitelist(self, text: str) -> Set[str]:
        whitelist: Set[str] = set()
        for m in OFFICER_LABEL_RE.finditer(text):
            cleaned = self._clean_candidate(m.group(1))
            cleaned = re.sub(r"^(?:PPKP|PKP)\s+", "", cleaned, flags=re.I).strip()
            if len(cleaned) >= 5:
                whitelist.add(cleaned)
        # Tangkap juga nama selepas frasa "PPKP <Nama>" dalam teks naratif
        for m in re.finditer(r"\b(?:PPKP|PKP)[ \t]+([A-Z][A-Za-z'@\.]+(?:[ \t]+(?:bin|binti|bte|a/l|a/p|[A-Z][A-Za-z'@\.]+)){1,5})", text):
            whitelist.add(self._clean_candidate(m.group(1)))
        return whitelist

    def redact(
        self,
        text: str,
        use_ollama: bool = True,
        *,
        redact_moh_emails: bool = False,
    ) -> RedactionResult:
        if not text:
            return RedactionResult(original_text="", redacted_text="")

        officer_whitelist = self._build_officer_whitelist(text)
        ollama_entities: Dict[str, List[str]] = {}
        ollama_available = False
        warnings: List[str] = []

        if use_ollama:
            ollama_entities, ollama_available = self._extract_entities_with_ollama(text)

        found_items: Dict[str, Tuple[str, str]] = {}

        def _register(raw_val: str, category: str, source: str) -> None:
            cleaned = (
                raw_val.strip()
                if category in ("NO_KP", "NO_SSM", "NO_TEL", "PASPORT", "EMEL", "ALAMAT", "KAD_KUASA")
                else self._clean_candidate(raw_val)
            )
            if not cleaned:
                return
            if category in ("SUSPEK", "SAKSI") and not self._is_valid_person(cleaned, officer_whitelist):
                return
            if category == "PREMIS":
                if len(cleaned) < 4 or cleaned.lower() in NON_PERSON_STOPWORDS:
                    return
                if re.match(r"^(?:no\.?|lot|jalan|jln|blok|tingkat)\b", cleaned, flags=re.I):
                    return
            if re.fullmatch(r"\[[A-Z_]+_\d+\]", cleaned):
                return
            if cleaned not in found_items:
                found_items[cleaned] = (category, source)

        # 1. Entiti daripada Ollama (jika aktif)
        ollama_key_map = {
            "ic_numbers": "NO_KP",
            "ssm_numbers": "NO_SSM",
            "phone_numbers": "NO_TEL",
            "premises": "PREMIS",
            "suspects": "SUSPEK",
            "witnesses": "SAKSI",
        }
        for key, cat in ollama_key_map.items():
            for val in ollama_entities.get(key, []):
                if val in text:
                    _register(val, cat, "ollama")

        # 2. Enjin Regex Pintar Malaysia
        for m in MYKAD_RE.finditer(text):
            _register(m.group(1), "NO_KP", "regex")

        for m in MYKAD_SPACED_RE.finditer(text):
            _register(m.group(1), "NO_KP", "regex")

        for m in MYKAD_COMPACT_RE.finditer(text):
            _register(m.group(1), "NO_KP", "regex")

        for m in SSM_RE.finditer(text):
            _register(m.group(0), "NO_SSM", "regex")

        for m in MYKAD_UNLABELED_12_RE.finditer(text):
            cand12 = m.group(1)
            if cand12 not in found_items and _is_valid_unlabeled_mykad_12(cand12):
                _register(cand12, "NO_KP", "regex")

        for m in PASSPORT_RE.finditer(text):
            _register(m.group(1), "PASPORT", "regex")

        for m in PHONE_RE.finditer(text):
            _register(m.group(0), "NO_TEL", "regex")

        for m in EMAIL_RE.finditer(text):
            email_val = m.group(0)
            if redact_moh_emails or not email_val.lower().endswith("@moh.gov.my"):
                _register(email_val, "EMEL", "regex")

        if redact_moh_emails:
            for m in KKM_CARD_RE.finditer(text):
                _register(m.group(1), "KAD_KUASA", "regex")

        for m in RESIDENTIAL_ADDR_RE.finditer(text):
            addr_val = m.group(1).strip()
            if len(addr_val) >= 8 and not (addr_val.startswith("[") and addr_val.endswith("]")):
                _register(addr_val, "ALAMAT", "regex")

        if redact_moh_emails:
            for m in INCIDENT_ADDR_RE.finditer(text):
                addr_val = m.group(1).strip()
                if len(addr_val) >= 8 and not (addr_val.startswith("[") and addr_val.endswith("]")):
                    _register(addr_val, "ALAMAT", "regex")

        for m in PREMISE_LABEL_RE.finditer(text):
            raw_prem = m.group(1).strip()
            # Jika ada maklumat syarikat dalam kurungan seperti "Tapak Bina X (Apex Bina Sdn. Bhd.)", daftar kedua-duanya
            paren = re.search(r"\(([^)]+(?:Sdn\.?\s*Bhd\.?|Enterprise|Trading)[^)]*)\)", raw_prem, flags=re.I)
            if paren:
                _register(paren.group(1), "PREMIS", "regex")
            _register(raw_prem, "PREMIS", "regex")

        for m in COMPANY_PHRASE_RE.finditer(text):
            _register(m.group(1), "PREMIS", "regex")

        for m in RESTORAN_PHRASE_RE.finditer(text):
            _register(m.group(1), "PREMIS", "regex")

        for m in SUSPECT_LABEL_RE.finditer(text):
            _register(m.group(1), "SUSPEK", "regex")

        for m in WITNESS_LABEL_RE.finditer(text):
            _register(m.group(1), "SAKSI", "regex")

        for m in MALAYSIAN_NAME_RE.finditer(text):
            candidate = self._clean_candidate(m.group(1))
            if candidate not in found_items:
                start = max(0, m.start() - 60)
                context_before = text[start : m.start()].lower()
                if any(w in context_before for w in ("saksi", "diambil oleh")):
                    _register(candidate, "SAKSI", "regex")
                else:
                    _register(candidate, "SUSPEK", "regex")

        ordered_items = sorted(
            found_items.items(),
            key=lambda kv: (text.find(kv[0]) if text.find(kv[0]) >= 0 else 10**9, -len(kv[0])),
        )

        counters: Dict[str, int] = {
            "SUSPEK": 0,
            "SAKSI": 0,
            "PREMIS": 0,
            "NO_KP": 0,
            "PASPORT": 0,
            "NO_SSM": 0,
            "NO_TEL": 0,
            "EMEL": 0,
            "ALAMAT": 0,
            "KAD_KUASA": 0,
        }
        token_map: Dict[str, str] = {}
        entities: List[RedactedEntity] = []
        value_to_token: Dict[str, str] = {}

        for original_val, (category, source) in ordered_items:
            counters[category] = counters.get(category, 0) + 1
            token = f"[{category}_{counters[category]}]"
            token_map[token] = original_val
            value_to_token[original_val] = token
            entities.append(
                RedactedEntity(
                    token=token,
                    category=category,
                    original=original_val,
                    source=source,
                )
            )

        redacted_text = text
        for original_val in sorted(value_to_token.keys(), key=len, reverse=True):
            redacted_text = redacted_text.replace(original_val, value_to_token[original_val])

        if ollama_entities and ollama_available:
            engine_used = f"ollama ({self.ollama_model}) + regex-kkm"
        elif ollama_available:
            engine_used = f"ollama ({self.ollama_model}) + regex-kkm"
        else:
            engine_used = "regex-kkm (ollama-offline)"

        return RedactionResult(
            original_text=text,
            redacted_text=redacted_text,
            token_map=token_map,
            entities=entities,
            engine_used=engine_used,
            ollama_available=ollama_available,
            warnings=warnings,
        )

    @staticmethod
    def rehydrate(text: str, token_map: Dict[str, str]) -> str:
        if not text or not token_map:
            return text
        restored = text
        for token in sorted(token_map.keys(), key=len, reverse=True):
            restored = restored.replace(token, token_map[token])
        return restored
