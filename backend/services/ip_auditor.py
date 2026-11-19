"""Modul Semakan IP Sebelum Hantar TPR (IP Technical Auditor).

Menilai fail PDF/DOCX/TXT Kertas Siasatan terhadap 20 perkara asas IP
menggunakan `gemini-decision-1` (apabila API key aktif) dan enjin semakan
fakta/statutori tempatan yang menyemak percanggahan tarikh, kesilapan petikan
seksyen, format MyKad, nombor lak barang kes, S.112 KTJ dan Sijil S.90A.
"""

from __future__ import annotations

import io
import re
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

import pymupdf as fitz
from docx import Document

from backend.core.model_router import UIPModelRouter
from backend.core.redactor import RedactionResult

IP_AUDIT_CRITERIA: List[Dict[str, Any]] = [
    {
        "code": "C01",
        "title": "Tarikh, Masa & Lokasi Kejadian Sama dalam Semua Borang",
        "category": "Fakta Kes",
        "threshold": 0.90,
        "description": "Tarikh, masa dan alamat tempat kejadian mesti konsisten antara Borang Pemeriksaan, DS, Rakaman S.112, Laporan Makmal/Entomologi, Sijil 90A dan Borang 114.",
        "positive_keywords": ["tarikh kejadian", "masa kejadian", "alamat kejadian", "tarikh dan masa yang sama", "konsisten"],
        "negative_keywords": ["tidak konsisten", "tarikh berbeza", "percanggahan tarikh", "masa berlainan", "berbeza dengan tarikh"],
        "statute_ref": "Seksyen 153 Kanun Tatacara Jenayah [Akta 593]",
        "remedy": "Selaraskan semua tarikh dan waktu pada Borang Pemeriksaan, DS, laporan makmal/entomologi dan Borang 114 supaya tiada percanggahan.",
    },
    {
        "code": "C02",
        "title": "Nama Penuh & No. K/P OKT / OKS Tepat (Ikut MyKad)",
        "category": "Identiti OKT",
        "threshold": 0.92,
        "description": "Nama penuh ikut MyKad dan No. K/P 12 digit OKT/OKS direkod dengan betul.",
        "positive_keywords": ["[suspek_1]", "[no_kp_1]", "no. k/p", "kad pengenalan", "nama suspek", "nama pemilik", "nama pengurus"],
        "negative_keywords": ["tiada no. kp", "identiti belum disahkan", "nama tidak lengkap"],
        "statute_ref": "Seksyen 152 Kanun Tatacara Jenayah [Akta 593]",
        "remedy": "Dapatkan salinan MyKad atau semakan JPN dan rekodkan nama penuh serta No. K/P 12 digit OKS dengan tepat.",
    },
    {
        "code": "C03",
        "title": "Cetakan Carian SSM / Lesen PBT & Liabiliti Syarikat",
        "category": "Identiti OKT",
        "threshold": 0.88,
        "description": "Cetakan carian rasmi SSM (e-Info/MyData) dan lesen PBT dilampirkan; jika melibatkan syarikat Sdn. Bhd., rujuk Seksyen 51 Akta 852 / Seksyen 33A Akta 281.",
        "positive_keywords": ["[no_ssm_1]", "ssm", "e-info", "mydata", "lesen premis", "pengarah", "seksyen 51", "seksyen 33a"],
        "negative_keywords": ["tiada carian ssm", "belum buat carian ssm"],
        "statute_ref": "Seksyen 51 Akta 852 / Seksyen 33A Akta Makanan 1983 / Akta Syarikat 2016",
        "remedy": "Lampirkan cetakan carian rasmi e-Info SSM bersama Sijil S.90A dan sahkan sama ada pertuduhan dikenakan ke atas syarikat atau pengarah (S.51 Akta 852 / S.33A Akta 281).",
    },
    {
        "code": "C04",
        "title": "Salinan Kad Kuasa & Surat Kuasa Pegawai Diberi Kuasa",
        "category": "Kuasa Pegawai",
        "threshold": 0.90,
        "description": "PPKP pemeriksa dan IO mempunyai No. Kad Kuasa rasmi KKM yang sah di bawah Seksyen 25 Akta 852 / Seksyen 3 Akta 281 / Seksyen 3 Akta 154 / Seksyen 2 & 3 Akta 342 serta salinan Kad Kuasa dilampirkan.",
        "positive_keywords": ["kad kuasa", "salinan kad kuasa", "pegawai diberi kuasa", "ppkp", "surat kuasa", "kkm-"],
        "negative_keywords": ["tiada kad kuasa", "luput tarikh kuasa"],
        "statute_ref": "Seksyen 25 Akta 852 / Seksyen 3 Akta 281 / Seksyen 3 Akta 154 / Seksyen 2 & 3 Akta 342",
        "remedy": "Lampirkan salinan Kad Kuasa rasmi KKM yang masih sah dan surat pelantikan / penurunan kuasa.",
    },
    {
        "code": "C05",
        "title": "Rakaman Percakapan Saksi & OKT (Seksyen 112 KTJ)",
        "category": "Prosedur KTJ",
        "threshold": 0.92,
        "description": "Percakapan saksi utama (termasuk PPKP pengiring/saksi bebas) dan OKT diambil secara bertulis di bawah Seksyen 112 KTJ.",
        "positive_keywords": ["seksyen 112", "s.112", "percakapan saksi", "percakapan okt", "rakaman s.112"],
        "negative_keywords": ["tiada percakapan", "belum dirakam"],
        "statute_ref": "Seksyen 112(1) Kanun Tatacara Jenayah [Akta 593]",
        "remedy": "Ambil rakaman percakapan bertulis saksi pengiring, saksi bebas, dan OKT di bawah Seksyen 112 KTJ.",
    },
    {
        "code": "C06",
        "title": "Tandatangan Saksi, IO & Perakuan Seksyen 112(5) KTJ",
        "category": "Prosedur KTJ",
        "threshold": 0.90,
        "description": "Setiap rakaman S.112 KTJ dibaca semula dan ditandatangani oleh pembuat pernyataan, IO serta jurubahasa (hanya jika tidak fasih Bahasa Melayu).",
        "positive_keywords": ["ditandatangani oleh saksi", "ditandatangani oleh semua", "112(5)", "dibaca semula", "tandatangan"],
        "negative_keywords": ["belum ditandatangani", "tiada tandatangan", "tidak bertandatangan"],
        "statute_ref": "Seksyen 112(5) Kanun Tatacara Jenayah [Akta 593]",
        "remedy": "Pastikan saksi, OKT, jurubahasa (jika bahasa asing) dan IO menandatangani setiap helaian serta perakuan penutup Seksyen 112(5) KTJ.",
    },
    {
        "code": "C07",
        "title": "Amaran Statutori Seksyen 112(2) & (3) menurut S.112(4) KTJ",
        "category": "Prosedur KTJ",
        "threshold": 0.88,
        "description": "IO memaklumkan kewajipan menjawab benar dan hak enggan menjawab soalan membabitkan diri di bawah Seksyen 112(2) & (3) sebelum merakam percakapan.",
        "positive_keywords": ["112(2)", "112(3)", "112(4)", "amaran", "seksyen 112"],
        "negative_keywords": ["tiada nota amaran", "tiada amaran", "tidak diberi amaran"],
        "statute_ref": "Seksyen 112(2), 112(3) & 112(4) Kanun Tatacara Jenayah [Akta 593]",
        "remedy": "Catatkan perakuan pemakluman Seksyen 112(2) & (3) KTJ di awal setiap rakaman percakapan sebelum soalan dikemukakan.",
    },
    {
        "code": "C08",
        "title": "Diari Siasatan (DS) Mengikut Susunan Masa (Seksyen 119 KTJ)",
        "category": "Dokumen IP",
        "threshold": 0.85,
        "description": "Diari Siasatan (DS) bernombor butiran lengkap merekodkan siasatan dari laporan pertama hingga IP ditutup untuk semakan UIP/TPR.",
        "positive_keywords": ["diari siasatan", "susunan masa", "kronologi", "seksyen 119", "ds"],
        "negative_keywords": ["tiada diari siasatan", "ds tidak lengkap"],
        "statute_ref": "Seksyen 119 Kanun Tatacara Jenayah [Akta 593]",
        "remedy": "Lengkapkan jadual Diari Siasatan (DS) dengan butiran tarikh, masa, tindakan dan tandatangan ringkas IO.",
    },
    {
        "code": "C09",
        "title": "Borang Senarai Sitaan / Perintah Tutup & Akuan Terima",
        "category": "Barang Kes",
        "threshold": 0.90,
        "description": "Senarai Benda Disita (Seksyen 36 Akta 852 / Seksyen 4 Akta 281) atau Perintah Penutupan Premis (Seksyen 11 Akta 281) disediakan dan salinan diserahkan berserta akuan terima.",
        "positive_keywords": ["seksyen 36", "senarai benda disita", "senarai sitaan", "borang sitaan", "perintah penutupan", "akuan tandatangan terima", "akuan terima"],
        "negative_keywords": ["tiada borang sitaan", "salinan tidak diserahkan", "sitaan seksyen 38"],
        "statute_ref": "Seksyen 35 & 36 Akta 852 / Seksyen 4 & 11 Akta Makanan 1983",
        "remedy": "Gunakan Borang Senarai Benda Disita di bawah Seksyen 36 Akta 852 (bukan Seksyen 38) atau Perintah Seksyen 11 Akta 281 dengan tandatangan terima pemilik.",
    },
    {
        "code": "C10",
        "title": "Rantaian Barang Kes (Label, Nombor Lak / Seal & Stor)",
        "category": "Barang Kes",
        "threshold": 0.92,
        "description": "Semua barang kes/sampel dilabel tanda eksibit (P1..Pn), dilak (seal) dengan nombor siri lak KKM yang jelas, dan direkod keluar-masuk stor eksibit.",
        "positive_keywords": ["dilak", "seal", "lak keselamatan", "lak rasmi", "stor eksibit", "dilabel"],
        "negative_keywords": ["tidak mempunyai nombor lak", "tidak mempunyai nombor meterai", "tiada seal", "rantaian terputus", "tiada label"],
        "statute_ref": "SOP Pengendalian Barang Kes & Rantaian Eksibit UIP KKM",
        "remedy": "Rekodkan nombor siri lak (seal) KKM, tanda eksibit, dan borang serah-terima stor eksibit atau makmal dengan lengkap.",
    },
    {
        "code": "C11",
        "title": "Perakuan Juruanalisis (S.19 Akta 281) / Entomologi (Akta 154) / Makmal TBIS 20C (Akta 342)",
        "category": "Bukti Makmal",
        "threshold": 0.88,
        "description": "Bagi kes persampelan makanan (S.19 Akta 281), pembiakan Aedes (Akta 154), atau kes Tibi (TBIS 20C di bawah Akta 342), laporan rasmi makmal/entomologi/kahak dan borang permintaan ujian wajib dilampirkan.",
        "positive_keywords": ["perakuan juruanalisis", "seksyen 19", "laporan makmal", "entomologi", "mkak", "laporan analisis", "tbis 20c", "smear positif"],
        "negative_keywords": ["tiada laporan makmal", "laporan entomologi belum diterima", "najis tikus ke makmal"],
        "statute_ref": "Seksyen 19 Akta Makanan 1983 / Seksyen 399 KTJ / Akta 154 / Akta 342 (TBIS 20C)",
        "remedy": "Lampirkan Perakuan Juruanalisis Makanan (S.19 Akta 281), Sijil Pengecaman Entomologi (Akta 154), atau Borang/Keputusan Makmal TBIS 20C (Akta 342).",
    },
    {
        "code": "C12",
        "title": "Sijil Seksyen 90A(2) Akta Keterangan 1950 (Cetakan Digital & SSM)",
        "category": "Keterangan Digital",
        "threshold": 0.95,
        "description": "Setiap gambar digital yang dicetak dan cetakan komputer e-Info SSM wajib disertai Sijil Seksyen 90A(2) dengan spesifikasi kamera/komputer dan klausa 'sepanjang pengetahuan dan kepercayaan'.",
        "positive_keywords": ["sijil seksyen 90a", "90a(2)", "sepanjang pengetahuan dan kepercayaan", "beroperasi dalam keadaan baik", "pengendalian biasa"],
        "negative_keywords": ["belum ditandatangani dan belum dilampirkan", "tiada sijil seksyen 90a", "tanpa sijil 90a", "belum dilampirkan", "akan disediakan kemudian", "masih dalam tindakan"],
        "statute_ref": "Seksyen 90A(1), (2) & (4) Akta Keterangan 1950 [Akta 56]",
        "remedy": "Sediakan dan tandatangani Sijil Seksyen 90A(2) lengkap dengan model kamera, komputer, pencetak, tarikh cetakan, dan klausa 'sepanjang pengetahuan dan kepercayaan saya'.",
    },
    {
        "code": "C13",
        "title": "Gambar Bukti Berwarna, Bertarikh & Ada Kapsyen Lokasi",
        "category": "Keterangan Digital",
        "threshold": 0.85,
        "description": "Gambar bukti kesalahan jelas, berwarna, bertarikh, mempunyai kapsyen lokasi tepat dan dikenal pasti nama jurugambar PPKP.",
        "positive_keywords": ["gambar", "foto", "jurugambar", "kamera", "keping gambar"],
        "negative_keywords": ["gambar kabur", "tiada gambar bukti", "tiada tarikh gambar"],
        "statute_ref": "Seksyen 90A Akta Keterangan 1950 [Akta 56]",
        "remedy": "Susun gambar foto berwarna berkapsyen (tarikh, masa, lokasi, nama jurugambar PPKP) dan labelkan sebagai eksibit.",
    },
    {
        "code": "C14",
        "title": "Ketepatan Seksyen Kesalahan & Hukuman Borang 114 (Tiada Duplicity)",
        "category": "Kertas Pertuduhan",
        "threshold": 0.95,
        "description": "Borang 114 memisahkan Seksyen Kesalahan dengan Seksyen Hukuman secara tepat, tidak mencampurkan dua kesalahan berlainan (S.163 KTJ), serta disertakan draf Borang 143 & Izin Mendakwa TPR.",
        "positive_keywords": ["borang 114", "borang 143", "izin mendakwa", "dibaca bersama", "pertuduhan berasingan"],
        "negative_keywords": ["pertindihan pertuduhan", "duplicity", "seksyen salah", "dalam satu pertuduhan yang sama"],
        "statute_ref": "Seksyen 128, 152, 154, 163 & 376(3) KTJ [Akta 593]",
        "remedy": "Asingkan setiap kesalahan ke dalam Borang 114 berasingan (S.163 KTJ), nyatakan Seksyen Kesalahan dan Seksyen Hukuman secara tepat, serta sertakan Borang 143 & permohonan Izin Mendakwa TPR.",
    },
    {
        "code": "C15",
        "title": "Semua Elemen Kesalahan Masuk dalam Ayat Pertuduhan",
        "category": "Kertas Pertuduhan",
        "threshold": 0.92,
        "description": "Ayat pertuduhan mengandungi semua unsur wajib kesalahan (identiti OKS, tarikh, masa, premis, daerah/negeri, perbuatan spesifik, peraturan subsidiari seperti P.U.(A) 260/2024 atau PPKM 2009).",
        "positive_keywords": ["melanggar", "peraturan", "seksyen", "premis", "p.u."],
        "negative_keywords": ["intipati tidak lengkap", "unsur kesalahan tidak dibuktikan"],
        "statute_ref": "Seksyen 152 & 154 Kanun Tatacara Jenayah [Akta 593]",
        "remedy": "Pastikan teks pertuduhan Borang 114 menyebut lengkap 5 unsur mandatori termasuk peraturan subsidiari (cth: Peraturan 6 P.U.(A) 260/2024 bagi pameran vape).",
    },
    {
        "code": "C16",
        "title": "Semakan Had Masa Pendakwaan & Tamat Tempoh Kompaun / Pendakwaan Terus S.22(b) Akta 342",
        "category": "Kompaun & Had Masa",
        "threshold": 0.90,
        "description": "Kes masih dalam had masa pendakwaan; jika tawaran kompaun dikeluarkan (S.48 Akta 852 [30 hari], S.33 Akta 281, atau S.25 Akta 154 [14 hari]), Unit Hasil sahkan belum dibayar. Kes ingkar rawatan Tibi (S.22(b) Akta 342 / TBIS 10D) dibawa terus ke mahkamah tanpa tawaran kompaun.",
        "positive_keywords": ["had masa", "tamat tempoh", "seksyen 48", "seksyen 33", "seksyen 25", "tanpa bayaran", "tbis 10d", "tiada tawaran kompaun", "izin mendakwa"],
        "negative_keywords": ["tamat had masa", "tempoh kompaun belum tamat", "kompaun telah dibayar", "kompaun seksyen 44"],
        "statute_ref": "Seksyen 48 Akta 852 / Seksyen 33 Akta 281 / Seksyen 25 Akta 154 / Seksyen 22(b) & 24(a) Akta 342",
        "remedy": "Lampirkan pengesahan Unit Hasil bahawa tawaran kompaun tidak dibayar selepas tamat tempoh statutori, atau rujukan TBIS 10D/Izin Dakwa bagi kes pendakwaan terus Akta 342.",
    },
    {
        "code": "C17",
        "title": "Bukti Serahan Sah Notis S.32B / S.47 / Notis Arahan Rawatan Akta 342 / Kad AR",
        "category": "Kompaun & Had Masa",
        "threshold": 0.88,
        "description": "Ada bukti serahan sah Notis Seksyen 47 Akta 852 / Notis Seksyen 32B Akta 281 / Notis Arahan Menjalani Rawatan Akta 342 & TBIS 10D (tandatangan terima serahan tangan & saksi atau Kad AR pos berdaftar).",
        "positive_keywords": ["bukti serahan", "pos berdaftar", "kad ar", "seksyen 32b", "seksyen 47", "akuan terima", "notis arahan menjalani rawatan", "tbis 10d", "diserahkan secara tangan"],
        "negative_keywords": ["tiada bukti serahan", "gagal serah notis"],
        "statute_ref": "Seksyen 47 Akta 852 / Seksyen 32B Akta Makanan 1983 / Seksyen 22(b) Akta 342",
        "remedy": "Lampirkan salinan Notis S.32B / S.47 / Notis Arahan Rawatan bertandatangan terima oleh penerima & saksi atau Kad AR Pos Berdaftar.",
    },
    {
        "code": "C18",
        "title": "Pelan Lakar Lokasi Kejadian Dilampirkan & Bertandatangan",
        "category": "Dokumen IP",
        "threshold": 0.82,
        "description": "Pelan lakar premis/tapak menunjukkan kedudukan sebenar barang kes atau tempat pembiakan larva beserta tandatangan IO dan tarikh.",
        "positive_keywords": ["pelan lakar", "rajah kasar", "kedudukan", "ditandatangani oleh io", "bertandatangan io"],
        "negative_keywords": ["tiada pelan lakar", "rajah kasar tidak bertandatangan"],
        "statute_ref": "Standard Penyediaan Kertas Siasatan UIP KKM",
        "remedy": "Lampirkan pelan lakar lokasi (tidak mengikut skala) dengan tanda kedudukan eksibit serta tandatangan dan tarikh IO.",
    },
    {
        "code": "C19",
        "title": "Fakta Kes Jelas & Selari dengan Borang 114",
        "category": "Dokumen IP",
        "threshold": 0.88,
        "description": "Fakta Kes ditulis objektif mengikut kronologi sebelum, semasa dan selepas pemeriksaan serta selari dengan Borang 114 dan Laporan Pengadu (FIR).",
        "positive_keywords": ["fakta kes", "laporan pengadu", "pemeriksaan", "mendapati", "perintah"],
        "negative_keywords": ["fakta kes bercanggah", "tiada fakta kes"],
        "statute_ref": "Garis Panduan Penyediaan Fakta Kes UIP KKM",
        "remedy": "Semak semula Fakta Kes dan Laporan Pengadu (FIR) supaya selari dengan tarikh, lokasi, dan pertuduhan pada Borang 114.",
    },
    {
        "code": "C20",
        "title": "Maklumat Sulit (Nama/No. KP/Syarikat) Ditutup Sebelum Hantar AI",
        "category": "Privasi & OSA",
        "threshold": 0.85,
        "description": "Nama OKT, saksi, No. K/P dan nama syarikat ditutup menggunakan token [SUSPEK_1] sebelum diproses oleh AI awan (patuh OSA/PDPA).",
        "positive_keywords": ["[suspek_1]", "[no_kp_1]", "[premis_1]", "penyamaran", "pdpa"],
        "negative_keywords": [],
        "statute_ref": "Akta Rahsia Rasmi 1972 (OSA) & PDPA 2010",
        "remedy": "Pastikan fungsi penyamaran data sulit aktif sebelum menghantar teks ke AI luar.",
    },
]


