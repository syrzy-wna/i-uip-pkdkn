"""Penjana Dokumen Rasmi .docx KKM & Mahkamah Majistret Seluruh Malaysia (python-docx).

Menghasilkan dokumen mengikut format sebenar amalan Mahkamah Majistret & UIP KKM (Semenanjung, Sabah, Sarawak & WP):
1. Borang Mahkamah 114 (Kertas Pertuduhan Rasmi KTJ — tanpa jadual biru kolej!)
2. Borang Mahkamah 143 (Pengaduan kepada Majistret — Seksyen 128 KTJ)
3. Diari Siasatan (Seksyen 119 KTJ — dengan tanda SULIT S.119(2) KTJ)
4. Rakaman Percakapan Seksyen 112 KTJ (dengan Amaran S.112(4), Soal-Jawab, Perakuan S.112(5) & Cap Ibu Jari)
5. Sijil Seksyen 90A(2) & (3)(a) Akta Keterangan 1950 (lengkap jadual peranti, KEW.PA & klausa statutori)
6. Pakej Kertas Siasatan Lengkap (Kulit IP, Indeks A-G, Kertas Minit 1-4, Izin Mendakwa TPR, Borang 143, Borang 114, Fakta Kes, Saksi, Eksibit, Sijil 90A, Rakaman S.112, DS)
7. Notis Kompaun Lapangan / Notis Seksyen 32B / Seksyen 47 / Borang 2 P.U.(A) 259/2024
"""

from __future__ import annotations

import io
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

from backend.core.malaysia_offices import (
    normalize_malaysia_health_office,
    resolve_saman_jurisdiction_header,
)

# Buang aksara kawalan XML tidak sah (cth: form-feed \x0c, vertical-tab \x0b, NUL \x00 dari PDF)
_XML_ILLEGAL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_FILENAME_SAFE_RE = re.compile(r"[^A-Za-z0-9_-]+")


def _safe_str(val: Any, default: str = "-") -> str:
    if val is None:
        return default
    cleaned = _XML_ILLEGAL_RE.sub("", str(val))
    return cleaned if cleaned.strip() else default


def _safe_dict(val: Any) -> Dict[str, Any]:
    return val if isinstance(val, dict) else {}


def _safe_list(val: Any) -> List[Any]:
    return val if isinstance(val, list) else []


def _slug_for_filename(raw: Any) -> str:
    s = _safe_str(raw, "").strip()
    if not s or "[" in s or "..." in s:
        return ""
    slug = _FILENAME_SAFE_RE.sub("_", s).strip("_")
    return slug[:36]


def _resolve_office_display(
    b114: Dict[str, Any],
    s90a: Optional[Dict[str, Any]] = None,
    officer_profile: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    prof = _safe_dict(officer_profile)
    s90 = _safe_dict(s90a)
    pejabat_explicit = _safe_str(
        b114.get("pejabat_pkd") or s90.get("pejabat_pkd") or prof.get("district_pkd"),
        "",
    )
    daerah_raw = _safe_str(b114.get("daerah"), "")
    if daerah_raw == "-":
        daerah_raw = ""
    negeri_raw = _safe_str(b114.get("negeri"), "")
    if negeri_raw == "-":
        negeri_raw = ""
    # Bersihkan pengepala "DALAM NEGERI ... MALAYSIA" sekiranya sudah berformat mahkamah
    negeri_clean_in = re.sub(
        r"^(?:DALAM\s+NEGERI|DI\s+NEGERI|DI)\s+", "", negeri_raw, flags=re.I
    )
    negeri_clean_in = re.sub(r",?\s*MALAYSIA\s*$", "", negeri_clean_in, flags=re.I).strip()

    return normalize_malaysia_health_office(
        district_pkd=pejabat_explicit,
        state_jkn=_safe_str(prof.get("state_jkn"), ""),
        daerah_override=daerah_raw if not pejabat_explicit else "",
        negeri_override=negeri_clean_in,
    )


def _set_cell_shading(cell: Any, fill_hex: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill_hex)
    tc_pr.append(shd)


def _configure_base_doc(font_name: str = "Times New Roman") -> Document:
    doc = Document()
    for section in doc.sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.9)
        section.right_margin = Inches(0.9)
    style = doc.styles["Normal"]
    style.font.name = font_name
    style.font.size = Pt(11)
    style.font.color.rgb = RGBColor(0, 0, 0)
    return doc


def _add_paragraph_text(
    doc: Document,
    text: Any,
    bold: bool = False,
    italic: bool = False,
    underline: bool = False,
    size: int = 11,
    align: WD_ALIGN_PARAGRAPH = WD_ALIGN_PARAGRAPH.LEFT,
    space_before: int = 0,
    space_after: int = 4,
) -> Any:
    p = doc.add_paragraph()
    p.alignment = align
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(space_after)
    safe_txt = _XML_ILLEGAL_RE.sub("", "" if text is None else str(text))
    run = p.add_run(safe_txt)
    run.bold = bold
    run.italic = italic
    run.underline = underline
    run.font.name = "Times New Roman"
    run.font.size = Pt(size)
    run.font.color.rgb = RGBColor(0, 0, 0)
    return p


def _add_clean_table(
    doc: Document,
    headers: List[str],
    rows: List[List[Any]],
    header_fill: str = "E2E8F0",
) -> None:
    """Jadual rasmi KKM (latar kelabu cair profesional, tulisan hitam)."""
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    hdr_cells = table.rows[0].cells
    for i, header in enumerate(headers):
        hdr_cells[i].text = _safe_str(header, "")
        _set_cell_shading(hdr_cells[i], header_fill)
        for paragraph in hdr_cells[i].paragraphs:
            for run in paragraph.runs:
                run.bold = True
                run.font.size = Pt(10)
                run.font.name = "Times New Roman"
                run.font.color.rgb = RGBColor(0, 0, 0)

    for row_data in rows:
        row_cells = table.add_row().cells
        for i, val in enumerate(row_data):
            row_cells[i].text = _safe_str(val, "-")
            for paragraph in row_cells[i].paragraphs:
                for run in paragraph.runs:
                    run.font.size = Pt(10)
                    run.font.name = "Times New Roman"
                    run.font.color.rgb = RGBColor(0, 0, 0)


def _doc_to_bytes(doc: Document) -> bytes:
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.getvalue()


