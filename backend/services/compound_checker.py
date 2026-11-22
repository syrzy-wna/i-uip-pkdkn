"""Modul Semakan Notis Kompaun Lapangan ("Zero-Defect Notice") untuk PPKP.

Menyemak 10 perkara wajib berserta validasi undang-undang sebenar mengikut Akta:
- Validasi format dan tarikh lahir 6 digit MyKad + kod negeri (atau No. Pasport)
- Validasi had maksimum kompaun (cth: RM500 Seksyen 25 Akta 154)
- Validasi tempoh bayaran (cth: 30 hari di bawah P.U. (A) 259/2024 Akta 852)
- Pengesanan kesilapan petikan seksyen (cth: S.16(1) vs S.16(2), S.44 vs S.48,
  Peraturan 30 vs Peraturan 31 untuk suntikan tifoid)
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

MYKAD_STRICT_RE = re.compile(r"^(\d{2})(\d{2})(\d{2})-(\d{2})-\d{4}$")
DATE_LIKE_RE = re.compile(
    r"\d{1,4}[/-]\d{1,2}[/-]\d{1,4}|\b(?:jan|feb|mac|apr|mei|jun|jul|ogos|sep|okt|nov|dis)\b",
    re.I,
)
VALID_STATE_CODES = {
    *{f"{i:02d}" for i in range(1, 17)},
    *{f"{i:02d}" for i in range(21, 60)},
    "71", "82",
}


class CompoundNoticeChecker:
    """Penyemak 10 perkara wajib Notis Kompaun Lapangan KKM berpandukan Akta sebenar."""

    @staticmethod
    def _clean(val: Any) -> str:
        return str(val or "").strip()

    @staticmethod
    def _validate_mykad(ic_str: str) -> tuple[bool, str]:
        m = MYKAD_STRICT_RE.match(ic_str)
        if not m:
            return False, "Format No. K/P mestilah 12 digit XXXXXX-XX-XXXX (contoh: 890415-10-5321)."
        month = int(m.group(2))
        day = int(m.group(3))
        state = m.group(4)
        if not (1 <= month <= 12 and 1 <= day <= 31):
            return False, f"6 digit tarikh lahir pada No. K/P ({m.group(1)}{m.group(2)}{m.group(3)}) tidak sah."
        if state not in VALID_STATE_CODES:
            return False, f"Kod negeri '{state}' pada No. K/P tidak sah."
        return True, f"No. K/P sah ({ic_str})."

    @staticmethod
    def _extract_rm_amount(amaun_str: str) -> float | None:
        cleaned = amaun_str.replace(",", "")
        m = re.search(r"(\d+(?:\.\d{1,2})?)", cleaned)
        return float(m.group(1)) if m else None

    def check_notice(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        nama_penerima = self._clean(payload.get("nama_penerima"))
        no_kp = self._clean(payload.get("no_kp"))
        nama_premis = self._clean(payload.get("nama_premis"))
        alamat_kejadian = self._clean(payload.get("alamat_kejadian"))
        no_ssm = self._clean(payload.get("no_ssm"))
        tarikh_masa = self._clean(payload.get("tarikh_masa"))
        akta_seksyen = self._clean(payload.get("peruntukan_undang"))
        kesalahan_ringkas = self._clean(payload.get("kesalahan_ringkas"))
        amaun_rm = self._clean(payload.get("amaun_kompaun_rm"))
        tempoh_bayaran = self._clean(payload.get("tempoh_bayaran"))
        pegawai_pengeluar = self._clean(payload.get("pegawai_pengeluar"))
        no_kad_kuasa = self._clean(payload.get("no_kad_kuasa"))
        status_serahan = self._clean(payload.get("status_serahan") or "tandatangan_terima")
        saksi_ppkp = self._clean(payload.get("saksi_ppkp"))

        checks: List[Dict[str, Any]] = []
        low_sec = akta_seksyen.lower()
        low_err = kesalahan_ringkas.lower()

        # 1. Nama penuh penerima / OKT ikut MyKad
        ok_nama = len(nama_penerima) >= 5 and "[" not in nama_penerima
        checks.append({
            "code": "K01",
            "label": "Nama Penuh Penerima / OKT (Ikut MyKad)",
            "status": "LULUS" if ok_nama else "GAGAL",
            "note": f"Nama direkodkan: {nama_penerima}" if ok_nama else "Masukkan nama penuh OKT seperti tertera pada MyKad (elak nama panggilan).",
        })

        # 2. No. KP 12 digit sah (tarikh lahir + kod negeri)
        ok_kp, kp_msg = self._validate_mykad(no_kp)
        checks.append({
            "code": "K02",
            "label": "Kesahihan No. Kad Pengenalan (12 Digit)",
            "status": "LULUS" if ok_kp else "GAGAL",
            "note": kp_msg,
        })

        # 3. Nama premis & alamat lengkap tempat kejadian
        ok_tempat = len(nama_premis) >= 3 and len(alamat_kejadian) >= 10
        checks.append({
            "code": "K03",
            "label": "Nama Premis & Alamat Lengkap Tempat Kejadian",
            "status": "LULUS" if ok_tempat else "GAGAL",
            "note": "Nama premis dan alamat lengkap telah diisi." if ok_tempat else "Isi nama kedai/premis serta nombor lot/jalan, poskod, dan daerah tempat kesalahan berlaku.",
        })

        # 4. No. SSM jika melibatkan syarikat / perniagaan
        perlu_ssm = any(w in nama_premis.lower() for w in ("sdn", "bhd", "enterprise", "trading", "restoran", "kedai", "bistro", "mart", "kafe"))
        ok_ssm = (len(no_ssm) >= 5 and "tidak" not in no_ssm.lower()) if perlu_ssm else True
        checks.append({
            "code": "K04",
            "label": "No. Daftar SSM (Jika Premis Perniagaan/Syarikat)",
            "status": "LULUS" if ok_ssm else "SEMAK",
            "note": f"No. SSM: {no_ssm or 'Kes individu (tidak wajib)'}" if ok_ssm else "Premis perniagaan dikesan — semak dan masukkan No. SSM daripada papan tanda lesen atau carian SSM.",
        })

        # 5. Tarikh & Masa kesalahan tepat
        ok_tarikh = bool(tarikh_masa) and (bool(DATE_LIKE_RE.search(tarikh_masa)) or len(tarikh_masa) >= 8)
        checks.append({
            "code": "K05",
            "label": "Tarikh & Masa Kesalahan Tepat",
            "status": "LULUS" if ok_tarikh else "GAGAL",
            "note": f"Tarikh/Masa: {tarikh_masa}" if ok_tarikh else "Nyatakan tarikh dan waktu tepat kesalahan ditemui (contoh: 14/10/2026, 10.45 pagi).",
        })

        # 6. Ketepatan Seksyen & Peraturan Mengikut Akta + Pengesahan Pustaka Akta Verbatim
        from backend.rag.legal_engine import get_legal_library, validate_legal_output

        legal_lib = get_legal_library()
        lib_snapshot = legal_lib.to_snapshot_dict()

        sec_errors: List[str] = []
        has_sec_kw = ("seksyen" in low_sec or "peraturan" in low_sec) and (
            "akta" in low_sec or "ppkm" in low_sec or "ppm" in low_sec or "p.u." in low_sec or "ppkht" in low_sec
        )
        if not has_sec_kw:
            sec_errors.append("Nyatakan Akta serta nombor Seksyen/Peraturan yang lengkap.")
        if "ppkht" in low_sec or "324/2004" in low_sec:
            sec_errors.append("PPKHT 2004 telah DIMANSUHKAN sepenuhnya oleh Akta 852 mulai 1 Oktober 2024.")
        if "ordinan darurat" in low_sec or "82/2021" in low_sec:
            sec_errors.append("Ordinan Darurat 2021 telah TAMAT TEMPOH. Rujuk Seksyen 25 Akta 342 (Pindaan Akta A1742) & P.U. (A) 139/2025.")
        if "852" in low_sec and "16(1)" in low_sec:
            sec_errors.append("Seksyen 16(1) Akta 852 ialah kuasa Menteri mewartakan kawasan. Kesalahan individu merokok ialah Seksyen 16(2) Akta 852.")
        if "852" in low_sec and "seksyen 44" in low_sec:
            sec_errors.append("Seksyen 44 Akta 852 ialah perlindungan pemberi maklumat. Kuasa kompaun Akta 852 ialah Seksyen 48 [P.U. (A) 259/2024].")
        if ("tifoid" in low_err or "typhoid" in low_err or "vaksin" in low_err) and "peraturan 30" in low_sec and "31" not in low_sec:
            sec_errors.append("Kesalahan tiada suntikan anti-tifoid ialah di bawah Peraturan 31(1) PPKM 2009 (Peraturan 30 ialah Latihan Pengendali Makanan).")
        if "154" in low_sec and "8(2)" in low_sec:
            sec_errors.append("Kesalahan ingkar perintah Seksyen 8 Akta 154 ialah di bawah Seksyen 8(8) Akta 154.")

        # Semak seksyen rekaan atau unsur tidak terpenuhi melalui validate_legal_output
        val_res = validate_legal_output(
            {
                "peruntukan_undang": akta_seksyen,
                "keputusan_tindakan": f"Kompaun {akta_seksyen} {amaun_rm}",
                "alasan_keputusan": kesalahan_ringkas,
            },
            lib_snapshot,
            question_context=f"{akta_seksyen} {kesalahan_ringkas}",
        )
        if val_res.get("invalid_citations"):
            sec_errors.extend(val_res["invalid_citations"])
        if val_res.get("unfulfilled_element_errors"):
            sec_errors.extend(val_res["unfulfilled_element_errors"])

        ok_seksyen = len(sec_errors) == 0
        checks.append({
            "code": "K06",
            "label": "Ketepatan Seksyen / Peraturan Statutori",
            "status": "LULUS" if ok_seksyen else "GAGAL",
            "note": f"Peruntukan sah: {akta_seksyen}" if ok_seksyen else " ".join(sec_errors),
        })

        # 7. Ayat butiran kesalahan jelas
        ok_butiran = len(kesalahan_ringkas) >= 25
        checks.append({
            "code": "K07",
            "label": "Ayat Butiran Kesalahan Jelas (Fakta Lapangan)",
            "status": "LULUS" if ok_butiran else "GAGAL",
            "note": "Butiran kesalahan menerangkan fakta apa yang dilihat semasa pemeriksaan." if ok_butiran else "Tulis butiran kesalahan dengan jelas (apa yang dilihat/dijumpai oleh PPKP di premis).",
        })

        # 8. Validasi Had Amaun Kompaun & Tempoh Bayaran Mengikut Akta Sebenar
        rm_val = self._extract_rm_amount(amaun_rm)
        k08_status = "LULUS"
        k08_note = f"Amaun: {amaun_rm} ({tempoh_bayaran})"
        if rm_val is None or rm_val <= 0:
            k08_status = "GAGAL"
            k08_note = "Masukkan amaun kompaun dalam RM yang sah."
        elif "154" in low_sec and rm_val > 500.0:
            k08_status = "GAGAL"
            k08_note = f"TIDAK SAH (Ultra Vires): Had kompaun maksimum Seksyen 25 Akta 154 ialah RM 500.00 (anda masukkan RM {rm_val:.2f})."
        elif "852" in low_sec:
            if "16(2)" in low_sec and rm_val > 2500.0:
                k08_status = "GAGAL"
                k08_note = "Melebihi had maksimum 50% daripada denda RM5,000 (Seksyen 16(3) Akta 852)."
            elif "17(1)" in low_sec and rm_val > 250.0:
                k08_status = "GAGAL"
                k08_note = "Melebihi had maksimum 50% daripada denda RM500 bagi OBD (Seksyen 17(2) Akta 852)."
            elif "30" not in tempoh_bayaran:
                k08_status = "SEMAK"
                k08_note = "Di bawah Peraturan Pengkompaunan Akta 852 [P.U. (A) 259/2024], tempoh bayaran rasmi ialah 30 hari dari tarikh tawaran kompaun."
        elif not ("14" in tempoh_bayaran or "30" in tempoh_bayaran or "hari" in tempoh_bayaran.lower()):
            k08_status = "SEMAK"
            k08_note = "Nyatakan tempoh bayaran rasmi (14 hari bagi Akta 154/281, 30 hari bagi Akta 852)."

        checks.append({
            "code": "K08",
            "label": "Had Amaun Kompaun & Tempoh Bayar Statutori",
            "status": k08_status,
            "note": k08_note,
        })

        # 9. Nama & No. Kad Kuasa PPKP pengeluar notis
        ok_ppkp = len(pegawai_pengeluar) >= 5 and len(no_kad_kuasa) >= 4
        checks.append({
            "code": "K09",
            "label": "Nama & No. Kad Kuasa PPKP Pengeluar Notis",
            "status": "LULUS" if ok_ppkp else "GAGAL",
            "note": f"Dikeluarkan oleh {pegawai_pengeluar} ({no_kad_kuasa})" if ok_ppkp else "Wajib isi nama PPKP dan No. Kad Kuasa rasmi KKM pada borang notis.",
        })

        # 10. Status serahan (tandatangan terima / enggan tandatangan + saksi PPKP)
        if status_serahan == "enggan_tandatangan":
            ok_serahan = len(saksi_ppkp) >= 5
            serahan_note = (
                f"Penerima enggan tandatangan — disaksikan oleh {saksi_ppkp} (sambung serahan Pos Berdaftar AR)."
                if ok_serahan
                else "Jika OKT enggan tandatangan terima notis, wajib catat nama PPKP saksi pengiring dan hantar melalui Pos Berdaftar AR."
            )
        else:
            ok_serahan = True
            serahan_note = "Serahan tangan berserta akuan tandatangan penerima."
        checks.append({
            "code": "K10",
            "label": "Tatacara Serahan & Tandatangan Terima / Saksi",
            "status": "LULUS" if ok_serahan else "GAGAL",
            "note": serahan_note,
        })

        lulus = sum(1 for c in checks if c["status"] == "LULUS")
        semak = sum(1 for c in checks if c["status"] == "SEMAK")
        gagal = sum(1 for c in checks if c["status"] == "GAGAL")

        if gagal == 0 and semak == 0:
            readiness = "SEDIA CETAK & SERAH (SIFAR CACAT)"
        elif gagal == 0:
            readiness = "PERLU SEMAKAN RINGKAS"
        else:
            readiness = "TIDAK SAH / PERLU BETULKAN DAHULU"

        # Pisahkan ayat Butiran Kesalahan Notis Kompaun daripada Ayat Pertuduhan Borang 114
        peruntukan_kompaun = (
            "Seksyen 48 Akta 852 [P.U. (A) 259/2024]"
            if "852" in low_sec
            else ("Seksyen 25 Akta 154" if "154" in low_sec else "Notis Seksyen 32B & Seksyen 33 Akta Makanan 1983")
        )
        suggested_offense_text = (
            f"Pada {tarikh_masa or '[Tarikh & Masa]'}, bertempat di {nama_premis or '[Nama Premis]'}, "
            f"{alamat_kejadian or '[Alamat Premis]'}, kamu {nama_penerima or '[Nama OKT]'} (No. K/P: {no_kp or '[No. KP]'}) "
            f"telah didapati {kesalahan_ringkas or '[nyatakan perbuatan kesalahan]'}, yang merupakan suatu kesalahan di bawah "
            f"{akta_seksyen or '[Seksyen Kesalahan]'} dan boleh dikompaun di bawah {peruntukan_kompaun}."
        )

        return {
            "readiness_status": readiness,
            "score_percent": round((lulus / len(checks)) * 100, 1),
            "counts": {"LULUS": lulus, "SEMAK": semak, "GAGAL": gagal},
            "checks": checks,
            "suggested_offense_text": suggested_offense_text,
            "legal_validation": val_res,
        }
