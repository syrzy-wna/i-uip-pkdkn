"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  CheckSquare,
  ExternalLink,
  FileSearch,
  Loader2,
  Lock,
  Play,
  Sparkles,
} from "lucide-react";
import AppGuidePanel from "@/components/AppGuidePanel";
import AuditPanel from "@/components/AuditPanel";
import AuthAccountModal from "@/components/AuthAccountModal";
import CaseRegistryModal from "@/components/CaseRegistryModal";
import CompoundNoticePanel from "@/components/CompoundNoticePanel";
import DevConsoleModal from "@/components/DevConsoleModal";
import DraftDocxEditor from "@/components/DraftDocxEditor";
import LeftEvidencePane from "@/components/LeftEvidencePane";
import MobileBottomNav from "@/components/MobileBottomNav";
import RedactionPreview from "@/components/RedactionPreview";
import SplashScreenModal from "@/components/SplashScreenModal";
import SystemSettingsModal from "@/components/SystemSettingsModal";
import TopNavbar, { type ActiveAppMode } from "@/components/TopNavbar";
import UIPAdvisorPanel from "@/components/UIPAdvisorPanel";
import WorkspaceStepper from "@/components/WorkspaceStepper";
import {
  extractEvidence,
  fetchCases,
  fetchCurrentOfficer,
  fetchSampleCases,
  fetchSystemStatus,
  generateDrafts,
  queryStatutoryRag,
  runIpAudit,
  runRedaction,
  saveCaseRecord,
} from "@/lib/api";
import type {
  DraftGenerationResponse,
  EvidenceExtractionResponse,
  IPAuditReport,
  IPCaseRecord,
  NotisKompaunData,
  OfficerProfile,
  RedactResponse,
  StatutoryCitation,
  SystemStatus,
  WorkflowMode,
} from "@/lib/types";

type RightTab = ActiveAppMode;

const EMPTY_COMPOUND_NOTICE: NotisKompaunData = {
  no_notis: "",
  nama_penerima: "",
  no_kp: "",
  nama_premis: "",
  alamat_kejadian: "",
  no_ssm: "",
  tarikh_masa: "",
  peruntukan_undang: "",
  peruntukan_kompaun: "",
  kesalahan_ringkas: "",
  amaun_kompaun_rm: "",
  tempoh_bayaran: "",
  pegawai_pengeluar: "",
  no_kad_kuasa: "",
  status_serahan: "tandatangan_terima",
  saksi_ppkp: "",
};

function buildCompoundFromCase(
  rec: IPCaseRecord,
  officer?: OfficerProfile | null
): NotisKompaunData {
  if (rec.draft?.notis_kompaun) {
    return { ...EMPTY_COMPOUND_NOTICE, ...rec.draft.notis_kompaun };
  }
  return {
    ...EMPTY_COMPOUND_NOTICE,
    no_notis: rec.no_ip ? `KKM/KOM/${rec.no_ip.split("/").pop()}` : "",
    nama_penerima: rec.nama_okt || "",
    no_kp: rec.no_kp_okt || "",
    nama_premis: rec.nama_premis || "",
    alamat_kejadian: rec.alamat_kejadian || "",
    no_ssm: rec.no_ssm || "",
    tarikh_masa: [rec.tarikh_kejadian, rec.masa_kejadian].filter(Boolean).join(", "),
    peruntukan_undang:
      rec.akta_utama === "Akta 852"
        ? "Seksyen 10(1) Akta 852 dibaca bersama Peraturan 6 P.U. (A) 260/2024"
        : rec.akta_utama === "Akta 154"
          ? "Seksyen 13(1) dibaca bersama Seksyen 13(2) Akta 154"
          : "Peraturan 11(1) PPKM 2009 [P.U. (A) 95/2009]",
    peruntukan_kompaun:
      rec.akta_utama === "Akta 852"
        ? "Seksyen 48 Akta 852 [P.U. (A) 259/2024]"
        : rec.akta_utama === "Akta 154"
          ? "Seksyen 25 Akta 154 (Maksimum RM500)"
          : "Notis Seksyen 32B & Seksyen 33 Akta Makanan 1983",
    amaun_kompaun_rm: "RM 500.00",
    tempoh_bayaran:
      rec.akta_utama === "Akta 852"
        ? "30 hari dari tarikh tawaran kompaun"
        : "14 hari dari tarikh serahan notis",
    pegawai_pengeluar: rec.pegawai_io || officer?.full_name || "",
    no_kad_kuasa: rec.no_kad_kuasa || officer?.kkm_authority_card_no || "",
  };
}

