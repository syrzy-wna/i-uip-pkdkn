"use client";

import React, { useEffect, useRef, useState } from "react";
import {
  AlertCircle,
  BookCheck,
  ChevronDown,
  ChevronUp,
  Download,
  FileCheck2,
  FileEdit,
  FileText,
  FolderOpen,
  Loader2,
  Pencil,
  Plus,
  Save,
  Sparkles,
  Trash2,
} from "lucide-react";
import { downloadDocx } from "@/lib/api";
import type { DraftGenerationResponse, MinitEntry } from "@/lib/types";

interface DraftDocxEditorProps {
  draft: DraftGenerationResponse | null;
  onChangeDraft: (updated: DraftGenerationResponse) => void;
  hasCaseInput: boolean;
  activeCaseTitle?: string;
  draftLoading: boolean;
  hasUnsavedChanges?: boolean;
  savingCase?: boolean;
  initialSection?: string | null;
  onGenerateDraft: () => void;
  onStartBlankDraft: () => void;
  onSaveDraft: () => void;
  onSwitchToInput: () => void;
  onLoadSampleCase: () => void;
}

const EDITOR_SECTIONS = [
  { id: "minit", label: "1. Minit IP" },
  { id: "borang114", label: "2. Borang 114" },
  { id: "fakta", label: "3. Fakta Kes" },
  { id: "sijil90a", label: "4. Sijil 90A" },
  { id: "saksi", label: "5. Saksi (SP)" },
  { id: "eksibit", label: "6. Eksibit (P)" },
  { id: "rakaman112", label: "7. Rakaman S.112" },
  { id: "diari", label: "8. Diari Siasatan" },
  { id: "kronologi", label: "9. Kronologi" },
  { id: "cadangan", label: "10. Cadangan IO" },
  { id: "saman111", label: "11. Saman 111 & Hujahan" },
];

const INPUT_CLASS =
  "mt-0.5 w-full rounded-lg border border-slate-300 bg-white px-2.5 py-2 text-base text-slate-900 shadow-sm transition hover:border-blue-400 focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-100 sm:py-1.5 sm:text-xs";

const TEXTAREA_CLASS =
  "mt-0.5 w-full rounded-lg border border-slate-300 bg-white p-2.5 text-base leading-relaxed text-slate-900 shadow-sm transition hover:border-blue-400 focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-100 sm:text-xs";

function SectionHeader({
  id,
  title,
  badge,
  isOpen,
  onToggle,
}: {
  id: string;
  title: string;
  badge?: string;
  isOpen: boolean;
  onToggle: (id: string) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onToggle(id)}
      className="flex min-h-[40px] w-full items-center justify-between gap-2 text-left"
    >
      <div className="flex flex-wrap items-center gap-2">
        <h4 className="text-xs font-extrabold text-slate-900">{title}</h4>
        <span className="inline-flex items-center gap-1 rounded bg-blue-50 px-1.5 py-0.5 text-[10px] font-bold text-blue-700">
          <Pencil className="h-2.5 w-2.5" /> Boleh Edit
        </span>
        {badge && (
          <span className="rounded bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-600">
            {badge}
          </span>
        )}
      </div>
      <span className="inline-flex shrink-0 items-center gap-1 text-[11px] font-bold text-slate-500">
        {isOpen ? "Tutup" : "Buka"}
        {isOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
      </span>
    </button>
  );
}

