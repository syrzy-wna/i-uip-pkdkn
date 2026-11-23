"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  ExternalLink,
  FileCheck2,
  FolderOpen,
  Loader2,
  MessageSquareQuote,
  Plus,
  Save,
  Scale,
  Search,
  Sparkles,
  Zap,
} from "lucide-react";
import AppGuidePanel from "@/components/AppGuidePanel";
import AuditPanel, {
  type AuditFixContext,
  mapCriterionToEditorSection,
} from "@/components/AuditPanel";
import AuthAccountModal from "@/components/AuthAccountModal";
import CaseRegistryModal from "@/components/CaseRegistryModal";
import CompoundNoticePanel from "@/components/CompoundNoticePanel";
import DevConsoleModal from "@/components/DevConsoleModal";
import DraftDocxEditor, {
  type EditorGroupTab,
  mapSectionToGroup,
} from "@/components/DraftDocxEditor";
import LeftEvidencePane from "@/components/LeftEvidencePane";
import type { CompoundPrefillMeta } from "@/components/LegalDirectoryPanel";
import MobileBottomNav from "@/components/MobileBottomNav";
import OnboardingCardsModal from "@/components/OnboardingCardsModal";
import SplashScreenModal from "@/components/SplashScreenModal";
import SystemSettingsModal from "@/components/SystemSettingsModal";
import TopNavbar, { type ActiveAppMode } from "@/components/TopNavbar";
import UIPAdvisorPanel, { type PakarWorkspaceTab } from "@/components/UIPAdvisorPanel";
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

type IpWorkspaceStep = 1 | 2 | 3;

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

const HOME_OPERATION_CHIPS: Array<{ label: string; question: string }> = [
  {
    label: "Premis Makanan",
    question: "Restoran kotor ada najis tikus dan 2 pekerja tiada suntikan tifoid",
  },
  {
    label: "Vape / Merokok",
    question: "Guru tangkap pelajar sedang hisap vape dalam tandas sekolah",
  },
  {
    label: "Pembiakan Aedes",
    question: "Pemeriksaan rumah jumpa jentik-jentik Aedes dalam kolah bilik air",
  },
  {
    label: "Tibi / Penyakit Berjangkit",
    question: "Pesakit Tibi positif cicir rawatan dan enggan hadir ke klinik kesihatan",
  },
];

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
        ? "Seksyen 16(2) Akta 852"
        : rec.akta_utama === "Akta 154"
          ? "Seksyen 13(1) dibaca bersama Seksyen 13(2) Akta 154"
          : rec.akta_utama === "Akta 342"
            ? "Seksyen 22(b) Akta 342"
            : "Peraturan 11(1) PPKM 2009 [P.U. (A) 95/2009]",
    peruntukan_kompaun:
      rec.akta_utama === "Akta 852"
        ? "Seksyen 48 Akta 852 [P.U. (A) 259/2024]"
        : rec.akta_utama === "Akta 154"
          ? "Seksyen 25 Akta 154 (Maksimum RM500)"
          : rec.akta_utama === "Akta 342"
            ? "Seksyen 25 Akta 342 [P.U. (A) 139/2025]"
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
    kronologi_kes: [
      { tarikh: "", peristiwa: "Pemeriksaan premis / operasi penguatkuasaan dijalankan." },
    ],
    kertas_cadangan_io:
      "Mohon pertimbangan dan izin mendakwa daripada Timbalan Pendakwa Raya (TPR).",
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

function composeCaseTextFromDraft(
  draft: DraftGenerationResponse,
  fallbackText: string
): string {
  const sections: string[] = [];

  if (fallbackText.trim()) {
    sections.push(`=== REKOD ASAL KES ===\n${fallbackText.trim()}`);
  }

  const b114 = draft.borang_114;
  sections.push(
    [
      "=== BORANG 114 (PERTUDUHAN) ===",
      `Mahkamah: ${b114.mahkamah}`,
      `No. Kes: ${b114.no_kes}`,
      `Nama Tertuduh (OKT): ${b114.nama_tertuduh}`,
      `No. K/P Tertuduh: ${b114.no_kp_tertuduh}`,
      `Alamat: ${b114.alamat_tertuduh}`,
      `Tarikh & Masa Kejadian: ${b114.tarikh_kejadian} ${b114.masa_kejadian}`,
      `Tempat Kejadian: ${b114.tempat_kejadian}`,
      `Seksyen Kesalahan: ${b114.akta_dan_seksyen}`,
      `Seksyen Hukuman: ${b114.seksyen_hukuman} (${b114.hukuman_maksimum})`,
      `Teks Pertuduhan: ${b114.teks_pertuduhan}`,
    ].join("\n")
  );

  if (draft.saman_111) {
    sections.push(
      `=== SAMAN 111 ===\nMahkamah: ${draft.saman_111.mahkamah}\nTarikh Hadir: ${draft.saman_111.tarikh_hadir} ${draft.saman_111.masa_hadir}`
    );
  }

  if (draft.fakta_kes?.trim()) {
    sections.push(`=== FAKTA KES ===\n${draft.fakta_kes.trim()}`);
  }

  if (Array.isArray(draft.minit_ip) && draft.minit_ip.length > 0) {
    sections.push(
      "=== KERTAS MINIT IP ===\n" +
        draft.minit_ip
          .map((m) => `${m.bil} (${m.tarikh}) [${m.daripada} -> ${m.kepada}]: ${m.kandungan}`)
          .join("\n")
    );
  } else if (typeof draft.minit_ip === "string" && draft.minit_ip.trim()) {
    sections.push(`=== KERTAS MINIT IP ===\n${draft.minit_ip.trim()}`);
  }

  if (draft.kertas_cadangan_io?.trim()) {
    sections.push(`=== CADANGAN IO & IZIN MENDAKWA TPR ===\n${draft.kertas_cadangan_io.trim()}`);
  }

  if (draft.senarai_saksi?.length) {
    sections.push(
      "=== SENARAI SAKSI ===\n" +
        draft.senarai_saksi
          .map((s) => `${s.bil}: ${s.nama} (${s.no_kp}) - ${s.jawatan_peranan}, ${s.alamat_hubungan}`)
          .join("\n")
    );
  }

  if (draft.senarai_eksibit?.length) {
    sections.push(
      "=== SENARAI EKSIBIT ===\n" +
        draft.senarai_eksibit
          .map((e) => `${e.tanda}: ${e.perihal} | Lak/Seal: ${e.no_lak_seal} | Simpanan: ${e.lokasi_simpanan}`)
          .join("\n")
    );
  }

  if (draft.sijil_90a) {
    const s90 = draft.sijil_90a;
    sections.push(
      [
        "=== PERAKUAN DOKUMEN KOMPUTER (SIJIL SEKSYEN 90A AKTA KETERANGAN 1950) ===",
        `Pegawai: ${s90.nama_pegawai} (${s90.jawatan}, ${s90.pejabat_pkd})`,
        `Kamera / Peranti: ${s90.peranti_kamera}`,
        `Komputer: ${s90.perihal_komputer}`,
        `Pencetak: ${s90.perihal_pencetak}`,
        `Dokumen Digital: ${s90.senarai_dokumen_digital}`,
      ].join("\n")
    );
  }

  if (draft.rakaman_112?.trim()) {
    sections.push(`=== RAKAMAN PERCAKAPAN SEKSYEN 112 KTJ ===\n${draft.rakaman_112.trim()}`);
  }

  if (draft.diari_siasatan?.length) {
    sections.push(
      "=== DIARI SIASATAN (SEKSYEN 119 KTJ) ===\n" +
        draft.diari_siasatan
          .map((d) => `${d.bil}. ${d.tarikh} ${d.masa} (${d.pegawai}): ${d.butiran_tindakan}`)
          .join("\n")
    );
  }

  return sections.join("\n\n");
}

