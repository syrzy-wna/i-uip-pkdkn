"""Konfigurasi berpusat bagi backend UIP-Command (menyokong kemas kini runtime dari UI)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = Path(__file__).resolve().parents[1]

load_dotenv(BASE_DIR / ".env")
load_dotenv(BACKEND_DIR / ".env", override=False)


def _resolve_path(raw_path: str, default_rel: str) -> Path:
    candidate = Path(raw_path or default_rel)
    if candidate.is_absolute():
        return candidate
    if (BASE_DIR / candidate).exists():
        return (BASE_DIR / candidate).resolve()
    return (BASE_DIR / default_rel).resolve()


DEFAULT_GOOGLE_CLIENT_ID = (
    "290203327893-b7f42feigfscdd4rfo1eh1a3n5age7ev.apps.googleusercontent.com"
)
DEFAULT_DEV_ADMIN_EMAILS = "zero4eleven@gmail.com"


def _normalize_database_url(*env_names: str) -> str:
    """Membersihkan rentetan DATABASE_URL daripada awalan 'psql ' atau tanda petik luar."""
    for name in env_names:
        raw = os.getenv(name, "").strip()
        if not raw:
            continue
        if raw.lower().startswith("psql "):
            raw = raw[5:].strip()
        if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in ("'", '"'):
            raw = raw[1:-1].strip()
        if raw:
            return raw
    return ""


@dataclass
class Settings:
    """Tetapan persekitaran dan pemetaan model AI UIP-Command yang boleh dikemas kini secara runtime."""

    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "").strip()
    google_client_id: str = os.getenv("GOOGLE_CLIENT_ID", DEFAULT_GOOGLE_CLIENT_ID).strip()
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "gemma3:12b").strip()
    ollama_timeout_seconds: float = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "12.0"))

    # Pemetaan model Gemini (menyokong model terkini & standard Google AI Studio)
    decision_model: str = os.getenv("DECISION_MODEL", "gemini-decision-1").strip()
    multimodal_model: str = os.getenv("MULTIMODAL_MODEL", "gemini-4-hydrogen").strip()
    reasoning_model: str = os.getenv("REASONING_MODEL", "gemini-4-argon").strip()
    reasoning_model_alias: str = os.getenv("REASONING_MODEL_ALIAS", "gemini-3.1-pro-preview").strip()
    standard_fallback_model: str = os.getenv("STANDARD_GEMINI_MODEL", "gemini-3.8-flash").strip()

    # Direktori data, ChromaDB, SOP KKM 2024 & SQLite
    akta_dir: Path = _resolve_path(os.getenv("AKTA_DIR", "./data/akta"), "data/akta")
    sop_kkm_dir: Path = _resolve_path(
        os.getenv("SOP_KKM_DIR", "./data/sop_kkm_2024"), "data/sop_kkm_2024"
    )
    sop_brain_router_model: str = os.getenv("SOP_BRAIN_ROUTER_MODEL", "gemini-2.5-flash").strip()
    sop_brain_answer_model: str = os.getenv("SOP_BRAIN_ANSWER_MODEL", "gemini-2.5-pro").strip()
    sop_brain_use_context_cache: bool = (
        os.getenv("SOP_BRAIN_USE_CONTEXT_CACHE", "false").strip().lower() in ("1", "true", "yes")
    )
    chroma_persist_dir: Path = _resolve_path(
        os.getenv("CHROMA_PERSIST_DIR", "./data/chroma_db"), "data/chroma_db"
    )
    sqlite_db_path: Path = _resolve_path(
        os.getenv("SQLITE_DB_PATH", "./data/uip_command.db"), "data/uip_command.db"
    )
    database_url: str = _normalize_database_url(
        "DATABASE_URL",
        "NEON_DATABASE_URL",
        "POSTGRES_URL",
        "POSTGRESQL_URL",
    )

    # Arkib & Private Bucket Eksklusif Pembangun (zero4eleven@gmail.com sahaja)
    dev_archive_s3_endpoint: str = (
        os.getenv("DEV_ARCHIVE_S3_ENDPOINT") or os.getenv("AWS_ENDPOINT_URL_S3") or ""
    ).strip().rstrip("/")
    dev_archive_s3_access_key: str = (
        os.getenv("DEV_ARCHIVE_S3_ACCESS_KEY") or os.getenv("AWS_ACCESS_KEY_ID") or ""
    ).strip()
    dev_archive_s3_secret_key: str = (
        os.getenv("DEV_ARCHIVE_S3_SECRET_KEY") or os.getenv("AWS_SECRET_ACCESS_KEY") or ""
    ).strip()
    dev_archive_s3_region: str = (
        os.getenv("DEV_ARCHIVE_S3_REGION") or os.getenv("AWS_REGION") or "ap-southeast-1"
    ).strip()
    dev_archive_bucket: str = os.getenv("DEV_ARCHIVE_BUCKET", "dev-vault").strip()
    dev_archive_prefix: str = os.getenv("DEV_ARCHIVE_PREFIX", "dev-vault").strip().strip("/")
    dev_archive_db_max_bytes: int = int(os.getenv("DEV_ARCHIVE_DB_MAX_BYTES", "5242880"))
    dev_archive_max_upload_bytes: int = int(os.getenv("DEV_ARCHIVE_MAX_UPLOAD_BYTES", "20971520"))
    dev_archive_local_enabled: bool = (
        os.getenv("DEV_ARCHIVE_LOCAL_ENABLED", "true").strip().lower() not in ("0", "false", "no")
    )
    dev_archive_local_dir: Path = _resolve_path(
        os.getenv("DEV_ARCHIVE_LOCAL_DIR", "./data/dev_vault"), "data/dev_vault"
    )

    cors_origins_raw: str = os.getenv(
        "CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
    )
    dev_admin_emails_raw: str = os.getenv(
        "DEV_ADMIN_EMAILS", DEFAULT_DEV_ADMIN_EMAILS
    )

    @property
    def dev_admin_emails(self) -> List[str]:
        return [
            item.strip().lower()
            for item in self.dev_admin_emails_raw.split(",")
            if item.strip()
        ]

    @property
    def has_dev_archive_s3(self) -> bool:
        return bool(
            self.dev_archive_s3_endpoint
            and self.dev_archive_s3_access_key
            and self.dev_archive_s3_secret_key
            and self.dev_archive_bucket
        )

    @property
    def dev_archive_s3_host(self) -> str:
        raw = self.dev_archive_s3_endpoint
        if not raw:
            return ""
        without_scheme = raw.split("://", 1)[-1]
        if "@" in without_scheme:
            without_scheme = without_scheme.split("@", 1)[-1]
        return without_scheme.split("/", 1)[0]

    @property
    def has_gemini_key(self) -> bool:
        key = self.gemini_api_key.strip()
        return bool(key) and key != "your_gemini_api_key_here"

    @property
    def masked_gemini_key(self) -> str:
        if not self.has_gemini_key:
            return ""
        key = self.gemini_api_key.strip()
        if len(key) <= 8:
            return "*" * len(key)
        return f"{key[:4]}...{key[-4:]}"

    @property
    def cors_origins(self) -> List[str]:
        return [item.strip() for item in self.cors_origins_raw.split(",") if item.strip()]

    def apply_overrides(self, overrides: Dict[str, str]) -> None:
        if "gemini_api_key" in overrides and overrides["gemini_api_key"] is not None:
            self.gemini_api_key = str(overrides["gemini_api_key"]).strip()
        if "google_client_id" in overrides and overrides["google_client_id"] is not None:
            self.google_client_id = str(overrides["google_client_id"]).strip()
        if "ollama_base_url" in overrides and overrides["ollama_base_url"]:
            self.ollama_base_url = str(overrides["ollama_base_url"]).strip().rstrip("/")
        if "ollama_model" in overrides and overrides["ollama_model"]:
            self.ollama_model = str(overrides["ollama_model"]).strip()
        if "decision_model" in overrides and overrides["decision_model"]:
            self.decision_model = str(overrides["decision_model"]).strip()
        if "multimodal_model" in overrides and overrides["multimodal_model"]:
            self.multimodal_model = str(overrides["multimodal_model"]).strip()
        if "reasoning_model" in overrides and overrides["reasoning_model"]:
            self.reasoning_model = str(overrides["reasoning_model"]).strip()
        if "standard_fallback_model" in overrides and overrides["standard_fallback_model"]:
            self.standard_fallback_model = str(overrides["standard_fallback_model"]).strip()


settings = Settings()