@dataclass
class CriterionAuditResult:
    code: str
    title: str
    category: str
    status: str  # "LULUS" | "SEMAK" | "GAGAL"
    answer: str  # "Yes" | "No"
    calibrated_score: float
    threshold: float
    evidence_snippet: str
    statute_ref: str
    recommendation: str


@dataclass
class IPAuditReport:
    filename: str
    akta_utama: str
    overall_score: float
    readiness_status: str
    counts: Dict[str, int]
    criteria_results: List[CriterionAuditResult]
    tpr_summary_notes: List[str]
    kuiri_tpr: List[Dict[str, str]]
    ip_folder_checklist: List[Dict[str, str]]
    statutory_citations: List[Dict[str, Any]]
    redaction_summary: Dict[str, Any]
    models_used: Dict[str, str]
    extracted_text: str


def extract_text_from_upload(file_bytes: bytes, filename: str) -> str:
    low = filename.lower()
    if low.endswith(".pdf"):
        pages: List[str] = []
        with fitz.open(stream=file_bytes, filetype="pdf") as doc:
            for idx, page in enumerate(doc, start=1):
                pages.append(f"--- Muka Surat {idx} ---\n{page.get_text('text')}")
        return "\n".join(pages).strip()
    if low.endswith(".docx"):
        doc = Document(io.BytesIO(file_bytes))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    return file_bytes.decode("utf-8", errors="ignore")


