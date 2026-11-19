"use client";

import React, { useMemo, useState } from "react";
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  FileText,
  FolderOpen,
  Loader2,
  Scale,
  ShieldAlert,
  Sparkles,
  XCircle,
} from "lucide-react";
import type { IPAuditReport } from "@/lib/types";

interface AuditPanelProps {
  report: IPAuditReport | null;
  hasCaseInput: boolean;
  activeCaseTitle?: string;
  auditLoading: boolean;
  draftLoading: boolean;
  onRunAudit: () => void;
  onSwitchToInput: () => void;
  onLoadSampleCase: () => void;
  onJumpToEditor: (sectionId?: string) => void;
}

type StatusFilter = "SEMUA" | "GAGAL" | "SEMAK" | "LULUS";

function mapCriterionToEditorSection(code: string): string {
  const c = (code || "").toUpperCase();
  if (c === "C06" || c === "C07" || c === "C08" || c === "C14" || c === "C15") return "borang114";
  if (c === "C12") return "sijil90a";
  if (c === "C10" || c === "C13") return "rakaman112";
  if (c === "C09" || c === "C11") return "eksibit";
  if (c === "C17") return "diari";
  if (c === "C01" || c === "C02" || c === "C03" || c === "C04" || c === "C05") return "fakta";
  return "borang114";
}

