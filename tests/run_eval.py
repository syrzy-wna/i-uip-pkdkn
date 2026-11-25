"""
Skrip Ujian Regresi Automatik (Golden Test Set) untuk i-UIP Nerus.
Jalankan sebelum deploy ke Cloud Run untuk pastikan 0% ralat akta & SOP.

Penggunaan:
  export GEMINI_API_KEY="kunci_anda"
  python tests/run_eval.py --mode router    # Uji Stage 1 Router sahaja (pantas & murah)
  python tests/run_eval.py --mode full      # Uji penuh Router + Jawapan Pakar UIP (Dual Knowledge Store)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.sop_brain.uip_brain import (
    IUIPNerusBrain,
    build_statutory_context_for_question,
)


def run_tests(mode: str = "router", require_live_api: bool = False) -> int:
    tests_path = ROOT / "tests" / "golden_test_set.json"
    tests = json.loads(tests_path.read_text(encoding="utf-8"))
    brain = IUIPNerusBrain(package_root=ROOT)

    live_api = brain.has_api_key
    print(
        f"=== Ujian Regresi i-UIP Nerus SOP Brain (mode={mode}) ===\n"
        f"SOP Aktif Diindeks : {len(brain.active_index)} (0 SOP PPKHT mansuh)\n"
        f"Status GEMINI_API_KEY: {'AKTIF (Live Gemini API, temp=0.0)' if live_api else 'TIADA (Mod Penghala Deterministik Tempatan)'}\n"
    )

    if mode == "full" and not live_api:
        print("AMARAN: --mode full memerlukan GEMINI_API_KEY aktif. Sila tetapkan export GEMINI_API_KEY sebelum menjalankan mod penuh.")
        return 2
    if require_live_api and not live_api:
        print("RALAT: --require-live-api diaktifkan tetapi GEMINI_API_KEY tidak ditemui.")
        return 2

    passed = 0
    failed = 0

    for tc in tests:
        tid = tc["id"]
        print(f"[{tid}] Menguji ({tc['kategori']})...")
        errors = []

        if mode == "router":
            route = brain.route_question(tc["soalan"], allow_local_fallback=not require_live_api)
            if route.melibatkan_akta_852 != tc["must_flag_akta_852"]:
                errors.append(
                    f"Flag Akta 852 salah: dapat {route.melibatkan_akta_852}, jangka {tc['must_flag_akta_852']}"
                )
            if tc["expected_any_sop_ids"]:
                if not any(s in route.selected_sop_ids for s in tc["expected_any_sop_ids"]):
                    errors.append(
                        f"SOP tidak sepadan: dapat {route.selected_sop_ids}, jangka salah satu {tc['expected_any_sop_ids']}"
                    )
            for s in route.selected_sop_ids:
                if "PPKHT" in s.upper():
                    errors.append(f"KRITIKAL: Router memilih SOP mansuh {s}")
        else:
            konteks_statut = build_statutory_context_for_question(tc["soalan"])
            res = brain.tanya_pakar_uip(
                tc["soalan"],
                konteks_statut_tambahan=konteks_statut,
            )
            route = res["routing"]
            ans = res["jawapan"]

            if route["melibatkan_akta_852"] != tc["must_flag_akta_852"]:
                errors.append("Flag Akta 852 tidak tepat.")
            if tc["expected_any_sop_ids"]:
                if not any(s in route["selected_sop_ids"] for s in tc["expected_any_sop_ids"]):
                    errors.append(f"SOP dipilih: {route['selected_sop_ids']}")
            for bad in tc["forbidden_terms"]:
                if bad.lower() in ans.lower():
                    errors.append(f"KRITIKAL: Jawapan mengandungi terma terlarang '{bad}'")
            if tc["must_mention_any"]:
                if not any(k.lower() in ans.lower() for k in tc["must_mention_any"]):
                    errors.append(f"Jawapan terlepas kata kunci wajib: {tc['must_mention_any']}")

        if errors:
            failed += 1
            print(f"  -> GAGAL: {' | '.join(errors)}")
        else:
            passed += 1
            print("  -> LULUS")

    print(f"\nKeputusan Akhir: {passed}/{len(tests)} LULUS, {failed} GAGAL.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["router", "full"], default="router")
    parser.add_argument("--require-live-api", action="store_true")
    args = parser.parse_args()
    raise SystemExit(run_tests(args.mode, require_live_api=args.require_live_api))