export default function DraftDocxEditor({
  draft,
  onChangeDraft,
  hasCaseInput,
  activeCaseTitle,
  draftLoading,
  hasUnsavedChanges = false,
  savingCase = false,
  initialSection = null,
  onGenerateDraft,
  onStartBlankDraft,
  onSaveDraft,
  onSwitchToInput,
  onLoadSampleCase,
}: DraftDocxEditorProps) {
  const [exporting, setExporting] = useState<string | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);
  const [expandedCitations, setExpandedCitations] = useState<Record<number, boolean>>({});
  const [openSections, setOpenSections] = useState<Record<string, boolean>>({
    minit: true,
    borang114: true,
    fakta: true,
    sijil90a: true,
    saksi: false,
    eksibit: false,
    rakaman112: false,
    diari: false,
    kronologi: false,
    cadangan: false,
    saman111: false,
  });

  const sectionRefs = useRef<Record<string, HTMLDivElement | null>>({});

  const jumpToSection = (secId: string) => {
    setOpenSections((prev) => ({ ...prev, [secId]: true }));
    window.setTimeout(() => {
      sectionRefs.current[secId]?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 60);
  };

  useEffect(() => {
    if (initialSection && draft) {
      setOpenSections((prev) => ({ ...prev, [initialSection]: true }));
      window.setTimeout(() => {
        sectionRefs.current[initialSection]?.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      }, 90);
    }
  }, [initialSection, draft]);

  const toggleSection = (secId: string) => {
    setOpenSections((prev) => ({ ...prev, [secId]: !prev[secId] }));
  };

  const setAllSections = (openVal: boolean) => {
    const next: Record<string, boolean> = {};
    for (const s of EDITOR_SECTIONS) next[s.id] = openVal;
    setOpenSections(next);
  };

  if (!draft) {
    return (
      <div className="space-y-4 rounded-xl border border-dashed border-slate-300 bg-slate-50/80 p-5 sm:p-7">
        <div className="flex flex-col items-center text-center">
          <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-blue-100 text-blue-700">
            <FileEdit className="h-6 w-6" />
          </div>
          <h3 className="text-sm font-extrabold text-slate-900 sm:text-base">
            Bina &amp; Edit Pakej Kertas Siasatan (IP) &amp; Dokumen Word (.docx)
          </h3>
          <p className="mt-1 max-w-lg text-xs leading-relaxed text-slate-600">
            Sistem akan membina <strong>11 dokumen lengkap</strong> secara automatik mengikut format Mahkamah Majistret &amp; UIP KKM. Semua kotak boleh diklik dan diedit sebelum dimuat turun ke Microsoft Word.
          </p>
        </div>

        <div className="mx-auto grid max-w-2xl grid-cols-1 gap-2 text-left text-xs sm:grid-cols-3">
          <div className="rounded-lg border border-slate-200 bg-white p-3">
            <div className="font-extrabold text-[#0f2744]">① Pertuduhan &amp; Pengaduan</div>
            <p className="mt-0.5 text-[11px] text-slate-500">Borang 114, Borang 143, Saman 111 &amp; Minit 1–4</p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-white p-3">
            <div className="font-extrabold text-[#0f2744]">② Keterangan &amp; Eksibit</div>
            <p className="mt-0.5 text-[11px] text-slate-500">Fakta Kes, Sijil 90A, Senarai Saksi &amp; Barang Kes</p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-white p-3">
            <div className="font-extrabold text-[#0f2744]">③ Rakaman &amp; Diari</div>
            <p className="mt-0.5 text-[11px] text-slate-500">Rakaman S.112 KTJ, Diari Siasatan (DS) &amp; Kronologi</p>
          </div>
        </div>

        {activeCaseTitle && hasCaseInput && (
          <div className="mx-auto max-w-xl rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-center text-xs text-blue-900">
            Kes sedia ada dipilih: <strong>{activeCaseTitle}</strong>
          </div>
        )}

        <div className="flex flex-col items-center justify-center gap-2 sm:flex-row sm:flex-wrap">
          {hasCaseInput ? (
            <button
              type="button"
              disabled={draftLoading}
              onClick={onGenerateDraft}
              className="inline-flex min-h-[44px] w-full items-center justify-center gap-2 rounded-xl bg-blue-600 px-5 py-2.5 text-xs font-extrabold text-white shadow-sm hover:bg-blue-700 disabled:opacity-60 sm:w-auto"
            >
              {draftLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Sparkles className="h-4 w-4 text-amber-200" />
              )}
              Jana Draf Fail IP &amp; .docx Sekarang
            </button>
          ) : (
            <button
              type="button"
              onClick={onSwitchToInput}
              className="inline-flex min-h-[44px] w-full items-center justify-center gap-2 rounded-xl bg-[#0f2744] px-5 py-2.5 text-xs font-extrabold text-white shadow-sm hover:bg-slate-800 sm:w-auto"
            >
              <FolderOpen className="h-4 w-4 text-amber-300" />
              Langkah 1: Muat Naik Fail / Isi Fakta Kes
            </button>
          )}

          <button
            type="button"
            onClick={onStartBlankDraft}
            className="inline-flex min-h-[44px] w-full items-center justify-center gap-1.5 rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-xs font-bold text-slate-800 hover:bg-slate-100 sm:w-auto"
          >
            <Pencil className="h-3.5 w-3.5" />
            Mula Borang Kosong (Edit Manual)
          </button>

          {!hasCaseInput && (
            <button
              type="button"
              onClick={onLoadSampleCase}
              className="inline-flex min-h-[44px] w-full items-center justify-center gap-1.5 rounded-xl border border-indigo-200 bg-indigo-50 px-4 py-2.5 text-xs font-bold text-indigo-800 hover:bg-indigo-100 sm:w-auto"
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
    try {
      await downloadDocx(docType, draft as unknown as Record<string, unknown>);
    } catch (err) {
      setExportError(err instanceof Error ? err.message : "Gagal muat turun fail .docx");
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
          lokasi_simpanan: "Stor Eksibit PKD",
        },
      ],
    });
  };

  return (
    <div className="space-y-3.5">
      {/* Banner Mod Suntingan + Butang Simpan Perubahan */}
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-emerald-200 bg-emerald-50/80 p-3">
        <div className="flex items-start gap-2">
          <Pencil className="mt-0.5 h-4 w-4 shrink-0 text-emerald-700" />
          <div className="text-xs text-emerald-950">
            <span className="font-extrabold">Mod Suntingan Aktif:</span> Klik mana-mana kotak putih di bawah untuk membetulkan nama, No. K/P, tarikh atau teks sebelum muat turun Word.
          </div>
        </div>
        <button
          type="button"
          disabled={savingCase}
          onClick={onSaveDraft}
          className={`inline-flex min-h-[40px] items-center gap-1.5 rounded-lg px-3.5 py-2 text-xs font-extrabold shadow-sm transition disabled:opacity-60 ${
            hasUnsavedChanges
              ? "bg-amber-500 text-slate-950 hover:bg-amber-400"
              : "bg-emerald-700 text-white hover:bg-emerald-800"
          }`}
        >
          {savingCase ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Save className="h-3.5 w-3.5" />}
          {hasUnsavedChanges ? "Simpan Perubahan*" : "Simpan ke Daftar Kes"}
        </button>
      </div>

      {hasUnsavedChanges && (
        <div className="flex items-center gap-1.5 rounded-lg border border-amber-300 bg-amber-50 px-3 py-1.5 text-[11px] font-semibold text-amber-900">
          <AlertCircle className="h-3.5 w-3.5 shrink-0" />
          Anda mempunyai suntingan yang belum disimpan ke fail kes. Tekan <strong>Simpan Perubahan</strong> di atas sebelum bertukar kes.
        </div>
      )}

      {/* Bar Muat Turun Fail Word (.docx) Berhierarki */}
      <div className="rounded-xl border border-blue-200 bg-blue-50/70 p-3 space-y-2.5">
        <div>
          <h3 className="text-xs font-extrabold text-blue-950">
            Muat Turun Dokumen Rasmi Microsoft Word (.docx)
          </h3>
          <p className="text-[11px] text-blue-800">
            Format Mahkamah Majistret &amp; UIP KKM: Kulit IP, Minit, Borang 143, Borang 114, Saman 111, Sijil 90A, S.112 &amp; Diari Siasatan.
          </p>
        </div>

        <button
          type="button"
          disabled={exporting !== null}
          onClick={() => handleExport("pakej_ip")}
          className="inline-flex min-h-[44px] w-full items-center justify-center gap-2 rounded-xl bg-emerald-700 px-4 py-2.5 text-xs font-extrabold text-white shadow-sm hover:bg-emerald-800 disabled:opacity-60"
        >
          {exporting === "pakej_ip" ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <FileCheck2 className="h-4 w-4 text-amber-200" />
          )}
          Muat Turun Pakej Fail IP Penuh (.docx)
        </button>

        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          <button
            type="button"
            disabled={exporting !== null}
            onClick={() => handleExport("borang_114")}
            className="inline-flex min-h-[42px] items-center justify-center gap-1.5 rounded-lg border border-slate-300 bg-white px-2.5 py-2 text-[11px] font-bold text-[#0f2744] hover:bg-slate-100 disabled:opacity-60"
          >
            {exporting === "borang_114" ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Download className="h-3.5 w-3.5 text-blue-700" />
            )}
            Borang 114
          </button>

          <button
            type="button"
            disabled={exporting !== null}
            onClick={() => handleExport("saman_111")}
            className="inline-flex min-h-[42px] items-center justify-center gap-1.5 rounded-lg border border-slate-300 bg-white px-2.5 py-2 text-[11px] font-bold text-[#0f2744] hover:bg-slate-100 disabled:opacity-60"
          >
            {exporting === "saman_111" ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Download className="h-3.5 w-3.5 text-blue-700" />
            )}
            Saman 111
          </button>

          <button
            type="button"
            disabled={exporting !== null}
            onClick={() => handleExport("diari_siasatan")}
            className="inline-flex min-h-[42px] items-center justify-center gap-1.5 rounded-lg border border-slate-300 bg-white px-2.5 py-2 text-[11px] font-bold text-[#0f2744] hover:bg-slate-100 disabled:opacity-60"
          >
            {exporting === "diari_siasatan" ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Download className="h-3.5 w-3.5 text-blue-700" />
            )}
            Diari Siasatan
          </button>

          <button
            type="button"
            disabled={exporting !== null}
            onClick={() => handleExport("rakaman_112")}
            className="inline-flex min-h-[42px] items-center justify-center gap-1.5 rounded-lg border border-slate-300 bg-white px-2.5 py-2 text-[11px] font-bold text-[#0f2744] hover:bg-slate-100 disabled:opacity-60"
          >
            {exporting === "rakaman_112" ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Download className="h-3.5 w-3.5 text-blue-700" />
            )}
            Rakaman S.112
          </button>
        </div>

        {exportError && (
          <p className="text-xs font-semibold text-rose-700">{exportError}</p>
        )}
      </div>

      {/* Bar Navigasi Lompat 11 Seksyen + Buka/Tutup Semua */}
      <div className="sticky top-0 z-10 rounded-xl border border-slate-200 bg-white/95 p-2 shadow-sm backdrop-blur-sm space-y-1.5">
        <div className="flex items-center justify-between gap-2 px-1 text-[11px]">
          <span className="font-extrabold text-slate-700">Lompat Pantas ke Bahagian Dokumen:</span>
          <div className="flex gap-1.5">
            <button
              type="button"
              onClick={() => setAllSections(true)}
              className="rounded bg-slate-100 px-2 py-0.5 font-bold text-slate-700 hover:bg-slate-200"
            >
              Buka Semua
            </button>
            <button
              type="button"
              onClick={() => setAllSections(false)}
              className="rounded bg-slate-100 px-2 py-0.5 font-bold text-slate-700 hover:bg-slate-200"
            >
              Tutup Semua
            </button>
          </div>
        </div>
        <div className="flex gap-1.5 overflow-x-auto pb-0.5 no-scrollbar">
          {EDITOR_SECTIONS.map((s) => (
            <button
              key={s.id}
              type="button"
              onClick={() => jumpToSection(s.id)}
              className={`shrink-0 rounded-lg border px-2.5 py-1.5 text-[11px] font-bold transition ${
                openSections[s.id]
                  ? "border-[#0f2744] bg-[#0f2744] text-white"
                  : "border-slate-200 bg-slate-50 text-slate-700 hover:border-blue-300 hover:bg-blue-50"
              }`}
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>

      {/* 1. Kertas Minit Siasatan (Minit 1-4) */}
      <div
        ref={(el) => {
          sectionRefs.current.minit = el;
        }}
        className="rounded-xl border border-slate-200 bg-slate-50/70 p-3"
      >
        <SectionHeader
          id="minit"
          title="1. Kertas Minit Siasatan (Minit 1 – 4)"
          badge={`${minitList.length} Minit`}
          isOpen={Boolean(openSections.minit)}
          onToggle={toggleSection}
        />
        {openSections.minit && (
          <div className="mt-2.5 space-y-2.5 border-t border-slate-200 pt-2.5">
            {minitList.map((m, idx) => (
              <div key={idx} className="rounded-lg border border-slate-200 bg-white p-2.5 text-xs space-y-2">
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
                  <div>
                    <label className="text-[10px] font-bold text-slate-500">Bil. Minit</label>
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
                    <label className="text-[10px] font-bold text-slate-500">Daripada → Kepada</label>
                    <input
                      type="text"
                      value={`${m.daripada} → ${m.kepada}`}
                      onChange={(e) => {
                        const parts = e.target.value.split("→");
                        const next = [...minitList];
                        next[idx] = {
                          ...next[idx],
                          daripada: (parts[0] || "").trim(),
                          kepada: (parts[1] || "").trim(),
                        };
                        onChangeDraft({ ...draft, minit_ip: next });
                      }}
                      className={INPUT_CLASS}
                    />
                  </div>
                  <div>
                    <label className="text-[10px] font-bold text-slate-500">Tarikh Minit</label>
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
                  <label className="text-[10px] font-bold text-slate-500">Kandungan Minit</label>
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
        )}
      </div>

      {/* 2. Borang 114 */}
      <div
        ref={(el) => {
          sectionRefs.current.borang114 = el;
        }}
        className="rounded-xl border border-slate-200 bg-slate-50/70 p-3"
      >
        <SectionHeader
          id="borang114"
          title="2. Kertas Pertuduhan Rasmi (Borang Mahkamah 114)"
          badge={draft.akta_utama}
          isOpen={Boolean(openSections.borang114)}
          onToggle={toggleSection}
        />
        {openSections.borang114 && (
          <div className="mt-2.5 space-y-2.5 border-t border-slate-200 pt-2.5">
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              <div>
                <label className="text-[11px] font-semibold text-slate-600">Mahkamah Majistret</label>
                <input
                  type="text"
                  value={draft.borang_114.mahkamah}
                  onChange={(e) => updateBorang114("mahkamah", e.target.value)}
                  className={INPUT_CLASS}
                />
              </div>
              <div>
                <label className="text-[11px] font-semibold text-slate-600">No. Kes / No. IP</label>
                <input
                  type="text"
                  value={draft.borang_114.no_kes}
                  onChange={(e) => updateBorang114("no_kes", e.target.value)}
                  className={INPUT_CLASS}
                />
              </div>
              <div>
                <label className="text-[11px] font-semibold text-slate-600">Nama OKS / Tertuduh</label>
                <input
                  type="text"
                  value={draft.borang_114.nama_tertuduh}
                  onChange={(e) => updateBorang114("nama_tertuduh", e.target.value)}
                  className={INPUT_CLASS}
                />
              </div>
              <div>
                <label className="text-[11px] font-semibold text-slate-600">No. Kad Pengenalan</label>
                <input
                  type="text"
                  value={draft.borang_114.no_kp_tertuduh}
                  onChange={(e) => updateBorang114("no_kp_tertuduh", e.target.value)}
                  className={INPUT_CLASS}
                />
              </div>
              <div>
                <label className="text-[11px] font-semibold text-slate-600">Umur / Jantina</label>
                <input
                  type="text"
                  value={draft.borang_114.umur_jantina || ""}
                  onChange={(e) => updateBorang114("umur_jantina", e.target.value)}
                  className={INPUT_CLASS}
                />
              </div>
              <div>
                <label className="text-[11px] font-semibold text-slate-600">Pekerjaan / Jawatan</label>
                <input
                  type="text"
                  value={draft.borang_114.pekerjaan || ""}
                  onChange={(e) => updateBorang114("pekerjaan", e.target.value)}
                  className={INPUT_CLASS}
                />
              </div>
              <div className="sm:col-span-2">
                <label className="text-[11px] font-semibold text-slate-600">Alamat OKS</label>
                <input
                  type="text"
                  value={draft.borang_114.alamat_tertuduh}
                  onChange={(e) => updateBorang114("alamat_tertuduh", e.target.value)}
                  className={INPUT_CLASS}
                />
              </div>
              <div>
                <label className="text-[11px] font-semibold text-slate-600">Tarikh Kejadian</label>
                <input
                  type="text"
                  value={draft.borang_114.tarikh_kejadian}
                  onChange={(e) => updateBorang114("tarikh_kejadian", e.target.value)}
                  className={INPUT_CLASS}
                />
              </div>
              <div>
                <label className="text-[11px] font-semibold text-slate-600">Masa Kejadian</label>
                <input
                  type="text"
                  value={draft.borang_114.masa_kejadian}
                  onChange={(e) => updateBorang114("masa_kejadian", e.target.value)}
                  className={INPUT_CLASS}
                />
              </div>
              <div className="sm:col-span-2">
                <label className="text-[11px] font-semibold text-slate-600">Tempat Kejadian</label>
                <input
                  type="text"
                  value={draft.borang_114.tempat_kejadian}
                  onChange={(e) => updateBorang114("tempat_kejadian", e.target.value)}
                  className={INPUT_CLASS}
                />
              </div>
              <div>
                <label className="text-[11px] font-semibold text-slate-600">Seksyen Kesalahan</label>
                <input
                  type="text"
                  value={draft.borang_114.akta_dan_seksyen}
                  onChange={(e) => updateBorang114("akta_dan_seksyen", e.target.value)}
                  className={INPUT_CLASS}
                />
              </div>
              <div>
                <label className="text-[11px] font-semibold text-slate-600">Seksyen Hukuman</label>
                <input
                  type="text"
                  value={draft.borang_114.seksyen_hukuman}
                  onChange={(e) => updateBorang114("seksyen_hukuman", e.target.value)}
                  className={INPUT_CLASS}
                />
              </div>
              <div className="sm:col-span-2">
                <label className="text-[11px] font-semibold text-slate-600">Hukuman Statutori Maksimum</label>
                <input
                  type="text"
                  value={draft.borang_114.hukuman_maksimum || ""}
                  onChange={(e) => updateBorang114("hukuman_maksimum", e.target.value)}
                  className={INPUT_CLASS}
                />
              </div>
            </div>

            <div>
              <label className="text-[11px] font-semibold text-slate-600">
                Teks Pertuduhan Rasmi Borang 114
              </label>
              <textarea
                rows={4}
                value={draft.borang_114.teks_pertuduhan}
                onChange={(e) => updateBorang114("teks_pertuduhan", e.target.value)}
                className={TEXTAREA_CLASS}
              />
            </div>
          </div>
        )}
      </div>

      {/* 3. Fakta Kes Ringkas */}
      <div
        ref={(el) => {
          sectionRefs.current.fakta = el;
        }}
        className="rounded-xl border border-slate-200 bg-slate-50/70 p-3"
      >
        <SectionHeader
          id="fakta"
          title="3. Fakta Kes Ringkas"
          isOpen={Boolean(openSections.fakta)}
          onToggle={toggleSection}
        />
        {openSections.fakta && (
          <div className="mt-2.5 border-t border-slate-200 pt-2.5">
            <textarea
              rows={8}
              value={draft.fakta_kes}
              onChange={(e) => onChangeDraft({ ...draft, fakta_kes: e.target.value })}
              className={TEXTAREA_CLASS}
            />
          </div>
        )}
      </div>

      {/* 4. Sijil Seksyen 90A(2) */}
      <div
        ref={(el) => {
          sectionRefs.current.sijil90a = el;
        }}
        className="rounded-xl border border-slate-200 bg-slate-50/70 p-3"
      >
        <SectionHeader
          id="sijil90a"
          title="4. Sijil Seksyen 90A(2) Akta Keterangan 1950"
          isOpen={Boolean(openSections.sijil90a)}
          onToggle={toggleSection}
        />
        {openSections.sijil90a && (
          <div className="mt-2.5 space-y-2 border-t border-slate-200 pt-2.5">
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              <div>
                <label className="text-[11px] font-semibold text-slate-600">Nama Pegawai</label>
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
                <label className="text-[11px] font-semibold text-slate-600">Jawatan</label>
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
            </div>
            <div>
              <label className="text-[11px] font-semibold text-slate-600">Kamera / Peranti Input</label>
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
              <label className="text-[11px] font-semibold text-slate-600">Komputer &amp; Pencetak Pejabat</label>
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
            <div>
              <label className="text-[11px] font-semibold text-slate-600">Senarai Dokumen Digital / Foto</label>
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
        )}
      </div>

      {/* 5. Senarai Saksi Pendakwaan (SP) */}
      <div
        ref={(el) => {
          sectionRefs.current.saksi = el;
        }}
        className="rounded-xl border border-slate-200 bg-slate-50/70 p-3"
      >
        <SectionHeader
          id="saksi"
          title="5. Senarai Saksi Pendakwaan (SP)"
          badge={`${draft.senarai_saksi.length} Orang`}
          isOpen={Boolean(openSections.saksi)}
          onToggle={toggleSection}
        />
        {openSections.saksi && (
          <div className="mt-2.5 space-y-2 border-t border-slate-200 pt-2.5">
            <div className="flex justify-end">
              <button
                type="button"
                onClick={addSaksiRow}
                className="inline-flex min-h-[36px] items-center gap-1 rounded-lg bg-blue-600 px-3 py-1 text-[11px] font-bold text-white hover:bg-blue-700"
              >
                <Plus className="h-3.5 w-3.5" /> Tambah Saksi
              </button>
            </div>
            <div className="space-y-2">
              {draft.senarai_saksi.map((s, idx) => (
                <div
                  key={idx}
                  className="grid grid-cols-1 gap-2 rounded-lg border border-slate-200 bg-white p-2.5 sm:grid-cols-12"
                >
                  <div className="sm:col-span-2">
                    <label className="text-[10px] font-bold text-slate-500">Kod SP</label>
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
                    <label className="text-[10px] font-bold text-slate-500">Nama Saksi</label>
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
                    <label className="text-[10px] font-bold text-slate-500">No. K/P Saksi</label>
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
                    <label className="text-[10px] font-bold text-slate-500">Peranan / Jawatan</label>
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
                      className="inline-flex min-h-[38px] min-w-[38px] items-center justify-center rounded-lg bg-rose-50 text-rose-600 ring-1 ring-rose-200 hover:bg-rose-100"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* 6. Senarai Barang Kes / Eksibit (P) */}
      <div
        ref={(el) => {
          sectionRefs.current.eksibit = el;
        }}
        className="rounded-xl border border-slate-200 bg-slate-50/70 p-3"
      >
        <SectionHeader
          id="eksibit"
          title="6. Senarai Barang Kes / Eksibit (P)"
          badge={`${draft.senarai_eksibit.length} Item`}
          isOpen={Boolean(openSections.eksibit)}
          onToggle={toggleSection}
        />
        {openSections.eksibit && (
          <div className="mt-2.5 space-y-2 border-t border-slate-200 pt-2.5">
            <div className="flex justify-end">
              <button
                type="button"
                onClick={addEksibitRow}
                className="inline-flex min-h-[36px] items-center gap-1 rounded-lg bg-blue-600 px-3 py-1 text-[11px] font-bold text-white hover:bg-blue-700"
              >
                <Plus className="h-3.5 w-3.5" /> Tambah Eksibit
              </button>
            </div>
            <div className="space-y-2">
              {draft.senarai_eksibit.map((ex, idx) => (
                <div
                  key={idx}
                  className="grid grid-cols-1 gap-2 rounded-lg border border-slate-200 bg-white p-2.5 sm:grid-cols-12"
                >
                  <div className="sm:col-span-2">
                    <label className="text-[10px] font-bold text-slate-500">Tanda</label>
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
                    <label className="text-[10px] font-bold text-slate-500">Perihal Barang Kes</label>
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
                    <label className="text-[10px] font-bold text-slate-500">No. Lak / Seal</label>
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
                    <label className="text-[10px] font-bold text-slate-500">Lokasi Simpanan</label>
                    <input
                      type="text"
                      placeholder="Stor Eksibit PKD"
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
                      className="inline-flex min-h-[38px] min-w-[38px] items-center justify-center rounded-lg bg-rose-50 text-rose-600 ring-1 ring-rose-200 hover:bg-rose-100"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* 7. Rakaman Percakapan S.112 KTJ */}
      <div
        ref={(el) => {
          sectionRefs.current.rakaman112 = el;
        }}
        className="rounded-xl border border-slate-200 bg-slate-50/70 p-3"
      >
        <SectionHeader
          id="rakaman112"
          title="7. Draf Rakaman Percakapan Seksyen 112 KTJ"
          isOpen={Boolean(openSections.rakaman112)}
          onToggle={toggleSection}
        />
        {openSections.rakaman112 && (
          <div className="mt-2.5 border-t border-slate-200 pt-2.5">
            <textarea
              rows={8}
              value={draft.rakaman_112 || ""}
              onChange={(e) => onChangeDraft({ ...draft, rakaman_112: e.target.value })}
              className={TEXTAREA_CLASS}
            />
          </div>
        )}
      </div>

      {/* 8. Diari Siasatan */}
      <div
        ref={(el) => {
          sectionRefs.current.diari = el;
        }}
        className="rounded-xl border border-slate-200 bg-slate-50/70 p-3"
      >
        <SectionHeader
          id="diari"
          title="8. Diari Siasatan (DS — Seksyen 119 KTJ)"
          badge={`${draft.diari_siasatan.length} Baris`}
          isOpen={Boolean(openSections.diari)}
          onToggle={toggleSection}
        />
        {openSections.diari && (
          <div className="mt-2.5 space-y-2 border-t border-slate-200 pt-2.5">
            <div className="flex justify-end">
              <button
                type="button"
                onClick={addDiariRow}
                className="inline-flex min-h-[36px] items-center gap-1 rounded-lg bg-blue-600 px-3 py-1 text-[11px] font-bold text-white hover:bg-blue-700"
              >
                <Plus className="h-3.5 w-3.5" /> Tambah Baris DS
              </button>
            </div>
            <div className="space-y-2">
              {draft.diari_siasatan.map((row, idx) => (
                <div
                  key={`${row.bil}-${idx}`}
                  className="grid grid-cols-1 gap-2 rounded-lg border border-slate-200 bg-white p-2.5 sm:grid-cols-12"
                >
                  <div className="sm:col-span-1">
                    <label className="text-[10px] font-bold text-slate-500">Bil.</label>
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
                    <label className="text-[10px] font-bold text-slate-500">Tarikh</label>
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
                    <label className="text-[10px] font-bold text-slate-500">Masa</label>
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
                    <label className="text-[10px] font-bold text-slate-500">Butiran Tindakan IO</label>
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
                      className="inline-flex min-h-[38px] min-w-[38px] items-center justify-center rounded-lg bg-rose-50 text-rose-600 ring-1 ring-rose-200 hover:bg-rose-100"
                      title="Padam baris"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* 9. Kronologi Kes */}
      <div
        ref={(el) => {
          sectionRefs.current.kronologi = el;
        }}
        className="rounded-xl border border-slate-200 bg-slate-50/70 p-3"
      >
        <SectionHeader
          id="kronologi"
          title="9. Kronologi Kes (Susunan Tarikh Siasatan)"
          badge={`${(draft.kronologi_kes || []).length} Peristiwa`}
          isOpen={Boolean(openSections.kronologi)}
          onToggle={toggleSection}
        />
        {openSections.kronologi && (
          <div className="mt-2.5 space-y-2 border-t border-slate-200 pt-2.5">
            <div className="flex justify-end">
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
                className="inline-flex min-h-[36px] items-center gap-1 rounded-lg bg-blue-600 px-3 py-1 text-[11px] font-bold text-white hover:bg-blue-700"
              >
                <Plus className="h-3.5 w-3.5" /> Tambah Kronologi
              </button>
            </div>
            <div className="space-y-2">
              {(draft.kronologi_kes || []).map((item, idx) => (
                <div
                  key={idx}
                  className="grid grid-cols-1 gap-2 rounded-lg border border-slate-200 bg-white p-2.5 sm:grid-cols-12"
                >
                  <div className="sm:col-span-3">
                    <label className="text-[10px] font-bold text-slate-500">Tarikh / Waktu</label>
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
                    <label className="text-[10px] font-bold text-slate-500">Peristiwa / Tindakan</label>
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
                      className="inline-flex min-h-[38px] min-w-[38px] items-center justify-center rounded-lg bg-rose-50 text-rose-600 ring-1 ring-rose-200 hover:bg-rose-100"
                      title="Padam baris"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* 10. Kertas Cadangan IO */}
      <div
        ref={(el) => {
          sectionRefs.current.cadangan = el;
        }}
        className="rounded-xl border border-slate-200 bg-slate-50/70 p-3"
      >
        <SectionHeader
          id="cadangan"
          title="10. Kertas Cadangan Pegawai Penyiasat (IO)"
          isOpen={Boolean(openSections.cadangan)}
          onToggle={toggleSection}
        />
        {openSections.cadangan && (
          <div className="mt-2.5 border-t border-slate-200 pt-2.5">
            <textarea
              rows={5}
              value={draft.kertas_cadangan_io || ""}
              onChange={(e) => onChangeDraft({ ...draft, kertas_cadangan_io: e.target.value })}
              className={TEXTAREA_CLASS}
            />
          </div>
        )}
      </div>

      {/* 11. Saman 111 & Hujahan Pemberatan Hukuman */}
      <div
        ref={(el) => {
          sectionRefs.current.saman111 = el;
        }}
        className="rounded-xl border border-slate-200 bg-slate-50/70 p-3"
      >
        <SectionHeader
          id="saman111"
          title="11. Saman (Mahkamah 111) &amp; Hujahan Pemberatan"
          isOpen={Boolean(openSections.saman111)}
          onToggle={toggleSection}
        />
        {openSections.saman111 && (
          <div className="mt-2.5 space-y-3 border-t border-slate-200 pt-2.5">
            {draft.saman_111 && (
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
                <div>
                  <label className="text-[11px] font-semibold text-slate-600">Mahkamah Majistret</label>
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
                  <label className="text-[11px] font-semibold text-slate-600">Tarikh Hadir Mahkamah</label>
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
                  <label className="text-[11px] font-semibold text-slate-600">Masa Hadir</label>
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

            <div>
              <div className="mb-1.5 flex flex-wrap items-center justify-between gap-2">
                <span className="text-[11px] font-bold text-slate-700">
                  Poin Pemberatan Hukuman (Jika OKT Mengaku Salah / Sabit):
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
                  className="inline-flex min-h-[34px] items-center gap-1 rounded-lg bg-blue-600 px-2.5 py-1 text-[11px] font-bold text-white hover:bg-blue-700"
                >
                  <Plus className="h-3.5 w-3.5" /> Tambah Poin
                </button>
              </div>
              <div className="space-y-1.5">
                {(draft.pemberatan_hukuman || []).map((pt, idx) => (
                  <div key={idx} className="flex items-center gap-1.5">
                    <span className="w-5 text-center text-[11px] font-bold text-slate-600">
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
                      className="inline-flex min-h-[38px] min-w-[38px] items-center justify-center rounded-lg bg-rose-50 text-rose-600 ring-1 ring-rose-200 hover:bg-rose-100"
                      title="Padam poin"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Petikan Akta Sebenar */}
      {draft.statutory_citations.length > 0 && (
        <div className="rounded-xl border border-teal-200 bg-teal-50/50 p-3">
          <div className="mb-1.5 flex items-center gap-1.5 text-xs font-bold text-teal-900">
            <BookCheck className="h-4 w-4 text-teal-700" />
            <span>Teks Akta Sebenar Yang Dirujuk</span>
          </div>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            {draft.statutory_citations.slice(0, 2).map((cit, i) => {
              const isExp = Boolean(expandedCitations[i]);
              return (
                <div
                  key={i}
                  className="rounded-lg border border-teal-200 bg-white p-2.5 text-[11px] text-slate-700"
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="font-bold text-teal-800">
                      {cit.akta_code} — {cit.section}
                    </div>
                    <button
                      type="button"
                      onClick={() => setExpandedCitations((p) => ({ ...p, [i]: !p[i] }))}
                      className="rounded bg-teal-50 px-2 py-0.5 text-[10px] font-bold text-teal-700 hover:bg-teal-100"
                    >
                      {isExp ? "Ringkas" : "Baca Penuh"}
                    </button>
                  </div>
                  <p className={`mt-1 whitespace-pre-line ${isExp ? "" : "line-clamp-4"}`}>
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
