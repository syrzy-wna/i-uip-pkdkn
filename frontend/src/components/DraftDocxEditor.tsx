"use client";

import React, { useEffect, useRef, useState } from "react";
import {
  AlertCircle,
  ArrowRight,
  BookCheck,
  CheckCircle2,
  ChevronDown,
  Download,
  FileCheck2,
  FileEdit,
  FileText,
  FolderOpen,
  Loader2,
  Pencil,
  Plus,
  RefreshCw,
  Save,
  Sparkles,
  Trash2,
  UserCheck,
  X,
} from "lucide-react";
import { downloadDocx } from "@/lib/api";
import type { AuditFixContext } from "@/components/AuditPanel";
import type { DraftGenerationResponse, MinitEntry } from "@/lib/types";

export type EditorGroupTab = "pertuduhan" | "fakta_minit" | "saksi_eksibit" | "rakaman_diari";

interface DraftDocxEditorProps {
  draft: DraftGenerationResponse | null;
  onChangeDraft: (updated: DraftGenerationResponse) => void;
  hasCaseInput: boolean;
  activeCaseTitle?: string;
  draftLoading: boolean;
  auditLoading?: boolean;
  hasUnsavedChanges?: boolean;
  savingCase?: boolean;
  initialSection?: string | null;
  onTargetSectionConsumed?: () => void;
  activeFixContext?: AuditFixContext | null;
  onDismissFixContext?: () => void;
  auditIssueCounts?: Partial<Record<EditorGroupTab, number>>;
  missingKadKuasa?: boolean;
  onOpenProfile?: () => void;
  onGenerateDraft: () => void;
  onReRunAudit?: () => void;
  onStartBlankDraft: () => void;
  onSaveDraft: () => void;
  onSwitchToInput: () => void;
  onLoadSampleCase: () => void;
  onDownloaded?: (filename: string) => void;
}

const GROUP_TABS: Array<{ id: EditorGroupTab; label: string }> = [
  { id: "pertuduhan", label: "1. Pertuduhan & Saman" },
  { id: "fakta_minit", label: "2. Minit, Fakta & Kronologi" },
  { id: "saksi_eksibit", label: "3. Saksi, Eksibit & S.90A" },
  { id: "rakaman_diari", label: "4. Rakaman S.112 & Diari" },
];

export function mapSectionToGroup(secId?: string | null): EditorGroupTab {
  if (!secId) return "pertuduhan";
  if (secId === "borang114" || secId === "saman111") return "pertuduhan";
  if (secId === "minit" || secId === "fakta" || secId === "kronologi" || secId === "cadangan") {
    return "fakta_minit";
  }
  if (secId === "saksi" || secId === "eksibit" || secId === "sijil90a") {
    return "saksi_eksibit";
  }
  return "rakaman_diari";
}

const INPUT_CLASS =
  "mt-1 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-base text-slate-900 transition hover:border-slate-400 focus:border-[#0f2744] focus:outline-none focus:ring-2 focus:ring-slate-200 sm:text-sm";

const TEXTAREA_CLASS =
  "mt-1 w-full rounded-xl border border-slate-300 bg-white p-3 text-base leading-relaxed text-slate-900 transition hover:border-slate-400 focus:border-[#0f2744] focus:outline-none focus:ring-2 focus:ring-slate-200 sm:text-sm";

const DOC_BADGES = [
  "Kulit & Indeks A–G",
  "Minit 1–4",
  "Borang 114 (Pertuduhan)",
  "Borang 143 (Pengaduan)",
  "Saman 111",
  "Fakta Kes",
  "Sijil S.90A",
  "Senarai Saksi & Eksibit",
  "Rakaman S.112",
  "Diari Siasatan S.119",
];