export default function AuditPanel({
  report,
  hasCaseInput,
  activeCaseTitle,
  auditLoading,
  draftLoading,
  onRunAudit,
  onSwitchToInput,
  onLoadSampleCase,
  onJumpToEditor,
}: AuditPanelProps) {
  const [filter, setFilter] = useState<StatusFilter>("SEMUA");

  const filtered = useMemo(() => {
    if (!report) return [];
    if (filter === "SEMUA") return report.criteria_results;
    return report.criteria_results.filter((c) => c.status === filter);
  }, [report, filter]);

  if (!report) {
    return (
      <div className="space-y-4 rounded-xl border border-dashed border-slate-300 bg-slate-50/80 p-5 sm:p-7">
        <div className="flex flex-col items-center text-center">
          <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-[#0f2744]/10 text-[#0f2744]">
            <Scale className="h-6 w-6" />
          </div>
          <h3 className="text-sm font-extrabold text-slate-900 sm:text-base">
            Semakan Kualiti Kertas Siasatan Pra-TPR (20 Perkara Wajib)
          </h3>
          <p className="mt-1 max-w-lg text-xs leading-relaxed text-slate-600">
            Kesan kesilapan seksyen (contoh: S.38/S.44/Akta 514), percanggahan tarikh, kekurangan Sijil 90A, dan kesempurnaan rantaian eksibit sebelum dihantar kepada TPR.
          </p>
        </div>

        <div className="mx-auto grid max-w-2xl grid-cols-1 gap-2 text-left text-xs sm:grid-cols-3">
          <div className="rounded-lg border border-slate-200 bg-white p-3">
            <div className="font-extrabold text-[#0f2744]">📄 Fail PDF / Word IP</div>
            <p className="mt-0.5 text-[11px] text-slate-500">Semak keseluruhan dokumen IP yang sudah siap</p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-white p-3">
            <div className="font-extrabold text-[#0f2744]">📸 Gambar Bukti / SSM</div>
            <p className="mt-0.5 text-[11px] text-slate-500">Ekstrak teks foto &amp; kesan lompang bukti</p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-white p-3">
            <div className="font-extrabold text-[#0f2744]">📝 Catatan Operasi</div>
            <p className="mt-0.5 text-[11px] text-slate-500">Semak draf awal PPKP sebelum fail dibuka</p>
          </div>
        </div>

        {activeCaseTitle && hasCaseInput && (
          <div className="mx-auto max-w-xl rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-center text-xs text-blue-900">
            Bahan kes sedia: <strong>{activeCaseTitle}</strong>
          </div>
        )}

        <div className="flex flex-col items-center justify-center gap-2 sm:flex-row sm:flex-wrap">
          {hasCaseInput ? (
            <button
              type="button"
              disabled={auditLoading}
              onClick={onRunAudit}
              className="inline-flex min-h-[44px] w-full items-center justify-center gap-2 rounded-xl bg-[#0f2744] px-5 py-2.5 text-xs font-extrabold text-white shadow-sm hover:bg-slate-800 disabled:opacity-60 sm:w-auto"
            >
              {auditLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Sparkles className="h-4 w-4 text-amber-300" />
              )}
              Jalankan Semakan 20 Kriteria Sekarang
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
            onClick={onLoadSampleCase}
            className="inline-flex min-h-[44px] w-full items-center justify-center gap-1.5 rounded-xl border border-indigo-200 bg-indigo-50 px-4 py-2.5 text-xs font-bold text-indigo-800 hover:bg-indigo-100 sm:w-auto"
          >
            <FileText className="h-3.5 w-3.5" />
            Cuba Contoh Kes Sebenar
          </button>
        </div>
      </div>
    );
  }

  const badgeClass =
    report.readiness_status.includes("SEDIA")
      ? "bg-emerald-100 text-emerald-800 border-emerald-300"
      : report.readiness_status.includes("DITOLAK") || report.readiness_status.includes("KRITIKAL")
        ? "bg-rose-100 text-rose-800 border-rose-300"
        : "bg-amber-100 text-amber-800 border-amber-300";

  const toggleFilter = (target: Exclude<StatusFilter, "SEMUA">) => {
    setFilter((prev) => (prev === target ? "SEMUA" : target));
  };

  return (
    <div className="space-y-4">
      {/* Kad Skor Ringkasan */}
      <div className="rounded-xl border border-slate-200 bg-slate-50 p-3.5 sm:p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              Keputusan Semakan Pra-TPR ({report.akta_utama})
            </div>
            <div className="mt-1 flex flex-wrap items-center gap-3">
              <span className="text-3xl font-extrabold text-slate-900">
                {report.overall_score}%
              </span>
              <span className={`rounded-full border px-3 py-1 text-xs font-bold ${badgeClass}`}>
                {report.readiness_status}
              </span>
            </div>
          </div>

          {/* 3 Kad Skor Boleh Klik untuk Terus Tapis */}
          <div className="grid grid-cols-3 gap-2 w-full sm:w-auto">
            <button
              type="button"
              onClick={() => toggleFilter("LULUS")}
              title="Klik untuk tapis kriteria LULUS sahaja"
              className={`rounded-lg bg-emerald-50 px-3 py-2 text-center ring-1 transition hover:bg-emerald-100 ${
                filter === "LULUS" ? "ring-2 ring-emerald-600 shadow-sm" : "ring-emerald-200"
              }`}
            >
              <div className="text-lg font-extrabold text-emerald-700">{report.counts.LULUS}</div>
              <div className="text-[10px] font-bold text-emerald-800">LULUS</div>
            </button>
            <button
              type="button"
              onClick={() => toggleFilter("SEMAK")}
              title="Klik untuk tapis kriteria SEMAK sahaja"
              className={`rounded-lg bg-amber-50 px-3 py-2 text-center ring-1 transition hover:bg-amber-100 ${
                filter === "SEMAK" ? "ring-2 ring-amber-600 shadow-sm" : "ring-amber-200"
              }`}
            >
              <div className="text-lg font-extrabold text-amber-700">{report.counts.SEMAK}</div>
              <div className="text-[10px] font-bold text-amber-800">SEMAK</div>
            </button>
            <button
              type="button"
              onClick={() => toggleFilter("GAGAL")}
              title="Klik untuk tapis kriteria GAGAL sahaja"
              className={`rounded-lg bg-rose-50 px-3 py-2 text-center ring-1 transition hover:bg-rose-100 ${
                filter === "GAGAL" ? "ring-2 ring-rose-600 shadow-sm" : "ring-rose-200"
              }`}
            >
              <div className="text-lg font-extrabold text-rose-700">{report.counts.GAGAL}</div>
              <div className="text-[10px] font-bold text-rose-800">GAGAL</div>
            </button>
          </div>
        </div>

        {/* Teguran Semakan */}
        <div className="mt-3 rounded-lg border border-slate-200 bg-white p-3 text-xs">
          <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-1.5 font-bold text-slate-800">
              <ShieldAlert className="h-4 w-4 text-blue-600" />
              <span>Ringkasan Teguran untuk Pegawai Penyiasat (IO)</span>
            </div>
            <button
              type="button"
              disabled={draftLoading}
              onClick={() => onJumpToEditor("borang114")}
              className="inline-flex min-h-[38px] items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-bold text-white shadow-sm hover:bg-blue-700 disabled:opacity-60"
            >
              {draftLoading ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <ArrowRight className="h-3.5 w-3.5" />
              )}
              {draftLoading ? "Sedang Membuka Editor..." : "Baiki Dalam Editor IP"}
            </button>
          </div>
          <ul className="list-disc space-y-1 pl-4 text-[11px] text-slate-600">
            {report.tpr_summary_notes.map((note, idx) => (
              <li key={idx}>{note}</li>
            ))}
          </ul>
        </div>

        {/* Senarai Kuiri Biasa TPR / UIP */}
        {report.kuiri_tpr && report.kuiri_tpr.length > 0 && (
          <div className="mt-3 rounded-lg border border-rose-200 bg-rose-50/60 p-3 text-xs">
            <div className="mb-2 font-bold text-rose-900">
              Senarai Kuiri Yang Perlu IO Selesaikan ({report.kuiri_tpr.length} Isu)
            </div>
            <div className="space-y-2">
              {report.kuiri_tpr.map((q) => (
                <div key={q.code} className="rounded-lg bg-white p-2.5 ring-1 ring-rose-200/80">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex flex-wrap items-center gap-1.5">
                      <span
                        className={`rounded px-1.5 py-0.5 text-[9px] font-bold ${
                          q.tahap === "KUIRI WAJIB"
                            ? "bg-rose-100 text-rose-800"
                            : "bg-amber-100 text-amber-800"
                        }`}
                      >
                        {q.tahap}
                      </span>
                      <span className="font-bold text-slate-900">
                        {q.code}: {q.isu}
                      </span>
                    </div>
                    <button
                      type="button"
                      disabled={draftLoading}
                      onClick={() => onJumpToEditor(mapCriterionToEditorSection(q.code))}
                      className="inline-flex items-center gap-1 rounded bg-blue-50 px-2 py-1 text-[11px] font-bold text-blue-700 hover:bg-blue-100"
                    >
                      Baiki Isu Ini <ArrowRight className="h-3 w-3" />
                    </button>
                  </div>
                  <div className="mt-1 text-[11px] text-slate-700">
                    <strong>Tindakan IO:</strong> {q.tindakan_io}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Penapis 20 Perkara */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-xs font-bold text-slate-700">
          Senarai Semak 20 Kriteria Asas IP ({filtered.length} dipaparkan)
        </span>
        <div className="grid w-full grid-cols-4 gap-1 rounded-lg bg-slate-100 p-1 sm:w-auto">
          {(["SEMUA", "GAGAL", "SEMAK", "LULUS"] as StatusFilter[]).map((st) => (
            <button
              key={st}
              type="button"
              onClick={() => setFilter(st)}
              className={`min-h-[38px] rounded-md px-2.5 py-1 text-[11px] font-bold transition sm:min-h-0 ${
                filter === st
                  ? "bg-white text-slate-900 shadow-sm"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      {/* Kad Setiap Perkara */}
      <div className="space-y-2.5">
        {filtered.map((item) => {
          const isPass = item.status === "LULUS";
          const isFail = item.status === "GAGAL";
          const scorePct = Math.round(item.calibrated_score * 100);
          const thresholdPct = Math.round(item.threshold * 100);

          return (
            <div
              key={item.code}
              className={`rounded-lg border p-3 ${
                isFail
                  ? "border-rose-200 bg-rose-50/40"
                  : isPass
                    ? "border-emerald-200 bg-white"
                    : "border-amber-200 bg-amber-50/30"
              }`}
            >
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="flex items-start gap-2">
                  {isPass ? (
                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
                  ) : isFail ? (
                    <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-600" />
                  ) : (
                    <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
                  )}
                  <div>
                    <div className="flex flex-wrap items-center gap-1.5">
                      <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] font-bold text-white">
                        {item.code}
                      </span>
                      <span className="text-xs font-bold text-slate-900">{item.title}</span>
                      <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-600">
                        {item.category}
                      </span>
                    </div>
                    <div className="mt-0.5 text-[11px] text-slate-500">
                      Rujukan: {item.statute_ref}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-[11px] font-semibold text-slate-600">
                    Markah: <strong>{scorePct}%</strong> (Lulus {thresholdPct}%)
                  </span>
                  <span
                    className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${
                      isPass
                        ? "bg-emerald-100 text-emerald-800"
                        : isFail
                          ? "bg-rose-100 text-rose-800"
                          : "bg-amber-100 text-amber-800"
                    }`}
                  >
                    {item.status}
                  </span>
                </div>
              </div>

              <div className="relative mt-2 h-2 w-full overflow-hidden rounded-full bg-slate-200">
                <div
                  className={`h-full rounded-full ${
                    isPass ? "bg-emerald-500" : isFail ? "bg-rose-500" : "bg-amber-500"
                  }`}
                  style={{ width: `${scorePct}%` }}
                />
                <div
                  title={`Markah Lulus: ${thresholdPct}%`}
                  className="absolute top-0 h-full w-0.5 bg-slate-900"
                  style={{ left: `${thresholdPct}%` }}
                />
              </div>

              <div className="mt-2 grid grid-cols-1 gap-1.5 text-[11px] sm:grid-cols-2">
                <div className="rounded bg-slate-50 p-2 text-slate-700 ring-1 ring-slate-200/70">
                  <span className="font-semibold text-slate-900">Penemuan dalam IP: </span>
                  {item.evidence_snippet}
                </div>
                <div
                  className={`rounded p-2 ring-1 ${
                    isPass
                      ? "bg-emerald-50/50 text-emerald-900 ring-emerald-200/70"
                      : "bg-amber-50/70 text-amber-950 ring-amber-200/80"
                  }`}
                >
                  <span className="font-semibold">Tindakan IO: </span>
                  {item.recommendation}
                  {!isPass && (
                    <button
                      type="button"
                      onClick={() => onJumpToEditor(mapCriterionToEditorSection(item.code))}
                      className="mt-1.5 inline-flex items-center gap-1 rounded bg-white px-2 py-0.5 text-[10px] font-bold text-blue-700 ring-1 ring-blue-200 hover:bg-blue-50"
                    >
                      Baiki bahagian ini dalam Editor <ArrowRight className="h-3 w-3" />
                    </button>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
