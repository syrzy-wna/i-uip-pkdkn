"""Penjana Dokumen Rasmi .docx KKM & Mahkamah Majistret (python-docx).

Menghasilkan dokumen mengikut format sebenar amalan Mahkamah Majistret & UIP KKM:
1. Borang Mahkamah 114 (Kertas Pertuduhan Rasmi KTJ — tanpa jadual biru kolej!)
2. Borang Mahkamah 143 (Pengaduan kepada Majistret — Seksyen 128 KTJ)
3. Diari Siasatan (Seksyen 119 KTJ)
4. Rakaman Percakapan Seksyen 112 KTJ (dengan Butiran Saksi, Amaran S.112(4), Soal-Jawab, Perakuan S.112(5) & 4 Tandatangan)
5. Sijil Seksyen 90A(2) Akta Keterangan 1950 (lengkap jadual peranti & klausa 'sepanjang pengetahuan dan kepercayaan saya')
6. Pakej Kertas Siasatan Lengkap (Kulit IP, Indeks A-G, Kertas Minit 1-4, Izin Mendakwa TPR, Borang 143, Borang 114, Fakta Kes, Saksi, Eksibit, Sijil 90A, Rakaman S.112, DS)
7. Notis Kompaun Lapangan / Notis Seksyen 32B / Seksyen 47
"""

from __future__ import annotations

import io
from datetime import datetime
from typing import Any, Dict, List

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


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
    text: str,
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
    run = p.add_run(text)
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
    rows: List[List[str]],
    header_fill: str = "E2E8F0",
) -> None:
    """Jadual rasmi KKM (latar kelabu cair profesional, tulisan hitam)."""
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    hdr_cells = table.rows[0].cells
    for i, header in enumerate(headers):
        hdr_cells[i].text = header
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
            row_cells[i].text = str(val or "-")
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