function buildBlankDraft(
  aktaUtama: string,
  officer: OfficerProfile | null,
  compound: NotisKompaunData
): DraftGenerationResponse {
  return {
    workflow: "ip_builder",
    akta_utama: aktaUtama || "Akta 852",
    minit_ip: [
      {
        bil: "Minit 1",
        tarikh: "",
        daripada: "Pegawai Penyiasat (IO)",
        kepada: "UIP / TPR",
        kandungan: "Kertas Siasatan dibuka untuk tindakan dan arahan lanjut.",
      },
    ],
    kronologi_kes: [{ tarikh: "", peristiwa: "Pemeriksaan premis / operasi penguatkuasaan dijalankan." }],
    kertas_cadangan_io: "Mohon pertimbangan dan izin mendakwa daripada Timbalan Pendakwa Raya (TPR).",
    saman_111: {
      mahkamah:
        officer?.default_magistrate_court ||
        "MAHKAMAH MAJISTRET DI KUALA TERENGGANU, TERENGGANU DARUL IMAN",
      tarikh_hadir: "",
      masa_hadir: "09.00 pagi",
    },
    pemberatan_hukuman: [
      "Kesalahan ini melibatkan kepentingan kesihatan awam dan keselamatan masyarakat setempat.",
    ],
    borang_114: {
      mahkamah:
        officer?.default_magistrate_court ||
        "MAHKAMAH MAJISTRET DI KUALA TERENGGANU, TERENGGANU DARUL IMAN",
      no_kes: "",
      nama_tertuduh: compound.nama_penerima || "",
      no_kp_tertuduh: compound.no_kp || "",
      umur_jantina: "",
      pekerjaan: "",
      alamat_tertuduh: compound.alamat_kejadian || "",
      tarikh_kejadian: "",
      masa_kejadian: "",
      tempat_kejadian: compound.alamat_kejadian || "",
      akta_dan_seksyen: compound.peruntukan_undang || "",
      seksyen_hukuman: "",
      hukuman_maksimum: "",
      teks_pertuduhan: "",
    },
    diari_siasatan: [
      {
        bil: "1",
        tarikh: "",
        masa: "",
        butiran_tindakan: "Terima aduan / jalankan pemeriksaan di lokasi kejadian.",
        pegawai: officer?.full_name || "PPKP / IO",
      },
    ],
    fakta_kes: "",
    rakaman_112: "",
    senarai_saksi: [
      {
        bil: "SP1",
        nama: officer?.full_name || "",
        no_kp: "",
        jawatan_peranan: "Pegawai Pengadu / Penyiasat",
        alamat_hubungan: officer?.district_pkd || "PKD Kuala Nerus",
      },
    ],
    senarai_eksibit: [
      {
        tanda: "P1",
        perihal: "Gambar foto tempat kejadian dan barang bukti digital",
        no_lak_seal: "-",
        lokasi_simpanan: "Stor Eksibit PKD Kuala Nerus",
      },
    ],
    sijil_90a: {
      nama_pegawai: officer?.full_name || "",
      jawatan: `${officer?.designation || "PPKP"} Gred ${officer?.grade || "U5"}`,
      pejabat_pkd: officer?.district_pkd || "Pejabat Kesihatan Daerah Kuala Nerus",
      peranti_kamera: officer?.default_camera_desc || "Kamera Digital Rasmi Pejabat KKM",
      perihal_komputer:
        officer?.default_computer_desc || "Komputer Meja Rasmi KKM Pejabat PKD Kuala Nerus",
      perihal_pencetak: officer?.default_printer_desc || "Pencetak Laser Warna Pejabat PKD",
      senarai_dokumen_digital: "Gambar foto pemeriksaan premis & cetakan Carian Rasmi SSM",
    },
    notis_kompaun: compound,
    tpr_simulation_notes: [],
    statutory_citations: [],
    redaction_preview: {
      engine_used: "manual",
      ollama_available: false,
      entities_masked: 0,
      rehydrated: true,
      redacted_excerpt: "",
      token_map: {},
    },
    models_used: { legal_reasoning: "manual-editor" },
  };
}

