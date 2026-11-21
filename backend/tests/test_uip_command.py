"""Ujian pengesahan komprehensif bertaraf produksi untuk UIP-Command."""

from __future__ import annotations

import io
import json

import pymupdf as fitz
from docx import Document
from fastapi.testclient import TestClient

from backend.core.redactor import PrivacyRedactor
from backend.main import app
from backend.rag.statutory_store import get_statutory_store
from backend.services.doc_generator import generate_docx_by_type
from backend.services.sample_cases import SAMPLE_CASES
from training.prepare_dataset import build_training_records

client = TestClient(app)
_CACHED_TEST_HEADERS: dict[str, str] | None = None
_CACHED_DEV_HEADERS: dict[str, str] | None = None


def _get_auth_headers() -> dict[str, str]:
    global _CACHED_TEST_HEADERS
    if _CACHED_TEST_HEADERS is not None:
        return _CACHED_TEST_HEADERS
    import uuid

    email = f"ppkp.pytest.{uuid.uuid4().hex[:6]}@moh.gov.my"
    res = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "PytestKKM#2026",
            "full_name": "PPKP Ujian Pytest",
        },
    )
    assert res.status_code == 200
    assert res.json()["user"]["is_dev_admin"] is False
    _CACHED_TEST_HEADERS = {"Authorization": f"Bearer {res.json()['token']}"}
    return _CACHED_TEST_HEADERS


def _get_dev_admin_headers() -> dict[str, str]:
    global _CACHED_DEV_HEADERS
    if _CACHED_DEV_HEADERS is not None:
        return _CACHED_DEV_HEADERS

    res = client.post(
        "/api/auth/register",
        json={
            "email": "zero4eleven@gmail.com",
            "password": "DevAdminKKM#2026",
            "full_name": "Ihsan Syairazy",
        },
    )
    if res.status_code == 400:
        res = client.post(
            "/api/auth/login",
            json={
                "email": "zero4eleven@gmail.com",
                "password": "DevAdminKKM#2026",
            },
        )
    assert res.status_code == 200
    assert res.json()["user"]["is_dev_admin"] is True
    _CACHED_DEV_HEADERS = {"Authorization": f"Bearer {res.json()['token']}"}
    return _CACHED_DEV_HEADERS


def test_privacy_redaction_whitelists_io_and_masks_cleanly() -> None:
    redactor = PrivacyRedactor()
    raw = (
        "Nama Premis: Kedai Serbaneka Harmoni Jaya Sdn. Bhd.\n"
        "No. SSM: 202101034892 (1435192-K)\n"
        "Alamat Kejadian: No. 18, Jalan PJS 8/9, Petaling Jaya\n"
        "Nama Suspek (OKT): Mohd Hafizuddin bin Kamaruddin\n"
        "No. K/P: 890415-10-5321\n"
        "No. Tel: 012-7748392\n"
        "Pegawai Penyiasat (IO): PPKP Ahmad Faizal bin Ramli (No. Kad Kuasa: KKM-PKD-0842)\n"
        "Saksi: Nurul Ain binti Zulkifli (No. K/P: 950821-08-6124, Juruwang Kedai)\n"
        "Nama Pengurus Tapak: Tan Wei Ming\n"
        "No. Pasport: A1234567"
    )
    res = redactor.redact(raw, use_ollama=False)
    assert "Mohd Hafizuddin bin Kamaruddin" not in res.redacted_text
    assert "Nurul Ain binti Zulkifli" not in res.redacted_text
    assert "Tan Wei Ming" not in res.redacted_text
    assert "890415-10-5321" not in res.redacted_text
    assert "A1234567" not in res.redacted_text
    assert "Kedai Serbaneka Harmoni Jaya Sdn. Bhd." not in res.redacted_text
    # Pegawai Penyiasat mesti dikekalkan (tidak disamarkan sebagai suspek) & No. 18 alamat tidak jadi PREMIS
    assert "Ahmad Faizal bin Ramli" in res.redacted_text
    assert "No. 18, Jalan PJS 8/9" in res.redacted_text

    restored = redactor.rehydrate(res.redacted_text, res.token_map)
    assert restored == raw


def test_statutory_rag_store_exact_malaysian_sections() -> None:
    store = get_statutory_store()
    assert store.chunk_count >= 20
    acts = {a["akta_code"] for a in store.list_available_acts()}
    assert {"Akta 852", "Akta 281", "Akta 154", "Akta 342", "Akta 593", "Akta 56"}.issubset(acts)

    hits_sitaan = store.search_statutes("senarai benda disita sitaan Akta 852", akta_filter="Akta 852", top_k=3)
    assert any("36" in h.section or "35" in h.section for h in hits_sitaan)

    hits_kompaun = store.search_statutes("kuasa mengkompaun kesalahan P.U. 259", akta_filter="Akta 852", top_k=3)
    assert any("48" in h.section for h in hits_kompaun)

    hits_tifoid = store.search_statutes("vaksinasi suntikan anti tifoid pengendali", akta_filter="Akta 281", top_k=3)
    assert any("31" in h.section for h in hits_tifoid)

    # Uji domain routing RAG bagi soalan luar templat Unit CDC / penyakit berjangkit (tanpa penapis akta)
    hits_cdc = store.search_statutes("kes positif penyakit berjangkit datang pejabat aduan unit cdc boleh kompaun", top_k=3)
    assert hits_cdc
    assert hits_cdc[0].akta_code == "Akta 342"
    assert "(Akta 852)" not in hits_cdc[0].section


