"use client";

import React, { useMemo, useState } from "react";
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Scale,
  ShieldAlert,
  XCircle,
} from "lucide-react";
import type { IPAuditReport } from "@/lib/types";

interface AuditPanelProps {
  report: IPAuditReport | null;
  onJumpToEditor: () => void;
}

type StatusFilter = "SEMUA" | "GAGAL" | "SEMAK" | "LULUS";

export default function AuditPanel({ report, onJumpToEditor }: AuditPanelProps) {
  const [filter, setFilter] = useState<StatusFilter>("SEMUA");

  const filtered = useMemo(() => {
    if (!report) return [];
    if (filter === "SEMUA") return report.criteria_results;
    return report.criteria_results.filter((c) => c.status === filter);
  }, [report, filter]);

  if (!report) {
    return (
      <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-slate-50/70 p-10 text-center">
        <Scale className="mb-3 h-10 w-10 text-slate-400" />
        <h3 className="text-sm font-bold text-slate-700">
          Belum Ada Keputusan Semakan Pra-TPR
        </h3>
        <p className="mt-1 max-w-md text-xs text-slate-500">
          Pilih kes dalam Daftar PKD atau muat naik PDF Kertas Siasatan di sebelah kiri,
          kemudian tekan <strong>Semak IP (20 Perkara Wajib)</strong>.
        </p>
      </div>
    );
  }

  const badgeClass =
    report.readiness_status.includes("SEDIA")
      ? "bg-emerald-100 text-emerald-800 border-emerald-300"
      : report.readiness_status.includes("DITOLAK") || report.readiness_status.includes("KRITIKAL")
        ? "bg-rose-100 text-rose-800 border-rose-300"
        : "bg-amber-100 text-amber-800 border-amber-300";

  return (
    <div className="space-y-4">
      {/* Kad Skor Ringkasan */}
      <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              Keputusan Semakan Pra-TPR ({report.akta_utama})
            </div>
            <div className="mt-1 flex flex-wrap items-center gap-3">
              <span className="text-3xl font-extrabold text-slate-900">
                {report.overall_score}%
              </span>
              <span
                className={`rounded-full border px-3 py-1 text-xs font-bold ${badgeClass}`}
              >
                {report.readiness_status}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <div className="rounded-lg bg-emerald-50 px-3 py-2 text-center ring-1 ring-emerald-200">
              <div className="text-lg font-bold text-emerald-700">
                {report.counts.LULUS}
              </div>
              <div className="text-[10px] font-semibold text-emerald-800">LULUS</div>
            </div>
            <div className="rounded-lg bg-amber-50 px-3 py-2 text-center ring-1 ring-amber-200">
              <div className="text-lg font-bold text-amber-700">
                {report.counts.SEMAK}
              </div>
              <div className="text-[10px] font-semibold text-amber-800">SEMAK</div>
            </div>
            <div className="rounded-lg bg-rose-50 px-3 py-2 text-center ring-1 ring-rose-200">
              <div className="text-lg font-bold text-rose-700">
                {report.counts.GAGAL}
              </div>
              <div className="text-[10px] font-semibold text-rose-800">GAGAL</div>
            </div>
          </div>
        </div>

        {/* Teguran Semakan */}
        <div className="mt-3 rounded-lg border border-slate-200 bg-white p-2.5 text-xs">
          <div className="mb-1 flex items-center justify-between">
            <div className="flex items-center gap-1.5 font-bold text-slate-800">
              <ShieldAlert className="h-3.5 w-3.5 text-blue-600" />
              <span>Ringkasan Teguran untuk Pegawai Penyiasat (IO)</span>
            </div>
            <button
              type="button"
              onClick={onJumpToEditor}
              className="inline-flex items-center gap-1 rounded bg-blue-50 px-2 py-1 text-[11px] font-bold text-blue-700 hover:bg-blue-100"
            >
              Baiki Dalam Editor IP <ArrowRight className="h-3 w-3" />
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
          <div className="mt-3 rounded-lg border border-rose-200 bg-rose-50/60 p-2.5 text-xs">
            <div className="mb-1.5 font-bold text-rose-900">
              Senarai Kuiri Yang Perlu IO Selesaikan ({report.kuiri_tpr.length} Isu)
            </div>
            <div className="space-y-1.5">
              {report.kuiri_tpr.map((q) => (
                <div key={q.code} className="rounded bg-white p-2 ring-1 ring-rose-200/70">
                  <div className="flex items-center gap-1.5">
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
                  <div className="mt-0.5 text-[11px] text-slate-700">
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
        <div className="flex gap-1 rounded-lg bg-slate-100 p-1">
          {(["SEMUA", "GAGAL", "SEMAK", "LULUS"] as StatusFilter[]).map((st) => (
            <button
              key={st}
              type="button"
              onClick={() => setFilter(st)}
              className={`rounded-md px-2.5 py-1 text-[11px] font-bold transition ${
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
              className={`rounded-lg border p-3 transition ${
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
                      <span className="text-xs font-bold text-slate-900">
                        {item.title}
                      </span>
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
                    isPass
                      ? "bg-emerald-500"
                      : isFail
                        ? "bg-rose-500"
                        : "bg-amber-500"
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
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
