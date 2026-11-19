"use client";

import React, { useEffect, useRef, useState } from "react";
import {
  BookOpen,
  Camera,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  ClipboardList,
  Copy,
  ExternalLink,
  FileSearch,
  FileText,
  FileUp,
  FolderPlus,
  Image as ImageIcon,
  Loader2,
  Pencil,
  Play,
  PlusCircle,
  Save,
  Search,
  Sparkles,
  Trash2,
} from "lucide-react";
import type { ActiveAppMode } from "@/components/TopNavbar";
import type {
  EvidenceExtractionResponse,
  IPCaseRecord,
  IPFolderSectionStatus,
  StatutoryCitation,
} from "@/lib/types";

interface LeftEvidencePaneProps {
  activeMode: ActiveAppMode;
  cases: IPCaseRecord[];
  activeCaseId: string;
  isSampleCase?: boolean;
  onSelectCase: (rec: IPCaseRecord) => void;
  onOpenNewCase: () => void;
  onStartBlankCase: () => void;
  onSaveCurrentCase: () => void;
  savingCase: boolean;
  hasUnsavedChanges?: boolean;
  aktaUtama: string;
  onChangeAkta: (akta: string) => void;
  caseText: string;
  onChangeCaseText: (text: string) => void;
  uploadedFile: File | null;
  previewUrl: string | null;
  onFileSelected: (file: File | null) => void;
  onRunAudit: () => void;
  onRunDraft: () => void;
  onExtractEvidence: (docHint: string, replaceText?: boolean) => void;
  onSearchRag: (query: string) => void;
  ragResults: StatutoryCitation[];
  ragLoading: boolean;
  auditLoading: boolean;
  draftLoading: boolean;
  extractLoading: boolean;
  extractedEvidence: EvidenceExtractionResponse | null;
  folderChecklist?: IPFolderSectionStatus[];
  fileTriggerNonce?: number;
}

const AKTA_OPTIONS: Array<{ value: string; label: string }> = [
  { value: "Akta 852", label: "Akta 852 — Produk Merokok & Vape" },
  { value: "Akta 281", label: "Akta 281 — Makanan 1983 & PPKM 2009" },
  { value: "Akta 154", label: "Akta 154 — Aedes & Pembawa Penyakit" },
  { value: "Akta 342", label: "Akta 342 — Penyakit Berjangkit / Tibi" },
  { value: "Akta 593", label: "Akta 593 — Kanun Tatacara Jenayah (KTJ)" },
  { value: "Akta 56", label: "Akta 56 — Akta Keterangan 1950" },
  { value: "Semua", label: "Semua Akta KKM" },
];

const DEFAULT_FOLDER_INDEX: IPFolderSectionStatus[] = [
  { bahagian: "A", tajuk: "Kertas Minit, Izin Mendakwa TPR & Fakta Kes", status: "BELUM DISEMAK" },
  { bahagian: "B", tajuk: "Borang 114 (Pertuduhan) & Borang 143 (Pengaduan)", status: "BELUM DISEMAK" },
  { bahagian: "C", tajuk: "Notis S.32B / S.47, Kompaun & Kad AR Pos", status: "BELUM DISEMAK" },
  { bahagian: "D", tajuk: "Borang Sitaan (S.36) / Perintah S.11, Gambar & Sijil 90A", status: "BELUM DISEMAK" },
  { bahagian: "E", tajuk: "Rakaman Percakapan S.112 KTJ & Senarai Saksi", status: "BELUM DISEMAK" },
  { bahagian: "F", tajuk: "Carian SSM, Kad Kuasa & Laporan Makmal (S.19) / Entomologi", status: "BELUM DISEMAK" },
  { bahagian: "G", tajuk: "Diari Siasatan (Seksyen 119 KTJ)", status: "BELUM DISEMAK" },
];