export default function DraftDocxEditor({
  draft,
  onChangeDraft,
  hasCaseInput,
  activeCaseTitle,
  draftLoading,
  auditLoading = false,
  hasUnsavedChanges = false,
  savingCase = false,
  initialSection = null,
  onTargetSectionConsumed,
  activeFixContext = null,
  onDismissFixContext,
  auditIssueCounts,
  missingKadKuasa = false,
  onOpenProfile,
  onGenerateDraft,
  onReRunAudit,
  onStartBlankDraft,
  onSaveDraft,
  onSwitchToInput,
  onLoadSampleCase,
  onDownloaded,
}: DraftDocxEditorProps) {
  const [activeGroup, setActiveGroup] = useState<EditorGroupTab>("pertuduhan");
  const [exporting, setExporting] = useState<string | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);
  const [downloadOkMsg, setDownloadOkMsg] = useState<string | null>(null);
  const [showMoreExports, setShowMoreExports] = useState(false);
  const [expandedCitations, setExpandedCitations] = useState<Record<number, boolean>>({});
  const sectionRefs = useRef<Record<string, HTMLDivElement | null>>({});
  const exportMenuRef = useRef<HTMLDivElement | null>(null);
  const hasDraft = Boolean(draft);

  // Lompat ke bahagian sasaran sekali sahaja apabila initialSection ditetapkan (elak ditendang balik setiap huruf ditaip)
  useEffect(() => {
    if (!initialSection || !hasDraft) return;
    setActiveGroup(mapSectionToGroup(initialSection));
    const targetKey = initialSection;
    const timer = window.setTimeout(() => {
      sectionRefs.current[targetKey]?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    }, 90);
    onTargetSectionConsumed?.();
    return () => window.clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialSection, hasDraft]);

  // Tutup menu Muat Turun Berasingan bila klik di luar atau tekan Escape
  useEffect(() => {
    if (!showMoreExports) return;
    const onMouseDown = (e: MouseEvent) => {
      if (exportMenuRef.current && !exportMenuRef.current.contains(e.target as Node)) {
        setShowMoreExports(false);
      }
    };
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setShowMoreExports(false);
    };
    document.addEventListener("mousedown", onMouseDown);
    window.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onMouseDown);
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [showMoreExports]);

  if (!draft) {
    return (
      <div className="mx-auto max-w-3xl space-y-5 rounded-2xl border border-dashed border-slate-300 bg-white p-6 text-center sm:p-8">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-100 text-[#0f2744]">
          <FileEdit className="h-6 w-6" />
        </div>
        <div className="space-y-1.5">
          <h3 className="text-base font-extrabold text-slate-900">
            Sedia &amp; Sunting Fail Kertas Siasatan Lengkap (Word)
          </h3>
          <p className="mx-auto max-w-lg text-sm leading-relaxed text-slate-600">
            Daripada satu catatan kes, sistem menyediakan semua dokumen rasmi di bawah untuk anda semak dan muat turun dalam format Microsoft Word:
          </p>
        </div>

        <div className="flex flex-wrap justify-center gap-1.5">
          {DOC_BADGES.map((label) => (
            <span
              key={label}
              className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-semibold text-slate-700"
            >
              {label}
            </span>
          ))}
        </div>

        {activeCaseTitle && hasCaseInput && (
          <div className="mx-auto max-w-xl rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-xs text-slate-800">
            Bahan kes sedia: <strong>{activeCaseTitle}</strong>
          </div>
        )}

        <div className="flex flex-col items-center justify-center gap-2.5 sm:flex-row sm:flex-wrap">
          {hasCaseInput ? (
            <button
              type="button"
              disabled={draftLoading}
              onClick={onGenerateDraft}
              className="inline-flex min-h-[46px] w-full items-center justify-center gap-2 rounded-xl bg-[#0f2744] px-6 py-2.5 text-sm font-extrabold text-white shadow-sm hover:bg-slate-800 disabled:opacity-60 sm:w-auto"
            >
              {draftLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
              {draftLoading ? "Sedang menyediakan draf..." : "Bina Draf Fail IP Sekarang"}
            </button>
          ) : (
            <button
              type="button"
              onClick={onSwitchToInput}
              className="inline-flex min-h-[46px] w-full items-center justify-center gap-2 rounded-xl bg-[#0f2744] px-6 py-2.5 text-sm font-extrabold text-white shadow-sm hover:bg-slate-800 sm:w-auto"
            >
              <FolderOpen className="h-4 w-4" />
              Masukkan Bahan Kes Dahulu
            </button>
          )}

          <button
            type="button"
            onClick={onStartBlankDraft}
            className="inline-flex min-h-[44px] w-full items-center justify-center gap-1.5 rounded-xl border border-slate-300 bg-white px-4 py-2 text-xs font-bold text-slate-800 hover:bg-slate-50 sm:w-auto"
          >
            <Pencil className="h-3.5 w-3.5" />
            Isi Borang Kosong
          </button>

          {!hasCaseInput && (
            <button
              type="button"
              onClick={onLoadSampleCase}
              className="inline-flex min-h-[44px] w-full items-center justify-center gap-1.5 rounded-xl border border-slate-300 bg-white px-4 py-2 text-xs font-bold text-[#0f2744] hover:bg-slate-50 sm:w-auto"
            >
              <FileText className="h-3.5 w-3.5" />
              Cuba Contoh Kes Sebenar
            </button>
          )}
        </div>
      </div>
    );
  }

  const handleExport = async (
    docType:
      | "borang_114"
      | "saman_111"
      | "diari_siasatan"
      | "rakaman_112"
      | "pakej_ip"
  ) => {
    setExporting(docType);
    setExportError(null);
    setDownloadOkMsg(null);
    setShowMoreExports(false);
    try {
      const fname = await downloadDocx(docType, draft as unknown as Record<string, unknown>);
      setDownloadOkMsg(
        `Fail ${fname} berjaya dimuat turun — sila semak ruang Muat Turun pada peranti anda.`
      );
      if (onDownloaded) onDownloaded(fname);
    } catch (err) {
      setExportError(err instanceof Error ? err.message : "Gagal memuat turun fail Word.");
    } finally {
      setExporting(null);
    }
  };

  const updateBorang114 = (
    field: keyof DraftGenerationResponse["borang_114"],
    value: string
  ) => {
    onChangeDraft({
      ...draft,
      borang_114: {
        ...draft.borang_114,
        [field]: value,
      },
    });
  };

  const minitList: MinitEntry[] = Array.isArray(draft.minit_ip)
    ? draft.minit_ip
    : [
        {
          bil: "Minit 1",
          tarikh: "-",
          daripada: "IO",
          kepada: "UIP / TPR",
          kandungan: String(draft.minit_ip || ""),
        },
      ];

  const addDiariRow = () => {
    const nextBil = String(draft.diari_siasatan.length + 1);
    onChangeDraft({
      ...draft,
      diari_siasatan: [
        ...draft.diari_siasatan,
        {
          bil: nextBil,
          tarikh: "",
          masa: "",
          butiran_tindakan: "Catatan tindakan susulan IO...",
          pegawai: draft.sijil_90a.nama_pegawai || "PPKP / IO",
        },
      ],
    });
  };

  const addSaksiRow = () => {
    const nextBil = `SP${draft.senarai_saksi.length + 1}`;
    onChangeDraft({
      ...draft,
      senarai_saksi: [
        ...draft.senarai_saksi,
        {
          bil: nextBil,
          nama: "",
          no_kp: "",
          jawatan_peranan: "Saksi Pendakwaan",
          alamat_hubungan: "",
        },
      ],
    });
  };

  const addEksibitRow = () => {
    const nextTanda = `P${draft.senarai_eksibit.length + 1}`;
    onChangeDraft({
      ...draft,
      senarai_eksibit: [
        ...draft.senarai_eksibit,
        {
          tanda: nextTanda,
          perihal: "",
          no_lak_seal: "-",
          lokasi_simpanan: "Stor Eksibit Pejabat Kesihatan",
        },
      ],
    });
  };

  const nextTabMap: Record<EditorGroupTab, { next: EditorGroupTab; label: string } | null> = {
    pertuduhan: { next: "fakta_minit", label: "Seterusnya: Minit, Fakta & Kronologi" },
    fakta_minit: { next: "saksi_eksibit", label: "Seterusnya: Saksi, Eksibit & S.90A" },
    saksi_eksibit: { next: "rakaman_diari", label: "Seterusnya: Rakaman S.112 & Diari" },
    rakaman_diari: null,
  };

  return (
    <div className="mx-auto max-w-4xl space-y-4">
      {/* Tip Kontekstual Profil */}
      {missingKadKuasa && onOpenProfile && (
        <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-amber-200 bg-amber-50 px-4 py-2.5 text-xs text-amber-950">
          <div className="flex items-center gap-2">
            <UserCheck className="h-4 w-4 shrink-0 text-amber-700" />
            <span>
              Simpan <strong>No. Kad Kuasa &amp; model komputer pejabat</strong> dalam profil supaya Sijil 90A &amp; Borang 114 diisi secara automatik.
            </span>
          </div>
          <button
            type="button"
            onClick={onOpenProfile}
            className="font-bold text-[#0f2744] hover:underline"
          >
            Lengkapkan Profil →
          </button>
        </div>
      )}

      {/* Banner Peringatan Melekat Jika Lompat Dari Kuiri Semakan Pra-TPR */}
      {activeFixContext && (
        <div className="flex flex-wrap items-start justify-between gap-3 rounded-2xl border border-amber-300 bg-amber-50 p-4 text-xs text-amber-950 shadow-sm">
          <div className="space-y-1">
            <div className="font-extrabold text-amber-950">
              Sedang Membaiki Perkara Pra-TPR: {activeFixContext.title}
            </div>
            <p className="leading-relaxed text-amber-900">
              <strong>Tindakan:</strong> {activeFixContext.recommendation}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {onReRunAudit && (
              <button
                type="button"
                disabled={auditLoading}
                onClick={onReRunAudit}
                className="inline-flex min-h-[38px] items-center gap-1.5 rounded-xl bg-[#0f2744] px-3.5 py-1.5 text-xs font-bold text-white hover:bg-slate-800 disabled:opacity-60"
              >
                {auditLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
                Semak Semula Skor
              </button>
            )}
            {onDismissFixContext && (
              <button
                type="button"
                onClick={onDismissFixContext}
                aria-label="Tutup nota baiki"
                className="inline-flex min-h-[38px] min-w-[38px] items-center justify-center rounded-lg text-amber-800 hover:bg-amber-100"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>
        </div>
      )}

      {/* 1. BAR TINDAKAN TUNGGAL EDITOR */}
      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div className="space-y-0.5">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="text-base font-extrabold text-slate-900">
                Langkah 3: Sunting Draf &amp; Muat Turun Word ({draft.akta_utama})
              </h3>
              {hasUnsavedChanges ? (
                <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-bold text-amber-900">
                  <AlertCircle className="h-3.5 w-3.5" /> Belum Disimpan
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-bold text-emerald-800">
                  <CheckCircle2 className="h-3.5 w-3.5" /> Disimpan
                </span>
              )}
            </div>
            <p className="text-xs text-slate-600">
              Ubah mana-mana ruangan di bawah, semak semula skor Pra-TPR jika perlu, atau terus muat turun fail Word.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              disabled={savingCase}
              onClick={onSaveDraft}
              className={`inline-flex min-h-[44px] items-center gap-1.5 rounded-xl border px-3.5 py-2 text-xs font-bold transition disabled:opacity-60 ${
                hasUnsavedChanges
                  ? "border-amber-400 bg-amber-50 text-amber-950 hover:bg-amber-100"
                  : "border-slate-300 bg-white text-slate-700 hover:bg-slate-50"
              }`}
            >
              {savingCase ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
              {hasUnsavedChanges ? "Simpan Perubahan" : "Simpan Kes"}
            </button>

            {onReRunAudit && (
              <button
                type="button"
                disabled={auditLoading}
                onClick={onReRunAudit}
                className="inline-flex min-h-[44px] items-center gap-1.5 rounded-xl border border-slate-300 bg-white px-3.5 py-2 text-xs font-bold text-[#0f2744] hover:bg-slate-50 disabled:opacity-60"
              >
                {auditLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
                Semak Semula Skor
              </button>
            )}

            <button
              type="button"
              disabled={exporting !== null}
              onClick={() => handleExport("pakej_ip")}
              className="inline-flex min-h-[44px] items-center gap-2 rounded-xl bg-[#0f2744] px-4 py-2 text-xs font-extrabold text-white shadow-sm hover:bg-slate-800 disabled:opacity-60"
            >
              {exporting === "pakej_ip" ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <FileCheck2 className="h-4 w-4" />
              )}
              Muat Turun Pakej IP (.docx)
            </button>

            <div ref={exportMenuRef} className="relative">
              <button
                type="button"
                aria-expanded={showMoreExports}
                onClick={() => setShowMoreExports((v) => !v)}
                className="inline-flex min-h-[44px] items-center gap-1 rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs font-bold text-slate-700 hover:bg-slate-50"
              >
                <Download className="h-3.5 w-3.5 text-[#0f2744]" />
                Muat Turun Berasingan
                <ChevronDown className="h-3.5 w-3.5" />
              </button>

              {showMoreExports && (
                <div className="absolute left-0 z-30 mt-1.5 w-56 max-w-[calc(100vw-2rem)] rounded-xl border border-slate-200 bg-white p-1.5 shadow-lg sm:left-auto sm:right-0">
                  {[
                    { type: "borang_114" as const, label: "Borang 114 Sahaja" },
                    { type: "saman_111" as const, label: "Saman 111 Sahaja" },
                    { type: "diari_siasatan" as const, label: "Diari Siasatan Sahaja" },
                    { type: "rakaman_112" as const, label: "Rakaman S.112 Sahaja" },
                  ].map((item) => (
                    <button
                      key={item.type}
                      type="button"
                      disabled={exporting !== null}
                      onClick={() => handleExport(item.type)}
                      className="flex min-h-[44px] w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-xs font-semibold text-slate-700 hover:bg-slate-100 hover:text-slate-900"
                    >
                      <Download className="h-3.5 w-3.5 text-[#0f2744]" />
                      {item.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {exportError && (
          <p className="mt-2.5 text-xs font-semibold text-rose-700">{exportError}</p>
        )}
        {downloadOkMsg && (
          <div className="mt-3 flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-3.5 py-2.5 text-xs font-bold text-emerald-900">
            <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600" />
            <span>{downloadOkMsg}</span>
          </div>
        )}
      </div>

      {/* 2. NAVIGASI 4 KUMPULAN DOKUMEN DENGAN LENCANA BILANGAN ISU */}
      <div className="flex gap-1.5 overflow-x-auto pb-1 no-scrollbar">
        {GROUP_TABS.map((tab) => {
          const issues = auditIssueCounts?.[tab.id] || 0;
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveGroup(tab.id)}
              className={`inline-flex min-h-[42px] shrink-0 items-center gap-1.5 rounded-xl px-3.5 py-2 text-xs font-extrabold transition ${
                activeGroup === tab.id
                  ? "bg-[#0f2744] text-white shadow-sm"
                  : "border border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
              }`}
            >
              <span>{tab.label}</span>
              {issues > 0 && (
                <span
                  className={`rounded-full px-1.5 py-0.5 text-[11px] font-extrabold ${
                    activeGroup === tab.id
                      ? "bg-amber-300 text-slate-950"
                      : "bg-rose-100 text-rose-800"
                  }`}
                >
                  {issues}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* KUMPULAN 1: BORANG 114 & SAMAN 111 */}
      {activeGroup === "pertuduhan" && (
        <div className="space-y-4">
          <div
            ref={(el) => {
              sectionRefs.current.borang114 = el;
            }}
            className="scroll-mt-20 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm space-y-3 sm:p-5"
          >
            <div className="flex items-center justify-between border-b border-slate-200 pb-2.5">
              <h4 className="text-sm font-extrabold text-slate-900">
                Kertas Pertuduhan Rasmi (Borang Mahkamah 114)
              </h4>
              <span className="rounded-md bg-blue-50 px-2.5 py-0.5 text-[11px] font-bold text-blue-800">
                {draft.akta_utama}
              </span>
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div>
                <label className="text-xs font-semibold text-slate-700">
                  Nama OKS / Tertuduh <span className="text-rose-600">*</span>
                </label>
                <input
                  type="text"
                  value={draft.borang_114.nama_tertuduh}
                  onChange={(e) => updateBorang114("nama_tertuduh", e.target.value)}
                  className={INPUT_CLASS}
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-700">
                  No. Kad Pengenalan <span className="text-rose-600">*</span>
                </label>
                <input
                  type="text"
                  value={draft.borang_114.no_kp_tertuduh}
                  onChange={(e) => updateBorang114("no_kp_tertuduh", e.target.value)}
                  className={INPUT_CLASS}
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-700">
                  Tarikh Kejadian <span className="text-rose-600">*</span>
                </label>
                <input
                  type="text"
                  value={draft.borang_114.tarikh_kejadian}
                  onChange={(e) => updateBorang114("tarikh_kejadian", e.target.value)}
                  className={INPUT_CLASS}
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-700">
                  Masa Kejadian <span className="text-rose-600">*</span>
                </label>
                <input
                  type="text"
                  value={draft.borang_114.masa_kejadian}
                  onChange={(e) => updateBorang114("masa_kejadian", e.target.value)}
                  className={INPUT_CLASS}
                />
              </div>
              <div className="sm:col-span-2">
                <label className="text-xs font-semibold text-slate-700">
                  Tempat Kejadian <span className="text-rose-600">*</span>
                </label>
                <input
                  type="text"
                  value={draft.borang_114.tempat_kejadian}
                  onChange={(e) => updateBorang114("tempat_kejadian", e.target.value)}
                  className={INPUT_CLASS}
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-700">
                  Seksyen Kesalahan <span className="text-rose-600">*</span>
                </label>
                <input
                  type="text"
                  value={draft.borang_114.akta_dan_seksyen}
                  onChange={(e) => updateBorang114("akta_dan_seksyen", e.target.value)}
                  className={INPUT_CLASS}
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-700">
                  Seksyen Hukuman <span className="text-rose-600">*</span>
                </label>
                <input
                  type="text"
                  value={draft.borang_114.seksyen_hukuman}
                  onChange={(e) => updateBorang114("seksyen_hukuman", e.target.value)}
                  className={INPUT_CLASS}
                />
              </div>
              <div className="sm:col-span-2">
                <label className="text-xs font-semibold text-slate-700">
                  Hukuman Maksimum Mengikut Akta
                </label>
                <input
                  type="text"
                  value={draft.borang_114.hukuman_maksimum || ""}
                  onChange={(e) => updateBorang114("hukuman_maksimum", e.target.value)}
                  className={INPUT_CLASS}
                />
              </div>
              <div className="sm:col-span-2">
                <label className="text-xs font-semibold text-slate-700">
                  Teks Pertuduhan Rasmi Borang 114 <span className="text-rose-600">*</span>
                </label>
                <textarea
                  rows={4}
                  value={draft.borang_114.teks_pertuduhan}
                  onChange={(e) => updateBorang114("teks_pertuduhan", e.target.value)}
                  className={TEXTAREA_CLASS}
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-700">Mahkamah Majistret</label>
                <input
                  type="text"
                  value={draft.borang_114.mahkamah}
                  onChange={(e) => updateBorang114("mahkamah", e.target.value)}
                  className={INPUT_CLASS}
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-700">No. Kes / No. IP</label>
                <input
                  type="text"
                  value={draft.borang_114.no_kes}
                  onChange={(e) => updateBorang114("no_kes", e.target.value)}
                  className={INPUT_CLASS}
                />
              </div>
              <div className="sm:col-span-2">
                <label className="text-xs font-semibold text-slate-700">Alamat OKS</label>
                <input
                  type="text"
                  value={draft.borang_114.alamat_tertuduh}
                  onChange={(e) => updateBorang114("alamat_tertuduh", e.target.value)}
                  className={INPUT_CLASS}
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-700">
                  Umur / Jantina <span className="font-normal text-slate-400">(Pilihan)</span>
                </label>
                <input
                  type="text"
                  value={draft.borang_114.umur_jantina || ""}
                  onChange={(e) => updateBorang114("umur_jantina", e.target.value)}
                  className={INPUT_CLASS}
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-700">
                  Pekerjaan / Jawatan <span className="font-normal text-slate-400">(Pilihan)</span>
                </label>
                <input
                  type="text"
                  value={draft.borang_114.pekerjaan || ""}
                  onChange={(e) => updateBorang114("pekerjaan", e.target.value)}
                  className={INPUT_CLASS}
                />
              </div>
            </div>
          </div>

          <div
            ref={(el) => {
              sectionRefs.current.saman111 = el;
            }}
            className="scroll-mt-20 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm space-y-3 sm:p-5"
          >
            <h4 className="border-b border-slate-200 pb-2 text-sm font-extrabold text-slate-900">
              Saman (Mahkamah 111) &amp; Hujahan Pemberatan Hukuman
            </h4>

            {draft.saman_111 && (
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                <div>
                  <label className="text-xs font-semibold text-slate-700">Mahkamah Majistret</label>
                  <input
                    type="text"
                    value={draft.saman_111.mahkamah || ""}
                    onChange={(e) =>
                      onChangeDraft({
                        ...draft,
                        saman_111: { ...draft.saman_111, mahkamah: e.target.value },
                      })
                    }
                    className={INPUT_CLASS}
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-700">Tarikh Hadir Mahkamah</label>
                  <input
                    type="text"
                    value={draft.saman_111.tarikh_hadir || ""}
                    onChange={(e) =>
                      onChangeDraft({
                        ...draft,
                        saman_111: { ...draft.saman_111, tarikh_hadir: e.target.value },
                      })
                    }
                    className={INPUT_CLASS}
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-700">Masa Hadir</label>
                  <input
                    type="text"
                    value={draft.saman_111.masa_hadir || ""}
                    onChange={(e) =>
                      onChangeDraft({
                        ...draft,
                        saman_111: { ...draft.saman_111, masa_hadir: e.target.value },
                      })
                    }
                    className={INPUT_CLASS}
                  />
                </div>
              </div>
            )}

            <div className="space-y-2 pt-1">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="text-xs font-bold text-slate-700">
                  Perkara Pemberatan Hukuman (Jika OKT Mengaku Salah / Sabit)
                </span>
                <button
                  type="button"
                  onClick={() =>
                    onChangeDraft({
                      ...draft,
                      pemberatan_hukuman: [
                        ...(draft.pemberatan_hukuman || []),
                        "Faktor pemberatan tambahan kepentingan kesihatan awam...",
                      ],
                    })
                  }
                  className="inline-flex min-h-[36px] items-center gap-1 rounded-lg bg-blue-50 px-3 py-1.5 text-xs font-bold text-blue-800 hover:bg-blue-100"
                >
                  <Plus className="h-3.5 w-3.5" /> Tambah Perkara
                </button>
              </div>
              <div className="space-y-2">
                {(draft.pemberatan_hukuman || []).map((pt, idx) => (
                  <div key={idx} className="flex items-center gap-2">
                    <span className="w-5 text-center text-xs font-bold text-slate-500">
                      {idx + 1}.
                    </span>
                    <input
                      type="text"
                      value={pt}
                      onChange={(e) => {
                        const next = [...(draft.pemberatan_hukuman || [])];
                        next[idx] = e.target.value;
                        onChangeDraft({ ...draft, pemberatan_hukuman: next });
                      }}
                      className={INPUT_CLASS}
                    />
                    <button
                      type="button"
                      onClick={() =>
                        onChangeDraft({
                          ...draft,
                          pemberatan_hukuman: (draft.pemberatan_hukuman || []).filter((_, i) => i !== idx),
                        })
                      }
                      className="inline-flex min-h-[38px] min-w-[38px] items-center justify-center rounded-lg bg-rose-50 text-rose-600 hover:bg-rose-100"
                      title="Padam perkara"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* KUMPULAN 2: MINIT, FAKTA KES, KRONOLOGI & CADANGAN IO */}
      {activeGroup === "fakta_minit" && (
        <div className="space-y-4">
          <div
            ref={(el) => {
              sectionRefs.current.fakta = el;
            }}
            className="scroll-mt-20 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm space-y-2 sm:p-5"
          >
            <h4 className="text-sm font-extrabold text-slate-900">Fakta Kes Ringkas</h4>
            <textarea
              rows={7}
              value={draft.fakta_kes}
              onChange={(e) => onChangeDraft({ ...draft, fakta_kes: e.target.value })}
              className={TEXTAREA_CLASS}
            />
          </div>

          <div
            ref={(el) => {
              sectionRefs.current.minit = el;
            }}
            className="scroll-mt-20 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm space-y-3 sm:p-5"
          >
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 pb-2">
              <h4 className="text-sm font-extrabold text-slate-900">
                Kertas Minit Siasatan ({minitList.length} Minit)
              </h4>
              <button
                type="button"
                onClick={() => {
                  const nextBil = String(minitList.length + 1);
                  const nextEntry: MinitEntry = {
                    bil: nextBil,
                    daripada: "Pegawai Penyiasat (IO)",
                    kepada: "Ketua Unit UIP / TPR",
                    tarikh: "",
                    kandungan: "",
                  };
                  onChangeDraft({ ...draft, minit_ip: [...minitList, nextEntry] });
                }}
                className="inline-flex min-h-[40px] items-center gap-1 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-bold text-[#0f2744] hover:bg-slate-50"
              >
                <Plus className="h-3.5 w-3.5" /> Tambah Minit
              </button>
            </div>
            <div className="divide-y divide-slate-200">
              {minitList.map((m, idx) => (
                <div key={idx} className="space-y-2.5 py-3 first:pt-1 last:pb-0">
                  <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-4">
                    <div>
                      <label className="text-xs font-semibold text-slate-600">Bil. Minit</label>
                      <input
                        type="text"
                        value={m.bil}
                        onChange={(e) => {
                          const next = [...minitList];
                          next[idx] = { ...next[idx], bil: e.target.value };
                          onChangeDraft({ ...draft, minit_ip: next });
                        }}
                        className={INPUT_CLASS}
                      />
                    </div>
                    <div>
                      <label className="text-xs font-semibold text-slate-600">Daripada</label>
                      <input
                        type="text"
                        value={m.daripada}
                        onChange={(e) => {
                          const next = [...minitList];
                          next[idx] = { ...next[idx], daripada: e.target.value };
                          onChangeDraft({ ...draft, minit_ip: next });
                        }}
                        className={INPUT_CLASS}
                      />
                    </div>
                    <div>
                      <label className="text-xs font-semibold text-slate-600">Kepada</label>
                      <input
                        type="text"
                        value={m.kepada}
                        onChange={(e) => {
                          const next = [...minitList];
                          next[idx] = { ...next[idx], kepada: e.target.value };
                          onChangeDraft({ ...draft, minit_ip: next });
                        }}
                        className={INPUT_CLASS}
                      />
                    </div>
                    <div>
                      <label className="text-xs font-semibold text-slate-600">Tarikh</label>
                      <input
                        type="text"
                        value={m.tarikh}
                        onChange={(e) => {
                          const next = [...minitList];
                          next[idx] = { ...next[idx], tarikh: e.target.value };
                          onChangeDraft({ ...draft, minit_ip: next });
                        }}
                        className={INPUT_CLASS}
                      />
                    </div>
                  </div>
                  <div>
                    <label className="text-xs font-semibold text-slate-600">Kandungan Minit</label>
                    <textarea
                      rows={2}
                      value={m.kandungan}
                      onChange={(e) => {
                        const next = [...minitList];
                        next[idx] = { ...next[idx], kandungan: e.target.value };
                        onChangeDraft({ ...draft, minit_ip: next });
                      }}
                      className={TEXTAREA_CLASS}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div
            ref={(el) => {
              sectionRefs.current.kronologi = el;
            }}
            className="scroll-mt-20 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm space-y-3 sm:p-5"
          >
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 pb-2">
              <h4 className="text-sm font-extrabold text-slate-900">
                Kronologi Kes ({(draft.kronologi_kes || []).length} Peristiwa)
              </h4>
              <button
                type="button"
                onClick={() => {
                  const current = draft.kronologi_kes || [];
                  onChangeDraft({
                    ...draft,
                    kronologi_kes: [
                      ...current,
                      { tarikh: "", peristiwa: "Catatan peristiwa atau tindakan susulan..." },
                    ],
                  });
                }}
                className="inline-flex min-h-[36px] items-center gap-1 rounded-lg bg-blue-50 px-3 py-1.5 text-xs font-bold text-blue-800 hover:bg-blue-100"
              >
                <Plus className="h-3.5 w-3.5" /> Tambah Kronologi
              </button>
            </div>
            <div className="space-y-2.5">
              {(draft.kronologi_kes || []).map((item, idx) => (
                <div key={idx} className="grid grid-cols-1 gap-2 sm:grid-cols-12">
                  <div className="sm:col-span-3">
                    <label className="text-xs font-semibold text-slate-600">Tarikh / Waktu</label>
                    <input
                      type="text"
                      placeholder="18 Nov 2026"
                      value={item.tarikh}
                      onChange={(e) => {
                        const next = [...(draft.kronologi_kes || [])];
                        next[idx] = { ...next[idx], tarikh: e.target.value };
                        onChangeDraft({ ...draft, kronologi_kes: next });
                      }}
                      className={`${INPUT_CLASS} font-semibold`}
                    />
                  </div>
                  <div className="sm:col-span-8">
                    <label className="text-xs font-semibold text-slate-600">Peristiwa / Tindakan</label>
                    <input
                      type="text"
                      placeholder="Peristiwa..."
                      value={item.peristiwa}
                      onChange={(e) => {
                        const next = [...(draft.kronologi_kes || [])];
                        next[idx] = { ...next[idx], peristiwa: e.target.value };
                        onChangeDraft({ ...draft, kronologi_kes: next });
                      }}
                      className={INPUT_CLASS}
                    />
                  </div>
                  <div className="flex items-end justify-end sm:col-span-1">
                    <button
                      type="button"
                      onClick={() =>
                        onChangeDraft({
                          ...draft,
                          kronologi_kes: (draft.kronologi_kes || []).filter((_, i) => i !== idx),
                        })
                      }
                      className="inline-flex min-h-[38px] min-w-[38px] items-center justify-center rounded-lg bg-rose-50 text-rose-600 hover:bg-rose-100"
                      title="Padam baris"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div
            ref={(el) => {
              sectionRefs.current.cadangan = el;
            }}
            className="scroll-mt-20 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm space-y-2 sm:p-5"
          >
            <h4 className="text-sm font-extrabold text-slate-900">
              Kertas Cadangan Pegawai Penyiasat (IO)
            </h4>
            <textarea
              rows={4}
              value={draft.kertas_cadangan_io || ""}
              onChange={(e) => onChangeDraft({ ...draft, kertas_cadangan_io: e.target.value })}
              className={TEXTAREA_CLASS}
            />
          </div>
        </div>
      )}

      {/* KUMPULAN 3: SAKSI, EKSIBIT & SIJIL 90A */}
      {activeGroup === "saksi_eksibit" && (
        <div className="space-y-4">
          <div
            ref={(el) => {
              sectionRefs.current.saksi = el;
            }}
            className="scroll-mt-20 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm space-y-3 sm:p-5"
          >
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 pb-2">
              <h4 className="text-sm font-extrabold text-slate-900">
                Senarai Saksi Pendakwaan ({draft.senarai_saksi.length} Orang)
              </h4>
              <button
                type="button"
                onClick={addSaksiRow}
                className="inline-flex min-h-[36px] items-center gap-1 rounded-lg bg-blue-50 px-3 py-1.5 text-xs font-bold text-blue-800 hover:bg-blue-100"
              >
                <Plus className="h-3.5 w-3.5" /> Tambah Saksi
              </button>
            </div>
            <div className="divide-y divide-slate-200">
              {draft.senarai_saksi.map((s, idx) => (
                <div key={idx} className="grid grid-cols-1 gap-2.5 py-3 first:pt-1 last:pb-0 sm:grid-cols-12">
                  <div className="sm:col-span-2">
                    <label className="text-xs font-semibold text-slate-600">Kod SP</label>
                    <input
                      type="text"
                      value={s.bil}
                      onChange={(e) => {
                        const next = [...draft.senarai_saksi];
                        next[idx] = { ...next[idx], bil: e.target.value };
                        onChangeDraft({ ...draft, senarai_saksi: next });
                      }}
                      className={`${INPUT_CLASS} font-bold`}
                    />
                  </div>
                  <div className="sm:col-span-4">
                    <label className="text-xs font-semibold text-slate-600">Nama Saksi</label>
                    <input
                      type="text"
                      placeholder="Nama Penuh Saksi"
                      value={s.nama}
                      onChange={(e) => {
                        const next = [...draft.senarai_saksi];
                        next[idx] = { ...next[idx], nama: e.target.value };
                        onChangeDraft({ ...draft, senarai_saksi: next });
                      }}
                      className={INPUT_CLASS}
                    />
                  </div>
                  <div className="sm:col-span-3">
                    <label className="text-xs font-semibold text-slate-600">No. K/P Saksi</label>
                    <input
                      type="text"
                      placeholder="XXXXXX-XX-XXXX"
                      value={s.no_kp || ""}
                      onChange={(e) => {
                        const next = [...draft.senarai_saksi];
                        next[idx] = { ...next[idx], no_kp: e.target.value };
                        onChangeDraft({ ...draft, senarai_saksi: next });
                      }}
                      className={INPUT_CLASS}
                    />
                  </div>
                  <div className="sm:col-span-2">
                    <label className="text-xs font-semibold text-slate-600">Peranan</label>
                    <input
                      type="text"
                      placeholder="Pengadu / Pengiring"
                      value={s.jawatan_peranan}
                      onChange={(e) => {
                        const next = [...draft.senarai_saksi];
                        next[idx] = { ...next[idx], jawatan_peranan: e.target.value };
                        onChangeDraft({ ...draft, senarai_saksi: next });
                      }}
                      className={INPUT_CLASS}
                    />
                  </div>
                  <div className="flex items-end justify-end sm:col-span-1">
                    <button
                      type="button"
                      onClick={() =>
                        onChangeDraft({
                          ...draft,
                          senarai_saksi: draft.senarai_saksi.filter((_, i) => i !== idx),
                        })
                      }
                      title="Padam saksi"
                      className="inline-flex min-h-[38px] min-w-[38px] items-center justify-center rounded-lg bg-rose-50 text-rose-600 hover:bg-rose-100"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div
            ref={(el) => {
              sectionRefs.current.eksibit = el;
            }}
            className="scroll-mt-20 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm space-y-3 sm:p-5"
          >
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 pb-2">
              <h4 className="text-sm font-extrabold text-slate-900">
                Senarai Barang Kes / Eksibit ({draft.senarai_eksibit.length} Barang Kes)
              </h4>
              <button
                type="button"
                onClick={addEksibitRow}
                className="inline-flex min-h-[36px] items-center gap-1 rounded-lg bg-blue-50 px-3 py-1.5 text-xs font-bold text-blue-800 hover:bg-blue-100"
              >
                <Plus className="h-3.5 w-3.5" /> Tambah Eksibit
              </button>
            </div>
            <div className="divide-y divide-slate-200">
              {draft.senarai_eksibit.map((ex, idx) => (
                <div key={idx} className="grid grid-cols-1 gap-2.5 py-3 first:pt-1 last:pb-0 sm:grid-cols-12">
                  <div className="sm:col-span-2">
                    <label className="text-xs font-semibold text-slate-600">Tanda</label>
                    <input
                      type="text"
                      value={ex.tanda}
                      onChange={(e) => {
                        const next = [...draft.senarai_eksibit];
                        next[idx] = { ...next[idx], tanda: e.target.value };
                        onChangeDraft({ ...draft, senarai_eksibit: next });
                      }}
                      className={`${INPUT_CLASS} font-bold`}
                    />
                  </div>
                  <div className="sm:col-span-4">
                    <label className="text-xs font-semibold text-slate-600">Perihal Barang Kes</label>
                    <input
                      type="text"
                      placeholder="Perihal lengkap barang kes"
                      value={ex.perihal}
                      onChange={(e) => {
                        const next = [...draft.senarai_eksibit];
                        next[idx] = { ...next[idx], perihal: e.target.value };
                        onChangeDraft({ ...draft, senarai_eksibit: next });
                      }}
                      className={INPUT_CLASS}
                    />
                  </div>
                  <div className="sm:col-span-2">
                    <label className="text-xs font-semibold text-slate-600">No. Lak</label>
                    <input
                      type="text"
                      placeholder="No. Lak KKM"
                      value={ex.no_lak_seal || "-"}
                      onChange={(e) => {
                        const next = [...draft.senarai_eksibit];
                        next[idx] = { ...next[idx], no_lak_seal: e.target.value };
                        onChangeDraft({ ...draft, senarai_eksibit: next });
                      }}
                      className={INPUT_CLASS}
                    />
                  </div>
                  <div className="sm:col-span-3">
                    <label className="text-xs font-semibold text-slate-600">Lokasi Simpanan</label>
                    <input
                      type="text"
                      placeholder="Stor Eksibit Pejabat Kesihatan"
                      value={ex.lokasi_simpanan || ""}
                      onChange={(e) => {
                        const next = [...draft.senarai_eksibit];
                        next[idx] = { ...next[idx], lokasi_simpanan: e.target.value };
                        onChangeDraft({ ...draft, senarai_eksibit: next });
                      }}
                      className={INPUT_CLASS}
                    />
                  </div>
                  <div className="flex items-end justify-end sm:col-span-1">
                    <button
                      type="button"
                      onClick={() =>
                        onChangeDraft({
                          ...draft,
                          senarai_eksibit: draft.senarai_eksibit.filter((_, i) => i !== idx),
                        })
                      }
                      title="Padam eksibit"
                      className="inline-flex min-h-[38px] min-w-[38px] items-center justify-center rounded-lg bg-rose-50 text-rose-600 hover:bg-rose-100"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div
            ref={(el) => {
              sectionRefs.current.sijil90a = el;
            }}
            className="scroll-mt-20 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm space-y-3 sm:p-5"
          >
            <h4 className="border-b border-slate-200 pb-2 text-sm font-extrabold text-slate-900">
              Sijil Seksyen 90A(2) Akta Keterangan 1950
            </h4>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div>
                <label className="text-xs font-semibold text-slate-600">Nama Pegawai</label>
                <input
                  type="text"
                  value={draft.sijil_90a.nama_pegawai}
                  onChange={(e) =>
                    onChangeDraft({
                      ...draft,
                      sijil_90a: { ...draft.sijil_90a, nama_pegawai: e.target.value },
                    })
                  }
                  className={INPUT_CLASS}
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-600">Jawatan</label>
                <input
                  type="text"
                  value={draft.sijil_90a.jawatan}
                  onChange={(e) =>
                    onChangeDraft({
                      ...draft,
                      sijil_90a: { ...draft.sijil_90a, jawatan: e.target.value },
                    })
                  }
                  className={INPUT_CLASS}
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-600">Kamera / Telefon Digunakan</label>
                <input
                  type="text"
                  value={draft.sijil_90a.peranti_kamera || ""}
                  onChange={(e) =>
                    onChangeDraft({
                      ...draft,
                      sijil_90a: { ...draft.sijil_90a, peranti_kamera: e.target.value },
                    })
                  }
                  className={INPUT_CLASS}
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-600">Pejabat Kesihatan (PKD / PKK / PKB)</label>
                <input
                  type="text"
                  value={draft.sijil_90a.pejabat_pkd || ""}
                  onChange={(e) =>
                    onChangeDraft({
                      ...draft,
                      sijil_90a: { ...draft.sijil_90a, pejabat_pkd: e.target.value },
                    })
                  }
                  className={INPUT_CLASS}
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-600">Komputer Pejabat</label>
                <input
                  type="text"
                  value={draft.sijil_90a.perihal_komputer}
                  onChange={(e) =>
                    onChangeDraft({
                      ...draft,
                      sijil_90a: { ...draft.sijil_90a, perihal_komputer: e.target.value },
                    })
                  }
                  className={INPUT_CLASS}
                />
              </div>
              <div className="sm:col-span-2">
                <label className="text-xs font-semibold text-slate-600">Pencetak Pejabat</label>
                <input
                  type="text"
                  value={draft.sijil_90a.perihal_pencetak || ""}
                  onChange={(e) =>
                    onChangeDraft({
                      ...draft,
                      sijil_90a: { ...draft.sijil_90a, perihal_pencetak: e.target.value },
                    })
                  }
                  className={INPUT_CLASS}
                />
              </div>
              <div className="sm:col-span-2">
                <label className="text-xs font-semibold text-slate-600">
                  Senarai Dokumen Digital / Foto
                </label>
                <textarea
                  rows={2}
                  value={draft.sijil_90a.senarai_dokumen_digital}
                  onChange={(e) =>
                    onChangeDraft({
                      ...draft,
                      sijil_90a: {
                        ...draft.sijil_90a,
                        senarai_dokumen_digital: e.target.value,
                      },
                    })
                  }
                  className={TEXTAREA_CLASS}
                />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* KUMPULAN 4: RAKAMAN S.112 & DIARI SIASATAN */}
      {activeGroup === "rakaman_diari" && (
        <div className="space-y-4">
          <div
            ref={(el) => {
              sectionRefs.current.rakaman112 = el;
            }}
            className="scroll-mt-20 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm space-y-2 sm:p-5"
          >
            <h4 className="text-sm font-extrabold text-slate-900">
              Draf Rakaman Percakapan Seksyen 112 KTJ
            </h4>
            <textarea
              rows={8}
              value={draft.rakaman_112 || ""}
              onChange={(e) => onChangeDraft({ ...draft, rakaman_112: e.target.value })}
              className={TEXTAREA_CLASS}
            />
          </div>

          <div
            ref={(el) => {
              sectionRefs.current.diari = el;
            }}
            className="scroll-mt-20 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm space-y-3 sm:p-5"
          >
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 pb-2">
              <h4 className="text-sm font-extrabold text-slate-900">
                Diari Siasatan (DS — Seksyen 119 KTJ) ({draft.diari_siasatan.length} Baris)
              </h4>
              <button
                type="button"
                onClick={addDiariRow}
                className="inline-flex min-h-[36px] items-center gap-1 rounded-lg bg-blue-50 px-3 py-1.5 text-xs font-bold text-blue-800 hover:bg-blue-100"
              >
                <Plus className="h-3.5 w-3.5" /> Tambah Catatan Diari
              </button>
            </div>
            <div className="divide-y divide-slate-200">
              {draft.diari_siasatan.map((row, idx) => (
                <div
                  key={`${row.bil}-${idx}`}
                  className="grid grid-cols-1 gap-2.5 py-3 first:pt-1 last:pb-0 sm:grid-cols-12"
                >
                  <div className="sm:col-span-1">
                    <label className="text-xs font-semibold text-slate-600">Bil.</label>
                    <input
                      type="text"
                      placeholder="1"
                      value={row.bil}
                      onChange={(e) => {
                        const next = [...draft.diari_siasatan];
                        next[idx] = { ...next[idx], bil: e.target.value };
                        onChangeDraft({ ...draft, diari_siasatan: next });
                      }}
                      className={`${INPUT_CLASS} font-bold`}
                    />
                  </div>
                  <div className="sm:col-span-2">
                    <label className="text-xs font-semibold text-slate-600">Tarikh</label>
                    <input
                      type="text"
                      placeholder="18/11/2026"
                      value={row.tarikh || row.tarikh_masa || ""}
                      onChange={(e) => {
                        const next = [...draft.diari_siasatan];
                        next[idx] = { ...next[idx], tarikh: e.target.value };
                        onChangeDraft({ ...draft, diari_siasatan: next });
                      }}
                      className={INPUT_CLASS}
                    />
                  </div>
                  <div className="sm:col-span-2">
                    <label className="text-xs font-semibold text-slate-600">Masa</label>
                    <input
                      type="text"
                      placeholder="10.30 pagi"
                      value={row.masa || ""}
                      onChange={(e) => {
                        const next = [...draft.diari_siasatan];
                        next[idx] = { ...next[idx], masa: e.target.value };
                        onChangeDraft({ ...draft, diari_siasatan: next });
                      }}
                      className={INPUT_CLASS}
                    />
                  </div>
                  <div className="sm:col-span-6">
                    <label className="text-xs font-semibold text-slate-600">Butiran Tindakan IO</label>
                    <input
                      type="text"
                      placeholder="Catatan tindakan siasatan..."
                      value={row.butiran_tindakan}
                      onChange={(e) => {
                        const next = [...draft.diari_siasatan];
                        next[idx] = { ...next[idx], butiran_tindakan: e.target.value };
                        onChangeDraft({ ...draft, diari_siasatan: next });
                      }}
                      className={INPUT_CLASS}
                    />
                  </div>
                  <div className="flex items-end justify-end sm:col-span-1">
                    <button
                      type="button"
                      onClick={() =>
                        onChangeDraft({
                          ...draft,
                          diari_siasatan: draft.diari_siasatan.filter((_, i) => i !== idx),
                        })
                      }
                      className="inline-flex min-h-[38px] min-w-[38px] items-center justify-center rounded-lg bg-rose-50 text-rose-600 hover:bg-rose-100"
                      title="Padam baris"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Butang Terus ke Tab Kumpulan Seterusnya */}
      {nextTabMap[activeGroup] && (
        <div className="flex justify-end">
          <button
            type="button"
            onClick={() => {
              const target = nextTabMap[activeGroup];
              if (target) {
                setActiveGroup(target.next);
                window.scrollTo({ top: 0, behavior: "smooth" });
              }
            }}
            className="inline-flex min-h-[40px] items-center gap-1.5 rounded-xl border border-slate-300 bg-white px-4 py-2 text-xs font-bold text-slate-800 hover:bg-slate-50"
          >
            {nextTabMap[activeGroup]?.label}
            <ArrowRight className="h-4 w-4 text-blue-700" />
          </button>
        </div>
      )}

      {/* Petikan Akta Sebenar */}
      {draft.statutory_citations.length > 0 && (
        <div className="rounded-2xl border border-slate-200 bg-white p-4">
          <div className="mb-2 flex items-center gap-1.5 text-xs font-extrabold text-slate-800">
            <BookCheck className="h-4 w-4 text-teal-700" />
            <span>Teks Akta Sebenar Yang Dirujuk</span>
          </div>
          <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
            {draft.statutory_citations.slice(0, 2).map((cit, i) => {
              const isExp = Boolean(expandedCitations[i]);
              return (
                <div
                  key={i}
                  className="rounded-xl border border-slate-200 bg-slate-50/50 p-3 text-xs text-slate-700"
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="font-bold text-teal-800">
                      {cit.akta_code} — {cit.section}
                    </div>
                    <button
                      type="button"
                      onClick={() => setExpandedCitations((p) => ({ ...p, [i]: !p[i] }))}
                      className="text-xs font-bold text-teal-700 hover:underline"
                    >
                      {isExp ? "Ringkaskan" : "Baca Penuh"}
                    </button>
                  </div>
                  <p className={`mt-1 whitespace-pre-line ${isExp ? "" : "line-clamp-3"}`}>
                    {cit.text}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
