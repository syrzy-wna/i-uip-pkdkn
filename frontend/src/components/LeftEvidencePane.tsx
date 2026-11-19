"use client";

import React, { useEffect, useRef, useState } from "react";
import {
  ArrowLeft,
  Camera,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  FileSearch,
  FileUp,
  FolderPlus,
  Image as ImageIcon,
  Loader2,
  Pencil,
  Play,
  Sparkles,
  Trash2,
} from "lucide-react";
import type { ActiveAppMode } from "@/components/TopNavbar";
import type { EvidenceExtractionResponse, IPCaseRecord } from "@/lib/types";

interface LeftEvidencePaneProps {
  activeMode: ActiveAppMode;
  cases: IPCaseRecord[];
  activeCaseId: string;
  isSampleCase?: boolean;
  onSelectCase: (rec: IPCaseRecord) => void;
  onOpenNewCase: () => void;
  onStartBlankCase: () => void;
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
  onExtractEvidence: (docHint: string, replaceText?: boolean) => void;
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
  activeMode,
  cases,
  activeCaseId,
  isSampleCase = false,
  onSelectCase,
  onOpenNewCase,
  onStartBlankCase,
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
  onBackToResult,
  hasExistingResult = false,
  onExtractEvidence,
  auditLoading,
  draftLoading,
  extractLoading,
  extractedEvidence,
  fileTriggerNonce = 0,
}: LeftEvidencePaneProps) {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const cameraInputRef = useRef<HTMLInputElement | null>(null);

  const [docHint, setDocHint] = useState("bukti_kesalahan");
  const [replaceTextOnExtract, setReplaceTextOnExtract] = useState(true);
  const [showAdvancedExtract, setShowAdvancedExtract] = useState(false);
  const [isDragging, setIsDragging] = useState(false);

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

  const isDraftMode = activeMode === "draft";

  return (
    <section className="flex h-full flex-col rounded-2xl border border-slate-200 bg-white shadow-sm">
      {/* Header Panel Sumber Kes */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 px-4 py-3.5">
        <div>
          <h2 className="text-sm font-extrabold text-slate-900">
            Bahan Kes &amp; Fakta Kejadian
          </h2>
          <p className="text-xs text-slate-500">
            Pilih kes, muat naik fail/foto, atau taip fakta ringkas kes.
          </p>
        </div>

        <button
          type="button"
          onClick={onOpenNewCase}
          className="inline-flex min-h-[38px] items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-bold text-slate-800 hover:bg-slate-50"
        >
          <FolderPlus className="h-3.5 w-3.5 text-blue-700" />
          + Kes Baharu
        </button>
      </div>

      {/* Bahagian Kemas Tanpa Kotak Bertindan */}
      <div className="flex flex-1 flex-col divide-y divide-slate-200 px-4">
        {/* Bahagian A: Pilih Kes & Akta */}
        <div className="space-y-2.5 py-3.5">
          <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
            <div>
              <label htmlFor="case-select" className="block text-xs font-semibold text-slate-700">
                Fail Kes PKD
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
                className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-2.5 py-2 text-base font-semibold text-slate-800 focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-100 sm:text-sm"
              >
                <option value="">-- Kes Kosong / Baru Mula --</option>
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
                className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-2.5 py-2 text-base font-semibold text-slate-800 focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-100 sm:text-sm"
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
            <div className="inline-flex items-center rounded-md bg-amber-50 px-2.5 py-1 text-[11px] font-bold text-amber-900">
              Sedang memaparkan Contoh Kes (Templat) — anda boleh edit atau pilih kes kosong di atas.
            </div>
          )}
        </div>

        {/* Bahagian B: Muat Naik Fail / Kamera */}
        <div className="space-y-2.5 py-3.5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-700">
              Fail / Gambar Bukti <span className="font-normal text-slate-400">(Pilihan)</span>
            </span>
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
            className={`rounded-xl border-2 border-dashed p-3.5 transition ${
              isDragging
                ? "border-blue-600 bg-blue-50"
                : uploadedFile
                  ? "border-emerald-300 bg-emerald-50/30"
                  : "cursor-pointer border-slate-300 bg-slate-50/50 hover:border-blue-400 hover:bg-blue-50/30"
            }`}
          >
            {!uploadedFile ? (
              <div className="space-y-3 text-center sm:text-left">
                <div className="flex flex-col items-center gap-2 sm:flex-row">
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-blue-100 text-blue-700">
                    <FileUp className="h-5 w-5" />
                  </div>
                  <div>
                    <div className="text-xs font-bold text-slate-900">
                      {isDragging
                        ? "Lepaskan fail di sini..."
                        : "Tarik atau pilih PDF IP, Word (.docx), Carian SSM atau Foto"}
                    </div>
                    <p className="text-xs text-slate-500">
                      Sistem akan membaca fail ini secara automatik apabila anda menekan butang proses di bawah.
                    </p>
                  </div>
                </div>

                <div
                  className="grid grid-cols-2 gap-2"
                  onClick={(e) => e.stopPropagation()}
                >
                  <button
                    type="button"
                    onClick={() => cameraInputRef.current?.click()}
                    className="inline-flex min-h-[42px] items-center justify-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-bold text-slate-800 hover:bg-slate-50"
                  >
                    <Camera className="h-4 w-4 text-blue-700" />
                    Ambil Foto
                  </button>
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="inline-flex min-h-[42px] items-center justify-center gap-1.5 rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-xs font-bold text-blue-900 hover:bg-blue-100"
                  >
                    <FileUp className="h-4 w-4" />
                    Pilih Fail
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-2.5">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex min-w-0 items-center gap-2">
                    <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-600" />
                    <div className="min-w-0">
                      <div className="truncate text-xs font-bold text-slate-900">
                        {uploadedFile.name}
                      </div>
                      <div className="text-[11px] text-slate-500">
                        {Math.max(1, Math.round(uploadedFile.size / 1024))} KB • Sedia dianalisa terus
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-1.5">
                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      className="rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-xs font-bold text-slate-700 hover:bg-slate-50"
                    >
                      Tukar
                    </button>
                    <button
                      type="button"
                      onClick={() => handleChooseFile(null)}
                      className="inline-flex min-h-[36px] min-w-[36px] items-center justify-center rounded-lg bg-rose-50 text-rose-600 hover:bg-rose-100"
                      title="Buang fail"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>

                {/* Pilihan Lanjutan Terlipat Supaya Tak Serabut */}
                <div className="flex flex-wrap items-center justify-between gap-2 border-t border-emerald-200/70 pt-2">
                  <button
                    type="button"
                    disabled={extractLoading}
                    onClick={() => onExtractEvidence(docHint, replaceTextOnExtract)}
                    className="inline-flex items-center gap-1.5 text-xs font-bold text-teal-800 hover:underline disabled:opacity-60"
                  >
                    {extractLoading ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <Sparkles className="h-3.5 w-3.5" />
                    )}
                    Baca &amp; masuk teks ke catatan sahaja
                  </button>

                  <button
                    type="button"
                    onClick={() => setShowAdvancedExtract((v) => !v)}
                    className="inline-flex items-center gap-1 text-[11px] font-semibold text-slate-500 hover:text-slate-800"
                  >
                    Tetapan bacaan
                    {showAdvancedExtract ? (
                      <ChevronUp className="h-3.5 w-3.5" />
                    ) : (
                      <ChevronDown className="h-3.5 w-3.5" />
                    )}
                  </button>
                </div>

                {showAdvancedExtract && (
                  <div className="space-y-2 rounded-lg bg-white p-2.5 border border-slate-200">
                    <div className="flex items-center gap-2">
                      <ImageIcon className="h-4 w-4 shrink-0 text-slate-400" />
                      <select
                        value={docHint}
                        onChange={(e) => setDocHint(e.target.value)}
                        className="flex-1 rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-base font-medium text-slate-700 sm:text-xs"
                      >
                        <option value="bukti_kesalahan">Gambar Bukti Kesalahan Premis</option>
                        <option value="sijil_ssm">Cetakan / Gambar Carian SSM</option>
                        <option value="borang_sitaan">Borang Sitaan / Tulisan Tangan</option>
                        <option value="kertas_siasatan_pdf">Fail PDF / Word Kertas Siasatan</option>
                      </select>
                    </div>
                    <label className="flex items-center gap-2 text-xs text-slate-700 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={replaceTextOnExtract}
                        onChange={(e) => setReplaceTextOnExtract(e.target.checked)}
                        className="h-4 w-4 rounded border-slate-300 text-blue-600"
                      />
                      <span>Ganti catatan sedia ada dengan teks fail ini</span>
                    </label>
                  </div>
                )}
              </div>
            )}
          </div>

          {previewUrl && isImage && (
            <div className="overflow-hidden rounded-xl border border-slate-200 bg-slate-50 p-1">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={previewUrl}
                alt="Gambar Bukti Kesalahan"
                className="max-h-40 w-full rounded-lg object-contain"
              />
            </div>
          )}

          {previewUrl && isPdf && (
            <>
              <div className="hidden overflow-hidden rounded-xl border border-slate-200 bg-white md:block">
                <iframe
                  src={previewUrl}
                  title="Paparan PDF Kertas Siasatan"
                  className="h-44 w-full"
                />
              </div>
              <div className="flex items-center justify-between rounded-xl border border-blue-200 bg-blue-50 px-3 py-2 text-xs md:hidden">
                <span className="truncate font-bold text-blue-950">{uploadedFile?.name}</span>
                <a
                  href={previewUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex shrink-0 items-center gap-1 rounded-md bg-white px-2.5 py-1 text-xs font-bold text-blue-800 ring-1 ring-blue-300"
                >
                  Buka PDF <ExternalLink className="h-3 w-3" />
                </a>
              </div>
            </>
          )}

          {extractedEvidence && (
            <div className="rounded-lg border border-teal-200 bg-teal-50/70 p-2.5 text-xs text-teal-950">
              <div className="font-bold">✓ Maklumat Dibaca:</div>
              <p className="mt-0.5 leading-relaxed">{extractedEvidence.structured_summary}</p>
            </div>
          )}

          <p className="text-[11px] text-slate-400">
            Nota: Fail/foto dibaca untuk analisis; simpanan kekal merekod teks, keputusan audit &amp; draf borang.
          </p>
        </div>

        {/* Bahagian C: Catatan Fakta Kes */}
        <div className="flex flex-1 flex-col py-3.5 space-y-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <label htmlFor="case-text-editor" className="text-xs font-semibold text-slate-700">
              Catatan Fakta Kes
            </label>
            <div className="flex items-center gap-2 text-[11px] text-slate-400">
              <span>{caseText.length.toLocaleString()} huruf</span>
              {caseText.trim().length > 0 && (
                <button
                  type="button"
                  onClick={() => onChangeCaseText("")}
                  className="font-semibold text-slate-500 hover:text-rose-700 hover:underline"
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
            rows={8}
            placeholder={`Taip atau tampal fakta kes anda di sini...\nContoh:\nTarikh & Masa Kejadian: 18 November 2026, jam 10.30 pagi\nNama Premis & No. SSM: Kedai Runcit Maju (TR0012345-X)\nNama OKT & No. K/P: Ali bin Abu (880102-11-5011)\nKesalahan Ditemui: Pamer produk vape secara terbuka...`}
            className="min-h-[170px] w-full flex-1 resize-y rounded-xl border border-slate-300 bg-white p-3 font-sans text-base leading-relaxed text-slate-900 shadow-sm hover:border-blue-400 focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-100 sm:text-sm"
          />

          {/* 1 CTA Utama Jelas Mengikut Mod */}
          <div className="space-y-2 pt-2">
            {isDraftMode ? (
              <button
                type="button"
                disabled={draftLoading}
                onClick={onRunDraft}
                className="inline-flex min-h-[46px] w-full items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-extrabold text-white shadow-sm transition hover:bg-blue-700 disabled:opacity-60"
              >
                {draftLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Play className="h-4 w-4" />
                )}
                {draftLoading ? "Sedang Membina Draf IP..." : "Jana Draf IP & Borang 114"}
              </button>
            ) : (
              <button
                type="button"
                disabled={auditLoading}
                onClick={onRunAudit}
                className="inline-flex min-h-[46px] w-full items-center justify-center gap-2 rounded-xl bg-[#0f2744] px-4 py-2.5 text-sm font-extrabold text-white shadow-sm transition hover:bg-slate-800 disabled:opacity-60"
              >
                {auditLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <FileSearch className="h-4 w-4 text-amber-300" />
                )}
                {auditLoading ? "Sedang Menyemak IP..." : "Semak IP Sekarang (20 Perkara)"}
              </button>
            )}

            <div className="flex flex-wrap items-center justify-between gap-2 pt-0.5">
              {isDraftMode && onStartBlankDraft && (
                <button
                  type="button"
                  onClick={onStartBlankDraft}
                  className="inline-flex items-center gap-1 text-xs font-bold text-slate-600 hover:text-slate-900 hover:underline"
                >
                  <Pencil className="h-3.5 w-3.5" />
                  Atau mula borang IP kosong (isi manual)
                </button>
              )}

              {hasExistingResult && onBackToResult && (
                <button
                  type="button"
                  onClick={onBackToResult}
                  className="inline-flex items-center gap-1 text-xs font-bold text-blue-700 hover:underline lg:hidden"
                >
                  <ArrowLeft className="h-3.5 w-3.5" />
                  Kembali ke Paparan Hasil
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