def test_audit_ip_detects_wrong_sections_and_date_conflicts() -> None:
    headers = _get_auth_headers()
    # Kes 1 (Akta 852 tanpa Sijil 90A): C12 GAGAL, C11 LULUS (tidak perlukan makmal)
    kes1 = SAMPLE_CASES[0]
    resp1 = client.post(
        "/api/audit-ip",
        headers=headers,
        data={"text": kes1["text"], "akta_utama": kes1["akta_utama"], "use_ollama": "false"},
    )
    assert resp1.status_code == 200
    body1 = resp1.json()
    assert len(body1["criteria_results"]) == 20
    by_code1 = {c["code"]: c for c in body1["criteria_results"]}
    assert by_code1["C12"]["status"] == "GAGAL"
    assert by_code1["C11"]["status"] == "LULUS"
    assert len(body1["ip_folder_checklist"]) == 7

    # Kes 2 (Akta Makanan 1983 lengkap): mesti SEDIA DIHANTAR KE TPR
    kes2 = SAMPLE_CASES[1]
    resp2 = client.post(
        "/api/audit-ip",
        headers=headers,
        data={"text": kes2["text"], "akta_utama": kes2["akta_utama"], "use_ollama": "false"},
    )
    assert resp2.status_code == 200
    body2 = resp2.json()
    assert body2["counts"]["GAGAL"] == 0
    assert body2["readiness_status"] == "SEDIA DIHANTAR KE TPR"

    # Kes 3 (Akta 154): tarikh bercanggah & kuiri kritikal
    kes3 = SAMPLE_CASES[2]
    resp3 = client.post(
        "/api/audit-ip",
        headers=headers,
        data={"text": kes3["text"], "akta_utama": kes3["akta_utama"], "use_ollama": "false"},
    )
    assert resp3.status_code == 200
    body3 = resp3.json()
    by_code3 = {c["code"]: c for c in body3["criteria_results"]}
    assert by_code3["C01"]["status"] == "GAGAL"
    assert body3["counts"]["GAGAL"] >= 3

    # Kes salah petikan seksyen (Seksyen 38 sitaan, Seksyen 44 kompaun, Peraturan 30 tifoid)
    bad_statutes_text = (
        "Tarikh Kejadian: 10 Mei 2026\n"
        "Borang Sitaan Seksyen 38 Akta 852 telah diserahkan.\n"
        "Tawaran kompaun Seksyen 44 Akta 852 dikeluarkan.\n"
        "Kesalahan tiada suntikan anti-tifoid di bawah Peraturan 30 PPKM 2009."
    )
    resp_bad = client.post(
        "/api/audit-ip",
        headers=headers,
        data={"text": bad_statutes_text, "akta_utama": "Akta 852", "use_ollama": "false"},
    )
    assert resp_bad.status_code == 200
    by_bad = {c["code"]: c for c in resp_bad.json()["criteria_results"]}
    assert by_bad["C09"]["status"] == "GAGAL"
    assert by_bad["C16"]["status"] == "GAGAL"
    assert by_bad["C14"]["status"] == "GAGAL"

    # Kes 4 (Akta 342 Tibi lengkap - rujukan PKD/JKNS): mesti lulus tanpa kuiri gagal
    kes4 = SAMPLE_CASES[3]
    resp4 = client.post(
        "/api/audit-ip",
        headers=headers,
        data={"text": kes4["text"], "akta_utama": kes4["akta_utama"], "use_ollama": "false"},
    )
    assert resp4.status_code == 200
    body4 = resp4.json()
    assert body4["counts"]["GAGAL"] == 0

    # Semakan kesilapan sebenar: PPKP tersilap tulis "Seksyen 22(b) Akta 514" untuk kes Tibi
    bad_tb_514_text = (
        "KERTAS MINIT: Minit 2\n"
        "Kes pesakit tibi PTB smear positif cicir rawatan (TBIS 10D).\n"
        "Berdasarkan seksyen 22(b) Akta 514 mohon tindakan mahkamah."
    )
    resp_tb_bad = client.post(
        "/api/audit-ip",
        headers=headers,
        data={"text": bad_tb_514_text, "akta_utama": "Akta 342", "use_ollama": "false"},
    )
    assert resp_tb_bad.status_code == 200
    by_tb_bad = {c["code"]: c for c in resp_tb_bad.json()["criteria_results"]}
    assert by_tb_bad["C14"]["status"] == "GAGAL"
    assert "Akta 342" in by_tb_bad["C14"]["recommendation"]


def test_generate_drafts_uses_real_case_facts_and_official_docx_format() -> None:
    custom_case = (
        "NO. IP: PKD-SBN/UIP/281/2026/099\n"
        "DAERAH: Seremban, Negeri Sembilan\n"
        "Tarikh Kejadian: 19 Disember 2026\n"
        "Masa Kejadian: 11.20 pagi\n"
        "Nama Premis: Restoran Sedap Selalu Enterprise\n"
        "No. SSM: NS0098123-K\n"
        "Alamat Kejadian: No. 5, Jalan Dato Bandar Tunggal, 70000 Seremban\n"
        "Nama Pemilik (OKT): Lim Kah Wai\n"
        "No. K/P: 820312-05-5123\n"
        "Pegawai Penyiasat (IO): PPKP Noraini binti Yusof (Kad Kuasa: KKM-NS-091)\n"
        "Saksi: Kamal bin Kassim (No. K/P: 900101-05-5211, PPKP Pengiring)\n"
        "Kesalahan: membiarkan pengendali makanan bekerja tanpa suntikan anti-tifoid yang sah di bawah Peraturan 31(1) PPKM 2009."
    )
    resp = client.post(
        "/api/generate-draft",
        headers=_get_auth_headers(),
        json={
            "case_text": custom_case,
            "akta_utama": "Akta 281",
            "workflow": "ip_builder",
            "use_ollama": False,
        },
    )
    assert resp.status_code == 200
    draft = resp.json()

    # Pastikan guna fakta sebenar kes ini, BUKAN hardcoded kes lain!
    pertuduhan = draft["borang_114"]["teks_pertuduhan"]
    assert "19 Disember 2026" in pertuduhan
    assert "Restoran Sedap Selalu Enterprise" in pertuduhan
    assert "Seremban" in pertuduhan
    assert "14 Oktober 2026" not in pertuduhan
    assert "Ahmad Faizal" not in draft["fakta_kes"]
    assert "Peraturan 31(1)" in draft["borang_114"]["akta_dan_seksyen"]

    # Semak kandungan fail Word .docx rasmi
    raw_full, _ = generate_docx_by_type("pakej_ip", draft)
    word_doc = Document(io.BytesIO(raw_full))
    full_text = "\n".join(p.text for p in word_doc.paragraphs)
    assert "(Mahkamah 114)" in full_text
    assert "(Mahkamah 143)" in full_text
    assert "KULIT KERTAS SIASATAN (IP)" in full_text
    assert "sepanjang pengetahuan dan kepercayaan saya" in full_text
    assert "SEKSYEN 112(5)" in full_text


def test_tb_akta_342_draft_and_pkd_docx_sections() -> None:
    kes4 = SAMPLE_CASES[3]
    resp = client.post(
        "/api/generate-draft",
        headers=_get_auth_headers(),
        json={
            "case_text": kes4["text"],
            "akta_utama": kes4["akta_utama"],
            "workflow": "ip_builder",
            "use_ollama": False,
        },
    )
    assert resp.status_code == 200
    draft = resp.json()

    assert "Seksyen 22(b)" in draft["borang_114"]["akta_dan_seksyen"]
    assert "Seksyen 24(a)" in draft["borang_114"]["seksyen_hukuman"]
    assert draft["borang_114"]["nama_tertuduh"] == "Muthusamy a/l Ramasamy"
    assert "13 Januari 2026" in draft["borang_114"]["teks_pertuduhan"]
    assert "Tuberkulosis" in draft["borang_114"]["teks_pertuduhan"]
    assert "Harmoni Jaya" not in draft["fakta_kes"]
    assert len(draft.get("kronologi_kes") or []) >= 2
    assert len(draft.get("kertas_cadangan_io") or "") >= 40
    assert "22(b)" in (draft.get("kertas_cadangan_io") or "")
    assert len(draft.get("pemberatan_hukuman") or []) >= 4
    assert draft.get("saman_111", {}).get("nama_oks") == "Muthusamy a/l Ramasamy"

    raw_full, _ = generate_docx_by_type("pakej_ip", draft)
    word_doc = Document(io.BytesIO(raw_full))
    para_text = "\n".join(p.text for p in word_doc.paragraphs)
    table_text = "\n".join(
        cell.text
        for tbl in word_doc.tables
        for row in tbl.rows
        for cell in row.cells
    )
    assert "(Am 6)" in para_text
    assert "KRONOLOGI KES" in para_text
    assert "KERTAS CADANGAN PEGAWAI PENYIASAT" in para_text
    assert "(Mahkamah 111 - Pin. 1/85)" in para_text
    assert "HUJAHAN PEMBERATAN HUKUMAN" in para_text
    assert "No. Butir-Butir Penyiasatan" in table_text

    raw_saman, fname_saman = generate_docx_by_type("saman_111", draft)
    assert fname_saman == "Saman_Mahkamah_111.docx"
    saman_doc = Document(io.BytesIO(raw_saman))
    saman_text = "\n".join(p.text for p in saman_doc.paragraphs)
    assert "(Mahkamah 111 - Pin. 1/85)" in saman_text
    assert "Muthusamy a/l Ramasamy" in saman_text


