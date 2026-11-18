"""Skrip Utiliti Penyediaan Dataset Fine-Tuning UIP-Command (`training/prepare_dataset.py`).

Mengimbas folder arkib Kertas Siasatan sebenar (.pdf, .docx, .txt), menjalankan
penyamaran data sulit (OSA/PDPA Auto-Redaction) supaya tiada maklumat peribadi
sebenar masuk ke dalam dataset latihan, dan mengeksport fail JSONL sedia guna
untuk Unsloth (`finetune_unsloth.py`).

Contoh penggunaan:
    python training/prepare_dataset.py --input-dir ./arkib_ip --output ./training/uip_dataset.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.core.redactor import PrivacyRedactor
from backend.services.ip_auditor import extract_text_from_upload
from backend.services.sample_cases import SAMPLE_CASES


def build_training_records(
    raw_text: str,
    source_name: str,
    redactor: PrivacyRedactor,
    use_ollama: bool = False,
) -> List[Dict[str, Any]]:
    """Menukar satu teks Kertas Siasatan menjadi pasangan arahan-jawapan JSONL."""
    redacted = redactor.redact(raw_text, use_ollama=use_ollama).redacted_text
    records: List[Dict[str, Any]] = [
        {
            "source": source_name,
            "task": "borang_114_drafting",
            "conversations": [
                {
                    "from": "system",
                    "value": (
                        "Anda ialah Pegawai Undang-Undang Unit Perundangan dan Pendakwaan (UIP), "
                        "Kementerian Kesihatan Malaysia. Gunakan laras bahasa rasmi perundangan "
                        "Malaysia dan kekalkan semua token penyamaran privasi seperti [SUSPEK_1]."
                    ),
                },
                {
                    "from": "human",
                    "value": (
                        "Berdasarkan ringkasan siasatan berikut, gubal intipati Fakta Kes dan "
                        "semakan pematuhan tatacara (Seksyen 112 KTJ, Sijil Seksyen 90A, Rantaian Eksibit):\n\n"
                        f"{redacted[:3500]}"
                    ),
                },
                {
                    "from": "gpt",
                    "value": (
                        "RINGKASAN SEMAKAN & LARAS BAHASA RASMI UIP:\n"
                        "1. Fakta Kes hendaklah menyatakan tarikh, masa, tempat kejadian ([PREMIS_1]), "
                        "identiti OKT ([SUSPEK_1], No. K/P: [NO_KP_1]) serta intipati kesalahan mengikut seksyen akta.\n"
                        "2. Pastikan percakapan di bawah Seksyen 112 Kanun Tatacara Jenayah dibaca semula dan "
                        "ditandatangani berserta amaran Seksyen 112(2)/(3) KTJ.\n"
                        "3. Lampirkan Sijil Seksyen 90A Akta Keterangan 1950 bagi semua cetakan foto digital dan e-Info SSM."
                    ),
                },
            ],
        },
        {
            "source": source_name,
            "task": "osa_pdpa_redaction",
            "conversations": [
                {
                    "from": "system",
                    "value": "Anda ialah enjin penyamaran data sulit OSA/PDPA UIP-Command.",
                },
                {
                    "from": "human",
                    "value": f"Sahkan bahawa teks berikut bebas daripada kebocoran identiti asal dan gunakan token piawai:\n\n{redacted[:2500]}",
                },
                {
                    "from": "gpt",
                    "value": "Semua entiti sensitif telah digantikan dengan token [SUSPEK_n], [SAKSI_n], [PREMIS_n], [NO_KP_n], [NO_SSM_n], dan [NO_TEL_n] mengikut piawaian privasi UIP.",
                },
            ],
        },
    ]
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description="Sediakan dataset JSONL daripada arkib IP UIP.")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=None,
        help="Direktori mengandungi fail arkib IP (.pdf, .docx, .txt). Jika kosong, guna kes sampel terbina.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT_DIR / "training" / "uip_dataset.jsonl",
        help="Laluan fail JSONL output.",
    )
    parser.add_argument(
        "--use-ollama",
        action="store_true",
        help="Aktifkan Ollama tempatan untuk bantuan penyamaran NER tambahan.",
    )
    args = parser.parse_args()

    redactor = PrivacyRedactor()
    all_records: List[Dict[str, Any]] = []

    if args.input_dir and args.input_dir.exists():
        files = [
            p
            for p in sorted(args.input_dir.rglob("*"))
            if p.is_file() and p.suffix.lower() in (".pdf", ".docx", ".txt")
        ]
        for file_path in files:
            text = extract_text_from_upload(file_path.read_bytes(), file_path.name)
            if len(text.strip()) >= 80:
                all_records.extend(
                    build_training_records(text, file_path.name, redactor, use_ollama=args.use_ollama)
                )
    else:
        print("[INFO] Tiada --input-dir dibekalkan; menjana templat JSONL daripada kes sampel KKM...")
        for sample in SAMPLE_CASES:
            all_records.extend(
                build_training_records(
                    sample["text"], sample["id"], redactor, use_ollama=args.use_ollama
                )
            )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as fh:
        for rec in all_records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"[SELESAI] {len(all_records)} rekod latihan disamarkan ditulis ke: {args.output}")


if __name__ == "__main__":
    main()
