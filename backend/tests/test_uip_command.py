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
    assert len(scenarios) == 19
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


def test_advisor_reuses_similar_question_from_qa_collection_and_respects_guards(monkeypatch) -> None:
    import uuid
    from types import SimpleNamespace
    from backend.main import advisor_service, router_service

    advisor_service.clear_cache()

    def _reg_with_card(tag: str, full_name: str, card_no: str) -> dict[str, str]:
        email = f"ppkp.{tag}.{uuid.uuid4().hex[:6]}@moh.gov.my"
        reg = client.post(
            "/api/auth/register",
            json={
                "email": email,
                "password": "QACollection#2026",
                "full_name": full_name,
                "kkm_authority_card_no": card_no,
            },
        )
        assert reg.status_code == 200
        return {"Authorization": f"Bearer {reg.json()['token']}"}

    headers_x = _reg_with_card("x", "PPKP Encik Ahmad X", "KKM-TRG-X111")
    headers_y = _reg_with_card("y", "PPKP Puan Siti Y", "KKM-TRG-Y222")

    unique_tag = uuid.uuid4().hex[:6]
    ai_marker_title = f"Nasihat AI: Pemprosesan Kicap Berkarat & Label Luput ({unique_tag})"

    class _FakeInteractions:
        def create(self, **kwargs):
            raise RuntimeError("Guna models.generate_content terus")

    class _FakeModelsSeed:
        def generate_content(self, *, model, contents, config):
            return SimpleNamespace(
                text=json.dumps(
                    {
                        "tajuk_nasihat": ai_marker_title,
                        "keputusan_tindakan": "SITA PRODUK LUPUT S.4(1)(f) & PERINTAH TUTUP S.11 AKTA MAKANAN 1983",
                        "sesuai_buka_ip": True,
                        "alasan_keputusan": "Mesin pemprosesan kicap berkarat dan label tamat tempoh tanpa kelulusan MeSTI mendedahkan risiko keselamatan makanan.",
                        "cadangan_pertuduhan": [
                            {
                                "perihal": "Mengilang makanan dalam keadaan tidak suci & berkarat",
                                "seksyen_kesalahan": "Peraturan 11(1) PPKM 2009 / Seksyen 11 Akta 281",
                                "seksyen_hukuman": "Peraturan 11(2) PPKM 2009",
                                "hukuman_maksimum": "Denda maks RM10,000 atau penjara maks 2 tahun",
                                "boleh_kompaun": "Tutup premis S.11 serta sitaan/Buka IP",
                            }
                        ],
                        "sop_lapangan": ["Tutup kilang S.11 Akta 281 serta-merta & sita botol berlabel luput."],
                        "eksibit_wajib": ["Sampel botol kicap luput tarikh + Sijil S.90A(2)."],
                        "perangkap_kesilapan": ["Pastikan label asal tidak diubah selepas sitaan."],
                        "templat_ringkas": "Pemeriksaan kilang kicap mendapati mesin karat dan label luput tarikh tanpa MeSTI.",
                    }
                )
            )

    monkeypatch.setattr(
        router_service,
        "_genai_client",
        SimpleNamespace(interactions=_FakeInteractions(), models=_FakeModelsSeed()),
    )

    q_orig = f"kilang kicap guna mesin berkarat dan label tamat tempoh tanpa sijil MeSTI {unique_tag}, boleh sita dan tutup premis?"
    seed_resp = client.post(
        "/api/advisor/consult",
        headers=headers_x,
        json={"question": q_orig, "akta_hint": "Semua", "use_ai": True},
    )
    assert seed_resp.status_code == 200
    assert seed_resp.json()["tajuk_nasihat"] == ai_marker_title

    # Pastikan tersimpan dalam Koleksi Q&A di bawah Akta 281 sebagai jawapan AI
    qa_list_1 = client.get("/api/advisor/answered", headers=headers_y, params={"akta": "Akta 281", "q": unique_tag})
    assert qa_list_1.status_code == 200
    items_1 = qa_list_1.json()["items"]
    assert len(items_1) == 1
    assert items_1[0]["is_ai_answered"] is True
    seed_qa_id = items_1[0]["id"]

    # Pasang spy: tidak boleh memanggil Gemini apabila soalan lebih kurang sama ditanya tanpa use_ai=True
    class _ForbiddenModels:
        def generate_content(self, **kwargs):
            raise AssertionError("Tidak sepatutnya panggil Gemini apabila padan Koleksi Q&A!")

    monkeypatch.setattr(
        router_service,
        "_genai_client",
        SimpleNamespace(interactions=_FakeInteractions(), models=_ForbiddenModels()),
    )

    # Pengguna Y tanya soalan berbeza ayat tetapi maksud lebih kurang sama (use_ai=False)
    q_similar = f"kilang buat kicap ada mesin karat serta label luput tarikh tiada sijil MeSTI {unique_tag}, boleh tutup dan sita?"
    reuse_resp = client.post(
        "/api/advisor/consult",
        headers=headers_y,
        json={"question": q_similar, "akta_hint": "Semua", "use_ai": False},
    )
    assert reuse_resp.status_code == 200
    reuse_body = reuse_resp.json()
    assert reuse_body["from_qa_collection"] is True
    assert reuse_body["matched_collection_id"] == seed_qa_id
    assert reuse_body["matched_collection_similarity"] >= 62
    assert reuse_body["tajuk_nasihat"] == ai_marker_title
    assert reuse_body["ai_succeeded"] is True
    assert reuse_body["ai_attempted"] is False
    assert "Koleksi Q&A Pakar" in reuse_body["engine_used"]
    # Pastikan templat kes dipersonalisasi dengan profil Pengguna Y, BUKAN Pengguna X
    assert "PPKP Puan Siti Y" in reuse_body["draf_teks_kes_cadangan"]
    assert "KKM-TRG-Y222" in reuse_body["draf_teks_kes_cadangan"]
    assert "PPKP Encik Ahmad X" not in reuse_body["draf_teks_kes_cadangan"]

    # Koleksi Q&A tidak mewujudkan kad pendua, sebaliknya ask_count meningkat >= 2
    qa_list_2 = client.get("/api/advisor/answered", headers=headers_y, params={"akta": "Akta 281", "q": unique_tag})
    assert qa_list_2.status_code == 200
    items_2 = qa_list_2.json()["items"]
    assert len(items_2) == 1
    assert items_2[0]["ask_count"] >= 2

    # Uji pengawal polariti klinikal: PTB Smear Positif tidak boleh dipadankan ke soalan PTB Smear Negatif
    r_pos = client.post(
        "/api/advisor/consult",
        headers=headers_x,
        json={
            "question": f"pesakit tibi PTB smear positif AFB positif enggan sambung rawatan {unique_tag}",
            "akta_hint": "Akta 342",
            "use_ai": False,
        },
    )
    assert r_pos.status_code == 200
    r_neg = client.post(
        "/api/advisor/consult",
        headers=headers_y,
        json={
            "question": f"pesakit saringan tibi PTB smear negatif afb negatif enggan mula rawatan {unique_tag}",
            "akta_hint": "Akta 342",
            "use_ai": False,
        },
    )
    assert r_neg.status_code == 200
    neg_body = r_neg.json()
    assert neg_body["sesuai_buka_ip"] is False
    assert "Smear Positif" not in neg_body["tajuk_nasihat"]

    # Uji butang 'Analisa Baharu dengan AI' (use_ai=True) sentiasa memanggil Gemini segar
    fresh_title = f"Analisis AI Segar Baharu ({unique_tag})"

    class _FreshModels:
        def generate_content(self, *, model, contents, config):
            return SimpleNamespace(
                text=json.dumps(
                    {
                        "tajuk_nasihat": fresh_title,
                        "keputusan_tindakan": "BUKA IP SEGERA & SITAAAN AKTA 281",
                        "sesuai_buka_ip": True,
                        "alasan_keputusan": "Analisa AI baharu khusus bagi keadaan mesin berkarat.",
                        "cadangan_pertuduhan": [
                            {
                                "perihal": "Premis pengilangan tidak bersih",
                                "seksyen_kesalahan": "Peraturan 11(1) PPKM 2009",
                                "seksyen_hukuman": "Peraturan 11(2) PPKM 2009",
                                "hukuman_maksimum": "Denda maks RM10,000 atau penjara 2 tahun",
                                "boleh_kompaun": "Buka IP & tutup S.11",
                            }
                        ],
                        "sop_lapangan": ["Sita mesin dan produk luput tarikh."],
                        "eksibit_wajib": ["Gambar mesin karat + Sijil S.90A."],
                        "perangkap_kesilapan": ["Rekod nombor batch produk dengan tepat."],
                        "templat_ringkas": "Analisa segar kilang kicap.",
                    }
                )
            )

    monkeypatch.setattr(
        router_service,
        "_genai_client",
        SimpleNamespace(interactions=_FakeInteractions(), models=_FreshModels()),
    )
    fresh_resp = client.post(
        "/api/advisor/consult",
        headers=headers_y,
        json={"question": q_similar, "akta_hint": "Semua", "use_ai": True},
    )
    assert fresh_resp.status_code == 200
    fresh_body = fresh_resp.json()
    assert fresh_body["from_qa_collection"] is False
    assert fresh_body["ai_attempted"] is True
    assert fresh_body["ai_succeeded"] is True
    assert fresh_body["tajuk_nasihat"] == fresh_title
    advisor_service.clear_cache()