def test_compound_notice_checker_statutory_limits_and_ic_validation() -> None:
    # Kes Akta 154 amaun RM800 (> RM500) + MyKad bulan 13 + Peraturan 30 tifoid -> mesti GAGAL
    invalid_payload = {
        "no_notis": "KKM/KOM/154/001",
        "nama_penerima": "Tan Wei Ming",
        "no_kp": "841319-01-5523",  # Bulan 13 tidak sah
        "nama_premis": "Tapak Bina Maju Sdn. Bhd.",
        "alamat_kejadian": "Lot 4501, Mukim Tebrau, 81100 Johor Bahru",
        "no_ssm": "201801009821",
        "tarikh_masa": "20/09/2026, 08.40 pagi",
        "peruntukan_undang": "Seksyen 13(1) Akta 154",
        "kesalahan_ringkas": "membiarkan air bertakung membiak larva nyamuk Aedes aegypti di tapak binaan.",
        "amaun_kompaun_rm": "RM 800.00",  # Ultra vires > RM500 Seksyen 25 Akta 154
        "tempoh_bayaran": "14 hari",
        "pegawai_pengeluar": "PPKP Zulhilmi bin Mansor",
        "no_kad_kuasa": "KKM-JHR-112",
        "status_serahan": "enggan_tandatangan",
        "saksi_ppkp": "",
    }
    resp_bad = client.post("/api/check-compound", headers=_get_auth_headers(), json=invalid_payload)
    assert resp_bad.status_code == 200
    body_bad = resp_bad.json()
    by_code = {c["code"]: c for c in body_bad["checks"]}
    assert by_code["K02"]["status"] == "GAGAL"
    assert by_code["K08"]["status"] == "GAGAL"
    assert by_code["K10"]["status"] == "GAGAL"

    # Kes sah Akta 154 (RM500)
    valid_payload = {
        **invalid_payload,
        "no_kp": "840919-01-5523",
        "amaun_kompaun_rm": "RM 500.00",
        "status_serahan": "tandatangan_terima",
    }
    resp_ok = client.post("/api/check-compound", headers=_get_auth_headers(), json=valid_payload)
    assert resp_ok.status_code == 200
    assert resp_ok.json()["counts"]["GAGAL"] == 0


def test_sqlite_cases_crud_and_runtime_settings() -> None:
    headers = _get_auth_headers()
    # Cipta kes baharu dalam SQLite
    resp_create = client.post(
        "/api/cases",
        headers=headers,
        json={
            "no_ip": "PKD-TEST/2026/777",
            "tajuk_kes": "Kes Ujian SQLite",
            "akta_utama": "Akta 852",
            "case_text": "Tarikh Kejadian: 18 November 2026\nNama Premis: Kedai Ujian Enterprise\nKesalahan: pamer vape.",
        },
    )
    assert resp_create.status_code == 200
    created_id = resp_create.json()["case"]["id"]

    resp_list = client.get("/api/cases", headers=headers)
    assert resp_list.status_code == 200
    case_ids = {c["id"] for c in resp_list.json()["cases"]}
    assert created_id in case_ids
    assert "kes-akta-342-tibi" in case_ids

    resp_del = client.delete(f"/api/cases/{created_id}", headers=headers)
    assert resp_del.status_code == 200

    # Uji endpoint GET/POST /api/settings (tanpa merosakkan kunci sebenar jika ada)
    resp_get_set = client.get("/api/settings")
    assert resp_get_set.status_code == 200
    assert "ollama_base_url" in resp_get_set.json()


def test_training_dataset_preparation_masks_pii() -> None:
    redactor = PrivacyRedactor()
    records = build_training_records(SAMPLE_CASES[0]["text"], "kes_uji", redactor, use_ollama=False)
    assert len(records) == 2
    serialized = json.dumps(records, ensure_ascii=False)
    assert "Mohd Hafizuddin bin Kamaruddin" not in serialized
    assert "890415-10-5321" not in serialized
    assert "[SUSPEK_1]" in serialized


def test_officer_account_register_login_profile_and_autofill() -> None:
    import uuid

    resp_demos = client.get("/api/auth/demo-accounts")
    assert resp_demos.status_code == 200
    assert resp_demos.json()["accounts"] == []

    unique_email = f"ppkp.ujian.{uuid.uuid4().hex[:6]}@moh.gov.my"
    resp_reg = client.post(
        "/api/auth/register",
        json={
            "email": unique_email,
            "password": "RahsiaKKM#2026",
            "full_name": "PPKP Mohd Amirul bin Zaki",
            "ic_number": "910412-10-5511",
            "designation": "Penolong Pegawai Kesihatan Persekitaran (PPKP)",
            "grade": "U32",
            "kkm_authority_card_no": "KKM-SEL-U6-991",
            "district_pkd": "Pejabat Kesihatan Daerah Hulu Langat",
            "default_computer_desc": "Komputer Meja HP EliteDesk PKD Hulu Langat",
            "default_camera_desc": "Kamera Digital Canon EOS PKD Hulu Langat",
        },
    )
    assert resp_reg.status_code == 200
    reg_body = resp_reg.json()
    assert reg_body["user"]["email"] == unique_email
    # Sahkan gred lama U32 dinormalkan secara automatik ke gred SSPA U6
    assert reg_body["user"]["grade"] == "U6"
    assert "password_hash" not in reg_body["user"]
    assert reg_body["token"]

    resp_login = client.post(
        "/api/auth/login",
        json={"email": unique_email, "password": "RahsiaKKM#2026"},
    )
    assert resp_login.status_code == 200
    token = resp_login.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp_me = client.get("/api/auth/me", headers=headers)
    assert resp_me.status_code == 200
    assert resp_me.json()["user"]["kkm_authority_card_no"] == "KKM-SEL-U6-991"

    resp_upd = client.put(
        "/api/auth/profile",
        headers=headers,
        json={"grade": "U7"},
    )
    assert resp_upd.status_code == 200
    assert resp_upd.json()["user"]["grade"] == "U7"

    # Pastikan janaan draf mengisi profil & perkakasan S.90A pegawai yang log masuk secara automatik
    resp_draft = client.post(
        "/api/generate-draft",
        headers=headers,
        json={
            "case_text": "Tarikh Kejadian: 18 November 2026\nNama Premis: Kedai Runcit Ujian\nKesalahan: pamer vape.",
            "akta_utama": "Akta 852",
            "workflow": "ip_builder",
            "use_ollama": False,
        },
    )
    assert resp_draft.status_code == 200
    s90 = resp_draft.json()["sijil_90a"]
    assert s90["peranti_kamera"] == "Kamera Digital Canon EOS PKD Hulu Langat"
    assert s90["perihal_komputer"] == "Komputer Meja HP EliteDesk PKD Hulu Langat"

    resp_out = client.post("/api/auth/logout", headers=headers)
    assert resp_out.status_code == 200
    assert resp_out.json()["logged_out"] is True
    assert client.get("/api/auth/me", headers=headers).status_code == 401