function getOnboardingHideKey(user: OfficerProfile): string {
  const ident = (user.email || user.id || "default").trim().toLowerCase();
  return `uip_onboarding_cards_hide_v1:${ident}`;
}

export default function UIPCommandPage() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [cases, setCases] = useState<IPCaseRecord[]>([]);
  const [activeCaseId, setActiveCaseId] = useState<string>("");
  const [workflow, setWorkflow] = useState<WorkflowMode>("audit_ip");
  const [aktaUtama, setAktaUtama] = useState<string>("Akta 852");
  const [useOllama] = useState<boolean>(true);
  const [caseText, setCaseText] = useState<string>("");

  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [fileTriggerNonce, setFileTriggerNonce] = useState(0);

  const [activeTab, setActiveTab] = useState<ActiveAppMode>("home");
  const [ipStep, setIpStep] = useState<IpWorkspaceStep>(1);
  const [auditSubView, setAuditSubView] = useState<"criteria" | "folder" | "privacy">("criteria");

  // Home Smart Ask & One-Click Demo wiring
  const [homeQuestion, setHomeQuestion] = useState("");
  const [advisorInitialQuestion, setAdvisorInitialQuestion] = useState<string | null>(null);
  const [advisorQueryNonce, setAdvisorQueryNonce] = useState(0);
  const [pakarTab, setPakarTab] = useState<PakarWorkspaceTab>("ask");
  const [pakarTabNonce, setPakarTabNonce] = useState(0);
  const [compoundAutoCheckNonce, setCompoundAutoCheckNonce] = useState(0);

  // Case workspace states
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
  const [activeFixContext, setActiveFixContext] = useState<AuditFixContext | null>(null);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);
  const [toastMsg, setToastMsg] = useState<string | null>(null);

  const [settingsOpen, setSettingsOpen] = useState(false);
  const [devConsoleOpen, setDevConsoleOpen] = useState(false);
  const [registryOpen, setRegistryOpen] = useState(false);
  const [registryInitialMode, setRegistryInitialMode] = useState<"list" | "new">("list");
  const [authOpen, setAuthOpen] = useState(false);
  const [authInitialTab, setAuthInitialTab] = useState<
    "google" | "login" | "register" | "profile"
  >("google");
  const [onboardingOpen, setOnboardingOpen] = useState(false);
  const [onboardingDontShow, setOnboardingDontShow] = useState(false);

  const [authToken, setAuthToken] = useState<string | null>(null);
  const [officer, setOfficer] = useState<OfficerProfile | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [isOnline, setIsOnline] = useState(true);

  useEffect(() => {
    if (typeof window === "undefined") return;
    setIsOnline(window.navigator.onLine);
    const onOnline = () => setIsOnline(true);
    const onOffline = () => setIsOnline(false);
    window.addEventListener("online", onOnline);
    window.addEventListener("offline", onOffline);
    return () => {
      window.removeEventListener("online", onOnline);
      window.removeEventListener("offline", onOffline);
    };
  }, []);

  const showToast = useCallback((msg: string) => {
    setToastMsg(msg);
    window.setTimeout(() => {
      setToastMsg((prev) => (prev === msg ? null : prev));
    }, 3800);
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
    (rec: IPCaseRecord, currentOfficer?: OfficerProfile | null, force = false): boolean => {
      if (!force && hasUnsavedChanges && rec.id !== activeCaseId) {
        const ok = window.confirm(
          "Anda mempunyai perubahan yang belum disimpan pada kes semasa. Tukar kes tanpa menyimpan?"
        );
        if (!ok) return false;
      }
      setActiveCaseId(rec.id);
      setAktaUtama(rec.akta_utama);
      setWorkflow(rec.workflow || "audit_ip");
      setCaseText(rec.case_text || "");
      setAuditReport(rec.audit_report || null);
      setDraft(rec.draft || null);
      setRedaction(null);
      setActiveFixContext(null);
      setCompoundNotice(buildCompoundFromCase(rec, currentOfficer));
      setHasUnsavedChanges(false);
      setErrorBanner(null);
      return true;
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
            ? `Sistem tidak dapat disambungkan buat masa ini (${err.message}). Sila cuba sebentar lagi.`
            : "Sistem tidak dapat disambungkan buat masa ini. Sila semak sambungan internet anda."
        );
      } finally {
        if (mounted) setAuthChecked(true);
      }
    }
    bootstrap();
    return () => {
      mounted = false;
    };
  }, []);

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
    setErrorBanner(null);

    if (mode === "directory") {
      setActiveTab("advisor");
      setPakarTab("directory");
      setPakarTabNonce((n) => n + 1);
    } else if (mode === "advisor") {
      setActiveTab("advisor");
      setPakarTab("ask");
      setPakarTabNonce((n) => n + 1);
    } else if (mode === "compound") {
      setActiveTab("compound");
      setWorkflow("notis_kompaun");
    } else if (mode === "draft") {
      setActiveTab("draft");
      setWorkflow("ip_builder");
      setIpStep(3);
    } else if (mode === "redaction") {
      setActiveTab("redaction");
      setWorkflow("audit_ip");
      setAuditSubView("privacy");
      setIpStep(2);
    } else if (mode === "audit") {
      setActiveTab("audit");
      setWorkflow("audit_ip");
      setAuditSubView("criteria");
      setIpStep(auditReport ? 2 : draft ? 3 : 1);
    } else {
      setActiveTab(mode);
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
    setActiveFixContext(null);
    setExtractedEvidence(null);
    handleFileSelected(null);
    setCompoundNotice({
      ...EMPTY_COMPOUND_NOTICE,
      pegawai_pengeluar: officer?.full_name || "",
      no_kad_kuasa: officer?.kkm_authority_card_no || "",
    });
    setHasUnsavedChanges(false);
    setIpStep(1);
    setErrorBanner(null);
    showToast("Sedia untuk kes baharu — muat naik fail atau taip fakta kes.");
  };

  const handleLoadSampleCase = async (): Promise<{ text: string; akta: string } | null> => {
    if (!confirmDiscardIfDirty()) return null;
    setErrorBanner(null);
    const sample = cases.find((c) => c.id.startsWith("kes-")) || cases[0];
    if (sample) {
      applyCaseRecord(sample, officer, true);
      showToast(`Contoh kes dimuatkan: ${sample.tajuk_kes}`);
      return { text: sample.case_text || "", akta: sample.akta_utama };
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
        setRedaction(null);
        setActiveFixContext(null);
        setExtractedEvidence(null);
        setCompoundNotice({
          ...EMPTY_COMPOUND_NOTICE,
          pegawai_pengeluar: officer?.full_name || "",
          no_kad_kuasa: officer?.kkm_authority_card_no || "",
        });
        setHasUnsavedChanges(false);
        showToast(`Contoh kes dimuatkan: ${s.title}`);
        return { text: s.text, akta: s.akta_utama };
      }
    } catch (err) {
      setErrorBanner(err instanceof Error ? err.message : "Gagal memuatkan contoh kes.");
    }
    return null;
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
      showToast("Fail kes berjaya disimpan.");
    } catch (err) {
      setErrorBanner(err instanceof Error ? err.message : "Gagal menyimpan fail kes.");
    } finally {
      setSavingCase(false);
    }
  };

  const handleRunAudit = async (overrideText?: string, overrideAkta?: string) => {
    const usingOverride = typeof overrideText === "string" && overrideText.trim().length > 0;
    const textToAudit = usingOverride ? overrideText.trim() : caseText;
    const aktaToUse = overrideAkta || aktaUtama;
    const fileToUse = usingOverride ? null : uploadedFile;

    if (!textToAudit.trim() && !fileToUse) {
      setErrorBanner(
        "Sila muat naik fail PDF/gambar atau taip catatan fakta kes di Langkah 1 dahulu."
      );
      setIpStep(1);
      return;
    }

    setAuditLoading(true);
    setErrorBanner(null);
    try {
      const report = await runIpAudit({
        text: textToAudit,
        aktaUtama: aktaToUse,
        useOllama,
        caseId: activeCaseId || undefined,
        file: fileToUse,
      });
      setAuditReport(report);
      const nextText = report.extracted_text && fileToUse ? report.extracted_text : textToAudit;
      if (report.extracted_text && fileToUse) {
        setCaseText(report.extracted_text);
      }
      setRedaction({
        original_text: report.extracted_text || textToAudit,
        redacted_text: report.redaction_summary.redacted_text,
        token_map: report.redaction_summary.token_map,
        entities: report.redaction_summary.entities,
        engine_used: report.redaction_summary.engine_used,
        ollama_available: report.redaction_summary.ollama_available,
        warnings: report.redaction_summary.warnings,
      });
      setActiveFixContext(null);

      const isSavedUserCase = Boolean(activeCaseId && !activeCaseId.startsWith("kes-"));
      if (isSavedUserCase) {
        saveCaseRecord({
          id: activeCaseId,
          akta_utama: aktaToUse,
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
        setHasUnsavedChanges(true);
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
      setAuditSubView("criteria");
      setIpStep(2);
      showToast(`Semakan Pra-TPR siap — Skor ${report.overall_score}%`);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      setErrorBanner(err instanceof Error ? err.message : "Gagal menjalankan semakan Pra-TPR.");
    } finally {
      setAuditLoading(false);
    }
  };

  const handleRunDraft = async (targetSection?: string, fixContext?: AuditFixContext) => {
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
      setErrorBanner("Sila muat naik fail kes atau taip catatan fakta kes di Langkah 1 dahulu.");
      setIpStep(1);
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
            draftRes.redaction_preview.redacted_text ||
            draftRes.redaction_preview.redacted_excerpt,
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
      if (fixContext) {
        setActiveFixContext(fixContext);
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
      setIpStep(3);
      showToast("Draf Fail IP siap — semak dan sunting sebelum muat turun Word (.docx).");
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      setErrorBanner(err instanceof Error ? err.message : "Gagal menjana draf Fail IP.");
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
        showToast("Butiran asas kes aktif telah dimasukkan ke borang kompaun.");
      } else {
        setErrorBanner(
          "Tiada kes aktif dipilih. Anda boleh ambil foto Sijil SSM atau isi borang di bawah secara manual."
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
        showToast("Butiran kes berjaya diisi ke Borang Notis Kompaun.");
      }
    } catch (err) {
      setErrorBanner(err instanceof Error ? err.message : "Gagal mengisi data ke borang kompaun.");
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
      throw new Error(
        "Teks tidak dapat dibaca daripada fail ini. Pastikan foto jelas dan tidak kabur."
      );
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
      showToast(`Maklumat daripada ${file.name} berjaya diisi ke Notis Kompaun.`);
    }
  };

  const handleStartBlankDraft = () => {
    const blank = buildBlankDraft(aktaUtama, officer, compoundNotice);
    setDraft(blank);
    setHasUnsavedChanges(true);
    setActiveTab("draft");
    setIpStep(3);
    showToast("Borang IP kosong dibuka — semua ruangan sedia diisi.");
  };

  const handleRunRedaction = async () => {
    if (!caseText.trim()) {
      setErrorBanner("Tiada fakta kes untuk disemak perlindungan data.");
      setIpStep(1);
      return;
    }
    setRedactLoading(true);
    setErrorBanner(null);
    try {
      const res = await runRedaction(caseText, useOllama);
      setRedaction(res);
      showToast(`${res.entities.length} maklumat peribadi telah dikenal pasti dan dilindungi.`);
    } catch (err) {
      setErrorBanner(err instanceof Error ? err.message : "Gagal menyemak perlindungan data.");
    } finally {
      setRedactLoading(false);
    }
  };

  const handleExtractEvidence = async (
    docHint: string,
    replaceText = false,
    fileOverride?: File
  ) => {
    const targetFile = fileOverride || uploadedFile;
    if (!targetFile) return;
    setExtractLoading(true);
    setErrorBanner(null);
    try {
      const res = await extractEvidence(targetFile, docHint);
      setExtractedEvidence(res);
      if (res.raw_text) {
        setCaseText((prev) =>
          !replaceText && prev.trim()
            ? `${prev.trim()}\n\n--- HASIL BACAAN FAIL (${res.filename}) ---\n${res.raw_text}`
            : res.raw_text
        );
        setHasUnsavedChanges(true);
      }
      showToast(`Teks berjaya dibaca daripada ${res.filename}.`);
    } catch (err) {
      setErrorBanner(err instanceof Error ? err.message : "Gagal membaca fail yang dimuat naik.");
    } finally {
      setExtractLoading(false);
    }
  };

  const handleApplyFromAdvisorOrDirectory = (
    draftText: string,
    aktaDisyorkan: string,
    bukaIp: boolean,
    compoundMeta?: CompoundPrefillMeta
  ) => {
    if (!confirmDiscardIfDirty()) return;
    setCaseText(draftText);
    setAktaUtama(aktaDisyorkan);
    setActiveCaseId("");
    setDraft(null);
    setAuditReport(null);
    setActiveFixContext(null);
    setHasUnsavedChanges(true);

    if (!bukaIp) {
      setCompoundNotice((prev) => ({
        ...EMPTY_COMPOUND_NOTICE,
        ...prev,
        peruntukan_undang: compoundMeta?.seksyen || prev.peruntukan_undang,
        peruntukan_kompaun: compoundMeta?.kuasaKompaun || prev.peruntukan_kompaun,
        amaun_kompaun_rm: compoundMeta?.amaun || prev.amaun_kompaun_rm,
        tempoh_bayaran: compoundMeta?.tempoh || prev.tempoh_bayaran,
        kesalahan_ringkas: compoundMeta?.kesalahanRingkas || prev.kesalahan_ringkas,
        pegawai_pengeluar: prev.pegawai_pengeluar || officer?.full_name || "",
        no_kad_kuasa: prev.no_kad_kuasa || officer?.kkm_authority_card_no || "",
      }));
      setActiveTab("compound");
      setWorkflow("notis_kompaun");
      showToast(
        "Seksyen dan butiran kesalahan telah diisi ke Borang Kompaun — lengkapkan nama dan alamat penerima."
      );
    } else {
      setActiveTab("audit");
      setWorkflow("ip_builder");
      setIpStep(1);
      showToast(
        "Fakta kes dimuatkan ke Langkah 1 Fail IP — tekan 'Semak Pra-TPR' atau terus bina draf."
      );
    }

    if (typeof window !== "undefined") {
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  };

  // One-click demos from Home
  const handleHomeAskSubmit = (q: string) => {
    const clean = q.trim();
    if (!clean) {
      handleSelectMode("advisor");
      return;
    }
    setAdvisorInitialQuestion(clean);
    setAdvisorQueryNonce((n) => n + 1);
    setPakarTab("ask");
    setPakarTabNonce((n) => n + 1);
    setActiveTab("advisor");
    setHomeQuestion("");
    if (typeof window !== "undefined") {
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  };

  const handleDemoCompoundLimit = () => {
    if (!confirmDiscardIfDirty()) return;
    setCompoundNotice({
      no_notis: "KKM/PKDKN/KOM/DEMO-01",
      nama_penerima: "Ahmad bin Abdullah",
      no_kp: "840512-11-5213",
      nama_premis: "Kediaman No. 14, Taman Gong Badak",
      alamat_kejadian: "No. 14, Jalan Gong Badak 2, 21300 Kuala Nerus, Terengganu",
      no_ssm: "-",
      tarikh_masa: "22/11/2026, 10.30 pagi",
      peruntukan_undang: "Seksyen 13(1) dibaca bersama Seksyen 13(2) Akta 154",
      peruntukan_kompaun: "Seksyen 25 Akta 154 (Maksimum RM500)",
      kesalahan_ringkas:
        "Membiak serangga pembawa penyakit (larva nyamuk Aedes) dalam bekas takungan air di kawasan rumah.",
      amaun_kompaun_rm: "RM 1,000.00",
      tempoh_bayaran: "14 hari dari tarikh serahan notis",
      pegawai_pengeluar: officer?.full_name || "PPKP PKD Kuala Nerus",
      no_kad_kuasa: officer?.kkm_authority_card_no || "KKM-TRG-2024-0812",
      status_serahan: "tandatangan_terima",
      saksi_ppkp: "PPKP Mohd Faizal bin Ismail",
    });
    setActiveTab("compound");
    setWorkflow("notis_kompaun");
    setCompoundAutoCheckNonce((n) => n + 1);
    showToast("Contoh notis Akta 154 (RM1,000) dimuatkan — lihat semakan had RM500 automatik.");
  };

  const handleDemoAuditIp = async () => {
    const loaded = await handleLoadSampleCase();
    if (!loaded || !loaded.text.trim()) return;
    setActiveTab("audit");
    setIpStep(1);
    await handleRunAudit(loaded.text, loaded.akta);
  };

  const handleAuthenticatedSuccess = async (user: OfficerProfile, token: string) => {
    window.localStorage.setItem("uip_auth_token", token);
    setAuthToken(token);
    setOfficer(user);
    setAuthOpen(false);
    setActiveTab("home");
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
    setActiveFixContext(null);
    setExtractedEvidence(null);
    handleFileSelected(null);
    setCaseText("");
    setCompoundNotice(EMPTY_COMPOUND_NOTICE);
    setHasUnsavedChanges(false);
    setErrorBanner(null);
    setActiveTab("home");
    setIpStep(1);
    window.localStorage.removeItem("uip_auth_token");
  };

  const auditIssueCounts = useMemo(() => {
    const counts: Partial<Record<EditorGroupTab, number>> = {};
    if (!auditReport?.criteria_results) return counts;
    for (const item of auditReport.criteria_results) {
      if (item.status === "GAGAL" || item.status === "SEMAK") {
        const grp = mapSectionToGroup(mapCriterionToEditorSection(item.code));
        counts[grp] = (counts[grp] || 0) + 1;
      }
    }
    return counts;
  }, [auditReport]);

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
            <div className="pt-1 text-xs text-slate-300">Sedang membuka akaun anda...</div>
          </div>
        </div>
      </div>
    );
  }

  if (!officer) {
    return (
      <div className="min-h-[100dvh] bg-[#08192e]">
        {(!isOnline || errorBanner) && (
          <div className="fixed inset-x-0 top-3 z-[70] mx-auto max-w-xl px-3">
            {!isOnline && (
              <div className="mb-2 flex items-center gap-2 rounded-xl border border-amber-300 bg-amber-50 px-4 py-2.5 text-xs font-bold text-amber-950 shadow-lg">
                <AlertCircle className="h-4 w-4 shrink-0 text-amber-600" />
                <span>Tiada sambungan internet. Sila sambungkan talian untuk log masuk.</span>
              </div>
            )}
            {errorBanner && (
              <div className="flex items-center justify-between gap-2 rounded-xl border border-rose-300 bg-rose-50 px-4 py-2.5 text-xs font-semibold text-rose-900 shadow-lg">
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
            )}
          </div>
        )}
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
  const missingKadKuasa = !officer.kkm_authority_card_no?.trim();
  const hasCaseInput = Boolean(caseText.trim() || uploadedFile);
  const activeCaseObj = cases.find((c) => c.id === activeCaseId);
  const isSampleCase = Boolean(activeCaseObj?.id?.startsWith("kes-"));
  const activeCaseTitle = activeCaseObj
    ? activeCaseObj.tajuk_kes.replace(/^Kes \d+:\s*/, "")
    : uploadedFile?.name;

  const isIpWorkspace = activeTab === "audit" || activeTab === "draft" || activeTab === "redaction";

  const mobileBadges: Partial<Record<ActiveAppMode, string>> = {};
  if (auditReport) mobileBadges.audit = `${auditReport.overall_score}%`;
  if (draft) mobileBadges.draft = "✓";

  const recentCases = cases.filter((c) => !c.id.startsWith("kes-")).slice(0, 3);
  const quickResumeList = recentCases.length > 0 ? recentCases : cases.slice(0, 3);

  return (
    <div className="flex min-h-[100dvh] flex-col bg-[#f4f7fb] pb-24 lg:pb-0">
      <TopNavbar
        status={status}
        activeMode={activeTab}
        onSelectMode={handleSelectMode}
        caseCount={cases.length}
        onOpenCases={() => {
          setRegistryInitialMode("list");
          setRegistryOpen(true);
        }}
        onOpenSettings={() => setSettingsOpen(true)}
        officer={officer}
        isDevAdmin={isDevAdmin}
        onOpenAccount={() => {
          setAuthInitialTab("profile");
          setAuthOpen(true);
        }}
        onOpenSplash={() => handleSelectMode("home")}
        onOpenOnboarding={handleOpenOnboardingManual}
        onOpenDevConsole={() => setDevConsoleOpen(true)}
      />

      {!isOnline && (
        <div className="border-b border-amber-300 bg-amber-50 px-4 py-2 text-center text-xs font-bold text-amber-950">
          Tiada sambungan internet dikesan. Sesetengah fungsi simpanan dan bantuan AI memerlukan
          talian internet.
        </div>
      )}

      {/* Toast & Ralat Terapung */}
      {(toastMsg || errorBanner) && (
        <div className="pointer-events-none fixed inset-x-0 top-16 z-50 mx-auto max-w-2xl space-y-2 px-3 sm:px-4">
          {toastMsg && (
            <div className="pointer-events-auto flex items-center gap-2 rounded-xl border border-emerald-300 bg-emerald-50/95 px-4 py-2.5 text-xs font-bold text-emerald-900 shadow-lg backdrop-blur">
              <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600" />
              <span>{toastMsg}</span>
            </div>
          )}
          {errorBanner && (
            <div className="pointer-events-auto flex items-center justify-between gap-2 rounded-xl border border-rose-300 bg-rose-50/95 px-4 py-2.5 text-xs font-semibold text-rose-900 shadow-lg backdrop-blur">
              <div className="flex items-center gap-2">
                <AlertCircle className="h-4 w-4 shrink-0 text-rose-600" />
                <span>{errorBanner}</span>
              </div>
              <button
                type="button"
                onClick={() => setErrorBanner(null)}
                className="shrink-0 rounded px-2 py-1 text-xs font-bold hover:bg-rose-100"
              >
                Tutup
              </button>
            </div>
          )}
        </div>
      )}

      {/* PAPARAN 0: UTAMA (TENANG, JELAS & CUBA DALAM 10 SAAT) */}
      {activeTab === "home" && (
        <main className="mx-auto w-full max-w-5xl flex-1 space-y-5 p-4 sm:p-6">
          {/* 1. Ucapan & Bar Tanya Terus */}
          <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-xs font-bold text-slate-500">
                  {officer.district_pkd || "PKD Kuala Nerus"} • Gred {officer.grade}
                </p>
                <h2 className="mt-1 text-lg font-extrabold text-slate-900 sm:text-2xl">
                  Selamat bertugas, {officer.full_name}. Nak buat kerja apa hari ini?
                </h2>
                <p className="mt-1 text-xs text-slate-600 sm:text-sm">
                  Tanya seksyen undang-undang, semak notis kompaun, atau lengkapkan Fail IP hingga
                  siap muat turun Word.
                </p>
              </div>

              <button
                type="button"
                onClick={() => {
                  setRegistryInitialMode("new");
                  setRegistryOpen(true);
                }}
                className="inline-flex min-h-[42px] items-center gap-1.5 rounded-xl bg-[#0f2744] px-4 py-2 text-xs font-extrabold text-white shadow-sm transition hover:bg-slate-800"
              >
                <Plus className="h-4 w-4 text-amber-300" />
                Daftar Kes Baharu
              </button>
            </div>

            {/* Smart Ask Bar */}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleHomeAskSubmit(homeQuestion);
              }}
              className="mt-4 flex flex-col gap-2 sm:flex-row"
            >
              <div className="relative flex-1">
                <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <input
                  type="text"
                  value={homeQuestion}
                  onChange={(e) => setHomeQuestion(e.target.value)}
                  placeholder="Tanya situasi di lokasi... cth: Pelajar hisap vape dalam tandas sekolah"
                  className="min-h-[46px] w-full rounded-xl border border-slate-300 bg-slate-50/70 pl-10 pr-4 text-sm text-slate-900 placeholder:text-slate-400 transition focus:border-[#0f2744] focus:bg-white focus:outline-none focus:ring-2 focus:ring-slate-200"
                />
              </div>
              <button
                type="submit"
                className="inline-flex min-h-[46px] items-center justify-center gap-1.5 rounded-xl bg-[#0f2744] px-5 text-xs font-extrabold text-white shadow-sm transition hover:bg-slate-800"
              >
                <MessageSquareQuote className="h-4 w-4 text-amber-300" />
                Tanya Pakar
              </button>
            </form>

            {/* 4 Chip Operasi PKD */}
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <span className="text-xs font-semibold text-slate-500">Topik pantas:</span>
              {HOME_OPERATION_CHIPS.map((chip) => (
                <button
                  key={chip.label}
                  type="button"
                  onClick={() => handleHomeAskSubmit(chip.question)}
                  className="min-h-[34px] rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-semibold text-slate-700 transition hover:border-[#0f2744] hover:bg-slate-100 hover:text-[#0f2744]"
                >
                  {chip.label}
                </button>
              ))}
            </div>
          </section>

          {/* 2. Cuba Dalam 10 Saat (Guna Contoh Kes Sebenar) */}
          <section className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4 sm:p-5">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <span className="inline-flex h-7 w-7 items-center justify-center rounded-lg bg-[#0f2744] text-amber-300">
                  <Zap className="h-4 w-4" />
                </span>
                <div>
                  <h3 className="text-xs font-extrabold text-slate-900 sm:text-sm">
                    Cuba Dalam 10 Saat (Guna Contoh Kes Sebenar)
                  </h3>
                  <p className="text-xs text-slate-600">
                    Baru pertama kali buka? Klik mana-mana butang untuk terus lihat hasil sebenar.
                  </p>
                </div>
              </div>
            </div>

            <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-3">
              <button
                type="button"
                onClick={() =>
                  handleHomeAskSubmit("Guru tangkap pelajar sedang hisap vape dalam tandas sekolah")
                }
                className="flex min-h-[46px] items-center justify-between gap-2 rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-left text-xs font-bold text-slate-800 shadow-sm transition hover:border-[#0f2744] hover:bg-slate-50"
              >
                <span className="flex items-center gap-2">
                  <Sparkles className="h-4 w-4 shrink-0 text-amber-600" />
                  <span>Cuba Tanya Pakar (Pelajar Hisap Vape)</span>
                </span>
                <ArrowRight className="h-3.5 w-3.5 shrink-0 text-slate-400" />
              </button>

              <button
                type="button"
                onClick={handleDemoCompoundLimit}
                className="flex min-h-[46px] items-center justify-between gap-2 rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-left text-xs font-bold text-slate-800 shadow-sm transition hover:border-[#0f2744] hover:bg-slate-50"
              >
                <span className="flex items-center gap-2">
                  <FileCheck2 className="h-4 w-4 shrink-0 text-amber-600" />
                  <span>Cuba Semak Kompaun (Had RM500)</span>
                </span>
                <ArrowRight className="h-3.5 w-3.5 shrink-0 text-slate-400" />
              </button>

              <button
                type="button"
                disabled={auditLoading}
                onClick={handleDemoAuditIp}
                className="flex min-h-[46px] items-center justify-between gap-2 rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-left text-xs font-bold text-slate-800 shadow-sm transition hover:border-[#0f2744] hover:bg-slate-50 disabled:opacity-60"
              >
                <span className="flex items-center gap-2">
                  {auditLoading ? (
                    <Loader2 className="h-4 w-4 shrink-0 animate-spin text-[#0f2744]" />
                  ) : (
                    <Scale className="h-4 w-4 shrink-0 text-amber-600" />
                  )}
                  <span>Cuba Semak Fail IP (20 Semakan TPR)</span>
                </span>
                <ArrowRight className="h-3.5 w-3.5 shrink-0 text-slate-400" />
              </button>
            </div>
          </section>

          {/* 3. 3 Kad Ruang Kerja Utama (Tenang & Jelas Input → Hasil) */}
          <section className="grid grid-cols-1 gap-3.5 md:grid-cols-3">
            <button
              type="button"
              onClick={() => handleSelectMode("advisor")}
              className="group flex flex-col justify-between rounded-2xl border border-slate-200 bg-white p-5 text-left shadow-sm transition hover:border-[#0f2744] hover:shadow-md"
            >
              <div>
                <div className="flex items-center justify-between">
                  <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-slate-100 text-[#0f2744] transition group-hover:bg-[#0f2744] group-hover:text-white">
                    <MessageSquareQuote className="h-5 w-5" />
                  </div>
                  <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-[11px] font-bold text-slate-600">
                    Situasi → SOP &amp; Akta
                  </span>
                </div>
                <h3 className="mt-4 text-base font-extrabold text-slate-900">Pakar &amp; Akta</h3>
                <p className="mt-1.5 text-xs leading-relaxed text-slate-600">
                  Tanya situasi di lokasi untuk tahu ada kesalahan atau tidak, semak senarai
                  kesalahan dan rujuk teks penuh 6 akta KKM.
                </p>
              </div>
              <div className="mt-4 inline-flex items-center gap-1 text-xs font-extrabold text-[#0f2744]">
                Buka Pakar &amp; Akta <ArrowRight className="h-3.5 w-3.5" />
              </div>
            </button>

            <button
              type="button"
              onClick={() => handleSelectMode("compound")}
              className="group flex flex-col justify-between rounded-2xl border border-slate-200 bg-white p-5 text-left shadow-sm transition hover:border-[#0f2744] hover:shadow-md"
            >
              <div>
                <div className="flex items-center justify-between">
                  <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-slate-100 text-[#0f2744] transition group-hover:bg-[#0f2744] group-hover:text-white">
                    <FileCheck2 className="h-5 w-5" />
                  </div>
                  <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-[11px] font-bold text-slate-600">
                    Foto SSM → Notis Word
                  </span>
                </div>
                <h3 className="mt-4 text-base font-extrabold text-slate-900">Notis Kompaun</h3>
                <p className="mt-1.5 text-xs leading-relaxed text-slate-600">
                  Ambil foto Sijil SSM atau isi borang berpandu 3 langkah, semak 10 perkara wajib
                  dan muat turun Notis Word siap cetak.
                </p>
              </div>
              <div className="mt-4 inline-flex items-center gap-1 text-xs font-extrabold text-[#0f2744]">
                Buka Notis Kompaun <ArrowRight className="h-3.5 w-3.5" />
              </div>
            </button>

            <button
              type="button"
              onClick={() => handleSelectMode("audit")}
              className="group flex flex-col justify-between rounded-2xl border border-slate-200 bg-white p-5 text-left shadow-sm transition hover:border-[#0f2744] hover:shadow-md"
            >
              <div>
                <div className="flex items-center justify-between">
                  <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-slate-100 text-[#0f2744] transition group-hover:bg-[#0f2744] group-hover:text-white">
                    <Scale className="h-5 w-5" />
                  </div>
                  <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-[11px] font-bold text-slate-600">
                    PDF / Fakta → Fail IP Word
                  </span>
                </div>
                <h3 className="mt-4 text-base font-extrabold text-slate-900">
                  Fail IP (Semak &amp; Bina)
                </h3>
                <p className="mt-1.5 text-xs leading-relaxed text-slate-600">
                  Muat naik PDF Kertas Siasatan atau catatan kes untuk 20 semakan Pra-TPR, sunting
                  Borang 114, Saman 111 &amp; Sijil 90A, lalu muat turun Word.
                </p>
              </div>
              <div className="mt-4 inline-flex items-center gap-1 text-xs font-extrabold text-[#0f2744]">
                Buka Fail IP <ArrowRight className="h-3.5 w-3.5" />
              </div>
            </button>
          </section>

          {/* 4. Sambung Fail Terakhir */}
          {quickResumeList.length > 0 && (
            <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
              <div className="flex flex-wrap items-center justify-between gap-2 pb-3">
                <h3 className="text-xs font-extrabold uppercase tracking-wide text-slate-700">
                  {recentCases.length > 0 ? "Sambung Fail Kes Terakhir" : "Contoh Fail Kes Sedia Ada"}
                </h3>
                <button
                  type="button"
                  onClick={() => {
                    setRegistryInitialMode("list");
                    setRegistryOpen(true);
                  }}
                  className="inline-flex items-center gap-1 text-xs font-bold text-[#0f2744] hover:underline"
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
                      const ok = applyCaseRecord(c, officer, true);
                      if (!ok) return;
                      if (c.draft) {
                        setActiveTab("draft");
                        setIpStep(3);
                      } else if (c.audit_report) {
                        setActiveTab("audit");
                        setIpStep(2);
                      } else {
                        setActiveTab("audit");
                        setIpStep(1);
                      }
                    }}
                    className="flex flex-col items-start rounded-xl border border-slate-200 bg-slate-50/50 p-3.5 text-left transition hover:border-[#0f2744] hover:bg-slate-50"
                  >
                    <div className="flex w-full items-center justify-between gap-2">
                      <span className="rounded bg-[#0f2744] px-2 py-0.5 text-[11px] font-bold text-white">
                        {c.akta_utama}
                      </span>
                      <span className="text-[11px] font-semibold text-slate-600">
                        {c.skor_audit ? `Skor ${c.skor_audit}%` : c.status_kes}
                      </span>
                    </div>
                    <div className="mt-1.5 line-clamp-1 text-xs font-bold text-slate-900">
                      {c.tajuk_kes.replace(/^Kes \d+:\s*/, "")}
                    </div>
                    <div className="mt-0.5 text-xs text-slate-500">
                      {c.nama_okt || c.nama_premis || "Klik untuk sambung fail"}
                    </div>
                  </button>
                ))}
              </div>
            </section>
          )}
        </main>
      )}

      {/* PAPARAN 1: PAKAR & AKTA (TANYA SITUASI + SENARAI KESALAHAN & TEKS AKTA + SEJARAH) */}
      {(activeTab === "advisor" || activeTab === "directory") && (
        <main className="mx-auto w-full max-w-[1440px] flex-1 p-3 sm:p-5">
          <UIPAdvisorPanel
            aktaUtama={aktaUtama}
            authToken={authToken}
            officer={officer}
            isDevAdmin={isDevAdmin}
            initialQuestion={advisorInitialQuestion}
            initialQuestionNonce={advisorQueryNonce}
            initialWorkspaceTab={pakarTab}
            workspaceTabNonce={pakarTabNonce}
            onApplyToCaseBuilder={handleApplyFromAdvisorOrDirectory}
          />
        </main>
      )}

      {/* PAPARAN 2: NOTIS KOMPAUN */}
      {activeTab === "compound" && (
        <main className="mx-auto w-full max-w-5xl flex-1 p-3 sm:p-5">
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
            onOpenProfile={() => {
              setAuthInitialTab("profile");
              setAuthOpen(true);
            }}
            missingKadKuasa={missingKadKuasa}
            autoFillLoading={draftLoading}
            activeCaseTitle={activeCaseTitle}
            hasCaseSource={Boolean(caseText.trim() || uploadedFile || activeCaseId)}
            savingCase={savingCase}
            onSaveNotice={handleSaveCurrentCase}
            onDownloaded={(fname) =>
              showToast(`Fail ${fname} berjaya dimuat turun ke peranti anda.`)
            }
            autoCheckNonce={compoundAutoCheckNonce}
          />
        </main>
      )}

      {/* PAPARAN 3: PANDUAN */}
      {activeTab === "guide" && (
        <main className="mx-auto w-full max-w-5xl flex-1 p-3 sm:p-5">
          <AppGuidePanel onNavigateMode={handleSelectMode} />
        </main>
      )}

      {/* PAPARAN 4: RUANG KERJA FAIL IP BERSEPADU (3 LANGKAH JELAS — SATU LAJUR KEMAS) */}
      {isIpWorkspace && (
        <main className="mx-auto w-full max-w-5xl flex-1 space-y-4 p-3 sm:p-5">
          {/* Bar Tajuk Kes & Simpan */}
          <div className="flex flex-wrap items-center justify-between gap-2 rounded-2xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
            <div className="flex min-w-0 items-center gap-2 text-xs">
              <span className="shrink-0 rounded-md bg-[#0f2744] px-2.5 py-0.5 text-[11px] font-bold text-white">
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

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => {
                  setRegistryInitialMode("list");
                  setRegistryOpen(true);
                }}
                className="inline-flex min-h-[38px] items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs font-bold text-slate-700 hover:bg-slate-50"
              >
                <FolderOpen className="h-3.5 w-3.5 text-slate-500" />
                <span className="hidden sm:inline">Tukar Fail</span>
              </button>

              <button
                type="button"
                disabled={savingCase}
                onClick={handleSaveCurrentCase}
                className={`inline-flex min-h-[38px] items-center gap-1.5 rounded-xl border px-3.5 py-1.5 text-xs font-bold transition disabled:opacity-60 ${
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
            </div>
          </div>

          {/* Stepper 3 Langkah Fail IP */}
          <div className="grid grid-cols-3 gap-2 rounded-2xl border border-slate-200 bg-white p-1.5 shadow-sm">
            {[
              {
                step: 1 as IpWorkspaceStep,
                label: "1. Bahan Kes",
                shortLabel: "1. Bahan",
                done: hasCaseInput,
                badge: null as string | null,
              },
              {
                step: 2 as IpWorkspaceStep,
                label: "2. Semak Pra-TPR",
                shortLabel: "2. Semak",
                done: Boolean(auditReport),
                badge: auditReport ? `${auditReport.overall_score}%` : null,
              },
              {
                step: 3 as IpWorkspaceStep,
                label: "3. Edit & Muat Turun Word",
                shortLabel: "3. Word",
                done: Boolean(draft),
                badge: draft ? "Sedia" : null,
              },
            ].map((item) => {
              const active = ipStep === item.step;
              return (
                <button
                  key={item.step}
                  type="button"
                  onClick={() => {
                    setIpStep(item.step);
                    setActiveTab(item.step === 3 ? "draft" : "audit");
                    if (item.step === 2) setAuditSubView("criteria");
                  }}
                  className={`flex min-h-[44px] items-center justify-center gap-1.5 rounded-xl px-2.5 py-2 text-xs font-extrabold transition ${
                    active
                      ? "bg-[#0f2744] text-white shadow-sm"
                      : "text-slate-700 hover:bg-slate-100"
                  }`}
                >
                  <span className="hidden sm:inline">{item.label}</span>
                  <span className="sm:hidden">{item.shortLabel}</span>
                  {item.badge && (
                    <span
                      className={`rounded-full px-2 py-0.5 text-[10px] font-extrabold ${
                        active
                          ? "bg-white/20 text-white"
                          : "bg-slate-100 text-slate-700"
                      }`}
                    >
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </div>

          {/* LANGKAH 1: BAHAN KES */}
          {ipStep === 1 && (
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
              onLoadSampleCase={() => {
                void handleLoadSampleCase();
              }}
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
              onRunAudit={() => {
                void handleRunAudit();
              }}
              onRunDraft={() => {
                void handleRunDraft();
              }}
              onStartBlankDraft={handleStartBlankDraft}
              hasExistingResult={Boolean(auditReport || draft)}
              onBackToResult={() => setIpStep(auditReport ? 2 : 3)}
              onExtractEvidence={handleExtractEvidence}
              auditLoading={auditLoading}
              draftLoading={draftLoading}
              extractLoading={extractLoading}
              extractedEvidence={extractedEvidence}
              fileTriggerNonce={fileTriggerNonce}
            />
          )}

          {/* LANGKAH 2: SEMAK PRA-TPR (20 SEMAKAN + FAIL A–G + PERLINDUNGAN DATA) */}
          {ipStep === 2 && (
            <AuditPanel
              report={auditReport}
              redaction={redaction}
              redactLoading={redactLoading}
              onRunRedaction={handleRunRedaction}
              hasCaseInput={hasCaseInput}
              activeCaseTitle={activeCaseTitle}
              auditLoading={auditLoading}
              draftLoading={draftLoading}
              onRunAudit={() => {
                void handleRunAudit();
              }}
              onSwitchToInput={() => {
                setIpStep(1);
                setFileTriggerNonce((n) => n + 1);
              }}
              onLoadSampleCase={() => {
                void handleLoadSampleCase();
              }}
              onJumpToEditor={(sectionId, fixContext) => {
                if (fixContext) setActiveFixContext(fixContext);
                if (!draft) {
                  void handleRunDraft(sectionId, fixContext);
                } else {
                  if (sectionId) setEditorTargetSection(sectionId);
                  setActiveTab("draft");
                  setIpStep(3);
                  window.scrollTo({ top: 0, behavior: "smooth" });
                }
              }}
              initialSubView={auditSubView}
            />
          )}

          {/* LANGKAH 3: EDIT & MUAT TURUN FAIL IP WORD */}
          {ipStep === 3 && (
            <DraftDocxEditor
              draft={draft}
              onChangeDraft={(next) => {
                setDraft(next);
                setHasUnsavedChanges(true);
              }}
              hasCaseInput={hasCaseInput}
              activeCaseTitle={activeCaseTitle}
              draftLoading={draftLoading}
              auditLoading={auditLoading}
              hasUnsavedChanges={hasUnsavedChanges}
              savingCase={savingCase}
              initialSection={editorTargetSection}
              activeFixContext={activeFixContext}
              onDismissFixContext={() => setActiveFixContext(null)}
              auditIssueCounts={auditIssueCounts}
              missingKadKuasa={missingKadKuasa}
              onOpenProfile={() => {
                setAuthInitialTab("profile");
                setAuthOpen(true);
              }}
              onGenerateDraft={() => {
                void handleRunDraft();
              }}
              onReRunAudit={
                draft
                  ? () => {
                      const composed = composeCaseTextFromDraft(draft, caseText);
                      void handleRunAudit(composed, draft.akta_utama || aktaUtama);
                    }
                  : undefined
              }
              onStartBlankDraft={handleStartBlankDraft}
              onSaveDraft={handleSaveCurrentCase}
              onSwitchToInput={() => setIpStep(1)}
              onLoadSampleCase={() => {
                void handleLoadSampleCase();
              }}
              onDownloaded={(fname) =>
                showToast(`Fail ${fname} berjaya dimuat turun ke peranti anda.`)
              }
            />
          )}
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
        onSelectCase={(rec) => {
          const ok = applyCaseRecord(rec, officer);
          if (!ok) return;
          if (rec.draft) {
            setActiveTab("draft");
            setIpStep(3);
          } else if (rec.audit_report) {
            setActiveTab("audit");
            setIpStep(2);
          } else {
            setActiveTab("audit");
            setIpStep(1);
          }
          if (typeof window !== "undefined") {
            window.scrollTo({ top: 0, behavior: "smooth" });
          }
        }}
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
        <div className="mx-auto flex max-w-[1440px] items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src="/images/logo-pkdkn.png"
              alt="Logo PKD Kuala Nerus"
              className="h-6 w-auto object-contain"
            />
            <span>
              <strong>i-UIP Nerus</strong> • Unit Inspektorat &amp; Perundangan,{" "}
              <strong>PKD Kuala Nerus, Terengganu</strong>
            </span>
          </div>
          <div className="flex items-center gap-4">
            <button
              type="button"
              onClick={handleOpenOnboardingManual}
              className="font-semibold text-slate-600 hover:text-[#0f2744] hover:underline"
            >
              Pengenalan Ringkas
            </button>
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
        onOpenCases={() => {
          setRegistryInitialMode("list");
          setRegistryOpen(true);
        }}
        caseCount={cases.length}
        badges={mobileBadges}
      />
    </div>
  );
}