def _append_kulit_dan_indeks_ip(doc: Document, payload: Dict[str, Any]) -> None:
    b114 = payload.get("borang_114", {})
    no_kes = b114.get("no_kes", "PKD/UIP/2026/001")
    daerah = b114.get("daerah", "-")
    akta = payload.get("akta_utama", "-")

    _add_paragraph_text(doc, "SULIT (UNTUK KEGUNAAN RASMI UIP KKM SAHAJA)", bold=True, size=10, align=WD_ALIGN_PARAGRAPH.RIGHT, space_after=6)
    _add_paragraph_text(doc, "KEMENTERIAN KESIHATAN MALAYSIA", bold=True, size=13, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    _add_paragraph_text(doc, "UNIT INSPEKTORAT DAN PERUNDANGAN (UIP)", bold=True, size=12, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    _add_paragraph_text(doc, "KULIT KERTAS SIASATAN (IP)", bold=True, underline=True, size=12, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=10)

    kulit_rows = [
        ["No. Kertas Siasatan (IP)", no_kes],
        ["Pejabat Kesihatan Daerah / Negeri", f"PKD {daerah} / {b114.get('negeri', '')}"],
        ["Akta & Seksyen Kesalahan", f"{akta} — {b114.get('akta_dan_seksyen', '-')}"],
        ["Seksyen Hukuman", b114.get("seksyen_hukuman", "-")],
        ["Nama OKS / OKT", b114.get("nama_tertuduh", "-")],
        ["No. Kad Pengenalan", b114.get("no_kp_tertuduh", "-")],
        ["Tarikh & Masa Kejadian", f"{b114.get('tarikh_kejadian', '-')} / {b114.get('masa_kejadian', '-')}"],
        ["Alamat Tempat Kejadian", b114.get("tempat_kejadian", "-")],
        ["Pegawai Penyiasat (IO)", b114.get("pegawai_pengadu", "-")],
    ]
    _add_clean_table(doc, ["Perkara Kulit IP", "Butiran Kes"], kulit_rows)

    _add_paragraph_text(doc, "INDEKS KANDUNGAN FAIL KERTAS SIASATAN", bold=True, underline=True, size=11, space_before=12, space_after=6)
    indeks_rows = [
        ["A", "Kertas Minit Siasatan (Minit 1 hingga Minit 4) & Surat Izin Mendakwa TPR", "Lampiran A"],
        ["B", "Pengaduan kepada Majistret (Borang 143) & Kertas Pertuduhan (Borang 114)", "Lampiran B"],
        ["C", "Fakta Kes, Senarai Saksi Pendakwaan (SP) & Senarai Barang Kes (P)", "Lampiran C"],
        ["D", "Notis S.32B / S.47, Tawaran Kompaun, Pengesahan Belum Bayar & Kad AR", "Lampiran D"],
        ["E", "Borang Sitaan (S.36) / Perintah S.11, Pelan Lakar, Gambar & Sijil Seksyen 90A(2)", "Lampiran E"],
        ["F", "Rakaman Percakapan Seksyen 112 KTJ (Saksi & OKT)", "Lampiran F"],
        ["G", "Cetakan Carian SSM, Salinan Kad Kuasa & Laporan Makmal/Entomologi", "Lampiran G"],
        ["H", "Diari Siasatan (Seksyen 119 KTJ)", "Lampiran H"],
    ]
    _add_clean_table(doc, ["Bahagian", "Perihal Kandungan Fail IP", "Folio"], indeks_rows)


def _append_minit_ip(doc: Document, minit_list: Any, no_kes: str) -> None:
    _add_paragraph_text(doc, "(Am 6)", bold=True, size=10, align=WD_ALIGN_PARAGRAPH.RIGHT, space_after=1)
    _add_paragraph_text(doc, "KERTAS MINIT KERTAS SIASATAN", bold=True, size=12, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    _add_paragraph_text(doc, f"No. Kertas Siasatan: {no_kes}", bold=True, size=11, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=10)

    if isinstance(minit_list, str):
        _add_paragraph_text(doc, minit_list, size=11, space_after=8)
    else:
        rows = []
        for idx, item in enumerate(minit_list or [], start=1):
            if isinstance(item, dict):
                rows.append([
                    item.get("bil") or item.get("no_minit") or f"Minit {idx}",
                    item.get("tarikh", "-"),
                    f"Daripada: {item.get('daripada', '-')}\nKepada: {item.get('kepada', '-')}",
                    item.get("kandungan") or item.get("butiran") or item.get("catatan", "-"),
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
    if not izin:
        return
    _add_paragraph_text(doc, "PERMOHONAN IZIN MENDakwa (SANKSIPENDAKWA RAYA)", bold=True, size=12, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    _add_paragraph_text(doc, f"({izin.get('peruntukan_izin', 'Seksyen 376(3) Kanun Tatacara Jenayah')})", bold=True, size=10, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=10)

    _add_paragraph_text(doc, f"Kepada: {izin.get('kepada', 'Timbalan Pendakwa Raya')}", bold=True, space_after=4)
    _add_paragraph_text(doc, f"No. Rujukan Kertas Siasatan: {izin.get('rujukan_ip', '-')}", space_after=6)
    _add_paragraph_text(
        doc,
        f"Adalah dengan hormatnya dikemukakan Kertas Siasatan di atas terhadap {izin.get('nama_okt', '-')} "
        f"bagi kesalahan di bawah {izin.get('seksyen_dipohon', '-')} untuk pertimbangan dan keizinan bertulis "
        "Pihak Yang Arif Timbalan Pendakwa Raya bagi memulakan pendakwaan di Mahkamah Majistret.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY,
        space_after=18,
    )
    _add_paragraph_text(doc, "[   ] DIIZINKAN MENDAKWA        [   ] TIDAK DIIZINKAN / KEMBALIKAN UNTUK SIASATAN LANJUT", bold=True, space_after=18)
    _add_paragraph_text(
        doc,
        "............................................................\n"
        "Timbalan Pendakwa Raya\n"
        "Tarikh: ........................................",
        space_after=8,
    )


def _append_borang_143(doc: Document, b143: Dict[str, Any]) -> None:
    if not b143:
        return
    _add_paragraph_text(doc, "(Mahkamah 143)", bold=True, size=10, align=WD_ALIGN_PARAGRAPH.RIGHT, space_after=2)
    _add_paragraph_text(doc, "(Seksyen 128 Kanun Tatacara Jenayah)", italic=True, size=10, align=WD_ALIGN_PARAGRAPH.RIGHT, space_after=6)
    _add_paragraph_text(doc, "PENGADUAN KEPADA MAJISTRET", bold=True, underline=True, size=12, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    _add_paragraph_text(doc, b143.get("mahkamah", "DALAM MAHKAMAH MAJISTRET"), bold=True, size=11, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=10)

    _add_paragraph_text(
        doc,
        f"Saya, {b143.get('pengadu', '-')}, dengan ini mengadu kepada Majistret bahawa "
        f"{b143.get('oks_nama', '-')} (No. K/P: {b143.get('oks_kp', '-')}) yang beralamat di "
        f"{b143.get('oks_alamat', '-')} telah melakukan kesalahan seperti berikut:-",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY,
        space_after=8,
    )
    _add_paragraph_text(doc, b143.get("butiran_aduan", "-"), align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_after=14)
    _add_paragraph_text(
        doc,
        "Tandatangan Pengadu: ........................................     Diambil di hadapan saya,\n"
        "Jawatan: Pegawai Diberi Kuasa KKM                                 ......................................................\n"
        "Tarikh: ........................................                  Majistret",
        size=10,
    )


def _append_borang_114(doc: Document, b114: Dict[str, Any]) -> None:
    """Format tulen Borang Mahkamah 114 (Jadual Kedua KTJ - tanpa jadual biru kolej)."""
    current_year = datetime.now().year
    _add_paragraph_text(doc, "(Mahkamah 114)", bold=True, size=10, align=WD_ALIGN_PARAGRAPH.RIGHT, space_after=1)
    _add_paragraph_text(doc, "(Kanun Tatacara Jenayah — Seksyen 152, 153 & 154)", italic=True, size=9, align=WD_ALIGN_PARAGRAPH.RIGHT, space_after=6)

    _add_paragraph_text(doc, b114.get("mahkamah", "DALAM MAHKAMAH MAJISTRET"), bold=True, size=12, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=1)
    _add_paragraph_text(doc, b114.get("negeri", "DALAM NEGERI SELANGOR, MALAYSIA"), bold=True, size=11, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=1)
    _add_paragraph_text(doc, f"KES SAMAN NO: {b114.get('no_kes', f'.................... TAHUN {current_year}')}", bold=True, size=11, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=10)

    _add_paragraph_text(doc, "PENDAKWA RAYA", bold=True, size=11, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    _add_paragraph_text(doc, "LAWAN", bold=True, size=10, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    _add_paragraph_text(doc, f"{b114.get('nama_tertuduh', '-')}", bold=True, size=11, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=10)

    # Blok butiran OKS (teks tersusun bersih, tiada latar warna biru)
    butiran_oks = (
        f"Nama OKS / Tertuduh   : {b114.get('nama_tertuduh', '-')}\n"
        f"No. Kad Pengenalan    : {b114.get('no_kp_tertuduh', '-')}\n"
        f"Umur / Jantina        : {b114.get('umur_jantina', '-')}\n"
        f"Pekerjaan / Jawatan   : {b114.get('pekerjaan', '-')}\n"
        f"Alamat Terkini        : {b114.get('alamat_tertuduh', '-')}"
    )
    _add_paragraph_text(doc, butiran_oks, size=10, space_after=10)

    _add_paragraph_text(
        doc,
        f"adalah dipertuduh atas pengaduan {b114.get('pegawai_pengadu', 'Pegawai Pendakwa KKM')} "
        "bagi pihak Pendakwa Raya seperti berikut:-",
        italic=True,
        size=11,
        space_after=8,
    )

    _add_paragraph_text(doc, "PERTUDUHAN", bold=True, underline=True, size=11, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=6)
    pertuduhan_txt = b114.get("teks_pertuduhan", "-")
    _add_paragraph_text(doc, pertuduhan_txt, size=11, align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_after=10)

    _add_paragraph_text(
        doc,
        f"Seksyen Kesalahan : {b114.get('akta_dan_seksyen', '-')}\n"
        f"Seksyen Hukuman   : {b114.get('seksyen_hukuman', '-')}\n"
        f"Hukuman Maksimum  : {b114.get('hukuman_maksimum', '-')}",
        bold=True,
        size=10,
        space_after=16,
    )

    _add_paragraph_text(
        doc,
        f"Bertarikh pada ........ haribulan ...................... {current_year}\n\n\n"
        "............................................................          ............................................................\n"
        "Timbalan Pendakwa Raya / Pegawai Pendakwa                          Majistret\n"
        "Kementerian Kesihatan Malaysia                                     Mahkamah Majistret",
        size=10,
    )


def _append_diari_siasatan(doc: Document, entries: List[Dict[str, str]], no_kes: str, b114: Dict[str, Any]) -> None:
    _add_paragraph_text(doc, "KEMENTERIAN KESIHATAN MALAYSIA", bold=True, size=12, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=1)
    _add_paragraph_text(doc, "DIARI SIASATAN (SEKSYEN 119 KANUN TATACARA JENAYAH)", bold=True, underline=True, size=11, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=8)

    nama_io = b114.get("pegawai_pengadu", "-")
    daerah = b114.get("daerah", "-")
    negeri = b114.get("negeri", "")
    nama_oks = b114.get("nama_tertuduh", "-")
    no_kp_oks = b114.get("no_kp_tertuduh", "-")

    meta_rows = [
        ["Nama Pegawai", nama_io, "No. Kes / IP", no_kes],
        ["Jawatan", "PPKP / Pegawai Penyiasat (IO)", "Seksyen", b114.get("akta_dan_seksyen", "-")],
        ["Pejabat", f"PKD {daerah}, {negeri}".strip(", "), "Nama OKS/OKT", f"{nama_oks} (No. K/P: {no_kp_oks})"],
    ]
    _add_clean_table(doc, ["Perkara", "Butiran Pegawai", "Rujukan", "Butiran Kes"], meta_rows)
    _add_paragraph_text(doc, "", space_after=4)

    rows = []
    for i, e in enumerate(entries):
        tarikh_val = e.get("tarikh") or e.get("tarikh_masa", "-")
        masa_val = e.get("masa") or ""
        tarikh_masa = f"{tarikh_val}\n({masa_val})".strip() if masa_val and masa_val != "-" else str(tarikh_val)
        butiran = str(e.get("butiran_tindakan", "-"))
        rows.append([
            e.get("bil", str(i + 1)),
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
        f"Pejabat Kesihatan Daerah {daerah}    |    Tarikh: ....................",
        size=10,
        space_before=12,
    )


def _append_rakaman_112(doc: Document, rakaman_112: str, no_kes: str) -> None:
    _add_paragraph_text(doc, "PERCAKAPAN DI BAWAH SEKSYEN 112 KANUN TATACARA JENAYAH [AKTA 593]", bold=True, underline=True, size=11, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    _add_paragraph_text(doc, f"No. Kertas Siasatan: {no_kes}", bold=True, size=10, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=10)

    _add_paragraph_text(doc, rakaman_112 or "-", size=10, align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_after=12)

    _add_paragraph_text(
        doc,
        "PERAKUAN PENUTUP DI BAWAH SEKSYEN 112(5) KANUN TATACARA JENAYAH:\n"
        "\"Percakapan di atas telah dibaca semula kepada saya dalam Bahasa Melayu dan saya mengakui "
        "ianya adalah benar dan betul tanpa sebarang pindaan.\"",
        bold=True,
        size=10,
        space_after=14,
    )

    _add_paragraph_text(
        doc,
        ".................................................          .................................................\n"
        "Tandatangan Orang Yang Diperiksa                            Tandatangan Pegawai Perakam (IO)\n\n"
        ".................................................          .................................................\n"
        "Tandatangan Jurubahasa (jika ada)                          Tarikh & Masa Tamat Rakaman",
        size=10,
    )


def _append_sijil_90a(doc: Document, s90a: Dict[str, Any], no_kes: str) -> None:
    _add_paragraph_text(doc, "SIJIL PERAKUAN DI BAWAH SEKSYEN 90A(2) AKTA KETERANGAN 1950 [AKTA 56]", bold=True, underline=True, size=11, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    _add_paragraph_text(doc, f"NO. KERTAS SIASATAN: {no_kes}", bold=True, size=10, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=10)

    nama = s90a.get("nama_pegawai", "........................................")
    jawatan = s90a.get("jawatan", "Penolong Pegawai Kesihatan Persekitaran (PPKP)")
    pejabat = s90a.get("pejabat_pkd", "Pejabat Kesihatan Daerah")

    _add_paragraph_text(
        doc,
        f"Saya, {nama}, yang memegang jawatan sebagai {jawatan} di {pejabat}, Kementerian Kesihatan Malaysia, "
        "dengan ini memperakukan seperti berikut:-",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY,
        space_after=8,
    )

    hw_rows = [
        ["Peranti Pengambil Gambar / Kamera", s90a.get("peranti_kamera", "Kamera Digital Rasmi / Telefon Penguatkuasaan PKD")],
        ["Komputer Pemproses", s90a.get("perihal_komputer", "Komputer Meja Rasmi Pejabat PKD")],
        ["Pencetak (Printer)", s90a.get("perihal_pencetak", "Pencetak Laser Pejabat PKD")],
        ["Dokumen / Eksibit Digital Dicetak", s90a.get("senarai_dokumen_digital", "-")],
    ]
    _add_clean_table(doc, ["Butiran Perkakasan & Eksibit Digital", "Spesifikasi Rasmi"], hw_rows)

    klausa = (
        "\n1. Bahawa saya ialah orang yang bertanggungjawab bagi pengendalian komputer dan pengurusan "
        "aktiviti yang berkaitan dengan pengendalian komputer tersebut yang dinyatakan dalam jadual di atas.\n\n"
        "2. Bahawa dokumen-dokumen dan cetakan gambar digital tersebut telah dikeluarkan oleh komputer "
        "berkenaan dalam perjalanan penggunaannya yang biasa menurut Seksyen 90A(1) & (6) Akta Keterangan 1950.\n\n"
        "3. Bahawa sepanjang tempoh yang material semasa dokumen-dokumen itu dikeluarkan, komputer dan pencetak "
        "berkenaan berada dalam keadaan pengendalian yang baik dan beroperasi dengan sewajarnya dalam segala hal "
        "yang material menurut Seksyen 90A(4) Akta Keterangan 1950.\n\n"
        "4. Perakuan ini dibuat oleh saya sepanjang pengetahuan dan kepercayaan saya menurut kehendak "
        "Seksyen 90A(2) Akta Keterangan 1950 [Akta 56]."
    )
    _add_paragraph_text(doc, klausa, align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_after=14)

    _add_paragraph_text(
        doc,
        "Tandatangan Pegawai Memperaku: ........................................\n"
        f"Nama Penuh: {nama}\n"
        f"Jawatan: {jawatan}\n"
        f"Pejabat: {pejabat}\n"
        "Tarikh: ........................................",
        size=10,
    )


def _append_kronologi_kes(
    doc: Document, entries: List[Dict[str, str]], no_kes: str, b114: Dict[str, Any]
) -> None:
    _add_paragraph_text(doc, "KEMENTERIAN KESIHATAN MALAYSIA", bold=True, size=12, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=1)
    _add_paragraph_text(doc, "KRONOLOGI KES", bold=True, underline=True, size=12, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=6)
    _add_paragraph_text(
        doc,
        f"No. Kertas Siasatan: {no_kes}   |   Nama OKS: {b114.get('nama_tertuduh', '-')} ({b114.get('no_kp_tertuduh', '-')})",
        bold=True,
        size=10,
        space_after=8,
    )

    rows = [
        [
            str(item.get("tarikh") or item.get("tarikh_masa") or "-"),
            str(item.get("peristiwa") or item.get("peristiwa_tindakan") or item.get("catatan") or "-"),
        ]
        for item in (entries or [])
        if isinstance(item, dict)
    ]
    _add_clean_table(doc, ["Tarikh", "Peristiwa / Tindakan Klinikal & Penguatkuasaan"], rows or [["-", "-"]])


def _append_kertas_cadangan_io(
    doc: Document, cadangan_text: str, no_kes: str, b114: Dict[str, Any]
) -> None:
    _add_paragraph_text(doc, "KEMENTERIAN KESIHATAN MALAYSIA", bold=True, size=12, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=1)
    _add_paragraph_text(doc, "KERTAS CADANGAN PEGAWAI PENYIASAT", bold=True, underline=True, size=12, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=4)
    _add_paragraph_text(doc, f"No. Kertas Siasatan: {no_kes}", bold=True, size=10, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=10)

    for para in str(cadangan_text or "-").splitlines():
        if para.strip():
            _add_paragraph_text(doc, para.strip(), align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_after=6)

    _add_paragraph_text(
        doc,
        "\nTandatangan Pegawai Penyiasat (IO):\n"
        "............................................................\n"
        f"({b114.get('pegawai_pengadu', 'Pegawai Penyiasat KKM')})\n"
        f"Pejabat Kesihatan Daerah {b114.get('daerah', '-')}\n"
        "Tarikh: ........................................",
        size=10,
        space_before=12,
    )


def _append_saman_111(doc: Document, saman: Dict[str, Any], b114: Dict[str, Any]) -> None:
    _add_paragraph_text(doc, "(Mahkamah 111 - Pin. 1/85)", bold=True, size=10, align=WD_ALIGN_PARAGRAPH.RIGHT, space_after=1)
    _add_paragraph_text(doc, "NEGERI-NEGERI TANAH MELAYU", bold=True, size=10, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=1)
    _add_paragraph_text(doc, "SAMAN KEPADA ORANG KENA SAMAN (OKS)", bold=True, underline=True, size=12, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    _add_paragraph_text(doc, saman.get("mahkamah", b114.get("mahkamah", "DALAM MAHKAMAH MAJISTRET")), bold=True, size=11, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=8)

    _add_paragraph_text(doc, f"No. Saman / Kes: {saman.get('no_saman') or saman.get('no_kes') or b114.get('no_kes', '-')}", bold=True, space_after=6)
    _add_paragraph_text(
        doc,
        f"Kepada:\n{saman.get('nama_oks') or saman.get('kepada_tertuduh') or saman.get('nama_okt') or b114.get('nama_tertuduh', '-')}\n"
        f"No. Kad Pengenalan: {saman.get('no_kp') or b114.get('no_kp_tertuduh', '-')}\n"
        f"Alamat: {saman.get('alamat') or b114.get('alamat_tertuduh', '-')}",
        space_after=8,
    )
    _add_paragraph_text(
        doc,
        f"BAHAWASANYA aduan telah dibuat kepada saya bahawa kamu telah melakukan kesalahan seperti berikut:\n\n"
        f"\"{saman.get('teks_pertuduhan', b114.get('teks_pertuduhan', '-'))}\"\n\n"
        f"Hukuman Diperuntukkan: {saman.get('hukuman', b114.get('seksyen_hukuman', '-'))}",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY,
        space_after=10,
    )
    _add_paragraph_text(
        doc,
        f"MAKA OLEH YANG DEMIKIAN, kamu adalah diperintahkan supaya hadir sendiri di hadapan Mahkamah Majistret "
        f"pada {saman.get('tarikh_hadir', '........ haribulan .................... 2026')} "
        f"jam {saman.get('masa_hadir', '9.00 pagi')} untuk menjawab aduan tersebut dan diperlakukan mengikut undang-undang.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY,
        space_after=16,
    )
    _add_paragraph_text(
        doc,
        "Bertarikh pada ........ haribulan ...................... 2026\n\n"
        "............................................................\n"
        "Majistret / Pendaftar Mahkamah",
        size=10,
        align=WD_ALIGN_PARAGRAPH.RIGHT,
    )


def _append_pemberatan_hukuman(
    doc: Document, points: List[str], no_kes: str, b114: Dict[str, Any]
) -> None:
    _add_paragraph_text(doc, "KEMENTERIAN KESIHATAN MALAYSIA", bold=True, size=12, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=1)
    _add_paragraph_text(doc, "HUJAHAN PEMBERATAN HUKUMAN (PEGAWAI PENDAKWA)", bold=True, underline=True, size=12, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=4)
    _add_paragraph_text(
        doc,
        f"No. Kes: {no_kes}   |   OKS/OKT: {b114.get('nama_tertuduh', '-')} ({b114.get('no_kp_tertuduh', '-')})",
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
    for idx, pt in enumerate(points or [], start=1):
        _add_paragraph_text(doc, f"{idx}. {pt}", align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_after=6)


def generate_borang_114_docx(payload: Dict[str, Any]) -> bytes:
    doc = _configure_base_doc()
    b114 = payload.get("borang_114", payload)
    _append_borang_114(doc, b114)
    return _doc_to_bytes(doc)


def generate_diari_siasatan_docx(payload: Dict[str, Any]) -> bytes:
    doc = _configure_base_doc()
    b114 = payload.get("borang_114", {})
    no_kes = b114.get("no_kes", "PKD/UIP/2026/001")
    _append_diari_siasatan(doc, payload.get("diari_siasatan", []), no_kes, b114)
    return _doc_to_bytes(doc)


def generate_rakaman_112_docx(payload: Dict[str, Any]) -> bytes:
    doc = _configure_base_doc()
    no_kes = payload.get("borang_114", {}).get("no_kes", "PKD/UIP/2026/001")
    _append_rakaman_112(doc, payload.get("rakaman_112", ""), no_kes)
    return _doc_to_bytes(doc)


def generate_compound_notice_docx(payload: Dict[str, Any]) -> bytes:
    doc = _configure_base_doc()
    kom = payload.get("notis_kompaun", payload)
    _add_paragraph_text(doc, "KEMENTERIAN KESIHATAN MALAYSIA", bold=True, size=12, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=1)
    _add_paragraph_text(doc, "UNIT INSPEKTORAT DAN PERUNDANGAN (UIP)", bold=True, size=11, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=1)
    _add_paragraph_text(doc, "NOTIS KESALAHAN & TAWARAN MENGKOMPAUN", bold=True, underline=True, size=11, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=10)

    rows = [
        ["No. Notis", kom.get("no_notis", "-")],
        ["Nama Penerima / OKT", kom.get("nama_penerima", "-")],
        ["No. Kad Pengenalan", kom.get("no_kp", "-")],
        ["Nama Premis / Syarikat", kom.get("nama_premis", "-")],
        ["No. Daftar SSM", kom.get("no_ssm", "-")],
        ["Alamat Tempat Kejadian", kom.get("alamat_kejadian", "-")],
        ["Tarikh & Masa Kejadian", kom.get("tarikh_masa", "-")],
        ["Peruntukan Kesalahan", kom.get("peruntukan_undang", "-")],
        ["Peruntukan Kompaun", kom.get("peruntukan_kompaun", "-")],
        ["Butir-Butir Kesalahan", kom.get("kesalahan_ringkas", "-")],
        ["Amaun Tawaran Kompaun", kom.get("amaun_kompaun_rm", "-")],
        ["Tempoh Bayaran", kom.get("tempoh_bayaran", "-")],
        ["PPKP Pengeluar Notis", f"{kom.get('pegawai_pengeluar', '-')} ({kom.get('no_kad_kuasa', '-')})"],
    ]
    _add_clean_table(doc, ["Medan Notis", "Maklumat Rasmi"], rows)
    _add_paragraph_text(
        doc,
        "\nPERINGATAN: Sekiranya tawaran kompaun ini gagal dijelaskan dalam tempoh yang ditetapkan, "
        "tindakan pendakwaan di Mahkamah Majistret akan dimulakan tanpa notis lanjut.",
        size=10,
        space_before=10,
    )
    return _doc_to_bytes(doc)


def generate_full_ip_package_docx(payload: Dict[str, Any]) -> bytes:
    """Menjana Pakej IP Lengkap mengikut susunan rasmi fail Kertas Siasatan UIP KKM."""
    doc = _configure_base_doc()
    b114 = payload.get("borang_114", {})
    no_kes = b114.get("no_kes", "PKD/UIP/2026/001")

    # 1. Kulit IP & Indeks Kandungan Fail (A-H)
    _append_kulit_dan_indeks_ip(doc, payload)
    doc.add_page_break()

    # 2. Kertas Minit (Am 6) & Izin Mendakwa TPR
    if payload.get("minit_ip"):
        _append_minit_ip(doc, payload["minit_ip"], no_kes)
    if payload.get("izin_mendakwa"):
        _add_paragraph_text(doc, "", space_after=8)
        _append_izin_mendakwa(doc, payload["izin_mendakwa"])
    doc.add_page_break()

    # 2B. Kronologi Kes & Kertas Cadangan Pegawai Penyiasat (IO)
    if payload.get("kronologi_kes"):
        _append_kronologi_kes(doc, payload["kronologi_kes"], no_kes, b114)
        doc.add_page_break()
    if payload.get("kertas_cadangan_io"):
        _append_kertas_cadangan_io(doc, payload["kertas_cadangan_io"], no_kes, b114)
        doc.add_page_break()

    # 3. Pengaduan Majistret (Borang 143), Saman (Mahkamah 111) & Kertas Pertuduhan (Borang 114)
    if payload.get("borang_143"):
        _append_borang_143(doc, payload["borang_143"])
        doc.add_page_break()
    if payload.get("saman_111"):
        _append_saman_111(doc, payload["saman_111"], b114)
        doc.add_page_break()
    _append_borang_114(doc, b114)
    doc.add_page_break()

    # 4. Fakta Kes, Senarai Saksi & Senarai Barang Kes (Eksibit)
    _add_paragraph_text(doc, "KEMENTERIAN KESIHATAN MALAYSIA — UNIT INSPEKTORAT DAN PERUNDANGAN", bold=True, size=11, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    _add_paragraph_text(doc, f"FAKTA KES, SENARAI SAKSI & BARANG KES ({no_kes})", bold=True, underline=True, size=11, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=10)

    _add_paragraph_text(doc, "FAKTA KES", bold=True, underline=True, size=11, space_after=4)
    _add_paragraph_text(doc, payload.get("fakta_kes", "-"), align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_after=10)

    _add_paragraph_text(doc, "SENARAI SAKSI PENDAKWAAN", bold=True, underline=True, size=11, space_after=4)
    saksi_rows = [
        [
            s.get("bil", "-"),
            s.get("nama", "-"),
            s.get("no_kp", "-"),
            s.get("jawatan_peranan", "-"),
            s.get("alamat_hubungan", "-"),
        ]
        for s in payload.get("senarai_saksi", [])
    ]
    _add_clean_table(doc, ["Bil.", "Nama Saksi", "No. K/P / Kad Kuasa", "Jawatan / Peranan", "Alamat / Pejabat"], saksi_rows or [["SP1", "-", "-", "-", "-"]])

    _add_paragraph_text(doc, "SENARAI BARANG KES (EKSIBIT)", bold=True, underline=True, size=11, space_before=10, space_after=4)
    ex_rows = [
        [
            e.get("tanda", "-"),
            e.get("perihal", "-"),
            e.get("no_lak_seal", "-"),
            e.get("lokasi_simpanan", "-"),
        ]
        for e in payload.get("senarai_eksibit", [])
    ]
    _add_clean_table(doc, ["Tanda", "Perihal Barang Kes", "No. Lak (Seal)", "Tempat Simpanan"], ex_rows or [["P1", "-", "-", "-"]])
    doc.add_page_break()

    # 5. Sijil Seksyen 90A(2) Akta Keterangan 1950
    _append_sijil_90a(doc, payload.get("sijil_90a", {}), no_kes)
    doc.add_page_break()

    # 6. Rakaman Percakapan Seksyen 112 KTJ
    if payload.get("rakaman_112"):
        _append_rakaman_112(doc, payload["rakaman_112"], no_kes)
        doc.add_page_break()

    # 7. Diari Siasatan (Seksyen 119 KTJ)
    _append_diari_siasatan(doc, payload.get("diari_siasatan", []), no_kes, b114)

    # 8. Hujahan Pemberatan Hukuman Pegawai Pendakwa
    if payload.get("pemberatan_hukuman"):
        doc.add_page_break()
        _append_pemberatan_hukuman(doc, payload["pemberatan_hukuman"], no_kes, b114)

    return _doc_to_bytes(doc)


def generate_docx_by_type(doc_type: str, payload: Dict[str, Any]) -> tuple[bytes, str]:
    normalized = doc_type.strip().lower()
    if normalized == "borang_114":
        return generate_borang_114_docx(payload), "Borang_114_Mahkamah_Pertuduhan.docx"
    if normalized == "saman_111":
        doc = _configure_base_doc()
        b114 = payload.get("borang_114", {})
        _append_saman_111(doc, payload.get("saman_111", b114), b114)
        return _doc_to_bytes(doc), "Saman_Mahkamah_111.docx"
    if normalized == "diari_siasatan":
        return generate_diari_siasatan_docx(payload), "Diari_Siasatan_S119_KTJ.docx"
    if normalized == "rakaman_112":
        return generate_rakaman_112_docx(payload), "Rakaman_Percakapan_S112_KTJ.docx"
    if normalized == "notis_kompaun":
        return generate_compound_notice_docx(payload), "Notis_Kompaun_KKM.docx"
    return generate_full_ip_package_docx(payload), "Pakej_Kertas_Siasatan_UIP_Lengkap.docx"