def test_uip_advisor_scenarios_and_consult() -> None:
    import time

    headers = _get_auth_headers()
    resp_list = client.get("/api/advisor/scenarios", headers=headers)
    assert resp_list.status_code == 200
    scenarios = resp_list.json()["scenarios"]
    assert len(scenarios) == 17
    acts = {s["akta_utama"] for s in scenarios}
    assert {"Akta 852", "Akta 281", "Akta 154", "Akta 342"}.issubset(acts)

    # Uji klik templat terus (pantasklik tapak binaan Akta 154)
    resp_tapak = client.post(
        "/api/advisor/consult",
        headers=headers,
        json={
            "question": "Tapak pembinaan membiak Aedes, boleh kompaun atau buka IP?",
            "akta_hint": "Akta 154",
            "scenario_id": "ak154_aedes_tapak_bina",
        },
    )
    assert resp_tapak.status_code == 200
    tapak_body = resp_tapak.json()
    assert tapak_body["sesuai_buka_ip"] is True
    assert tapak_body["akta_disyorkan"] == "Akta 154"
    assert len(tapak_body["sop_lapangan"]) >= 3
    assert len(tapak_body["eksibit_wajib"]) >= 3
    assert len(tapak_body["perangkap_kesilapan"]) >= 1
    assert "draf_teks_kes_cadangan" in tapak_body

    # Uji soalan seperti tangkapan skrin pengguna: budak sekolah hisap rokok tepi jalan (Mod Pantas < 2s)
    t0 = time.monotonic()
    resp_obd = client.post(
        "/api/advisor/consult",
        headers=headers,
        json={
            "question": "ada budak sekolah hisap rokok tepi jalan",
            "akta_hint": "Semua",
            "use_ai": False,
        },
    )
    elapsed_obd = time.monotonic() - t0
    assert resp_obd.status_code == 200
    obd_body = resp_obd.json()
    assert obd_body["scenario_id"] == "ak852_obd_merokok_tepi_jalan"
    assert "17(1)" in json.dumps(obd_body["cadangan_pertuduhan"], ensure_ascii=False)
    assert "16(2)" not in json.dumps(obd_body["cadangan_pertuduhan"], ensure_ascii=False)
    assert elapsed_obd < 2.0

    # Uji kes Tibi PTB Smear Negatif (AFB Negatif) enggan mula rawatan TIDAK disalah tafsir sebagai Smear Positif
    resp_tb_neg = client.post(
        "/api/advisor/consult",
        headers=headers,
        json={
            "question": "kes yang disaring tibi telah diminta untuk mula rawatan ptb smear negatif - afb negatif namun taknak mulakan rawatan",
            "akta_hint": "Semua",
            "use_ai": False,
        },
    )
    assert resp_tb_neg.status_code == 200
    tb_neg_body = resp_tb_neg.json()
    assert tb_neg_body["scenario_id"] == "ak342_tibi_smear_negatif_enggan_mula"
    assert tb_neg_body["sesuai_buka_ip"] is False
    assert "Smear Positif" not in tb_neg_body["tajuk_nasihat"]
    assert "15(1)" in json.dumps(tb_neg_body["cadangan_pertuduhan"], ensure_ascii=False)

    # Uji soalan tangkapan skrin pengguna: kes COVID-19 positif datang kerja diadukan majikan ke Unit CDC
    resp_covid = client.post(
        "/api/advisor/consult",
        headers=headers,
        json={
            "question": "ada kes covid positif datng kerja. majikan adukan kepada unit cdc. boleh kompaun ke?",
            "akta_hint": "Semua",
            "use_ai": False,
        },
    )
    assert resp_covid.status_code == 200
    covid_body = resp_covid.json()
    assert covid_body["scenario_id"] == "ak342_covid_positif_tempat_kerja"
    assert covid_body["akta_disyorkan"] == "Akta 342"
    assert covid_body["sesuai_buka_ip"] is False
    covid_dump = json.dumps(covid_body, ensure_ascii=False)
    assert "15 Julai 2024" in covid_dump
    assert "139/2025" in covid_dump
    assert "Akta 852" not in covid_body["tajuk_nasihat"]

    # Uji soalan di luar templat tetap tidak terperangkap pada kad pertama (ak852_pamer_vape)
    resp_unmatched = client.post(
        "/api/advisor/consult",
        headers=headers,
        json={
            "question": "adakah pegawai kesihatan berkuasa memasuki gudang untuk pemeriksaan bahan bercetak import tanpa waran?",
            "akta_hint": "Semua",
            "use_ai": False,
        },
    )
    assert resp_unmatched.status_code == 200
    unmatched_body = resp_unmatched.json()
    assert unmatched_body["scenario_id"] == "rag_custom_query"
    assert "(Akta 852) (Akta 852)" not in json.dumps(unmatched_body, ensure_ascii=False)

    # Uji gabungan multi-kesalahan (< 2s): restoran ada najis tikus + pekerja tiada tifoid
    t1 = time.monotonic()
    resp_combo = client.post(
        "/api/advisor/consult",
        headers=headers,
        json={
            "question": "Restoran kotor ada najis tikus di dapur dan 2 pekerja tiada suntikan tifoid",
            "akta_hint": "Semua",
            "use_ai": False,
        },
    )
    elapsed_combo = time.monotonic() - t1
    assert resp_combo.status_code == 200
    combo_body = resp_combo.json()
    combo_charges = json.dumps(combo_body["cadangan_pertuduhan"], ensure_ascii=False)
    assert "11(1)" in combo_charges
    assert "31(1)" in combo_charges
    assert elapsed_combo < 2.0

    # Uji soalan bebas (pengendali makanan tiada suntikan tifoid)
    resp_free = client.post(
        "/api/advisor/consult",
        headers=headers,
        json={
            "question": "Tukang masak restoran tiada suntikan tifoid dan tiada sijil LPM, nak caj peraturan mana?",
            "akta_hint": "Akta 281",
            "use_ai": False,
        },
    )
    assert resp_free.status_code == 200
    free_body = resp_free.json()
    assert free_body["akta_disyorkan"] == "Akta 281"
    combined_charges = json.dumps(free_body["cadangan_pertuduhan"], ensure_ascii=False)
    assert "31" in combined_charges


