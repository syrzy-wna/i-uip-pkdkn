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
    _CACHED_TEST_HEADERS = {"Authorization": f"Bearer {res.json()['token']}"}
    return _CACHED_TEST_HEADERS


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
            "kkm_authority_card_no": "KKM-SEL-U32-991",
            "district_pkd": "Pejabat Kesihatan Daerah Hulu Langat",
            "default_computer_desc": "Komputer Meja HP EliteDesk PKD Hulu Langat",
            "default_camera_desc": "Kamera Digital Canon EOS PKD Hulu Langat",
        },
    )
    assert resp_reg.status_code == 200
    reg_body = resp_reg.json()
    assert reg_body["user"]["email"] == unique_email
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
    assert resp_me.json()["user"]["kkm_authority_card_no"] == "KKM-SEL-U32-991"

    resp_upd = client.put(
        "/api/auth/profile",
        headers=headers,
        json={"grade": "U36"},
    )
    assert resp_upd.status_code == 200
    assert resp_upd.json()["user"]["grade"] == "U36"

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
    assert len(scenarios) == 11
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
    assert elapsed_obd < 2.0

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
    g_email = f"ppkp.nerus.{uuid.uuid4().hex[:6]}@gmail.com"
    client.post("/api/settings", headers=_get_auth_headers(), json={"google_client_id": ""})

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
            "grade": "U32",
        },
    )
    assert resp_first.status_code == 200
    b1 = resp_first.json()
    assert b1["is_new_account"] is True
    assert b1["user"]["email"] == g_email
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


def test_dev_overview_tracks_who_uses_what_and_api_costs(monkeypatch) -> None:
    import uuid
    import httpx

    # 1. Uji simpan & dapatkan google_client_id melalui /api/settings
    headers = _get_auth_headers()
    client_id_test = f"123456-{uuid.uuid4().hex[:6]}.apps.googleusercontent.com"
    resp_save = client.post("/api/settings", headers=headers, json={"google_client_id": client_id_test})
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

    # 3. Semak /api/dev/overview memaparkan siapa guna & apa dibuat + anggaran kos
    dev_resp = client.get("/api/dev/overview", headers={"Authorization": f"Bearer {token}"})
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
    from backend.core.config import DEFAULT_GOOGLE_CLIENT_ID
    client.post("/api/settings", headers=headers, json={"google_client_id": DEFAULT_GOOGLE_CLIENT_ID})


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
    from backend.core.config import DEFAULT_GOOGLE_CLIENT_ID
    from backend.core.database import _PgConnAdapter

    for path in ("/healthz", "/api/health"):
        resp = client.get(path)
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok", "db": "sqlite"}

    assert (
        _PgConnAdapter._translate_sql("SELECT * FROM users WHERE email = ? AND id = ?")
        == "SELECT * FROM users WHERE email = %s AND id = %s"
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