def test_fasa5_validate_legal_output_blocks_fabricated_repealed_and_unfulfilled_elements() -> None:
    """
    FASA 5 (1): Mengesahkan validateLegalOutput() menangkap & menyekat:
    (a) Seksyen rekaan yang tidak wujud dalam statute_sections_verbatim (cth: Seksyen 999 Akta 852)
    (b) Undang-undang terbatal dalam repealed_and_blocked_provisions (cth: Peraturan 13(1) PPKHT 2004, Ordinan Darurat 2021)
    (c) Cadangan kompaun S.17(1) Akta 852 apabila unsur mandatori tidak dipenuhi (pelajar memiliki vape dalam beg sekolah tanpa bukti merokok/mengunyah/menggunakan/membeli).
    """
    headers = _get_auth_headers()

    # (a) Seksyen rekaan: Seksyen 999 Akta 852
    resp_fabricated = client.post(
        "/api/legal/validate",
        headers=headers,
        json={
            "ai_response": {
                "tajuk_nasihat": "Ujian Seksyen Rekaan",
                "keputusan_tindakan": "KELUARKAN NOTIS KOMPAUN",
                "cadangan_pertuduhan": [
                    {
                        "perihal": "Kesalahan rekaan",
                        "seksyen_kesalahan": "Seksyen 999 Akta 852",
                        "seksyen_hukuman": "Seksyen 999(2) Akta 852",
                        "hukuman_maksimum": "Denda RM50,000",
                        "boleh_kompaun": "Boleh dikompaun",
                    }
                ],
            },
            "question_context": "Periksa kedai runcit jual rokok",
        },
    )
    assert resp_fabricated.status_code == 200
    fab_data = resp_fabricated.json()
    assert fab_data["passed"] is False
    assert any("999" in s for s in fab_data["invalid_citations"])
    assert "Amaran Sistem: Cadangan petikan undang-undang gagal pengesahan Pustaka Akta." in (
        fab_data["warning_banner"] or ""
    )

    # (b) Undang-undang yang telah dimansuhkan: Peraturan 13(1) PPKHT 2004 & Ordinan Darurat 2021
    resp_repealed = client.post(
        "/api/legal/validate",
        headers=headers,
        json={
            "ai_response": {
                "tajuk_nasihat": "Kompaun Pelajar Memiliki Rokok",
                "keputusan_tindakan": "KELUARKAN KOMPAUN PPKHT 2004",
                "cadangan_pertuduhan": [
                    {
                        "perihal": "Orang belum dewasa memiliki hasil tembakau",
                        "seksyen_kesalahan": "Peraturan 13(1) PPKHT 2004 dan Ordinan Darurat 2021 Akta 342",
                        "seksyen_hukuman": "Peraturan 13(2) PPKHT 2004",
                    }
                ],
            },
            "question_context": "Pelajar sekolah ada rokok",
        },
    )
    assert resp_repealed.status_code == 200
    rep_data = resp_repealed.json()
    assert rep_data["passed"] is False
    assert len(rep_data["repealed_hits"]) >= 1
    assert "PPKHT 2004" in (rep_data["warning_banner"] or "")

    # (c) Unsur mandatori tidak dipenuhi: Pelajar memiliki vape di dalam beg sekolah tanpa bukti merokok/menggunakan/membeli
    resp_unfulfilled = client.post(
        "/api/legal/validate",
        headers=headers,
        json={
            "ai_response": {
                "tajuk_nasihat": "Kompaun Pelajar Simpan Vape Dalam Beg",
                "keputusan_tindakan": "KELUARKAN NOTIS KOMPAUN SEKSYEN 17(1) AKTA 852",
                "sesuai_buka_ip": False,
                "cadangan_pertuduhan": [
                    {
                        "perihal": "Orang belum dewasa memiliki vape dalam beg sekolah",
                        "seksyen_kesalahan": "Seksyen 17(1) Akta 852",
                        "seksyen_hukuman": "Seksyen 17(2) Akta 852",
                        "hukuman_maksimum": "Denda RM500",
                        "boleh_kompaun": "Boleh dikompaun RM50",
                    }
                ],
            },
            "question_context": "Cikgu disiplin jumpa vape dalam beg sekolah pelajar semasa spotcheck, pelajar tidak menghisap atau membeli",
        },
    )
    assert resp_unfulfilled.status_code == 200
    unf_data = resp_unfulfilled.json()
    assert unf_data["passed"] is False
    assert len(unf_data["unfulfilled_element_errors"]) >= 1
    assert any("17(1)" in err for err in unf_data["unfulfilled_element_errors"])

    # Uji terus melalui /api/advisor/consult: situasi pelajar simpan vape dalam beg sekolah WAJIB menolak kompaun S.17(1)
    resp_bag_consult = client.post(
        "/api/advisor/consult",
        headers=headers,
        json={
            "question": "Guru disiplin rampas pod vape dijumpai dalam beg sekolah pelajar tingkatan 3 semasa spotcheck, tiada saksi nampak pelajar menghisap atau membeli. Boleh keluar kompaun Seksyen 17(1) Akta 852?",
            "akta_hint": "Akta 852",
            "use_ai": False,
        },
    )
    assert resp_bag_consult.status_code == 200
    bag_body = resp_bag_consult.json()
    assert "BUKAN KESALAHAN" in bag_body["keputusan_tindakan"].upper()
    assert "UNSUR MANDATORI TIDAK TERPENUHI" in bag_body["keputusan_tindakan"].upper()
    assert "17(1)" in bag_body["keputusan_tindakan"].upper()
    assert bag_body["sesuai_buka_ip"] is False
    evals = bag_body.get("element_evaluations") or []
    assert len(evals) >= 1
    assert any(
        el.get("status") == "TIDAK TERPENUHI"
        for ev in evals
        for el in ev.get("element_evaluations", [])
    )
    assert bag_body["legal_validation"]["passed"] is True


def test_fasa5_unindexed_statute_refuses_to_guess_and_verbatim_citations_match_100_percent() -> None:
    """
    FASA 5 (2) & (3):
    - Apabila suatu akta mempunyai total_sections_indexed == 0, sistem enggan meneka dan memulangkan
      status 'AKTA BELUM DIINDEKS — MUAT NAIK PDF WARTA'.
    - Semua teks dalam 'statutory_citations' (tab Petikan Akta) sepadan 100% aksara-demi-aksara
      dengan 'verbatim_text_bm' dalam 'statute_sections_verbatim'.
    """
    headers = _get_auth_headers()
    admin_headers = _get_dev_admin_headers()

    # 1. Daftarkan satu statut ujian dengan total_sections_indexed == 0
    reg_resp = client.post(
        "/api/legal/register-statute",
        headers=admin_headers,
        json={
            "statute_id": "AKTA_999_UJIAN",
            "official_title_bm": "Akta Kesihatan Persekitaran Ujian 2026 [Akta 999]",
            "act_number_or_pu": "Akta 999",
            "official_title_en": "Environmental Health Test Act 2026 [Act 999]",
        },
    )
    assert reg_resp.status_code == 200
    assert reg_resp.json()["statute"]["total_sections_indexed"] == 0

    # Tanya Pakar mengenai Akta 999 yang belum diindeks
    consult_unindexed = client.post(
        "/api/advisor/consult",
        headers=headers,
        json={
            "question": "Apakah seksyen kesalahan dan kompaun di bawah Akta 999?",
            "akta_hint": "AKTA_999_UJIAN",
            "use_ai": False,
        },
    )
    assert consult_unindexed.status_code == 200
    unindexed_body = consult_unindexed.json()
    assert "AKTA BELUM DIINDEKS — MUAT NAIK PDF WARTA" in unindexed_body["keputusan_tindakan"]
    assert unindexed_body["cadangan_pertuduhan"] == []

    # Semak juga /api/legal/sections untuk statut yang belum diindeks
    sec_unindexed = client.get(
        "/api/legal/sections",
        headers=headers,
        params={"statute_id": "AKTA_999_UJIAN"},
    )
    assert sec_unindexed.status_code == 200
    assert (
        sec_unindexed.json()["status"]
        == "AKTA BELUM DIINDEKS — MUAT NAIK PDF WARTA"
    )

    # 2. Ambil snapshot penuh statute_sections_verbatim dan sahkan 100% padanan aksara-demi-aksara
    snap_resp = client.get("/api/legal/snapshot", headers=headers)
    assert snap_resp.status_code == 200
    snap = snap_resp.json()
    verbatim_by_doc_id = {
        sec["doc_id"]: sec["verbatim_text_bm"]
        for sec in snap["statute_sections_verbatim"]
    }
    verbatim_texts_set = set(verbatim_by_doc_id.values())
    assert len(verbatim_by_doc_id) >= 35

    # Uji beberapa pertanyaan Pakar UIP merentasi Akta 852, Akta 281, Akta 154, Akta 342
    sample_queries = [
        ("Budak sekolah hisap rokok di tepi jalan", "Akta 852"),
        ("Premis restoran kotor ada lipas dan pengendali tiada suntikan tifoid", "Akta 281"),
        ("Tapak binaan ada pembiakan jentik-jentik Aedes", "Akta 154"),
        ("Pesakit Tibi smear positif ingkar perintah pengawasan Seksyen 15(1)", "Akta 342"),
    ]
    for q_text, akta_hint in sample_queries:
        r = client.post(
            "/api/advisor/consult",
            headers=headers,
            json={"question": q_text, "akta_hint": akta_hint, "use_ai": False},
        )
        assert r.status_code == 200
        body = r.json()
        citations = body.get("statutory_citations", [])
        assert len(citations) >= 1
        for cit in citations:
            doc_id = cit.get("doc_id") or cit.get("chunk_id")
            assert doc_id in verbatim_by_doc_id, f"doc_id {doc_id} tiada dalam statute_sections_verbatim"
            # Sahkan 100% aksara-demi-aksara (character-for-character)
            assert cit["text"] == verbatim_by_doc_id[doc_id]
            assert cit["text"] in verbatim_texts_set


