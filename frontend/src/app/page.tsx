"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Database,
  ExternalLink,
  FileCheck2,
  FileText,
  FolderOpen,
  Layers,
  Loader2,
  MessageSquareQuote,
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
  Save,
  Scale,
} from "lucide-react";
import AppGuidePanel from "@/components/AppGuidePanel";
import AuditPanel from "@/components/AuditPanel";
import AuthAccountModal from "@/components/AuthAccountModal";
import CaseRegistryModal from "@/components/CaseRegistryModal";
import CompoundNoticePanel from "@/components/CompoundNoticePanel";
import DevConsoleModal from "@/components/DevConsoleModal";
import DraftDocxEditor from "@/components/DraftDocxEditor";
import LeftEvidencePane from "@/components/LeftEvidencePane";
import LegalDirectoryPanel from "@/components/LegalDirectoryPanel";
import MobileBottomNav from "@/components/MobileBottomNav";
import OnboardingCardsModal from "@/components/OnboardingCardsModal";
import SplashScreenModal from "@/components/SplashScreenModal";
import SystemSettingsModal from "@/components/SystemSettingsModal";
import TopNavbar, { type ActiveAppMode } from "@/components/TopNavbar";
import UIPAdvisorPanel from "@/components/UIPAdvisorPanel";
import {
  extractEvidence,
  fetchCases,
  fetchCurrentOfficer,
  fetchSampleCases,
  fetchSystemStatus,
  generateDrafts,
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
  SystemStatus,
  WorkflowMode,
} from "@/lib/types";

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

function getOnboardingHideKey(user: OfficerProfile): string {
  const ident = (user.email || user.id || "default").trim().toLowerCase();
  return `uip_onboarding_cards_hide_v1:${ident}`;
}

