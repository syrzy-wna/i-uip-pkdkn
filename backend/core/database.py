"""Pangkalan Data SQLite tempatan (`data/uip_command.db`) untuk UIP-Command.

Menyimpan:
1. Tetapan runtime (GEMINI_API_KEY, OLLAMA_BASE_URL, pilihan model) supaya
   boleh diubah terus dari antaramuka web tanpa menyunting fail .env.
2. Daftar Kes IP PKD (ip_cases) lengkap dengan teks kes, status senarai semak
   fail IP (Bahagian A-G), laporan semakan Pra-TPR terkini, dan draf dokumen.
"""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from backend.core.config import settings
from backend.services.sample_cases import SAMPLE_CASES


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
        self._conn = psycopg.connect(normalized, row_factory=dict_row, connect_timeout=15)

    def __enter__(self) -> "_PgConnAdapter":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if exc_type is not None:
            self._conn.rollback()
        self._conn.close()

    @staticmethod
    def _translate_sql(sql: str) -> str:
        return sql.replace("?", "%s")

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> _PgCursorAdapter:
        cur = self._conn.execute(self._translate_sql(sql), params)
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
                    grade TEXT NOT NULL DEFAULT 'U29',
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
            # Produksi: pastikan tiada akaun demo palsu atau log seed tinggal dalam pangkalan data
            conn.execute("DELETE FROM users WHERE is_demo = 1")
            conn.execute("DELETE FROM activity_logs WHERE id LIKE 'act-seed-%'")
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
                    str(payload.get("grade") or "U29").strip(),
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
                "grade": payload.get("grade") or "U29",
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
                updates.append(f"{field} = ?")
                params.append(str(payload[field]).strip())
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

        users_list = []
        for r in user_rows:
            u = self._safe_user_dict(r)
            u["total_actions"] = int(r["total_actions"] or 0)
            u["latest_activity_at"] = r["latest_activity_at"] or u.get("last_seen_at") or u.get("updated_at") or ""
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
                    "module": "Tanya Pakar UIP (Mod Pantas Statutori) & 11 Situasi Lazim",
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
        }

    @staticmethod
    def _safe_user_dict(row: sqlite3.Row) -> Dict[str, Any]:
        d = dict(row)
        d.pop("password_hash", None)
        d.pop("password_salt", None)
        d["is_demo"] = bool(d.get("is_demo", 0))
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
