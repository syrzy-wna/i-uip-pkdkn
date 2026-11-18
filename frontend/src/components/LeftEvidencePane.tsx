"use client";

import React, { useRef, useState } from "react";
import {
  BookOpen,
  CheckCircle2,
  ClipboardList,
  Copy,
  FileSearch,
  FileUp,
  FolderPlus,
  Image as ImageIcon,
  Loader2,
  Play,
  Save,
  Search,
  Sparkles,
  Trash2,
} from "lucide-react";
import type {
  EvidenceExtractionResponse,
  IPCaseRecord,
  IPFolderSectionStatus,
  StatutoryCitation,
} from "@/lib/types";

interface LeftEvidencePaneProps {
  cases: IPCaseRecord[];
  activeCaseId: string;
  onSelectCase: (rec: IPCaseRecord) => void;
  onOpenNewCase: () => void;
  onSaveCurrentCase: () => void;
  savingCase: boolean;
  aktaUtama: string;
  onChangeAkta: (akta: string) => void;
  caseText: string;
  onChangeCaseText: (text: string) => void;
  uploadedFile: File | null;
  previewUrl: string | null;
  onFileSelected: (file: File | null) => void;
  onRunAudit: () => void;
  onRunDraft: () => void;
  onExtractEvidence: (docHint: string) => void;
  onSearchRag: (query: string) => void;
  ragResults: StatutoryCitation[];
  ragLoading: boolean;
  auditLoading: boolean;
  draftLoading: boolean;
  extractLoading: boolean;
  extractedEvidence: EvidenceExtractionResponse | null;
  folderChecklist?: IPFolderSectionStatus[];
}