def _append_kulit_dan_indeks_ip(
    doc: Document,
    payload: Dict[str, Any],
    officer_profile: Optional[Dict[str, Any]] = None,
) -> None:
    current_year = datetime.now().year
    b114 = _safe_dict(payload.get("borang_114"))
    s90a = _safe_dict(payload.get("sijil_90a"))
    office = _resolve_office_display(b114, s90a, officer_profile)
    no_kes = _safe_str(b114.get("no_kes"), f"PKD/UIP/{current_year}/001")
    akta = _safe_str(payload.get("akta_utama"), "-")
    office_line = f"{office['pejabat_rasmi']} / {office['negeri']}" if office["negeri"] else office["pejabat_rasmi"]

    _add_paragraph_text(doc, "SULIT (UNTUK KEGUNAAN RASMI UIP KKM SAHAJA)", bold=True, size=10, align=WD_ALIGN_PARAGRAPH.RIGHT, space_after=6)
    _add_paragraph_text(doc, "KEMENTERIAN KESIHATAN MALAYSIA", bold=True, size=13, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    _add_paragraph_text(doc, "UNIT INSPEKTORAT DAN PERUNDANGAN (UIP)", bold=True, size=12, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    _add_paragraph_text(doc, "KULIT KERTAS SIASATAN (IP)", bold=True, underline=True, size=12, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=10)

    kulit_rows = [
        ["No. Kertas Siasatan (IP)", no_kes],
        ["Pejabat Kesihatan / Negeri", office_line],
        ["Akta & Seksyen Kesalahan", f"{akta} — {_safe_str(b114.get('akta_dan_seksyen'))}"],
        ["Seksyen Hukuman", _safe_str(b114.get("seksyen_hukuman"))],
        ["Nama OKS / OKT", _safe_str(b114.get("nama_tertuduh"))],
        ["No. Kad Pengenalan / SSM", _safe_str(b114.get("no_kp_tertuduh"))],
        ["Tarikh & Masa Kejadian", f"{_safe_str(b114.get('tarikh_kejadian'))} / {_safe_str(b114.get('masa_kejadian'))}"],
        ["Alamat Tempat Kejadian", _safe_str(b114.get("tempat_kejadian"))],
        ["Pegawai Penyiasat (IO)", _safe_str(b114.get("pegawai_pengadu") or _safe_dict(officer_profile).get("full_name"))],
    ]
    _add_clean_table(doc, ["Perkara Kulit IP", "Butiran Kes"], kulit_rows)

    _add_paragraph_text(doc, "INDEKS KANDUNGAN FAIL KERTAS SIASATAN (7 BAHAGIAN A–G)", bold=True, underline=True, size=11, space_before=12, space_after=6)
    indeks_rows = [
        ["A", "Kertas Minit (Am 6), Izin Mendakwa TPR, Kronologi, Kertas Cadangan IO, Laporan Pengadu & Fakta Kes", "Bahagian A"],
        ["B", "Pengaduan kepada Majistret (Borang 143), Saman (Borang 111) & Kertas Pertuduhan (Borang 114)", "Bahagian B"],
        ["C", "Notis S.32B / S.47 / Arahan Rawatan Akta 342, Tawaran Kompaun, Pengesahan Belum Bayar & Kad AR", "Bahagian C"],
        ["D", "Borang Sitaan (S.36) / Perintah S.11, Senarai Barang Kes (P), Pelan Lakar, Gambar & Sijil Seksyen 90A(2)", "Bahagian D"],
        ["E", "Rakaman Percakapan Seksyen 112 KTJ (Saksi & OKT) & Senarai Saksi Pendakwaan (SP)", "Bahagian E"],
        ["F", "Cetakan Carian SSM, Salinan Kad Kuasa & Laporan Makmal (S.19/S.20) / Entomologi / TBIS 20C", "Bahagian F"],
        ["G", "Diari Siasatan (Seksyen 119 KTJ — SULIT S.119(2)) & Hujahan Pemberatan Hukuman (Folio Berasingan)", "Bahagian G"],
    ]
    _add_clean_table(doc, ["Bahagian", "Perihal Kandungan Fail IP", "Folio"], indeks_rows)


def _append_minit_ip(doc: Document, minit_list: Any, no_kes: str) -> None:
    _add_paragraph_text(doc, "(Am 6)", bold=True, size=10, align=WD_ALIGN_PARAGRAPH.RIGHT, space_after=1)
    _add_paragraph_text(doc, "KERTAS MINIT KERTAS SIASATAN", bold=True, size=12, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    _add_paragraph_text(doc, f"No. Kertas Siasatan: {_safe_str(no_kes)}", bold=True, size=11, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=10)

    if isinstance(minit_list, str):
        _add_paragraph_text(doc, minit_list, size=11, space_after=8)
    else:
        rows = []
        for idx, item in enumerate(_safe_list(minit_list), start=1):
            if isinstance(item, dict):
                rows.append([
                    _safe_str(item.get("bil") or item.get("no_minit"), f"Minit {idx}"),
                    _safe_str(item.get("tarikh")),
                    f"Daripada: {_safe_str(item.get('daripada'))}\nKepada: {_safe_str(item.get('kepada'))}",
                    _safe_str(item.get("kandungan") or item.get("butiran") or item.get("catatan")),
                ])
        _add_clean_table(doc, ["No. Minit", "Tarikh", "Pengirim / Penerima", "Butiran Minit & Arahan"], rows or [["Minit 1", "-", "-", "-"]])

    _add_paragraph_text(
        doc,
        "(Kertas Minit ini dalam ukuran Metrik ISO A4 = 210mm x 297mm)",
        italic=True,
        size=8,
        align=WD_ALIGN_PARAGRAPH.CENTER,
        space_before=6,
        space_after=4,
    )


def _append_izin_mendakwa(doc: Document, izin: Dict[str, Any]) -> None:
    izin_d = _safe_dict(izin)
    if not izin_d:
        return
    _add_paragraph_text(doc, "PERMOHONAN IZIN MENDAKWA (KEIZINAN PENDAKWA RAYA)", bold=True, size=12, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    _add_paragraph_text(
        doc,
        f"({_safe_str(izin_d.get('peruntukan_izin'), 'Perkara 145(3) Perlembagaan Persekutuan, Seksyen 376(3) & Seksyen 377(b) Kanun Tatacara Jenayah')})",
        bold=True,
        size=10,
        align=WD_ALIGN_PARAGRAPH.CENTER,
        space_after=10,
    )

    _add_paragraph_text(doc, f"Kepada: {_safe_str(izin_d.get('kepada'), 'Timbalan Pendakwa Raya')}", bold=True, space_after=4)
    _add_paragraph_text(doc, f"No. Rujukan Kertas Siasatan: {_safe_str(izin_d.get('rujukan_ip'))}", space_after=6)
    _add_paragraph_text(
        doc,
        f"Adalah dengan hormatnya dikemukakan Kertas Siasatan di atas terhadap {_safe_str(izin_d.get('nama_okt'))} "
        f"bagi kesalahan di bawah {_safe_str(izin_d.get('seksyen_dipohon'))} untuk pertimbangan dan keizinan bertulis "
        "Pihak Yang Arif Timbalan Pendakwa Raya bagi memulakan pendakwaan di Mahkamah Majistret.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY,
        space_after=18,
    )
    _add_paragraph_text(doc, "[   ] DIIZINKAN MENDAKWA        [   ] TIDAK DIIZINKAN / KEMBALIKAN UNTUK SIASATAN LANJUT", bold=True, space_after=18)
    _add_paragraph_text(
        doc,
        "............................................................\n"
        "Timbalan Pendakwa Raya\n"
        "Jabatan Peguam Negara Malaysia\n"
        "Tarikh: ........................................",
        space_after=8,
    )


def _append_borang_143(doc: Document, b143: Dict[str, Any]) -> None:
    d143 = _safe_dict(b143)
    if not d143:
        return
    _add_paragraph_text(doc, "(Mahkamah 143)", bold=True, size=10, align=WD_ALIGN_PARAGRAPH.RIGHT, space_after=2)
    _add_paragraph_text(doc, "(Seksyen 128 Kanun Tatacara Jenayah)", italic=True, size=10, align=WD_ALIGN_PARAGRAPH.RIGHT, space_after=6)
    _add_paragraph_text(doc, "PENGADUAN KEPADA MAJISTRET", bold=True, underline=True, size=12, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    _add_paragraph_text(doc, _safe_str(d143.get("mahkamah"), "DALAM MAHKAMAH MAJISTRET"), bold=True, size=11, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=10)

    _add_paragraph_text(
        doc,
        f"Saya, {_safe_str(d143.get('pengadu'))}, dengan ini mengadu kepada Majistret bahawa "
        f"{_safe_str(d143.get('oks_nama'))} (No. K/P / SSM: {_safe_str(d143.get('oks_kp'))}) yang beralamat di "
        f"{_safe_str(d143.get('oks_alamat'))} telah melakukan kesalahan seperti berikut:-",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY,
        space_after=8,
    )
    _add_paragraph_text(doc, _safe_str(d143.get("butiran_aduan")), align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_after=14)
    _add_paragraph_text(
        doc,
        "Tandatangan Pengadu: ........................................     Diambil di hadapan saya,\n"
        "Jawatan: Pegawai Diberi Kuasa KKM                                 ......................................................\n"
        "Tarikh: ........................................                  Majistret",
        size=10,
    )


def _append_borang_114(
    doc: Document,
    b114: Dict[str, Any],
    officer_profile: Optional[Dict[str, Any]] = None,
) -> None:
    """Format tulen Borang Mahkamah 114 (Jadual Kedua KTJ — seragam seluruh Malaysia)."""
    d114 = _safe_dict(b114)
    current_year = datetime.now().year
    office = _resolve_office_display(d114, None, officer_profile)
    prof = _safe_dict(officer_profile)

    sec_combo_low = f"{_safe_str(d114.get('akta_dan_seksyen'), '')} {_safe_str(d114.get('hukuman_maksimum'), '')}".lower()
    requires_sessions_court = bool(
        ("281" in sec_combo_low or "makanan 1983" in sec_combo_low)
        and re.search(r"(?<!\w)(?:seksyen\s+(?:13(?:\(1\))?|13a(?:\(\d+\))?|13b(?:\(\d+\))?)|s\.?\s*(?:13(?:\(1\))?|13a|13b))(?!\w)", sec_combo_low)
    )
    raw_mahkamah = _safe_str(
        d114.get("mahkamah") or prof.get("default_magistrate_court"),
        "DALAM MAHKAMAH SESYEN" if requires_sessions_court else "DALAM MAHKAMAH MAJISTRET",
    )
    if requires_sessions_court and "majistret" in raw_mahkamah.lower() and "sesyen" not in raw_mahkamah.lower():
        mahkamah_hdr = re.sub(r"MAHKAMAH\s+MAJISTRET", "MAHKAMAH SESYEN", raw_mahkamah, flags=re.I)
    else:
        mahkamah_hdr = raw_mahkamah
    negeri_hdr = _safe_str(d114.get("negeri"), "")
    if not negeri_hdr or negeri_hdr == "-":
        negeri_hdr = office["negeri_mahkamah"] if office["negeri"] else ""

    _add_paragraph_text(doc, "(Mahkamah 114)", bold=True, size=10, align=WD_ALIGN_PARAGRAPH.RIGHT, space_after=1)
    _add_paragraph_text(doc, "(Kanun Tatacara Jenayah — Seksyen 152, 153 & 154)", italic=True, size=9, align=WD_ALIGN_PARAGRAPH.RIGHT, space_after=6)

    _add_paragraph_text(doc, mahkamah_hdr, bold=True, size=12, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=1)
    if negeri_hdr and negeri_hdr.lower() not in mahkamah_hdr.lower():
        _add_paragraph_text(doc, negeri_hdr, bold=True, size=11, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=1)
    _add_paragraph_text(doc, f"KES SAMAN NO: {_safe_str(d114.get('no_kes'), f'.................... TAHUN {current_year}')}", bold=True, size=11, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=10)

    nama_tertuduh = _safe_str(d114.get("nama_tertuduh"))
    no_kp_tertuduh = _safe_str(d114.get("no_kp_tertuduh"))
    is_corp_okt = any(w in nama_tertuduh.lower() for w in ("sdn", "bhd", "berhad", "enterprise", "plt", "llp"))

    _add_paragraph_text(doc, "PENDAKWA RAYA", bold=True, size=11, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    _add_paragraph_text(doc, "LAWAN", bold=True, size=10, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    _add_paragraph_text(doc, nama_tertuduh, bold=True, size=11, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=10)

    if is_corp_okt:
        butiran_oks = (
            f"Nama Syarikat / OKS       : {nama_tertuduh}\n"
            f"No. Pendaftaran SSM / K/P : {no_kp_tertuduh}\n"
            f"Alamat Berdaftar / Premis : {_safe_str(d114.get('alamat_tertuduh'))}"
        )
    else:
        butiran_oks = (
            f"Nama OKS / Tertuduh   : {nama_tertuduh}\n"
            f"No. Kad Pengenalan    : {no_kp_tertuduh}\n"
            f"Umur / Jantina        : {_safe_str(d114.get('umur_jantina'))}\n"
            f"Pekerjaan / Jawatan   : {_safe_str(d114.get('pekerjaan'))}\n"
            f"Alamat Terkini        : {_safe_str(d114.get('alamat_tertuduh'))}"
        )
    _add_paragraph_text(doc, butiran_oks, size=10, space_after=10)

    pengadu_name = _safe_str(d114.get("pegawai_pengadu") or prof.get("full_name"), "Pegawai Pendakwa KKM")
    _add_paragraph_text(
        doc,
        f"adalah dituduh atas pengaduan {pengadu_name} bagi pihak Pendakwa Raya seperti berikut:-",
        italic=True,
        size=11,
        space_after=8,
    )

    _add_paragraph_text(doc, "PERTUDUHAN", bold=True, underline=True, size=11, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=6)
    _add_paragraph_text(doc, _safe_str(d114.get("teks_pertuduhan")), size=11, align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_after=10)

    _add_paragraph_text(
        doc,
        f"Seksyen Kesalahan : {_safe_str(d114.get('akta_dan_seksyen'))}\n"
        f"Seksyen Hukuman   : {_safe_str(d114.get('seksyen_hukuman'))}\n"
        f"Hukuman Maksimum  : {_safe_str(d114.get('hukuman_maksimum'))}",
        bold=True,
        size=10,
        space_after=16,
    )

    bench_title = "Hakim Mahkamah Sesyen" if requires_sessions_court else "Majistret"
    bench_court = "Mahkamah Sesyen (S.63/64 Akta 92)" if requires_sessions_court else "Mahkamah Majistret"
    _add_paragraph_text(
        doc,
        f"Bertarikh pada ........ haribulan ...................... {current_year}\n\n\n"
        "............................................................          ............................................................\n"
        f"Timbalan Pendakwa Raya / Pegawai Pendakwa                          {bench_title}\n"
        f"Bagi Pihak Pendakwa Raya (Seksyen 376 / 377(b) KTJ)                {bench_court}",
        size=10,
    )


def _append_diari_siasatan(
    doc: Document,
    entries: Any,
    no_kes: str,
    b114: Dict[str, Any],
    s90a: Optional[Dict[str, Any]] = None,
    officer_profile: Optional[Dict[str, Any]] = None,
) -> None:
    d114 = _safe_dict(b114)
    office = _resolve_office_display(d114, s90a, officer_profile)
    prof = _safe_dict(officer_profile)

    _add_paragraph_text(
        doc,
        "SULIT — TERLINDUNG DI BAWAH SEKSYEN 119(2) KTJ (TIDAK BOLEH DIDEDAHKAN KEPADA OKT)",
        bold=True,
        size=9,
        align=WD_ALIGN_PARAGRAPH.RIGHT,
        space_after=4,
    )
    _add_paragraph_text(doc, "KEMENTERIAN KESIHATAN MALAYSIA", bold=True, size=12, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=1)
    _add_paragraph_text(doc, "DIARI SIASATAN (SEKSYEN 119 KANUN TATACARA JENAYAH)", bold=True, underline=True, size=11, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=8)

    nama_io = _safe_str(d114.get("pegawai_pengadu") or prof.get("full_name"))
    nama_oks = _safe_str(d114.get("nama_tertuduh"))
    no_kp_oks = _safe_str(d114.get("no_kp_tertuduh"))
    pejabat_line = f"{office['pejabat_rasmi']}, {office['negeri']}" if office["negeri"] else office["pejabat_rasmi"]

    meta_rows = [
        ["Nama Pegawai", nama_io, "No. Kes / IP", _safe_str(no_kes)],
        ["Jawatan", "PPKP / Pegawai Penyiasat (IO)", "Seksyen", _safe_str(d114.get("akta_dan_seksyen"))],
        ["Pejabat", pejabat_line, "Nama OKS/OKT", f"{nama_oks} (No. K/P / SSM: {no_kp_oks})"],
    ]
    _add_clean_table(doc, ["Perkara", "Butiran Pegawai", "Rujukan", "Butiran Kes"], meta_rows)
    _add_paragraph_text(doc, "", space_after=4)

    rows = []
    for i, e in enumerate(_safe_list(entries)):
        if not isinstance(e, dict):
            continue
        tarikh_val = _safe_str(e.get("tarikh") or e.get("tarikh_masa"))
        masa_val = _safe_str(e.get("masa"), "")
        tarikh_masa = f"{tarikh_val}\n({masa_val})".strip() if masa_val and masa_val != "-" else tarikh_val
        butiran = _safe_str(e.get("butiran_tindakan"))
        rows.append([
            _safe_str(e.get("bil"), str(i + 1)),
            tarikh_masa,
            f"{butiran}\n\n[t.t. awal IO: ............]",
        ])
    if not rows:
        rows = [["1", "-", "Tiada catatan diari siasatan."]]
    _add_clean_table(doc, ["No. Butir-Butir Penyiasatan", "Tarikh & Masa", "Butir-Butir Penyiasatan"], rows)

    _add_paragraph_text(
        doc,
        "\nDisahkan oleh Pegawai Penyiasat (IO):\n"
        f"........................................\n"
        f"({nama_io})\n"
        f"{office['pejabat_rasmi']}    |    Tarikh: ....................",
        size=10,
        space_before=12,
    )


def _append_rakaman_112(doc: Document, rakaman_112: Any, no_kes: str) -> None:
    raw_112 = _safe_str(rakaman_112, "-")
    _add_paragraph_text(doc, "PERCAKAPAN DI BAWAH SEKSYEN 112 KANUN TATACARA JENAYAH [AKTA 593]", bold=True, underline=True, size=11, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    _add_paragraph_text(doc, f"No. Kertas Siasatan: {_safe_str(no_kes)}", bold=True, size=10, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=4)
    _add_paragraph_text(
        doc,
        "Tarikh & Masa Mula Rakaman: ........................................    |    Bahasa Digunakan: Bahasa Melayu / ....................................",
        size=9,
        align=WD_ALIGN_PARAGRAPH.CENTER,
        space_after=8,
    )

    if "112(2)" not in raw_112 and "112(4)" not in raw_112:
        _add_paragraph_text(
            doc,
            "AMARAN WAJIB DI BAWAH SEKSYEN 112(4) KANUN TATACARA JENAYAH:\n"
            "\"Kamu adalah terikat untuk menjawab semua soalan yang berhubungan dengan kes ini yang dikemukakan kepada kamu oleh saya "
            "di bawah Seksyen 112(2) Kanun Tatacara Jenayah, tetapi kamu berhak menolak untuk menjawab mana-mana soalan yang jawapannya "
            "berkecenderungan mendedahkan kamu kepada sesuatu pertuduhan jenayah atau penalti atau pelucuthakan. Kamu juga adalah terikat "
            "di sisi undang-undang untuk menyatakan yang benar di bawah Seksyen 112(3) Kanun Tatacara Jenayah.\"\n"
            "Pengakuan Faham Orang Yang Diperiksa: [   ] Faham    Tandatangan Awal: ............................",
            bold=True,
            size=9,
            align=WD_ALIGN_PARAGRAPH.JUSTIFY,
            space_after=8,
        )

    _add_paragraph_text(doc, raw_112, size=10, align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_after=12)

    _add_paragraph_text(
        doc,
        "PERAKUAN PENUTUP DI BAWAH SEKSYEN 112(5) KANUN TATACARA JENAYAH:\n"
        "\"Percakapan di atas telah dibaca semula kepada saya dalam bahasa yang saya gunakan semasa memberikannya "
        "(Bahasa Melayu / melalui jurubahasa), dan saya telah diberi peluang untuk membuat apa-apa pembetulan yang saya kehendaki, "
        "serta saya mengakui percakapan tersebut adalah benar dan betul.\"",
        bold=True,
        size=10,
        space_after=14,
    )

    _add_paragraph_text(
        doc,
        ".................................................          .................................................\n"
        "Tandatangan / Cap Ibu Jari Orang Yang Diperiksa            Tandatangan Pegawai Perakam (IO)\n"
        "No. K/P / Pasport: .............................            No. Kad Kuasa KKM: .............................\n\n"
        ".................................................          .................................................\n"
        "Tandatangan Jurubahasa (jika ada)                          Tarikh & Masa Tamat Rakaman",
        size=10,
    )


def _append_sijil_90a(
    doc: Document,
    s90a: Dict[str, Any],
    no_kes: str,
    officer_profile: Optional[Dict[str, Any]] = None,
) -> None:
    d90 = _safe_dict(s90a)
    prof = _safe_dict(officer_profile)
    _add_paragraph_text(doc, "SIJIL PERAKUAN DI BAWAH SEKSYEN 90A(2) & (3)(a) AKTA KETERANGAN 1950 [AKTA 56]", bold=True, underline=True, size=11, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    _add_paragraph_text(doc, f"NO. KERTAS SIASATAN: {_safe_str(no_kes)}", bold=True, size=10, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=10)

    nama = _safe_str(d90.get("nama_pegawai") or prof.get("full_name"), "........................................")
    jawatan = _safe_str(d90.get("jawatan") or prof.get("designation"), "Penolong Pegawai Kesihatan Persekitaran (PPKP)")
    pejabat = _safe_str(d90.get("pejabat_pkd") or prof.get("district_pkd"), "Pejabat Kesihatan Daerah / Kawasan / Bahagian")

    _add_paragraph_text(
        doc,
        f"Saya, {nama}, yang memegang jawatan sebagai {jawatan} di {pejabat}, Kementerian Kesihatan Malaysia, "
        "dengan ini memperakui seperti berikut:-",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY,
        space_after=8,
    )

    hw_rows = [
        ["Peranti Pengambil Gambar / Kamera", _safe_str(d90.get("peranti_kamera") or prof.get("default_camera_desc"), "Kamera Digital Rasmi Penguatkuasaan KKM")],
        ["Komputer Pemproses", _safe_str(d90.get("perihal_komputer") or prof.get("default_computer_desc"), "Komputer Meja Rasmi Pejabat KKM")],
        ["Pencetak (Printer)", _safe_str(d90.get("perihal_pencetak") or prof.get("default_printer_desc"), "Pencetak Laser Warna Pejabat KKM")],
        ["No. Siri / No. Harta Modal (KEW.PA) & Tarikh Cetakan", _safe_str(d90.get("no_siri_kewpa"), "[Nyatakan No. Harta Modal KEW.PA / Tarikh & Masa Cetakan]")],
        ["Dokumen / Eksibit Digital Dicetak", _safe_str(d90.get("senarai_dokumen_digital"))],
    ]
    _add_clean_table(doc, ["Butiran Perkakasan & Eksibit Digital", "Spesifikasi Rasmi"], hw_rows)

    klausa = (
        "\n1. Bahawa saya ialah orang yang bertanggungjawab bagi pengurusan pengendalian komputer tersebut "
        "atau bagi penjalanan aktiviti yang baginya komputer tersebut digunakan sebagaimana dinyatakan dalam jadual di atas.\n\n"
        "2. Bahawa dokumen-dokumen dan cetakan gambar digital tersebut telah dikeluarkan oleh komputer "
        "berkenaan dalam perjalanan penggunaannya yang biasa menurut Seksyen 90A(1) dan (6) Akta Keterangan 1950.\n\n"
        "3. Bahawa sepanjang tempoh yang material semasa dokumen-dokumen itu dikeluarkan, komputer dan pencetak "
        "berkenaan berada dalam keadaan pengendalian yang baik dan beroperasi dengan sewajarnya dalam segala hal "
        "yang material menurut Seksyen 90A(4) Akta Keterangan 1950.\n\n"
        "4. Perakuan ini dibuat oleh saya sepanjang pengetahuan dan kepercayaan saya menurut kehendak "
        "Seksyen 90A(2) dan (3)(a) Akta Keterangan 1950 [Akta 56]."
    )
    _add_paragraph_text(doc, klausa, align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_after=14)

    _add_paragraph_text(
        doc,
        "Tandatangan Pegawai Yang Membuat Perakuan: ........................................\n"
        f"Nama Penuh: {nama}\n"
        f"Jawatan: {jawatan}\n"
        f"Pejabat: {pejabat}\n"
        "Tarikh: ........................................",
        size=10,
    )


def _append_kronologi_kes(
    doc: Document, entries: Any, no_kes: str, b114: Dict[str, Any]
) -> None:
    d114 = _safe_dict(b114)
    _add_paragraph_text(doc, "KEMENTERIAN KESIHATAN MALAYSIA", bold=True, size=12, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=1)
    _add_paragraph_text(doc, "KRONOLOGI KES", bold=True, underline=True, size=12, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=6)
    _add_paragraph_text(
        doc,
        f"No. Kertas Siasatan: {_safe_str(no_kes)}   |   Nama OKS: {_safe_str(d114.get('nama_tertuduh'))} ({_safe_str(d114.get('no_kp_tertuduh'))})",
        bold=True,
        size=10,
        space_after=8,
    )

    rows = [
        [
            _safe_str(item.get("tarikh") or item.get("tarikh_masa")),
            _safe_str(item.get("peristiwa") or item.get("peristiwa_tindakan") or item.get("catatan")),
        ]
        for item in _safe_list(entries)
        if isinstance(item, dict)
    ]
    _add_clean_table(doc, ["Tarikh", "Peristiwa / Tindakan Klinikal & Penguatkuasaan"], rows or [["-", "-"]])


def _append_kertas_cadangan_io(
    doc: Document,
    cadangan_text: Any,
    no_kes: str,
    b114: Dict[str, Any],
    s90a: Optional[Dict[str, Any]] = None,
    officer_profile: Optional[Dict[str, Any]] = None,
) -> None:
    d114 = _safe_dict(b114)
    office = _resolve_office_display(d114, s90a, officer_profile)
    prof = _safe_dict(officer_profile)

    _add_paragraph_text(doc, "KEMENTERIAN KESIHATAN MALAYSIA", bold=True, size=12, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=1)
    _add_paragraph_text(doc, "KERTAS CADANGAN PEGAWAI PENYIASAT", bold=True, underline=True, size=12, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=4)
    _add_paragraph_text(doc, f"No. Kertas Siasatan: {_safe_str(no_kes)}", bold=True, size=10, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=10)

    for para in _safe_str(cadangan_text).splitlines():
        if para.strip():
            _add_paragraph_text(doc, para.strip(), align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_after=6)

    _add_paragraph_text(
        doc,
        "\nTandatangan Pegawai Penyiasat (IO):\n"
        "............................................................\n"
        f"({_safe_str(d114.get('pegawai_pengadu') or prof.get('full_name'), 'Pegawai Penyiasat KKM')})\n"
        f"{office['pejabat_rasmi']}\n"
        "Tarikh: ........................................",
        size=10,
        space_before=12,
    )


def _append_saman_111(
    doc: Document,
    saman: Dict[str, Any],
    b114: Dict[str, Any],
    officer_profile: Optional[Dict[str, Any]] = None,
) -> None:
    dsam = _safe_dict(saman)
    d114 = _safe_dict(b114)
    prof = _safe_dict(officer_profile)
    current_year = datetime.now().year

    mahkamah_txt = _safe_str(
        dsam.get("mahkamah") or d114.get("mahkamah") or prof.get("default_magistrate_court"),
        "DALAM MAHKAMAH MAJISTRET",
    )
    jurisdiction_hdr = resolve_saman_jurisdiction_header(
        mahkamah_txt,
        _safe_str(d114.get("negeri"), ""),
        _safe_str(d114.get("daerah"), ""),
        _safe_str(prof.get("state_jkn"), ""),
        _safe_str(prof.get("district_pkd"), ""),
    )

    _add_paragraph_text(doc, "(Mahkamah 111 - Pin. 1/85)", bold=True, size=10, align=WD_ALIGN_PARAGRAPH.RIGHT, space_after=1)
    _add_paragraph_text(doc, jurisdiction_hdr, bold=True, size=10, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=1)
    _add_paragraph_text(doc, "SAMAN KEPADA ORANG KENA SAMAN (OKS)", bold=True, underline=True, size=12, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    _add_paragraph_text(doc, mahkamah_txt, bold=True, size=11, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=8)

    _add_paragraph_text(doc, f"No. Saman / Kes: {_safe_str(dsam.get('no_saman') or dsam.get('no_kes') or d114.get('no_kes'))}", bold=True, space_after=6)
    _add_paragraph_text(
        doc,
        f"Kepada:\n{_safe_str(dsam.get('nama_oks') or dsam.get('kepada_tertuduh') or dsam.get('nama_okt') or d114.get('nama_tertuduh'))}\n"
        f"No. Kad Pengenalan / SSM: {_safe_str(dsam.get('no_kp') or d114.get('no_kp_tertuduh'))}\n"
        f"Alamat: {_safe_str(dsam.get('alamat') or d114.get('alamat_tertuduh'))}",
        space_after=8,
    )
    _add_paragraph_text(
        doc,
        f"BAHAWASANYA aduan telah dibuat kepada saya bahawa kamu telah melakukan kesalahan seperti berikut:\n\n"
        f"\"{_safe_str(dsam.get('teks_pertuduhan') or d114.get('teks_pertuduhan'))}\"\n\n"
        f"Hukuman Diperuntukkan: {_safe_str(dsam.get('hukuman') or d114.get('seksyen_hukuman'))}",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY,
        space_after=10,
    )
    _add_paragraph_text(
        doc,
        f"MAKA OLEH YANG DEMIKIAN, kamu adalah diperintahkan supaya hadir sendiri di hadapan Mahkamah Majistret "
        f"pada {_safe_str(dsam.get('tarikh_hadir'), f'........ haribulan .................... {current_year}')} "
        f"jam {_safe_str(dsam.get('masa_hadir'), '9.00 pagi')} untuk menjawab aduan tersebut dan diperlakukan mengikut undang-undang.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY,
        space_after=16,
    )
    _add_paragraph_text(
        doc,
        f"Bertarikh pada ........ haribulan ...................... {current_year}\n\n"
        "............................................................\n"
        "Majistret / Pendaftar Mahkamah",
        size=10,
        align=WD_ALIGN_PARAGRAPH.RIGHT,
    )


def _append_pemberatan_hukuman(
    doc: Document, points: Any, no_kes: str, b114: Dict[str, Any]
) -> None:
    d114 = _safe_dict(b114)
    _add_paragraph_text(doc, "KEMENTERIAN KESIHATAN MALAYSIA", bold=True, size=12, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=1)
    _add_paragraph_text(doc, "HUJAHAN PEMBERATAN HUKUMAN (PEGAWAI PENDAKWA)", bold=True, underline=True, size=12, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=4)
    _add_paragraph_text(
        doc,
        f"No. Kes: {_safe_str(no_kes)}   |   OKS/OKT: {_safe_str(d114.get('nama_tertuduh'))} ({_safe_str(d114.get('no_kp_tertuduh'))})",
        bold=True,
        size=10,
        align=WD_ALIGN_PARAGRAPH.CENTER,
        space_after=10,
    )
    _add_paragraph_text(
        doc,
        "Dengan izin Yang Arif Majistret, pihak pendakwaan memohon suatu hukuman yang berat dan setimpal dikenakan "
        "terhadap Tertuduh atas faktor-faktor pemberatan hukuman seperti berikut:",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY,
        space_after=8,
    )
    for idx, pt in enumerate(_safe_list(points), start=1):
        _add_paragraph_text(doc, f"{idx}. {_safe_str(pt)}", align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_after=6)


def generate_borang_114_docx(
    payload: Dict[str, Any], officer_profile: Optional[Dict[str, Any]] = None
) -> bytes:
    doc = _configure_base_doc()
    p = _safe_dict(payload)
    b114 = _safe_dict(p.get("borang_114")) or p
    _append_borang_114(doc, b114, officer_profile)
    return _doc_to_bytes(doc)


def generate_diari_siasatan_docx(
    payload: Dict[str, Any], officer_profile: Optional[Dict[str, Any]] = None
) -> bytes:
    doc = _configure_base_doc()
    p = _safe_dict(payload)
    b114 = _safe_dict(p.get("borang_114"))
    s90a = _safe_dict(p.get("sijil_90a"))
    no_kes = _safe_str(b114.get("no_kes"), f"PKD/UIP/{datetime.now().year}/001")
    _append_diari_siasatan(doc, _safe_list(p.get("diari_siasatan")), no_kes, b114, s90a, officer_profile)
    return _doc_to_bytes(doc)


def generate_rakaman_112_docx(
    payload: Dict[str, Any], officer_profile: Optional[Dict[str, Any]] = None
) -> bytes:
    doc = _configure_base_doc()
    p = _safe_dict(payload)
    no_kes = _safe_str(_safe_dict(p.get("borang_114")).get("no_kes"), f"PKD/UIP/{datetime.now().year}/001")
    _append_rakaman_112(doc, p.get("rakaman_112", ""), no_kes)
    return _doc_to_bytes(doc)


def generate_compound_notice_docx(
    payload: Dict[str, Any], officer_profile: Optional[Dict[str, Any]] = None
) -> bytes:
    doc = _configure_base_doc()
    p = _safe_dict(payload)
    kom = _safe_dict(p.get("notis_kompaun")) or p
    prof = _safe_dict(officer_profile)

    pejabat_hdr = _safe_str(kom.get("pejabat_pkd") or prof.get("district_pkd"), "")
    negeri_hdr = _safe_str(kom.get("state_jkn") or prof.get("state_jkn"), "")

    peruntukan = _safe_str(kom.get("peruntukan_undang"), "")
    low_per = peruntukan.lower()
    is_akta_852_notice = bool(
        re.search(r"(?<!\d)852(?!\d)", low_per)
        or any(pu in low_per for pu in ("257/2024", "258/2024", "259/2024", "260/2024", "261/2024", "262/2024", "263/2024", "264/2024"))
        or "produk merokok" in low_per
    )
    if is_akta_852_notice:
        akta_header = "AKTA KAWALAN PRODUK MEROKOK DEMI KESIHATAN AWAM 2024 [AKTA 852]"
        form_subtitle = "TAWARAN UNTUK MENGKOMPAUN KESALAHAN (BORANG 2 JADUAL KEDUA P.U. (A) 259/2024 — SEKSYEN 48(2))"
        peruntukan_kompaun_default = "Seksyen 48(2) Akta 852 [P.U. (A) 259/2024] (dengan keizinan bertulis Pendakwa Raya — Borang 1)"
        bayaran_clause = (
            "TEMPAT & TATACARA BAYARAN (PERATURAN 5(1) P.U. (A) 259/2024): Bayaran kompaun hendaklah dijelaskan dalam tempoh 30 hari "
            f"di Kaunter Unit Hasil {pejabat_hdr or 'mana-mana Pejabat Kesihatan berhampiran'} melalui wang tunai, kad kredit, kad debit, "
            "kad caj, atau pemindahan wang secara elektronik. Tawaran kompaun ini dibuat dengan keizinan bertulis Pendakwa Raya. "
            "Jika gagal dijelaskan dalam tempoh yang ditetapkan, tindakan pendakwaan di Mahkamah Majistret akan dimulakan tanpa notis lanjut."
        )
    elif "154" in low_per:
        akta_header = "AKTA PEMUSNAHAN SERANGGA PEMBAWA PENYAKIT 1975 [AKTA 154]"
        form_subtitle = "NOTIS KESALAHAN & TAWARAN MENGKOMPAUN (SEKSYEN 25 AKTA 154)"
        peruntukan_kompaun_default = "Seksyen 25 Akta 154 (Maksimum RM500.00; tempoh 14 hari)"
        bayaran_clause = (
            f"TEMPAT & TATACARA BAYARAN: Bayaran kompaun hendaklah dijelaskan dalam tempoh 14 hari di Kaunter Unit Hasil "
            f"{pejabat_hdr or 'Pejabat Kesihatan Daerah / Kawasan / Bahagian yang berkenaan'} (tunai / wang pos / kiriman wang / e-Bayaran). "
            "Sekiranya tawaran kompaun ini gagal dijelaskan dalam tempoh tersebut, tindakan pendakwaan di Mahkamah Majistret akan dimulakan tanpa notis lanjut."
        )
    elif "342" in low_per:
        akta_header = "AKTA PENCEGAHAN DAN PENGAWALAN PENYAKIT BERJANGKIT 1988 [AKTA 342] (PINDAAN AKTA A1742)"
        form_subtitle = "NOTIS TAWARAN MENGKOMPAUN KESALAHAN (SEKSYEN 25 AKTA 342 & P.U. (A) 139/2025)"
        peruntukan_kompaun_default = "Seksyen 25 Akta 342 [P.U. (A) 139/2025] (dengan keizinan bertulis Pendakwa Raya)"
        bayaran_clause = (
            f"TEMPAT & TATACARA BAYARAN: Tawaran kompaun ini dikeluarkan dengan keizinan bertulis Pendakwa Raya di bawah Seksyen 25 Akta 342. "
            f"Bayaran hendaklah dijelaskan dalam tempoh 14 hari di Kaunter Unit Hasil {pejabat_hdr or 'Pejabat Kesihatan yang berkenaan'} "
            "(tunai / wang pos / kiriman wang / e-Bayaran). Jika gagal dijelaskan, tindakan pendakwaan akan dimulakan tanpa notis lanjut."
        )
    else:
        akta_header = "AKTA MAKANAN 1983 [AKTA 281] & PERATURAN-PERATURAN KEBERSIHAN MAKANAN 2009"
        form_subtitle = "NOTIS SEKSYEN 32B & TAWARAN MENGKOMPAUN (JADUAL KELIMA PPKM 2009 — SEKSYEN 33 AKTA 281)"
        peruntukan_kompaun_default = "Notis Seksyen 32B & Seksyen 33 Akta Makanan 1983 (dengan keizinan bertulis Pendakwa Raya)"
        bayaran_clause = (
            "TEMPAT & TATACARA BAYARAN (PERATURAN 60(1) PPKM 2009): Tawaran kompaun ini dibuat dengan keizinan bertulis Pendakwa Raya. "
            f"Bayaran hendaklah dijelaskan dalam tempoh 14 hari di Kaunter Unit Hasil {pejabat_hdr or 'Pejabat Kesihatan Daerah / Kawasan / Bahagian yang berkenaan'} "
            "(tunai / kiriman wang / wang pos / pesanan bank atau draf atas nama Pegawai Kesihatan Daerah / Pengarah Kesihatan Negeri). "
            "Jika gagal dijelaskan dalam tempoh 14 hari, tindakan pendakwaan di Mahkamah Majistret akan dimulakan tanpa notis lanjut."
        )

    _add_paragraph_text(doc, "KEMENTERIAN KESIHATAN MALAYSIA", bold=True, size=12, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=1)
    if pejabat_hdr or negeri_hdr:
        _add_paragraph_text(
            doc,
            " — ".join(part for part in (pejabat_hdr.upper(), negeri_hdr.upper()) if part),
            bold=True,
            size=10,
            align=WD_ALIGN_PARAGRAPH.CENTER,
            space_after=1,
        )
    _add_paragraph_text(doc, "UNIT INSPEKTORAT DAN PERUNDANGAN (UIP)", bold=True, size=11, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=1)
    _add_paragraph_text(doc, akta_header, bold=True, size=10, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    _add_paragraph_text(doc, form_subtitle, bold=True, underline=True, size=10, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=10)

    status_serahan = _safe_str(kom.get("status_serahan"), "tandatangan_terima")
    saksi_ppkp = _safe_str(kom.get("saksi_ppkp"))
    pegawai_out = _safe_str(kom.get("pegawai_pengeluar") or prof.get("full_name"))
    kad_out = _safe_str(kom.get("no_kad_kuasa") or prof.get("kkm_authority_card_no"))

    rows = [
        ["No. Siri Notis", _safe_str(kom.get("no_notis"))],
        ["Nama Penerima / OKS", _safe_str(kom.get("nama_penerima"))],
        ["No. K/P / Pasport / SSM", _safe_str(kom.get("no_kp"))],
        ["Nama Premis / Syarikat", _safe_str(kom.get("nama_premis"))],
        ["No. Daftar SSM", _safe_str(kom.get("no_ssm"))],
        ["Alamat Tempat Kejadian", _safe_str(kom.get("alamat_kejadian") or kom.get("alamat_premis"))],
        ["Tarikh & Masa Kejadian", _safe_str(kom.get("tarikh_masa") or f"{kom.get('tarikh_kesalahan', '')} {kom.get('masa_kesalahan', '')}".strip())],
        ["Peruntukan Kesalahan", peruntukan or "-"],
        ["Peruntukan Kompaun", _safe_str(kom.get("peruntukan_kompaun"), peruntukan_kompaun_default)],
        ["Butir-Butir Kesalahan", _safe_str(kom.get("kesalahan_ringkas") or kom.get("ringkasan_kesalahan"))],
        ["Amaun Tawaran Kompaun", _safe_str(kom.get("amaun_kompaun_rm"))],
        ["Tempoh Bayaran", _safe_str(kom.get("tempoh_bayaran") or kom.get("tempoh_bayaran_hari"))],
        ["PPKP Pengeluar Notis", f"{pegawai_out} ({kad_out})"],
    ]
    _add_clean_table(doc, ["Butiran Notis", "Maklumat Rasmi"], rows)
    _add_paragraph_text(
        doc,
        f"\n{bayaran_clause}",
        size=9,
        align=WD_ALIGN_PARAGRAPH.JUSTIFY,
        space_before=8,
        space_after=10,
    )

    _add_paragraph_text(
        doc,
        "1. PENGELUARAN NOTIS (PEGAWAI DIBERI KUASA)\n"
        "Tandatangan PPKP Pengeluar: ........................................     Tarikh & Masa Serahan: ............................\n"
        f"Nama & No. Kad Kuasa: {pegawai_out} ({kad_out})",
        size=10,
        space_after=10,
    )
    _add_paragraph_text(
        doc,
        "2. AKUAN TERIMA PENERIMA / OKS\n"
        f"Status Serahan: {'[X] Serahan Tangan (Tandatangan Terima)   [ ] Enggan Tandatangan' if status_serahan != 'enggan_tandatangan' else '[ ] Serahan Tangan   [X] Enggan Tandatangan (Rujuk Saksi PPKP & Pos Berdaftar AR)'}\n"
        "Tandatangan Penerima / OKS: ........................................     Tarikh Terima: ....................................\n"
        f"Nama Penerima: {_safe_str(kom.get('nama_penerima'))}   |   No. K/P / Pasport / SSM: {_safe_str(kom.get('no_kp'))}",
        size=10,
        space_after=10,
    )
    _add_paragraph_text(
        doc,
        "3. PENGESAHAN SAKSI PPKP (WAJIB JIKA OKS ENGGAN TANDATANGAN)\n"
        "Tandatangan Saksi PPKP: ............................................     Tarikh: ...........................................\n"
        f"Nama Saksi Pengiring: {saksi_ppkp}   |   No. Resit Pos Berdaftar AR (jika dipos): ............................",
        size=10,
        space_after=6,
    )
    return _doc_to_bytes(doc)


def generate_full_ip_package_docx(
    payload: Dict[str, Any], officer_profile: Optional[Dict[str, Any]] = None
) -> bytes:
    """Menjana Pakej IP Lengkap mengikut susunan rasmi fail Kertas Siasatan UIP KKM (Bahagian A-G)."""
    doc = _configure_base_doc()
    p = _safe_dict(payload)
    b114 = _safe_dict(p.get("borang_114"))
    s90a = _safe_dict(p.get("sijil_90a"))
    no_kes = _safe_str(b114.get("no_kes"), f"PKD/UIP/{datetime.now().year}/001")

    # 1. Kulit IP & Indeks Kandungan Fail (7 Bahagian A-G)
    _append_kulit_dan_indeks_ip(doc, p, officer_profile)
    doc.add_page_break()

    # 2. Kertas Minit (Am 6) & Izin Mendakwa TPR
    if p.get("minit_ip"):
        _append_minit_ip(doc, p["minit_ip"], no_kes)
    if p.get("izin_mendakwa"):
        _add_paragraph_text(doc, "", space_after=8)
        _append_izin_mendakwa(doc, p["izin_mendakwa"])
    doc.add_page_break()

    # 2B. Kronologi Kes & Kertas Cadangan Pegawai Penyiasat (IO)
    if p.get("kronologi_kes"):
        _append_kronologi_kes(doc, p["kronologi_kes"], no_kes, b114)
        doc.add_page_break()
    if p.get("kertas_cadangan_io"):
        _append_kertas_cadangan_io(doc, p["kertas_cadangan_io"], no_kes, b114, s90a, officer_profile)
        doc.add_page_break()

    # 3. Pengaduan Majistret (Borang 143), Saman (Mahkamah 111) & Kertas Pertuduhan (Borang 114)
    if p.get("borang_143"):
        _append_borang_143(doc, p["borang_143"])
        doc.add_page_break()
    if p.get("saman_111"):
        _append_saman_111(doc, p["saman_111"], b114, officer_profile)
        doc.add_page_break()
    _append_borang_114(doc, b114, officer_profile)
    for extra_b114 in _safe_list(p.get("borang_114_tambahan")):
        if isinstance(extra_b114, dict):
            doc.add_page_break()
            _append_borang_114(doc, {**b114, **extra_b114}, officer_profile)
    doc.add_page_break()

    # 4. Fakta Kes, Senarai Saksi & Senarai Barang Kes (Eksibit)
    _add_paragraph_text(doc, "KEMENTERIAN KESIHATAN MALAYSIA — UNIT INSPEKTORAT DAN PERUNDANGAN", bold=True, size=11, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    _add_paragraph_text(doc, f"FAKTA KES, SENARAI SAKSI & BARANG KES ({no_kes})", bold=True, underline=True, size=11, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=10)

    _add_paragraph_text(doc, "FAKTA KES", bold=True, underline=True, size=11, space_after=4)
    _add_paragraph_text(doc, _safe_str(p.get("fakta_kes")), align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_after=10)

    _add_paragraph_text(doc, "SENARAI SAKSI PENDAKWAAN", bold=True, underline=True, size=11, space_after=4)
    saksi_rows = [
        [
            _safe_str(s.get("bil")),
            _safe_str(s.get("nama")),
            _safe_str(s.get("no_kp")),
            _safe_str(s.get("jawatan_peranan")),
            _safe_str(s.get("alamat_hubungan")),
        ]
        for s in _safe_list(p.get("senarai_saksi"))
        if isinstance(s, dict)
    ]
    _add_clean_table(doc, ["Bil.", "Nama Saksi", "No. K/P / Kad Kuasa", "Jawatan / Peranan", "Alamat / Pejabat"], saksi_rows or [["SP1", "-", "-", "-", "-"]])

    _add_paragraph_text(doc, "SENARAI BARANG KES (EKSIBIT)", bold=True, underline=True, size=11, space_before=10, space_after=4)
    ex_rows = [
        [
            _safe_str(e.get("tanda")),
            _safe_str(e.get("perihal")),
            _safe_str(e.get("no_lak_seal")),
            _safe_str(e.get("lokasi_simpanan")),
        ]
        for e in _safe_list(p.get("senarai_eksibit"))
        if isinstance(e, dict)
    ]
    _add_clean_table(doc, ["Tanda", "Perihal Barang Kes", "No. Lak (Seal)", "Tempat Simpanan"], ex_rows or [["P1", "-", "-", "-"]])
    doc.add_page_break()

    # 5. Sijil Seksyen 90A(2) & (3)(a) Akta Keterangan 1950
    _append_sijil_90a(doc, s90a, no_kes, officer_profile)
    doc.add_page_break()

    # 6. Rakaman Percakapan Seksyen 112 KTJ
    if p.get("rakaman_112"):
        _append_rakaman_112(doc, p["rakaman_112"], no_kes)
        doc.add_page_break()

    # 7. Diari Siasatan (Seksyen 119 KTJ)
    _append_diari_siasatan(doc, _safe_list(p.get("diari_siasatan")), no_kes, b114, s90a, officer_profile)

    # 8. Hujahan Pemberatan Hukuman Pegawai Pendakwa (Folio Berasingan daripada Diari Siasatan)
    if p.get("pemberatan_hukuman"):
        doc.add_page_break()
        _append_pemberatan_hukuman(doc, _safe_list(p["pemberatan_hukuman"]), no_kes, b114)

    return _doc_to_bytes(doc)


def generate_docx_by_type(
    doc_type: str,
    payload: Dict[str, Any],
    officer_profile: Optional[Dict[str, Any]] = None,
) -> tuple[bytes, str]:
    normalized = str(doc_type or "").strip().lower()
    p = _safe_dict(payload)
    if not officer_profile and isinstance(p.get("officer_profile"), dict):
        officer_profile = p.get("officer_profile")
    b114 = _safe_dict(p.get("borang_114"))
    case_slug = _slug_for_filename(b114.get("no_kes") or p.get("no_kes"))
    suffix = f"_{case_slug}" if case_slug else ""

    if normalized == "borang_114":
        return generate_borang_114_docx(p, officer_profile), f"Borang_114_Pertuduhan{suffix}.docx"
    if normalized == "saman_111":
        doc = _configure_base_doc()
        _append_saman_111(doc, _safe_dict(p.get("saman_111")) or b114, b114, officer_profile)
        return _doc_to_bytes(doc), f"Saman_Mahkamah_111{suffix}.docx"
    if normalized == "diari_siasatan":
        return generate_diari_siasatan_docx(p, officer_profile), f"Diari_Siasatan_S119_KTJ{suffix}.docx"
    if normalized == "rakaman_112":
        return generate_rakaman_112_docx(p, officer_profile), f"Rakaman_Percakapan_S112_KTJ{suffix}.docx"
    if normalized == "notis_kompaun":
        kom = _safe_dict(p.get("notis_kompaun")) or p
        notis_slug = _slug_for_filename(kom.get("no_notis"))
        n_suf = f"_{notis_slug}" if notis_slug else ""
        return generate_compound_notice_docx(p, officer_profile), f"Notis_Kompaun_KKM{n_suf}.docx"
    return generate_full_ip_package_docx(p, officer_profile), f"Pakej_Kertas_Siasatan_UIP{suffix}.docx"