def test_fasa5_gazette_ingestion_pipeline_and_admin_verification() -> None:
    """
    FASA 5 (4): Mengesahkan saluran paip pengekstrakan Warta (/api/legal/ingest),
    penyaringan kesalahan DRAFT_PENDING_REVIEW, dan pengesahan Admin (/api/legal/verify).
    """
    headers = _get_auth_headers()
    admin_headers = _get_dev_admin_headers()
    sample_gazette_text = (
        "BAHAGIAN I - PERMULAAN\n"
        "Seksyen 1. Tajuk ringkas dan permulaan kuat kuasa.\n"
        "(1) Akta ini bolehlah dinamakan Akta Ujian Warta 2026.\n\n"
        "BAHAGIAN II - KAWALAN KESIHATAN\n"
        "Seksyen 5. Larangan membuang sisa klinikal.\n"
        "(1) Tiada seorang pun boleh membuang sisa klinikal di tempat awam.\n"
        "(2) Mana-mana orang yang melanggar subseksyen (1) melakukan suatu kesalahan dan boleh, "
        "apabila disabitkan, didenda tidak melebihi sepuluh ribu ringgit atau dipenjara selama tempoh "
        "tidak melebihi dua tahun atau kedua-duanya.\n"
    )

    resp_ingest = client.post(
        "/api/legal/ingest",
        headers=admin_headers,
        files={
            "file": (
                "AKTA_999_UJIAN.txt",
                sample_gazette_text.encode("utf-8"),
                "text/plain",
            )
        },
        data={
            "statute_id": "AKTA_999_UJIAN",
            "official_title_bm": "Akta Ujian Warta 2026 [Akta 999]",
            "act_number_or_pu": "Akta 999",
            "verified_by_admin": "false",
        },
    )
    assert resp_ingest.status_code == 200
    ing_data = resp_ingest.json()["legal_library_ingest"]
    assert ing_data["sections_extracted"] == 2
    assert ing_data["new_offences_swept"] >= 1

    # Semak kesalahan yang disapu berada dalam status DRAFT_PENDING_REVIEW sebelum disahkan Admin
    off_resp = client.get(
        "/api/legal/offences",
        headers=headers,
        params={"statute_id": "AKTA_999_UJIAN"},
    )
    assert off_resp.status_code == 200
    swept_offences = off_resp.json()["offences"]
    assert len(swept_offences) >= 1
    draft_offence = swept_offences[0]
    assert draft_offence["verified_status"] == "DRAFT_PENDING_REVIEW"

    # Admin klik "Sahkan Warta"
    ver_resp = client.post(
        "/api/legal/verify",
        headers=admin_headers,
        json={"statute_id": "AKTA_999_UJIAN", "verified": True},
    )
    assert ver_resp.status_code == 200
    assert ver_resp.json()["updated_statutes"] >= 1

    off_resp_after = client.get(
        "/api/legal/offences",
        headers=headers,
        params={"statute_id": "AKTA_999_UJIAN"},
    )
    assert off_resp_after.status_code == 200
    assert off_resp_after.json()["offences"][0]["verified_status"] == "VERIFIED_AGC"

    # Bersihkan fail ujian sementara & override DB supaya data/akta/ dan data/legal_library/ kekal bersih
    from backend.core.config import settings
    from backend.core.database import get_uip_db
    from backend.rag.legal_engine import get_legal_library

    test_akta_file = settings.akta_dir / "AKTA_999_UJIAN.txt"
    if test_akta_file.exists():
        test_akta_file.unlink()
    get_uip_db().delete_legal_admin_override("STATUTE", "AKTA_999_UJIAN")
    get_legal_library()._bootstrap_library()