const AKTA_OPTIONS = [
  "Akta 852",
  "Akta 281",
  "Akta 154",
  "Akta 342",
  "Akta 593",
  "Akta 56",
  "Semua",
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
  cases,
  activeCaseId,
  onSelectCase,
  onOpenNewCase,
  onSaveCurrentCase,
  savingCase,
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
}: LeftEvidencePaneProps) {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [docHint, setDocHint] = useState("bukti_kesalahan");
  const [ragQuery, setRagQuery] = useState("Seksyen 36 Akta 852 atau Seksyen 90A");
  const [expandedRagIdx, setExpandedRagIdx] = useState<number | null>(null);
  const [showFolderIndex, setShowFolderIndex] = useState(false);
  const [showRagPanel, setShowRagPanel] = useState(false);

  const isPdf = uploadedFile?.name.toLowerCase().endsWith(".pdf");
  const isImage =
    uploadedFile?.type.startsWith("image/") ||
    /\.(png|jpe?g|webp)$/i.test(uploadedFile?.name || "");

  const checklistToDisplay =
    folderChecklist && folderChecklist.length > 0
      ? folderChecklist
      : DEFAULT_FOLDER_INDEX;

  return (
    <section className="flex h-full flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      {/* Tajuk Panel Kiri */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3">
        <div>
          <h2 className="text-sm font-bold text-slate-900">
            Rekod Kes, Fail Bukti &amp; Rujukan Akta
          </h2>
          <p className="text-xs text-slate-500">
            Muat naik PDF Kertas Siasatan, gambar premis/SSM, atau urus kes PKD.
          </p>
        </div>

        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={onOpenNewCase}
            className="inline-flex items-center gap-1 rounded-lg bg-blue-50 px-2.5 py-1.5 text-xs font-bold text-blue-800 ring-1 ring-blue-200 hover:bg-blue-100"
          >
            <FolderPlus className="h-3.5 w-3.5" />
            Kes Baharu
          </button>
          <button
            type="button"
            disabled={savingCase}
            onClick={onSaveCurrentCase}
            className="inline-flex items-center gap-1 rounded-lg bg-emerald-50 px-2.5 py-1.5 text-xs font-bold text-emerald-800 ring-1 ring-emerald-200 hover:bg-emerald-100 disabled:opacity-60"
          >
            {savingCase ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Save className="h-3.5 w-3.5" />
            )}
            Simpan
          </button>
        </div>
      </div>

      {/* Pemilih Kes Tersimpan + Akta */}
      <div className="space-y-2">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
            Kes Aktif dalam Daftar PKD
          </span>
          <div className="flex items-center gap-2">
            <label className="text-xs font-medium text-slate-600" htmlFor="akta-select">
              Akta:
            </label>
            <select
              id="akta-select"
              value={aktaUtama}
              onChange={(e) => onChangeAkta(e.target.value)}
              className="rounded-lg border border-slate-300 bg-slate-50 px-2 py-1 text-xs font-semibold text-slate-800 focus:border-blue-500 focus:outline-none"
            >
              {AKTA_OPTIONS.map((opt) => (
                <option key={opt} value={opt}>
                  {opt}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-1.5 sm:grid-cols-2">
          {cases.slice(0, 4).map((rec) => {
            const active = rec.id === activeCaseId;
            return (
              <button
                key={rec.id}
                type="button"
                onClick={() => onSelectCase(rec)}
                className={`rounded-lg border p-2 text-left transition ${
                  active
                    ? "border-blue-600 bg-blue-50/80 ring-1 ring-blue-500"
                    : "border-slate-200 bg-slate-50/50 hover:border-slate-300 hover:bg-slate-50"
                }`}
              >
                <div className="flex items-center justify-between gap-1">
                  <span className="text-[11px] font-bold text-blue-800">
                    {rec.akta_utama}
                  </span>
                  <span
                    className={`rounded px-1.5 py-0.5 text-[9px] font-semibold ${
                      rec.status_kes.includes("DITOLAK") || rec.status_kes.includes("KRITIKAL")
                        ? "bg-rose-100 text-rose-700"
                        : rec.status_kes.includes("SEDIA")
                          ? "bg-emerald-100 text-emerald-700"
                          : "bg-amber-100 text-amber-800"
                    }`}
                  >
                    {rec.badge}
                  </span>
                </div>
                <div className="mt-1 line-clamp-2 text-xs font-semibold text-slate-800">
                  {rec.tajuk_kes.replace(/^Kes \d+:\s*/, "")}
                </div>
              </button>
            );
          })}
        </div>

        {cases.length > 4 && (
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-semibold text-slate-500">Semua Kes:</span>
            <select
              value={activeCaseId}
              onChange={(e) => {
                const found = cases.find((c) => c.id === e.target.value);
                if (found) onSelectCase(found);
              }}
              className="flex-1 rounded-lg border border-slate-300 bg-white px-2 py-1 text-xs font-medium text-slate-800"
            >
              {cases.map((c) => (
                <option key={c.id} value={c.id}>
                  [{c.akta_utama}] {c.tajuk_kes}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Indeks Kandungan Fail IP (Bahagian A-G) */}
      <div className="rounded-lg border border-slate-200 bg-slate-50/80 p-2.5">
        <button
          type="button"
          onClick={() => setShowFolderIndex(!showFolderIndex)}
          className="flex w-full items-center justify-between text-xs font-bold text-slate-800"
        >
          <span className="inline-flex items-center gap-1.5">
            <ClipboardList className="h-4 w-4 text-[#0f2744]" />
            Indeks Kandungan Fail IP (Bahagian A – G)
          </span>
          <span className="text-[11px] font-semibold text-blue-700">
            {showFolderIndex ? "Tutup Senarai" : "Lihat Status Fail"}
          </span>
        </button>

        {showFolderIndex && (
          <div className="mt-2 space-y-1 border-t border-slate-200 pt-2">
            {checklistToDisplay.map((sec) => (
              <div
                key={sec.bahagian}
                className="flex items-center justify-between gap-2 rounded bg-white px-2 py-1 text-[11px] ring-1 ring-slate-200/70"
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

      {/* Zon Muat Naik Fail */}
      <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50/70 p-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <FileUp className="h-4 w-4 text-blue-600" />
            <div className="text-xs">
              <span className="font-semibold text-slate-800">
                {uploadedFile
                  ? `${uploadedFile.name} (${Math.round(uploadedFile.size / 1024)} KB)`
                  : "Muat Naik Fail PDF IP / Gambar Premis / Carian SSM / .docx"}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-1.5">
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.txt,.docx,image/*"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0] || null;
                onFileSelected(file);
              }}
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="rounded-md bg-white px-2.5 py-1 text-xs font-semibold text-slate-700 shadow-sm ring-1 ring-slate-300 hover:bg-slate-50"
            >
              Pilih Fail
            </button>
            {uploadedFile && (
              <button
                type="button"
                onClick={() => onFileSelected(null)}
                className="rounded-md bg-rose-50 p-1 text-rose-600 ring-1 ring-rose-200 hover:bg-rose-100"
                title="Buang fail"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
        </div>

        {uploadedFile && (
          <div className="mt-2 flex flex-wrap items-center justify-between gap-2 border-t border-slate-200 pt-2">
            <div className="flex items-center gap-2">
              <ImageIcon className="h-3.5 w-3.5 text-slate-500" />
              <select
                value={docHint}
                onChange={(e) => setDocHint(e.target.value)}
                className="rounded border border-slate-300 bg-white px-2 py-1 text-xs text-slate-700"
              >
                <option value="bukti_kesalahan">Gambar Bukti Kesalahan</option>
                <option value="sijil_ssm">Cetakan Carian SSM</option>
                <option value="borang_sitaan">Borang Sitaan Tulisan Tangan</option>
                <option value="kertas_siasatan_pdf">Fail PDF Kertas Siasatan</option>
              </select>
            </div>
            <button
              type="button"
              disabled={extractLoading}
              onClick={() => onExtractEvidence(docHint)}
              className="inline-flex items-center gap-1.5 rounded-md bg-teal-600 px-2.5 py-1 text-xs font-semibold text-white hover:bg-teal-700 disabled:opacity-60"
            >
              {extractLoading ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Sparkles className="h-3.5 w-3.5" />
              )}
              Ekstrak Teks &amp; Bukti Dokumen (OCR / Vision)
            </button>
          </div>
        )}

        {previewUrl && isImage && (
          <div className="mt-2 overflow-hidden rounded-lg border border-slate-200 bg-white p-1.5">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={previewUrl}
              alt="Gambar Bukti Kesalahan"
              className="max-h-48 w-full rounded bg-slate-900/5 object-contain"
            />
          </div>
        )}
        {previewUrl && isPdf && (
          <div className="mt-2 overflow-hidden rounded-lg border border-slate-200 bg-white">
            <iframe
              src={previewUrl}
              title="Paparan PDF Kertas Siasatan"
              className="h-52 w-full"
            />
          </div>
        )}

        {extractedEvidence && (
          <div className="mt-2 rounded-md border border-teal-200 bg-teal-50/70 p-2 text-xs text-teal-900">
            <div className="font-semibold">
              Hasil Pengekstrakan ({extractedEvidence.model_used}):
            </div>
            <p className="mt-0.5 text-[11px]">{extractedEvidence.structured_summary}</p>
          </div>
        )}
      </div>

      {/* Editor Teks Kes */}
      <div className="flex flex-1 flex-col">
        <div className="mb-1 flex items-center justify-between gap-2">
          <label
            htmlFor="case-text-editor"
            className="text-xs font-semibold uppercase tracking-wider text-slate-500"
          >
            Teks Kertas Siasatan / Catatan Operasi PPKP
          </label>
          <div className="flex items-center gap-2">
            {caseText.trim().length > 0 && (
              <button
                type="button"
                onClick={() => onChangeCaseText("")}
                className="rounded bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-600 hover:bg-rose-50 hover:text-rose-700"
              >
                Kosongkan Teks
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
          rows={10}
          placeholder="Taip atau tampal fakta operasi, catatan diari siasatan, atau muat naik PDF IP di atas..."
          className="min-h-[200px] w-full flex-1 resize-y rounded-lg border border-slate-300 bg-slate-50/40 p-3 font-mono text-xs leading-relaxed text-slate-800 focus:border-blue-500 focus:bg-white focus:outline-none"
        />
      </div>

      {/* Butang Tindakan Utama */}
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        <button
          type="button"
          disabled={auditLoading}
          onClick={onRunAudit}
          className="inline-flex items-center justify-center gap-2 rounded-lg bg-[#0f2744] px-4 py-2.5 text-xs font-bold text-white shadow-sm transition hover:bg-slate-800 disabled:opacity-60"
        >
          {auditLoading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <FileSearch className="h-4 w-4 text-amber-300" />
          )}
          Semak IP (20 Perkara Wajib)
        </button>
        <button
          type="button"
          disabled={draftLoading}
          onClick={onRunDraft}
          className="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-xs font-bold text-white shadow-sm transition hover:bg-blue-700 disabled:opacity-60"
        >
          {draftLoading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Play className="h-4 w-4" />
          )}
          Jana Fail IP &amp; Borang 114
        </button>
      </div>

      {/* Carian Teks Akta Sebenar (Boleh Lipat supaya panel kiri bersih) */}
      <div className="rounded-lg border border-slate-200 bg-slate-50 p-2.5">
        <button
          type="button"
          onClick={() => setShowRagPanel(!showRagPanel)}
          className="flex w-full items-center justify-between text-xs font-bold text-slate-800"
        >
          <span className="inline-flex items-center gap-1.5">
            <BookOpen className="h-4 w-4 text-teal-600" />
            Semak Teks Akta Sebenar (Okapi BM25 + ChromaDB)
          </span>
          <span className="text-[11px] font-semibold text-teal-700">
            {showRagPanel ? "Tutup" : "Buka Carian Akta"}
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
                placeholder="Cari seksyen akta (cth: Seksyen 36 sitaan, Peraturan 31 tifoid)..."
                className="flex-1 rounded-md border border-slate-300 bg-white px-2.5 py-1.5 text-xs text-slate-800 focus:border-teal-500 focus:outline-none"
              />
              <button
                type="button"
                disabled={ragLoading}
                onClick={() => onSearchRag(ragQuery)}
                className="inline-flex items-center gap-1 rounded-md bg-teal-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-teal-700 disabled:opacity-60"
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
                            className="rounded bg-slate-100 p-1 text-slate-600 hover:bg-slate-200"
                          >
                            <Copy className="h-3 w-3" />
                          </button>
                          <button
                            type="button"
                            onClick={() => setExpandedRagIdx(expanded ? null : idx)}
                            className="rounded bg-teal-50 px-1.5 py-0.5 text-[10px] font-semibold text-teal-700"
                          >
                            {expanded ? "Ringkas" : "Baca Penuh"}
                          </button>
                        </div>
                      </div>
                      <p className="mt-1 whitespace-pre-line text-[11px] leading-relaxed text-slate-600">
                        {expanded ? item.text : `${item.text.slice(0, 260)}${item.text.length > 260 ? "..." : ""}`}
                      </p>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