def test_uip_advisor_use_ai_runs_even_with_scenario_id_and_fallback_diag(monkeypatch) -> None:
    """Memastikan use_ai=True memanggil Gemini walaupun scenario_id dihantar & memparse JSON fallback."""
    from types import SimpleNamespace
    from backend.main import advisor_service, router_service

    advisor_service.clear_cache()
    headers = _get_auth_headers()

    captured_gc: dict = {}

    class _FakeInteractions:
        def create(self, **kwargs):
            raise RuntimeError("Simulasi Interactions gagal sementara")

    class _FakeModels:
        def generate_content(self, *, model, contents, config):
            captured_gc["model"] = model
            captured_gc["has_schema"] = bool(getattr(config, "response_json_schema", None))
            return SimpleNamespace(
                text=(
                    "```json\n"
                    + json.dumps(
                        {
                            "tajuk_nasihat": "Analisis AI Khusus: PTB Smear Negatif Enggan Mula Rawatan",
                            "keputusan_tindakan": "SAHKAN DIAGNOSIS MO/FMS & SERAH NOTIS S.15(1)/S.14 SEBELUM IP",
                            "sesuai_buka_ip": False,
                            "alasan_keputusan": "Keputusan makmal AFB negatif belum membolehkan dakwaan S.22(b) tanpa pengesahan klinikal dan serahan notis bertulis.",
                            "cadangan_pertuduhan": [
                                {
                                    "perihal": "Perintah Pengawasan/Ujian Lanjutan",
                                    "seksyen_kesalahan": "Seksyen 15(1) Akta 342",
                                    "seksyen_hukuman": "Seksyen 24 Akta 342",
                                    "hukuman_maksimum": "Denda maks RM10,000 atau penjara 2 tahun",
                                    "boleh_kompaun": "Tidak sesuai dibuka IP S.22(b) sebelum notis bertulis diingkari",
                                }
                            ],
                            "sop_lapangan": ["Rujuk MO/FMS sahkan GeneXpert/Kultur TBIS 20C."],
                            "eksibit_wajib": ["Laporan Klinikal MO/FMS & TBIS 20C."],
                            "perangkap_kesilapan": ["Jangan tuduh sebagai kes PTB Smear Positif cicir rawatan."],
                            "templat_ringkas": "Siasatan kes PTB Smear Negatif enggan mula rawatan di bawah Akta 342.",
                        }
                    )
                    + "\n```"
                )
            )

    fake_client = SimpleNamespace(interactions=_FakeInteractions(), models=_FakeModels())
    monkeypatch.setattr(router_service, "_genai_client", fake_client)

    resp_ai = client.post(
        "/api/advisor/consult",
        headers=headers,
        json={
            "question": "kes yang disaring tibi telah diminta untuk mula rawatan ptb smear negatif - afb negatif namun taknak mulakan rawatan",
            "akta_hint": "Semua",
            "scenario_id": "ak342_tibi_smear_negatif_enggan_mula",
            "use_ai": True,
        },
    )
    assert resp_ai.status_code == 200
    body = resp_ai.json()
    assert body["ai_attempted"] is True
    assert body["ai_succeeded"] is True
    assert body["fallback_reason"] is None
    assert "Analisis AI Khusus" in body["tajuk_nasihat"]
    assert captured_gc.get("has_schema") is True
    assert "Gemini API" in body["engine_used"]

    # Uji jika semua model gagal -> fallback_reason dipulangkan secara telus (tidak disenyapkan)
    advisor_service.clear_cache()

    class _AlwaysFailModels:
        def generate_content(self, **kwargs):
            raise TimeoutError("APITimeoutError: Request timed out. This is a client-side timeout")

    monkeypatch.setattr(
        router_service,
        "_genai_client",
        SimpleNamespace(interactions=_FakeInteractions(), models=_AlwaysFailModels()),
    )
    resp_fail = client.post(
        "/api/advisor/consult",
        headers=headers,
        json={
            "question": "Soalan ujian apabila semua model gagal buat sementara waktu",
            "akta_hint": "Akta 342",
            "use_ai": True,
        },
    )
    assert resp_fail.status_code == 200
    fail_body = resp_fail.json()
    assert fail_body["ai_attempted"] is True
    assert fail_body["ai_succeeded"] is False
    assert fail_body["fallback_reason"]
    assert "Pelayan AI" in fail_body["fallback_reason"]
    assert "APITimeoutError" not in fail_body["fallback_reason"]
    assert "client-side timeout" not in fail_body["fallback_reason"]
    advisor_service.clear_cache()


def test_google_auth_requires_real_oauth_token_and_no_demo_accounts(monkeypatch) -> None:
    import uuid
    import httpx

    # 1. Pastikan tiada akaun demo/palsu dalam mod produksi sebenar
    resp_demos = client.get("/api/auth/demo-accounts")
    assert resp_demos.status_code == 200
    assert resp_demos.json()["accounts"] == []

    # 2. Pastikan log masuk Google tanpa token OAuth rasmi DITOLAK (tiada pintasan emel palsu)
    resp_no_token = client.post("/api/auth/google", json={})
    assert resp_no_token.status_code == 400

    # 3. Uji aliran pengesahan token rasmi Google (tokeninfo id_token + userinfo access_token)
    from backend.core.config import DEFAULT_GOOGLE_CLIENT_ID

    g_email = f"ppkp.nerus.{uuid.uuid4().hex[:6]}@gmail.com"
    dev_headers = _get_dev_admin_headers()
    client.post("/api/settings", headers=dev_headers, json={"google_client_id": ""})

    class _MockResp:
        def __init__(self, status_code: int, payload: dict) -> None:
            self.status_code = status_code
            self._payload = payload

        def json(self) -> dict:
            return self._payload

    def _fake_httpx_get(url: str, **kwargs):
        if "tokeninfo" in url:
            return _MockResp(
                200,
                {
                    "email": g_email,
                    "email_verified": "true",
                    "name": "PPKP Syafiqah binti Mohd Noor",
                },
            )
        if "userinfo" in url:
            return _MockResp(
                200,
                {
                    "email": g_email,
                    "email_verified": True,
                    "name": "PPKP Syafiqah binti Mohd Noor",
                },
            )
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(httpx, "get", _fake_httpx_get)

    resp_first = client.post(
        "/api/auth/google",
        json={
            "id_token": "real-google-id-token-placeholder",
            "kkm_authority_card_no": "KKM/TRG/PKD-KN/0555",
            "grade": "U6",
        },
    )
    assert resp_first.status_code == 200
    b1 = resp_first.json()
    assert b1["is_new_account"] is True
    assert b1["user"]["email"] == g_email
    assert b1["user"]["grade"] == "U6"
    assert b1["user"]["is_dev_admin"] is False
    assert "Kuala Nerus" in b1["user"]["district_pkd"]
    assert "Terengganu" in b1["user"]["state_jkn"]
    assert b1["token"]

    # Log masuk kali kedua guna access_token OAuth2 popup -> guna akaun sedia ada
    resp_second = client.post(
        "/api/auth/google",
        json={"access_token": "ya29.real-access-token"},
    )
    assert resp_second.status_code == 200
    b2 = resp_second.json()
    assert b2["is_new_account"] is False
    assert b2["user"]["full_name"] == "PPKP Syafiqah binti Mohd Noor"
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {b2['token']}"}).status_code == 200
    client.post("/api/settings", headers=dev_headers, json={"google_client_id": DEFAULT_GOOGLE_CLIENT_ID})


def test_dev_overview_tracks_who_uses_what_and_api_costs(monkeypatch) -> None:
    import uuid
    import httpx
    from backend.core.config import DEFAULT_GOOGLE_CLIENT_ID

    # 0. Sahkan pengguna biasa (bukan zero4eleven@gmail.com) disekat HTTP 403 daripada Konsol Dev & Tetapan
    regular_headers = _get_auth_headers()
    assert client.get("/api/dev/overview", headers=regular_headers).status_code == 403
    assert client.post("/api/settings", headers=regular_headers, json={"google_client_id": "x"}).status_code == 403

    # 1. Uji simpan & dapatkan google_client_id menggunakan akaun pembangun Ihsan Syairazy (zero4eleven@gmail.com)
    dev_headers = _get_dev_admin_headers()
    client_id_test = f"123456-{uuid.uuid4().hex[:6]}.apps.googleusercontent.com"
    resp_save = client.post("/api/settings", headers=dev_headers, json={"google_client_id": client_id_test})
    assert resp_save.status_code == 200
    assert resp_save.json()["settings"]["google_client_id"] == client_id_test
    assert resp_save.json()["settings"]["google_client_id_configured"] is True

    # 2. Daftar / log masuk pengguna Google sebenar dengan token yang disahkan aud-nya
    g_email = f"devcheck.{uuid.uuid4().hex[:6]}@gmail.com"

    class _MockGoogleTokenResp:
        status_code = 200

        def json(self) -> dict:
            return {
                "email": g_email,
                "email_verified": "true",
                "name": "PPKP Zulkifli bin Rashid",
                "aud": client_id_test,
            }

    monkeypatch.setattr(httpx, "get", lambda url, **kwargs: _MockGoogleTokenResp())

    auth_res = client.post(
        "/api/auth/google",
        json={
            "id_token": "verified-jwt-for-client-id",
            "kkm_authority_card_no": "KKM/TRG/PKD-KN/0912",
        },
    ).json()
    token = auth_res["token"]

    consult_res = client.post(
        "/api/advisor/consult",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "question": "Kedai pamer vape terbuka dan jual kepada pelajar sekolah",
            "akta_hint": "Akta 852",
            "use_ai": False,
        },
    )
    assert consult_res.status_code == 200

    # 3. Semak /api/dev/overview dibenarkan untuk zero4eleven@gmail.com dan disekat 403 untuk pengguna Google lain
    assert client.get("/api/dev/overview", headers={"Authorization": f"Bearer {token}"}).status_code == 403
    dev_resp = client.get("/api/dev/overview", headers=dev_headers)
    assert dev_resp.status_code == 200
    overview = dev_resp.json()
    assert overview["developer"] == "g.dev/syrzy"
    assert overview["google_client_id_configured"] is True

    user_emails = {u["email"] for u in overview["users"]}
    assert g_email in user_emails

    # Sahkan aktiviti LOGIN_GOOGLE dan TANYA_PAKAR_UIP direkodkan di bawah pegawai itu
    matching_acts = [a for a in overview["activities"] if a["user_email"] == g_email]
    act_types = {a["action_type"] for a in matching_acts}
    assert "LOGIN_GOOGLE" in act_types
    assert "TANYA_PAKAR_UIP" in act_types
    assert overview["summary"]["total_actions"] >= 2
    assert overview["summary"]["local_free_calls"] >= 1
    assert len(overview["pricing_reference"]) >= 4

    # Pulihkan google_client_id kepada Client ID lalai
    client.post("/api/settings", headers=dev_headers, json={"google_client_id": DEFAULT_GOOGLE_CLIENT_ID})


