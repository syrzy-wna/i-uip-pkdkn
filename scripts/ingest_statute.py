#!/usr/bin/env python3
"""Skrip CLI Saluran Penghuraian PDF Warta Rasmi AGC (FASA 2 — Statute Ingestion Pipeline).

Penggunaan:
    python3 scripts/ingest_statute.py --file data/akta/AKTA_852.pdf --statute-id AKTA_852
    python3 scripts/ingest_statute.py --file data/akta/PPKM_2009.pdf --statute-id PPKM_2009 --verify
    python3 scripts/ingest_statute.py --audit
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.core.database import get_uip_db
from backend.rag.legal_engine import get_legal_library
from backend.rag.statutory_store import get_statutory_store


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Hurai & indeks fail PDF/TXT Warta Kerajaan Rasmi (AGC) ke dalam Pustaka Akta 2-Lapisan i-UIP Nerus."
    )
    parser.add_argument("--file", "-f", type=str, help="Laluan ke fail PDF atau TXT Warta Rasmi AGC.")
    parser.add_argument(
        "--statute-id",
        "-s",
        type=str,
        default=None,
        help="Kod statute_id (cth: AKTA_852, AKTA_281, PPKM_2009, AKTA_154, AKTA_342, AKTA_593, AKTA_56, AKTA_611).",
    )
    parser.add_argument("--title-bm", type=str, default=None, help="Tajuk rasmi Bahasa Melayu.")
    parser.add_argument("--act-no", type=str, default=None, help="Nombor Akta atau P.U. (A).")
    parser.add_argument("--effective-date", type=str, default=None, help="Tarikh kuat kuasa (YYYY-MM-DD).")
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Sahkan terus sebagai VERIFIED_AGC (lalai: DRAFT_PENDING_REVIEW).",
    )
    parser.add_argument(
        "--audit",
        action="store_true",
        help="Cetak Laporan Liputan 100% (Coverage Audit Dashboard) bagi semua akta.",
    )
    args = parser.parse_args()

    library = get_legal_library()
    db = get_uip_db()

    if args.audit and not args.file:
        report = library.get_coverage_audit_report()
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    if not args.file:
        parser.error("Sila berikan --file <laluan_pdf_warta> atau --audit.")

    file_path = Path(args.file).resolve()
    if not file_path.exists():
        print(f"RALAT: Fail tidak dijumpai: {file_path}", file=sys.stderr)
        return 1

    raw_bytes = file_path.read_bytes()
    result = library.ingest_statute_bytes(
        filename=file_path.name,
        raw_bytes=raw_bytes,
        statute_id=args.statute_id,
        official_title_bm=args.title_bm,
        act_number_or_pu=args.act_no,
        effective_date=args.effective_date,
        verified_by_admin=args.verify,
    )

    # Salin ke data/akta/ dan kemas kini stor RAG + tandakan cache Q&A lama sebagai STALE
    rag_store = get_statutory_store()
    rag_store.ingest_uploaded_file(file_path.name, raw_bytes)
    stale_marked = db.invalidate_advisor_qa_cache(
        akta_code=result["canonical_akta_code"],
        new_version=result["statute_library_version"],
    )
    result["stale_qa_cache_marked"] = stale_marked

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