def test_predeploy_audit_draft_only_defaults_pdf_parser_and_legacy_qa_filtering() -> None:
    """
    Audit 3 perkara kritikal pra-deploy:
    1. TIADA entri hardcoded atau .txt bertanda VERIFIED_AGC / verified_by_admin=True dalam legal_engine.py & data/legal_library/*.json.
    2. Penghurai PDF (pymupdf) berfungsi untuk muat naik PDF Warta sebenar serta tersenarai dalam backend/requirements.txt & Dockerfile.
    3. Rekod lama dalam Koleksi Q&A tanpa medan `statute_library_version` diabaikan secara automatik dan tidak dipaparkan kepada pengguna.
    """
    from pathlib import Path
    import uuid
    from backend.core.database import get_uip_db
    from backend.rag.legal_engine import (
        DEFAULT_MASTER_OFFENCES_MATRIX,
        DEFAULT_STATUTES_REGISTRY_META,
        get_legal_library,
    )

    root = Path(__file__).resolve().parents[2]
    headers = _get_auth_headers()
    admin_headers = _get_dev_admin_headers()

    # --- 1. Audit semua entri hardcoded & JSON snapshots ---
    lib = get_legal_library()
    lib._bootstrap_library()

    assert all(s["verified_by_admin"] is False for s in DEFAULT_STATUTES_REGISTRY_META)
    assert all(o["verified_status"] == "DRAFT_PENDING_REVIEW" for o in DEFAULT_MASTER_OFFENCES_MATRIX)

    reg_json = json.loads((root / "data/legal_library/statutes_registry.json").read_text(encoding="utf-8"))
    off_json = json.loads((root / "data/legal_library/master_offences_matrix.json").read_text(encoding="utf-8"))
    for st in reg_json["statutes_registry"]:
        if not str(st.get("source_pdf_filename") or "").lower().endswith(".pdf"):
            assert st["verified_by_admin"] is False, f"{st['statute_id']} bukan PDF tetapi verified_by_admin=True"
    for off in off_json:
        assert off["verified_status"] == "DRAFT_PENDING_REVIEW", (
            f"{off['offence_id']} bertanda {off['verified_status']} walaupun tiada PDF Warta rasmi"
        )

    # --- 2. Sahkan penghurai PDF sebenar (pymupdf) + backend/requirements.txt + Dockerfile ---
    reqs = (root / "backend/requirements.txt").read_text(encoding="utf-8").lower()
    dockerfile = (root / "Dockerfile").read_text(encoding="utf-8")
    assert "pymupdf" in reqs
    assert "python-multipart" in reqs
    assert "COPY backend/requirements.txt" in dockerfile
    assert "COPY scripts/" in dockerfile
    assert "COPY data/legal_library/" in dockerfile
    assert "import pymupdf" in dockerfile

    # Jana fail PDF Warta ujian menggunakan PyMuPDF dan muat naik ke /api/legal/ingest
    pdf_doc = fitz.open()
    page = pdf_doc.new_page()
    page.insert_text(
        (50, 72),
        "BAHAGIAN I - PERMULAAN\n"
        "Seksyen 1. Tajuk ringkas.\n"
        "(1) Akta ini dinamakan Akta Ujian PDF Warta 2026.\n\n"
        "BAHAGIAN II - KESALAHAN\n"
        "Seksyen 8. Larangan pencemaran air.\n"
        "(1) Mana-mana orang yang mencemarkan air melakukan suatu kesalahan dan boleh didenda RM5000.\n",
    )
    pdf_bytes = pdf_doc.tobytes()
    pdf_doc.close()

    resp_pdf = client.post(
        "/api/legal/ingest",
        headers=admin_headers,
        files={"file": ("AKTA_998_PDF.pdf", pdf_bytes, "application/pdf")},
        data={
            "statute_id": "AKTA_998_PDF",
            "official_title_bm": "Akta Ujian PDF Warta 2026 [Akta 998]",
            "act_number_or_pu": "Akta 998",
            "verified_by_admin": "false",
        },
    )
    assert resp_pdf.status_code == 200
    pdf_ing = resp_pdf.json()["legal_library_ingest"]
    assert pdf_ing["sections_extracted"] >= 2
    assert pdf_ing["verified_by_admin"] is False

    # Bersihkan fail PDF ujian sementara
    test_pdf_file = root / "data/akta/AKTA_998_PDF.pdf"
    if test_pdf_file.exists():
        test_pdf_file.unlink()
    lib._bootstrap_library()

    # --- 3. Sahkan rekod lama Koleksi Q&A tanpa `statute_library_version` diabaikan secara automatik ---
    db = get_uip_db()
    legacy_tag = f"legacynover{uuid.uuid4().hex[:6]}"
    legacy_id = f"arc-legacy-{uuid.uuid4().hex[:8]}"
    legacy_analysis = {
        "scenario_id": "legacy_pre_v2",
        "akta_disyorkan": "Akta 852",
        "tajuk_nasihat": f"Jawapan Lama Pra-V2 Tanpa Versi ({legacy_tag})",
        "keputusan_tindakan": "KOMPAUN LAMA PPKHT 2004",
        "sesuai_buka_ip": False,
        "alasan_keputusan": "Jawapan lama sebelum rombakan Closed-Book.",
        "cadangan_pertuduhan": [
            {
                "perihal": "Kesalahan lama",
                "seksyen_kesalahan": "Peraturan 13(1) PPKHT 2004",
                "seksyen_hukuman": "Peraturan 13(2) PPKHT 2004",
                "hukuman_maksimum": "RM1,000",
                "boleh_kompaun": "Kompaun RM50",
            }
        ],
        "sop_lapangan": ["Langkah lama 1", "Langkah lama 2"],
        "eksibit_wajib": ["Eksibit lama"],
        "perangkap_kesilapan": [],
        "templat_ringkas": "Templat lama",
        "ai_succeeded": True,
        # SENGAJA TIADA medan `statute_library_version`
    }

    with db._connect() as conn:
        conn.execute(
            """
            INSERT INTO dev_archive_records (
                id, category, action_type, endpoint, user_email, user_name,
                akta_utama, title, preview_text, redacted_input_text,
                redacted_response_text, request_json, redacted_analysis_json,
                model_used, is_cloud_api, status_summary, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                legacy_id,
                "ADVISOR_QA",
                "TANYA_PAKAR_UIP",
                "/api/advisor/consult",
                "legacy@moh.gov.my",
                "Pegawai Lama",
                "Akta 852",
                f"Soalan Lama {legacy_tag}",
                f"Soalan Lama {legacy_tag}",
                f"pelajar sekolah bawa vape dalam beg {legacy_tag} boleh kompaun?",
                "Jawapan lama",
                json.dumps({"question": f"pelajar sekolah bawa vape dalam beg {legacy_tag} boleh kompaun?"}),
                json.dumps(legacy_analysis, ensure_ascii=False),
                "gemini-legacy",
                1,
                "KOMPAUN LAMA",
                "2025-01-01 08:00:00",
            ),
        )
        conn.commit()

    # 3a. list_advisor_answered_questions & endpoint /api/advisor/answered WAJIB mengabaikan rekod lama ini
    resp_answered = client.get(
        "/api/advisor/answered",
        headers=headers,
        params={"q": legacy_tag},
    )
    assert resp_answered.status_code == 200
    assert resp_answered.json()["items"] == []

    # 3b. find_similar_answered_question WAJIB tidak memetik semula rekod lama ini
    sim_match = db.find_similar_answered_question(
        f"pelajar sekolah bawa vape dalam beg {legacy_tag} boleh kompaun?"
    )
    assert sim_match is None

    # 3c. _init_schema() (simulasi restart/deploy ke produksi) WAJIB menandakan rekod lama itu sebagai TANYA_PAKAR_UIP_STALE
    db._init_schema()
    with db._connect() as conn:
        row = conn.execute(
            "SELECT action_type FROM dev_archive_records WHERE id = ?",
            (legacy_id,),
        ).fetchone()
    assert row is not None
    assert row["action_type"] == "TANYA_PAKAR_UIP_STALE"


def test_official_agc_gazette_pdfs_installed_and_indexed_verbatim() -> None:
    """
    Sahkan kesemua 20 fail PDF Warta Kerajaan Rasmi (16 teras + 4 pelengkap AGC/KKM)
    wujud dalam data/akta/, sepadan hash SHA-256 dengan SUMBER_WARTA_AGC.json,
    diindeks 100% verbatim tanpa unindexed_statutes, serta mengandungi teks sahih utama.
    """
    import hashlib
    from pathlib import Path
    from backend.rag.legal_engine import get_legal_library

    root = Path(__file__).resolve().parents[2]
    akta_dir = root / "data/akta"
    manifest = json.loads((akta_dir / "SUMBER_WARTA_AGC.json").read_text(encoding="utf-8"))
    docs = manifest["documents"]
    assert len(docs) == 20

    lib = get_legal_library()
    report = lib.get_coverage_audit_report()
    assert report["unindexed_statutes"] == []
    assert report["active_statutes_count"] >= 20
    assert report["total_verbatim_sections"] >= 1450

    reg_by_id = {st["statute_id"]: st for st in report["statutes_registry"]}
    for item in docs:
        pdf_path = akta_dir / item["filename"]
        assert pdf_path.exists(), f"Fail PDF rasmi hilang: {item['filename']}"
        actual_sha = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
        assert actual_sha == item["sha256"], f"Hash SHA-256 tidak sepadan bagi {item['filename']}"
        st = reg_by_id[item["statute_id"]]
        assert st["source_pdf_filename"] == item["filename"]
        assert st["source_pdf_hash"] == item["sha256"]
        assert st["total_sections_indexed"] > 0
        assert st["verified_by_admin"] is False

    secs_by_id = {s["doc_id"]: s["verbatim_text_bm"] for s in lib.statute_sections_verbatim}
    expected_snippets = {
        "AKTA_852__S17": "orang belum dewasa",
        "AKTA_852__S24": "perakuan pemberian kuasa",
        "AKTA_852__S48": "mengkompaun",
        "AKTA_852__S49": "pertubuhan perbadanan",
        "AKTA_852_PERATURAN_KOMPAUN_2024__P2": "Jadual Pertama",
        "AKTA_281__S13B": "diadukkan",
        "PPKM_2009__P31": "vaksin",
        "PPKM_2009__P34": "perosak",
        "PPM_1985__P14": "penandaan tarikh",
        "AKTA_154__S13": "serangga pembawa penyakit",
        "AKTA_342__S22": "menghalang",
        "AKTA_342_PERATURAN_KOMPAUN_2025__P2": "Jadual Pertama",
        "AKTA_593__S112": "police investigation",
        "AKTA_56__S73AA": "criminal",
        "AKTA_56__S90A": "computer",
        "AKTA_56__S114A": "publication",
        "AKTA_611__S83": "kanak-kanak",
    }
    for doc_id, needle in expected_snippets.items():
        assert doc_id in secs_by_id, f"Seksyen kritikal hilang: {doc_id}"
        normalized_text = " ".join(secs_by_id[doc_id].lower().split())
        assert needle.lower() in normalized_text, (
            f"Teks sahih '{needle}' tidak ditemui dalam {doc_id}"
        )

    # Sahkan sapuan penuh master_offences_matrix jauh melebihi 25 rekod teras & semua pautan doc_id sah
    assert len(lib.master_offences_matrix) >= 80
    seen_off_ids: set[str] = set()
    for off in lib.master_offences_matrix:
        oid = off["offence_id"]
        assert oid not in seen_off_ids, f"Duplikasi offence_id ditemui: {oid}"
        seen_off_ids.add(oid)
        doc_ids = off.get("source_section_doc_ids") or []
        assert len(doc_ids) >= 1, f"{oid} tiada source_section_doc_ids"
        for did in doc_ids:
            assert did in secs_by_id, f"{oid} memautkan doc_id tidak wujud: {did}"


def test_amendment_companions_auto_inject_akta342_and_akta281_amendments() -> None:
    """
    Sahkan pautan wajib AMENDMENT_COMPANIONS:
    - Pertanyaan berkaitan kompaun/denda Akta 342 secara automatik menarik konteks AKTA_342_PINDAAN_2025
      (Akta A1742) dan AKTA_342_PERATURAN_KOMPAUN_2025 (P.U.(A) 139/2025) beserta arahan keras pindaan 2025.
    - Pertanyaan berkaitan Akta 281 secara automatik menarik konteks AKTA_281_PINDAAN_2024 (Akta A1702).
    """
    from backend.rag.legal_engine import get_legal_library

    lib = get_legal_library()
    headers = _get_auth_headers()

    g342 = lib.search_closed_book_grounding(
        "Berapa had kompaun dan denda maksimum bagi kesalahan di bawah Akta 342 sekarang?",
        akta_hint="Akta 342",
    )
    assert "AKTA_342_PINDAAN_2025" in g342["amendment_companions_applied"]
    assert "AKTA_342_PERATURAN_KOMPAUN_2025" in g342["amendment_companions_applied"]
    v342_sids = {v["statute_id"] for v in g342["verbatim_sections"]}
    assert "AKTA_342_PINDAAN_2025" in v342_sids
    assert "AKTA_342_PERATURAN_KOMPAUN_2025" in v342_sids
    assert "ARAHAN KERAS PINDAAN STATUTORI" in g342["statutory_context_block"]
    assert "RM5,000" in g342["statutory_context_block"]
    assert "139/2025" in g342["statutory_context_block"]

    # Semak juga melalui endpoint /api/advisor/consult
    resp_342 = client.post(
        "/api/advisor/consult",
        headers=headers,
        json={
            "question": "Berapa had kompaun individu dan syarikat serta penalti am Seksyen 24 Akta 342 terkini?",
            "akta_hint": "Akta 342",
            "use_ai": False,
        },
    )
    assert resp_342.status_code == 200
    body_342 = resp_342.json()
    assert "AKTA_342_PINDAAN_2025" in (body_342.get("amendment_companions_applied") or [])
    assert "AKTA_342_PERATURAN_KOMPAUN_2025" in (body_342.get("amendment_companions_applied") or [])
    cit_sids = {c.get("statute_id") for c in (body_342.get("statutory_citations") or [])}
    assert "AKTA_342_PINDAAN_2025" in cit_sids
    assert "AKTA_342_PERATURAN_KOMPAUN_2025" in cit_sids

    # Semak pautan Akta 281 <-> Akta A1702
    g281 = lib.search_closed_book_grounding(
        "Apakah pindaan terkini pada Seksyen 2 dan Seksyen 34 Akta Makanan 1983 (Akta 281)?",
        akta_hint="Akta 281",
    )
    assert "AKTA_281_PINDAAN_2024" in g281["amendment_companions_applied"]
    assert any(v["statute_id"] == "AKTA_281_PINDAAN_2024" for v in g281["verbatim_sections"])


def test_admin_verification_and_trap_edits_persist_across_library_restart() -> None:
    """
    Sahkan ketahanan Cloud Run:
    Status VERIFIED_AGC dan suntingan explicit_exclusions_and_traps yang disimpan Admin
    disimpan ke pangkalan data kekal (SQLite/PostgreSQL) dan kekal utuh walaupun
    ClosedBookLegalLibrary dimulakan semula atau _bootstrap_library(force_rebuild=True) dijalankan.
    """
    from backend.core.database import get_uip_db
    from backend.rag.legal_engine import ClosedBookLegalLibrary, get_legal_library

    admin_headers = _get_dev_admin_headers()
    db = get_uip_db()
    lib = get_legal_library()
    custom_trap = "UJIAN KETAHANAN CLOUD RUN: Pastikan sampel larva disahkan oleh Pegawai Entomologi KKM."

    try:
        # 1. Admin sahkan AKTA_154 sebagai VERIFIED_AGC
        ver_resp = client.post(
            "/api/legal/verify",
            headers=admin_headers,
            json={"statute_id": "AKTA_154", "verified": True},
        )
        assert ver_resp.status_code == 200
        assert ver_resp.json()["updated_statutes"] == 1
        assert ver_resp.json()["persisted_to_db"] is True

        # 2. Admin sunting explicit_exclusions_and_traps pada AKTA_154_S13_1
        orig_off = next(o for o in lib.master_offences_matrix if o["offence_id"] == "AKTA_154_S13_1")
        orig_traps = list(orig_off.get("explicit_exclusions_and_traps") or [])
        upd_resp = client.put(
            "/api/legal/offences/AKTA_154_S13_1",
            headers=admin_headers,
            json={"explicit_exclusions_and_traps": orig_traps + [custom_trap]},
        )
        assert upd_resp.status_code == 200

        # 3. Simulasi restart kontena Cloud Run: bina instans baharu + force_rebuild=True
        fresh_lib = ClosedBookLegalLibrary()
        fresh_lib._bootstrap_library(force_rebuild=True)

        ak154_reg = next(r for r in fresh_lib.statutes_registry if r["statute_id"] == "AKTA_154")
        assert ak154_reg["verified_by_admin"] is True
        assert ak154_reg.get("verified_at")

        ak154_offs = [o for o in fresh_lib.master_offences_matrix if o["statute_id"] == "AKTA_154"]
        assert len(ak154_offs) >= 3
        assert all(o["verified_status"] == "VERIFIED_AGC" for o in ak154_offs)

        ak154_s13 = next(o for o in ak154_offs if o["offence_id"] == "AKTA_154_S13_1")
        assert custom_trap in (ak154_s13.get("explicit_exclusions_and_traps") or [])
    finally:
        # Bersihkan override ujian supaya snapshot lalai kekal bersih (DRAFT_PENDING_REVIEW)
        db.delete_legal_admin_override("STATUTE", "AKTA_154")
        db.delete_legal_admin_override("OFFENCE", "AKTA_154_S13_1")
        lib._bootstrap_library(force_rebuild=True)


def test_two_branch_advisor_vape_checking_bag_vs_smoking_and_corrupt_cache_purge() -> None:
    """
    Sahkan Rombakan Aliran Keputusan 2-Cabang & 4 Pembaikan Pepijat Kritikal:
    1. Cabang A (`TIADA_KESALAHAN`): 'Guru maklum PPKP ada pelajar memiliki vape semasa checking bag'
       - status_kesalahan == 'TIADA_KESALAHAN'
       - Terangkan sebab tidak menyalahi S.17(1) Akta 852
       - Cadangkan langkah susulan (serah sekolah/KPM + bukti tambahan S.13(1) / S.13(3))
       - TIADA Seksyen 2 (Tafsiran) / Akta 171 / Akta 281 / PPKM 2009 / unsur palsu TERPENUHI
    2. Cabang B (`ADA_KESALAHAN`): 'Guru tangkap pelajar sedang hisap vape dalam tandas sekolah'
       - status_kesalahan == 'ADA_KESALAHAN'
       - Punca Kuasa lengkap: Seksyen 17(1) Akta 852 + peringatan Akta 611
       - Cadangan tindakan segera, SOP lapangan bernombor, barang bukti wajib, dan teks verbatim sah
       - TIADA Akta 171 / PPKM 2009 / Seksyen 2 (Tafsiran)
    3. Sekat & Bersihkan Cache Rosak:
       - Rekod lama/rosak 'Seksyen 2 — Tafsiran' / 'rag_custom_query' disorok daripada Koleksi Q&A
         dan dipadamkan dari DB semasa startup (`_init_schema()`).
    """
    import uuid
    from backend.core.database import get_uip_db

    headers = _get_auth_headers()
    db = get_uip_db()

    # ------------------------------------------------------------------
    # CABANG A: TIADA_KESALAHAN (Pelajar memiliki vape semasa checking bag)
    # ------------------------------------------------------------------
    resp_bag = client.post(
        "/api/advisor/consult",
        headers=headers,
        json={
            "question": "Guru maklum PPKP ada pelajar memiliki vape semasa checking bag",
            "akta_hint": "Semua",
            "use_ai": False,
        },
    )
    assert resp_bag.status_code == 200
    bag = resp_bag.json()
    assert bag["status_kesalahan"] == "TIADA_KESALAHAN"
    assert bag["tajuk_nasihat"] == "TIADA KESALAHAN DI BAWAH AKTA 852"
    assert bag["sesuai_buka_ip"] is False
    assert bag["cadangan_pertuduhan"] == []
    assert bag["ringkasan_keputusan"]
    assert "17(1)" in (bag.get("sebab_tidak_menyalahi") or "")
    assert "PPKHT 2004" in (bag.get("sebab_tidak_menyalahi") or "")

    follow_ups_text = " ".join(bag.get("langkah_susulan_ppkp") or [])
    assert "sekolah" in follow_ups_text.lower() or "kpm" in follow_ups_text.lower()
    assert "13(1)" in follow_ups_text
    assert "13(3)" in follow_ups_text

    # Pastikan TIADA Akta 171 / Akta 281 / PPKM 2009 / Seksyen 2 (Tafsiran) bocor ke respons
    bag_serialized = json.dumps(bag, ensure_ascii=False)
    assert "Akta 171" not in bag_serialized
    assert "PPKM 2009" not in bag_serialized
    assert "PPKM_2009" not in bag_serialized
    assert "Akta 281" not in bag_serialized
    for cit in bag.get("statutory_citations") or []:
        assert "tafsiran" not in str(cit.get("section") or "").lower()
        assert str(cit.get("statute_id") or "").startswith(("AKTA_852", "AKTA_611"))

    # Penilaian unsur mesti 1-2 seksyen Akta 852 relevan sahaja dan TIADA unsur palsu TERPENUHI
    bag_evals = bag.get("element_evaluations") or []
    assert 1 <= len(bag_evals) <= 2
    for ev in bag_evals:
        assert str(ev.get("offence_id") or "").startswith("AKTA_852")
        assert ev.get("action_blocked") is True
        assert ev.get("all_elements_satisfied") is False
        assert any(
            el.get("status") == "TIDAK TERPENUHI"
            for el in (ev.get("element_evaluations") or [])
        )
        assert not any(
            el.get("status") == "TERPENUHI"
            for el in (ev.get("element_evaluations") or [])
        )
    assert bag["legal_validation"]["passed"] is True

    # ------------------------------------------------------------------
    # CABANG B: ADA_KESALAHAN (Pelajar ditangkap sedang hisap vape)
    # ------------------------------------------------------------------
    resp_smoke = client.post(
        "/api/advisor/consult",
        headers=headers,
        json={
            "question": "Guru tangkap pelajar sedang hisap vape dalam tandas sekolah",
            "akta_hint": "Semua",
            "use_ai": False,
        },
    )
    assert resp_smoke.status_code == 200
    smoke = resp_smoke.json()
    assert smoke["status_kesalahan"] == "ADA_KESALAHAN"
    assert smoke["akta_disyorkan"] == "Akta 852"

    punca = smoke.get("punca_kuasa") or {}
    assert "17(1)" in str(punca.get("seksyen_kesalahan") or "")
    assert "852" in str(punca.get("seksyen_kesalahan") or "")
    assert "17(2)" in str(punca.get("seksyen_hukuman") or "")
    assert punca.get("kuasa_penguatkuasaan")
    assert "Akta 611" in str(punca.get("peringatan_akta_611") or "")

    assert smoke.get("ringkasan_keputusan")
    assert len(smoke.get("sop_lapangan") or []) >= 4
    assert len(smoke.get("eksibit_wajib") or []) >= 3
    assert len(smoke.get("cadangan_pertuduhan") or []) >= 1
    assert any("17(1)" in c.get("seksyen_kesalahan", "") for c in smoke["cadangan_pertuduhan"])

    # Pastikan TIADA Akta 171 / Akta 281 / PPKM 2009 / Seksyen 2 (Tafsiran) dalam jawapan vape
    smoke_serialized = json.dumps(smoke, ensure_ascii=False)
    assert "Akta 171" not in smoke_serialized
    assert "PPKM 2009" not in smoke_serialized
    assert "PPKM_2009" not in smoke_serialized
    assert "Akta 281" not in smoke_serialized
    smoke_doc_ids = {c.get("doc_id") for c in (smoke.get("statutory_citations") or [])}
    assert "AKTA_852__S17" in smoke_doc_ids
    assert "AKTA_611__S83" in smoke_doc_ids
    for cit in smoke.get("statutory_citations") or []:
        assert "tafsiran" not in str(cit.get("section") or "").lower()
    assert smoke["legal_validation"]["passed"] is True

    # Pastikan cache Q&A tidak mencampurkan soalan memiliki vape dengan soalan hisap vape
    assert smoke.get("matched_collection_id") != bag.get("matched_collection_id") or (
        smoke.get("from_qa_collection") is False
    )

    # ------------------------------------------------------------------
    # SEMAKAN PEMBERSIHAN CACHE ROSAK ('Seksyen 2 — Tafsiran')
    # ------------------------------------------------------------------
    corrupt_tag = f"corruptsec2{uuid.uuid4().hex[:6]}"
    corrupt_id = f"arc-corrupt-{uuid.uuid4().hex[:8]}"
    corrupt_analysis = {
        "scenario_id": "rag_custom_query",
        "akta_disyorkan": "Akta 852",
        "tajuk_nasihat": f"Rujukan Statutori UIP Mengikut Situasi Soalan ({corrupt_tag})",
        "keputusan_tindakan": "SEMAK AKTA",
        "sesuai_buka_ip": False,
        "alasan_keputusan": "Fallback rosak.",
        "cadangan_pertuduhan": [
            {
                "perihal": "Tafsiran",
                "seksyen_kesalahan": "Seksyen 2 — Tafsiran",
                "seksyen_hukuman": "Seksyen 2",
                "hukuman_maksimum": "-",
                "boleh_kompaun": "-",
            }
        ],
        "sop_lapangan": ["Langkah 1"],
        "eksibit_wajib": ["Bukti 1"],
        "perangkap_kesilapan": [],
        "templat_ringkas": "",
        "statute_library_version": "2.5.0-closed-book-agc-pdf",
        "is_fallback_response": True,
    }
    with db._connect() as conn:
        conn.execute(
            """
            INSERT INTO dev_archive_records (
                id, category, action_type, endpoint, user_email, user_name,
                akta_utama, title, preview_text, redacted_input_text,
                redacted_response_text, request_json, redacted_analysis_json,
                model_used, is_cloud_api, status_summary, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                corrupt_id,
                "ADVISOR_QA",
                "TANYA_PAKAR_UIP",
                "/api/advisor/consult",
                "corrupt@moh.gov.my",
                "Pegawai Ujian",
                "Akta 852",
                f"Soalan Rosak {corrupt_tag}",
                f"Soalan Rosak {corrupt_tag}",
                f"pelajar memiliki vape {corrupt_tag}",
                "Seksyen 2 — Tafsiran",
                json.dumps({"question": f"pelajar memiliki vape {corrupt_tag}"}),
                json.dumps(corrupt_analysis, ensure_ascii=False),
                "rag-fallback",
                0,
                "FALLBACK",
                "2026-01-01 08:00:00",
            ),
        )
        conn.commit()

    # 1. Endpoint /api/advisor/answered WAJIB menyembunyikan rekod rosak ini serta-merta
    ans_check = client.get("/api/advisor/answered", headers=headers, params={"q": corrupt_tag})
    assert ans_check.status_code == 200
    assert ans_check.json()["items"] == []

    # 2. _init_schema() (startup produksi) WAJIB memadamkan rekod rosak dari DB
    db._init_schema()
    with db._connect() as conn:
        remaining = conn.execute(
            "SELECT COUNT(*) AS cnt FROM dev_archive_records WHERE id = ?",
            (corrupt_id,),
        ).fetchone()
    assert int(remaining["cnt"]) == 0


