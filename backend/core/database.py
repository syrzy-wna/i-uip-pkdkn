"""Pangkalan Data SQLite tempatan (`data/uip_command.db`) untuk UIP-Command.

Menyimpan:
1. Tetapan runtime (GEMINI_API_KEY, OLLAMA_BASE_URL, pilihan model) supaya
   boleh diubah terus dari antaramuka web tanpa menyunting fail .env.
2. Daftar Kes IP PKD (ip_cases) lengkap dengan teks kes, status senarai semak
   fail IP (Bahagian A-G), laporan semakan Pra-TPR terkini, dan draf dokumen.
"""

from __future__ import annotations

import base64
import difflib
import hashlib
import json
import re
import secrets
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from backend.core.config import settings
from backend.services.sample_cases import SAMPLE_CASES


LEGACY_TO_SSPA_GRADE: Dict[str, str] = {
    "U29": "U5",
    "U32": "U6",
    "U36": "U7",
    "U38": "U7",
    "U40": "U8",
    "U41": "U9",
    "U42": "U9",
    "U41/U42": "U9",
    "U44": "U10",
    "U48": "U12",
    "U52": "U13",
    "U54": "U14",
    "UD41": "UD9",
    "UD43": "UD9",
    "UD44": "UD10",
    "UD48": "UD12",
    "UD52": "UD13",
    "UD54": "UD14",
    "C41": "C9",
    "C44": "C10",
    "C48": "C12",
    "C52": "C13",
    "C54": "C14",
}

ADVISOR_ACT_META: tuple[tuple[str, str], ...] = (
    ("Akta 852", "Akta Kawalan Produk Merokok Demi Kesihatan Awam 2024"),
    ("Akta 281", "Akta Makanan 1983 & Peraturan-Peraturan Kebersihan Makanan 2009"),
    ("Akta 154", "Akta Pemusnahan Serangga Pembawa Penyakit 1975"),
    ("Akta 342", "Akta Pencegahan dan Pengawalan Penyakit Berjangkit 1988"),
    ("Akta 593", "Kanun Tatacara Jenayah (KTJ)"),
    ("Akta 56", "Akta Keterangan 1950 (Seksyen 90A)"),
    ("Akta Lain / Rujukan Silang", "Rujukan Silang Agensi & Akta Berkaitan"),
)


def _match_canonical_act_from_text(text: str) -> Optional[str]:
    low = (text or "").strip().lower()
    if not low:
        return None
    if re.search(r"(?<!\d)(?:akta\s*)?852(?!\d)", low) or "produk merokok" in low or "ppkht" in low:
        return "Akta 852"
    if (
        re.search(r"(?<!\d)(?:akta\s*)?281(?!\d)", low)
        or "akta makanan" in low
        or "ppkm" in low
        or "ppm 1985" in low
    ):
        return "Akta 281"
    if (
        re.search(r"(?<!\d)(?:akta\s*)?154(?!\d)", low)
        or "serangga pembawa penyakit" in low
        or "apspp" in low
    ):
        return "Akta 154"
    if (
        re.search(r"(?<!\d)(?:akta\s*)?342(?!\d)", low)
        or "penyakit berjangkit" in low
        or "apppb" in low
    ):
        return "Akta 342"
    if (
        re.search(r"(?<!\d)(?:akta\s*)?593(?!\d)", low)
        or "kanun tatacara jenayah" in low
        or re.search(r"\bktj\b", low)
    ):
        return "Akta 593"
    if re.search(r"\bakta\s*56\b", low) or "akta keterangan" in low or "keterangan 1950" in low:
        return "Akta 56"
    return None


def classify_advisor_akta_group(
    raw_akta: Optional[str],
    analysis: Optional[Dict[str, Any]] = None,
) -> str:
    """Mengelaskan rekod Tanya Pakar kepada kategori Akta KKM yang konsisten."""
    ana = analysis if isinstance(analysis, dict) else {}
    primary_charge = ""
    charges = ana.get("cadangan_pertuduhan")
    if isinstance(charges, list) and charges and isinstance(charges[0], dict):
        primary_charge = str(charges[0].get("seksyen_kesalahan") or "")

    first_cit_act = ""
    citations = ana.get("statutory_citations")
    if isinstance(citations, list) and citations and isinstance(citations[0], dict):
        first_cit_act = str(citations[0].get("akta_code") or "")

    for candidate in (
        str(ana.get("akta_disyorkan") or ""),
        str(raw_akta or ""),
        primary_charge,
        first_cit_act,
    ):
        matched = _match_canonical_act_from_text(candidate)
        if matched:
            return matched
    return "Akta Lain / Rujukan Silang"


def _normalize_advisor_question_key(text: str) -> str:
    cleaned = re.sub(r"[^\w]+", " ", (text or "").lower(), flags=re.UNICODE)
    return re.sub(r"\s+", " ", cleaned).strip()


_EXTRA_QA_NORMALIZATIONS: Dict[str, str] = {
    "tak": "tidak",
    "tk": "tidak",
    "x": "tidak",
    "buleh": "boleh",
    "bleh": "boleh",
    "kompun": "kompaun",
    "keje": "kerja",
    "tmpt": "tempat",
    "klu": "kalau",
    "klo": "kalau",
    "mcmana": "bagaimana",
    "camana": "bagaimana",
    "restoren": "restoran",
    "berkarat": "karat",
    "luput tarikh": "luput",
    "tamat tempoh": "luput",
}

_GENERIC_QA_TOKENS = {
    "kes",
    "boleh",
    "kompaun",
    "seksyen",
    "peraturan",
    "akta",
    "tindakan",
    "soalan",
    "caj",
    "dakwa",
    "siasat",
    "buka",
    "notis",
    "hukuman",
    "denda",
    "buat",
    "guna",
    "rujuk",
    "pakar",
    "uip",
    "ppkp",
    "kkm",
    "pkd",
    "sila",
    "mohon",
    "tanya",
    "tahu",
    "kena",
    "perlu",
    "wajib",
    "minta",
    "mana",
    "berapa",
    "status",
    "prosedur",
    "langkah",
    "sop",
    "terus",
    "terima",
}

_DISTINCT_QA_SUBJECTS: tuple[tuple[str, ...], ...] = (
    ("covid",),
    ("tibi", "ptb", "tb"),
    ("aedes", "denggi"),
    ("tifoid",),
    ("hfmd",),
    ("vape", "rokok", "tembakau"),
)


def _qa_extract_tokens(text: str) -> tuple[str, set[str], set[str]]:
    """Menormalkan soalan perbualan PPKP dan memisahkan kata umum vs kata isi spesifik."""
    from backend.rag.statutory_store import MALAY_STOPWORDS, _normalize_query_text, _stem_malay_legal

    stripped = re.sub(r"\[[A-Z0-9_]+\]", " ", text or "")
    norm = _normalize_query_text(stripped)
    for src, dst in _EXTRA_QA_NORMALIZATIONS.items():
        norm = re.sub(rf"(?<!\w){re.escape(src)}(?!\w)", dst, norm)
    clean_norm = _normalize_advisor_question_key(norm)

    raw_words = re.findall(r"[a-zA-Z0-9]+", clean_norm)
    all_tokens: set[str] = set()
    for w in raw_words:
        if len(w) < 2 or w in MALAY_STOPWORDS:
            continue
        stemmed = _stem_malay_legal(w)
        tok = stemmed if len(stemmed) >= 2 else w
        all_tokens.add(tok)

    specific_tokens = all_tokens - _GENERIC_QA_TOKENS
    return clean_norm, all_tokens, specific_tokens


def _has_legal_fact_conflict(q_norm: str, cand_norm: str, cand_item: Dict[str, Any]) -> bool:
    """Mengelak padanan palsu antara kes yang berlawanan fakta kritikal (cth. positif vs negatif)."""
    # 1. Positif vs Negatif (cth. PTB Smear Positif vs Smear Negatif)
    q_has_neg = bool(re.search(r"\bnegatif\b", q_norm))
    q_has_pos = bool(re.search(r"\bpositif\b", q_norm))
    c_has_neg = bool(re.search(r"\bnegatif\b", cand_norm))
    c_has_pos = bool(re.search(r"\bpositif\b", cand_norm))
    if (q_has_neg and not q_has_pos and c_has_pos and not c_has_neg) or (
        c_has_neg and not c_has_pos and q_has_pos and not q_has_neg
    ):
        return True

    # 2. Taska/HFMD vs Premis Makanan
    taska_terms = ("taska", "tadika", "tabika", "hfmd")
    food_terms = ("restoran", "kedai makan", "dapur", "gerai", "tikus", "tifoid")
    q_taska = any(re.search(rf"\b{t}\b", q_norm) for t in taska_terms)
    c_taska = any(re.search(rf"\b{t}\b", cand_norm) for t in taska_terms)
    q_food = any(re.search(rf"\b{t}\b", q_norm) for t in food_terms)
    c_food = any(re.search(rf"\b{t}\b", cand_norm) for t in food_terms)
    if (q_taska and c_food and not c_taska) or (c_taska and q_food and not q_taska):
        return True

    # 3. Tapak Bina vs Kediaman (Akta 154)
    bina_terms = ("tapak bina", "pembinaan", "kontraktor")
    rumah_terms = ("rumah", "kediaman", "taman perumahan")
    q_bina = any(t in q_norm for t in bina_terms)
    c_bina = any(t in cand_norm for t in bina_terms)
    q_rumah = any(t in q_norm for t in rumah_terms)
    c_rumah = any(t in cand_norm for t in rumah_terms)
    if (q_bina and c_rumah and not c_bina) or (c_bina and q_rumah and not q_bina):
        return True

    # 4. Menjual kepada OBD vs OBD Merokok (Akta 852)
    jual_terms = ("jual", "menjual", "penjual", "pekedai")
    hisap_terms = ("hisap", "menghisap", "merokok")
    q_jual = any(re.search(rf"\b{t}\b", q_norm) for t in jual_terms)
    c_jual = any(re.search(rf"\b{t}\b", cand_norm) for t in jual_terms)
    q_hisap = any(re.search(rf"\b{t}\b", q_norm) for t in hisap_terms)
    c_hisap = any(re.search(rf"\b{t}\b", cand_norm) for t in hisap_terms)
    if (q_jual and not q_hisap and c_hisap and not c_jual) or (
        c_jual and not c_hisap and q_hisap and not q_jual
    ):
        return True

    # 5. Ketidaksepadanan penyakit/subjek berbeza (cth. COVID vs Tibi vs Aedes vs Tifoid)
    q_subjs = {
        idx
        for idx, group in enumerate(_DISTINCT_QA_SUBJECTS)
        if any(re.search(rf"\b{t}\b", q_norm) for t in group)
    }
    c_subjs = {
        idx
        for idx, group in enumerate(_DISTINCT_QA_SUBJECTS)
        if any(re.search(rf"\b{t}\b", cand_norm) for t in group)
    }
    if q_subjs and c_subjs and not (q_subjs & c_subjs):
        return True

    # 6. Jika pengguna menyebut nombor Akta secara eksplisit, elak petik daripada Akta berlainan
    q_explicit_act = _match_canonical_act_from_text(q_norm)
    cand_act = str(cand_item.get("akta_group") or "")
    if q_explicit_act and cand_act and q_explicit_act != cand_act:
        return True

    return False


