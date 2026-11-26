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
from datetime import date
from typing import Any, Dict, List, Optional

MYKAD_STRICT_RE = re.compile(r"^(\d{2})(\d{2})(\d{2})-(\d{2})-(\d{4})$")
PASSPORT_RE = re.compile(r"^[A-Z]{1,2}\d{6,9}$", re.I)
SSM_NEW_RE = re.compile(r"^\d{12}$")
SSM_OLD_RE = re.compile(r"^(?:\d{5,9}-[A-Z]|[A-Z]{2}\d{6,8}-[A-Z]|LLP\d{6,8}-[A-Z]{2,4})$", re.I)
DATE_LIKE_RE = re.compile(
    r"\d{1,4}[/-]\d{1,2}[/-]\d{1,4}|\b(?:jan|feb|mac|apr|mei|jun|jul|ogos|sep|okt|nov|dis)\b",
    re.I,
)
VALID_STATE_CODES = {
    *{f"{i:02d}" for i in range(1, 17)},
    *{f"{i:02d}" for i in range(21, 60)},
    *{f"{i:02d}" for i in range(60, 69)},
    "71", "72", "74", "75", "76", "77", "78", "79",
    *{f"{i:02d}" for i in range(82, 94)},
    "98", "99",
}


class CompoundNoticeChecker:
    """Penyemak 10 perkara wajib Notis Kompaun Lapangan KKM berpandukan Akta sebenar."""

    @staticmethod
    def _clean(val: Any) -> str:
        return str(val or "").strip()

    @staticmethod
    def _parse_incident_date(tarikh_masa: str) -> Optional[date]:
        """Ekstrak tarikh kejadian daripada rentetan tarikh/masa untuk pengiraan umur OBD tepat pada tarikh kejadian."""
        raw = (tarikh_masa or "").strip()
        if not raw:
            return None
        # Format YYYY-MM-DD atau YYYY/MM/DD
        m_iso = re.search(r"\b((?:19|20)\d{2})[-/](\d{1,2})[-/](\d{1,2})\b", raw)
        if m_iso:
            try:
                return date(int(m_iso.group(1)), int(m_iso.group(2)), int(m_iso.group(3)))
            except ValueError:
                pass
        # Format DD/MM/YYYY atau DD-MM-YYYY
        m_dmy = re.search(r"\b(\d{1,2})[-/](\d{1,2})[-/]((?:19|20)\d{2})\b", raw)
        if m_dmy:
            try:
                return date(int(m_dmy.group(3)), int(m_dmy.group(2)), int(m_dmy.group(1)))
            except ValueError:
                pass
        # Format "14 Oktober 2026" / "14 Okt 2026"
        month_map = {
            "jan": 1, "feb": 2, "mac": 3, "mar": 3, "apr": 4, "mei": 5, "may": 5,
            "jun": 6, "jul": 7, "ogo": 8, "aug": 8, "sep": 9, "okt": 10, "oct": 10,
            "nov": 11, "dis": 12, "dec": 12,
        }
        m_txt = re.search(r"\b(\d{1,2})\s+([A-Za-z]{3,10})\s+((?:19|20)\d{2})\b", raw)
        if m_txt:
            mon = month_map.get(m_txt.group(2).lower()[:3])
            if mon:
                try:
                    return date(int(m_txt.group(3)), mon, int(m_txt.group(1)))
                except ValueError:
                    pass
        return None

    @staticmethod
    def _parse_mykad_dob(yy: int, mm: int, dd: int, ref_date: Optional[date] = None) -> Optional[date]:
        today = ref_date or date.today()
        cur_yy = today.year % 100
        full_year = (2000 + yy) if yy <= cur_yy else (1900 + yy)
        try:
            return date(full_year, mm, dd)
        except ValueError:
            return None

    @classmethod
    def _validate_recipient_id(cls, id_str: str, ref_date: Optional[date] = None) -> tuple[bool, str, Optional[int]]:
        """Sahkan No. MyKad (12 digit + kalendar + kod negeri JPN), No. Pasport, atau No. SSM syarikat."""
        cleaned = id_str.strip()
        if not cleaned:
            return False, "Masukkan No. K/P 12 digit (XXXXXX-XX-XXXX), No. Pasport (warga asing), atau No. SSM (syarikat).", None

        eval_date = ref_date or date.today()
        m = MYKAD_STRICT_RE.match(cleaned)
        if m:
            yy, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
            state = m.group(4)
            dob = cls._parse_mykad_dob(yy, month, day, ref_date=eval_date)
            if not dob:
                return False, f"6 digit tarikh lahir pada No. K/P ({m.group(1)}{m.group(2)}{m.group(3)}) tidak sah mengikut kalendar.", None
            if state not in VALID_STATE_CODES:
                return False, f"Kod negeri/negara '{state}' pada No. K/P tidak sah.", None
            age = eval_date.year - dob.year - ((eval_date.month, eval_date.day) < (dob.month, dob.day))
            date_suffix = " pada tarikh kejadian" if ref_date else ""
            age_note = f"Umur anggaran{date_suffix}: {age} tahun (OBD bawah 18 tahun)" if age < 18 else f"Umur anggaran{date_suffix}: {age} tahun"
            return True, f"No. K/P sah ({cleaned}). {age_note}.", age

        compact = cleaned.replace(" ", "")
        if PASSPORT_RE.match(compact):
            return True, f"No. Pasport sah bagi warga asing ({compact.upper()}). Pastikan salinan pasport dilampirkan.", None

        # Bezakan 12-digit SSM baharu (format rasmi SSM: YYYY + 01..06 + 6 digit, cth. 202101034892)
        # daripada MyKad 12-digit tanpa sengkang (atau MyKad rosak seperti 841319015523)
        if SSM_NEW_RE.match(compact):
            year_prefix = int(compact[0:4])
            entity_code = int(compact[4:6])
            if 1950 <= year_prefix <= (date.today().year + 1) and entity_code in (1, 2, 3, 4, 5, 6):
                return True, f"No. Pendaftaran Syarikat / SSM sah bagi penerima perbadanan ({compact.upper()}).", None
            # Semak sama ada ia sebenarnya MyKad 12-digit tanpa sengkang
            yy, month, day = int(compact[0:2]), int(compact[2:4]), int(compact[4:6])
            state = compact[6:8]
            if cls._parse_mykad_dob(yy, month, day, ref_date=eval_date) and state in VALID_STATE_CODES:
                formatted_ic = f"{compact[0:6]}-{compact[6:8]}-{compact[8:12]}"
                return (
                    False,
                    f"No. K/P hendaklah ditaip menggunakan format rasmi bertanda sengkang: {formatted_ic} (elak kekeliruan dengan No. SSM 12 digit).",
                    None,
                )
            return (
                False,
                f"Nombor 12 digit '{compact}' tidak sah sebagai No. K/P (tarikh lahir/kod negeri tidak sah) dan bukan format rasmi No. SSM baharu (YYYY01–06XXXXXX).",
                None,
            )

        if SSM_OLD_RE.match(compact):
            return True, f"No. Pendaftaran Syarikat / SSM sah bagi penerima perbadanan ({compact.upper()}).", None

        return (
            False,
            "Format pengenalan tidak sah. Gunakan No. K/P 12 digit XXXXXX-XX-XXXX (cth: 890415-10-5321), No. Pasport (cth: A12345678), atau No. SSM syarikat.",
            None,
        )

    @staticmethod
    def _extract_rm_amount(amaun_str: str) -> tuple[Optional[float], bool]:
        """Ekstrak nilai RM tunggal; kesan jika pengguna menulis julat seperti 'RM 250 - RM 500'."""
        cleaned = amaun_str.replace(",", "")
        nums = re.findall(r"\d+(?:\.\d{1,2})?", cleaned)
        if not nums:
            return None, False
        if len(nums) > 1:
            return float(nums[0]), True
        return float(nums[0]), False

    @staticmethod
    def _is_valid_ssm(no_ssm: str) -> bool:
        raw = no_ssm.strip()
        if not raw or len(raw) < 6:
            return False
        low = raw.lower()
        if any(bad in low for bad in ("tidak", "tiada", "belum", "n/a", "none", "null", "12345")):
            return False
        # Ekstrak token pertama (cth: "202101034892 (1435192-K)" atau "SA0549123-M")
        tokens = re.findall(r"[A-Za-z0-9-]+", raw)
        for tok in tokens:
            if SSM_OLD_RE.match(tok):
                return True
            if SSM_NEW_RE.match(tok):
                yr = int(tok[0:4])
                ent = int(tok[4:6])
                if 1950 <= yr <= (date.today().year + 1) and ent in (1, 2, 3, 4, 5, 6):
                    return True
        return False

    def check_notice(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        no_notis = self._clean(payload.get("no_notis"))
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
        low_premis = nama_premis.lower()
        incident_dt = self._parse_incident_date(tarikh_masa)

        is_akta_852_sec = bool(
            re.search(r"(?<!\d)852(?!\d)", low_sec)
            or any(pu in low_sec for pu in ("257/2024", "258/2024", "259/2024", "260/2024", "261/2024", "262/2024", "263/2024", "264/2024"))
            or "produk merokok" in low_sec
        )
        is_non_kkm_statute = bool(
            re.search(r"\b(?:akta|act)\s*(?:574|344|593|56|388|92|611)\b", low_sec)
            or any(
                k in low_sec
                for k in (
                    "kanun keseksaan", "penal code", "akta polis", "police act",
                    "kanun tatacara jenayah", "criminal procedure", "akta keterangan",
                    "akta tafsiran", "mahkamah rendah", "kanak-kanak 2001",
                )
            )
        )

        # 1. Nama penuh penerima / OKS ikut MyKad atau Pasport
        ok_nama = len(nama_penerima) >= 5 and "[" not in nama_penerima
        checks.append({
            "code": "K01",
            "label": "Nama Penuh Penerima / OKS (Ikut MyKad / Pasport)",
            "status": "LULUS" if ok_nama else "GAGAL",
            "note": f"Nama direkodkan: {nama_penerima}" if ok_nama else "Masukkan nama penuh OKS seperti tertera pada MyKad, Pasport, atau nama syarikat SSM (elak nama panggilan).",
        })

        # 2. No. KP 12 digit sah (kalendar + kod negeri JPN), Pasport, atau No. SSM
        ok_kp, kp_msg, recipient_age = self._validate_recipient_id(no_kp, ref_date=incident_dt)
        checks.append({
            "code": "K02",
            "label": "Kesahihan No. Kad Pengenalan / Pasport / SSM",
            "status": "LULUS" if ok_kp else "GAGAL",
            "note": kp_msg,
        })

        # 3. Nama premis & alamat lengkap tempat kejadian
        # Bagi kesalahan individu di tempat terbuka (cth: S.16(2)/S.17(1) Akta 852), alamat lengkap (>=10 aksara) sudah memadai.
        low_penerima = nama_penerima.lower()
        is_corporate_recipient = (
            self._is_valid_ssm(no_kp)
            or bool(no_ssm)
            or any(w in low_penerima for w in ("sdn", "bhd", "enterprise", "trading", "holdings", "resources"))
        )
        is_premise_required = (
            is_corporate_recipient
            or any(
                k in low_sec
                for k in ("18(1)", "ppkm", "ppm", "281", "154", "makanan")
            )
            or any(
                w in low_premis
                for w in ("sdn", "bhd", "enterprise", "trading", "restoran", "kedai", "bistro", "mart", "kafe", "kilang", "tapak bina")
            )
        )
        ok_tempat = (len(nama_premis) >= 3 and len(alamat_kejadian) >= 10) if is_premise_required else (len(alamat_kejadian) >= 10)
        checks.append({
            "code": "K03",
            "label": "Lokasi & Alamat Lengkap Tempat Kejadian",
            "status": "LULUS" if ok_tempat else "GAGAL",
            "note": (
                "Nama premis dan alamat lengkap telah diisi."
                if len(nama_premis) >= 3 and ok_tempat
                else (
                    "Alamat lengkap tempat kejadian telah diisi (kes individu di kawasan terbuka)."
                    if ok_tempat
                    else "Isi nama premis (jika berkaitan) serta alamat lengkap termasuk jalan, poskod dan daerah tempat kesalahan berlaku."
                )
            ),
        })

        # 4. No. SSM jika melibatkan syarikat / perniagaan
        perlu_ssm = any(w in low_premis for w in ("sdn", "bhd", "enterprise", "trading", "restoran", "kedai", "bistro", "mart", "kafe", "tapak bina", "construction"))
        ok_ssm = self._is_valid_ssm(no_ssm) if perlu_ssm else True
        checks.append({
            "code": "K04",
            "label": "No. Daftar SSM (Jika Premis Perniagaan / Syarikat)",
            "status": "LULUS" if ok_ssm else "SEMAK",
            "note": f"No. SSM: {no_ssm or 'Kes individu (tidak wajib)'}" if ok_ssm else "Premis perniagaan dikesan — masukkan No. SSM yang sah (cth: 202101034892 atau SA0549123-M) daripada papan tanda lesen atau carian SSM.",
        })

        # 5. Tarikh & Masa kesalahan tepat
        ok_tarikh = bool(tarikh_masa) and (bool(DATE_LIKE_RE.search(tarikh_masa)) or len(tarikh_masa) >= 8)
        checks.append({
            "code": "K05",
            "label": "Tarikh & Masa Kesalahan Tepat",
            "status": "LULUS" if ok_tarikh else "GAGAL",
            "note": f"Tarikh/Masa: {tarikh_masa}" if ok_tarikh else "Nyatakan tarikh dan waktu tepat kesalahan ditemui (contoh: 14/10/2026, 10.45 pagi).",
        })

        # 6. Ketepatan Seksyen & Peraturan Mengikut Akta + Semakan Boleh Kompaun + Pustaka Akta
        from backend.rag.legal_engine import get_legal_library, validate_legal_output

        legal_lib = get_legal_library()
        lib_snapshot = legal_lib.to_snapshot_dict()

        sec_errors: List[str] = []
        sec_warnings: List[str] = []
        has_sec_kw = ("seksyen" in low_sec or "peraturan" in low_sec) and (
            "akta" in low_sec or "ppkm" in low_sec or "ppm" in low_sec or "p.u." in low_sec or "ppkht" in low_sec or "kanun" in low_sec
        )
        if not has_sec_kw:
            sec_errors.append("Nyatakan Akta serta nombor Seksyen/Peraturan yang lengkap.")
        if is_non_kkm_statute:
            sec_errors.append(
                "TIDAK BOLEH DIKOMPAUN OLEH PPKP: Akta 574 (Kanun Keseksaan), Akta 344 (Akta Polis), Akta 593 (KTJ), Akta 56, Akta 388, Akta 92 dan Akta 611 bukan peruntukan kompaun KKM. Buat Laporan Polis Seksyen 107 KTJ atau rujuk TPR/PDRM."
            )
        if "ppkht" in low_sec or "324/2004" in low_sec:
            sec_errors.append("PPKHT 2004 telah DIMANSUHKAN sepenuhnya oleh Akta 852 mulai 1 Oktober 2024.")
        if "ordinan darurat" in low_sec or "82/2021" in low_sec:
            sec_errors.append("Ordinan Darurat 2021 telah TAMAT TEMPOH. Rujuk Seksyen 25 Akta 342 (Pindaan Akta A1742) & P.U. (A) 139/2025.")
        if is_akta_852_sec and "16(1)" in low_sec:
            sec_errors.append("Seksyen 16(1) Akta 852 ialah kuasa Menteri mewartakan kawasan. Kesalahan individu merokok ialah Seksyen 16(2) Akta 852.")
        if is_akta_852_sec and "seksyen 44" in low_sec:
            sec_errors.append("Seksyen 44 Akta 852 ialah perlindungan pemberi maklumat. Kuasa kompaun Akta 852 ialah Seksyen 48 [P.U. (A) 259/2024].")
        if ("tifoid" in low_err or "typhoid" in low_err or "vaksin" in low_err) and "peraturan 30" in low_sec and "31" not in low_sec:
            sec_errors.append("Kesalahan pengendali makanan tiada suntikan antitifoid ialah Peraturan 31(1) PPKM 2009 [hukuman Peraturan 31(3)]. Bagi pemilik premis, gunakan Peraturan 11(1)(b) (Peraturan 30 ialah Latihan Pengendali Makanan).")
        if "154" in low_sec and "8(2)" in low_sec:
            sec_errors.append("Kesalahan ingkar perintah Seksyen 8 Akta 154 ialah di bawah Seksyen 8(8) Akta 154 (bukan Seksyen 8(2)).")

        # Sekat kesalahan TIDAK BOLEH KOMPAUN mengikut Senarai Putih Jadual Warta AGC
        if is_akta_852_sec:
            allowed_852 = (r"13\(3\)", r"16\(2\)", r"17\(1\)", r"18\(1\)(?:\([abc]\))?")
            has_allowed_852 = any(re.search(rf"(?<![0-9a-z]){sec}(?![0-9a-z])", low_sec) for sec in allowed_852)
            has_explicit_noncomp_852 = any(
                re.search(rf"(?<![0-9a-z]){sec}(?![0-9a-z])", low_sec)
                for sec in (r"3\(1\)", r"7\(1\)", r"8\(", r"9\(1\)", r"10\(1\)", r"11\(", r"12\(", r"13\(1\)", r"14\(", r"15\(", r"20\(")
            )
            if has_explicit_noncomp_852 or (has_sec_kw and not has_allowed_852):
                sec_errors.append(
                    "TIDAK BOLEH DIKOMPAUN: Di bawah Jadual Pertama P.U. (A) 259/2024, hanya Seksyen 13(3), 16(2), 17(1) dan 18(1) Akta 852 boleh dikompaun. Peruntukan lain (cth: S.3(1), 7(1), 9(1), 10(1), 13(1), 14, 15) wajib disita barang kes dan dibuka Fail IP terus ke Mahkamah."
                )
            # Semakan konsistensi umur OBD (<18 tahun) berdasarkan MyKad (dikira pada tarikh kejadian jika diisi)
            if recipient_age is not None:
                if recipient_age < 5 and "16(2)" in low_sec:
                    sec_warnings.append(
                        f"Sila semak tahun lahir MyKad ({recipient_age} tahun — kemungkinan warga emas lahir pada tahun 1920-an). Sahkan umur sebenar penerima sebelum menyerahkan notis."
                    )
                elif recipient_age < 18 and "16(2)" in low_sec:
                    sec_errors.append(
                        f"SALAH SEKSYEN UMUR (OBD {recipient_age} tahun): Penerima berumur bawah 18 tahun. Gunakan Seksyen 17(1) Akta 852 (bukan Seksyen 16(2)) serta patuhi perlindungan Akta Kanak-Kanak 2001 [Akta 611]."
                    )
                elif recipient_age >= 18 and ("17(1)" in low_sec or "13(3)" in low_sec):
                    sec_errors.append(
                        f"SALAH SEKSYEN UMUR ({recipient_age} tahun): Seksyen 17(1) dan 13(3) Akta 852 hanya terpakai bagi Orang Belum Dewasa (bawah 18 tahun). Bagi dewasa merokok di kawasan larangan, gunakan Seksyen 16(2) Akta 852."
                    )
                elif recipient_age < 18 and ("17(1)" in low_sec or "13(3)" in low_sec):
                    sec_warnings.append(
                        f"Peringatan Akta 611: Penerima ialah Orang Belum Dewasa ({recipient_age} tahun). Maklumkan ibu bapa/penjaga dan elakkan dedahan identiti awam."
                    )

        # Semak Seksyen Akta Makanan 1983 [Akta 281] tidak boleh kompaun walaupun pengguna turut menulis "PPKM"/"PPM"
        if "281" in low_sec or "makanan 1983" in low_sec:
            if re.search(
                r"(?<!\w)(?:seksyen|s\.?)\s*(?:4\(4\)|11(?:\([12]\))?|13(?:\(1\))?|13a(?:\([123]\))?|13b(?:\(\d+\))?|13c|14|15|16|17)(?!\w)",
                low_sec,
            ):
                sec_errors.append(
                    "TIDAK BOLEH DIKOMPAUN: Seksyen 4(4), 11, 13, 13A, 13B, 13C dan 14–17 Akta Makanan 1983 ialah kesalahan serius yang wajib dibuka Kertas Siasatan (IP) untuk pendakwaan terus ke Mahkamah."
                )

        if "154" in low_sec:
            if any(re.search(rf"(?<![0-9a-z]){sec}(?![0-9a-z])", low_sec) for sec in (r"8\(8\)", r"20(?!\w)", r"21(?!\w)")):
                sec_errors.append(
                    "TIDAK BOLEH DIKOMPAUN: Seksyen 8(8) (ingkar perintah bertulis), Seksyen 20 dan Seksyen 21 (menghalang pegawai) Akta 154 wajib dibawa terus ke Mahkamah melalui Kertas Siasatan (IP)."
                )

        if "342" in low_sec:
            allowed_342 = (r"10\(2\)", r"11\(5\)", r"21a\(3\)", r"22\(b\)", r"22\(c\)", r"22\(d\)")
            has_allowed_342 = any(re.search(rf"(?<![0-9a-z]){sec}(?![0-9a-z])", low_sec) for sec in allowed_342)
            has_explicit_noncomp_342 = any(
                re.search(rf"(?<![0-9a-z]){sec}(?![0-9a-z])", low_sec)
                for sec in (r"12\(", r"22\(a\)", r"22\(e\)", r"14(?!\w)", r"14a(?!\w)", r"15\(", r"18\(")
            )
            if has_explicit_noncomp_342 or (has_sec_kw and not has_allowed_342):
                sec_errors.append(
                    "TIDAK BOLEH DIKOMPAUN: Di bawah Jadual Pertama P.U. (A) 139/2025, HANYA Seksyen 10(2), 11(5), 21A(3), 22(b), 22(c) dan 22(d) Akta 342 boleh dikompaun. Buka Kertas Siasatan (IP) untuk pendakwaan terus ke Mahkamah."
                )
            elif "22(b)" in low_sec and any(w in low_err for w in ("tibi", "tuberkulosis", "tbis", "smear")):
                sec_warnings.append(
                    "Dasar UIP KKM: Kes pesakit Tibi cicir rawatan (S.22(b) Akta 342) lazimnya dibawa terus untuk Izin Mendakwa Mahkamah demi keselamatan awam."
                )

        # Semak seksyen rekaan, peruntukan dimansuhkan, penalti/kompaun tidak sah, atau unsur tidak dipenuhi melalui validate_legal_output
        val_res = validate_legal_output(
            {
                "peruntukan_undang": akta_seksyen,
                "keputusan_tindakan": f"Kompaun {akta_seksyen} {amaun_rm}",
                "alasan_keputusan": kesalahan_ringkas,
            },
            lib_snapshot,
            question_context=f"{akta_seksyen} {kesalahan_ringkas}",
        )
        for err_key in ("invalid_citations", "repealed_hits", "penalty_mismatches", "unfulfilled_element_errors"):
            for item_err in val_res.get(err_key) or []:
                if item_err not in sec_errors:
                    sec_errors.append(item_err)

        ok_seksyen = len(sec_errors) == 0
        k06_status = "GAGAL" if not ok_seksyen else ("SEMAK" if sec_warnings else "LULUS")
        k06_note = (
            " ".join(sec_errors)
            if not ok_seksyen
            else (" ".join(sec_warnings) if sec_warnings else f"Peruntukan sah dan boleh dikompaun: {akta_seksyen}")
        )
        checks.append({
            "code": "K06",
            "label": "Ketepatan Seksyen & Status Boleh Kompaun",
            "status": k06_status,
            "note": k06_note,
        })

        # 7. Ayat butiran kesalahan jelas
        ok_butiran = len(kesalahan_ringkas) >= 25
        checks.append({
            "code": "K07",
            "label": "Ayat Butiran Kesalahan Jelas (Fakta Lapangan)",
            "status": "LULUS" if ok_butiran else "GAGAL",
            "note": "Butiran kesalahan menerangkan fakta apa yang dilihat semasa pemeriksaan." if ok_butiran else "Tulis butiran kesalahan dengan jelas (apa yang dilihat/dijumpai oleh PPKP di premis).",
        })

        # 8. Validasi Had Amaun Kompaun & Tempoh Bayaran Mengikut Undang-Undang Sebenar
        rm_val, is_range = self._extract_rm_amount(amaun_rm)
        k08_status = "LULUS"
        k08_note = f"Amaun: {amaun_rm} ({tempoh_bayaran})"
        compact_kp = no_kp.replace(" ", "")
        is_ssm_12 = bool(
            SSM_NEW_RE.match(compact_kp)
            and 1950 <= int(compact_kp[0:4]) <= (date.today().year + 1)
            and int(compact_kp[4:6]) in (1, 2, 3, 4, 5, 6)
        )
        is_corporate = bool(
            is_ssm_12
            or SSM_OLD_RE.match(compact_kp)
            or any(w in nama_penerima.lower() for w in ("sdn", "bhd", "berhad"))
        )
        low_tempoh = tempoh_bayaran.lower()
        has_exact_14_days = bool(re.search(r"(?<!\d)14\s*hari\b", low_tempoh) or re.fullmatch(r"\s*14\s*", low_tempoh))
        has_exact_30_days = bool(re.search(r"(?<!\d)30\s*hari\b", low_tempoh) or re.fullmatch(r"\s*30\s*", low_tempoh))

        if is_non_kkm_statute:
            k08_status = "GAGAL"
            k08_note = "TIDAK SAH: Kesalahan di bawah Akta 574/344/593/56/388/92/611 tidak mempunyai kuasa kompaun oleh PPKP KKM."
        elif is_range:
            k08_status = "GAGAL"
            k08_note = "TIDAK SAH: Amaun kompaun mestilah satu nilai RM tepat (bukan julat seperti 'RM 250 - RM 500')."
        elif rm_val is None or rm_val <= 0:
            k08_status = "GAGAL"
            k08_note = "Masukkan amaun kompaun dalam RM yang sah."
        elif "154" in low_sec:
            if rm_val > 500.0:
                k08_status = "GAGAL"
                k08_note = f"TIDAK SAH (Melebihi Had Undang-Undang): Had kompaun maksimum Seksyen 25 Akta 154 ialah RM 500.00 (anda masukkan RM {rm_val:.2f})."
            elif not has_exact_14_days:
                k08_status = "GAGAL"
                k08_note = "TIDAK SAH: Tempoh bayaran kompaun di bawah Seksyen 25 Akta 154 ialah tepat 14 hari (bukan 30 hari atau nilai lain)."
            elif any(w in (low_premis + " " + low_err) for w in ("tapak bina", "tapak pembinaan", "pembinaan")):
                k08_status = "SEMAK"
                k08_note = f"Amaun RM {rm_val:.2f} (14 hari) mematuhi had S.25 Akta 154. Nota Dasar KKM: Pembiakan Aedes di tapak pembinaan lazimnya disyorkan dibuka IP terus ke Mahkamah."
        elif is_akta_852_sec:
            if ("16(2)" in low_sec or "18(1)" in low_sec) and rm_val > 2500.0:
                k08_status = "GAGAL"
                k08_note = "TIDAK SAH (Melebihi Had Undang-Undang): Had kompaun maksimum ialah 50% daripada denda RM5,000 iaitu RM 2,500.00 (P.U. (A) 259/2024)."
            elif ("17(1)" in low_sec or "13(3)" in low_sec) and rm_val > 250.0:
                k08_status = "GAGAL"
                k08_note = "TIDAK SAH (Melebihi Had Undang-Undang): Had kompaun maksimum OBD ialah 50% daripada denda RM500 iaitu RM 250.00 (P.U. (A) 259/2024)."
            elif not has_exact_30_days:
                k08_status = "GAGAL"
                k08_note = "TIDAK SAH: Di bawah Peraturan Pengkompaunan Akta 852 [P.U. (A) 259/2024], tempoh bayaran rasmi ialah tepat 30 hari (serta memerlukan keizinan bertulis Pendakwa Raya / Borang 1)."
            else:
                k08_note = f"Amaun RM {rm_val:.2f} (30 hari) mematuhi had P.U. (A) 259/2024. Pastikan keizinan bertulis Pendakwa Raya (Borang 1 S.48(2)) diperoleh sebelum tawaran kompaun."
        elif "342" in low_sec:
            cap_342 = 50000.0 if is_corporate else 5000.0
            if rm_val > cap_342:
                k08_status = "GAGAL"
                k08_note = f"TIDAK SAH (Melebihi Had Undang-Undang): Had kompaun maksimum Seksyen 25 Akta 342 [P.U. (A) 139/2025] ialah RM {cap_342:,.2f}."
            elif not has_exact_14_days:
                k08_status = "GAGAL"
                k08_note = "TIDAK SAH: Tempoh bayaran tawaran kompaun di bawah Seksyen 25 Akta 342 [P.U. (A) 139/2025] ialah tepat 14 hari."
            else:
                k08_note = f"Amaun RM {rm_val:.2f} (14 hari) mematuhi had Seksyen 25 Akta 342 (maks RM5,000 individu / RM50,000 syarikat dengan keizinan bertulis Pendakwa Raya)."
        elif "ppkm" in low_sec or "281" in low_sec or "ppm" in low_sec or "makanan" in low_sec:
            if re.search(r"(?<![0-9a-z])32(?:\([123]\))?(?![0-9a-z])", low_sec) and "ppkm" in low_sec and rm_val > 500.0:
                k08_status = "GAGAL"
                k08_note = "TIDAK SAH: Had kompaun maksimum Peraturan 32 PPKM 2009 ialah 50% daripada denda RM1,000 [Peraturan 32(3)], iaitu RM 500.00."
            elif rm_val > 5000.0:
                k08_status = "GAGAL"
                k08_note = "TIDAK SAH (Melebihi Had Undang-Undang): Had kompaun maksimum Seksyen 33 Akta Makanan 1983 (50% daripada denda RM10,000) ialah RM 5,000.00."
            elif not has_exact_14_days:
                k08_status = "GAGAL"
                k08_note = "TIDAK SAH: Tempoh bayaran kompaun Notis S.32B / S.33 Akta Makanan 1983 (PPKM 2009) ialah tepat 14 hari."
        elif not (has_exact_14_days or has_exact_30_days):
            k08_status = "SEMAK"
            k08_note = "Nyatakan tempoh bayaran rasmi (14 hari bagi Akta 154/281/342, 30 hari bagi Akta 852)."

        checks.append({
            "code": "K08",
            "label": "Had Amaun Kompaun & Tempoh Bayaran Mengikut Undang-Undang",
            "status": k08_status,
            "note": k08_note,
        })

        # 9. No. Siri Notis, Nama & No. Kad Kuasa PPKP pengeluar notis
        ok_ppkp = len(pegawai_pengeluar) >= 5 and len(no_kad_kuasa) >= 4
        ok_no_notis = len(no_notis) >= 3 and "[" not in no_notis
        if not ok_ppkp:
            k09_status = "GAGAL"
            k09_note = "Wajib isi nama PPKP dan No. Kad Kuasa rasmi KKM pada borang notis."
        elif not ok_no_notis:
            k09_status = "SEMAK"
            k09_note = f"Dikeluarkan oleh {pegawai_pengeluar} ({no_kad_kuasa}), tetapi No. Siri Notis belum diisi."
        else:
            k09_status = "LULUS"
            k09_note = f"No. Notis {no_notis} dikeluarkan oleh {pegawai_pengeluar} ({no_kad_kuasa})."
        checks.append({
            "code": "K09",
            "label": "No. Siri Notis, Nama & No. Kad Kuasa PPKP Pengeluar",
            "status": k09_status,
            "note": k09_note,
        })

        # 10. Status serahan (tandatangan terima / enggan tandatangan + saksi PPKP)
        if status_serahan == "enggan_tandatangan":
            ok_serahan = len(saksi_ppkp) >= 5
            serahan_note = (
                f"Penerima enggan tandatangan — disaksikan oleh {saksi_ppkp} (sambung serahan Pos Berdaftar AR)."
                if ok_serahan
                else "Jika OKS enggan tandatangan terima notis, wajib catat nama PPKP saksi pengiring dan hantar melalui Pos Berdaftar AR."
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
            readiness = "SEDIA CETAK & SERAH (LENGKAP)"
        elif gagal == 0:
            readiness = "PERLU SEMAKAN RINGKAS"
        else:
            readiness = "TIDAK SAH / PERLU BETULKAN DAHULU"

        # Pisahkan ayat Butiran Kesalahan Notis Kompaun daripada Ayat Pertuduhan Borang 114
        if is_non_kkm_statute:
            peruntukan_kompaun = "TIDAK BOLEH DIKOMPAUN OLEH PPKP (Bukan Bidang Kuasa Kompaun KKM)"
        elif is_akta_852_sec:
            peruntukan_kompaun = "Seksyen 48 Akta 852 [P.U. (A) 259/2024]"
        elif "154" in low_sec:
            peruntukan_kompaun = "Seksyen 25 Akta 154"
        elif "342" in low_sec:
            peruntukan_kompaun = "Seksyen 25 Akta 342 [P.U. (A) 139/2025]"
        else:
            peruntukan_kompaun = "Notis Seksyen 32B & Seksyen 33 Akta Makanan 1983"

        # Elak ayat cadangan dibungkus dua kali ("Pada ..., telah didapati pada ..., telah didapati ...")
        raw_err = (kesalahan_ringkas or "").strip()
        m_already_wrapped = re.search(
            r"telah\s+didapati\s+(.*?)(?:,\s*yang\s+merupakan\s+suatu\s+kesalahan\s+di\s+bawah\b.*)?$",
            raw_err,
            flags=re.I | re.S,
        )
        clean_err = (m_already_wrapped.group(1) if m_already_wrapped else raw_err).strip().rstrip(". ,;")
        if clean_err and len(clean_err) >= 2 and clean_err[0].isupper() and not clean_err[1].isupper():
            clean_err = clean_err[0].lower() + clean_err[1:]
        lokasi_part = f"{nama_premis}, {alamat_kejadian}" if (nama_premis and alamat_kejadian) else (nama_premis or alamat_kejadian or "[Lokasi / Alamat Kejadian]")

        suggested_offense_text = (
            f"Pada {tarikh_masa or '[Tarikh & Masa]'}, bertempat di {lokasi_part}, "
            f"kamu {nama_penerima or '[Nama Penerima]'} (No. Pengenalan: {no_kp or '[No. KP/Pasport]'}) "
            f"telah didapati {clean_err or '[nyatakan perbuatan kesalahan]'}, yang merupakan suatu kesalahan di bawah "
            f"{akta_seksyen or '[Seksyen Kesalahan]'} dan boleh dikompaun di bawah {peruntukan_kompaun}."
        )

        return {
            "readiness_status": readiness,
            "score_percent": round((lulus / len(checks)) * 100, 1),
            "counts": {"LULUS": lulus, "SEMAK": semak, "GAGAL": gagal},
            "checks": checks,
            "suggested_offense_text": suggested_offense_text,
            "peruntukan_kompaun": peruntukan_kompaun,
            "legal_validation": val_res,
        }