def test_five_expert_audit_remediations_security_legal_compound_and_docx() -> None:
    import uuid
    from docx import Document as DocxDocument
    from backend.rag.legal_engine import INITIAL_STATUTE_LIBRARY_VERSION, validate_legal_output

    # ------------------------------------------------------------------
    # 1. KESELAMATAN: IDOR ISOLATION, SETTINGS MASKING & OFFICER LOCKING
    # ------------------------------------------------------------------
    tag = uuid.uuid4().hex[:6]
    reg_a = client.post(
        "/api/auth/register",
        json={
            "email": f"ppkp.idor.a.{tag}@moh.gov.my",
            "password": "IdorTest#2026A",
            "full_name": "PPKP Ahmad Faizal bin Ramli",
            "grade": "U5",
            "kkm_authority_card_no": "KKM-TRG-A101",
            "district_pkd": "Pejabat Kesihatan Daerah Kuala Nerus",
        },
    )
    reg_b = client.post(
        "/api/auth/register",
        json={
            "email": f"ppkp.idor.b.{tag}@moh.gov.my",
            "password": "IdorTest#2026B",
            "full_name": "PPKP Siti Hajar binti Yusof",
            "grade": "U6",
            "kkm_authority_card_no": "KKM-TRG-B202",
            "district_pkd": "Pejabat Kesihatan Daerah Kuala Nerus",
        },
    )
    assert reg_a.status_code == 200 and reg_b.status_code == 200
    headers_a = {"Authorization": f"Bearer {reg_a.json()['token']}"}
    headers_b = {"Authorization": f"Bearer {reg_b.json()['token']}"}

    private_case_id = f"kes-private-{tag}"
    create_a = client.post(
        "/api/cases",
        headers=headers_a,
        json={
            "id": private_case_id,
            "no_ip": f"PKDKN/UIP/852/2026/{tag}",
            "tajuk": "Kes Sulit Pengguna A",
            "akta_utama": "Akta 852",
            "workflow": "ip_builder",
            "status": "Draf",
            "case_text": "Fakta kes sulit pengguna A.",
        },
    )
    assert create_a.status_code == 200

    # Pengguna A nampak kes sendiri; Pengguna B TIDAK nampak kes Pengguna A tetapi masih nampak kes contoh
    list_a_ids = {c["id"] for c in client.get("/api/cases", headers=headers_a).json()["cases"]}
    list_b_ids = {c["id"] for c in client.get("/api/cases", headers=headers_b).json()["cases"]}
    assert private_case_id in list_a_ids
    assert private_case_id not in list_b_ids
    assert any(cid.startswith("kes-akta-") for cid in list_b_ids)

    # Pengguna B disekat 403 daripada menulis ganti atau memadam kes Pengguna A
    overwrite_b = client.post(
        "/api/cases",
        headers=headers_b,
        json={
            "id": private_case_id,
            "no_ip": f"PKDKN/UIP/852/2026/{tag}",
            "tajuk": "Cubaan Rampas Kes A",
            "akta_utama": "Akta 852",
        },
    )
    assert overwrite_b.status_code == 403

    delete_b = client.delete(f"/api/cases/{private_case_id}", headers=headers_b)
    assert delete_b.status_code == 403

    # Pengguna A boleh memadam kes miliknya sendiri
    assert client.delete(f"/api/cases/{private_case_id}", headers=headers_a).status_code == 200

    # Pegawai bukan admin tidak menerima masked_gemini_api_key pada /api/settings
    settings_non_admin = client.get("/api/settings", headers=headers_a)
    assert settings_non_admin.status_code == 200
    assert settings_non_admin.json().get("masked_gemini_api_key", "") == ""

    # Identiti pegawai dalam /api/generate-draft WAJIB menggunakan profil sesi sah (bukan payload palsu)
    spoof_draft = client.post(
        "/api/generate-draft",
        headers=headers_a,
        json={
            "case_text": "Tarikh Kejadian: 18 November 2026\nNama Premis: Kedai Runcit Nerus\nKesalahan: pamer vape secara terbuka.",
            "akta_utama": "Akta 852",
            "workflow": "ip_builder",
            "use_ollama": False,
            "officer_profile": {
                "full_name": "PEGAWAI PALSU",
                "kkm_authority_card_no": "PALSU-999",
            },
        },
    )
    assert spoof_draft.status_code == 200
    draft_dump = json.dumps(spoof_draft.json(), ensure_ascii=False)
    assert "PEGAWAI PALSU" not in draft_dump
    assert "PPKP Ahmad Faizal bin Ramli" in draft_dump

    # ------------------------------------------------------------------
    # 2. KETEPATAN UNDANG-UNDANG (v2.6.0, AKTA A1742, AKTA 852 S.10/S.13(3))
    # ------------------------------------------------------------------
    status_res = client.get("/api/status").json()
    assert status_res["statute_library_version"] == "2.6.0-closed-book-agc-pdf"
    assert INITIAL_STATUTE_LIBRARY_VERSION == "2.6.0-closed-book-agc-pdf"

    snap = client.get("/api/legal/snapshot", headers=headers_a).json()
    offence_by_id = {o["offence_id"]: o for o in snap["master_offences_matrix"]}
    assert "AKTA_852_S13_3" in offence_by_id
    assert "AKTA_342_S22_B" in offence_by_id
    s24_text = json.dumps(offence_by_id["AKTA_342_S22_B"], ensure_ascii=False)
    assert "10,000" in s24_text or "10000" in s24_text
    assert "100,000" in s24_text or "100000" in s24_text
    assert "AKTA_852_S10_1" in offence_by_id
    assert offence_by_id["AKTA_852_S10_1"]["compound_info"]["is_compoundable"] is False

    # Seksyen palsu pada Akta 852 WAJIB ditolak oleh validate_legal_output
    fake_check = validate_legal_output(
        {
            "akta_disyorkan": "Akta 852",
            "cadangan_pertuduhan": [
                {
                    "perihal": "Kesalahan palsu",
                    "seksyen_kesalahan": "Seksyen 99 Akta 852",
                    "seksyen_hukuman": "Seksyen 99(2) Akta 852",
                    "hukuman_maksimum": "RM 50,000",
                    "boleh_kompaun": "Boleh Kompaun",
                }
            ],
        },
        snap,
        question_context="Ujian seksyen palsu Akta 852",
    )
    assert fake_check["passed"] is False
    assert len(fake_check["invalid_citations"]) >= 1

    # Senario kedai pamer vape: TIDAK boleh kompaun + sitaan S.49 + hukuman S.10(2)(a)/(b)
    pamer_res = client.post(
        "/api/advisor/consult",
        headers=headers_a,
        json={
            "question": "Kedai pamer vape secara terbuka di kaunter",
            "akta_hint": "Akta 852",
            "use_ai": False,
        },
    )
    assert pamer_res.status_code == 200
    pamer = pamer_res.json()
    assert pamer["status_kesalahan"] == "ADA_KESALAHAN"
    assert pamer["punca_kuasa"]["boleh_kompaun_flag"] is False
    pamer_dump = json.dumps(pamer, ensure_ascii=False)
    assert "49" in pamer_dump
    assert "10(2)(a)" in pamer_dump and "10(2)(b)" in pamer_dump

    # ------------------------------------------------------------------
    # 3. PENYEMAK NOTIS KOMPAUN (TIDAK BOLEH KOMPAUN, TEMPOH, PASPORT, OBD)
    # ------------------------------------------------------------------
    base_comp = {
        "no_notis": "KKM/852/2026/001",
        "nama_penerima": "Zulkifli bin Hassan",
        "no_kp": "850410-11-5011",
        "nama_premis": "Restoran Pantai Nerus",
        "alamat_kejadian": "Lot 12, Kg. Tok Jembal, 21300 Kuala Nerus, Terengganu",
        "no_ssm": "202101034892",
        "tarikh_masa": "18/11/2026 jam 10:30 pagi",
        "kesalahan_ringkas": "Menghisap rokok di kawasan makan larangan merokok",
        "pegawai_pengeluar": "PPKP Ahmad Faizal bin Ramli",
        "no_kad_kuasa": "KKM-TRG-A101",
    }

    # a) Seksyen 10(1) Akta 852 & Seksyen 13(1) Akta 281 tidak boleh dikompaun -> GAGAL pada K06
    nc_852 = client.post(
        "/api/check-compound",
        headers=headers_a,
        json={**base_comp, "peruntukan_undang": "Seksyen 10(1) Akta 852", "amaun_kompaun_rm": "RM 500", "tempoh_bayaran": "30 hari"},
    ).json()
    assert nc_852["counts"]["GAGAL"] >= 1
    assert any(c["code"] == "K06" and c["status"] == "GAGAL" for c in nc_852["checks"])

    nc_281 = client.post(
        "/api/check-compound",
        headers=headers_a,
        json={**base_comp, "peruntukan_undang": "Seksyen 13(1) Akta 281", "amaun_kompaun_rm": "RM 500", "tempoh_bayaran": "14 hari"},
    ).json()
    assert nc_281["counts"]["GAGAL"] >= 1
    assert any(c["code"] == "K06" and c["status"] == "GAGAL" for c in nc_281["checks"])

    # b) Tempoh bayaran salah (30 hari pada Akta 154; 14 hari pada Akta 852) -> GAGAL pada K08
    bad_win_154 = client.post(
        "/api/check-compound",
        headers=headers_a,
        json={**base_comp, "peruntukan_undang": "Seksyen 13(1) Akta 154", "amaun_kompaun_rm": "RM 500", "tempoh_bayaran": "30 hari"},
    ).json()
    assert any(c["code"] == "K08" and c["status"] == "GAGAL" for c in bad_win_154["checks"])

    bad_win_852 = client.post(
        "/api/check-compound",
        headers=headers_a,
        json={**base_comp, "peruntukan_undang": "Seksyen 16(2) Akta 852", "amaun_kompaun_rm": "RM 250", "tempoh_bayaran": "14 hari"},
    ).json()
    assert any(c["code"] == "K08" and c["status"] == "GAGAL" for c in bad_win_852["checks"])

    # c) Amaun julat ("RM 250 - RM 500") -> GAGAL pada K08
    range_amt = client.post(
        "/api/check-compound",
        headers=headers_a,
        json={**base_comp, "peruntukan_undang": "Seksyen 16(2) Akta 852", "amaun_kompaun_rm": "RM 250 - RM 500", "tempoh_bayaran": "30 hari"},
    ).json()
    assert any(c["code"] == "K08" and c["status"] == "GAGAL" for c in range_amt["checks"])

    # d) Pasport sah diterima (K02 LULUS) & MyKad OBD (<18 tahun) pada S.16(2) Akta 852 ditolak (GAGAL pada K06)
    passport_ok = client.post(
        "/api/check-compound",
        headers=headers_a,
        json={**base_comp, "nama_penerima": "Rahman Hossain", "no_kp": "A54321987", "peruntukan_undang": "Seksyen 16(2) Akta 852", "amaun_kompaun_rm": "RM 250", "tempoh_bayaran": "30 hari"},
    ).json()
    assert any(c["code"] == "K02" and c["status"] == "LULUS" for c in passport_ok["checks"])

    obd_mismatch = client.post(
        "/api/check-compound",
        headers=headers_a,
        json={**base_comp, "nama_penerima": "Pelajar Bawah Umur", "no_kp": "120515-11-5011", "peruntukan_undang": "Seksyen 16(2) Akta 852", "amaun_kompaun_rm": "RM 250", "tempoh_bayaran": "30 hari"},
    ).json()
    assert obd_mismatch["counts"]["GAGAL"] >= 1
    assert any(c["code"] == "K06" and c["status"] == "GAGAL" for c in obd_mismatch["checks"])

    # e) Akta 342 memaparkan Seksyen 25 Akta 342 [P.U. (A) 139/2025]
    akta342_comp = client.post(
        "/api/check-compound",
        headers=headers_a,
        json={**base_comp, "peruntukan_undang": "Seksyen 22(b) Akta 342", "amaun_kompaun_rm": "RM 1000", "tempoh_bayaran": "14 hari"},
    ).json()
    assert "P.U. (A) 139/2025" in akta342_comp["peruntukan_kompaun"]

    # ------------------------------------------------------------------
    # 4. PENJANA DOKUMEN WORD (.DOCX): INDEKS 7 BAHAGIAN (A-G) & BAHASA RASMI
    # ------------------------------------------------------------------
    full_docx_res = client.post(
        "/api/export-docx",
        headers=headers_a,
        json={"doc_type": "pakej_ip_lengkap", "payload": spoof_draft.json()},
    )
    assert full_docx_res.status_code == 200
    doc = DocxDocument(io.BytesIO(full_docx_res.content))
    full_text_parts = [p.text for p in doc.paragraphs]
    for tbl in doc.tables:
        for row in tbl.rows:
            for cell in row.cells:
                full_text_parts.append(cell.text)
    full_docx_text = "\n".join(full_text_parts)
    for part_letter in ["Bahagian A", "Bahagian B", "Bahagian C", "Bahagian D", "Bahagian E", "Bahagian F", "Bahagian G"]:
        assert part_letter in full_docx_text, f"Missing {part_letter} in Indeks Fail IP"
    assert "Bahagian H" not in full_docx_text
    assert "PERMOHONAN IZIN MENDAKWA (KEIZINAN PENDAKWA RAYA)" in full_docx_text
    assert "adalah dituduh" in full_docx_text
    assert "adalah dituntut" not in full_docx_text
    assert "mengperakui" not in full_docx_text

    comp_docx_res = client.post(
        "/api/export-docx",
        headers=headers_a,
        json={
            "doc_type": "notis_kompaun",
            "payload": {
                "no_notis": "KKM/852/2026/099",
                "nama_penerima": "Zulkifli bin Hassan",
                "no_kp": "850410-11-5011",
                "nama_premis": "Restoran Pantai",
                "alamat_premis": "Lot 12, Kg. Tok Jembal, Kuala Nerus",
                "tarikh_kesalahan": "18/11/2026",
                "masa_kesalahan": "09:15 pagi",
                "peruntukan_undang": "Seksyen 16(2) Akta 852",
                "amaun_kompaun_rm": "RM 250.00",
                "tempoh_bayaran_hari": "30 hari",
                "ringkasan_kesalahan": "Menghisap rokok di premis makanan larangan merokok.",
            },
        },
    )
    assert comp_docx_res.status_code == 200
    cdoc = DocxDocument(io.BytesIO(comp_docx_res.content))
    c_parts = [p.text for p in cdoc.paragraphs]
    for tbl in cdoc.tables:
        for row in tbl.rows:
            for cell in row.cells:
                c_parts.append(cell.text)
    comp_docx_text = "\n".join(c_parts)
    assert "Unit Hasil" in comp_docx_text or "UNIT HASIL" in comp_docx_text
    assert "Saksi" in comp_docx_text or "SAKSI" in comp_docx_text