export default function LeftEvidencePane({
  activeMode,
  cases,
  activeCaseId,
  isSampleCase = false,
  onSelectCase,
  onOpenNewCase,
  onStartBlankCase,
  onSaveCurrentCase,
  savingCase,
  hasUnsavedChanges = false,
  aktaUtama,
  onChangeAkta,
  caseText,
  onChangeCaseText,
  uploadedFile,
  previewUrl,
  onFileSelected,
  onRunAudit,
  onRunDraft,
  onExtractEvidence,
  onSearchRag,
  ragResults,
  ragLoading,
  auditLoading,
  draftLoading,
  extractLoading,
  extractedEvidence,
  folderChecklist,
  fileTriggerNonce = 0,
}: LeftEvidencePaneProps) {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const cameraInputRef = useRef<HTMLInputElement | null>(null);

  const [docHint, setDocHint] = useState("bukti_kesalahan");
  const [replaceTextOnExtract, setReplaceTextOnExtract] = useState(true);
  const [isDragging, setIsDragging] = useState(false);
  const [ragQuery, setRagQuery] = useState("");
  const [expandedRagIdx, setExpandedRagIdx] = useState<number | null>(null);
  const [showFolderIndex, setShowFolderIndex] = useState(false);
  const [showRagPanel, setShowRagPanel] = useState(false);

  useEffect(() => {
    if (fileTriggerNonce > 0) {
      fileInputRef.current?.click();
    }
  }, [fileTriggerNonce]);

  useEffect(() => {
    setReplaceTextOnExtract(isSampleCase || !caseText.trim());
  }, [isSampleCase, uploadedFile]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleChooseFile = (file: File | null) => {
    onFileSelected(file);
    if (!file) return;
    const lower = file.name.toLowerCase();
    if (lower.endsWith(".pdf") || lower.endsWith(".docx") || lower.endsWith(".txt")) {
      setDocHint("kertas_siasatan_pdf");
    } else if (lower.includes("ssm")) {
      setDocHint("sijil_ssm");
    } else {
      setDocHint("bukti_kesalahan");
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    const dropped = e.dataTransfer.files?.[0] || null;
    if (dropped) {
      handleChooseFile(dropped);
    }
  };

  const isPdf = uploadedFile?.name.toLowerCase().endsWith(".pdf");
  const isImage =
    uploadedFile?.type.startsWith("image/") ||
    /\.(png|jpe?g|webp)$/i.test(uploadedFile?.name || "");

  const checklistToDisplay =
    folderChecklist && folderChecklist.length > 0 ? folderChecklist : DEFAULT_FOLDER_INDEX;

  const activeCaseObj = cases.find((c) => c.id === activeCaseId);

  return (
    <section className="flex h-full flex-col gap-3 rounded-xl border border-slate-200 bg-white p-3.5 shadow-sm sm:p-4">
      {/* Header Panel Input */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3">
        <div>
          <h2 className="text-sm font-extrabold text-slate-900">
            Bahan Kes, Muat Naik &amp; Catatan Fakta
          </h2>
          <p className="text-[11px] text-slate-500">
            Ikut 3 langkah ringkas di bawah untuk mula analisa atau bina dokumen.
          </p>
        </div>

        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={onOpenNewCase}
            className="inline-flex min-h-[38px] items-center gap-1 rounded-lg bg-blue-50 px-2.5 py-1.5 text-xs font-bold text-blue-800 ring-1 ring-blue-200 hover:bg-blue-100"
          >
            <FolderPlus className="h-3.5 w-3.5" />
            Kes Baharu
          </button>
          <button
            type="button"
            disabled={savingCase}
            onClick={onSaveCurrentCase}
            className={`inline-flex min-h-[38px] items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs font-bold ring-1 transition disabled:opacity-60 ${
              hasUnsavedChanges
                ? "bg-amber-100 text-amber-950 ring-amber-400 hover:bg-amber-200"
                : "bg-emerald-50 text-emerald-800 ring-emerald-200 hover:bg-emerald-100"
            }`}
          >
            {savingCase ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Save className="h-3.5 w-3.5" />
            )}
            {hasUnsavedChanges ? "Simpan*" : "Simpan"}
          </button>
        </div>
      </div>

      {/* LANGKAH 1: PILIH KES & AKTA */}
      <div className="space-y-2 rounded-xl border border-slate-200 bg-slate-50/70 p-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-1.5">
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-[#0f2744] text-[10px] font-extrabold text-white">
              1
            </span>
            <span className="text-xs font-extrabold text-slate-900">
              Pilih Kes &amp; Akta Utama
            </span>
            {isSampleCase && (
              <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-bold text-amber-900 ring-1 ring-amber-300">
                Contoh Kes (Templat)
              </span>
            )}
          </div>

          {(isSampleCase || caseText.trim().length > 0) && (
            <button
              type="button"
              onClick={onStartBlankCase}
              className="inline-flex items-center gap-1 rounded-md bg-white px-2 py-1 text-[11px] font-bold text-blue-700 ring-1 ring-blue-200 hover:bg-blue-50"
            >
              <PlusCircle className="h-3 w-3" />
              Mula Kes Kosong Saya
            </button>
          )}
        </div>

        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          <div>
            <label htmlFor="case-select" className="block text-[11px] font-semibold text-slate-600">
              Fail Kes Dalam Daftar PKD
            </label>
            <select
              id="case-select"
              value={activeCaseId || ""}
              onChange={(e) => {
                if (!e.target.value) {
                  onStartBlankCase();
                  return;
                }
                const found = cases.find((c) => c.id === e.target.value);
                if (found) onSelectCase(found);
              }}
              className="mt-0.5 w-full rounded-lg border border-slate-300 bg-white px-2.5 py-2 text-base font-semibold text-slate-800 focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-100 sm:py-1.5 sm:text-xs"
            >
              <option value="">-- Kes Kosong / Fail Baharu Saya --</option>
              {cases.map((c) => (
                <option key={c.id} value={c.id}>
                  [{c.akta_utama}] {c.tajuk_kes.replace(/^Kes \d+:\s*/, "")}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="akta-select" className="block text-[11px] font-semibold text-slate-600">
              Akta Penguatkuasaan
            </label>
            <select
              id="akta-select"
              value={aktaUtama}
              onChange={(e) => onChangeAkta(e.target.value)}
              className="mt-0.5 w-full rounded-lg border border-slate-300 bg-white px-2.5 py-2 text-base font-semibold text-slate-800 focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-100 sm:py-1.5 sm:text-xs"
            >
              {AKTA_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {activeCaseObj && (
          <div className="flex flex-wrap items-center justify-between gap-1 text-[11px] text-slate-600">
            <span>
              Status: <strong className="text-slate-900">{activeCaseObj.status_kes}</strong>
            </span>
            {activeCaseObj.skor_audit > 0 && (
              <span className="rounded bg-emerald-100 px-1.5 py-0.5 text-[10px] font-bold text-emerald-800">
                Skor Terkini: {activeCaseObj.skor_audit}%
              </span>
            )}
          </div>
        )}
      </div>

      {/* LANGKAH 2: ZON TARIK FAIL (DRAG & DROP SEBENAR) + KAMERA */}
      <div className="space-y-2 rounded-xl border border-slate-200 bg-slate-50/70 p-3">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-1.5">
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-[#0f2744] text-[10px] font-extrabold text-white">
              2
            </span>
            <span className="text-xs font-extrabold text-slate-900">
              Tarik Fail atau Ambil Foto Bukti (Pilihan)
            </span>
          </div>
        </div>

        {/* Input tersembunyi untuk fail & kamera */}
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.txt,.docx,image/*"
          className="hidden"
          onChange={(e) => {
            handleChooseFile(e.target.files?.[0] || null);
            e.target.value = "";
          }}
        />
        <input
          ref={cameraInputRef}
          type="file"
          accept="image/*"
          capture="environment"
          className="hidden"
          onChange={(e) => {
            handleChooseFile(e.target.files?.[0] || null);
            e.target.value = "";
          }}
        />

        {/* Dropzone Sebenar */}
        <div
          role="button"
          tabIndex={0}
          onClick={() => {
            if (!uploadedFile) fileInputRef.current?.click();
          }}
          onKeyDown={(e) => {
            if ((e.key === "Enter" || e.key === " ") && !uploadedFile) {
              e.preventDefault();
              fileInputRef.current?.click();
            }
          }}
          onDragEnter={(e) => {
            e.preventDefault();
            e.stopPropagation();
            setIsDragging(true);
          }}
          onDragOver={(e) => {
            e.preventDefault();
            e.stopPropagation();
            setIsDragging(true);
          }}
          onDragLeave={(e) => {
            e.preventDefault();
            e.stopPropagation();
            setIsDragging(false);
          }}
          onDrop={handleDrop}
          className={`rounded-xl border-2 border-dashed p-3 transition ${
            isDragging
              ? "border-blue-600 bg-blue-50 ring-2 ring-blue-300"
              : uploadedFile
                ? "border-emerald-300 bg-emerald-50/40"
                : "cursor-pointer border-slate-300 bg-white hover:border-blue-400 hover:bg-blue-50/30"
          }`}
        >
          {!uploadedFile ? (
            <div className="space-y-2.5 text-center sm:text-left">
              <div className="flex flex-col items-center gap-2 sm:flex-row sm:items-start">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-blue-100 text-blue-700">
                  <FileUp className="h-5 w-5" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="text-xs font-extrabold text-slate-900">
                    {isDragging
                      ? "Lepaskan fail di sini sekarang..."
                      : "Klik atau Tarik Fail Kes ke Sini"}
                  </div>
                  <p className="text-[11px] text-slate-500">
                    Anda boleh muat naik &amp; analisa salah satu daripada bahan berikut:
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 gap-1.5 text-left text-[10px] sm:grid-cols-3">
                <div className="rounded-lg border border-slate-200 bg-slate-50 px-2 py-1.5">
                  <strong className="block text-slate-800">📄 Fail PDF / Word (.docx)</strong>
                  <span className="text-slate-500">Kertas Siasatan, Laporan, Borang 114</span>
                </div>
                <div className="rounded-lg border border-slate-200 bg-slate-50 px-2 py-1.5">
                  <strong className="block text-slate-800">📸 Gambar Premis / Eksibit</strong>
                  <span className="text-slate-500">Foto kotor, vape, jentik-jentik</span>
                </div>
                <div className="rounded-lg border border-slate-200 bg-slate-50 px-2 py-1.5">
                  <strong className="block text-slate-800">🧾 Sijil SSM / Borang Tulisan</strong>
                  <span className="text-slate-500">Auto-baca nama, SSM, alamat &amp; MyKad</span>
                </div>
              </div>

              <div
                className="grid grid-cols-2 gap-2 pt-0.5"
                onClick={(e) => e.stopPropagation()}
              >
                <button
                  type="button"
                  onClick={() => cameraInputRef.current?.click()}
                  className="inline-flex min-h-[42px] items-center justify-center gap-1.5 rounded-lg border border-blue-200 bg-blue-50 px-2.5 py-2 text-xs font-bold text-blue-900 hover:bg-blue-100"
                >
                  <Camera className="h-4 w-4" />
                  Ambil Foto
                </button>
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="inline-flex min-h-[42px] items-center justify-center gap-1.5 rounded-lg bg-[#0f2744] px-2.5 py-2 text-xs font-bold text-white hover:bg-slate-800"
                >
                  <FileUp className="h-4 w-4 text-amber-300" />
                  Pilih Fail / Galeri
                </button>
              </div>
            </div>
          ) : (
            <div className="space-y-2.5">
              <div className="flex items-center justify-between gap-2">
                <div className="flex min-w-0 items-center gap-2">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-emerald-100 text-emerald-700">
                    <CheckCircle2 className="h-4 w-4" />
                  </div>
                  <div className="min-w-0">
                    <div className="truncate text-xs font-bold text-slate-900">
                      {uploadedFile.name}
                    </div>
                    <div className="text-[10px] text-slate-600">
                      {Math.max(1, Math.round(uploadedFile.size / 1024))} KB • Fail sedia dianalisa
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-[11px] font-bold text-slate-700 hover:bg-slate-50"
                  >
                    Tukar
                  </button>
                  <button
                    type="button"
                    onClick={() => handleChooseFile(null)}
                    className="inline-flex min-h-[36px] min-w-[36px] items-center justify-center rounded-lg bg-rose-50 text-rose-600 ring-1 ring-rose-200 hover:bg-rose-100"
                    title="Buang fail"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>

              <div className="space-y-2 border-t border-emerald-200/70 pt-2">
                <div className="flex flex-wrap items-center gap-2">
                  <ImageIcon className="h-3.5 w-3.5 shrink-0 text-slate-500" />
                  <select
                    value={docHint}
                    onChange={(e) => setDocHint(e.target.value)}
                    className="flex-1 rounded-lg border border-slate-300 bg-white px-2 py-1.5 text-xs font-semibold text-slate-700"
                  >
                    <option value="bukti_kesalahan">Gambar Bukti Kesalahan Premis</option>
                    <option value="sijil_ssm">Cetakan / Gambar Carian SSM</option>
                    <option value="borang_sitaan">Borang Sitaan / Tulisan Tangan</option>
                    <option value="kertas_siasatan_pdf">Fail PDF / Word Kertas Siasatan</option>
                  </select>
                </div>

                <label className="flex items-center gap-2 text-[11px] font-medium text-slate-700 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={replaceTextOnExtract}
                    onChange={(e) => setReplaceTextOnExtract(e.target.checked)}
                    className="h-3.5 w-3.5 rounded border-slate-300 text-blue-600"
                  />
                  <span>Gantikan teks catatan sedia ada dengan isi fail ini</span>
                </label>

                <button
                  type="button"
                  disabled={extractLoading}
                  onClick={() => onExtractEvidence(docHint, replaceTextOnExtract)}
                  className="inline-flex min-h-[42px] w-full items-center justify-center gap-1.5 rounded-lg bg-teal-600 px-3 py-2 text-xs font-extrabold text-white shadow-sm hover:bg-teal-700 disabled:opacity-60"
                >
                  {extractLoading ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Sparkles className="h-4 w-4 text-amber-200" />
                  )}
                  Baca &amp; Masukkan Teks Dari Fail Ini ke Catatan
                </button>
              </div>
            </div>
          )}
        </div>

        {previewUrl && isImage && (
          <div className="overflow-hidden rounded-lg border border-slate-200 bg-white p-1.5">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={previewUrl}
              alt="Gambar Bukti Kesalahan"
              className="max-h-44 w-full rounded bg-slate-900/5 object-contain"
            />
          </div>
        )}
        {previewUrl && isPdf && (
          <>
            <div className="hidden overflow-hidden rounded-lg border border-slate-200 bg-white md:block">
              <iframe
                src={previewUrl}
                title="Paparan PDF Kertas Siasatan"
                className="h-48 w-full"
              />
            </div>
            <div className="flex items-center justify-between rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-xs md:hidden">
              <span className="font-bold text-blue-950 truncate">{uploadedFile?.name}</span>
              <a
                href={previewUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex shrink-0 items-center gap-1 rounded-md bg-white px-2.5 py-1 text-[11px] font-bold text-blue-800 ring-1 ring-blue-300"
              >
                Buka PDF <ExternalLink className="h-3 w-3" />
              </a>
            </div>
          </>
        )}

        {extractedEvidence && (
          <div className="rounded-lg border border-teal-200 bg-teal-50/80 p-2.5 text-xs text-teal-950">
            <div className="font-bold">✓ Maklumat Berjaya Dibaca Dari Fail:</div>
            <p className="mt-0.5 text-[11px] leading-relaxed">{extractedEvidence.structured_summary}</p>
          </div>
        )}
      </div>

      {/* LANGKAH 3: EDITOR CATATAN FAKTA KES */}
      <div className="flex flex-1 flex-col rounded-xl border border-slate-200 bg-slate-50/70 p-3">
        <div className="mb-1.5 flex flex-wrap items-center justify-between gap-2">
          <label
            htmlFor="case-text-editor"
            className="flex items-center gap-1.5 text-xs font-extrabold text-slate-900"
          >
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-[#0f2744] text-[10px] font-extrabold text-white">
              3
            </span>
            <span>Catatan Fakta Kes (Klik untuk taip atau edit)</span>
            <span className="inline-flex items-center gap-0.5 rounded bg-blue-50 px-1.5 py-0.5 text-[10px] font-bold text-blue-700">
              <Pencil className="h-2.5 w-2.5" /> Boleh Edit
            </span>
          </label>
          <div className="flex items-center gap-2">
            {caseText.trim().length > 0 && (
              <button
                type="button"
                onClick={() => onChangeCaseText("")}
                className="rounded bg-white px-2 py-0.5 text-[11px] font-semibold text-slate-600 ring-1 ring-slate-200 hover:bg-rose-50 hover:text-rose-700"
              >
                Kosongkan
              </button>
            )}
            <span className="text-[11px] text-slate-400">
              {caseText.length.toLocaleString()} huruf
            </span>
          </div>
        </div>
        <textarea
          id="case-text-editor"
          value={caseText}
          onChange={(e) => onChangeCaseText(e.target.value)}
          rows={9}
          placeholder={`Taip atau tampal fakta kes anda di sini...\nContoh:\nTarikh & Masa Kejadian: 18 November 2026, jam 10.30 pagi\nNama Premis & No. SSM: Kedai Runcit Maju (TR0012345-X)\nNama OKT & No. K/P: Ali bin Abu (880102-11-5011)\nKesalahan Ditemui: Pamer produk vape secara terbuka...`}
          className="min-h-[190px] w-full flex-1 resize-y rounded-lg border border-slate-300 bg-white p-3 font-sans text-base leading-relaxed text-slate-900 shadow-sm hover:border-blue-400 focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-100 sm:text-xs"
        />
      </div>

      {/* CTA UTAMA KONTEKSTUAL (DESKTOP & PENUH DI PANEL INPUT) */}
      <div className="hidden space-y-2 lg:block">
        {activeMode === "draft" ? (
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            <button
              type="button"
              disabled={draftLoading}
              onClick={onRunDraft}
              className="inline-flex min-h-[44px] items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-xs font-extrabold text-white shadow-sm transition hover:bg-blue-700 disabled:opacity-60"
            >
              {draftLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
              Jana Draf IP &amp; Borang 114
            </button>
            <button
              type="button"
              disabled={auditLoading}
              onClick={onRunAudit}
              className="inline-flex min-h-[44px] items-center justify-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-xs font-bold text-slate-800 hover:bg-slate-50 disabled:opacity-60"
            >
              {auditLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileSearch className="h-4 w-4 text-[#0f2744]" />}
              Semak 20 Kriteria Dahulu
            </button>
          </div>
        ) : activeMode === "compound" ? (
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            <button
              type="button"
              disabled={draftLoading}
              onClick={onRunDraft}
              className="inline-flex min-h-[44px] items-center justify-center gap-2 rounded-lg bg-amber-600 px-4 py-2.5 text-xs font-extrabold text-white shadow-sm transition hover:bg-amber-700 disabled:opacity-60"
            >
              {draftLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileText className="h-4 w-4" />}
              Tarik Data ke Borang Kompaun
            </button>
            <button
              type="button"
              disabled={auditLoading}
              onClick={onRunAudit}
              className="inline-flex min-h-[44px] items-center justify-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-xs font-bold text-slate-800 hover:bg-slate-50 disabled:opacity-60"
            >
              {auditLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileSearch className="h-4 w-4 text-[#0f2744]" />}
              Semak IP (20 Kriteria)
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            <button
              type="button"
              disabled={auditLoading}
              onClick={onRunAudit}
              className="inline-flex min-h-[44px] items-center justify-center gap-2 rounded-lg bg-[#0f2744] px-4 py-2.5 text-xs font-extrabold text-white shadow-sm transition hover:bg-slate-800 disabled:opacity-60"
            >
              {auditLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <FileSearch className="h-4 w-4 text-amber-300" />
              )}
              Semak IP Sekarang (20 Perkara)
            </button>
            <button
              type="button"
              disabled={draftLoading}
              onClick={onRunDraft}
              className="inline-flex min-h-[44px] items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-xs font-bold text-white shadow-sm transition hover:bg-blue-700 disabled:opacity-60"
            >
              {draftLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
              Jana Fail IP &amp; Borang 114
            </button>
          </div>
        )}
      </div>

      {/* Alat Tambahan Berikon Chevron */}
      <div className="space-y-2">
        <div className="rounded-lg border border-slate-200 bg-slate-50/90 p-2.5">
          <button
            type="button"
            onClick={() => setShowFolderIndex(!showFolderIndex)}
            className="flex min-h-[36px] w-full items-center justify-between text-xs font-bold text-slate-800"
          >
            <span className="inline-flex items-center gap-1.5">
              <ClipboardList className="h-4 w-4 text-[#0f2744]" />
              Semak Susunan Fail IP (Bahagian A – G)
            </span>
            <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-blue-700">
              {showFolderIndex ? "Tutup" : "Lihat"}
              {showFolderIndex ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </span>
          </button>

          {showFolderIndex && (
            <div className="mt-2 space-y-1 border-t border-slate-200 pt-2">
              {checklistToDisplay.map((sec) => (
                <div
                  key={sec.bahagian}
                  className="flex items-center justify-between gap-2 rounded bg-white px-2 py-1.5 text-[11px] ring-1 ring-slate-200/70"
                >
                  <div className="flex items-center gap-1.5">
                    <span className="rounded bg-[#0f2744] px-1.5 py-0.5 font-bold text-white">
                      {sec.bahagian}
                    </span>
                    <span className="text-slate-700">{sec.tajuk}</span>
                  </div>
                  <span
                    className={`shrink-0 rounded px-1.5 py-0.5 text-[10px] font-bold ${
                      sec.status === "LENGKAP"
                        ? "bg-emerald-100 text-emerald-800"
                        : sec.status.includes("KUIRI")
                          ? "bg-rose-100 text-rose-800"
                          : "bg-amber-100 text-amber-800"
                    }`}
                  >
                    {sec.status}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="rounded-lg border border-slate-200 bg-slate-50/90 p-2.5">
          <button
            type="button"
            onClick={() => setShowRagPanel(!showRagPanel)}
            className="flex min-h-[36px] w-full items-center justify-between text-xs font-bold text-slate-800"
          >
            <span className="inline-flex items-center gap-1.5">
              <BookOpen className="h-4 w-4 text-teal-600" />
              Cari Ayat &amp; Seksyen Akta Rasmi
            </span>
            <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-teal-700">
              {showRagPanel ? "Tutup" : "Buka Carian"}
              {showRagPanel ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </span>
          </button>

          {(showRagPanel || ragResults.length > 0) && (
            <div className="mt-2 border-t border-slate-200 pt-2">
              <div className="flex gap-1.5">
                <input
                  type="text"
                  value={ragQuery}
                  onChange={(e) => setRagQuery(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") onSearchRag(ragQuery);
                  }}
                  placeholder="cth: Seksyen 36 sitaan, Peraturan 31 tifoid..."
                  className="flex-1 rounded-md border border-slate-300 bg-white px-2.5 py-2 text-base text-slate-800 focus:border-teal-500 focus:outline-none sm:py-1.5 sm:text-xs"
                />
                <button
                  type="button"
                  disabled={ragLoading}
                  onClick={() => onSearchRag(ragQuery)}
                  className="inline-flex min-h-[40px] items-center gap-1 rounded-md bg-teal-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-teal-700 disabled:opacity-60 sm:min-h-0"
                >
                  {ragLoading ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Search className="h-3.5 w-3.5" />
                  )}
                  Cari
                </button>
              </div>

              {ragResults.length > 0 && (
                <div className="mt-2 max-h-56 space-y-2 overflow-y-auto pr-1">
                  {ragResults.map((item, idx) => {
                    const expanded = expandedRagIdx === idx;
                    return (
                      <div
                        key={`${item.akta_code}-${idx}`}
                        className="rounded border border-slate-200 bg-white p-2 text-xs"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-bold text-teal-800">
                            {item.akta_code} • {item.section}
                          </span>
                          <div className="flex items-center gap-1.5">
                            <button
                              type="button"
                              onClick={() => navigator.clipboard?.writeText(item.text)}
                              title="Salin teks akta"
                              className="rounded bg-slate-100 p-1.5 text-slate-600 hover:bg-slate-200"
                            >
                              <Copy className="h-3.5 w-3.5" />
                            </button>
                            <button
                              type="button"
                              onClick={() => setExpandedRagIdx(expanded ? null : idx)}
                              className="rounded bg-teal-50 px-2 py-1 text-[10px] font-semibold text-teal-700"
                            >
                              {expanded ? "Ringkas" : "Baca Penuh"}
                            </button>
                          </div>
                        </div>
                        <p className="mt-1 whitespace-pre-line text-[11px] leading-relaxed text-slate-600">
                          {expanded
                            ? item.text
                            : `${item.text.slice(0, 260)}${item.text.length > 260 ? "..." : ""}`}
                        </p>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
