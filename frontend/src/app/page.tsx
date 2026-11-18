"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  AlertCircle,
  ArrowLeft,
  CheckSquare,
  ExternalLink,
  FileCheck2,
  FileEdit,
  Lock,
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
import {
  extractEvidence,
  fetchCases,
  fetchCurrentOfficer,
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

function buildCompoundFromCase(rec: IPCaseRecord): NotisKompaunData {
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
    amaun_kompaun_rm: rec.akta_utama === "Akta 154" ? "RM 500.00" : "RM 500.00",
    tempoh_bayaran:
      rec.akta_utama === "Akta 852"
        ? "30 hari dari tarikh tawaran kompaun"
        : "14 hari dari tarikh serahan notis",
    pegawai_pengeluar: rec.pegawai_io || "",
    no_kad_kuasa: rec.no_kad_kuasa || "",
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
  const [errorBanner, setErrorBanner] = useState<string | null>(null);

  const [settingsOpen, setSettingsOpen] = useState(false);
  const [devConsoleOpen, setDevConsoleOpen] = useState(false);
  const [registryOpen, setRegistryOpen] = useState(false);
  const [authOpen, setAuthOpen] = useState(false);
  const [authInitialTab, setAuthInitialTab] = useState<"google" | "login" | "register" | "profile">("google");
  const [splashOpen, setSplashOpen] = useState(false);
  const [mobileSplitPane, setMobileSplitPane] = useState<"input" | "result">("input");
  const [authToken, setAuthToken] = useState<string | null>(null);
  const [officer, setOfficer] = useState<OfficerProfile | null>(null);

  const applyCaseRecord = useCallback((rec: IPCaseRecord) => {
    setActiveCaseId(rec.id);
    setAktaUtama(rec.akta_utama);
    setWorkflow(rec.workflow || "audit_ip");
    setCaseText(rec.case_text || "");
    setAuditReport(rec.audit_report || null);
    setDraft(rec.draft || null);
    setRedaction(null);
    setCompoundNotice(buildCompoundFromCase(rec));
    setErrorBanner(null);
  }, []);

  useEffect(() => {
    let mounted = true;
    if (typeof window !== "undefined" && !window.sessionStorage.getItem("iuip_nerus_splash_seen")) {
      setSplashOpen(true);
    }
    async function bootstrap() {
      try {
        const savedToken =
          typeof window !== "undefined" ? window.localStorage.getItem("uip_auth_token") : null;
        const [sysStatus, caseList] = await Promise.all([
          fetchSystemStatus(),
          fetchCases(),
        ]);
        if (!mounted) return;
        setStatus(sysStatus);
        setCases(caseList);
        if (caseList.length > 0) {
          applyCaseRecord(caseList[0]);
        }
        if (savedToken) {
          try {
            const me = await fetchCurrentOfficer(savedToken);
            if (mounted) {
              setAuthToken(savedToken);
              setOfficer(me);
            }
          } catch {
            window.localStorage.removeItem("uip_auth_token");
          }
        }
      } catch (err) {
        if (!mounted) return;
        setErrorBanner(
          err instanceof Error
            ? `Pelayan Backend FastAPI (localhost:8000) tidak dapat dicapai: ${err.message}`
            : "Gagal menyambung ke Backend API."
        );
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
  };

  const handleSaveCurrentCase = async () => {
    setSavingCase(true);
    setErrorBanner(null);
    try {
      const saved = await saveCaseRecord({
        id: activeCaseId || undefined,
        akta_utama: aktaUtama,
        workflow,
        case_text: caseText,
        status_kes: auditReport?.readiness_status || "DALAM SIASATAN",
        skor_audit: auditReport?.overall_score || 0,
        audit_report: auditReport,
        draft,
      });
      setActiveCaseId(saved.id);
      setCases((prev) => {
        const exists = prev.some((c) => c.id === saved.id);
        return exists
          ? prev.map((c) => (c.id === saved.id ? saved : c))
          : [saved, ...prev];
      });
    } catch (err) {
      setErrorBanner(err instanceof Error ? err.message : "Gagal menyimpan kes PKD.");
    } finally {
      setSavingCase(false);
    }
  };

  const handleRunAudit = async () => {
    if (!caseText.trim() && !uploadedFile) {
      setErrorBanner("Sila masukkan teks kes atau muat naik fail PDF/DOCX dahulu.");
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
    } catch (err) {
      setErrorBanner(err instanceof Error ? err.message : "Gagal menyemak IP.");
    } finally {
      setAuditLoading(false);
    }
  };

  const handleRunDraft = async () => {
    if (!caseText.trim()) {
      setErrorBanner("Sila masukkan catatan kes untuk menjana draf Borang 114 dan DS.");
      return;
    }
    setDraftLoading(true);
    setErrorBanner(null);
    try {
      const draftRes = await generateDrafts({
        caseText,
        aktaUtama,
        workflow,
        useOllama,
        fastMode: true,
        caseId: activeCaseId || undefined,
        authToken,
        officerProfile: officer,
      });
      setDraft(draftRes);
      if (draftRes.redaction_preview) {
        setRedaction({
          original_text: caseText,
          redacted_text: draftRes.redaction_preview.redacted_text || draftRes.redaction_preview.redacted_excerpt,
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
      if (workflow !== "notis_kompaun") {
        setActiveTab("draft");
      }
      setMobileSplitPane("result");
    } catch (err) {
      setErrorBanner(err instanceof Error ? err.message : "Gagal menjana draf dokumen.");
    } finally {
      setDraftLoading(false);
    }
  };

  const handleRunRedaction = async () => {
    if (!caseText.trim()) {
      setErrorBanner("Tiada teks untuk ditutup maklumat sulitnya.");
      return;
    }
    setRedactLoading(true);
    setErrorBanner(null);
    try {
      const res = await runRedaction(caseText, useOllama);
      setRedaction(res);
      setActiveTab("redaction");
    } catch (err) {
      setErrorBanner(err instanceof Error ? err.message : "Gagal menyamarkan data sulit.");
    } finally {
      setRedactLoading(false);
    }
  };

  const handleExtractEvidence = async (docHint: string) => {
    if (!uploadedFile) return;
    setExtractLoading(true);
    setErrorBanner(null);
    try {
      const res = await extractEvidence(uploadedFile, docHint);
      setExtractedEvidence(res);
      if (res.raw_text) {
        setCaseText((prev) =>
          prev.trim()
            ? `${prev.trim()}\n\n--- HASIL EKSTRAK FAIL (${res.filename}) ---\n${res.raw_text}`
            : res.raw_text
        );
      }
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
    setSplashOpen(false);
    if (typeof window !== "undefined") {
      window.sessionStorage.setItem("iuip_nerus_splash_seen", "1");
    }
  };

  const isFullWidthMode = activeTab === "advisor" || activeTab === "guide";

  return (
    <div className="flex min-h-screen flex-col bg-[#f4f7fb] pb-16 lg:pb-0">
      <TopNavbar
        status={status}
        activeMode={activeTab}
        onSelectMode={handleSelectMode}
        useOllama={useOllama}
        onToggleOllama={setUseOllama}
        caseCount={cases.length}
        onOpenCases={() => setRegistryOpen(true)}
        onOpenSettings={() => setSettingsOpen(true)}
        officer={officer}
        onOpenAccount={() => {
          setAuthInitialTab(officer ? "profile" : "google");
          setAuthOpen(true);
        }}
        onOpenSplash={() => setSplashOpen(true)}
        onOpenDevConsole={() => setDevConsoleOpen(true)}
      />

      {errorBanner && (
        <div className="mx-auto mt-3 w-full max-w-[1680px] px-4">
          <div className="flex items-center gap-2 rounded-lg border border-rose-300 bg-rose-50 px-3 py-2 text-xs font-medium text-rose-800">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{errorBanner}</span>
          </div>
        </div>
      )}

      {/* Reka Letak Adaptif: Lebar Penuh untuk Tanya Pakar & Panduan, Split-View untuk Kerja Kes IP */}
      {isFullWidthMode ? (
        <main className="mx-auto w-full max-w-[1480px] flex-1 p-4 space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 shadow-xs">
            <div className="text-xs text-slate-600">
              {activeTab === "advisor" ? (
                <span>
                  Mod Bebas <strong>Tanya Pakar UIP</strong> — jawapan tidak dipengaruhi teks kes IP sebelah kiri.
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
              className="inline-flex items-center gap-1.5 rounded-lg bg-slate-100 px-3 py-1.5 text-xs font-bold text-slate-800 hover:bg-slate-200"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              Kembali ke Workspace Kes IP ({cases.find((c) => c.id === activeCaseId)?.akta_utama || aktaUtama})
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
                handleSelectMode(bukaIp ? "draft" : "compound");
              }}
            />
          ) : (
            <AppGuidePanel />
          )}
        </main>
      ) : (
        <main className="mx-auto grid w-full max-w-[1680px] flex-1 grid-cols-1 gap-4 p-3 sm:p-4 lg:grid-cols-12">
          {/* Penukar Paparan Telefon Pintar (Mobile Web Split-View Toggle) */}
          <div className="grid grid-cols-2 gap-1.5 rounded-xl bg-white p-1.5 shadow-xs ring-1 ring-slate-200 lg:hidden">
            <button
              type="button"
              onClick={() => setMobileSplitPane("input")}
              className={`rounded-lg py-2 text-xs font-bold transition ${
                mobileSplitPane === "input"
                  ? "bg-[#0f2744] text-white"
                  : "text-slate-600 hover:bg-slate-100"
              }`}
            >
              1. Input &amp; Fail Kes
            </button>
            <button
              type="button"
              onClick={() => setMobileSplitPane("result")}
              className={`rounded-lg py-2 text-xs font-bold transition ${
                mobileSplitPane === "result"
                  ? "bg-[#0f2744] text-white"
                  : "text-slate-600 hover:bg-slate-100"
              }`}
            >
              2. Keputusan &amp; Editor
            </button>
          </div>

          <div className={`${mobileSplitPane === "input" ? "block" : "hidden"} lg:col-span-5 lg:block`}>
            <LeftEvidencePane
              cases={cases}
              activeCaseId={activeCaseId}
              onSelectCase={applyCaseRecord}
              onOpenNewCase={() => setRegistryOpen(true)}
              onSaveCurrentCase={handleSaveCurrentCase}
              savingCase={savingCase}
              aktaUtama={aktaUtama}
              onChangeAkta={setAktaUtama}
              caseText={caseText}
              onChangeCaseText={setCaseText}
              uploadedFile={uploadedFile}
              previewUrl={previewUrl}
              onFileSelected={handleFileSelected}
              onRunAudit={handleRunAudit}
              onRunDraft={handleRunDraft}
              onExtractEvidence={handleExtractEvidence}
              onSearchRag={handleSearchRag}
              ragResults={ragResults}
              ragLoading={ragLoading}
              auditLoading={auditLoading}
              draftLoading={draftLoading}
              extractLoading={extractLoading}
              extractedEvidence={extractedEvidence}
              folderChecklist={auditReport?.ip_folder_checklist}
            />
          </div>

          <div
            className={`${
              mobileSplitPane === "result" ? "flex" : "hidden"
            } flex-col rounded-xl border border-slate-200 bg-white p-4 shadow-sm lg:col-span-7 lg:flex`}
          >
            <div className="mb-4 flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 pb-3">
              <div className="flex flex-wrap gap-1.5">
                <button
                  type="button"
                  onClick={() => handleSelectMode("audit")}
                  className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-xs font-bold transition ${
                    activeTab === "audit"
                      ? "bg-[#0f2744] text-white shadow-sm"
                      : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                  }`}
                >
                  <CheckSquare className="h-4 w-4" />
                  Audit IP (20 Kriteria)
                  {auditReport && (
                    <span className="ml-1 rounded-full bg-white/20 px-1.5 py-0.5 text-[10px]">
                      {auditReport.overall_score}%
                    </span>
                  )}
                </button>

                <button
                  type="button"
                  onClick={() => handleSelectMode("compound")}
                  className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-xs font-bold transition ${
                    activeTab === "compound"
                      ? "bg-[#0f2744] text-white shadow-sm"
                      : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                  }`}
                >
                  <FileCheck2 className="h-4 w-4" />
                  Notis Kompaun
                </button>

                <button
                  type="button"
                  onClick={() => handleSelectMode("draft")}
                  className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-xs font-bold transition ${
                    activeTab === "draft"
                      ? "bg-[#0f2744] text-white shadow-sm"
                      : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                  }`}
                >
                  <FileEdit className="h-4 w-4" />
                  Editor IP &amp; .docx
                </button>

                <button
                  type="button"
                  onClick={() => handleSelectMode("redaction")}
                  className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-xs font-bold transition ${
                    activeTab === "redaction"
                      ? "bg-[#0f2744] text-white shadow-sm"
                      : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                  }`}
                >
                  <Lock className="h-4 w-4" />
                  Penyamaran OSA/PDPA
                  {redaction && (
                    <span className="ml-1 rounded-full bg-emerald-500/25 px-1.5 py-0.5 text-[10px]">
                      {redaction.entities.length}
                    </span>
                  )}
                </button>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto pr-1">
              {activeTab === "audit" && (
                <AuditPanel
                  report={auditReport}
                  onJumpToEditor={() => {
                    if (!draft) handleRunDraft();
                    else handleSelectMode("draft");
                  }}
                />
              )}
              {activeTab === "compound" && (
                <CompoundNoticePanel
                  notice={compoundNotice}
                  onChangeNotice={setCompoundNotice}
                  onClearNotice={() => setCompoundNotice(EMPTY_COMPOUND_NOTICE)}
                  onAutoFillFromCase={handleRunDraft}
                  autoFillLoading={draftLoading}
                />
              )}
              {activeTab === "draft" && (
                <DraftDocxEditor draft={draft} onChangeDraft={setDraft} />
              )}
              {activeTab === "redaction" && (
                <RedactionPreview
                  redaction={redaction}
                  loading={redactLoading}
                  onRunRedaction={handleRunRedaction}
                />
              )}
            </div>
          </div>
        </main>
      )}

      <SystemSettingsModal
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        status={status}
        onStatusUpdated={setStatus}
      />

      <CaseRegistryModal
        open={registryOpen}
        onClose={() => setRegistryOpen(false)}
        cases={cases}
        activeCaseId={activeCaseId}
        onSelectCase={applyCaseRecord}
        onCasesUpdated={setCases}
      />

      <AuthAccountModal
        open={authOpen}
        onClose={() => setAuthOpen(false)}
        officer={officer}
        authToken={authToken}
        initialTab={authInitialTab}
        onAuthenticated={(user, token) => {
          setOfficer(user);
          setAuthToken(token);
          window.localStorage.setItem("uip_auth_token", token);
        }}
        onProfileUpdated={(updated) => setOfficer(updated)}
        onLoggedOut={() => {
          setOfficer(null);
          setAuthToken(null);
          window.localStorage.removeItem("uip_auth_token");
        }}
      />

      <DevConsoleModal
        open={devConsoleOpen}
        onClose={() => setDevConsoleOpen(false)}
      />

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

      <footer className="mt-auto border-t border-slate-200 bg-white/90 px-4 py-2.5 text-center text-[11px] text-slate-600">
        <div className="mx-auto flex max-w-[1680px] flex-wrap items-center justify-between gap-2">
          <span>
            <strong>i-UIP Nerus</strong> • Unit Inspektorat dan Perundangan (UIP),{" "}
            <strong>Pejabat Kesihatan Daerah Kuala Nerus, Terengganu</strong>
          </span>
          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={() => setDevConsoleOpen(true)}
              className="font-bold text-indigo-700 hover:underline"
            >
              Konsol Pembangun (Siapa Guna &amp; Kos)
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

      <MobileBottomNav activeMode={activeTab} onSelectMode={handleSelectMode} />
    </div>
  );
}