def test_mall_multistorey_parking_smoking_s16_2_and_corrupt_context_guard() -> None:
    """Sahkan kes 'Merokok dalam kereta di parking bertingkat mall' memetik S.16(2) Akta 852 + Jadual Pertama P.U.(A) 257/2024
    (BUKAN Seksyen 3(1) import/edar), semua unsur S.16(2) tepat tanpa bocoran 'transaksi jualan',
    dan cache rosak konteks tertutup ditolak automatik."""
    from backend.core.database import _is_corrupted_or_fallback_qa
    from backend.rag.legal_engine import get_legal_library

    lib = get_legal_library()
    q = "Merokok dalam kereta di parking bertingkat mall"
    grounding = lib.search_closed_book_grounding(q, akta_hint="Semua")

    cand_ids = [o["offence_id"] for o in grounding["candidate_offences"]]
    assert "AKTA_852_S16_2" in cand_ids
    assert "AKTA_852_S3_1" not in cand_ids

    sec_ids = [s["doc_id"] for s in grounding["verbatim_sections"]]
    assert "AKTA_852__S16" in sec_ids
    assert "AKTA_852_PERINTAH_LARANGAN_2024__JADUAL_PERTAMA" in sec_ids

    s16_eval = grounding["candidate_offences"][0]["element_evaluation"]
    assert s16_eval["offence_id"] == "AKTA_852_S16_2"
    assert s16_eval["all_elements_satisfied"] is True
    notes_blob = " ".join(e["notes"] for e in s16_eval["element_evaluations"]).lower()
    assert "transaksi jualan" not in notes_blob
    assert "257/2024" in notes_blob

    # Ujian penuh endpoint /api/advisor/consult
    headers = _get_auth_headers()
    resp = client.post(
        "/api/advisor/consult",
        headers=headers,
        json={"question": q, "akta_hint": "Semua", "use_ai": False},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status_kesalahan"] == "ADA_KESALAHAN"
    assert "16(2)" in data["punca_kuasa"]["seksyen_kesalahan"]
    assert "257/2024" in data["punca_kuasa"]["seksyen_kesalahan"]
    assert data["punca_kuasa"]["boleh_kompaun_flag"] is True
    assert data["legal_validation"]["passed"] is True
    cit_ids = [c.get("doc_id") for c in data["statutory_citations"]]
    assert "AKTA_852__S16" in cit_ids
    assert "AKTA_852_PERINTAH_LARANGAN_2024__JADUAL_PERTAMA" in cit_ids

    # Pastikan jawapan cache lama yang bocor mesej 'dalam konteks statutori semasa' dikesan sebagai rosak
    assert _is_corrupted_or_fallback_qa(
        {
            "status_kesalahan": "TIADA_KESALAHAN",
            "ringkasan_keputusan": "TIADA KESALAHAN dapat dibuktikan di bawah peruntukan yang dibekalkan dalam konteks statutori semasa.",
            "sebab_tidak_menyalahi": "Tiada seksyen kesalahan merokok di kawasan larangan dibekalkan dalam konteks rujukan tertutup ini.",
        }
    ) is True


def test_four_expert_smart_grounding_cafeteria_s18_and_field_cases() -> None:
    """Ujian menyeluruh rombakan 4 pakar:
    1. Kes sebenar pengguna: Kafeteria universiti tiada tanda larangan merokok (alasan universiti sudah pasang di pintu masuk) -> ADA_KESALAHAN Seksyen 18(1)(a) Akta 852 + P.U.(A) 258/2024 + Boleh Kompaun.
    2. Penanda aras 14+ kes lapangan PPKP (Akta 852, 281/PPKM/PPM, 154, 342): tiada kebuluran retrieval, tiada pemotongan Jadual Pertama, dan katalog domain lengkap tersedia.
    3. Penjaga konflik fakta Q&A & pembersihan cache rosak.
    4. Pengesah pasca-penjanaan `validate_legal_output` tanpa false-positive sambil kekal menyekat kesalahan tulen.
    """
    from backend.core.database import _has_legal_fact_conflict, _is_corrupted_or_fallback_qa
    from backend.rag.legal_engine import (
        _has_active_smoking_action,
        _has_signage_or_premise_smoking_duty_signal,
        get_legal_library,
        infer_domain_statute_ids,
        validate_legal_output,
    )

    lib = get_legal_library()

    # ------------------------------------------------------------------
    # 1. KES SEBENAR PENGGUNA: KAFETERIA UNIVERSITI TIADA TANDA LARANGAN MEROKOK
    # ------------------------------------------------------------------
    q_cafe = (
        "dalam cafetaria sebuah universiti, tiada tanda larangan merokok dipasang. "
        "peniaga cafe atas alasan universiti dah pasang pintu masuk university. boleh kompaun?"
    )
    assert _has_active_smoking_action(q_cafe) is False
    assert _has_signage_or_premise_smoking_duty_signal(q_cafe) is True

    g_cafe = lib.search_closed_book_grounding(q_cafe, akta_hint="Semua")
    assert g_cafe["candidate_offences"], "Mesti memulangkan calon kesalahan bagi kes papan tanda kafe"
    assert g_cafe["candidate_offences"][0]["offence_id"] == "AKTA_852_S18_1"
    sec_ids_cafe = [s["doc_id"] for s in g_cafe["verbatim_sections"]]
    assert "AKTA_852__S18" in sec_ids_cafe
    assert "AKTA_852_PERATURAN_TANDA_2024__P2" in sec_ids_cafe
    assert "AKTA_852_PERATURAN_TANDA_2024__JADUAL_PERTAMA" in sec_ids_cafe
    assert "AKTA_852_PERINTAH_LARANGAN_2024__JADUAL_PERTAMA" in sec_ids_cafe
    assert "[KATALOG RINGKAS SEMUA KESALAHAN DOMAIN" in g_cafe["statutory_context_block"]

    # Semak evaluasi unsur S.18(1)(a) sahaja (BUKAN S.16(2) individu merokok!)
    s18_eval = g_cafe["candidate_offences"][0]["element_evaluation"]
    assert s18_eval["offence_id"] == "AKTA_852_S18_1"
    assert s18_eval["action_blocked"] is False

    # Semak penuh endpoint /api/advisor/consult (Mod Pantas)
    headers = _get_auth_headers()
    resp_cafe = client.post(
        "/api/advisor/consult",
        headers=headers,
        json={"question": q_cafe, "akta_hint": "Semua", "use_ai": False},
    )
    assert resp_cafe.status_code == 200
    d_cafe = resp_cafe.json()
    assert d_cafe["status_kesalahan"] == "ADA_KESALAHAN"
    assert d_cafe["akta_disyorkan"] == "Akta 852"
    assert "18(1)(a)" in d_cafe["punca_kuasa"]["seksyen_kesalahan"]
    assert "258/2024" in d_cafe["punca_kuasa"]["seksyen_kesalahan"]
    assert d_cafe["punca_kuasa"]["boleh_kompaun_flag"] is True
    assert d_cafe["legal_validation"]["passed"] is True
    assert all(ev["offence_id"] != "AKTA_852_S16_2" for ev in d_cafe["element_evaluations"])
    cit_ids_cafe = [c.get("doc_id") for c in d_cafe["statutory_citations"]]
    assert "AKTA_852__S18" in cit_ids_cafe
    assert "AKTA_852_PERATURAN_TANDA_2024__P2" in cit_ids_cafe
    # Pastikan alasan universiti / pintu masuk dijawab terus dalam penjelasan
    reason_blob = f"{d_cafe['alasan_keputusan']} {d_cafe['keputusan_tindakan']}".lower()
    assert "pintu masuk" in reason_blob or "universiti" in reason_blob or "tempat makan" in reason_blob
    # Pastikan draf kes juga merujuk S.18(1)(a) & BUKAN S.16(2)
    assert "18(1)(a)" in d_cafe["draf_teks_kes_cadangan"]

    # ------------------------------------------------------------------
    # 2. PENANDA ARAS 12 KES LAPANGAN PPKP (RETRIEVAL + DOMAIN ROUTING)
    # ------------------------------------------------------------------
    field_benchmark = [
        ("Orang merokok di kawasan parkir terbuka R&R lebuh raya, boleh kompaun?", "AKTA_852", "AKTA_852__S16"),
        ("Kedai runcit simpan rokok dalam kabinet bertutup legap tidak nampak dari luar", "AKTA_852", "AKTA_852__S10"),
        ("Kedai serbaneka jual vape kepada remaja 16 tahun tanpa semak kad pengenalan", "AKTA_852", "AKTA_852__S13"),
        ("Restoran sudah daftar FoSIM tetapi gagal pamer sijil pendaftaran di dinding premis", "PPKM_2009", "PPKM_2009__P8"),
        ("Pekerja dapur tidak ambil suntikan tifoid dan tidak pakai apron semasa masak", "PPKM_2009", "PPKM_2009__P31"),
        ("Restoran kena perintah tutup Seksyen 11 tetapi buka pintu untuk cuci dapur sahaja bukan jual makanan", "AKTA_281", "AKTA_281__S11"),
        ("Jumpa lipas dalam makanan yang dihidangkan kepada pelanggan di restoran", "AKTA_281", "AKTA_281__S13B"),
        ("Makanan tamat tarikh luput diasingkan dalam stor pelupusan khas bukan di rak jualan", "PPM_1985", "PPM_1985__P14"),
        ("Pemeriksaan rumah jumpa bekas kosong ada air bertakung tetapi tiada larva Aedes", "AKTA_154", "AKTA_154__S13"),
        ("Tapak pembinaan ingkar perintah pembersihan Seksyen 8 Akta 154, boleh kompaun RM500?", "AKTA_154", "AKTA_154__S8"),
        ("Tuan rumah kunci pagar dan enggan beri kerjasama semburan kabus fogging denggi", "AKTA_154", "AKTA_154__S21"),
        ("Wabak HFMD dikesan di sebuah taska swasta, seksyen apa untuk tutup premis?", "AKTA_342", "AKTA_342__S18"),
    ]
    for q_text, expected_statute, expected_doc in field_benchmark:
        g = lib.search_closed_book_grounding(q_text, akta_hint="Semua")
        inferred = infer_domain_statute_ids(q_text, akta_hint="Semua")
        assert expected_statute in inferred, f"Domain salah untuk '{q_text}': dapat {inferred}"
        doc_ids = [s["doc_id"] for s in g["verbatim_sections"]]
        assert expected_doc in doc_ids, f"Dokumen verbatim '{expected_doc}' tercicir bagi '{q_text}': dapat {doc_ids}"
        assert "[KATALOG RINGKAS SEMUA KESALAHAN DOMAIN" in g["statutory_context_block"]

    # Pastikan Jadual Pertama P.U.(A) 257/2024 diindeks PENUH termasuk item 12 (IPT) & item 28 (dobi)
    g_dobi = lib.search_closed_book_grounding("Ada orang merokok di dalam kedai dobi layan diri", akta_hint="Semua")
    dobi_docs = [s["doc_id"] for s in g_dobi["verbatim_sections"]]
    assert "AKTA_852_PERINTAH_LARANGAN_2024__JADUAL_PERTAMA" in dobi_docs

    # Pastikan konflik auto-swept P.U.(A) 258/2024 Peraturan 2 telah diperbetulkan kepada boleh kompaun
    p2_258 = next(
        (o for o in lib.master_offences_matrix if o.get("offence_id") == "AKTA_852_PERATURAN_TANDA_2024_PERATURAN_2"),
        None,
    )
    if p2_258 is not None:
        assert p2_258["compound_info"]["is_compoundable"] is True

    # ------------------------------------------------------------------
    # 3. PENJAGA KONFLIK FAKTA Q&A & CACHE ROSAK
    # ------------------------------------------------------------------
    assert _has_legal_fact_conflict(
        "Merokok di parkir terbuka R&R",
        "Merokok dalam kereta di parking bertingkat mall",
        {},
    ) is True
    assert _has_legal_fact_conflict(
        "dalam cafetaria universiti tiada tanda larangan merokok dipasang",
        "orang merokok dalam restoran di universiti",
        {},
    ) is True
    assert _has_legal_fact_conflict(
        "Juruwang restoran tidak ambil suntikan tifoid dan tidak pegang makanan",
        "Pekerja dapur tidak ambil suntikan tifoid semasa memasak",
        {},
    ) is True
    assert _is_corrupted_or_fallback_qa(
        {
            "status_kesalahan": "TIADA_KESALAHAN",
            "ringkasan_keputusan": "Sila rujuk teks penuh Akta 852 di UIP.",
            "sebab_tidak_menyalahi": "Tidak boleh dikompaun terhadap peniaga kafe kerana peruntukan tersebut hanya terpakai kepada individu merokok.",
        }
    ) is True

    # ------------------------------------------------------------------
    # 4. PENGESAH PASCA-PENJANAAN `validate_legal_output` (TIADA FALSE POSITIVE)
    # ------------------------------------------------------------------
    # a) Seksyen 90A(2) bersama Akta 852 & amaran had Akta 154 tidak disekat secara palsu
    valid_ai_sample = {
        "akta_disyorkan": "Akta 852",
        "status_kesalahan": "ADA_KESALAHAN",
        "tajuk_nasihat": "Kegagalan Mempamerkan Tanda Larangan Merokok di Kafeteria Universiti",
        "keputusan_tindakan": "ADA KESALAHAN — Keluarkan Notis Seksyen 47 dan tawarkan kompaun Seksyen 48 Akta 852.",
        "alasan_keputusan": (
            "Pemunya kafe melanggar Seksyen 18(1)(a) Akta 852 dibaca bersama Peraturan 2(1) P.U. (A) 258/2024. "
            "Sertakan gambar bersama Sijil Seksyen 90A(2) Akta Keterangan 1950. "
            "Berbeza dengan PPKHT 2004 yang telah dimansuhkan, Akta 852 mengawal selia kewajipan ini secara tegas."
        ),
        "cadangan_pertuduhan": [
            {
                "perihal": "Gagal mempamerkan tanda larangan merokok mengikut spesifikasi",
                "seksyen_kesalahan": "Seksyen 18(1)(a) Akta 852 dibaca bersama Peraturan 2(1) P.U. (A) 258/2024",
                "seksyen_hukuman": "Seksyen 18(2) Akta 852",
                "hukuman_maksimum": "Denda maksimum RM5,000.00",
                "boleh_kompaun": "Boleh Kompaun — RM250 hingga RM2,500 (tempoh 30 hari)",
            }
        ],
    }
    v_ok = validate_legal_output(valid_ai_sample, lib.to_snapshot_dict(), question_context=q_cafe)
    assert v_ok["passed"] is True, f"Sepatutnya LULUS tetapi gagal: {v_ok}"

    # b) Kompaun korporat Akta 342 RM50,000 diluluskan, manakala Akta 154 RM1,000 aktif DISEKAT
    corp_342_sample = {
        "akta_disyorkan": "Akta 342",
        "status_kesalahan": "ADA_KESALAHAN",
        "keputusan_tindakan": "Syarikat boleh dikenakan kompaun RM50,000 di bawah Seksyen 25 Akta 342 (Pindaan Akta A1742).",
        "alasan_keputusan": "Seksyen 25 Akta 342 membenarkan had kompaun korporat sehingga RM50,000 bagi pertubuhan perbadanan.",
        "cadangan_pertuduhan": [],
    }
    assert validate_legal_output(corp_342_sample, lib.to_snapshot_dict(), question_context="Kilang ingkar arahan Akta 342")["passed"] is True

    warn_154_sample = {
        "akta_disyorkan": "Akta 154",
        "status_kesalahan": "ADA_KESALAHAN",
        "keputusan_tindakan": "Buka IP Terus di bawah Seksyen 8(8) Akta 154.",
        "alasan_keputusan": "Jangan keluarkan kompaun RM1,000 di bawah Akta 154 kerana melebihi had RM500 dan tidak sah.",
        "cadangan_pertuduhan": [],
    }
    assert validate_legal_output(warn_154_sample, lib.to_snapshot_dict(), question_context="Tapak binaan ingkar perintah Seksyen 8 Akta 154")["passed"] is True

    bad_154_sample = {
        "akta_disyorkan": "Akta 154",
        "status_kesalahan": "ADA_KESALAHAN",
        "keputusan_tindakan": "Tawarkan kompaun RM1,000 di bawah Seksyen 25 Akta 154.",
        "alasan_keputusan": "Keluarkan kompaun RM1,000 segera.",
        "cadangan_pertuduhan": [],
    }
    assert validate_legal_output(bad_154_sample, lib.to_snapshot_dict(), question_context="Pembiakan Aedes di rumah")["passed"] is False

    bad_sec_sample = {
        "akta_disyorkan": "Akta 852",
        "status_kesalahan": "ADA_KESALAHAN",
        "keputusan_tindakan": "Tuduh di bawah Seksyen 99 Akta 852.",
        "alasan_keputusan": "Kesalahan di bawah Seksyen 99 Akta 852.",
        "cadangan_pertuduhan": [],
    }
    assert validate_legal_output(bad_sec_sample, lib.to_snapshot_dict(), question_context="Merokok di restoran")["passed"] is False