def test_unauthenticated_requests_are_blocked_401() -> None:
    assert client.get("/api/cases").status_code == 401
    assert client.post("/api/cases", json={"case_text": "test"}).status_code == 401
    assert client.post("/api/audit-ip", data={"text": "test"}).status_code == 401
    assert client.post("/api/generate-draft", json={"case_text": "test"}).status_code == 401
    assert client.post("/api/advisor/consult", json={"question": "test"}).status_code == 401
    assert client.get("/api/dev/overview").status_code == 401
    assert client.post("/api/settings", json={"ollama_model": "gemma3:12b"}).status_code == 401


def test_cloud_run_healthz_and_postgres_adapter(monkeypatch) -> None:
    import uuid
    import httpx
    from backend.core.config import DEFAULT_GOOGLE_CLIENT_ID, _normalize_database_url
    from backend.core.database import _PgConnAdapter

    for path in ("/healthz", "/api/health"):
        resp = client.get(path)
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok", "db": "sqlite"}

    assert (
        _PgConnAdapter._translate_sql("SELECT * FROM users WHERE email = ? AND id = ?")
        == "SELECT * FROM users WHERE email = %s AND id = %s"
    )
    assert (
        _PgConnAdapter._translate_sql(
            "DELETE FROM activity_logs WHERE id LIKE 'act-seed-%' AND user_id = ?"
        )
        == "DELETE FROM activity_logs WHERE id LIKE 'act-seed-%%' AND user_id = %s"
    )

    # Uji execute() tanpa params tidak menghantar tuple kosong ke psycopg3
    recorded_calls: list[tuple[Any, ...]] = []

    class _FakeCur:
        rowcount = 1

        def fetchone(self):
            return None

        def fetchall(self):
            return []

    class _FakeRawConn:
        def execute(self, *args):
            recorded_calls.append(args)
            return _FakeCur()

    pg_adapter = object.__new__(_PgConnAdapter)
    pg_adapter._conn = _FakeRawConn()
    pg_adapter.execute("DELETE FROM activity_logs WHERE id LIKE 'act-seed-%'")
    pg_adapter.execute("SELECT * FROM users WHERE email = ?", ("test@moh.gov.my",))
    assert recorded_calls[0] == ("DELETE FROM activity_logs WHERE id LIKE 'act-seed-%'",)
    assert recorded_calls[1] == ("SELECT * FROM users WHERE email = %s", ("test@moh.gov.my",))

    # Uji _normalize_database_url membersihkan 'psql ', tanda petik, & fallback alias
    for env_key in ("DATABASE_URL", "NEON_DATABASE_URL", "POSTGRES_URL", "POSTGRESQL_URL"):
        monkeypatch.delenv(env_key, raising=False)

    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@ep-demo.aws.neon.tech/neondb?sslmode=require")
    assert _normalize_database_url("DATABASE_URL") == "postgresql://user:pass@ep-demo.aws.neon.tech/neondb?sslmode=require"

    monkeypatch.setenv("DATABASE_URL", "psql 'postgresql://user:pass@ep-demo.aws.neon.tech/neondb?sslmode=require'")
    assert _normalize_database_url("DATABASE_URL") == "postgresql://user:pass@ep-demo.aws.neon.tech/neondb?sslmode=require"

    monkeypatch.setenv("DATABASE_URL", '"postgresql://user:pass@ep-demo.aws.neon.tech/neondb"')
    assert _normalize_database_url("DATABASE_URL") == "postgresql://user:pass@ep-demo.aws.neon.tech/neondb"

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("NEON_DATABASE_URL", "postgres://user:pass@ep-alt.aws.neon.tech/neondb")
    assert (
        _normalize_database_url("DATABASE_URL", "NEON_DATABASE_URL", "POSTGRES_URL", "POSTGRESQL_URL")
        == "postgres://user:pass@ep-alt.aws.neon.tech/neondb"
    )

    # Uji nama Google pendek (cth. "Al") tidak gagal sekatan 3 aksara
    short_email = f"al.{uuid.uuid4().hex[:6]}@gmail.com"

    class _ShortResp:
        status_code = 200

        def json(self) -> dict:
            return {
                "email": short_email,
                "email_verified": "true",
                "name": "Al",
                "aud": DEFAULT_GOOGLE_CLIENT_ID,
            }

    monkeypatch.setattr(httpx, "get", lambda url, **kwargs: _ShortResp())
    resp_short = client.post("/api/auth/google", json={"id_token": "tok-short"})
    assert resp_short.status_code == 200
    assert resp_short.json()["user"]["email"] == short_email