export default function UIPCommandPage() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [cases, setCases] = useState<IPCaseRecord[]>([]);
  const [activeCaseId, setActiveCaseId] = useState<string>("");
  const [workflow, setWorkflow] = useState<WorkflowMode>("audit_ip");
  const [aktaUtama, setAktaUtama] = useState<string>("Akta 852");
  const [useOllama, setUseOllama] = useState<boolean>(true);
  const [caseText, setCaseText] = useState<string>("");

  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [fileTriggerNonce, setFileTriggerNonce] = useState(0);

  const [activeTab, setActiveTab] = useState<RightTab>("audit");
  const [auditReport, setAuditReport] = useState<IPAuditReport | null>(null);
  const [redaction, setRedaction] = useState<RedactResponse | null>(null);
  const [draft, setDraft] = useState<DraftGenerationResponse | null>(null);
  const [compoundNotice, setCompoundNotice] =
    useState<NotisKompaunData>(EMPTY_COMPOUND_NOTICE);
  const [extractedEvidence, setExtractedEvidence] =
    useState<EvidenceExtractionResponse | null>(null);
  const [ragResults, setRagResults] = useState<StatutoryCitation[]>([]);

  const [auditLoading, setAuditLoading] = useState(false);
  const [draftLoading, setDraftLoading] = useState(false);
  const [redactLoading, setRedactLoading] = useState(false);
  const [extractLoading, setExtractLoading] = useState(false);
  const [ragLoading, setRagLoading] = useState(false);
  const [savingCase, setSavingCase] = useState(false);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [editorTargetSection, setEditorTargetSection] = useState<string | null>(null);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);
  const [toastMsg, setToastMsg] = useState<string | null>(null);

  const [settingsOpen, setSettingsOpen] = useState(false);
  const [devConsoleOpen, setDevConsoleOpen] = useState(false);
  const [registryOpen, setRegistryOpen] = useState(false);
  const [registryInitialMode, setRegistryInitialMode] = useState<"list" | "new">("list");
  const [authOpen, setAuthOpen] = useState(false);
  const [authInitialTab, setAuthInitialTab] = useState<"google" | "login" | "register" | "profile">("google");
  const [splashOpen, setSplashOpen] = useState(false);
  const [mobileSplitPane, setMobileSplitPane] = useState<"input" | "result">("input");
  const [authToken, setAuthToken] = useState<string | null>(null);
  const [officer, setOfficer] = useState<OfficerProfile | null>(null);
  const [authChecked, setAuthChecked] = useState(false);

  const showToast = useCallback((msg: string) => {
    setToastMsg(msg);
    window.setTimeout(() => {
      setToastMsg((prev) => (prev === msg ? null : prev));
    }, 3600);
  }, []);

  const applyCaseRecord = useCallback(
    (rec: IPCaseRecord, currentOfficer?: OfficerProfile | null) => {
      setActiveCaseId(rec.id);
      setAktaUtama(rec.akta_utama);
      setWorkflow(rec.workflow || "audit_ip");
      setCaseText(rec.case_text || "");
      setAuditReport(rec.audit_report || null);
      setDraft(rec.draft || null);
      setRedaction(null);
      setCompoundNotice(buildCompoundFromCase(rec, currentOfficer));
      setHasUnsavedChanges(false);
      setErrorBanner(null);
    },
    []
  );

  useEffect(() => {
    let mounted = true;
    async function bootstrap() {
      try {
        const savedToken =
          typeof window !== "undefined" ? window.localStorage.getItem("uip_auth_token") : null;
        const sysStatus = await fetchSystemStatus();
        if (!mounted) return;
        setStatus(sysStatus);

        if (savedToken) {
          try {
            const me = await fetchCurrentOfficer(savedToken);
            const caseList = await fetchCases();
            if (!mounted) return;
            setAuthToken(savedToken);
            setOfficer(me);
            setCases(caseList);
            if (caseList.length > 0) {
              applyCaseRecord(caseList[0], me);
            }
          } catch {
            if (typeof window !== "undefined") {
              window.localStorage.removeItem("uip_auth_token");
            }
            if (mounted) setSplashOpen(true);
          }
        } else if (mounted) {
          setSplashOpen(true);
        }
      } catch (err) {
        if (!mounted) return;
        setErrorBanner(
          err instanceof Error
            ? `Pelayan Backend FastAPI tidak dapat dicapai: ${err.message}`
            : "Gagal menyambung ke Backend API."
        );
      } finally {
        if (mounted) setAuthChecked(true);
      }
    }
    bootstrap();
    return () => {
      mounted = false;
    };
  }, [applyCaseRecord]);

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  const handleFileSelected = useCallback(
    (file: File | null) => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
      setUploadedFile(file);
      setExtractedEvidence(null);
      if (file) {
        const url = URL.createObjectURL(file);
        setPreviewUrl(url);
      } else {
        setPreviewUrl(null);
      }
    },
    [previewUrl]
  );

  const handleSelectMode = (mode: ActiveAppMode) => {
    setActiveTab(mode);
    if (mode === "compound") setWorkflow("notis_kompaun");
    else if (mode === "draft") setWorkflow("ip_builder");
    else if (mode === "audit" || mode === "redaction") setWorkflow("audit_ip");

    if (mode === "compound" || mode === "redaction" || mode === "draft" || mode === "audit") {
      setMobileSplitPane("result");
    }
    if (typeof window !== "undefined") {
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  };

  const handleStartBlankCase = () => {
    setActiveCaseId("");
    setCaseText("");
    setAuditReport(null);
    setDraft(null);
    setRedaction(null);
    setExtractedEvidence(null);
    handleFileSelected(null);
    setCompoundNotice({
      ...EMPTY_COMPOUND_NOTICE,
      pegawai_pengeluar: officer?.full_name || "",
      no_kad_kuasa: officer?.kkm_authority_card_no || "",
    });
    setHasUnsavedChanges(false);
    setErrorBanner(null);
    showToast("Sedia untuk kes baharu — sila tarik fail atau taip fakta kes.");
  };

  const handleLoadSampleCase = async () => {
    setErrorBanner(null);
    if (cases.length > 0) {
      applyCaseRecord(cases[0], officer);
      showToast(`Contoh kes dimuatkan: ${cases[0].tajuk_kes}`);
      return;
    }
    try {
      const samples = await fetchSampleCases();
      if (samples.length > 0) {
        const s = samples[0];
        setActiveCaseId("");
        setAktaUtama(s.akta_utama);
        setCaseText(s.text);
        setAuditReport(null);
        setDraft(null);
        showToast(`Contoh kes dimuatkan: ${s.title}`);
      }
    } catch (err) {
      setErrorBanner(err instanceof Error ? err.message : "Gagal memuatkan contoh kes.");
    }
  };

  const handleSaveCurrentCase = async () => {
    setSavingCase(true);
    setErrorBanner(null);
    try {
      const draftToSave = draft ? { ...draft, notis_kompaun: compoundNotice } : null;
      const saved = await saveCaseRecord({
        id: activeCaseId || undefined,
        akta_utama: aktaUtama,
        workflow,
        case_text: caseText,
        nama_okt: compoundNotice.nama_penerima || undefined,
        no_kp_okt: compoundNotice.no_kp || undefined,
        nama_premis: compoundNotice.nama_premis || undefined,
        no_ssm: compoundNotice.no_ssm || undefined,
        alamat_kejadian: compoundNotice.alamat_kejadian || undefined,
        status_kes: auditReport?.readiness_status || "DALAM SIASATAN",
        skor_audit: auditReport?.overall_score || 0,
        audit_report: auditReport,
        draft: draftToSave,
      });
      setActiveCaseId(saved.id);
      setCases((prev) => {
        const exists = prev.some((c) => c.id === saved.id);
        return exists ? prev.map((c) => (c.id === saved.id ? saved : c)) : [saved, ...prev];
      });
      setHasUnsavedChanges(false);
      showToast("Fail kes & semua perubahan berjaya disimpan!");
    } catch (err) {
      setErrorBanner(err instanceof Error ? err.message : "Gagal menyimpan kes PKD.");
    } finally {
      setSavingCase(false);
    }
  };

  const handleRunAudit = async () => {
    if (!caseText.trim() && !uploadedFile) {
      setErrorBanner("Sila masukkan catatan fakta kes atau muat naik fail PDF/DOCX/gambar dahulu.");
      setMobileSplitPane("input");
      return;
    }
    setAuditLoading(true);
    setErrorBanner(null);
    try {
      const report = await runIpAudit({
        text: caseText,
        aktaUtama,
        useOllama,
        caseId: activeCaseId || undefined,
        file: uploadedFile,
      });
      setAuditReport(report);
      if (report.extracted_text && uploadedFile) {
        setCaseText(report.extracted_text);
      }
      setRedaction({
        original_text: report.extracted_text || caseText,
        redacted_text: report.redaction_summary.redacted_text,
        token_map: report.redaction_summary.token_map,
        entities: report.redaction_summary.entities,
        engine_used: report.redaction_summary.engine_used,
        ollama_available: report.redaction_summary.ollama_available,
        warnings: report.redaction_summary.warnings,
      });
      setCases((prev) =>
        prev.map((c) =>
          c.id === activeCaseId
            ? {
                ...c,
                status_kes: report.readiness_status,
                skor_audit: report.overall_score,
                audit_report: report,
              }
            : c
        )
      );
      setActiveTab("audit");
      setMobileSplitPane("result");
      showToast(`Semakan IP siap — Skor ${report.overall_score}%`);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      setErrorBanner(err instanceof Error ? err.message : "Gagal menyemak IP.");
    } finally {
      setAuditLoading(false);
    }
  };

  const handleRunDraft = async (targetSection?: string) => {
    let workingText = caseText.trim();
    if (!workingText && uploadedFile) {
      setDraftLoading(true);
      setErrorBanner(null);
      try {
        const ext = await extractEvidence(uploadedFile, "kertas_siasatan_pdf");
        setExtractedEvidence(ext);
        if (ext.raw_text?.trim()) {
          workingText = ext.raw_text.trim();
          setCaseText(workingText);
        }
      } catch (err) {
        setDraftLoading(false);
        setErrorBanner(
          err instanceof Error
            ? `Gagal membaca fail dimuat naik: ${err.message}`
            : "Gagal membaca fail dimuat naik."
        );
        return;
      }
    }

    if (!workingText) {
      setErrorBanner("Sila masukkan catatan fakta kes atau muat naik fail kes di Langkah 1 dahulu.");
      setMobileSplitPane("input");
      return;
    }

    setDraftLoading(true);
    setErrorBanner(null);
    try {
      const draftRes = await generateDrafts({
        caseText: workingText,
        aktaUtama,
        workflow,
        useOllama,
        fastMode: true,
        caseId: activeCaseId || undefined,
        authToken,
        officerProfile: officer,
      });
      setDraft(draftRes);
      setHasUnsavedChanges(true);
      if (draftRes.redaction_preview) {
        setRedaction({
          original_text: workingText,
          redacted_text:
            draftRes.redaction_preview.redacted_text || draftRes.redaction_preview.redacted_excerpt,
          token_map: draftRes.redaction_preview.token_map,
          entities: draftRes.redaction_preview.entities || [],
          engine_used: draftRes.redaction_preview.engine_used,
          ollama_available: draftRes.redaction_preview.ollama_available,
          warnings: draftRes.redaction_preview.warnings || [],
        });
      }
      if (draftRes.notis_kompaun) {
        setCompoundNotice((prev) => ({
          ...prev,
          ...draftRes.notis_kompaun,
        }));
      }
      if (targetSection) {
        setEditorTargetSection(targetSection);
      }
      if (workflow !== "notis_kompaun") {
        setActiveTab("draft");
      }
      setMobileSplitPane("result");
      showToast("Draf dokumen IP berjaya dijana — klik mana-mana kotak putih untuk edit!");
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      setErrorBanner(err instanceof Error ? err.message : "Gagal menjana draf dokumen.");
    } finally {
      setDraftLoading(false);
    }
  };

  const handleAutoFillCompound = async () => {
    setErrorBanner(null);
    const activeCase = cases.find((c) => c.id === activeCaseId);
    if (activeCase) {
      setCompoundNotice(buildCompoundFromCase(activeCase, officer));
    }
    if (!caseText.trim() && !uploadedFile) {
      if (activeCase) {
        showToast("Butiran asas kes aktif telah ditarik ke borang kompaun.");
      } else {
        setErrorBanner(
          "Tiada teks kes atau fail dimuat naik. Anda boleh isi borang ini secara manual atau tekan 'Imbas Foto Notis / SSM'."
        );
      }
      return;
    }

    setDraftLoading(true);
    try {
      let workingText = caseText.trim();
      if (!workingText && uploadedFile) {
        const ext = await extractEvidence(uploadedFile, "sijil_ssm");
        setExtractedEvidence(ext);
        workingText = ext.raw_text?.trim() || "";
        if (workingText) setCaseText(workingText);
      }
      if (!workingText) {
        setDraftLoading(false);
        return;
      }
      const draftRes = await generateDrafts({
        caseText: workingText,
        aktaUtama,
        workflow: "notis_kompaun",
        useOllama,
        fastMode: true,
        caseId: activeCaseId || undefined,
        authToken,
        officerProfile: officer,
      });
      if (draftRes.notis_kompaun) {
        setCompoundNotice((prev) => ({ ...prev, ...draftRes.notis_kompaun }));
        setHasUnsavedChanges(true);
        showToast("Data kes & seksyen berjaya diisi ke Borang Notis Kompaun!");
      }
    } catch (err) {
      setErrorBanner(err instanceof Error ? err.message : "Gagal menarik data ke borang kompaun.");
    } finally {
      setDraftLoading(false);
    }
  };

  const handleStartBlankDraft = () => {
    const blank = buildBlankDraft(aktaUtama, officer, compoundNotice);
    setDraft(blank);
    setHasUnsavedChanges(true);
    setActiveTab("draft");
    setMobileSplitPane("result");
    showToast("Borang IP kosong dibuka — semua ruangan sedia untuk ditaip.");
  };

  const handleRunRedaction = async () => {
    if (!caseText.trim()) {
      setErrorBanner("Tiada catatan teks kes untuk disemak penyamaran data peribadi.");
      setMobileSplitPane("input");
      return;
    }
    setRedactLoading(true);
    setErrorBanner(null);
    try {
      const res = await runRedaction(caseText, useOllama);
      setRedaction(res);
      setActiveTab("redaction");
      setMobileSplitPane("result");
      showToast(`${res.entities.length} data peribadi dikenal pasti & ditutup.`);
    } catch (err) {
      setErrorBanner(err instanceof Error ? err.message : "Gagal menyamarkan data sulit.");
    } finally {
      setRedactLoading(false);
    }
  };

  const handleExtractEvidence = async (docHint: string, replaceText = false) => {
    if (!uploadedFile) return;
    setExtractLoading(true);
    setErrorBanner(null);
    try {
      const res = await extractEvidence(uploadedFile, docHint);
      setExtractedEvidence(res);
      if (res.raw_text) {
        setCaseText((prev) =>
          !replaceText && prev.trim()
            ? `${prev.trim()}\n\n--- HASIL BACAAN FAIL (${res.filename}) ---\n${res.raw_text}`
            : res.raw_text
        );
        setHasUnsavedChanges(true);
      }
      showToast(`Teks berjaya dibaca daripada fail ${res.filename}!`);
    } catch (err) {
      setErrorBanner(err instanceof Error ? err.message : "Gagal membaca fail bukti.");
    } finally {
      setExtractLoading(false);
    }
  };

  const handleSearchRag = async (query: string) => {
    if (!query.trim()) return;
    setRagLoading(true);
    setErrorBanner(null);
    try {
      const res = await queryStatutoryRag(query, aktaUtama);
      setRagResults(res.results);
    } catch (err) {
      setErrorBanner(err instanceof Error ? err.message : "Gagal mencari teks akta.");
    } finally {
      setRagLoading(false);
    }
  };

  const closeSplashAndRemember = () => {
    if (!officer) return;
    setSplashOpen(false);
    if (typeof window !== "undefined") {
      window.sessionStorage.setItem("iuip_nerus_splash_seen", "1");
    }
  };

  const handleAuthenticatedSuccess = async (user: OfficerProfile, token: string) => {
    window.localStorage.setItem("uip_auth_token", token);
    setAuthToken(token);
    setOfficer(user);
    setSplashOpen(false);
    setAuthOpen(false);
    try {
      const caseList = await fetchCases();
      setCases(caseList);
      if (caseList.length > 0) {
        applyCaseRecord(caseList[0], user);
      }
    } catch {
      // Abaikan jika gagal sementara
    }
  };

  if (!authChecked) {
    return (
      <div className="flex min-h-[100dvh] items-center justify-center bg-[#08192e] p-6 text-white">
        <div className="flex max-w-sm flex-col items-center space-y-4 text-center">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/images/logo-iuip-nerus.png"
            alt="Logo i-UIP Nerus"
            className="h-20 w-20 rounded-full bg-white p-1 object-contain shadow-lg ring-2 ring-amber-400"
          />
          <div className="rounded-xl bg-white/95 px-3 py-1.5 shadow-md">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src="/images/logo-pkdkn.png"
              alt="Logo PKD Kuala Nerus"
              className="h-9 w-auto object-contain"
            />
          </div>
          <div className="space-y-1">
            <div className="text-xl font-extrabold tracking-tight text-amber-300">i-UIP Nerus</div>
            <p className="text-[11px] italic text-amber-100/90">
              &ldquo;Satu Hati, Satu Tekad: Memacu Kecemerlangan Kesihatan Kuala Nerus&rdquo;
            </p>
            <div className="pt-1 text-xs text-slate-300">
              Mengesahkan sesi pegawai PKD Kuala Nerus...
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!officer) {
    return (
      <div className="min-h-[100dvh] bg-[#08192e]">
        <SplashScreenModal
          open={!authOpen}
          officer={null}
          onClose={() => {}}
          onEnterApp={() => {
            setAuthInitialTab("google");
            setAuthOpen(true);
          }}
          onOpenGoogleAuth={() => {
            setAuthInitialTab("google");
            setAuthOpen(true);
          }}
          onOpenEmailAuth={(tabChoice) => {
            setAuthInitialTab(tabChoice);
            setAuthOpen(true);
          }}
        />
        <AuthAccountModal
          open={authOpen}
          onClose={() => setAuthOpen(false)}
          officer={null}
          authToken={null}
          initialTab={authInitialTab}
          onAuthenticated={handleAuthenticatedSuccess}
          onProfileUpdated={() => {}}
          onLoggedOut={() => {}}
        />
      </div>
    );
  }

  const isFullWidthMode = activeTab === "advisor" || activeTab === "guide";
  const isDevAdmin = Boolean(
    officer &&
      (officer.is_dev_admin || officer.email?.trim().toLowerCase() === "zero4eleven@gmail.com")
  );
  const hasCaseInput = Boolean(caseText.trim() || uploadedFile);
  const activeCaseObj = cases.find((c) => c.id === activeCaseId);
  const isSampleCase = Boolean(activeCaseObj?.id?.startsWith("kes-"));
  const activeCaseTitle = activeCaseObj
    ? activeCaseObj.tajuk_kes.replace(/^Kes \d+:\s*/, "")
    : uploadedFile?.name;

  const mobileBadges: Partial<Record<ActiveAppMode, string>> = {};
  if (auditReport) mobileBadges.audit = `${auditReport.overall_score}%`;
  if (draft) mobileBadges.draft = "✓";

  return (
    <div
      className={`flex min-h-[100dvh] flex-col bg-[#f4f7fb] lg:pb-0 ${
        !isFullWidthMode && mobileSplitPane === "input" ? "pb-36" : "pb-20"
      }`}
    >
      <TopNavbar
        status={status}
        activeMode={activeTab}
        onSelectMode={handleSelectMode}
        useOllama={useOllama}
        onToggleOllama={setUseOllama}
        caseCount={cases.length}
        onOpenCases={() => {
          setRegistryInitialMode("list");
          setRegistryOpen(true);
        }}
        onOpenSettings={() => setSettingsOpen(true)}
        officer={officer}
        isDevAdmin={isDevAdmin}
        onOpenAccount={() => {
          setAuthInitialTab(officer ? "profile" : "google");
          setAuthOpen(true);
        }}
        onOpenSplash={() => setSplashOpen(true)}
        onOpenDevConsole={() => setDevConsoleOpen(true)}
      />

      {/* Jalur Panduan 3 Langkah Kontekstual */}
      {activeTab !== "guide" && (
        <WorkspaceStepper
          activeMode={activeTab}
          hasInput={hasCaseInput}
          hasAudit={Boolean(auditReport)}
          hasDraft={Boolean(draft)}
          hasCompound={Boolean(compoundNotice.nama_penerima || compoundNotice.peruntukan_undang)}
          onJumpInput={
            !isFullWidthMode
              ? () => {
                  setMobileSplitPane("input");
                  window.scrollTo({ top: 0, behavior: "smooth" });
                }
              : undefined
          }
          onJumpResult={
            !isFullWidthMode
              ? () => {
                  setMobileSplitPane("result");
                  window.scrollTo({ top: 0, behavior: "smooth" });
                }
              : undefined
          }
        />
      )}

      {/* Toast Maklum Balas Pantas */}
      {toastMsg && (
        <div className="mx-auto mt-2.5 w-full max-w-[1680px] px-3 sm:px-4">
          <div className="flex items-center gap-2 rounded-xl border border-emerald-300 bg-emerald-50 px-3.5 py-2.5 text-xs font-bold text-emerald-900 shadow-sm">
            <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600" />
            <span>{toastMsg}</span>
          </div>
        </div>
      )}

      {errorBanner && (
        <div className="mx-auto mt-2.5 w-full max-w-[1680px] px-3 sm:px-4">
          <div className="flex items-center justify-between gap-2 rounded-xl border border-rose-300 bg-rose-50 px-3.5 py-2.5 text-xs font-semibold text-rose-900 shadow-sm">
            <div className="flex items-center gap-2">
              <AlertCircle className="h-4 w-4 shrink-0 text-rose-600" />
              <span>{errorBanner}</span>
            </div>
            <button
              type="button"
              onClick={() => setErrorBanner(null)}
              className="rounded px-2 py-0.5 text-[11px] font-bold hover:bg-rose-100"
            >
              Tutup
            </button>
          </div>
        </div>
      )}

      {/* Reka Letak Adaptif: Lebar Penuh untuk Tanya Pakar & Panduan, Split-View untuk Kerja Kes IP */}
      {isFullWidthMode ? (
        <main className="mx-auto w-full max-w-[1480px] flex-1 space-y-3 p-3 sm:p-4">
          <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 shadow-sm">
            <div className="text-xs text-slate-600">
              {activeTab === "advisor" ? (
                <span>
                  Mod Bebas <strong>Tanya Pakar UIP</strong> — tanya sebarang situasi kes di lapangan.
                </span>
              ) : (
                <span>
                  <strong>Buku Panduan Digital UIP KKM</strong> — rujukan carta alir, seksyen, susunan IP &amp; kesilapan biasa.
                </span>
              )}
            </div>
            <button
              type="button"
              onClick={() => handleSelectMode("audit")}
              className="inline-flex min-h-[38px] items-center gap-1.5 rounded-lg bg-slate-100 px-3 py-1.5 text-xs font-bold text-slate-800 hover:bg-slate-200"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              Kembali ke Ruang Kerja Kes ({activeCaseObj?.akta_utama || aktaUtama})
            </button>
          </div>

          {activeTab === "advisor" ? (
            <UIPAdvisorPanel
              aktaUtama={aktaUtama}
              authToken={authToken}
              officer={officer}
              onApplyToCaseBuilder={(draftText, aktaDisyorkan, bukaIp) => {
                setCaseText(draftText);
                setAktaUtama(aktaDisyorkan);
                setActiveCaseId("");
                setDraft(null);
                setAuditReport(null);
                setHasUnsavedChanges(true);
                handleSelectMode(bukaIp ? "draft" : "compound");
                showToast(
                  bukaIp
                    ? "Fakta kes dari Pakar UIP dimuatkan — tekan 'Jana Draf Fail IP' di bawah."
                    : "Fakta kes dimuatkan — tekan 'Tarik Data Dari Kes Aktif' untuk isi borang kompaun."
                );
              }}
            />
          ) : (
            <AppGuidePanel onNavigateMode={handleSelectMode} />
          )}
        </main>
      ) : (
        <main className="mx-auto grid w-full max-w-[1680px] flex-1 grid-cols-1 gap-4 p-3 sm:p-4 lg:grid-cols-12">
          {/* Penukar Paparan Telefon Pintar (Mobile Sticky Toggle) */}
          <div className="sticky top-14 z-20 grid grid-cols-2 gap-1.5 rounded-xl bg-white p-1.5 shadow-sm ring-1 ring-slate-200 lg:hidden">
            <button
              type="button"
              onClick={() => setMobileSplitPane("input")}
              className={`min-h-[42px] rounded-lg px-2 py-2 text-xs font-extrabold transition ${
                mobileSplitPane === "input"
                  ? "bg-[#0f2744] text-white"
                  : "text-slate-700 hover:bg-slate-100"
              }`}
            >
              1. Bahan Kes &amp; Muat Naik {hasCaseInput ? "✓" : ""}
            </button>
            <button
              type="button"
              onClick={() => setMobileSplitPane("result")}
              className={`min-h-[42px] rounded-lg px-2 py-2 text-xs font-extrabold transition ${
                mobileSplitPane === "result"
                  ? "bg-[#0f2744] text-white"
                  : "text-slate-700 hover:bg-slate-100"
              }`}
            >
              {activeTab === "compound"
                ? "2. Borang Notis Kompaun"
                : activeTab === "draft"
                  ? `2. Editor IP & Word ${draft ? "✓" : ""}`
                  : activeTab === "redaction"
                    ? "2. Privasi Data (PDPA)"
                    : `2. Keputusan Semak ${auditReport ? `(${auditReport.overall_score}%)` : ""}`}
            </button>
          </div>

          <div
            className={`${mobileSplitPane === "input" ? "block" : "hidden"} lg:col-span-5 lg:block`}
          >
            <LeftEvidencePane
              activeMode={activeTab}
              cases={cases}
              activeCaseId={activeCaseId}
              isSampleCase={isSampleCase}
              onSelectCase={(rec) => applyCaseRecord(rec, officer)}
              onOpenNewCase={() => {
                setRegistryInitialMode("new");
                setRegistryOpen(true);
              }}
              onStartBlankCase={handleStartBlankCase}
              onSaveCurrentCase={handleSaveCurrentCase}
              savingCase={savingCase}
              hasUnsavedChanges={hasUnsavedChanges}
              aktaUtama={aktaUtama}
              onChangeAkta={(next) => {
                setAktaUtama(next);
                setHasUnsavedChanges(true);
              }}
              caseText={caseText}
              onChangeCaseText={(next) => {
                setCaseText(next);
                setHasUnsavedChanges(true);
              }}
              uploadedFile={uploadedFile}
              previewUrl={previewUrl}
              onFileSelected={handleFileSelected}
              onRunAudit={handleRunAudit}
              onRunDraft={() => handleRunDraft()}
              onExtractEvidence={handleExtractEvidence}
              onSearchRag={handleSearchRag}
              ragResults={ragResults}
              ragLoading={ragLoading}
              auditLoading={auditLoading}
              draftLoading={draftLoading}
              extractLoading={extractLoading}
              extractedEvidence={extractedEvidence}
              folderChecklist={auditReport?.ip_folder_checklist}
              fileTriggerNonce={fileTriggerNonce}
            />
          </div>

          <div
            className={`${
              mobileSplitPane === "result" ? "flex" : "hidden"
            } flex-col rounded-xl border border-slate-200 bg-white p-3.5 shadow-sm sm:p-4 lg:col-span-7 lg:flex`}
          >
            {/* Header Tunggal Panel Kanan (Tiada lagi bar tab duplikasi!) */}
            <div className="mb-4 flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 pb-3">
              <div>
                <h2 className="text-sm font-extrabold text-slate-900">
                  {activeTab === "compound"
                    ? "Borang & Semakan Notis Kompaun"
                    : activeTab === "draft"
                      ? "Editor Fail IP & Dokumen Word (.docx)"
                      : activeTab === "redaction"
                        ? "Semakan Privasi Data Peribadi (OSA & PDPA)"
                        : "Keputusan Semakan Kualiti IP (20 Kriteria Pra-TPR)"}
                </h2>
                <p className="text-[11px] text-slate-500">
                  {activeCaseTitle
                    ? `Kes aktif: ${activeCaseTitle}`
                    : "Gunakan bahan kes atau isi terus di ruangan kerja ini."}
                </p>
              </div>

              {/* Sub-pil KHUSUS untuk mod Semak IP: Keputusan 20 Kriteria | Privasi Data */}
              {(activeTab === "audit" || activeTab === "redaction") && (
                <div className="grid grid-cols-2 gap-1 rounded-lg bg-slate-100 p-1">
                  <button
                    type="button"
                    onClick={() => handleSelectMode("audit")}
                    className={`inline-flex min-h-[36px] items-center justify-center gap-1.5 rounded-md px-3 py-1 text-xs font-bold transition ${
                      activeTab === "audit"
                        ? "bg-[#0f2744] text-white shadow-sm"
                        : "text-slate-700 hover:bg-white/70"
                    }`}
                  >
                    <CheckSquare className="h-3.5 w-3.5" />
                    20 Kriteria
                    {auditReport && (
                      <span className="rounded-full bg-white/20 px-1.5 py-0.5 text-[10px]">
                        {auditReport.overall_score}%
                      </span>
                    )}
                  </button>
                  <button
                    type="button"
                    onClick={() => handleSelectMode("redaction")}
                    className={`inline-flex min-h-[36px] items-center justify-center gap-1.5 rounded-md px-3 py-1 text-xs font-bold transition ${
                      activeTab === "redaction"
                        ? "bg-[#0f2744] text-white shadow-sm"
                        : "text-slate-700 hover:bg-white/70"
                    }`}
                  >
                    <Lock className="h-3.5 w-3.5" />
                    Privasi PDPA
                    {redaction && (
                      <span className="rounded-full bg-emerald-500/25 px-1.5 py-0.5 text-[10px]">
                        {redaction.entities.length}
                      </span>
                    )}
                  </button>
                </div>
              )}
            </div>

            <div className="flex-1 overflow-y-auto pr-0.5 sm:pr-1">
              {activeTab === "audit" && (
                <AuditPanel
                  report={auditReport}
                  hasCaseInput={hasCaseInput}
                  activeCaseTitle={activeCaseTitle}
                  auditLoading={auditLoading}
                  draftLoading={draftLoading}
                  onRunAudit={handleRunAudit}
                  onSwitchToInput={() => {
                    setMobileSplitPane("input");
                    setFileTriggerNonce((n) => n + 1);
                  }}
                  onLoadSampleCase={handleLoadSampleCase}
                  onJumpToEditor={(sectionId) => {
                    if (!draft) {
                      handleRunDraft(sectionId);
                    } else {
                      if (sectionId) setEditorTargetSection(sectionId);
                      handleSelectMode("draft");
                    }
                  }}
                />
              )}
              {activeTab === "compound" && (
                <CompoundNoticePanel
                  notice={compoundNotice}
                  onChangeNotice={(next) => {
                    setCompoundNotice(next);
                    setHasUnsavedChanges(true);
                  }}
                  onClearNotice={() => {
                    setCompoundNotice(EMPTY_COMPOUND_NOTICE);
                    setHasUnsavedChanges(true);
                  }}
                  onAutoFillFromCase={handleAutoFillCompound}
                  autoFillLoading={draftLoading}
                  activeCaseTitle={activeCaseTitle}
                  savingCase={savingCase}
                  onSaveNotice={handleSaveCurrentCase}
                  onSwitchToInput={() => setMobileSplitPane("input")}
                />
              )}
              {activeTab === "draft" && (
                <DraftDocxEditor
                  draft={draft}
                  onChangeDraft={(next) => {
                    setDraft(next);
                    setHasUnsavedChanges(true);
                  }}
                  hasCaseInput={hasCaseInput}
                  activeCaseTitle={activeCaseTitle}
                  draftLoading={draftLoading}
                  hasUnsavedChanges={hasUnsavedChanges}
                  savingCase={savingCase}
                  initialSection={editorTargetSection}
                  onGenerateDraft={() => handleRunDraft()}
                  onStartBlankDraft={handleStartBlankDraft}
                  onSaveDraft={handleSaveCurrentCase}
                  onSwitchToInput={() => setMobileSplitPane("input")}
                  onLoadSampleCase={handleLoadSampleCase}
                />
              )}
              {activeTab === "redaction" && (
                <RedactionPreview
                  redaction={redaction}
                  loading={redactLoading}
                  onRunRedaction={handleRunRedaction}
                  hasCaseInput={hasCaseInput}
                  onSwitchToInput={() => setMobileSplitPane("input")}
                />
              )}
            </div>
          </div>
        </main>
      )}

      {/* Bar Tindakan Melekit Mobile apabila berada di Panel Input */}
      {!isFullWidthMode && mobileSplitPane === "input" && (
        <div
          style={{ bottom: "calc(56px + env(safe-area-inset-bottom))" }}
          className="fixed inset-x-0 z-30 border-t border-slate-200 bg-white/95 px-3 py-2 shadow-lg backdrop-blur-sm lg:hidden"
        >
          <div className="flex items-center gap-2">
            {activeTab === "draft" ? (
              <button
                type="button"
                disabled={draftLoading}
                onClick={() => handleRunDraft()}
                className="inline-flex min-h-[44px] flex-1 items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 text-xs font-extrabold text-white shadow-sm disabled:opacity-60"
              >
                {draftLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
                Jana Fail IP &amp; Borang 114
              </button>
            ) : activeTab === "compound" ? (
              <button
                type="button"
                disabled={draftLoading}
                onClick={() => {
                  handleAutoFillCompound();
                  setMobileSplitPane("result");
                }}
                className="inline-flex min-h-[44px] flex-1 items-center justify-center gap-2 rounded-xl bg-amber-600 px-4 text-xs font-extrabold text-white shadow-sm disabled:opacity-60"
              >
                {draftLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                Tarik Data ke Borang Kompaun
              </button>
            ) : (
              <button
                type="button"
                disabled={auditLoading}
                onClick={handleRunAudit}
                className="inline-flex min-h-[44px] flex-1 items-center justify-center gap-2 rounded-xl bg-[#0f2744] px-4 text-xs font-extrabold text-white shadow-sm disabled:opacity-60"
              >
                {auditLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <FileSearch className="h-4 w-4 text-amber-300" />
                )}
                Semak IP Sekarang (20 Perkara)
              </button>
            )}
          </div>
        </div>
      )}

      {isDevAdmin && (
        <SystemSettingsModal
          open={settingsOpen}
          onClose={() => setSettingsOpen(false)}
          status={status}
          onStatusUpdated={setStatus}
        />
      )}

      <CaseRegistryModal
        open={registryOpen}
        onClose={() => setRegistryOpen(false)}
        cases={cases}
        activeCaseId={activeCaseId}
        onSelectCase={(rec) => applyCaseRecord(rec, officer)}
        onCasesUpdated={setCases}
        initialMode={registryInitialMode}
        officer={officer}
      />

      <AuthAccountModal
        open={authOpen}
        onClose={() => setAuthOpen(false)}
        officer={officer}
        authToken={authToken}
        initialTab={authInitialTab}
        onAuthenticated={handleAuthenticatedSuccess}
        onProfileUpdated={(updated) => setOfficer(updated)}
        onLoggedOut={() => {
          setOfficer(null);
          setAuthToken(null);
          setCases([]);
          setAuditReport(null);
          setDraft(null);
          setCaseText("");
          setSplashOpen(true);
          window.localStorage.removeItem("uip_auth_token");
        }}
      />

      {isDevAdmin && (
        <DevConsoleModal
          open={devConsoleOpen}
          onClose={() => setDevConsoleOpen(false)}
          authToken={authToken}
          developerEmail={officer?.email}
        />
      )}

      <SplashScreenModal
        open={splashOpen}
        officer={officer}
        onClose={closeSplashAndRemember}
        onEnterApp={(mode) => {
          closeSplashAndRemember();
          handleSelectMode(mode);
        }}
        onOpenGoogleAuth={() => {
          closeSplashAndRemember();
          setAuthInitialTab("google");
          setAuthOpen(true);
        }}
        onOpenEmailAuth={(tabChoice) => {
          closeSplashAndRemember();
          setAuthInitialTab(tabChoice);
          setAuthOpen(true);
        }}
      />

      <footer className="mt-auto border-t border-slate-200 bg-white/95 px-4 py-3 text-center text-[11px] text-slate-600">
        <div className="mx-auto flex max-w-[1680px] flex-col items-center justify-between gap-2 md:flex-row">
          <div className="flex flex-wrap items-center justify-center gap-2.5">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src="/images/logo-pkdkn.png"
              alt="Logo PKD Kuala Nerus"
              className="h-6 w-auto object-contain"
            />
            <span className="text-left">
              <strong>i-UIP Nerus</strong> • Unit Inspektorat &amp; Perundangan,{" "}
              <strong>PKD Kuala Nerus, Terengganu</strong>{" "}
              <span className="hidden italic text-slate-500 sm:inline">
                — &ldquo;Satu Hati, Satu Tekad: Memacu Kecemerlangan Kesihatan Kuala Nerus&rdquo;
              </span>
            </span>
          </div>
          <div className="flex flex-wrap items-center justify-center gap-3">
            {isDevAdmin && (
              <button
                type="button"
                onClick={() => setDevConsoleOpen(true)}
                className="font-bold text-indigo-700 hover:underline"
              >
                Konsol Pembangun (Siapa Guna &amp; Arkib)
              </button>
            )}
            <a
              href="https://g.dev/syrzy"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 font-bold text-[#0f2744] hover:text-blue-700 hover:underline"
            >
              <span>Dibangunkan oleh Dev: g.dev/syrzy</span>
              <ExternalLink className="h-3 w-3" />
            </a>
          </div>
        </div>
      </footer>

      <MobileBottomNav
        activeMode={activeTab}
        onSelectMode={handleSelectMode}
        badges={mobileBadges}
      />
    </div>
  );
}