class IPTechnicalAuditor:
    """Menyemak Kertas Siasatan terhadap 20 perkara asas sebelum dihantar ke TPR."""

    def __init__(self, router: Optional[UIPModelRouter] = None) -> None:
        self.router = router or UIPModelRouter()

    def audit_ip(
        self,
        raw_text: str,
        akta_utama: str = "Akta 852",
        filename: str = "kertas_siasatan.txt",
        use_ollama_redaction: bool = True,
        fast_mode: bool = False,
    ) -> IPAuditReport:
        redaction: RedactionResult = self.router.redactor.redact(
            raw_text, use_ollama=use_ollama_redaction
        )

        citations = self.router.rag_store.search_statutes(
            query=f"{akta_utama} Seksyen 112 Seksyen 90A Borang 114 {redaction.redacted_text[:400]}",
            akta_filter=None if akta_utama == "Semua" else akta_utama,
            top_k=4,
        )
        citations_dict = [
            {
                "akta_code": c.akta_code,
                "akta_title": c.akta_title,
                "section": c.section,
                "text": c.text,
                "score": c.score,
            }
            for c in citations
        ]

        if fast_mode:
            cloud_results, decision_model_used = None, "Enjin Semakan Statutori KKM (Mod Pantas)"
        else:
            cloud_results, decision_model_used = self.router.run_compliance_decision(
                redacted_text=redaction.redacted_text,
                criteria_list=IP_AUDIT_CRITERIA,
                statutory_context=citations,
            )

        cloud_by_code: Dict[str, Dict[str, Any]] = {}
        if cloud_results:
            for item in cloud_results:
                code = str(item.get("code", "")).strip().upper()
                if code:
                    cloud_by_code[code] = item

        criteria_results: List[CriterionAuditResult] = []
        for spec in IP_AUDIT_CRITERIA:
            code = spec["code"]
            # Sentiasa jalankan semakan statutori & fakta tempatan sebagai semakan keselamatan
            res_local = self._evaluate_criterion_local(
                spec=spec,
                raw_text=raw_text,
                redacted_text=redaction.redacted_text,
                akta_utama=akta_utama,
                token_map=redaction.token_map,
            )

            if (
                code in cloud_by_code
                and res_local["status"] != "GAGAL"
                and not res_local.get("contextual_override")
            ):
                c_item = cloud_by_code[code]
                score = round(min(0.99, max(0.01, float(c_item.get("calibrated_score", 0.50)))), 2)
                ans = str(c_item.get("answer", "No")).strip().capitalize()
                if ans not in ("Yes", "No"):
                    ans = "Yes" if score >= spec["threshold"] else "No"
                snippet = str(c_item.get("evidence_snippet", res_local["snippet"]))
                rec = str(c_item.get("recommendation", spec["remedy"]))
                status = self._determine_status(score, spec["threshold"], ans)
            else:
                score = res_local["score"]
                ans = res_local["answer"]
                snippet = res_local["snippet"]
                rec = res_local["recommendation"]
                status = res_local["status"]

            restored_snippet = self.router.redactor.rehydrate(snippet, redaction.token_map)
            criteria_results.append(
                CriterionAuditResult(
                    code=code,
                    title=spec["title"],
                    category=spec["category"],
                    status=status,
                    answer=ans,
                    calibrated_score=score,
                    threshold=spec["threshold"],
                    evidence_snippet=restored_snippet,
                    statute_ref=spec["statute_ref"],
                    recommendation=rec,
                )
            )

        counts = {
            "LULUS": sum(1 for c in criteria_results if c.status == "LULUS"),
            "SEMAK": sum(1 for c in criteria_results if c.status == "SEMAK"),
            "GAGAL": sum(1 for c in criteria_results if c.status == "GAGAL"),
        }
        overall_score = round(
            sum(c.calibrated_score for c in criteria_results) / max(1, len(criteria_results)) * 100,
            1,
        )

        if counts["GAGAL"] == 0 and counts["SEMAK"] <= 2 and overall_score >= 82.0:
            readiness = "SEDIA DIHANTAR KE TPR"
        elif counts["GAGAL"] >= 2 or overall_score < 65.0:
            readiness = "DITOLAK / ADA KUIRI KRITIKAL"
        else:
            readiness = "PERLU LENGKAPKAN DULU (IO)"

        tpr_notes = self._build_tpr_summary(criteria_results, readiness, akta_utama)
        kuiri_tpr = self._build_kuiri_tpr(criteria_results)
        ip_folder_checklist = self._build_ip_folder_checklist(criteria_results)

        return IPAuditReport(
            filename=filename,
            akta_utama=akta_utama,
            overall_score=overall_score,
            readiness_status=readiness,
            counts=counts,
            criteria_results=criteria_results,
            tpr_summary_notes=tpr_notes,
            kuiri_tpr=kuiri_tpr,
            ip_folder_checklist=ip_folder_checklist,
            statutory_citations=citations_dict,
            redaction_summary={
                "engine_used": redaction.engine_used,
                "ollama_available": redaction.ollama_available,
                "entities_masked": len(redaction.entities),
                "token_map": redaction.token_map,
                "entities": [asdict(e) for e in redaction.entities],
                "redacted_text": redaction.redacted_text,
                "warnings": redaction.warnings,
            },
            models_used={
                "privacy_engine": redaction.engine_used,
                "decision_engine": decision_model_used,
                "rag_engine": self.router.rag_store.engine_name,
            },
            extracted_text=raw_text,
        )

    @staticmethod
    def _determine_status(score: float, threshold: float, answer: str) -> str:
        if answer == "Yes" and score >= threshold:
            return "LULUS"
        if answer == "Yes":
            return "SEMAK"
        if score < 0.55:
            return "GAGAL"
        return "SEMAK"

    @staticmethod
    def _find_best_line_snippet(text: str, keywords: List[str]) -> str:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for kw in keywords:
            kw_low = kw.lower()
            for line in lines:
                if kw_low in line.lower():
                    return line[:220]
        return "Tiada maklumat berkaitan dijumpai dalam teks IP."

    @staticmethod
    def _detect_statutory_citation_errors(code: str, low: str) -> Optional[str]:
        """Mengesan petikan seksyen/peraturan yang salah secara baris demi baris."""
        lines = [ln.strip() for ln in low.splitlines() if ln.strip()]
        for ln in lines:
            if code == "C09" and (
                "sitaan seksyen 38" in ln
                or ("seksyen 38 akta 852" in ln and ("sitaan" in ln or "disita" in ln))
                or ("s.38 akta 852" in ln and ("sitaan" in ln or "disita" in ln))
            ):
                return "KESALAHAN SEKSYEN: Seksyen 38 Akta 852 ialah kos memegang barang disita. Penyitaan ialah Seksyen 35 dan Senarai Benda Disita ialah Seksyen 36 Akta 852!"
            if code == "C16" and (
                "kompaun seksyen 44" in ln
                or ("seksyen 44 akta 852" in ln and "kompaun" in ln)
            ):
                return "KESALAHAN SEKSYEN: Seksyen 44 Akta 852 ialah perlindungan pemberi maklumat. Kuasa mengkompaun ialah Seksyen 48 Akta 852 [P.U. (A) 259/2024]!"
            if code == "C03" and "seksyen 32b" in ln and ("pengarah" in ln or "syarikat" in ln or "liabiliti" in ln):
                return "KESALAHAN SEKSYEN: Seksyen 32B Akta Makanan 1983 ialah notis hadir mahkamah. Liabiliti pengarah/syarikat ialah Seksyen 33A Akta Makanan 1983!"
            if code == "C14" and ("tifoid" in ln or "typhoid" in ln) and "peraturan 30" in ln and "peraturan 31" not in ln:
                return "KESALAHAN PERATURAN: Kesalahan tiada suntikan anti-tifoid ialah di bawah Peraturan 31(1) PPKM 2009 (Peraturan 30 ialah Latihan Pengendali Makanan)."
            if code == "C14" and "akta 514" in ln and any(
                k in low for k in ("tibi", "tuberkulosis", "tbis", "apppb", "akta 342", "penyakit berjangkit", "22(b)")
            ):
                if not any(ok in ln for ok in ("pembetulan", "bukan akta 514", "ralat akta 514", "tersilap")):
                    return "KESALAHAN AKTA: Akta 514 ialah Akta Keselamatan dan Kesihatan Pekerjaan (OSHA 1994). Kes ingkar rawatan Tibi / penyakit berjangkit ialah di bawah Seksyen 22(b) Akta 342 [APPPB 1988]!"
        return None

    @staticmethod
    def _check_date_conflict(raw_text: str) -> Optional[str]:
        """Mengesan jika Tarikh Kejadian bercanggah dengan tarikh laporan entomologi / makmal / sitaan."""
        main_date_m = re.search(
            r"tarikh\s+kejadian\s*[:\-]\s*(\d{1,2}\s+[A-Za-z]+\s+\d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            raw_text,
            flags=re.I,
        )
        if not main_date_m:
            return None
        main_date = main_date_m.group(1).strip().lower()
        # Semak baris Laporan Entomologi / Borang Sampel / Borang Sitaan
        for line in raw_text.splitlines():
            l_low = line.lower()
            if any(tag in l_low for tag in ("laporan entomologi", "borang sampel", "tarikh kutipan", "tarikh pada borang")):
                other_m = re.search(r"(\d{1,2}\s+[A-Za-z]+\s+\d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", line)
                if other_m:
                    other_date = other_m.group(1).strip().lower()
                    if other_date != main_date:
                        return f"Tarikh pada dokumen sokongan ({other_m.group(1)}) bercanggah dengan Tarikh Kejadian ({main_date_m.group(1)})."
        return None

    def _evaluate_criterion_local(
        self,
        spec: Dict[str, Any],
        raw_text: str,
        redacted_text: str,
        akta_utama: str,
        token_map: Dict[str, str],
    ) -> Dict[str, Any]:
        low = redacted_text.lower()
        code = spec["code"]
        threshold = float(spec["threshold"])

        # Semak kesalahan petikan seksyen terlebih dahulu
        statute_err = self._detect_statutory_citation_errors(code, low)
        if statute_err:
            return {
                "score": 0.24,
                "answer": "No",
                "status": "GAGAL",
                "snippet": statute_err,
                "recommendation": statute_err,
            }

        # C01: Semak percanggahan tarikh sebenar merentas dokumen
        if code == "C01":
            conflict = self._check_date_conflict(raw_text)
            if conflict:
                return {
                    "score": 0.22,
                    "answer": "No",
                    "status": "GAGAL",
                    "snippet": conflict,
                    "recommendation": spec["remedy"],
                }

        # C02: Pengesahan MyKad sebenar secara tempatan (kerana nombor KP ditutup kepada [NO_KP_1] sebelum dihantar ke AI awan)
        if code == "C02":
            ic_m = re.search(r"\b(\d{2})(\d{2})(\d{2})-(\d{2})-(\d{4})\b", raw_text)
            has_neg_c02 = any(nk in low for nk in spec["negative_keywords"])
            if not has_neg_c02 and ic_m and ("[suspek_1]" in low or "no. k/p" in low or "kad pengenalan" in low):
                mm, dd = int(ic_m.group(2)), int(ic_m.group(3))
                if 1 <= mm <= 12 and 1 <= dd <= 31:
                    return {
                        "score": 0.94,
                        "answer": "Yes",
                        "status": "LULUS",
                        "snippet": self._find_best_line_snippet(redacted_text, ["[suspek_1]", "[no_kp_1]", "no. k/p"]),
                        "recommendation": "Identiti OKT/OKS dan format No. K/P 12 digit disahkan sah secara tempatan.",
                        "contextual_override": True,
                    }
                return {
                    "score": 0.25,
                    "answer": "No",
                    "status": "GAGAL",
                    "snippet": f"Format tarikh lahir pada No. K/P ({ic_m.group(0)}) tidak sah.",
                    "recommendation": spec["remedy"],
                }

        # C20: Semakan Penyamaran OSA/PDPA
        if code == "C20":
            masked_count = len(token_map)
            if masked_count >= 1:
                return {
                    "score": 0.96,
                    "answer": "Yes",
                    "status": "LULUS",
                    "snippet": f"Sebanyak {masked_count} maklumat peribadi (nama/No. KP/syarikat) telah ditutup sebelum disemak.",
                    "recommendation": "Patuh — maklumat sulit OKT dan saksi telah dilindungi.",
                    "contextual_override": True,
                }
            return {
                "score": 0.72,
                "answer": "No",
                "status": "SEMAK",
                "snippet": "Tiada nama atau No. K/P khusus dikesan untuk ditutup.",
                "recommendation": spec["remedy"],
            }

        # C11: Peka konteks Akta (Akta 852 iklan/pameran fizikal tidak wajib laporan makmal kecuali sampel cecair dihantar)
        if code == "C11" and ("852" in akta_utama or "akta 852" in low):
            if "sampel" not in low and "makmal" not in low and "kimia" not in low:
                return {
                    "score": 0.91,
                    "answer": "Yes",
                    "status": "LULUS",
                    "snippet": "Kes Akta 852 berasaskan bukti fizikal barang sitaan & gambar (ujian makmal kimia tidak wajib kecuali melibatkan analisis kandungan nikotin).",
                    "recommendation": "Tidak berkaitan untuk kes pameran/iklan melainkan terdapat sampel yang dihantar ke Jabatan Kimia.",
                    "contextual_override": True,
                }

        # Konteks khas Akta 342 Kes Tibi (pesakit individu, Notis Arahan Rawatan P4 & TBIS 10D/20C, pendakwaan terus tanpa kompaun/sitaan)
        is_tb_342 = ("342" in akta_utama or "akta 342" in low) and any(
            k in low for k in ("tibi", "tuberkulosis", "tbis", "smear positif")
        )
        if is_tb_342:
            has_neg = any(nk in low for nk in spec["negative_keywords"])
            if not has_neg:
                if code == "C03" and ("individu" in low or "pesakit" in low or "[suspek_1]" in low) and "sdn. bhd" not in low:
                    return {
                        "score": 0.92,
                        "answer": "Yes",
                        "status": "LULUS",
                        "snippet": "Kes melibatkan pesakit individu di bawah Akta 342 (carian SSM syarikat tidak berkenaan; identiti disahkan melalui MyKad/JPN).",
                        "recommendation": "Lengkap bagi kes pesakit individu di bawah Akta 342.",
                        "contextual_override": True,
                    }
                if code == "C09" and ("notis arahan" in low or "arahan menjalani rawatan" in low):
                    return {
                        "score": 0.92,
                        "answer": "Yes",
                        "status": "LULUS",
                        "snippet": self._find_best_line_snippet(redacted_text, ["notis arahan", "arahan menjalani rawatan"]),
                        "recommendation": "Patuh — Notis Arahan Menjalani Rawatan Penyakit Berjangkit (P4) menggantikan borang sitaan bagi kes Akta 342.",
                        "contextual_override": True,
                    }
                if code == "C10" and any(k in low for k in ("tbis", "eksibit", "p4", "p5")):
                    return {
                        "score": 0.90,
                        "answer": "Yes",
                        "status": "LULUS",
                        "snippet": "Rantaian eksibit kes Tibi berasaskan dokumen klinikal dan notis rasmi (e-Notifikasi P2, TBIS 20C P3, Notis Arahan P4, TBIS 10D P5).",
                        "recommendation": "Lengkap bagi rantaian eksibit dokumen klinikal & pengesanan Tibi.",
                        "contextual_override": True,
                    }
                if code == "C16" and ("tbis 10d" in low or "tiada tawaran kompaun" in low or "arahan menjalani rawatan" in low):
                    return {
                        "score": 0.93,
                        "answer": "Yes",
                        "status": "LULUS",
                        "snippet": "Kes ingkar rawatan Tibi di bawah Seksyen 22(b) Akta 342 dibawa terus untuk Izin Mendakwa mahkamah (tidak dikompaun) selepas tempoh notis tamat.",
                        "recommendation": "Patuh — pendakwaan terus Seksyen 22(b) Akta 342 tanpa tawaran kompaun.",
                        "contextual_override": True,
                    }

        neg_hits: List[str] = []
        for nk in spec["negative_keywords"]:
            if nk in low:
                if f"tanpa {nk}" in low or f"tiada {nk}" in low or f"bebas {nk}" in low:
                    continue
                neg_hits.append(nk)
        pos_hits = [pk for pk in spec["positive_keywords"] if pk in low]

        if neg_hits:
            snippet = self._find_best_line_snippet(redacted_text, neg_hits)
            score = round(max(0.14, 0.42 - (0.07 * (len(neg_hits) - 1))), 2)
            return {
                "score": score,
                "answer": "No",
                "status": "GAGAL",
                "snippet": snippet,
                "recommendation": spec["remedy"],
            }

        if len(low.strip()) < 120 and not pos_hits:
            return {
                "score": 0.35,
                "answer": "No",
                "status": "GAGAL",
                "snippet": "Teks dokumen terlalu pendek untuk disemak.",
                "recommendation": spec["remedy"],
            }

        if len(pos_hits) >= 2:
            snippet = self._find_best_line_snippet(redacted_text, pos_hits)
            boost = min(0.06, 0.02 * (len(pos_hits) - 2))
            score = round(min(0.98, threshold + 0.03 + boost), 2)
            return {
                "score": score,
                "answer": "Yes",
                "status": "LULUS",
                "snippet": snippet,
                "recommendation": "Lengkap dan patuh prosedur asas IP.",
            }

        if len(pos_hits) == 1:
            snippet = self._find_best_line_snippet(redacted_text, pos_hits)
            score = round(max(0.62, threshold - 0.08), 2)
            return {
                "score": score,
                "answer": "No",
                "status": "SEMAK",
                "snippet": snippet,
                "recommendation": spec["remedy"],
            }

        return {
            "score": 0.46,
            "answer": "No",
            "status": "GAGAL" if threshold >= 0.90 else "SEMAK",
            "snippet": "Dokumen atau catatan bagi perkara ini tidak dijumpai dalam teks IP.",
            "recommendation": spec["remedy"],
        }

    @staticmethod
    def _build_tpr_summary(
        results: List[CriterionAuditResult], readiness: str, akta_utama: str
    ) -> List[str]:
        failed = [r for r in results if r.status == "GAGAL"]
        review = [r for r in results if r.status == "SEMAK"]
        notes: List[str] = [
            f"Keputusan Semakan ({akta_utama}): {readiness}.",
        ]
        if failed:
            codes = ", ".join(f"{r.code} ({r.title})" for r in failed[:5])
            notes.append(f"Wajib baiki sebelum hantar IP ke TPR: {codes}.")
        if review:
            codes = ", ".join(r.code for r in review[:6])
            notes.append(f"Sila semak dan sahkan semula dokumen: {codes}.")
        if not failed and not review:
            notes.append("Semua 20 perkara asas IP sudah lengkap. Boleh terus hantar untuk permohonan Izin Mendakwa TPR.")
        return notes

    @staticmethod
    def _build_kuiri_tpr(results: List[CriterionAuditResult]) -> List[Dict[str, str]]:
        kuiri: List[Dict[str, str]] = []
        for r in results:
            if r.status == "LULUS":
                continue
            kuiri.append({
                "code": r.code,
                "tahap": "KUIRI WAJIB" if r.status == "GAGAL" else "PERINGATAN",
                "isu": r.title,
                "tindakan_io": r.recommendation,
            })
        return kuiri

    @staticmethod
    def _build_ip_folder_checklist(results: List[CriterionAuditResult]) -> List[Dict[str, str]]:
        """Memetakan keputusan 20 kriteria kepada Indeks Kandungan Fail IP KKM (Bahagian A-G)."""
        by_code = {r.code: r for r in results}

        def _agg(codes: List[str]) -> str:
            statuses = [by_code[c].status for c in codes if c in by_code]
            if any(s == "GAGAL" for s in statuses):
                return "TIDAK LENGKAP / KUIRI"
            if any(s == "SEMAK" for s in statuses):
                return "PERLU SEMAKAN"
            return "LENGKAP"

        return [
            {"bahagian": "A", "tajuk": "Kertas Minit, Izin Mendakwa TPR & Fakta Kes", "status": _agg(["C19", "C20"])},
            {"bahagian": "B", "tajuk": "Borang 114 (Pertuduhan) & Borang 143 (Pengaduan Majistret)", "status": _agg(["C14", "C15", "C01"])},
            {"bahagian": "C", "tajuk": "Notis S.32B / S.47, Tawaran Kompaun & Bukti Serahan (Kad AR)", "status": _agg(["C16", "C17"])},
            {"bahagian": "D", "tajuk": "Borang Sitaan (S.36) / Perintah S.11, Barang Kes, Pelan Lakar, Gambar & Sijil 90A", "status": _agg(["C09", "C10", "C12", "C13", "C18"])},
            {"bahagian": "E", "tajuk": "Rakaman Percakapan S.112 KTJ (Saksi & OKT) & Senarai Saksi", "status": _agg(["C05", "C06", "C07"])},
            {"bahagian": "F", "tajuk": "Carian Rasmi SSM, Kad Kuasa & Laporan Makmal (S.19) / Entomologi", "status": _agg(["C02", "C03", "C04", "C11"])},
            {"bahagian": "G", "tajuk": "Diari Siasatan (Seksyen 119 KTJ)", "status": _agg(["C08"])},
        ]