def test_dev_vault_archives_users_questions_docs_and_enforces_exclusive_access(monkeypatch) -> None:
    import uuid
    import zipfile
    import httpx
    from backend.core.config import settings

    # 1. Tanpa token -> 401 pada semua endpoint Arkib & Bucket Dev
    assert client.get("/api/dev/vault/health").status_code == 401
    assert client.get("/api/dev/vault/records").status_code == 401
    assert client.post("/api/dev/vault/export", json={"mode": "redacted"}).status_code == 401
    assert client.post("/api/dev/vault/retry-s3-sync").status_code == 401

    # 2. Pegawai biasa daftar & guna sistem -> disekat 403 daripada /api/dev/vault/* dan /api/rag/ingest
    unique_email = f"ppkp.vault.{uuid.uuid4().hex[:6]}@moh.gov.my"
    reg_res = client.post(
        "/api/auth/register",
        json={
            "email": unique_email,
            "password": "VaultUserKKM#2026",
            "full_name": "PPKP Nurul Huda binti Ismail",
            "ic_number": "920518-11-5214",
            "grade": "U5",
            "kkm_authority_card_no": "KKM-TRG-9988",
            "district_pkd": "Pejabat Kesihatan Daerah Kuala Nerus",
        },
    )
    assert reg_res.status_code == 200
    user_token = reg_res.json()["token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}

    assert client.get("/api/dev/vault/health", headers=user_headers).status_code == 403
    assert client.get("/api/dev/vault/records", headers=user_headers).status_code == 403
    assert client.post("/api/dev/vault/export", headers=user_headers, json={"mode": "redacted"}).status_code == 403
    assert client.post("/api/dev/vault/retry-s3-sync", headers=user_headers).status_code == 403
    assert (
        client.post(
            "/api/rag/ingest",
            headers=user_headers,
            files={"file": ("akta_test.txt", b"teks ujian", "text/plain")},
        ).status_code
        == 403
    )

    # Kemaskini profil
    upd_res = client.put("/api/auth/profile", headers=user_headers, json={"grade": "U6"})
    assert upd_res.status_code == 200

    # Tanya Pakar UIP
    consult_res = client.post(
        "/api/advisor/consult",
        headers=user_headers,
        json={
            "question": "Kedai makan di Kuala Nerus jual vape kepada remaja bawah 18 tahun",
            "akta_hint": "Akta 852",
            "use_ai": False,
        },
    )
    assert consult_res.status_code == 200

    # Muat naik PDF sebenar untuk Audit IP
    pdf_doc = fitz.open()
    page = pdf_doc.new_page()
    page.insert_text(
        (72, 72),
        "KERTAS SIASATAN UIP PKD KUALA NERUS\n"
        "Tarikh Kejadian: 12 November 2026\n"
        "Nama Premis: Kedai Vape Nerus Jaya Enterprise\n"
        "Nama Suspek (OKT): Ahmad Kamil bin Othman\n"
        "No. K/P: 880102-11-5011\n"
        "Pegawai Penyiasat (IO): PPKP Nurul Huda binti Ismail\n"
        "Kesalahan: pamer produk merokok secara terbuka di bawah Seksyen 10(1) Akta 852.",
    )
    pdf_bytes = pdf_doc.tobytes()
    pdf_doc.close()

    audit_res = client.post(
        "/api/audit-ip",
        headers=user_headers,
        data={"akta_utama": "Akta 852", "use_ollama": "false", "fast_mode": "true"},
        files={"file": ("ip_ujian_nerus.pdf", pdf_bytes, "application/pdf")},
    )
    assert audit_res.status_code == 200

    # Muat naik imej PNG sebenar untuk Ekstrak Bukti OCR
    png_1x1 = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc```\x00\x00"
        b"\x00\x04\x00\x01\xf6\x178U\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    ocr_res = client.post(
        "/api/extract-evidence",
        headers=user_headers,
        data={"doc_hint": "gambar_premis"},
        files={"file": ("bukti_premis_nerus.png", png_1x1, "image/png")},
    )
    assert ocr_res.status_code == 200

    # Jana Draf & Semak Kompaun & Eksport DOCX
    draft_res = client.post(
        "/api/generate-draft",
        headers=user_headers,
        json={
            "case_text": "Tarikh Kejadian: 12 November 2026\nNama Premis: Kedai Vape Nerus Jaya Enterprise\nNama Pemilik (OKT): Ahmad Kamil bin Othman\nNo. K/P: 880102-11-5011\nKesalahan: pamer vape secara terbuka.",
            "akta_utama": "Akta 852",
            "workflow": "ip_builder",
            "use_ollama": False,
        },
    )
    assert draft_res.status_code == 200

    comp_res = client.post(
        "/api/check-compound",
        headers=user_headers,
        json={
            "no_notis": "KKM/KOM/852/099",
            "nama_penerima": "Ahmad Kamil bin Othman",
            "no_kp": "880102-11-5011",
            "nama_premis": "Kedai Vape Nerus Jaya Enterprise",
            "peruntukan_undang": "Seksyen 10(1) Akta 852",
            "amaun_kompaun_rm": "RM 500.00",
        },
    )
    assert comp_res.status_code == 200

    docx_res = client.post(
        "/api/export-docx",
        headers=user_headers,
        json={"doc_type": "borang_114", "payload": draft_res.json()},
    )
    assert docx_res.status_code == 200

    # 3. Akses eksklusif Pembangun (zero4eleven@gmail.com) menggunakan header X-Auth-Token & Bearer
    dev_headers = _get_dev_admin_headers()
    dev_token = dev_headers["Authorization"].split(" ", 1)[1]
    x_auth_headers = {"X-Auth-Token": dev_token}

    health_res = client.get("/api/dev/vault/health", headers=x_auth_headers)
    assert health_res.status_code == 200
    health = health_res.json()
    assert health["is_private_locked"] is True
    assert "zero4eleven@gmail.com" in health["allowed_dev_emails"]
    assert health["total_records"] >= 7
    assert health["total_files"] >= 3
    assert "aws_secret_access_key" not in json.dumps(health).lower()

    list_res = client.get(
        "/api/dev/vault/records",
        headers=dev_headers,
        params={"user_email": unique_email, "limit": 50},
    )
    assert list_res.status_code == 200
    items = list_res.json()["items"]
    actions_archived = {i["action_type"] for i in items}
    assert {
        "REGISTER_ACCOUNT",
        "UPDATE_PROFILE",
        "TANYA_PAKAR_UIP",
        "AUDIT_IP_20",
        "EKSTRAK_BUKTI_OCR",
        "JANA_DRAF_IP",
        "SEMAK_KOMPAUN",
        "EXPORT_DOCX",
    }.issubset(actions_archived)

    # Semak rekod pendaftaran tidak menyimpan kata laluan / token & IC disamarkan
    reg_item = next(i for i in items if i["action_type"] == "REGISTER_ACCOUNT")
    reg_detail = client.get(f"/api/dev/vault/records/{reg_item['id']}", headers=dev_headers).json()
    reg_dump = json.dumps(reg_detail, ensure_ascii=False)
    assert "VaultUserKKM#2026" not in reg_dump
    assert "password_hash" not in reg_dump
    assert user_token not in reg_dump

    # Semak rekod Audit IP PDF: muat turun fail asal mesti 100% sepadan & versi PDPA menutup No. K/P
    pdf_item = next(i for i in items if i["action_type"] == "AUDIT_IP_20")
    pdf_detail = client.get(f"/api/dev/vault/records/{pdf_item['id']}", headers=dev_headers).json()
    assert "880102-11-5011" not in pdf_detail["redacted_input_text"]
    assert "880102-11-5011" in pdf_detail["raw_input_text"]
    assert pdf_detail["file_attachment"]["original_filename"] == "ip_ujian_nerus.pdf"

    dl_pdf = client.get(f"/api/dev/vault/records/{pdf_item['id']}/file", headers=x_auth_headers)
    assert dl_pdf.status_code == 200
    assert dl_pdf.content == pdf_bytes
    assert dl_pdf.headers.get("x-content-type-options") == "nosniff"
    assert "attachment" in (dl_pdf.headers.get("content-disposition") or "").lower()

    # Semak Eksport Bundle ZIP (mod redacted & mod full)
    exp_redacted = client.post(
        "/api/dev/vault/export",
        headers=dev_headers,
        json={"mode": "redacted", "format": "zip", "user_email": unique_email},
    )
    assert exp_redacted.status_code == 200
    with zipfile.ZipFile(io.BytesIO(exp_redacted.content)) as zf:
        names = set(zf.namelist())
        assert {"manifest.json", "users_registered.json", "records.jsonl"}.issubset(names)
        assert not any(n.startswith("attachments/") for n in names)
        users_text = zf.read("users_registered.json").decode("utf-8")
        assert "920518-11-5214" not in users_text
        assert "password_hash" not in users_text

    exp_full = client.post(
        "/api/dev/vault/export",
        headers=dev_headers,
        json={"mode": "full", "format": "zip", "user_email": unique_email},
    )
    assert exp_full.status_code == 200
    with zipfile.ZipFile(io.BytesIO(exp_full.content)) as zf:
        names = set(zf.namelist())
        assert any(n.endswith("ip_ujian_nerus.pdf") for n in names)

    # 4. Uji klien S3 SigV4 (Neon Object Storage) + fallback non-fatal jika S3 gagal
    s3_calls = []

    class _FakeS3Resp:
        def __init__(self, code: int = 200) -> None:
            self.status_code = code
            self.text = ""
            self.content = b""

    def _fake_s3_put(url: str, content: bytes = b"", headers: dict | None = None, **kwargs):
        s3_calls.append({"url": url, "headers": headers or {}, "len": len(content)})
        return _FakeS3Resp(200)

    monkeypatch.setattr(settings, "dev_archive_s3_endpoint", "https://br-test.storage.ap-southeast-1.aws.neon.tech")
    monkeypatch.setattr(settings, "dev_archive_s3_access_key", "nak_test_id")
    monkeypatch.setattr(settings, "dev_archive_s3_secret_key", "nak_test_secret")
    monkeypatch.setattr(settings, "dev_archive_bucket", "dev-vault")
    monkeypatch.setattr(httpx, "put", _fake_s3_put)

    q2 = client.post(
        "/api/advisor/consult",
        headers=user_headers,
        json={"question": "Ujian S3 Neon Object Storage sigv4", "akta_hint": "Akta 154", "use_ai": False},
    )
    assert q2.status_code == 200
    assert len(s3_calls) >= 1
    assert "AWS4-HMAC-SHA256" in s3_calls[0]["headers"].get("Authorization", "")
    assert "/dev-vault/" in s3_calls[0]["url"]

    # Uji fallback non-fatal apabila S3 memulangkan 500
    monkeypatch.setattr(httpx, "put", lambda url, **kwargs: _FakeS3Resp(500))
    q3 = client.post(
        "/api/advisor/consult",
        headers=user_headers,
        json={"question": "Ujian fallback jika S3 terputus", "akta_hint": "Akta 281", "use_ai": False},
    )
    assert q3.status_code == 200
    monkeypatch.setattr(settings, "dev_archive_s3_endpoint", "")
    monkeypatch.setattr(settings, "dev_archive_s3_access_key", "")
    monkeypatch.setattr(settings, "dev_archive_s3_secret_key", "")


def test_advisor_answered_questions_grouped_by_act_and_redacted() -> None:
    import uuid

    # 1. Tanpa token -> 401
    assert client.get("/api/advisor/answered").status_code == 401

    def _register_officer(tag: str) -> tuple[str, dict[str, str]]:
        email = f"ppkp.{tag}.{uuid.uuid4().hex[:6]}@moh.gov.my"
        reg = client.post(
            "/api/auth/register",
            json={
                "email": email,
                "password": "AdvisorQAPass#2026",
                "full_name": f"PPKP {tag.upper()} Ujian",
            },
        )
        assert reg.status_code == 200
        return email, {"Authorization": f"Bearer {reg.json()['token']}"}

    email_a, headers_a = _register_officer("a")
    email_b, headers_b = _register_officer("b")
    _email_c, headers_c = _register_officer("c")

    # Pengguna A tanya Akta 852 (mengandungi PII OKT & No. K/P sintetik) + Akta 154
    q_852 = "OKT: Ali bin Baba No. K/P 900101-11-5123 pamer vape secara terbuka di kaunter kedai"
    r_852 = client.post(
        "/api/advisor/consult",
        headers=headers_a,
        json={"question": q_852, "akta_hint": "Semua", "use_ai": False},
    )
    assert r_852.status_code == 200

    q_154 = "Tapak pembinaan membiak nyamuk Aedes aegypti boleh terus kompaun ke?"
    r_154_a = client.post(
        "/api/advisor/consult",
        headers=headers_a,
        json={"question": q_154, "akta_hint": "Semua", "use_ai": False},
    )
    assert r_154_a.status_code == 200

    # Pengguna B tanya Akta 281 + Akta 342 + ulang soalan Akta 154 (uji penyahduplikasian ask_count)
    r_281 = client.post(
        "/api/advisor/consult",
        headers=headers_b,
        json={
            "question": "Pengendali makanan restoran kotor tiada suntikan tifoid, nak guna peraturan mana?",
            "akta_hint": "Semua",
            "use_ai": False,
        },
    )
    assert r_281.status_code == 200

    q_342 = "ada kes covid positif datng kerja. majikan adukan kepada unit cdc. boleh kompaun ke?"
    r_342 = client.post(
        "/api/advisor/consult",
        headers=headers_b,
        json={"question": q_342, "akta_hint": "Semua", "use_ai": False},
    )
    assert r_342.status_code == 200

    r_154_b = client.post(
        "/api/advisor/consult",
        headers=headers_b,
        json={"question": q_154, "akta_hint": "Semua", "use_ai": False},
    )
    assert r_154_b.status_code == 200

    # Pengguna C baca himpunan soalan telah dijawab daripada semua pengguna & dikelaskan mengikut Akta
    resp_all = client.get("/api/advisor/answered", headers=headers_c)
    assert resp_all.status_code == 200
    body = resp_all.json()
    assert body["total_questions"] >= 4
    assert body["total_asks"] >= 5

    groups_by_code = {g["akta_code"]: g for g in body["groups"]}
    for code in ("Akta 852", "Akta 281", "Akta 154", "Akta 342"):
        assert code in groups_by_code
        assert groups_by_code[code]["count"] >= 1
        assert body["act_counts"][code] >= 1

    # Pastikan soalan berulang Akta 154 digabung dan ask_count >= 2
    ak154_item = next(
        it for it in groups_by_code["Akta 154"]["items"] if "aedes aegypti" in it["question"].lower()
    )
    assert ak154_item["ask_count"] >= 2

    # Pastikan privasi PDPA ketat: No. K/P & emel pengguna tidak bocor dalam jawapan awam
    dumped = json.dumps(body, ensure_ascii=False)
    assert "900101-11-5123" not in dumped
    assert "Ali bin Baba" not in dumped
    assert email_a not in dumped
    assert email_b not in dumped
    assert "token_map" not in dumped

    # Pastikan objek jawapan penuh tersedia untuk dipaparkan terus pada klik kad
    covid_item = next(
        it for it in groups_by_code["Akta 342"]["items"] if "covid" in it["question"].lower()
    )
    assert covid_item["answer"] is not None
    assert covid_item["answer"]["tajuk_nasihat"]
    assert covid_item["answer"]["keputusan_tindakan"]
    assert len(covid_item["answer"]["sop_lapangan"]) >= 1
    assert len(covid_item["answer"]["cadangan_pertuduhan"]) >= 1

    # Uji tapisan API mengikut Akta dan kata kunci carian
    resp_342_only = client.get(
        "/api/advisor/answered",
        headers=headers_c,
        params={"akta": "Akta 342", "q": "covid"},
    )
    assert resp_342_only.status_code == 200
    b342 = resp_342_only.json()
    assert [g["akta_code"] for g in b342["groups"]] == ["Akta 342"]
    assert any("covid" in it["question"].lower() for it in b342["items"])