function getOnboardingSessionKey(user: OfficerProfile): string {
  const ident = (user.email || user.id || "default").trim().toLowerCase();
  return `uip_onboarding_cards_session_v1:${ident}`;
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

  const [activeTab, setActiveTab] = useState<ActiveAppMode>("home");
  const [auditReport, setAuditReport] = useState<IPAuditReport | null>(null);
  const [redaction, setRedaction] = useState<RedactResponse | null>(null);
  const [draft, setDraft] = useState<DraftGenerationResponse | null>(null);
  const [compoundNotice, setCompoundNotice] =
    useState<NotisKompaunData>(EMPTY_COMPOUND_NOTICE);
  const [extractedEvidence, setExtractedEvidence] =
    useState<EvidenceExtractionResponse | null>(null);

  const [auditLoading, setAuditLoading] = useState(false);
  const [draftLoading, setDraftLoading] = useState(false);
  const [redactLoading, setRedactLoading] = useState(false);
  const [extractLoading, setExtractLoading] = useState(false);
  const [savingCase, setSavingCase] = useState(false);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [editorTargetSection, setEditorTargetSection] = useState<string | null>(null);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);
  const [toastMsg, setToastMsg] = useState<string | null>(null);

  const [desktopShowSource, setDesktopShowSource] = useState(true);
  const [mobileEditingInput, setMobileEditingInput] = useState(true);

  const [settingsOpen, setSettingsOpen] = useState(false);
  const [devConsoleOpen, setDevConsoleOpen] = useState(false);
  const [registryOpen, setRegistryOpen] = useState(false);
  const [registryInitialMode, setRegistryInitialMode] = useState<"list" | "new">("list");
  const [authOpen, setAuthOpen] = useState(false);
  const [authInitialTab, setAuthInitialTab] = useState<"google" | "login" | "register" | "profile">("google");
  const [onboardingOpen, setOnboardingOpen] = useState(false);
  const [onboardingDontShow, setOnboardingDontShow] = useState(false);

  const [authToken, setAuthToken] = useState<string | null>(null);
  const [officer, setOfficer] = useState<OfficerProfile | null>(null);
  const [authChecked, setAuthChecked] = useState(false);

  const showToast = useCallback((msg: string) => {
    setToastMsg(msg);
    window.setTimeout(() => {
      setToastMsg((prev) => (prev === msg ? null : prev));
    }, 3800);
  }, []);

  const maybeOpenOnboarding = useCallback((user: OfficerProfile, isFreshLogin: boolean) => {
    if (typeof window === "undefined") return;
    const hideKey = getOnboardingHideKey(user);
    const sessionKey = getOnboardingSessionKey(user);
    const hidden = window.localStorage.getItem(hideKey) === "1";
    setOnboardingDontShow(hidden);
    if (hidden) return;
    if (isFreshLogin) {
      window.sessionStorage.removeItem(sessionKey);
      setOnboardingOpen(true);
      return;
    }
    if (window.sessionStorage.getItem(sessionKey) !== "1") {
      setOnboardingOpen(true);
    }
  }, []);

  const handleToggleOnboardingDontShow = (val: boolean) => {
    setOnboardingDontShow(val);
    if (officer && typeof window !== "undefined") {
      const hideKey = getOnboardingHideKey(officer);
      if (val) window.localStorage.setItem(hideKey, "1");
      else window.localStorage.removeItem(hideKey);
    }
  };

  const handleCloseOnboarding = () => {
    if (officer && typeof window !== "undefined") {
      window.sessionStorage.setItem(getOnboardingSessionKey(officer), "1");
      const hideKey = getOnboardingHideKey(officer);
      if (onboardingDontShow) window.localStorage.setItem(hideKey, "1");
      else window.localStorage.removeItem(hideKey);
    }
    setOnboardingOpen(false);
  };

  const handleOpenOnboardingManual = () => {
    if (officer && typeof window !== "undefined") {
      setOnboardingDontShow(window.localStorage.getItem(getOnboardingHideKey(officer)) === "1");
    }
    setOnboardingOpen(true);
  };

  const confirmDiscardIfDirty = useCallback(() => {
    if (!hasUnsavedChanges) return true;
    return window.confirm(
      "Anda mempunyai perubahan yang belum disimpan. Teruskan tanpa menyimpan?"
    );
  }, [hasUnsavedChanges]);

  const applyCaseRecord = useCallback(
    (rec: IPCaseRecord, currentOfficer?: OfficerProfile | null, force = false) => {
      if (!force && hasUnsavedChanges && rec.id !== activeCaseId) {
        const ok = window.confirm(
          "Anda mempunyai perubahan yang belum disimpan pada kes semasa. Tukar kes tanpa menyimpan?"
        );
        if (!ok) return;
      }
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
      setMobileEditingInput(!(rec.audit_report || rec.draft));
    },
    [hasUnsavedChanges, activeCaseId]
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
            setActiveTab("home");
            maybeOpenOnboarding(me, false);
          } catch {
            if (typeof window !== "undefined") {
              window.localStorage.removeItem("uip_auth_token");
            }
          }
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
  }, [maybeOpenOnboarding]);

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
    setErrorBanner(null);
    if (mode === "compound") setWorkflow("notis_kompaun");
    else if (mode === "draft") {
      setWorkflow("ip_builder");
      setDesktopShowSource(!draft);
      setMobileEditingInput(!draft);
    } else if (mode === "audit" || mode === "redaction") {
      setWorkflow("audit_ip");
      setDesktopShowSource(true);
      setMobileEditingInput(!auditReport && mode !== "redaction");
    }
    if (typeof window !== "undefined") {
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  };

  const handleStartBlankCase = () => {
    if (!confirmDiscardIfDirty()) return;
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
    setDesktopShowSource(true);
    setMobileEditingInput(true);
    setErrorBanner(null);
    showToast("Sedia untuk kes baharu — muat naik fail atau taip fakta kes.");
  };

  const handleLoadSampleCase = async () => {
    if (!confirmDiscardIfDirty()) return;
    setErrorBanner(null);
    const sample = cases.find((c) => c.id.startsWith("kes-")) || cases[0];
    if (sample) {
      applyCaseRecord(sample, officer, true);
      showToast(`Contoh kes dimuatkan: ${sample.tajuk_kes}`);
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
        setHasUnsavedChanges(false);
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
      showToast("Fail kes & perubahan berjaya disimpan ke akaun PKD!");
    } catch (err) {
      setErrorBanner(err instanceof Error ? err.message : "Gagal menyimpan kes PKD.");
    } finally {
      setSavingCase(false);
    }
  };

  const handleRunAudit = async () => {
    if (!caseText.trim() && !uploadedFile) {
      setErrorBanner("Sila masukkan catatan fakta kes atau muat naik fail PDF/DOCX/gambar dahulu.");
      setMobileEditingInput(true);
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
      const nextText = report.extracted_text && uploadedFile ? report.extracted_text : caseText;
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

      const isSavedUserCase = Boolean(activeCaseId && !activeCaseId.startsWith("kes-"));
      if (isSavedUserCase) {
        saveCaseRecord({
          id: activeCaseId,
          akta_utama: aktaUtama,
          workflow,
          case_text: nextText,
          status_kes: report.readiness_status,
          skor_audit: report.overall_score,
          audit_report: report,
          draft: draft ? { ...draft, notis_kompaun: compoundNotice } : null,
        })
          .then((saved) => {
            setCases((prev) => prev.map((c) => (c.id === saved.id ? saved : c)));
            setHasUnsavedChanges(false);
          })
          .catch(() => {
            setHasUnsavedChanges(true);
          });
      } else {
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
      }

      setActiveTab("audit");
      setMobileEditingInput(false);
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
      setErrorBanner("Sila masukkan catatan fakta kes atau muat naik fail kes dahulu.");
      setMobileEditingInput(true);
      return;
    }

    setDraftLoading(true);
    setErrorBanner(null);
    try {
      const draftRes = await generateDrafts({
        caseText: workingText,
        aktaUtama,
        workflow: "ip_builder",
        useOllama,
        fastMode: true,
        caseId: activeCaseId || undefined,
        authToken,
        officerProfile: officer,
      });
      setDraft(draftRes);
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

      const isSavedUserCase = Boolean(activeCaseId && !activeCaseId.startsWith("kes-"));
      if (isSavedUserCase) {
        saveCaseRecord({
          id: activeCaseId,
          akta_utama: aktaUtama,
          workflow: "ip_builder",
          case_text: workingText,
          status_kes: auditReport?.readiness_status || "DALAM SIASATAN",
          skor_audit: auditReport?.overall_score || 0,
          audit_report: auditReport,
          draft: { ...draftRes, notis_kompaun: { ...compoundNotice, ...draftRes.notis_kompaun } },
        })
          .then((saved) => {
            setCases((prev) => prev.map((c) => (c.id === saved.id ? saved : c)));
            setHasUnsavedChanges(false);
          })
          .catch(() => {
            setHasUnsavedChanges(true);
          });
      } else {
        setHasUnsavedChanges(true);
      }

      setActiveTab("draft");
      setDesktopShowSource(false);
      setMobileEditingInput(false);
      showToast("Draf fail IP siap — semak dan edit sebelum muat turun Word (.docx).");
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
          "Tiada kes aktif dipilih. Anda boleh isi borang ini secara manual atau tekan 'Imbas Foto / SSM'."
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
        showToast("Data kes berjaya diisi ke Borang Notis Kompaun!");
      }
    } catch (err) {
      setErrorBanner(err instanceof Error ? err.message : "Gagal menarik data ke borang kompaun.");
    } finally {
      setDraftLoading(false);
    }
  };

  const handleExtractFileForCompound = async (file: File) => {
    handleFileSelected(file);
    const ext = await extractEvidence(file, "sijil_ssm");
    setExtractedEvidence(ext);
    const workingText = (ext.raw_text || "").trim();
    if (!workingText) {
      throw new Error("Teks tidak dapat dikesan daripada fail ini. Sila pastikan gambar/PDF jelas.");
    }
    setCaseText(workingText);
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
      showToast(`Maklumat daripada ${file.name} berjaya diisi ke Notis Kompaun!`);
    }
  };

  const handleStartBlankDraft = () => {
    const blank = buildBlankDraft(aktaUtama, officer, compoundNotice);
    setDraft(blank);
    setHasUnsavedChanges(true);
    setActiveTab("draft");
    setDesktopShowSource(false);
    setMobileEditingInput(false);
    showToast("Borang IP kosong dibuka — semua ruangan sedia diisi.");
  };

  const handleRunRedaction = async () => {
    if (!caseText.trim()) {
      setErrorBanner("Tiada catatan teks kes untuk disemak penyamaran data peribadi.");
      setMobileEditingInput(true);
      return;
    }
    setRedactLoading(true);
    setErrorBanner(null);
    try {
      const res = await runRedaction(caseText, useOllama);
      setRedaction(res);
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

  const handleAuthenticatedSuccess = async (user: OfficerProfile, token: string) => {
    window.localStorage.setItem("uip_auth_token", token);
    setAuthToken(token);
    setOfficer(user);
    setAuthOpen(false);
    setActiveTab("home");
    maybeOpenOnboarding(user, true);
    try {
      const caseList = await fetchCases();
      setCases(caseList);
    } catch {
      // Abaikan jika gagal sementara
    }
  };

  const handleFullLogout = () => {
    setOnboardingOpen(false);
    setOfficer(null);
    setAuthToken(null);
    setCases([]);
    setActiveCaseId("");
    setAuditReport(null);
    setDraft(null);
    setRedaction(null);
    setExtractedEvidence(null);
    handleFileSelected(null);
    setCaseText("");
    setCompoundNotice(EMPTY_COMPOUND_NOTICE);
    setHasUnsavedChanges(false);
    setErrorBanner(null);
    setActiveTab("home");
    window.localStorage.removeItem("uip_auth_token");
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
            <p className="text-xs italic text-amber-100/90">
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
          onEnterApp={() => setAuthOpen(true)}
          onOpenGoogleAuth={() => {
            setAuthInitialTab("google");
            setAuthOpen(true);
          }}
          onOpenEmailAuth={(tabChoice) => {
            setAuthInitialTab(tabChoice);
            setAuthOpen(true);
          }}
          onAuthenticated={handleAuthenticatedSuccess}
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

  const isIpWorkspace = activeTab === "audit" || activeTab === "draft" || activeTab === "redaction";
  const hasIpResult =
    activeTab === "draft" ? Boolean(draft) : activeTab === "redaction" ? true : Boolean(auditReport);

  const mobileBadges: Partial<Record<ActiveAppMode, string>> = {};
  if (auditReport) mobileBadges.audit = `${auditReport.overall_score}%`;
  if (draft) mobileBadges.draft = "✓";

  const recentCases = cases.filter((c) => !c.id.startsWith("kes-")).slice(0, 3);
  const quickResumeList = recentCases.length > 0 ? recentCases : cases.slice(0, 2);

  return (
    <div className="flex min-h-[100dvh] flex-col bg-[#f4f7fb] pb-20 lg:pb-0">
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
        onOpenSplash={() => handleSelectMode("home")}
        onOpenOnboarding={handleOpenOnboardingManual}
        onOpenDevConsole={() => setDevConsoleOpen(true)}
      />

      {/* Toast Maklum Balas Pantas */}
      {toastMsg && (
        <div className="mx-auto mt-3 w-full max-w-[1600px] px-3 sm:px-4">
          <div className="flex items-center gap-2 rounded-xl border border-emerald-300 bg-emerald-50 px-4 py-2.5 text-xs font-bold text-emerald-900 shadow-sm">
            <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600" />
            <span>{toastMsg}</span>
          </div>
        </div>
      )}

      {errorBanner && (
        <div className="mx-auto mt-3 w-full max-w-[1600px] px-3 sm:px-4">
          <div className="flex items-center justify-between gap-2 rounded-xl border border-rose-300 bg-rose-50 px-4 py-2.5 text-xs font-semibold text-rose-900 shadow-sm">
            <div className="flex items-center gap-2">
              <AlertCircle className="h-4 w-4 shrink-0 text-rose-600" />
              <span>{errorBanner}</span>
            </div>
            <button
              type="button"
              onClick={() => setErrorBanner(null)}
              className="rounded px-2 py-0.5 text-xs font-bold hover:bg-rose-100"
            >
              Tutup
            </button>
          </div>
        </div>
      )}

      {/* PAPARAN 0: MENU MULA TUGASAN (TENANG & LAPANG SELEPAS LOG MASUK) */}
      {activeTab === "home" && (
        <main className="mx-auto w-full max-w-5xl flex-1 space-y-6 p-4 sm:p-6">
          <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-xs font-bold uppercase tracking-wide text-blue-700">
                  {officer.district_pkd || "PKD Kuala Nerus"} • Gred {officer.grade}
                </p>
                <h2 className="mt-1 text-lg font-extrabold text-slate-900 sm:text-xl">
                  Selamat bertugas, {officer.full_name}
                </h2>
                <p className="mt-1 text-xs text-slate-600 sm:text-sm">
                  Pilih tugasan anda di bawah untuk bermula.
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  onClick={handleOpenOnboardingManual}
                  className="inline-flex min-h-[42px] items-center gap-1.5 rounded-xl border border-[#9e1b32]/25 bg-[#f7f4ef] px-3.5 py-2 text-xs font-extrabold text-[#6d0f21] shadow-sm transition hover:bg-[#efe7dc]"
                >
                  <Layers className="h-4 w-4 text-[#9e1b32]" />
                  Kenali Fungsi (8 Kad)
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setRegistryInitialMode("new");
                    setRegistryOpen(true);
                  }}
                  className="inline-flex min-h-[42px] items-center gap-1.5 rounded-xl bg-[#0f2744] px-4 py-2 text-xs font-extrabold text-white shadow-sm hover:bg-slate-800"
                >
                  <Plus className="h-4 w-4 text-amber-300" />
                  Daftar Kes IP Baharu
                </button>
              </div>
            </div>

            <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-2">
              <button
                type="button"
                onClick={() => handleSelectMode("advisor")}
                className="flex items-start gap-3.5 rounded-2xl border border-slate-200 bg-slate-50/40 p-4 text-left transition hover:border-indigo-400 hover:bg-indigo-50/40"
              >
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-indigo-100 text-indigo-700">
                  <MessageSquareQuote className="h-5 w-5" />
                </div>
                <div>
                  <div className="text-sm font-extrabold text-slate-900">1. Tanya Pakar UIP</div>
                  <p className="mt-1 text-xs leading-relaxed text-slate-600">
                    Tidak pasti seksyen kesalahan, had denda, atau tindakan di lokasi? Tanya di sini dan terus dapat SOP lengkap.
                  </p>
                </div>
              </button>

              <button
                type="button"
                onClick={() => handleSelectMode("compound")}
                className="flex items-start gap-3.5 rounded-2xl border border-slate-200 bg-slate-50/40 p-4 text-left transition hover:border-amber-400 hover:bg-amber-50/40"
              >
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-amber-100 text-amber-800">
                  <FileCheck2 className="h-5 w-5" />
                </div>
                <div>
                  <div className="text-sm font-extrabold text-slate-900">2. Notis Kompaun</div>
                  <p className="mt-1 text-xs leading-relaxed text-slate-600">
                    Imbas foto SSM / notis atau isi borang, semak 10 perkara wajib dan muat turun Notis Word (.docx).
                  </p>
                </div>
              </button>

              <button
                type="button"
                onClick={() => handleSelectMode("audit")}
                className="flex items-start gap-3.5 rounded-2xl border border-slate-200 bg-slate-50/40 p-4 text-left transition hover:border-emerald-400 hover:bg-emerald-50/40"
              >
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-emerald-100 text-emerald-700">
                  <Scale className="h-5 w-5" />
                </div>
                <div>
                  <div className="text-sm font-extrabold text-slate-900">3. Semak Fail IP (Pra-TPR)</div>
                  <p className="mt-1 text-xs leading-relaxed text-slate-600">
                    Muat naik PDF Kertas Siasatan, gambar bukti atau catatan untuk kesan kesilapan seksyen &amp; kuiri TPR.
                  </p>
                </div>
              </button>

              <button
                type="button"
                onClick={() => handleSelectMode("draft")}
                className="flex items-start gap-3.5 rounded-2xl border border-slate-200 bg-slate-50/40 p-4 text-left transition hover:border-blue-400 hover:bg-blue-50/40"
              >
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-blue-100 text-blue-700">
                  <FileText className="h-5 w-5" />
                </div>
                <div>
                  <div className="text-sm font-extrabold text-slate-900">4. Bina Fail IP &amp; Borang Word</div>
                  <p className="mt-1 text-xs leading-relaxed text-slate-600">
                    Jana &amp; sunting Borang 114, Saman 111, Diari Siasatan, Rakaman S.112, Sijil 90A &amp; eksport `.docx`.
                  </p>
                </div>
              </button>

              <button
                type="button"
                onClick={() => handleSelectMode("directory")}
                className="flex items-start gap-3.5 rounded-2xl border border-slate-200 bg-slate-50/40 p-4 text-left transition hover:border-teal-400 hover:bg-teal-50/40 sm:col-span-2"
              >
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-teal-100 text-teal-800">
                  <Database className="h-5 w-5" />
                </div>
                <div>
                  <div className="text-sm font-extrabold text-slate-900">
                    5. Direktori Akta &amp; Kesalahan
                  </div>
                  <p className="mt-1 text-xs leading-relaxed text-slate-600">
                    Semak senarai kesalahan mengikut Akta (Akta 852, Akta 281, PPKM 2009, PPM 1985, Akta 154, Akta 342), kategori pelaku, had kompaun, perkara wajib dibuktikan &amp; teks penuh akta.
                  </p>
                </div>
              </button>
            </div>
          </section>

          {/* Sambung Kes Tersimpan / Contoh */}
          {quickResumeList.length > 0 && (
            <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
              <div className="flex flex-wrap items-center justify-between gap-2 pb-3">
                <h3 className="text-xs font-extrabold uppercase tracking-wide text-slate-700">
                  {recentCases.length > 0
                    ? "Sambung Fail Kes Anda"
                    : "Atau Cuba Dengan Contoh Kes Sedia Ada"}
                </h3>
                <button
                  type="button"
                  onClick={() => {
                    setRegistryInitialMode("list");
                    setRegistryOpen(true);
                  }}
                  className="inline-flex items-center gap-1 text-xs font-bold text-blue-700 hover:underline"
                >
                  <FolderOpen className="h-3.5 w-3.5" />
                  Lihat Semua ({cases.length})
                </button>
              </div>

              <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
                {quickResumeList.map((c) => (
                  <button
                    key={c.id}
                    type="button"
                    onClick={() => {
                      applyCaseRecord(c, officer, true);
                      handleSelectMode(c.draft ? "draft" : "audit");
                    }}
                    className="flex flex-col items-start rounded-xl border border-slate-200 bg-slate-50/50 p-3 text-left transition hover:border-blue-400 hover:bg-blue-50/30"
                  >
                    <div className="flex w-full items-center justify-between gap-2">
                      <span className="rounded bg-[#0f2744] px-2 py-0.5 text-[11px] font-bold text-white">
                        {c.akta_utama}
                      </span>
                      <span className="text-[11px] font-semibold text-slate-500">
                        {c.skor_audit ? `Skor ${c.skor_audit}%` : c.status_kes}
                      </span>
                    </div>
                    <div className="mt-1.5 line-clamp-1 text-xs font-bold text-slate-900">
                      {c.tajuk_kes.replace(/^Kes \d+:\s*/, "")}
                    </div>
                    <div className="mt-0.5 text-[11px] text-slate-500">
                      {c.nama_okt || c.nama_premis || "Klik untuk buka kes"}
                    </div>
                  </button>
                ))}
              </div>
            </section>
          )}
        </main>
      )}

      {/* PAPARAN 1: TANYA PAKAR (FOKUS PENUH) */}
      {activeTab === "advisor" && (
        <main className="mx-auto w-full max-w-[1600px] flex-1 p-3 sm:p-5">
          <UIPAdvisorPanel
            aktaUtama={aktaUtama}
            authToken={authToken}
            officer={officer}
            isDevAdmin={isDevAdmin}
            onApplyToCaseBuilder={(draftText, aktaDisyorkan, bukaIp) => {
              if (!confirmDiscardIfDirty()) return;
              setCaseText(draftText);
              setAktaUtama(aktaDisyorkan);
              setActiveCaseId("");
              setDraft(null);
              setAuditReport(null);
              setHasUnsavedChanges(true);
              setDesktopShowSource(true);
              setMobileEditingInput(true);
              handleSelectMode(bukaIp ? "draft" : "compound");
              showToast(
                bukaIp
                  ? "Fakta kes dari Pakar UIP dimuatkan — tekan 'Jana Draf IP & Borang 114'."
                  : "Fakta kes dimuatkan — tekan 'Tarik Dari Kes Aktif' untuk isi borang kompaun."
              );
            }}
          />
        </main>
      )}

      {/* PAPARAN 1B: DIREKTORI KESALAHAN & PUSTAKA AKTA VERBATIM */}
      {activeTab === "directory" && (
        <main className="mx-auto w-full max-w-[1600px] flex-1 p-3 sm:p-5">
          <LegalDirectoryPanel
            authToken={authToken}
            officer={officer}
            isDevAdmin={isDevAdmin}
            onApplyOffenceToCase={(draftText, aktaCode, bukaIp) => {
              if (!confirmDiscardIfDirty()) return;
              setCaseText(draftText);
              setAktaUtama(aktaCode);
              setActiveCaseId("");
              setDraft(null);
              setAuditReport(null);
              setHasUnsavedChanges(true);
              setDesktopShowSource(true);
              setMobileEditingInput(true);
              handleSelectMode(bukaIp ? "draft" : "compound");
              showToast(
                bukaIp
                  ? "Templat Pertuduhan dari Direktori Akta dimuatkan ke Bina Fail IP!"
                  : "Templat Kesalahan dari Direktori Akta dimuatkan ke Borang Notis Kompaun!"
              );
            }}
          />
        </main>
      )}

      {/* PAPARAN 2: NOTIS KOMPAUN (FOKUS BORANG TUNGGAL — DESKTOP & MOBILE) */}
      {activeTab === "compound" && (
        <main className="mx-auto w-full max-w-[1600px] flex-1 p-3 sm:p-5">
          <CompoundNoticePanel
            notice={compoundNotice}
            onChangeNotice={(next) => {
              setCompoundNotice(next);
              setHasUnsavedChanges(true);
            }}
            onClearNotice={() => {
              setCompoundNotice({
                ...EMPTY_COMPOUND_NOTICE,
                pegawai_pengeluar: officer?.full_name || "",
                no_kad_kuasa: officer?.kkm_authority_card_no || "",
              });
              setHasUnsavedChanges(true);
            }}
            onAutoFillFromCase={handleAutoFillCompound}
            onExtractFileForCompound={handleExtractFileForCompound}
            onOpenCases={() => {
              setRegistryInitialMode("list");
              setRegistryOpen(true);
            }}
            autoFillLoading={draftLoading}
            activeCaseTitle={activeCaseTitle}
            hasCaseSource={Boolean(caseText.trim() || uploadedFile || activeCaseId)}
            savingCase={savingCase}
            onSaveNotice={handleSaveCurrentCase}
            onDownloaded={(fname) =>
              showToast(`Fail ${fname} berjaya dimuat turun ke peranti anda.`)
            }
          />
        </main>
      )}

      {/* PAPARAN 3: PANDUAN */}
      {activeTab === "guide" && (
        <main className="mx-auto w-full max-w-6xl flex-1 p-3 sm:p-5">
          <AppGuidePanel onNavigateMode={handleSelectMode} />
        </main>
      )}

      {/* PAPARAN 4: RUANG KERJA FAIL IP (SEMAK IP & BINA FAIL IP — SINGLE-FLOW MOBILE & COLLAPSIBLE DESKTOP) */}
      {isIpWorkspace && (
        <main className="mx-auto w-full max-w-[1600px] flex-1 space-y-3 p-3 sm:p-4">
          {/* Bar Konteks Tunggal & Kemas */}
          <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 shadow-sm">
            <div className="flex min-w-0 items-center gap-2 text-xs">
              <span className="shrink-0 rounded-md bg-[#0f2744] px-2 py-0.5 text-[11px] font-bold text-white">
                {aktaUtama}
              </span>
              <span className="truncate font-bold text-slate-900">
                {activeCaseTitle || "Kes Baharu (Belum Disimpan)"}
              </span>
              {isSampleCase && (
                <span className="hidden rounded bg-amber-100 px-2 py-0.5 text-[11px] font-bold text-amber-900 sm:inline">
                  Contoh Kes
                </span>
              )}
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                disabled={savingCase}
                onClick={handleSaveCurrentCase}
                className={`inline-flex min-h-[36px] items-center gap-1.5 rounded-lg border px-3 py-1 text-xs font-bold transition disabled:opacity-60 ${
                  hasUnsavedChanges
                    ? "border-amber-400 bg-amber-50 text-amber-950 hover:bg-amber-100"
                    : "border-slate-300 bg-white text-slate-700 hover:bg-slate-50"
                }`}
              >
                {savingCase ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Save className="h-3.5 w-3.5 text-emerald-700" />
                )}
                {hasUnsavedChanges ? "Simpan*" : "Simpan"}
              </button>

              {/* Toggle Panel Sumber di Desktop */}
              <button
                type="button"
                onClick={() => setDesktopShowSource((v) => !v)}
                className="hidden min-h-[36px] items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1 text-xs font-bold text-slate-700 hover:bg-slate-50 lg:inline-flex"
              >
                {desktopShowSource ? (
                  <>
                    <PanelLeftClose className="h-4 w-4 text-slate-600" />
                    Luaskan Paparan
                  </>
                ) : (
                  <>
                    <PanelLeftOpen className="h-4 w-4 text-blue-700" />
                    Tunjuk Bahan &amp; Fakta
                  </>
                )}
              </button>

              {/* Toggle Bahan vs Hasil di Mobile (Hanya bila ada hasil/editor) */}
              {hasIpResult && (
                <button
                  type="button"
                  onClick={() => setMobileEditingInput((v) => !v)}
                  className="inline-flex min-h-[36px] items-center gap-1 rounded-lg border border-blue-200 bg-blue-50 px-3 py-1 text-xs font-bold text-blue-800 lg:hidden"
                >
                  {mobileEditingInput ? (
                    <>
                      Lihat Keputusan <ChevronDown className="h-3.5 w-3.5" />
                    </>
                  ) : (
                    <>
                      Ubah Bahan Kes <ChevronUp className="h-3.5 w-3.5" />
                    </>
                  )}
                </button>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
            {/* Panel Sumber (Di Mobile: hanya bila sedang isi input atau tiada hasil lagi; Di Desktop: boleh dilipat) */}
            <div
              className={`${mobileEditingInput ? "block" : "hidden"} ${
                desktopShowSource ? "lg:col-span-5 lg:block" : "lg:hidden"
              }`}
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
                onStartBlankDraft={handleStartBlankDraft}
                hasExistingResult={hasIpResult}
                onBackToResult={() => setMobileEditingInput(false)}
                onExtractEvidence={handleExtractEvidence}
                auditLoading={auditLoading}
                draftLoading={draftLoading}
                extractLoading={extractLoading}
                extractedEvidence={extractedEvidence}
                fileTriggerNonce={fileTriggerNonce}
              />
            </div>

            {/* Panel Hasil / Editor (Di Mobile: bila hasil sedia; Di Desktop: 7 col atau penuh 12 col) */}
            <div
              className={`${mobileEditingInput ? "hidden" : "block"} ${
                desktopShowSource ? "lg:col-span-7" : "lg:col-span-12"
              } lg:block`}
            >
              {activeTab === "draft" ? (
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
                  onSwitchToInput={() => {
                    setDesktopShowSource(true);
                    setMobileEditingInput(true);
                  }}
                  onLoadSampleCase={handleLoadSampleCase}
                  onDownloaded={(fname) =>
                    showToast(`Fail ${fname} berjaya dimuat turun ke peranti anda.`)
                  }
                />
              ) : (
                <AuditPanel
                  report={auditReport}
                  redaction={redaction}
                  redactLoading={redactLoading}
                  onRunRedaction={handleRunRedaction}
                  hasCaseInput={hasCaseInput}
                  activeCaseTitle={activeCaseTitle}
                  auditLoading={auditLoading}
                  draftLoading={draftLoading}
                  onRunAudit={handleRunAudit}
                  onSwitchToInput={() => {
                    setDesktopShowSource(true);
                    setMobileEditingInput(true);
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
                  initialSubView={activeTab === "redaction" ? "privacy" : "criteria"}
                />
              )}
            </div>
          </div>
        </main>
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
        onLoggedOut={handleFullLogout}
      />

      {isDevAdmin && (
        <DevConsoleModal
          open={devConsoleOpen}
          onClose={() => setDevConsoleOpen(false)}
          authToken={authToken}
          developerEmail={officer?.email}
        />
      )}

      <OnboardingCardsModal
        open={onboardingOpen}
        officer={officer}
        dontShowAgain={onboardingDontShow}
        onToggleDontShowAgain={handleToggleOnboardingDontShow}
        onClose={handleCloseOnboarding}
        onNavigateMode={(mode) => {
          handleCloseOnboarding();
          handleSelectMode(mode);
        }}
        onOpenCases={() => {
          handleCloseOnboarding();
          setRegistryInitialMode("list");
          setRegistryOpen(true);
        }}
        onOpenProfile={() => {
          handleCloseOnboarding();
          setAuthInitialTab("profile");
          setAuthOpen(true);
        }}
      />

      <footer className="mt-auto hidden border-t border-slate-200 bg-white/95 px-4 py-3 text-[11px] text-slate-600 lg:block">
        <div className="mx-auto flex max-w-[1600px] items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src="/images/logo-pkdkn.png"
              alt="Logo PKD Kuala Nerus"
              className="h-6 w-auto object-contain"
            />
            <span>
              <strong>i-UIP Nerus</strong> • Unit Inspektorat &amp; Perundangan,{" "}
              <strong>PKD Kuala Nerus, Terengganu</strong> —{" "}
              <em className="text-slate-500">
                &ldquo;Satu Hati, Satu Tekad: Memacu Kecemerlangan Kesihatan Kuala Nerus&rdquo;
              </em>
            </span>
          </div>
          <div className="flex items-center gap-4">
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
