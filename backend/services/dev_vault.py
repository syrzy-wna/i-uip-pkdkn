"""Perkhidmatan Arkib & Bucket Eksklusif Pembangun (zero4eleven@gmail.com).

Menyediakan seni bina storan multi-lapisan:
1. Lapisan 1: Private S3-Compatible Object Storage (Neon Object Storage / GCS S3 Interop / R2 / S3)
   menggunakan klien pure-Python AWS SigV4 (tanpa kebergantungan boto3).
2. Lapisan 2: Pangkalan Data Kekal PostgreSQL / SQLite (dev_archive_records) termasuk
   penyamaran automatik PDPA (redacted) di samping teks & fail asal.
3. Lapisan 3: Folder Vault tempatan (data/dev_vault/) yang dikecualikan dari Git & Docker.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import io
import json
import re
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote, urlparse

import httpx

from backend.core.config import settings
from backend.core.database import UIPDatabase, _utc_now_iso
from backend.core.redactor import PrivacyRedactor

SENSITIVE_KEYS = {
    "password",
    "password_hash",
    "password_salt",
    "token",
    "id_token",
    "access_token",
    "refresh_token",
    "authorization",
    "x-auth-token",
    "gemini_api_key",
    "aws_access_key_id",
    "aws_secret_access_key",
    "dev_archive_s3_access_key",
    "dev_archive_s3_secret_key",
    "secret_key",
    "token_map",
}

EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()


def sanitize_filename(raw_name: Optional[str], fallback: str = "dokumen.bin") -> str:
    """Membersihkan nama fail daripada aksara path-traversal & suntikan header."""
    base = Path(str(raw_name or fallback)).name
    cleaned = re.sub(r"[\r\n\"'\\/;]+", "_", base)
    cleaned = re.sub(r"[^A-Za-z0-9._\-]+", "_", cleaned).strip("._")
    if not cleaned:
        return fallback
    return cleaned[:120]


def sanitize_payload(obj: Any) -> Any:
    """Menyingkirkan kunci rahsia (kata laluan, token, kunci API) secara rekursif."""
    if isinstance(obj, dict):
        cleaned: Dict[str, Any] = {}
        for k, v in obj.items():
            key_str = str(k)
            if key_str.strip().lower() in SENSITIVE_KEYS:
                continue
            cleaned[key_str] = sanitize_payload(v)
        return cleaned
    if isinstance(obj, list):
        return [sanitize_payload(item) for item in obj]
    return obj


def mask_ic_number(ic: Optional[str]) -> str:
    """Menyamarkan No. K/P pegawai untuk eksport versi PDPA."""
    val = str(ic or "").strip()
    if not val:
        return ""
    digits = re.sub(r"\D", "", val)
    if len(digits) == 12:
        return f"{digits[:6]}-**-**{digits[-2:]}"
    if len(val) > 4:
        return f"{'*' * (len(val) - 4)}{val[-4:]}"
    return "****"


def redact_for_vault(redactor: PrivacyRedactor, text: Optional[str]) -> Tuple[str, int]:
    """Menjalankan penyamaran PDPA tempatan pantas (Regex KKM, RM 0.00)."""
    src = str(text or "")
    if not src.strip():
        return src, 0
    try:
        res = redactor.redact(src, use_ollama=False)
        return res.redacted_text, len(res.entities)
    except Exception:
        return src, 0


def redact_json_value(redactor: PrivacyRedactor, value: Any) -> Any:
    """Menghasilkan salinan JSON selamat PDPA tanpa token_map dan menutup entiti PII."""
    if isinstance(value, dict):
        out: Dict[str, Any] = {}
        for k, v in value.items():
            kl = str(k).lower()
            if kl in SENSITIVE_KEYS or kl == "token_map":
                continue
            if kl in {"ic_number", "no_kp", "no_kp_okt", "no_kp_tertuduh"} and isinstance(v, str):
                out[str(k)] = mask_ic_number(v)
            elif kl == "original_text" and isinstance(v, str):
                red_txt, _ = redact_for_vault(redactor, v)
                out[str(k)] = red_txt
            else:
                out[str(k)] = redact_json_value(redactor, v)
        return out
    if isinstance(value, list):
        return [redact_json_value(redactor, item) for item in value]
    if isinstance(value, str):
        stripped = value.strip()
        if len(stripped) >= 5 and not (stripped.startswith("[") and stripped.endswith("]")):
            red_txt, _ = redact_for_vault(redactor, value)
            return red_txt
        return value
    return value


class PureSigV4S3Client:
    """Klien S3 serasi Neon Object Storage / GCS S3 / R2 menggunakan AWS SigV4 tulen."""

    def __init__(
        self,
        *,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
        region: str = "ap-southeast-1",
    ) -> None:
        self.endpoint_url = endpoint_url.strip().rstrip("/")
        self.access_key = access_key.strip()
        self.secret_key = secret_key.strip()
        self.region = (region or "ap-southeast-1").strip()

    def _build_url_and_uri(self, bucket: str, key: str) -> Tuple[str, str]:
        parsed = urlparse(self.endpoint_url)
        base_path = parsed.path.rstrip("/")
        clean_key = key.lstrip("/")
        encoded_key = quote(clean_key, safe="/-_.~")
        encoded_bucket = quote(bucket.strip(), safe="-_.~")
        canonical_uri = f"{base_path}/{encoded_bucket}/{encoded_key}"
        full_url = f"{parsed.scheme}://{parsed.netloc}{canonical_uri}"
        return full_url, canonical_uri

    @staticmethod
    def _hmac_sha256(key: bytes, msg: str) -> bytes:
        return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

    def _signing_key(self, date_stamp: str) -> bytes:
        k_date = self._hmac_sha256(("AWS4" + self.secret_key).encode("utf-8"), date_stamp)
        k_region = self._hmac_sha256(k_date, self.region)
        k_service = self._hmac_sha256(k_region, "s3")
        return self._hmac_sha256(k_service, "aws4_request")

    def _signed_headers(
        self,
        *,
        method: str,
        canonical_uri: str,
        payload_sha256: str,
        content_type: Optional[str] = None,
    ) -> Dict[str, str]:
        parsed = urlparse(self.endpoint_url)
        host = parsed.netloc
        now = datetime.now(timezone.utc)
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        date_stamp = now.strftime("%Y%m%d")

        headers_map: Dict[str, str] = {
            "host": host,
            "x-amz-content-sha256": payload_sha256,
            "x-amz-date": amz_date,
        }
        if content_type:
            headers_map["content-type"] = content_type

        sorted_keys = sorted(headers_map.keys())
        canonical_headers = "".join(f"{k}:{headers_map[k]}\n" for k in sorted_keys)
        signed_headers_str = ";".join(sorted_keys)

        canonical_request = "\n".join(
            [
                method.upper(),
                canonical_uri,
                "",  # tiada query string
                canonical_headers,
                signed_headers_str,
                payload_sha256,
            ]
        )
        credential_scope = f"{date_stamp}/{self.region}/s3/aws4_request"
        string_to_sign = "\n".join(
            [
                "AWS4-HMAC-SHA256",
                amz_date,
                credential_scope,
                hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
            ]
        )
        signature = hmac.new(
            self._signing_key(date_stamp),
            string_to_sign.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        auth_header = (
            f"AWS4-HMAC-SHA256 Credential={self.access_key}/{credential_scope}, "
            f"SignedHeaders={signed_headers_str}, Signature={signature}"
        )

        out_headers: Dict[str, str] = {
            "Authorization": auth_header,
            "x-amz-date": amz_date,
            "x-amz-content-sha256": payload_sha256,
        }
        if content_type:
            out_headers["Content-Type"] = content_type
        return out_headers

    def put_object(
        self,
        *,
        bucket: str,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> None:
        url, canonical_uri = self._build_url_and_uri(bucket, key)
        payload_hash = hashlib.sha256(data).hexdigest()
        headers = self._signed_headers(
            method="PUT",
            canonical_uri=canonical_uri,
            payload_sha256=payload_hash,
            content_type=content_type,
        )
        timeout = httpx.Timeout(connect=3.0, read=8.0, write=8.0, pool=3.0)
        resp = httpx.put(url, content=data, headers=headers, timeout=timeout)
        if not (200 <= resp.status_code < 300):
            raise RuntimeError(
                f"S3 PutObject gagal ({resp.status_code}): {resp.text[:180]}"
            )

    def get_object(self, *, bucket: str, key: str) -> bytes:
        url, canonical_uri = self._build_url_and_uri(bucket, key)
        headers = self._signed_headers(
            method="GET",
            canonical_uri=canonical_uri,
            payload_sha256=EMPTY_SHA256,
        )
        timeout = httpx.Timeout(connect=3.0, read=12.0, write=5.0, pool=3.0)
        resp = httpx.get(url, headers=headers, timeout=timeout)
        if not (200 <= resp.status_code < 300):
            raise RuntimeError(
                f"S3 GetObject gagal ({resp.status_code}): {resp.text[:180]}"
            )
        return resp.content


class DevArchiveVaultService:
    """Pengurus storan & eksport Arkib Eksklusif Pembangun (`zero4eleven@gmail.com`)."""

    def __init__(self, db: UIPDatabase, redactor: PrivacyRedactor) -> None:
        self.db = db
        self.redactor = redactor

    @staticmethod
    def _get_s3_client() -> Optional[PureSigV4S3Client]:
        if not settings.has_dev_archive_s3:
            return None
        return PureSigV4S3Client(
            endpoint_url=settings.dev_archive_s3_endpoint,
            access_key=settings.dev_archive_s3_access_key,
            secret_key=settings.dev_archive_s3_secret_key,
            region=settings.dev_archive_s3_region,
        )

    @staticmethod
    def _user_snapshot(user: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not user:
            return {}
        allow_keys = (
            "id",
            "email",
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
            "auth_provider",
            "created_at",
            "updated_at",
        )
        return {k: user[k] for k in allow_keys if k in user}

    def archive_event(
        self,
        *,
        category: str,
        action_type: str,
        endpoint: str,
        user: Optional[Dict[str, Any]] = None,
        title: str = "",
        akta_utama: str = "",
        case_id: str = "",
        raw_input_text: str = "",
        raw_response_text: str = "",
        request_payload: Optional[Dict[str, Any]] = None,
        analysis_payload: Optional[Dict[str, Any]] = None,
        model_used: str = "",
        is_cloud_api: bool = False,
        est_cost_myr: float = 0.0,
        latency_ms: int = 0,
        status_summary: str = "",
        attachment_bytes: Optional[bytes] = None,
        attachment_filename: Optional[str] = None,
        attachment_mime: Optional[str] = None,
    ) -> str:
        """Merekodkan setiap pengguna, soalan & dokumen analisis ke Bucket/Vault Pembangun."""
        record_id = f"arc-{uuid.uuid4().hex[:12]}"
        now_str = _utc_now_iso()
        now_utc = datetime.now(timezone.utc)
        yyyy, mm, dd = now_utc.strftime("%Y"), now_utc.strftime("%m"), now_utc.strftime("%d")

        safe_user = self._user_snapshot(user)
        safe_req = sanitize_payload(request_payload or {})
        safe_resp = sanitize_payload(analysis_payload or {})

        redacted_input, in_masked = redact_for_vault(self.redactor, raw_input_text)
        redacted_resp_txt, out_masked = redact_for_vault(self.redactor, raw_response_text)
        redacted_analysis = redact_json_value(self.redactor, safe_resp)

        # Pastikan IC pegawai dalam snapshot juga disamarkan untuk JSON versi PDPA
        pdpa_masked_total = in_masked + out_masked
        if safe_user.get("ic_number") and category == "USER_REGISTER":
            pdpa_masked_total = max(pdpa_masked_total, 1)

        preview_src = redacted_input or redacted_resp_txt or status_summary or title
        preview_clean = re.sub(r"\s+", " ", str(preview_src or "")).strip()[:280]

        has_file = bool(attachment_bytes)
        clean_fname = sanitize_filename(attachment_filename, "dokumen.bin") if has_file else ""
        clean_mime = str(attachment_mime or "application/octet-stream")[:120] if has_file else ""
        file_size = len(attachment_bytes) if attachment_bytes else 0
        file_sha256 = hashlib.sha256(attachment_bytes).hexdigest() if attachment_bytes else ""

        prefix = settings.dev_archive_prefix or "dev-vault"
        cat_slug = re.sub(r"[^a-z0-9_\-]+", "_", category.lower())
        meta_object_key = f"{prefix}/{yyyy}/{mm}/{dd}/{cat_slug}/{record_id}/record.json"
        file_object_key = (
            f"{prefix}/{yyyy}/{mm}/{dd}/{cat_slug}/{record_id}/attachment.bin" if has_file else ""
        )

        record_doc = {
            "id": record_id,
            "category": category,
            "action_type": action_type,
            "endpoint": endpoint,
            "created_at": now_str,
            "user": safe_user,
            "akta_utama": akta_utama,
            "case_id": case_id,
            "title": title or f"{action_type} ({clean_fname or akta_utama or 'UIP'})",
            "status_summary": status_summary,
            "model_used": model_used,
            "is_cloud_api": bool(is_cloud_api),
            "est_cost_myr": round(float(est_cost_myr or 0.0), 5),
            "latency_ms": int(latency_ms or 0),
            "raw_input_text": raw_input_text,
            "redacted_input_text": redacted_input,
            "raw_response_text": raw_response_text,
            "redacted_response_text": redacted_resp_txt,
            "request_payload": safe_req,
            "analysis_payload": safe_resp,
            "redacted_analysis_payload": redacted_analysis,
            "attachment": {
                "filename": clean_fname,
                "content_type": clean_mime,
                "size_bytes": file_size,
                "sha256": file_sha256,
                "object_key": file_object_key,
            }
            if has_file
            else None,
        }
        record_json_bytes = json.dumps(record_doc, ensure_ascii=False, indent=2).encode("utf-8")
        payload_sha256 = hashlib.sha256(record_json_bytes).hexdigest()

        storage_backend = "postgres_local_vault" if self.db.use_postgres else "sqlite_local_vault"
        bucket_name = ""
        sync_status = "db_fallback"
        sync_error = ""
        attachment_b64 = ""
        attachment_truncated = 0

        # Lapisan 1: Private S3 / Neon Object Storage Bucket (apabila dikonfigurasi)
        s3_client = self._get_s3_client()
        if s3_client is not None:
            try:
                s3_client.put_object(
                    bucket=settings.dev_archive_bucket,
                    key=meta_object_key,
                    data=record_json_bytes,
                    content_type="application/json; charset=utf-8",
                )
                if has_file and attachment_bytes is not None:
                    if file_size <= settings.dev_archive_max_upload_bytes:
                        s3_client.put_object(
                            bucket=settings.dev_archive_bucket,
                            key=file_object_key,
                            data=attachment_bytes,
                            content_type=clean_mime or "application/octet-stream",
                        )
                    else:
                        attachment_truncated = 1
                        sync_error = f"Lampiran melebihi had S3 ({file_size} bait)"
                storage_backend = "s3_neon"
                bucket_name = settings.dev_archive_bucket
                sync_status = "synced_s3"
            except Exception as exc:
                sync_status = "s3_error_fallback"
                sync_error = str(exc)[:220]

        # Lapisan 2: DB Blob Fallback (jika S3 belum aktif atau ralat sementara)
        if has_file and attachment_bytes is not None and sync_status != "synced_s3":
            if file_size <= settings.dev_archive_db_max_bytes:
                attachment_b64 = base64.b64encode(attachment_bytes).decode("ascii")
            else:
                attachment_truncated = 1
                if not sync_error:
                    sync_error = (
                        f"Fail melebihi had DB fallback ({file_size} bait > "
                        f"{settings.dev_archive_db_max_bytes} bait); metadata disimpan."
                    )

        # Lapisan 3: Folder Vault Tempatan Peribadi (gitignored & dockerignored)
        local_rel_path = ""
        if settings.dev_archive_local_enabled:
            try:
                vault_root = settings.dev_archive_local_dir.resolve()
                target_dir = (vault_root / yyyy / mm / dd / cat_slug / record_id).resolve()
                if target_dir.is_relative_to(vault_root):
                    target_dir.mkdir(parents=True, exist_ok=True)
                    (target_dir / "record.json").write_bytes(record_json_bytes)
                    if has_file and attachment_bytes is not None and file_size <= settings.dev_archive_max_upload_bytes:
                        att_path = (target_dir / "attachment.bin").resolve()
                        if att_path.is_relative_to(vault_root):
                            att_path.write_bytes(attachment_bytes)
                            local_rel_path = str(att_path.relative_to(vault_root)).replace("\\", "/")
            except OSError:
                pass

        self.db.insert_dev_archive(
            {
                "id": record_id,
                "category": category,
                "action_type": action_type,
                "endpoint": endpoint,
                "user_id": str(safe_user.get("id") or ""),
                "user_email": str(safe_user.get("email") or ""),
                "user_name": str(safe_user.get("full_name") or ""),
                "user_grade": str(safe_user.get("grade") or ""),
                "district_pkd": str(safe_user.get("district_pkd") or ""),
                "state_jkn": str(safe_user.get("state_jkn") or ""),
                "akta_utama": akta_utama,
                "case_id": case_id,
                "title": record_doc["title"],
                "preview_text": preview_clean,
                "raw_input_text": raw_input_text,
                "redacted_input_text": redacted_input,
                "raw_response_text": raw_response_text,
                "redacted_response_text": redacted_resp_txt,
                "request_json": json.dumps(safe_req, ensure_ascii=False),
                "response_json": json.dumps(safe_resp, ensure_ascii=False),
                "redacted_analysis_json": json.dumps(redacted_analysis, ensure_ascii=False),
                "user_snapshot_json": json.dumps(safe_user, ensure_ascii=False),
                "pdpa_entities_masked": pdpa_masked_total,
                "model_used": model_used,
                "is_cloud_api": bool(is_cloud_api),
                "est_cost_myr": est_cost_myr,
                "latency_ms": latency_ms,
                "status_summary": status_summary,
                "has_file": has_file,
                "file_name": clean_fname,
                "file_content_type": clean_mime,
                "file_size_bytes": file_size,
                "file_sha256": file_sha256,
                "payload_sha256": payload_sha256,
                "storage_backend": storage_backend,
                "bucket_name": bucket_name,
                "object_key": file_object_key if (bucket_name and has_file) else "",
                "metadata_object_key": meta_object_key if bucket_name else "",
                "local_path": local_rel_path,
                "attachment_b64": attachment_b64,
                "attachment_truncated": attachment_truncated,
                "sync_status": sync_status,
                "sync_error": sync_error,
                "created_at": now_str,
            }
        )
        return record_id

    @staticmethod
    def _parse_json_safe(raw: Optional[str]) -> Optional[Dict[str, Any]]:
        if not raw:
            return None
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {"data": parsed}
        except Exception:
            return None

    def format_detail_response(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Menukar baris DB kepada format DevVaultRecordDetail untuk Konsol Dev."""
        has_file = bool(row.get("has_file"))
        file_att = None
        if has_file:
            file_att = {
                "file_id": row["id"],
                "original_filename": row.get("file_name") or "dokumen.bin",
                "content_type": row.get("file_content_type") or "application/octet-stream",
                "size_bytes": int(row.get("file_size_bytes") or 0),
                "sha256": row.get("file_sha256") or "",
                "storage_backend": row.get("storage_backend") or "sqlite_local_vault",
                "object_key": row.get("object_key") or row.get("local_path") or "",
                "is_available": not bool(row.get("attachment_truncated")),
            }

        raw_user_snap = self._parse_json_safe(row.get("user_snapshot_json"))
        analysis_json = self._parse_json_safe(row.get("response_json"))
        redacted_analysis_json = self._parse_json_safe(row.get("redacted_analysis_json"))

        return {
            "id": row["id"],
            "category": row["category"],
            "action_type": row["action_type"],
            "title": row.get("title") or "",
            "preview_text": row.get("preview_text") or "",
            "akta_utama": row.get("akta_utama") or None,
            "user_id": row.get("user_id") or None,
            "user_email": row.get("user_email") or "",
            "user_name": row.get("user_name") or "",
            "district_pkd": row.get("district_pkd") or "",
            "model_used": row.get("model_used") or "",
            "is_cloud_api": bool(row.get("is_cloud_api")),
            "est_cost_myr": round(float(row.get("est_cost_myr") or 0.0), 5),
            "latency_ms": int(row.get("latency_ms") or 0),
            "has_file": has_file,
            "file_name": row.get("file_name") or None,
            "file_content_type": row.get("file_content_type") or None,
            "file_size_bytes": int(row.get("file_size_bytes") or 0) if has_file else None,
            "storage_backend": row.get("storage_backend") or "sqlite_local_vault",
            "pdpa_entities_masked": int(row.get("pdpa_entities_masked") or 0),
            "created_at": row.get("created_at") or "",
            "raw_input_text": row.get("raw_input_text") or "",
            "redacted_input_text": row.get("redacted_input_text") or "",
            "raw_response_text": row.get("raw_response_text") or "",
            "redacted_response_text": row.get("redacted_response_text") or "",
            "analysis_json": analysis_json,
            "redacted_analysis_json": redacted_analysis_json,
            "user_snapshot": raw_user_snap,
            "file_attachment": file_att,
            "storage_metadata": {
                "object_key": row.get("object_key") or row.get("metadata_object_key") or None,
                "bucket_name": row.get("bucket_name") or None,
                "payload_sha256": row.get("payload_sha256") or None,
                "source_endpoint": row.get("endpoint") or None,
                "sync_status": row.get("sync_status") or None,
            },
        }

    def _read_attachment_bytes(self, row: Dict[str, Any]) -> Optional[bytes]:
        """Membaca byte lampiran asal ikut turutan: Private S3 -> DB Base64 -> Local Vault."""
        bucket = str(row.get("bucket_name") or "").strip()
        obj_key = str(row.get("object_key") or "").strip()
        s3_client = self._get_s3_client()
        if s3_client is not None and bucket and obj_key:
            try:
                return s3_client.get_object(bucket=bucket, key=obj_key)
            except Exception:
                pass

        b64 = str(row.get("attachment_b64") or "").strip()
        if b64:
            try:
                return base64.b64decode(b64)
            except Exception:
                pass

        local_rel = str(row.get("local_path") or "").strip()
        if local_rel and settings.dev_archive_local_enabled:
            try:
                vault_root = settings.dev_archive_local_dir.resolve()
                candidate = (vault_root / local_rel).resolve()
                if (
                    candidate.is_relative_to(vault_root)
                    and candidate.exists()
                    and not candidate.is_symlink()
                    and candidate.is_file()
                ):
                    return candidate.read_bytes()
            except OSError:
                pass
        return None

    def resolve_file_download(
        self, record_id: str, kind: str = "attachment"
    ) -> Tuple[bytes, str, str]:
        """Memulangkan (bytes, filename, mime) bagi fail asal atau dossier JSON."""
        row = self.db.get_dev_archive_record(record_id, include_b64=True)
        if not row:
            raise FileNotFoundError("Rekod arkib tidak dijumpai.")

        if kind == "json":
            detail = self.format_detail_response(row)
            raw_bytes = json.dumps(detail, ensure_ascii=False, indent=2).encode("utf-8")
            return raw_bytes, f"{record_id}_dossier.json", "application/json; charset=utf-8"

        if not row.get("has_file"):
            raise FileNotFoundError("Rekod ini tidak mempunyai lampiran fail binari.")

        data = self._read_attachment_bytes(row)
        if data is None:
            raise FileNotFoundError(
                "Fail lampiran tidak ditemui di Bucket S3, pangkalan data, atau vault tempatan."
            )

        fname = sanitize_filename(row.get("file_name"), f"{record_id}.bin")
        mime = str(row.get("file_content_type") or "application/octet-stream")
        return data, fname, mime

    def build_export_bundle(
        self,
        *,
        mode: str = "redacted",
        fmt: str = "zip",
        category: Optional[str] = None,
        q: Optional[str] = None,
        user_email: Optional[str] = None,
        include_files: bool = True,
        limit: int = 500,
    ) -> Tuple[bytes, str, str]:
        """Menjana pakej eksport (.zip atau .jsonl) untuk dokumentasi & penambahbaikan sistem."""
        safe_mode = "full" if mode == "full" else "redacted"
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        rows = self.db.list_dev_archive_for_export(
            category=category, q=q, user_email=user_email, limit=limit
        )
        users_all = self.db.list_all_users_safe()

        if safe_mode == "redacted":
            users_export = [
                {**u, "ic_number": mask_ic_number(u.get("ic_number"))} for u in users_all
            ]
        else:
            users_export = users_all

        jsonl_lines: List[str] = []
        for row in rows:
            req_json = self._parse_json_safe(row.get("request_json")) or {}
            resp_json = self._parse_json_safe(row.get("response_json")) or {}
            red_json = self._parse_json_safe(row.get("redacted_analysis_json")) or {}
            user_snap = self._parse_json_safe(row.get("user_snapshot_json")) or {}
            if safe_mode == "redacted":
                if user_snap.get("ic_number"):
                    user_snap["ic_number"] = mask_ic_number(user_snap.get("ic_number"))
                item = {
                    "id": row["id"],
                    "created_at": row["created_at"],
                    "category": row["category"],
                    "action_type": row["action_type"],
                    "endpoint": row.get("endpoint") or "",
                    "user_email": row.get("user_email") or "",
                    "user_name": row.get("user_name") or "",
                    "district_pkd": row.get("district_pkd") or "",
                    "akta_utama": row.get("akta_utama") or "",
                    "title": row.get("title") or "",
                    "model_used": row.get("model_used") or "",
                    "latency_ms": int(row.get("latency_ms") or 0),
                    "pdpa_entities_masked": int(row.get("pdpa_entities_masked") or 0),
                    "input_text_redacted": row.get("redacted_input_text") or "",
                    "response_text_redacted": row.get("redacted_response_text") or "",
                    "analysis_redacted": red_json,
                    "user_snapshot": user_snap,
                    "file_name": row.get("file_name") or None,
                    "file_sha256": row.get("file_sha256") or None,
                }
            else:
                item = {
                    "id": row["id"],
                    "created_at": row["created_at"],
                    "category": row["category"],
                    "action_type": row["action_type"],
                    "endpoint": row.get("endpoint") or "",
                    "user_email": row.get("user_email") or "",
                    "user_name": row.get("user_name") or "",
                    "district_pkd": row.get("district_pkd") or "",
                    "akta_utama": row.get("akta_utama") or "",
                    "title": row.get("title") or "",
                    "model_used": row.get("model_used") or "",
                    "latency_ms": int(row.get("latency_ms") or 0),
                    "pdpa_entities_masked": int(row.get("pdpa_entities_masked") or 0),
                    "raw_input_text": row.get("raw_input_text") or "",
                    "redacted_input_text": row.get("redacted_input_text") or "",
                    "raw_response_text": row.get("raw_response_text") or "",
                    "redacted_response_text": row.get("redacted_response_text") or "",
                    "request_payload": req_json,
                    "analysis_payload": resp_json,
                    "analysis_redacted": red_json,
                    "user_snapshot": user_snap,
                    "file_name": row.get("file_name") or None,
                    "file_sha256": row.get("file_sha256") or None,
                }
            jsonl_lines.append(json.dumps(item, ensure_ascii=False))

        jsonl_bytes = ("\n".join(jsonl_lines) + ("\n" if jsonl_lines else "")).encode("utf-8")

        if fmt == "jsonl":
            fname = f"iuip-dev-vault-{safe_mode}-{stamp}.jsonl"
            return jsonl_bytes, fname, "application/x-ndjson; charset=utf-8"

        buf = io.BytesIO()
        max_zip_bytes = 40 * 1024 * 1024
        running_bytes = 0
        attached_files = 0
        skipped_files: List[str] = []

        with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            manifest = {
                "application": "i-UIP Nerus (KKM Malaysia)",
                "developer": "g.dev/syrzy (zero4eleven@gmail.com)",
                "export_mode": safe_mode,
                "generated_at_utc": _utc_now_iso(),
                "total_registered_users": len(users_export),
                "total_archive_records": len(rows),
                "filters": {
                    "category": category or "ALL",
                    "q": q or "",
                    "user_email": user_email or "",
                },
            }
            zf.writestr(
                "users_registered.json",
                json.dumps(users_export, ensure_ascii=False, indent=2).encode("utf-8"),
            )
            zf.writestr("records.jsonl", jsonl_bytes)

            if include_files:
                for row in rows:
                    rec_id = row["id"]
                    if safe_mode == "redacted":
                        red_txt = str(row.get("redacted_input_text") or "").strip()
                        if red_txt:
                            zf.writestr(f"redacted_texts/{rec_id}.txt", red_txt.encode("utf-8"))
                    elif row.get("has_file"):
                        file_data = self._read_attachment_bytes(row)
                        if not file_data:
                            skipped_files.append(rec_id)
                            continue
                        if running_bytes + len(file_data) > max_zip_bytes:
                            skipped_files.append(f"{rec_id} (had saiz ZIP 40MB dicapai)")
                            continue
                        clean_name = sanitize_filename(row.get("file_name"), "lampiran.bin")
                        zf.writestr(f"attachments/{rec_id}_{clean_name}", file_data)
                        running_bytes += len(file_data)
                        attached_files += 1

            manifest["attached_files_count"] = attached_files
            manifest["skipped_attachments"] = skipped_files
            zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"))

        fname = f"iuip-dev-vault-{safe_mode}-{stamp}.zip"
        return buf.getvalue(), fname, "application/zip"

    def retry_s3_sync(self, limit: int = 50) -> Dict[str, Any]:
        """Menyelaraskan rekod db_fallback ke Private S3 / Neon Object Storage Bucket."""
        s3_client = self._get_s3_client()
        if s3_client is None:
            return {
                "synced": 0,
                "failed": 0,
                "message": "Bucket S3/Neon Object Storage belum dikonfigurasi pada pelayan.",
            }

        rows = self.db.list_unsynced_dev_archive(limit=limit)
        prefix = settings.dev_archive_prefix or "dev-vault"
        synced = 0
        failed = 0
        errors: List[str] = []

        for row in rows:
            rec_id = row["id"]
            cat_slug = re.sub(r"[^a-z0-9_\-]+", "_", str(row.get("category") or "other").lower())
            created = str(row.get("created_at") or "")
            yyyy = created[:4] if len(created) >= 4 and created[:4].isdigit() else "2026"
            mm = created[5:7] if len(created) >= 7 and created[5:7].isdigit() else "01"
            dd = created[8:10] if len(created) >= 10 and created[8:10].isdigit() else "01"
            meta_key = row.get("metadata_object_key") or f"{prefix}/{yyyy}/{mm}/{dd}/{cat_slug}/{rec_id}/record.json"
            file_key = row.get("object_key") or (
                f"{prefix}/{yyyy}/{mm}/{dd}/{cat_slug}/{rec_id}/attachment.bin"
                if row.get("has_file")
                else ""
            )

            try:
                detail_bytes = json.dumps(
                    self.format_detail_response(row), ensure_ascii=False, indent=2
                ).encode("utf-8")
                s3_client.put_object(
                    bucket=settings.dev_archive_bucket,
                    key=meta_key,
                    data=detail_bytes,
                    content_type="application/json; charset=utf-8",
                )
                if row.get("has_file") and file_key:
                    att_bytes = self._read_attachment_bytes(row)
                    if att_bytes:
                        s3_client.put_object(
                            bucket=settings.dev_archive_bucket,
                            key=file_key,
                            data=att_bytes,
                            content_type=str(row.get("file_content_type") or "application/octet-stream"),
                        )
                self.db.mark_dev_archive_synced(
                    rec_id,
                    storage_backend="s3_neon",
                    bucket_name=settings.dev_archive_bucket,
                    object_key=file_key,
                    metadata_object_key=meta_key,
                    clear_b64=True,
                )
                synced += 1
            except Exception as exc:
                failed += 1
                errors.append(f"{rec_id}: {str(exc)[:120]}")

        return {
            "synced": synced,
            "failed": failed,
            "errors": errors[:10],
            "message": f"Sync selesai: {synced} rekod diselaraskan ke bucket '{settings.dev_archive_bucket}'.",
        }