def _is_reusable_qa_answer(entry: Dict[str, Any]) -> bool:
    """Memastikan hanya jawapan berkualiti (AI atau templat teras berstruktur) boleh dipetik semula."""
    if entry.get("is_ai_answered"):
        return True
    ans = entry.get("answer")
    if not isinstance(ans, dict):
        return False
    charges = ans.get("cadangan_pertuduhan") or []
    sop = ans.get("sop_lapangan") or []
    sc_id = str(ans.get("scenario_id") or "")
    alasan = str(ans.get("alasan_keputusan") or "").lower()
    if sc_id != "rag_custom_query" and len(charges) >= 1:
        return True
    return (
        len(charges) >= 1
        and len(sop) >= 2
        and "tiada padanan tepat dalam templat ringkas" not in alasan
    )


def normalize_sspa_grade(raw_grade: Optional[str], default: str = "U5") -> str:
    """Menukarkan gred SSM lama kepada gred SSPA semasa (U5, U6, U7, dll.)."""
    val = str(raw_grade or "").strip().upper()
    if not val:
        return default
    return LEGACY_TO_SSPA_GRADE.get(val, val)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")


def _hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    use_salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        use_salt.encode("utf-8"),
        120_000,
    ).hex()
    return digest, use_salt


def _verify_password(password: str, salt: str, expected_hash: str) -> bool:
    digest, _ = _hash_password(password, salt=salt)
    return secrets.compare_digest(digest, expected_hash)


class _PgCursorAdapter:
    """Penyesuai kursor psycopg supaya serasi dengan antara muka sqlite3."""

    def __init__(self, cur: Any) -> None:
        self._cur = cur

    @property
    def rowcount(self) -> int:
        return self._cur.rowcount

    def fetchone(self) -> Any:
        return self._cur.fetchone()

    def fetchall(self) -> List[Any]:
        return self._cur.fetchall()


class _PgConnAdapter:
    """Penyesuai sambungan PostgreSQL (psycopg) bagi Cloud Run dengan sintaks `?`."""

    def __init__(self, dsn: str) -> None:
        import psycopg
        from psycopg.rows import dict_row

        normalized = dsn.replace("postgres://", "postgresql://", 1) if dsn.startswith("postgres://") else dsn
        self._conn = psycopg.connect(normalized, row_factory=dict_row, connect_timeout=20)

    def __enter__(self) -> "_PgConnAdapter":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if exc_type is not None:
            self._conn.rollback()
        self._conn.close()

    @staticmethod
    def _translate_sql(sql: str) -> str:
        # Larikan literal '%' kepada '%%' sebelum menukar '?' kepada '%s' (keselamatan psycopg3)
        return sql.replace("%", "%%").replace("?", "%s")

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> _PgCursorAdapter:
        if params:
            cur = self._conn.execute(self._translate_sql(sql), params)
        else:
            cur = self._conn.execute(sql)
        return _PgCursorAdapter(cur)

    def commit(self) -> None:
        self._conn.commit()


