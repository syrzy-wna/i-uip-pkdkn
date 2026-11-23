"use client";

import React, { useEffect, useRef, useState } from "react";
import {
  ArrowRight,
  Camera,
  CheckCircle2,
  ExternalLink,
  FileSearch,
  FileText,
  FileUp,
  FolderPlus,
  Loader2,
  Pencil,
  Sparkles,
  Trash2,
} from "lucide-react";
import type { ActiveAppMode } from "@/components/TopNavbar";
import type { EvidenceExtractionResponse, IPCaseRecord } from "@/lib/types";

interface LeftEvidencePaneProps {
  activeMode?: ActiveAppMode;
  cases: IPCaseRecord[];
  activeCaseId: string;
  isSampleCase?: boolean;
  onSelectCase: (rec: IPCaseRecord) => void;
  onOpenNewCase: () => void;
  onStartBlankCase: () => void;
  onLoadSampleCase?: () => void;
  aktaUtama: string;
  onChangeAkta: (akta: string) => void;
  caseText: string;
  onChangeCaseText: (text: string) => void;
  uploadedFile: File | null;
  previewUrl: string | null;
  onFileSelected: (file: File | null) => void;
  onRunAudit: () => void;
  onRunDraft: () => void;
  onStartBlankDraft?: () => void;
  onBackToResult?: () => void;
  hasExistingResult?: boolean;
  onExtractEvidence: (docHint: string, replaceText?: boolean, fileOverride?: File) => void;
  auditLoading: boolean;
  draftLoading: boolean;
  extractLoading: boolean;
  extractedEvidence: EvidenceExtractionResponse | null;
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

export default function LeftEvidencePane({
  cases,
  activeCaseId,
  isSampleCase = false,
  onSelectCase,
  onOpenNewCase,
  onStartBlankCase,
  onLoadSampleCase,
  aktaUtama,
  onChangeAkta,
  caseText,
  onChangeCaseText,
  uploadedFile,
  previewUrl,
  onFileSelected,
  onRunAudit,
  onRunDraft,
  onStartBlankDraft,
  onExtractEvidence,
  auditLoading,
  draftLoading,
  extractLoading,
  extractedEvidence,
  fileTriggerNonce = 0,
}: LeftEvidencePaneProps) {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const cameraInputRef = useRef<HTMLInputElement | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  useEffect(() => {
    if (fileTriggerNonce > 0) {
      fileInputRef.current?.click();
    }
  }, [fileTriggerNonce]);

  const handleChooseFile = (file: File | null) => {
    onFileSelected(file);
    if (!file) return;
    const lower = file.name.toLowerCase();
    const hint =
      lower.endsWith(".pdf") || lower.endsWith(".docx") || lower.endsWith(".txt")
        ? "kertas_siasatan_pdf"
        : lower.includes("ssm")
          ? "sijil_ssm"
          : "bukti_kesalahan";
    // Auto-baca teks terus sebaik fail dipilih supaya pegawai nampak hasil serta-merta
    const shouldReplace = isSampleCase || !caseText.trim();
    onExtractEvidence(hint, shouldReplace, file);
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

  return (
    <section className="mx-auto max-w-3xl rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 p-4 sm:p-5">
        <div>
          <h2 className="text-base font-extrabold text-slate-900">
            Langkah 1: Masukkan Bahan Kes
          </h2>
          <p className="mt-0.5 text-xs text-slate-600 sm:text-sm">
            Muat naik PDF / foto bukti kes atau taip ringkasan fakta kejadian di bawah.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {!caseText.trim() && !uploadedFile && onLoadSampleCase && (
            <button
              type="button"
              onClick={onLoadSampleCase}
              className="inline-flex min-h-[40px] items-center gap-1.5 rounded-xl border border-slate-300 bg-slate-50 px-3.5 py-2 text-xs font-bold text-[#0f2744] hover:bg-slate-100"
            >
              <Sparkles className="h-4 w-4 text-amber-600" />
              Cuba Contoh Kes
            </button>
          )}
          <button
            type="button"
            onClick={onOpenNewCase}
            className="inline-flex min-h-[40px] items-center gap-1.5 rounded-xl border border-slate-300 bg-white px-3.5 py-2 text-xs font-bold text-slate-800 hover:bg-slate-50"
          >
            <FolderPlus className="h-4 w-4 text-[#0f2744]" />
            + Daftar Fail Baharu
          </button>
        </div>
      </div>

      <div className="divide-y divide-slate-200 px-4 sm:px-6">
        {/* A: Pilih Fail & Akta */}
        <div className="space-y-3 py-4">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <label htmlFor="case-select" className="block text-xs font-semibold text-slate-700">
                Pilih Fail Kes Sedia Ada
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
                className="mt-1 w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-base font-semibold text-slate-800 focus:border-[#0f2744] focus:outline-none sm:text-sm"
              >
                <option value="">-- Kes Baharu / Kosong --</option>
                {cases.map((c) => (
                  <option key={c.id} value={c.id}>
                    [{c.akta_utama}] {c.tajuk_kes.replace(/^Kes \d+:\s*/, "")}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="akta-select" className="block text-xs font-semibold text-slate-700">
                Akta Penguatkuasaan
              </label>
              <select
                id="akta-select"
                value={aktaUtama}
                onChange={(e) => onChangeAkta(e.target.value)}
                className="mt-1 w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-base font-semibold text-slate-800 focus:border-[#0f2744] focus:outline-none sm:text-sm"
              >
                {AKTA_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {isSampleCase && (
            <div className="inline-flex items-center rounded-lg bg-amber-50 px-3 py-1.5 text-xs font-bold text-amber-900">
              Sedang memaparkan Contoh Kes — anda boleh ubah teks di bawah atau pilih Kes Baharu di atas.
            </div>
          )}
        </div>

        {/* B: Muat Naik Fail / Kamera (Auto-Baca Sebaik Dipilih) */}
        <div className="space-y-3 py-4">
          <div className="text-xs font-semibold text-slate-700">
            Muat Naik PDF IP, Word, Carian SSM atau Gambar Bukti{" "}
            <span className="font-normal text-slate-500">(Pilihan — teks dibaca automatik)</span>
          </div>

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
            className={`rounded-xl border-2 border-dashed p-4 transition ${
              isDragging
                ? "border-[#0f2744] bg-slate-50"
                : uploadedFile
                  ? "border-emerald-300 bg-emerald-50/30"
                  : "cursor-pointer border-slate-300 bg-slate-50/60 hover:border-slate-400"
            }`}
          >
            {!uploadedFile ? (
              <div className="flex flex-col items-center justify-between gap-3 sm:flex-row">
                <div className="flex items-center gap-3 text-left">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-white text-[#0f2744] shadow-sm ring-1 ring-slate-200">
                    <FileUp className="h-5 w-5" />
                  </div>
                  <div>
                    <div className="text-sm font-bold text-slate-900">
                      {isDragging ? "Lepaskan fail di sini..." : "Pilih Fail PDF / Word / Foto Bukti"}
                    </div>
                    <p className="text-xs text-slate-600">
                      Teks daripada fail akan terus dimasukkan ke kotak catatan di bawah.
                    </p>
                  </div>
                </div>

                <div className="flex w-full gap-2 sm:w-auto" onClick={(e) => e.stopPropagation()}>
                  <button
                    type="button"
                    onClick={() => cameraInputRef.current?.click()}
                    className="inline-flex min-h-[44px] flex-1 items-center justify-center gap-1.5 rounded-xl border border-slate-300 bg-white px-3.5 py-2 text-xs font-bold text-slate-800 hover:bg-slate-100 sm:flex-none"
                  >
                    <Camera className="h-4 w-4 text-[#0f2744]" />
                    Ambil Foto
                  </button>
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="inline-flex min-h-[44px] flex-1 items-center justify-center gap-1.5 rounded-xl bg-[#0f2744] px-3.5 py-2 text-xs font-bold text-white hover:bg-slate-800 sm:flex-none"
                  >
                    <FileUp className="h-4 w-4" />
                    Pilih Fail
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex min-w-0 items-center gap-2.5">
                  {extractLoading ? (
                    <Loader2 className="h-5 w-5 shrink-0 animate-spin text-[#0f2744]" />
                  ) : (
                    <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-600" />
                  )}
                  <div className="min-w-0">
                    <div className="truncate text-sm font-bold text-slate-900">
                      {uploadedFile.name}
                    </div>
                    <div className="text-xs text-slate-600">
                      {Math.max(1, Math.round(uploadedFile.size / 1024))} KB •{" "}
                      {extractLoading ? "Sedang membaca teks daripada fail..." : "Fail sedia disemak"}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="min-h-[38px] rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-bold text-slate-700 hover:bg-slate-50"
                  >
                    Tukar Fail
                  </button>
                  <button
                    type="button"
                    onClick={() => handleChooseFile(null)}
                    aria-label="Buang fail"
                    className="inline-flex min-h-[38px] min-w-[38px] items-center justify-center rounded-lg bg-rose-50 text-rose-600 hover:bg-rose-100"
                    title="Buang fail"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            )}
          </div>

          {previewUrl && isImage && (
            <div className="overflow-hidden rounded-xl border border-slate-200 bg-slate-50 p-1.5">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={previewUrl}
                alt="Gambar Bukti Kesalahan"
                className="max-h-44 w-full rounded-lg object-contain"
              />
            </div>
          )}

          {previewUrl && isPdf && (
            <div className="flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50 px-3.5 py-2.5 text-xs">
              <span className="truncate font-bold text-slate-900">{uploadedFile?.name}</span>
              <a
                href={previewUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex shrink-0 items-center gap-1 rounded-lg bg-white px-3 py-1.5 text-xs font-bold text-[#0f2744] ring-1 ring-slate-300 hover:bg-slate-100"
              >
                Buka PDF <ExternalLink className="h-3.5 w-3.5" />
              </a>
            </div>
          )}

          {extractedEvidence && (
            <div className="rounded-xl border border-emerald-200 bg-emerald-50/50 p-3 text-xs text-emerald-950">
              <div className="font-bold">Maklumat Berjaya Dibaca:</div>
              <p className="mt-0.5 leading-relaxed">{extractedEvidence.structured_summary}</p>
            </div>
          )}
        </div>

        {/* C: Catatan Fakta Kes + 1 CTA Utama */}
        <div className="space-y-3 py-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <label htmlFor="case-text-editor" className="text-xs font-semibold text-slate-700">
              Catatan Fakta Kes
            </label>
            <div className="flex items-center gap-3 text-xs text-slate-500">
              <span>{caseText.length.toLocaleString()} aksara</span>
              {caseText.trim().length > 0 && (
                <button
                  type="button"
                  onClick={() => onChangeCaseText("")}
                  className="font-semibold text-slate-600 hover:text-rose-700 hover:underline"
                >
                  Kosongkan
                </button>
              )}
            </div>
          </div>

          <textarea
            id="case-text-editor"
            value={caseText}
            onChange={(e) => onChangeCaseText(e.target.value)}
            rows={7}
            placeholder={`Taip atau tampal fakta kes anda di sini...\nContoh:\nTarikh & Masa: 18 November 2026, jam 10.30 pagi\nPremis & No. SSM: Kedai Runcit Maju (TR0012345-X)\nNama OKT & No. K/P: Ali bin Abu (880102-11-5011)\nKesalahan Ditemui: Pamer produk vape secara terbuka di kaunter...`}
            className="min-h-[160px] w-full resize-y rounded-xl border border-slate-300 bg-white p-3.5 text-base leading-relaxed text-slate-900 focus:border-[#0f2744] focus:outline-none focus:ring-2 focus:ring-slate-200 sm:text-sm"
          />

          <p className="text-xs text-slate-500">
            Nota: Sistem hanya menyimpan teks, keputusan semakan dan draf borang (bukan fail gambar asal).
          </p>

          {/* 1 CTA Utama + Laluan Sekunder Kemas */}
          <div className="space-y-3 pt-2">
            <button
              type="button"
              disabled={auditLoading || extractLoading}
              onClick={onRunAudit}
              className="inline-flex min-h-[48px] w-full items-center justify-center gap-2 rounded-xl bg-[#0f2744] px-5 py-3 text-sm font-extrabold text-white shadow-sm transition hover:bg-slate-800 disabled:opacity-60"
            >
              {auditLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <FileSearch className="h-4 w-4" />
              )}
              {auditLoading ? "Sedang menyemak 20 perkara IP..." : "Semak Pra-TPR Sekarang (20 Semakan)"}
              {!auditLoading && <ArrowRight className="h-4 w-4" />}
            </button>

            <div className="flex flex-wrap items-center justify-between gap-2">
              <button
                type="button"
                disabled={draftLoading || extractLoading}
                onClick={onRunDraft}
                className="inline-flex min-h-[40px] items-center gap-1.5 text-xs font-bold text-[#0f2744] hover:underline disabled:opacity-60"
              >
                {draftLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <FileText className="h-3.5 w-3.5" />}
                {draftLoading ? "Sedang menyediakan draf Word..." : "Langkau semakan, terus bina draf Fail IP →"}
              </button>

              {onStartBlankDraft && (
                <button
                  type="button"
                  onClick={onStartBlankDraft}
                  className="inline-flex min-h-[40px] items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 hover:underline"
                >
                  <Pencil className="h-3.5 w-3.5" />
                  Isi borang IP kosong
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