class UIPDatabase:
    """Pengurus stor dwi-mod (SQLite WAL tempatan / PostgreSQL Cloud Run)."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = Path(db_path or settings.sqlite_db_path)
        self.use_postgres = bool(
            not db_path
            and settings.database_url.startswith(("postgres://", "postgresql://"))
        )
        if not self.use_postgres:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()
        self.load_runtime_settings_into_config()
        self._seed_initial_cases_if_empty()

    def _connect(self) -> Any:
        if self.use_postgres:
            return _PgConnAdapter(settings.database_url)
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS runtime_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ip_cases (
                    id TEXT PRIMARY KEY,
                    no_ip TEXT NOT NULL,
                    tajuk_kes TEXT NOT NULL,
                    akta_utama TEXT NOT NULL,
                    workflow TEXT NOT NULL DEFAULT 'audit_ip',
                    badge TEXT NOT NULL DEFAULT 'Dalam Tindakan',
                    nama_okt TEXT NOT NULL DEFAULT '',
                    no_kp_okt TEXT NOT NULL DEFAULT '',
                    nama_premis TEXT NOT NULL DEFAULT '',
                    no_ssm TEXT NOT NULL DEFAULT '',
                    alamat_kejadian TEXT NOT NULL DEFAULT '',
                    tarikh_kejadian TEXT NOT NULL DEFAULT '',
                    masa_kejadian TEXT NOT NULL DEFAULT '',
                    pegawai_io TEXT NOT NULL DEFAULT '',
                    no_kad_kuasa TEXT NOT NULL DEFAULT '',
                    status_kes TEXT NOT NULL DEFAULT 'DALAM SIASATAN',
                    skor_audit REAL NOT NULL DEFAULT 0.0,
                    case_text TEXT NOT NULL,
                    checklist_json TEXT NOT NULL DEFAULT '{}',
                    audit_json TEXT NOT NULL DEFAULT '',
                    draft_json TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    password_salt TEXT NOT NULL,
                    full_name TEXT NOT NULL,
                    ic_number TEXT NOT NULL DEFAULT '',
                    designation TEXT NOT NULL DEFAULT 'Penolong Pegawai Kesihatan Persekitaran (PPKP)',
                    grade TEXT NOT NULL DEFAULT 'U5',
                    kkm_authority_card_no TEXT NOT NULL DEFAULT '',
                    prosecution_authorization_no TEXT NOT NULL DEFAULT '',
                    state_jkn TEXT NOT NULL DEFAULT 'Jabatan Kesihatan Negeri Terengganu',
                    district_pkd TEXT NOT NULL DEFAULT 'Pejabat Kesihatan Daerah Kuala Nerus',
                    office_address TEXT NOT NULL DEFAULT 'Pejabat Kesihatan Daerah Kuala Nerus, 21300 Kuala Nerus, Terengganu',
                    unit_assignment TEXT NOT NULL DEFAULT 'Unit Inspektorat dan Perundangan (UIP)',
                    default_magistrate_court TEXT NOT NULL DEFAULT 'MAHKAMAH MAJISTRET DI KUALA TERENGGANU, TERENGGANU',
                    system_role TEXT NOT NULL DEFAULT 'PEGAWAI_PENYIASAT',
                    default_computer_desc TEXT NOT NULL DEFAULT 'Komputer Meja Rasmi KKM Dell OptiPlex Pejabat PKD',
                    default_printer_desc TEXT NOT NULL DEFAULT 'Pencetak Laser Warna Pejabat PKD',
                    default_camera_desc TEXT NOT NULL DEFAULT 'Kamera Digital Rasmi Pejabat KKM',
                    auth_provider TEXT NOT NULL DEFAULT 'email',
                    last_seen_at TEXT NOT NULL DEFAULT '',
                    is_demo INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.commit()
            if self.use_postgres:
                conn.execute(
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS auth_provider TEXT NOT NULL DEFAULT 'email'"
                )
                conn.execute(
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_seen_at TEXT NOT NULL DEFAULT ''"
                )
                conn.commit()
            else:
                for col_sql in (
                    "ALTER TABLE users ADD COLUMN auth_provider TEXT NOT NULL DEFAULT 'email'",
                    "ALTER TABLE users ADD COLUMN last_seen_at TEXT NOT NULL DEFAULT ''",
                ):
                    try:
                        conn.execute(col_sql)
                    except sqlite3.OperationalError:
                        pass
                conn.commit()
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_sessions (
                    token TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS activity_logs (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL DEFAULT '',
                    user_email TEXT NOT NULL DEFAULT '',
                    user_name TEXT NOT NULL DEFAULT 'Pegawai Tetamu',
                    district_pkd TEXT NOT NULL DEFAULT 'PKD Kuala Nerus',
                    action_type TEXT NOT NULL,
                    action_detail TEXT NOT NULL DEFAULT '',
                    model_used TEXT NOT NULL DEFAULT 'local-statutory-engine',
                    is_cloud_api INTEGER NOT NULL DEFAULT 0,
                    est_input_tokens INTEGER NOT NULL DEFAULT 0,
                    est_output_tokens INTEGER NOT NULL DEFAULT 0,
                    est_cost_usd REAL NOT NULL DEFAULT 0.0,
                    est_cost_myr REAL NOT NULL DEFAULT 0.0,
                    latency_ms INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_activity_created_at ON activity_logs(created_at DESC)"
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS dev_archive_records (
                    id TEXT PRIMARY KEY,
                    category TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    endpoint TEXT NOT NULL DEFAULT '',
                    user_id TEXT NOT NULL DEFAULT '',
                    user_email TEXT NOT NULL DEFAULT '',
                    user_name TEXT NOT NULL DEFAULT '',
                    user_grade TEXT NOT NULL DEFAULT '',
                    district_pkd TEXT NOT NULL DEFAULT '',
                    state_jkn TEXT NOT NULL DEFAULT '',
                    akta_utama TEXT NOT NULL DEFAULT '',
                    case_id TEXT NOT NULL DEFAULT '',
                    title TEXT NOT NULL DEFAULT '',
                    preview_text TEXT NOT NULL DEFAULT '',
                    raw_input_text TEXT NOT NULL DEFAULT '',
                    redacted_input_text TEXT NOT NULL DEFAULT '',
                    raw_response_text TEXT NOT NULL DEFAULT '',
                    redacted_response_text TEXT NOT NULL DEFAULT '',
                    request_json TEXT NOT NULL DEFAULT '{}',
                    response_json TEXT NOT NULL DEFAULT '{}',
                    redacted_analysis_json TEXT NOT NULL DEFAULT '{}',
                    user_snapshot_json TEXT NOT NULL DEFAULT '{}',
                    pdpa_entities_masked INTEGER NOT NULL DEFAULT 0,
                    model_used TEXT NOT NULL DEFAULT '',
                    is_cloud_api INTEGER NOT NULL DEFAULT 0,
                    est_cost_myr REAL NOT NULL DEFAULT 0.0,
                    latency_ms INTEGER NOT NULL DEFAULT 0,
                    status_summary TEXT NOT NULL DEFAULT '',
                    has_file INTEGER NOT NULL DEFAULT 0,
                    file_name TEXT NOT NULL DEFAULT '',
                    file_content_type TEXT NOT NULL DEFAULT '',
                    file_size_bytes BIGINT NOT NULL DEFAULT 0,
                    file_sha256 TEXT NOT NULL DEFAULT '',
                    payload_sha256 TEXT NOT NULL DEFAULT '',
                    storage_backend TEXT NOT NULL DEFAULT 'sqlite_local_vault',
                    bucket_name TEXT NOT NULL DEFAULT '',
                    object_key TEXT NOT NULL DEFAULT '',
                    metadata_object_key TEXT NOT NULL DEFAULT '',
                    local_path TEXT NOT NULL DEFAULT '',
                    attachment_b64 TEXT NOT NULL DEFAULT '',
                    attachment_truncated INTEGER NOT NULL DEFAULT 0,
                    sync_status TEXT NOT NULL DEFAULT 'db_fallback',
                    sync_error TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_dev_archive_created_at ON dev_archive_records(created_at DESC)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_dev_archive_category ON dev_archive_records(category, created_at DESC)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_dev_archive_user_email ON dev_archive_records(user_email, created_at DESC)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_dev_archive_case_id ON dev_archive_records(case_id)"
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS dev_vault_access_logs (
                    id TEXT PRIMARY KEY,
                    dev_email TEXT NOT NULL,
                    action TEXT NOT NULL,
                    record_id TEXT NOT NULL DEFAULT '',
                    detail TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                )
                """
            )
            # Produksi: pastikan tiada akaun demo palsu atau log seed tinggal dalam pangkalan data
            conn.execute("DELETE FROM users WHERE is_demo = 1")
            conn.execute("DELETE FROM activity_logs WHERE id LIKE ?", ("act-seed-%",))
            # Penjajaran gred SSM lama kepada SSPA (U29->U5, U32->U6, U36->U7, dll.)
            for old_g, new_g in LEGACY_TO_SSPA_GRADE.items():
                conn.execute("UPDATE users SET grade = ? WHERE UPPER(grade) = ?", (new_g, old_g))
            conn.commit()

    def load_runtime_settings_into_config(self) -> Dict[str, str]:
        with self._connect() as conn:
            rows = conn.execute("SELECT key, value FROM runtime_settings").fetchall()
        overrides = {row["key"]: row["value"] for row in rows}
        if overrides:
            settings.apply_overrides(overrides)
        return overrides

    def save_runtime_settings(self, payload: Dict[str, Optional[str]]) -> Dict[str, str]:
        now = _utc_now_iso()
        allowed = (
            "gemini_api_key",
            "google_client_id",
            "ollama_base_url",
            "ollama_model",
            "decision_model",
            "multimodal_model",
            "reasoning_model",
            "standard_fallback_model",
        )
        saved: Dict[str, str] = {}
        with self._connect() as conn:
            for key in allowed:
                if key not in payload or payload[key] is None:
                    continue
                val = str(payload[key]).strip()
                # Jangan timpa kunci API sebenar dengan rentetan bertopeng atau kosong melainkan diminta jelas
                if key == "gemini_api_key" and "..." in val and "*" not in val and len(val) <= 15:
                    continue
                conn.execute(
                    """
                    INSERT INTO runtime_settings (key, value, updated_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
                    """,
                    (key, val, now),
                )
                saved[key] = val
            conn.commit()
        settings.apply_overrides(saved)
        return saved

    def _seed_initial_cases_if_empty(self) -> None:
        with self._connect() as conn:
            count_row = conn.execute("SELECT COUNT(*) AS cnt FROM ip_cases").fetchone()
            if count_row and count_row["cnt"] > 0:
                return

        for sample in SAMPLE_CASES:
            self.upsert_case(
                {
                    "id": sample["id"],
                    "tajuk_kes": sample["title"],
                    "akta_utama": sample["akta_utama"],
                    "workflow": sample["workflow"],
                    "badge": sample["badge"],
                    "case_text": sample["text"],
                    "status_kes": (
                        "SEDIA DIHANTAR KE TPR"
                        if "Lengkap" in sample["badge"]
                        else ("KUIRI KRITIKAL" if "Kritikal" in sample["badge"] else "PERLU LENGKAPKAN")
                    ),
                }
            )

    def list_cases(self) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, no_ip, tajuk_kes, akta_utama, workflow, badge,
                       nama_okt, no_kp_okt, nama_premis, no_ssm, alamat_kejadian,
                       tarikh_kejadian, masa_kejadian, pegawai_io, no_kad_kuasa,
                       status_kes, skor_audit, case_text, checklist_json,
                       audit_json, draft_json, created_at, updated_at
                FROM ip_cases
                ORDER BY updated_at DESC
                """
            ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def get_case(self, case_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM ip_cases WHERE id = ?", (case_id,)).fetchone()
        return self._row_to_dict(row) if row else None

    def upsert_case(self, data: Dict[str, Any]) -> Dict[str, Any]:
        now = _utc_now_iso()
        case_id = str(data.get("id") or f"kes-{uuid.uuid4().hex[:8]}").strip()
        existing = self.get_case(case_id)

        case_text = str(data.get("case_text") or (existing["case_text"] if existing else ""))
        parsed = self._quick_extract_metadata(case_text)

        no_ip = str(data.get("no_ip") or parsed.get("no_ip") or (existing["no_ip"] if existing else "PKD/UIP/2026/BARU"))
        tajuk_kes = str(data.get("tajuk_kes") or (existing["tajuk_kes"] if existing else f"{no_ip} — {parsed.get('nama_premis') or 'Kes Penguatkuasaan'}"))
        akta_utama = str(data.get("akta_utama") or (existing["akta_utama"] if existing else "Akta 852"))
        workflow = str(data.get("workflow") or (existing["workflow"] if existing else "audit_ip"))
        badge = str(data.get("badge") or (existing["badge"] if existing else "Kes PKD"))

        nama_okt = str(data.get("nama_okt") or parsed.get("nama_okt") or (existing["nama_okt"] if existing else ""))
        no_kp_okt = str(data.get("no_kp_okt") or parsed.get("no_kp_okt") or (existing["no_kp_okt"] if existing else ""))
        nama_premis = str(data.get("nama_premis") or parsed.get("nama_premis") or (existing["nama_premis"] if existing else ""))
        no_ssm = str(data.get("no_ssm") or parsed.get("no_ssm") or (existing["no_ssm"] if existing else ""))
        alamat_kejadian = str(data.get("alamat_kejadian") or parsed.get("alamat_kejadian") or (existing["alamat_kejadian"] if existing else ""))
        tarikh_kejadian = str(data.get("tarikh_kejadian") or parsed.get("tarikh_kejadian") or (existing["tarikh_kejadian"] if existing else ""))
        masa_kejadian = str(data.get("masa_kejadian") or parsed.get("masa_kejadian") or (existing["masa_kejadian"] if existing else ""))
        pegawai_io = str(data.get("pegawai_io") or parsed.get("pegawai_io") or (existing["pegawai_io"] if existing else ""))
        no_kad_kuasa = str(data.get("no_kad_kuasa") or parsed.get("no_kad_kuasa") or (existing["no_kad_kuasa"] if existing else ""))
        status_kes = str(data.get("status_kes") or (existing["status_kes"] if existing else "DALAM SIASATAN"))
        skor_audit = float(data.get("skor_audit") if data.get("skor_audit") is not None else (existing["skor_audit"] if existing else 0.0))

        checklist_json = (
            json.dumps(data["checklist"], ensure_ascii=False)
            if isinstance(data.get("checklist"), dict)
            else (existing["checklist_json"] if existing else "{}")
        )
        audit_json = (
            json.dumps(data["audit_report"], ensure_ascii=False)
            if isinstance(data.get("audit_report"), dict)
            else (existing["audit_json"] if existing else "")
        )
        draft_json = (
            json.dumps(data["draft"], ensure_ascii=False)
            if isinstance(data.get("draft"), dict)
            else (existing["draft_json"] if existing else "")
        )
        created_at = existing["created_at"] if existing else now

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO ip_cases (
                    id, no_ip, tajuk_kes, akta_utama, workflow, badge,
                    nama_okt, no_kp_okt, nama_premis, no_ssm, alamat_kejadian,
                    tarikh_kejadian, masa_kejadian, pegawai_io, no_kad_kuasa,
                    status_kes, skor_audit, case_text, checklist_json,
                    audit_json, draft_json, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    no_ip=excluded.no_ip,
                    tajuk_kes=excluded.tajuk_kes,
                    akta_utama=excluded.akta_utama,
                    workflow=excluded.workflow,
                    badge=excluded.badge,
                    nama_okt=excluded.nama_okt,
                    no_kp_okt=excluded.no_kp_okt,
                    nama_premis=excluded.nama_premis,
                    no_ssm=excluded.no_ssm,
                    alamat_kejadian=excluded.alamat_kejadian,
                    tarikh_kejadian=excluded.tarikh_kejadian,
                    masa_kejadian=excluded.masa_kejadian,
                    pegawai_io=excluded.pegawai_io,
                    no_kad_kuasa=excluded.no_kad_kuasa,
                    status_kes=excluded.status_kes,
                    skor_audit=excluded.skor_audit,
                    case_text=excluded.case_text,
                    checklist_json=excluded.checklist_json,
                    audit_json=excluded.audit_json,
                    draft_json=excluded.draft_json,
                    updated_at=excluded.updated_at
                """,
                (
                    case_id,
                    no_ip,
                    tajuk_kes,
                    akta_utama,
                    workflow,
                    badge,
                    nama_okt,
                    no_kp_okt,
                    nama_premis,
                    no_ssm,
                    alamat_kejadian,
                    tarikh_kejadian,
                    masa_kejadian,
                    pegawai_io,
                    no_kad_kuasa,
                    status_kes,
                    skor_audit,
                    case_text,
                    checklist_json,
                    audit_json,
                    draft_json,
                    created_at,
                    now,
                ),
            )
            conn.commit()
        return self.get_case(case_id) or {}

    def delete_case(self, case_id: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM ip_cases WHERE id = ?", (case_id,))
            conn.commit()
            return cur.rowcount > 0

    def register_user(
        self, payload: Dict[str, Any], create_session_token: bool = True
    ) -> Dict[str, Any]:
        email = str(payload.get("email") or "").strip().lower()
        password = str(payload.get("password") or "")
        full_name = str(payload.get("full_name") or "").strip()
        if not email or "@" not in email:
            raise ValueError("Sila masukkan alamat emel rasmi yang sah.")
        if len(password) < 6:
            raise ValueError("Kata laluan mestilah sekurang-kurangnya 6 aksara.")
        if len(full_name) < 3:
            raise ValueError("Sila masukkan nama penuh pegawai mengikut MyKad.")

        with self._connect() as conn:
            exists = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
            if exists:
                raise ValueError("Emel pegawai ini telah didaftarkan. Sila log masuk.")

            user_id = str(payload.get("id") or f"usr-{uuid.uuid4().hex[:10]}")
            pw_hash, pw_salt = _hash_password(password)
            now = _utc_now_iso()
            conn.execute(
                """
                INSERT INTO users (
                    id, email, password_hash, password_salt, full_name, ic_number,
                    designation, grade, kkm_authority_card_no, prosecution_authorization_no,
                    state_jkn, district_pkd, office_address, unit_assignment,
                    default_magistrate_court, system_role, default_computer_desc,
                    default_printer_desc, default_camera_desc, auth_provider,
                    last_seen_at, is_demo, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    email,
                    pw_hash,
                    pw_salt,
                    full_name,
                    str(payload.get("ic_number") or "").strip(),
                    str(payload.get("designation") or "Penolong Pegawai Kesihatan Persekitaran (PPKP)").strip(),
                    normalize_sspa_grade(payload.get("grade"), "U5"),
                    str(payload.get("kkm_authority_card_no") or "").strip(),
                    str(payload.get("prosecution_authorization_no") or "").strip(),
                    str(payload.get("state_jkn") or "Jabatan Kesihatan Negeri Terengganu").strip(),
                    str(payload.get("district_pkd") or "Pejabat Kesihatan Daerah Kuala Nerus").strip(),
                    str(payload.get("office_address") or "Pejabat Kesihatan Daerah Kuala Nerus, 21300 Kuala Nerus, Terengganu").strip(),
                    str(payload.get("unit_assignment") or "Unit Inspektorat dan Perundangan (UIP)").strip(),
                    str(payload.get("default_magistrate_court") or "MAHKAMAH MAJISTRET DI KUALA TERENGGANU, DALAM NEGERI TERENGGANU DARUL IMAN").strip(),
                    str(payload.get("system_role") or "PEGAWAI_PENYIASAT").strip(),
                    str(payload.get("default_computer_desc") or "Komputer Meja Rasmi KKM Pejabat PKD").strip(),
                    str(payload.get("default_printer_desc") or "Pencetak Laser Warna Pejabat PKD").strip(),
                    str(payload.get("default_camera_desc") or "Kamera Digital Rasmi Penguatkuasaan PKD").strip(),
                    str(payload.get("auth_provider") or "email").strip(),
                    now,
                    int(payload.get("is_demo") or 0),
                    now,
                    now,
                ),
            )
            conn.commit()

        user = self.get_user_by_id(user_id)
        token = self.create_session(user_id) if create_session_token else ""
        return {"user": user, "token": token}

    def authenticate_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        clean_email = email.strip().lower()
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM users WHERE email = ?", (clean_email,)).fetchone()
        if not row:
            return None
        if not _verify_password(password, row["password_salt"], row["password_hash"]):
            return None
        token = self.create_session(row["id"])
        return {"user": self._safe_user_dict(row), "token": token}

    @staticmethod
    def _verify_google_oauth_token(id_token: str, access_token: str) -> Dict[str, str]:
        """Mengesahkan token Google OAuth 2.0 secara langsung dengan pelayan rasmi Google."""
        if not id_token and not access_token:
            raise ValueError(
                "Pengesahan Google OAuth 2.0 diperlukan. Sila log masuk melalui butang rasmi Google."
            )

        if id_token:
            try:
                resp = httpx.get(
                    "https://oauth2.googleapis.com/tokeninfo",
                    params={"id_token": id_token},
                    timeout=10.0,
                )
            except Exception as exc:
                raise ValueError(
                    f"Gagal menghubungi pelayan pengesahan Google OAuth: {exc}"
                ) from exc

            if resp.status_code != 200:
                raise ValueError("Token ID Google tidak sah atau sudah tamat tempoh.")

            claims = resp.json()
            if str(claims.get("email_verified", "")).lower() != "true":
                raise ValueError("Emel Akaun Google anda belum disahkan oleh Google.")
            if settings.google_client_id and claims.get("aud") != settings.google_client_id:
                raise ValueError(
                    "Token Google tidak sepadan dengan Google OAuth Client ID aplikasi ini."
                )
            email = str(claims.get("email") or "").strip().lower()
            full_name = str(claims.get("name") or "").strip()
            if not email or "@" not in email:
                raise ValueError("Maklumat emel daripada token Google tidak lengkap.")
            return {"email": email, "full_name": full_name}

        # Aliran Access Token (OAuth 2.0 Token Client Popup)
        try:
            resp = httpx.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10.0,
            )
        except Exception as exc:
            raise ValueError(
                f"Gagal menghubungi pelayan Google UserInfo: {exc}"
            ) from exc

        if resp.status_code != 200:
            raise ValueError("Token akses Google OAuth tidak sah atau sudah tamat tempoh.")

        claims = resp.json()
        if not claims.get("email_verified"):
            raise ValueError("Emel Akaun Google anda belum disahkan oleh Google.")
        email = str(claims.get("email") or "").strip().lower()
        full_name = str(claims.get("name") or "").strip()
        if not email or "@" not in email:
            raise ValueError("Maklumat emel daripada Google UserInfo tidak lengkap.")
        return {"email": email, "full_name": full_name}

    def authenticate_or_register_google_user(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Log masuk atau daftar akaun sebenar melalui pengesahan token Google OAuth 2.0."""
        id_token = str(payload.get("id_token") or "").strip()
        access_token = str(payload.get("access_token") or "").strip()
        verified = self._verify_google_oauth_token(id_token=id_token, access_token=access_token)

        email = verified["email"]
        full_name = verified["full_name"]
        if not full_name:
            prefix = email.split("@")[0].replace(".", " ").replace("_", " ").strip()
            full_name = prefix.title() if prefix else email
        if len(full_name) < 3:
            full_name = f"Pegawai {full_name}".strip()

        with self._connect() as conn:
            existing = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
            if existing:
                conn.execute(
                    "UPDATE users SET auth_provider = 'google', updated_at = ? WHERE id = ?",
                    (_utc_now_iso(), existing["id"]),
                )
                conn.commit()
        if existing:
            token = self.create_session(existing["id"])
            refreshed = self.get_user_by_id(existing["id"]) or self._safe_user_dict(existing)
            return {
                "user": refreshed,
                "token": token,
                "is_new_account": False,
                "auth_provider": "google",
            }

        reg_res = self.register_user(
            {
                "email": email,
                "password": secrets.token_urlsafe(24),
                "full_name": full_name,
                "ic_number": payload.get("ic_number") or "",
                "designation": payload.get("designation") or "Penolong Pegawai Kesihatan Persekitaran (PPKP)",
                "grade": normalize_sspa_grade(payload.get("grade"), "U5"),
                "kkm_authority_card_no": payload.get("kkm_authority_card_no") or "",
                "state_jkn": payload.get("state_jkn") or "Jabatan Kesihatan Negeri Terengganu",
                "district_pkd": payload.get("district_pkd") or "Pejabat Kesihatan Daerah Kuala Nerus",
                "office_address": payload.get("office_address") or "Pejabat Kesihatan Daerah Kuala Nerus, Lot PT 37820, Seberang Takir, 21300 Kuala Nerus, Terengganu",
                "default_magistrate_court": payload.get("default_magistrate_court") or "MAHKAMAH MAJISTRET DI KUALA TERENGGANU, DALAM NEGERI TERENGGANU DARUL IMAN",
                "system_role": payload.get("system_role") or "PEGAWAI_PENYIASAT",
                "auth_provider": "google",
            },
            create_session_token=True,
        )
        return {
            **reg_res,
            "is_new_account": True,
            "auth_provider": "google",
        }

    def create_session(self, user_id: str) -> str:
        token = secrets.token_urlsafe(32)
        now = _utc_now_iso()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO user_sessions (token, user_id, created_at, last_seen_at) VALUES (?, ?, ?, ?)",
                (token, user_id, now, now),
            )
            conn.execute(
                "UPDATE users SET last_seen_at = ? WHERE id = ?",
                (now, user_id),
            )
            conn.commit()
        return token

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return self._safe_user_dict(row) if row else None

    def get_user_by_token(self, token: str) -> Optional[Dict[str, Any]]:
        if not token:
            return None
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT u.* FROM users u
                JOIN user_sessions s ON s.user_id = u.id
                WHERE s.token = ?
                """,
                (token,),
            ).fetchone()
            if row:
                conn.execute(
                    "UPDATE user_sessions SET last_seen_at = ? WHERE token = ?",
                    (_utc_now_iso(), token),
                )
                conn.commit()
        return self._safe_user_dict(row) if row else None

    def update_user_profile(
        self, user_id: str, payload: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        updatable = (
            "full_name",
            "ic_number",
            "designation",
            "grade",
            "kkm_authority_card_no",
            "prosecution_authorization_no",
            "state_jkn",
            "district_pkd",
            "office_address",
            "unit_assignment",
            "default_magistrate_court",
            "system_role",
            "default_computer_desc",
            "default_printer_desc",
            "default_camera_desc",
        )
        updates: List[str] = []
        params: List[Any] = []
        for field in updatable:
            if field in payload and payload[field] is not None:
                val = str(payload[field]).strip()
                if field == "grade":
                    val = normalize_sspa_grade(val, "U5")
                updates.append(f"{field} = ?")
                params.append(val)
        if not updates:
            return self.get_user_by_id(user_id)

        updates.append("updated_at = ?")
        params.append(_utc_now_iso())
        params.append(user_id)

        with self._connect() as conn:
            conn.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", tuple(params))
            conn.commit()
        return self.get_user_by_id(user_id)

    def logout_session(self, token: str) -> bool:
        if not token:
            return False
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM user_sessions WHERE token = ?", (token,))
            conn.commit()
            return cur.rowcount > 0

    def list_demo_accounts(self) -> List[Dict[str, str]]:
        """Tiada akaun demo/palsu dalam mod produksi sebenar."""
        return []

    # ---------------- Telemetri Pembangun & Kos Operasi API ----------------

    USD_TO_MYR = 4.45

    @classmethod
    def _estimate_api_cost(
        cls,
        model_used: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> tuple[bool, float, float]:
        """Menganggarkan kos panggilan API dalam USD dan MYR mengikut model sebenar."""
        m = (model_used or "").lower()
        is_local = (
            not m
            or any(
                tag in m
                for tag in (
                    "local",
                    "statutori",
                    "pantas",
                    "templat",
                    "bm25",
                    "regex",
                    "ollama",
                    "gemma3",
                    "cache",
                    "python-docx",
                    "simulasi",
                    "oauth",
                    "google-gis",
                )
            )
        )
        if is_local or "gemini" not in m:
            return False, 0.0, 0.0

        # Kadar rujukan rasmi Gemini Pay-As-You-Go (USD per 1,000,000 token)
        if any(k in m for k in ("argon", "pro", "3.1-pro", "2.5-pro")):
            in_rate_per_1m = 1.25
            out_rate_per_1m = 10.00
        elif "decision" in m:
            in_rate_per_1m = 0.30
            out_rate_per_1m = 1.50
        else:
            # gemini-4-hydrogen / gemini-2.5-flash / standard flash
            in_rate_per_1m = 0.30
            out_rate_per_1m = 2.50

        usd = (max(0, input_tokens) / 1_000_000.0) * in_rate_per_1m + (
            max(0, output_tokens) / 1_000_000.0
        ) * out_rate_per_1m
        myr = usd * cls.USD_TO_MYR
        return True, round(usd, 6), round(myr, 5)

    def log_activity(
        self,
        *,
        action_type: str,
        action_detail: str = "",
        user: Optional[Dict[str, Any]] = None,
        model_used: str = "local-statutory-engine",
        est_input_tokens: int = 0,
        est_output_tokens: int = 0,
        latency_ms: int = 0,
    ) -> str:
        """Merekodkan setiap penggunaan aplikasi ke dalam SQLite untuk semakan Dev."""
        is_cloud, cost_usd, cost_myr = self._estimate_api_cost(
            model_used=model_used,
            input_tokens=est_input_tokens,
            output_tokens=est_output_tokens,
        )
        log_id = f"act-{uuid.uuid4().hex[:10]}"
        now = _utc_now_iso()
        user_id = str((user or {}).get("id") or "")
        user_email = str((user or {}).get("email") or "tetamu@pkd-kualanerus.local")
        user_name = str((user or {}).get("full_name") or "Pegawai UIP (Mod Tetamu)")
        district_pkd = str((user or {}).get("district_pkd") or "Pejabat Kesihatan Daerah Kuala Nerus")
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO activity_logs (
                    id, user_id, user_email, user_name, district_pkd,
                    action_type, action_detail, model_used, is_cloud_api,
                    est_input_tokens, est_output_tokens, est_cost_usd, est_cost_myr,
                    latency_ms, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    log_id,
                    user_id,
                    user_email,
                    user_name,
                    district_pkd,
                    action_type,
                    action_detail[:280],
                    model_used[:120],
                    1 if is_cloud else 0,
                    int(est_input_tokens),
                    int(est_output_tokens),
                    float(cost_usd),
                    float(cost_myr),
                    int(latency_ms),
                    now,
                ),
            )
            if user_id:
                conn.execute("UPDATE users SET last_seen_at = ? WHERE id = ?", (now, user_id))
            conn.commit()
        return log_id

    def get_dev_overview(self) -> Dict[str, Any]:
        """Memulangkan ringkasan siapa guna, apa dibuat & kos operasi untuk Konsol Dev (g.dev/syrzy)."""
        with self._connect() as conn:
            user_rows = conn.execute(
                """
                SELECT u.*,
                    (SELECT COUNT(*) FROM activity_logs a WHERE a.user_id = u.id OR LOWER(a.user_email) = LOWER(u.email)) AS total_actions,
                    (SELECT MAX(created_at) FROM activity_logs a WHERE a.user_id = u.id OR LOWER(a.user_email) = LOWER(u.email)) AS latest_activity_at
                FROM users u
                ORDER BY COALESCE(NULLIF(u.last_seen_at, ''), u.updated_at) DESC
                """
            ).fetchall()
            activity_rows = conn.execute(
                "SELECT * FROM activity_logs ORDER BY created_at DESC LIMIT 120"
            ).fetchall()
            action_breakdown_rows = conn.execute(
                """
                SELECT action_type,
                    COUNT(*) AS count,
                    SUM(CASE WHEN is_cloud_api = 1 THEN 1 ELSE 0 END) AS cloud_calls,
                    SUM(est_cost_usd) AS total_usd,
                    SUM(est_cost_myr) AS total_myr
                FROM activity_logs
                GROUP BY action_type
                ORDER BY count DESC
                """
            ).fetchall()
            totals_row = conn.execute(
                """
                SELECT
                    COUNT(*) AS total_actions,
                    SUM(CASE WHEN is_cloud_api = 1 THEN 1 ELSE 0 END) AS cloud_calls,
                    SUM(CASE WHEN is_cloud_api = 0 THEN 1 ELSE 0 END) AS local_calls,
                    COALESCE(SUM(est_input_tokens), 0) AS total_input_tokens,
                    COALESCE(SUM(est_output_tokens), 0) AS total_output_tokens,
                    COALESCE(SUM(est_cost_usd), 0.0) AS total_cost_usd,
                    COALESCE(SUM(est_cost_myr), 0.0) AS total_cost_myr,
                    COALESCE(AVG(latency_ms), 0.0) AS avg_latency_ms
                FROM activity_logs
                """
            ).fetchone()
            active_sessions_row = conn.execute("SELECT COUNT(*) AS cnt FROM user_sessions").fetchone()
            active_sessions = active_sessions_row["cnt"] if active_sessions_row else 0
            archive_count_rows = conn.execute(
                """
                SELECT LOWER(user_email) AS email_l, COUNT(*) AS cnt
                FROM dev_archive_records
                GROUP BY LOWER(user_email)
                """
            ).fetchall()

        archive_counts_by_email = {
            str(r["email_l"] or ""): int(r["cnt"] or 0) for r in archive_count_rows
        }

        users_list = []
        for r in user_rows:
            u = self._safe_user_dict(r)
            u["total_actions"] = int(r["total_actions"] or 0)
            u["latest_activity_at"] = r["latest_activity_at"] or u.get("last_seen_at") or u.get("updated_at") or ""
            u["archived_records_count"] = archive_counts_by_email.get(
                str(u.get("email") or "").strip().lower(), 0
            )
            users_list.append(u)

        activities_list = [dict(r) for r in activity_rows]
        breakdown_list = [
            {
                "action_type": r["action_type"],
                "count": int(r["count"] or 0),
                "cloud_calls": int(r["cloud_calls"] or 0),
                "total_usd": round(float(r["total_usd"] or 0.0), 6),
                "total_myr": round(float(r["total_myr"] or 0.0), 5),
            }
            for r in action_breakdown_rows
        ]

        return {
            "developer": "g.dev/syrzy",
            "host_office": "Pejabat Kesihatan Daerah Kuala Nerus, Terengganu",
            "google_client_id_configured": bool(settings.google_client_id),
            "gemini_api_key_configured": settings.has_gemini_key,
            "summary": {
                "total_users": len(users_list),
                "active_sessions": int(active_sessions or 0),
                "total_actions": int(totals_row["total_actions"] or 0),
                "cloud_api_calls": int(totals_row["cloud_calls"] or 0),
                "local_free_calls": int(totals_row["local_calls"] or 0),
                "total_input_tokens": int(totals_row["total_input_tokens"] or 0),
                "total_output_tokens": int(totals_row["total_output_tokens"] or 0),
                "total_cost_usd": round(float(totals_row["total_cost_usd"] or 0.0), 6),
                "total_cost_myr": round(float(totals_row["total_cost_myr"] or 0.0), 4),
                "avg_latency_ms": round(float(totals_row["avg_latency_ms"] or 0.0), 1),
                "usd_to_myr_rate": self.USD_TO_MYR,
                "action_breakdown": breakdown_list,
            },
            "pricing_reference": [
                {
                    "module": "Tanya Pakar UIP (Mod Pantas Statutori) & 17 Situasi & Rujukan Statutori",
                    "engine": "Enjin Tempatan Statutori (CPU PC)",
                    "cost_per_call_myr": "RM 0.00 (Percuma)",
                    "notes": "Tiada panggilan API awan; respons < 0.03s.",
                },
                {
                    "module": "Jana 16 Draf IP + Borang 114 + Eksport .docx + Penyamaran PDPA",
                    "engine": "Templat Rasmi KKM + Regex/Ollama Tempatan",
                    "cost_per_call_myr": "RM 0.00 (Percuma)",
                    "notes": "Diproses 100% dalam pelayan tempatan tanpa kos token.",
                },
                {
                    "module": "Google Sign-In / Daftar Pantas (OAuth 2.0 GIS)",
                    "engine": "Google Identity Services",
                    "cost_per_call_myr": "RM 0.00 (Percuma)",
                    "notes": "Tiada caj per pengguna atau caj bulanan daripada Google.",
                },
                {
                    "module": "Semak IP 20 Kriteria Pra-TPR (Mod AI Gemini)",
                    "engine": settings.decision_model,
                    "cost_per_call_myr": "~RM 0.007 / IP (< 1 sen)",
                    "notes": "~3,000 token masuk + ~500 keluar. Cache aktif (semakan ulangan RM 0.00).",
                },
                {
                    "module": "Ekstrak Gambar Premis / Sijil SSM / Tulisan Tangan (OCR)",
                    "engine": settings.multimodal_model,
                    "cost_per_call_myr": "~RM 0.005 - RM 0.008 / imej",
                    "notes": "Boleh guna Free Tier Google AI Studio (had harian) sebelum Pay-As-You-Go.",
                },
                {
                    "module": "Mod AI Mendalam (Tanya Pakar / Gubal Pertuduhan AI)",
                    "engine": f"{settings.reasoning_model} / Flash",
                    "cost_per_call_myr": "~RM 0.01 - RM 0.08 / panggilan",
                    "notes": "Hanya aktif jika pegawai togol 'Mod AI Mendalam' dihidupkan.",
                },
            ],
            "users": users_list,
            "activities": activities_list,
            "vault_summary": self.get_dev_vault_health(),
        }

    # ---------------- Arkib & Private Bucket Pembangun (zero4eleven@gmail.com) ----------------

    def insert_dev_archive(self, record: Dict[str, Any]) -> str:
        """Menyimpan satu rekod arkib pembangun ke jadual dev_archive_records."""
        rec_id = str(record.get("id") or f"arc-{uuid.uuid4().hex[:12]}")
        now = str(record.get("created_at") or _utc_now_iso())
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO dev_archive_records (
                    id, category, action_type, endpoint,
                    user_id, user_email, user_name, user_grade, district_pkd, state_jkn,
                    akta_utama, case_id, title, preview_text,
                    raw_input_text, redacted_input_text, raw_response_text, redacted_response_text,
                    request_json, response_json, redacted_analysis_json, user_snapshot_json,
                    pdpa_entities_masked, model_used, is_cloud_api, est_cost_myr, latency_ms,
                    status_summary, has_file, file_name, file_content_type, file_size_bytes,
                    file_sha256, payload_sha256, storage_backend, bucket_name,
                    object_key, metadata_object_key, local_path, attachment_b64,
                    attachment_truncated, sync_status, sync_error, created_at
                )
                VALUES (
                    ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?
                )
                """,
                (
                    rec_id,
                    str(record.get("category") or "DRAFT_COMPOUND"),
                    str(record.get("action_type") or ""),
                    str(record.get("endpoint") or ""),
                    str(record.get("user_id") or ""),
                    str(record.get("user_email") or ""),
                    str(record.get("user_name") or ""),
                    str(record.get("user_grade") or ""),
                    str(record.get("district_pkd") or ""),
                    str(record.get("state_jkn") or ""),
                    str(record.get("akta_utama") or ""),
                    str(record.get("case_id") or ""),
                    str(record.get("title") or "")[:300],
                    str(record.get("preview_text") or "")[:500],
                    str(record.get("raw_input_text") or ""),
                    str(record.get("redacted_input_text") or ""),
                    str(record.get("raw_response_text") or ""),
                    str(record.get("redacted_response_text") or ""),
                    str(record.get("request_json") or "{}"),
                    str(record.get("response_json") or "{}"),
                    str(record.get("redacted_analysis_json") or "{}"),
                    str(record.get("user_snapshot_json") or "{}"),
                    int(record.get("pdpa_entities_masked") or 0),
                    str(record.get("model_used") or "")[:120],
                    1 if record.get("is_cloud_api") else 0,
                    float(record.get("est_cost_myr") or 0.0),
                    int(record.get("latency_ms") or 0),
                    str(record.get("status_summary") or "")[:240],
                    1 if record.get("has_file") else 0,
                    str(record.get("file_name") or "")[:200],
                    str(record.get("file_content_type") or "")[:120],
                    int(record.get("file_size_bytes") or 0),
                    str(record.get("file_sha256") or ""),
                    str(record.get("payload_sha256") or ""),
                    str(record.get("storage_backend") or "sqlite_local_vault"),
                    str(record.get("bucket_name") or ""),
                    str(record.get("object_key") or ""),
                    str(record.get("metadata_object_key") or ""),
                    str(record.get("local_path") or ""),
                    str(record.get("attachment_b64") or ""),
                    1 if record.get("attachment_truncated") else 0,
                    str(record.get("sync_status") or "db_fallback"),
                    str(record.get("sync_error") or "")[:240],
                    now,
                ),
            )
            conn.commit()
        return rec_id

    def get_dev_vault_health(self) -> Dict[str, Any]:
        """Status kesihatan bucket & kiraan kategori arkib eksklusif Dev."""
        with self._connect() as conn:
            totals = conn.execute(
                """
                SELECT
                    COUNT(*) AS total_records,
                    COALESCE(SUM(CASE WHEN has_file = 1 THEN 1 ELSE 0 END), 0) AS total_files,
                    COALESCE(SUM(file_size_bytes), 0) AS total_bytes,
                    MAX(created_at) AS last_archived_at,
                    COALESCE(SUM(CASE WHEN sync_status != 'synced_s3' THEN 1 ELSE 0 END), 0) AS unsynced_count
                FROM dev_archive_records
                """
            ).fetchone()
            cat_rows = conn.execute(
                """
                SELECT category, COUNT(*) AS cnt
                FROM dev_archive_records
                GROUP BY category
                """
            ).fetchall()

        cat_map: Dict[str, int] = {
            "USER_REGISTER": 0,
            "ADVISOR_QA": 0,
            "AUDIT_IP": 0,
            "OCR_EVIDENCE": 0,
            "DRAFT_COMPOUND": 0,
        }
        for r in cat_rows:
            k = str(r["category"] or "")
            if k in cat_map:
                cat_map[k] = int(r["cnt"] or 0)

        totals_dict = dict(totals) if totals else {}
        total_records = int(totals_dict.get("total_records") or 0)
        cat_counts = {"ALL": total_records, **cat_map}

        s3_active = settings.has_dev_archive_s3
        if s3_active:
            backend_type = "s3_neon"
            backend_label = "Private S3 / Neon Object Storage Aktif"
        elif self.use_postgres:
            backend_type = "postgres_local_vault"
            backend_label = "PostgreSQL Vault + Local Vault"
        else:
            backend_type = "sqlite_local_vault"
            backend_label = "SQLite Vault + Local Vault"

        local_vault_rel = "dev_vault"
        try:
            local_vault_rel = str(settings.dev_archive_local_dir.name or "dev_vault")
        except Exception:
            pass

        return {
            "backend_type": backend_type,
            "backend_label": backend_label,
            "db_engine": "postgresql" if self.use_postgres else "sqlite",
            "is_cloud_bucket": bool(s3_active),
            "is_private_locked": True,
            "bucket_name": settings.dev_archive_bucket if s3_active else None,
            "bucket_prefix": settings.dev_archive_prefix if s3_active else None,
            "bucket_endpoint_host": settings.dev_archive_s3_host if s3_active else None,
            "bucket_region": settings.dev_archive_s3_region if s3_active else None,
            "local_vault_path": f"data/{local_vault_rel}" if settings.dev_archive_local_enabled else None,
            "is_ephemeral_warning": bool(not s3_active and not self.use_postgres),
            "total_records": total_records,
            "total_files": int(totals_dict.get("total_files") or 0),
            "total_bytes": int(totals_dict.get("total_bytes") or 0),
            "unsynced_count": int(totals_dict.get("unsynced_count") or 0),
            "last_archived_at": totals_dict.get("last_archived_at") or None,
            "allowed_dev_emails": list(settings.dev_admin_emails),
            "category_counts": cat_counts,
        }

    @staticmethod
    def _build_dev_archive_where(
        category: Optional[str] = None,
        q: Optional[str] = None,
        user_email: Optional[str] = None,
        has_file: bool = False,
    ) -> tuple[str, List[Any]]:
        clauses: List[str] = []
        params: List[Any] = []
        if category and category != "ALL":
            clauses.append("category = ?")
            params.append(category.strip())
        if user_email and user_email.strip():
            clauses.append("LOWER(user_email) = LOWER(?)")
            params.append(user_email.strip())
        if has_file:
            clauses.append("has_file = 1")
        if q and q.strip():
            pat = f"%{q.strip()}%"
            clauses.append(
                "("
                "LOWER(title) LIKE LOWER(?) OR "
                "LOWER(preview_text) LIKE LOWER(?) OR "
                "LOWER(user_name) LIKE LOWER(?) OR "
                "LOWER(user_email) LIKE LOWER(?) OR "
                "LOWER(district_pkd) LIKE LOWER(?) OR "
                "LOWER(file_name) LIKE LOWER(?) OR "
                "LOWER(akta_utama) LIKE LOWER(?) OR "
                "LOWER(redacted_input_text) LIKE LOWER(?)"
                ")"
            )
            params.extend([pat] * 8)
        where_sql = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        return where_sql, params

    def list_dev_archive(
        self,
        *,
        category: Optional[str] = None,
        q: Optional[str] = None,
        user_email: Optional[str] = None,
        has_file: bool = False,
        limit: int = 30,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Menyenaraikan rekod arkib ringan (tanpa blob attachment_b64) untuk Konsol Dev."""
        where_sql, params = self._build_dev_archive_where(
            category=category, q=q, user_email=user_email, has_file=has_file
        )
        safe_limit = max(1, min(int(limit), 200))
        safe_offset = max(0, int(offset))

        with self._connect() as conn:
            count_row = conn.execute(
                f"SELECT COUNT(*) AS cnt FROM dev_archive_records {where_sql}",
                tuple(params),
            ).fetchone()
            rows = conn.execute(
                f"""
                SELECT
                    id, category, action_type, title, preview_text,
                    akta_utama, user_id, user_email, user_name, district_pkd,
                    model_used, is_cloud_api, est_cost_myr, latency_ms,
                    has_file, file_name, file_content_type, file_size_bytes,
                    storage_backend, pdpa_entities_masked, created_at
                FROM dev_archive_records
                {where_sql}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                tuple(params + [safe_limit, safe_offset]),
            ).fetchall()

        health = self.get_dev_vault_health()
        items = []
        for r in rows:
            d = dict(r)
            items.append(
                {
                    "id": d["id"],
                    "category": d["category"],
                    "action_type": d["action_type"],
                    "title": d["title"],
                    "preview_text": d["preview_text"],
                    "akta_utama": d.get("akta_utama") or None,
                    "user_id": d.get("user_id") or None,
                    "user_email": d.get("user_email") or "",
                    "user_name": d.get("user_name") or "",
                    "district_pkd": d.get("district_pkd") or "",
                    "model_used": d.get("model_used") or "",
                    "is_cloud_api": bool(d.get("is_cloud_api")),
                    "est_cost_myr": round(float(d.get("est_cost_myr") or 0.0), 5),
                    "latency_ms": int(d.get("latency_ms") or 0),
                    "has_file": bool(d.get("has_file")),
                    "file_name": d.get("file_name") or None,
                    "file_content_type": d.get("file_content_type") or None,
                    "file_size_bytes": int(d.get("file_size_bytes") or 0) if d.get("has_file") else None,
                    "storage_backend": d.get("storage_backend") or health["backend_type"],
                    "pdpa_entities_masked": int(d.get("pdpa_entities_masked") or 0),
                    "created_at": d.get("created_at") or "",
                }
            )

        count_dict = dict(count_row) if count_row else {}
        return {
            "developer": "g.dev/syrzy",
            "storage_health": health,
            "category_counts": health["category_counts"],
            "total_matching": int(count_dict.get("cnt") or 0),
            "limit": safe_limit,
            "offset": safe_offset,
            "items": items,
        }

    def get_dev_archive_record(
        self, record_id: str, include_b64: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Mendapatkan satu rekod arkib lengkap berdasarkan ID."""
        cols = (
            "*"
            if include_b64
            else (
                "id, category, action_type, endpoint, user_id, user_email, user_name, "
                "user_grade, district_pkd, state_jkn, akta_utama, case_id, title, "
                "preview_text, raw_input_text, redacted_input_text, raw_response_text, "
                "redacted_response_text, request_json, response_json, redacted_analysis_json, "
                "user_snapshot_json, pdpa_entities_masked, model_used, is_cloud_api, "
                "est_cost_myr, latency_ms, status_summary, has_file, file_name, "
                "file_content_type, file_size_bytes, file_sha256, payload_sha256, "
                "storage_backend, bucket_name, object_key, metadata_object_key, "
                "local_path, attachment_truncated, sync_status, sync_error, created_at"
            )
        )
        with self._connect() as conn:
            row = conn.execute(
                f"SELECT {cols} FROM dev_archive_records WHERE id = ?",
                (record_id,),
            ).fetchone()
        return dict(row) if row else None

    def list_dev_archive_for_export(
        self,
        *,
        category: Optional[str] = None,
        q: Optional[str] = None,
        user_email: Optional[str] = None,
        limit: int = 500,
    ) -> List[Dict[str, Any]]:
        """Mendapatkan senarai rekod arkib (termasuk attachment_b64) bagi eksport bundle."""
        where_sql, params = self._build_dev_archive_where(
            category=category, q=q, user_email=user_email, has_file=False
        )
        safe_limit = max(1, min(int(limit), 2000))
        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT * FROM dev_archive_records
                {where_sql}
                ORDER BY created_at DESC
                LIMIT ?
                """,
                tuple(params + [safe_limit]),
            ).fetchall()
        return [dict(r) for r in rows]

    def list_unsynced_dev_archive(self, limit: int = 50) -> List[Dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 200))
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM dev_archive_records
                WHERE sync_status != 'synced_s3'
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def mark_dev_archive_synced(
        self,
        record_id: str,
        *,
        storage_backend: str,
        bucket_name: str,
        object_key: str,
        metadata_object_key: str,
        clear_b64: bool = True,
    ) -> None:
        with self._connect() as conn:
            if clear_b64:
                conn.execute(
                    """
                    UPDATE dev_archive_records
                    SET storage_backend = ?, bucket_name = ?, object_key = ?,
                        metadata_object_key = ?, sync_status = 'synced_s3',
                        sync_error = '', attachment_b64 = ''
                    WHERE id = ?
                    """,
                    (storage_backend, bucket_name, object_key, metadata_object_key, record_id),
                )
            else:
                conn.execute(
                    """
                    UPDATE dev_archive_records
                    SET storage_backend = ?, bucket_name = ?, object_key = ?,
                        metadata_object_key = ?, sync_status = 'synced_s3',
                        sync_error = ''
                    WHERE id = ?
                    """,
                    (storage_backend, bucket_name, object_key, metadata_object_key, record_id),
                )
            conn.commit()

    def log_dev_vault_access(
        self,
        dev_email: str,
        action: str,
        record_id: str = "",
        detail: str = "",
    ) -> None:
        log_id = f"dva-{uuid.uuid4().hex[:10]}"
        now = _utc_now_iso()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO dev_vault_access_logs (id, dev_email, action, record_id, detail, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (log_id, dev_email, action[:60], record_id[:60], detail[:240], now),
            )
            conn.commit()

    def list_all_users_safe(self) -> List[Dict[str, Any]]:
        """Memulangkan semua profil pengguna berdaftar (tanpa hash/salt) untuk dokumentasi Dev."""
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
        return [self._safe_user_dict(r) for r in rows]

    @staticmethod
    def _sanitize_advisor_answer(
        analysis: Dict[str, Any],
        *,
        akta_group: str,
        fallback_title: str,
        fallback_status: str,
        fallback_resp: str,
        fallback_model: str,
    ) -> Dict[str, Any]:
        """Menormalkan struktur jawapan Pakar UIP daripada rekod terkelas PDPA."""
        charges_raw = analysis.get("cadangan_pertuduhan")
        charges = [c for c in charges_raw if isinstance(c, dict)] if isinstance(charges_raw, list) else []
        citations_raw = analysis.get("statutory_citations")
        citations = [c for c in citations_raw if isinstance(c, dict)] if isinstance(citations_raw, list) else []

        def _str_list(key: str) -> List[str]:
            val = analysis.get(key)
            if isinstance(val, list):
                return [str(x) for x in val if str(x).strip()]
            return []

        return {
            "scenario_id": str(analysis.get("scenario_id") or "answered_archive"),
            "akta_disyorkan": str(analysis.get("akta_disyorkan") or akta_group),
            "tajuk_nasihat": str(analysis.get("tajuk_nasihat") or fallback_title),
            "keputusan_tindakan": str(
                analysis.get("keputusan_tindakan")
                or fallback_status
                or "Rujuk langkah SOP & petikan akta."
            ),
            "sesuai_buka_ip": bool(analysis.get("sesuai_buka_ip", False)),
            "alasan_keputusan": str(analysis.get("alasan_keputusan") or fallback_resp or ""),
            "cadangan_pertuduhan": charges,
            "sop_lapangan": _str_list("sop_lapangan"),
            "eksibit_wajib": _str_list("eksibit_wajib"),
            "perangkap_kesilapan": _str_list("perangkap_kesilapan"),
            "templat_ringkas": str(analysis.get("templat_ringkas") or ""),
            "draf_teks_kes_cadangan": str(analysis.get("draf_teks_kes_cadangan") or ""),
            "engine_used": str(
                analysis.get("engine_used")
                or fallback_model
                or "Mod Pantas — Rujukan Statutori UIP"
            ),
            "ai_attempted": bool(analysis.get("ai_attempted", False)),
            "ai_succeeded": bool(analysis.get("ai_succeeded", False)),
            "fallback_reason": analysis.get("fallback_reason"),
            "statutory_citations": citations,
        }

    def list_advisor_answered_questions(
        self,
        *,
        akta: Optional[str] = None,
        q: Optional[str] = None,
        limit: int = 120,
    ) -> Dict[str, Any]:
        """Mengumpul semua soalan Tanya Pakar yang telah dijawab (versi PDPA) dan mengelaskannya mengikut Akta."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    id, akta_utama, title, redacted_input_text, redacted_response_text,
                    redacted_analysis_json, model_used, is_cloud_api, status_summary, created_at
                FROM dev_archive_records
                WHERE category = ? AND action_type = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                ("ADVISOR_QA", "TANYA_PAKAR_UIP", 600),
            ).fetchall()

        deduped: Dict[tuple[str, str], Dict[str, Any]] = {}
        id_to_dedup_key: Dict[str, tuple[str, str]] = {}
        deferred_reused: List[tuple[str, str, tuple[str, str], Dict[str, Any]]] = []

        for r in rows:
            row = dict(r)
            raw_json_str = str(row.get("redacted_analysis_json") or "").strip()
            analysis: Dict[str, Any] = {}
            if raw_json_str and raw_json_str != "{}":
                try:
                    parsed = json.loads(raw_json_str)
                    if isinstance(parsed, dict):
                        analysis = parsed
                except Exception:
                    analysis = {}

            redacted_resp = str(row.get("redacted_response_text") or "").strip()
            if not analysis and not redacted_resp:
                continue

            redacted_q = re.sub(r"\s+", " ", str(row.get("redacted_input_text") or "")).strip()
            is_template_placeholder = (
                not redacted_q
                or redacted_q == "Rujuk templat situasi ini"
                or redacted_q.startswith("[Templat Situasi:")
            )
            fallback_tajuk = str(analysis.get("tajuk_nasihat") or "").strip()
            if is_template_placeholder:
                question_text = fallback_tajuk or re.sub(
                    r"\s+", " ", str(row.get("title") or "")
                ).strip()
            else:
                question_text = redacted_q

            if not question_text:
                continue

            norm_key = _normalize_advisor_question_key(question_text)
            if not norm_key:
                continue

            akta_group = classify_advisor_akta_group(row.get("akta_utama"), analysis)
            is_ai = bool(analysis.get("ai_succeeded") or row.get("is_cloud_api"))

            safe_fallback_title = fallback_tajuk or (
                question_text if len(question_text) <= 120 else f"{question_text[:117]}..."
            )
            answer_obj = self._sanitize_advisor_answer(
                analysis,
                akta_group=akta_group,
                fallback_title=safe_fallback_title,
                fallback_status=str(row.get("status_summary") or ""),
                fallback_resp=redacted_resp,
                fallback_model=str(row.get("model_used") or ""),
            )

            charges = answer_obj.get("cadangan_pertuduhan") or []
            primary_sec = (
                str(charges[0].get("seksyen_kesalahan") or "").strip()
                if charges and isinstance(charges[0], dict)
                else ""
            )
            alasan_clean = re.sub(r"\s+", " ", str(answer_obj.get("alasan_keputusan") or "")).strip()
            alasan_short = (
                alasan_clean if len(alasan_clean) <= 190 else f"{alasan_clean[:187]}..."
            )

            entry = {
                "id": str(row.get("id") or ""),
                "question": question_text,
                "akta_group": akta_group,
                "akta_disyorkan": str(answer_obj.get("akta_disyorkan") or akta_group),
                "tajuk_nasihat": str(answer_obj.get("tajuk_nasihat") or safe_fallback_title),
                "keputusan_tindakan": str(answer_obj.get("keputusan_tindakan") or ""),
                "alasan_ringkas": alasan_short,
                "seksyen_utama": primary_sec,
                "sesuai_buka_ip": bool(answer_obj.get("sesuai_buka_ip", False)),
                "is_ai_answered": is_ai,
                "engine_used": str(answer_obj.get("engine_used") or ""),
                "ask_count": 1,
                "last_asked_at": str(row.get("created_at") or ""),
                "answer": answer_obj,
            }

            dedup_key = (akta_group, norm_key)
            matched_coll_id = str(analysis.get("matched_collection_id") or "").strip()
            if analysis.get("from_qa_collection") and matched_coll_id:
                deferred_reused.append((matched_coll_id, entry["last_asked_at"], dedup_key, entry))
                continue

            existing = deduped.get(dedup_key)
            if not existing:
                deduped[dedup_key] = entry
            else:
                existing["ask_count"] += 1
                if entry["last_asked_at"] > existing["last_asked_at"]:
                    existing["last_asked_at"] = entry["last_asked_at"]
                if not existing["is_ai_answered"] and entry["is_ai_answered"]:
                    ask_total = existing["ask_count"]
                    latest_ts = existing["last_asked_at"]
                    deduped[dedup_key] = {
                        **entry,
                        "ask_count": ask_total,
                        "last_asked_at": latest_ts,
                    }
            id_to_dedup_key[entry["id"]] = dedup_key

        for target_id, reused_ts, dkey, fallback_entry in deferred_reused:
            resolved_key = id_to_dedup_key.get(target_id)
            if resolved_key and resolved_key in deduped:
                target_entry = deduped[resolved_key]
                target_entry["ask_count"] += 1
                if reused_ts > target_entry["last_asked_at"]:
                    target_entry["last_asked_at"] = reused_ts
            elif dkey in deduped:
                target_entry = deduped[dkey]
                target_entry["ask_count"] += 1
                if reused_ts > target_entry["last_asked_at"]:
                    target_entry["last_asked_at"] = reused_ts
            else:
                deduped[dkey] = fallback_entry
                id_to_dedup_key[fallback_entry["id"]] = dkey

        all_items = sorted(
            deduped.values(),
            key=lambda x: x.get("last_asked_at") or "",
            reverse=True,
        )

        act_counts: Dict[str, int] = {code: 0 for code, _ in ADVISOR_ACT_META}
        total_asks_all = 0
        for it in all_items:
            grp = str(it.get("akta_group") or "Akta Lain / Rujukan Silang")
            act_counts[grp] = act_counts.get(grp, 0) + 1
            total_asks_all += int(it.get("ask_count") or 1)

        akta_filter = (akta or "").strip()
        q_filter = (q or "").strip().lower()

        filtered: List[Dict[str, Any]] = []
        for it in all_items:
            if akta_filter and akta_filter.lower() != "semua":
                if (
                    it["akta_group"].lower() != akta_filter.lower()
                    and akta_filter.lower() not in it["akta_disyorkan"].lower()
                ):
                    continue
            if q_filter:
                haystack = " ".join(
                    [
                        it.get("question", ""),
                        it.get("tajuk_nasihat", ""),
                        it.get("keputusan_tindakan", ""),
                        it.get("seksyen_utama", ""),
                        it.get("akta_group", ""),
                        it.get("akta_disyorkan", ""),
                    ]
                ).lower()
                if q_filter not in haystack:
                    continue
            filtered.append(it)

        safe_limit = max(1, min(int(limit), 200))
        limited_items = filtered[:safe_limit]

        grouped_map: Dict[str, List[Dict[str, Any]]] = {}
        for it in limited_items:
            grouped_map.setdefault(it["akta_group"], []).append(it)

        groups = []
        for code, title in ADVISOR_ACT_META:
            grp_items = grouped_map.get(code)
            if grp_items:
                groups.append(
                    {
                        "akta_code": code,
                        "akta_title": title,
                        "count": len(grp_items),
                        "items": grp_items,
                    }
                )

        return {
            "total_questions": len(all_items),
            "total_asks": total_asks_all,
            "total_matching": len(limited_items),
            "act_counts": act_counts,
            "groups": groups,
            "items": limited_items,
        }

    def find_similar_answered_question(
        self,
        question: str,
        *,
        akta_hint: str = "Semua",
        min_score: float = 0.62,
    ) -> Optional[Dict[str, Any]]:
        """Mencari padanan soalan tepat atau lebih kurang sama daripada Koleksi Soalan & Jawapan Pakar."""
        raw_q = (question or "").strip()
        if len(raw_q) < 8 or raw_q.lower().startswith("rujuk templat situasi ini"):
            return None

        q_norm, q_all, q_spec = _qa_extract_tokens(raw_q)
        if len(q_all) < 3 or len(q_spec) < 2:
            return None

        data = self.list_advisor_answered_questions(
            akta=akta_hint if akta_hint and akta_hint != "Semua" else None,
            limit=200,
        )
        candidates = data.get("items") or []
        if not candidates:
            return None

        best_item: Optional[Dict[str, Any]] = None
        best_sim = 0.0
        best_rank = (-1.0, "")

        for item in candidates:
            if not _is_reusable_qa_answer(item):
                continue

            cand_q = str(item.get("question") or "").strip()
            if not cand_q:
                continue

            cand_norm, cand_all, cand_spec = _qa_extract_tokens(cand_q)
            if not cand_all:
                continue

            if _has_legal_fact_conflict(q_norm, cand_norm, item):
                continue

            if q_norm == cand_norm:
                sim = 1.0
            else:
                shared_spec = q_spec & cand_spec
                if len(shared_spec) < 2:
                    continue

                def _tok_weights(tokens: set[str]) -> float:
                    total = 0.0
                    for tok in tokens:
                        total += 0.6 if tok in _GENERIC_QA_TOKENS else 2.5
                    return total

                q_w = _tok_weights(q_all)
                c_w = _tok_weights(cand_all)
                shared_w = _tok_weights(q_all & cand_all)
                if q_w + c_w <= 0:
                    continue
                weighted_dice = (2.0 * shared_w) / (q_w + c_w)
                char_sim = difflib.SequenceMatcher(None, q_norm, cand_norm).ratio()
                sim = 0.72 * weighted_dice + 0.28 * char_sim

            if sim < min_score:
                continue

            rank_score = sim + (0.05 if item.get("is_ai_answered") else 0.0)
            rank_key = (rank_score, str(item.get("last_asked_at") or ""))
            if rank_key > best_rank:
                best_rank = rank_key
                best_sim = min(1.0, sim)
                best_item = item

        if not best_item:
            return None

        return {
            **best_item,
            "similarity": round(best_sim, 4),
            "similarity_percent": min(100, int(round(best_sim * 100))),
        }

    @staticmethod
    def _safe_user_dict(row: sqlite3.Row) -> Dict[str, Any]:
        d = dict(row)
        d.pop("password_hash", None)
        d.pop("password_salt", None)
        d["is_demo"] = bool(d.get("is_demo", 0))
        d["is_dev_admin"] = str(d.get("email") or "").strip().lower() in settings.dev_admin_emails
        return d

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
        d = dict(row)
        try:
            d["checklist"] = json.loads(d.get("checklist_json") or "{}")
        except Exception:
            d["checklist"] = {}
        try:
            d["audit_report"] = json.loads(d["audit_json"]) if d.get("audit_json") else None
        except Exception:
            d["audit_report"] = None
        try:
            d["draft"] = json.loads(d["draft_json"]) if d.get("draft_json") else None
        except Exception:
            d["draft"] = None
        return d

    @staticmethod
    def _quick_extract_metadata(text: str) -> Dict[str, str]:
        import re

        def _find(pat: str) -> str:
            m = re.search(pat, text, flags=re.I | re.M)
            return m.group(1).strip() if m else ""

        return {
            "no_ip": _find(r"(?:no\.?\s*ip|no\.?\s*kertas\s+siasatan)\s*[:\-]\s*([^\n\r]+)"),
            "tarikh_kejadian": _find(r"tarikh\s+kejadian\s*[:\-]\s*([^\n\r]+)"),
            "masa_kejadian": _find(r"masa\s+kejadian\s*[:\-]\s*([^\n\r]+)"),
            "nama_premis": _find(r"nama\s+premis\s*[:\-]\s*([^\n\r]+)"),
            "no_ssm": _find(r"no\.?\s*ssm\s*[:\-]\s*([^\n\r]+)"),
            "alamat_kejadian": _find(r"(?:alamat\s+kejadian|tempat\s+kejadian|alamat\s+premis)\s*[:\-]\s*([^\n\r]+)"),
            "nama_okt": _find(r"(?:nama\s+(?:suspek|okt|pemilik|pengurus\s+tapak|tertuduh)(?:\s*\([^)]+\))?)\s*[:\-]\s*([^\n\r]+)"),
            "no_kp_okt": _find(r"no\.?\s*k/?p\s*[:\-]\s*(\d{6}-\d{2}-\d{4})"),
            "pegawai_io": _find(r"(?:pegawai\s+penyiasat(?:\s*\(io\))?)\s*[:\-]\s*([^\n\r(]+)"),
            "no_kad_kuasa": _find(r"kad\s+kuasa\s*[:\-]\s*([A-Za-z0-9\-]+)"),
        }


_db_instance: Optional[UIPDatabase] = None


def get_uip_db() -> UIPDatabase:
    global _db_instance
    if _db_instance is None:
        _db_instance = UIPDatabase()
    return _db_instance
