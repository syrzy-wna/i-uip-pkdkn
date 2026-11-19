"use client";

import React, { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  ClipboardList,
  FileText,
  FolderOpen,
  Loader2,
  Lock,
  Scale,
  Sparkles,
  XCircle,
} from "lucide-react";
import RedactionPreview from "@/components/RedactionPreview";
import type { IPAuditReport, RedactResponse } from "@/lib/types";

interface AuditPanelProps {
  report: IPAuditReport | null;
  redaction: RedactResponse | null;
  redactLoading: boolean;
  onRunRedaction: () => void;
  hasCaseInput: boolean;
  activeCaseTitle?: string;
  auditLoading: boolean;
  draftLoading: boolean;
  onRunAudit: () => void;
  onSwitchToInput: () => void;
  onLoadSampleCase: () => void;
  onJumpToEditor: (sectionId?: string) => void;
  initialSubView?: "criteria" | "folder" | "privacy";
}

type StatusFilter = "ISSUES" | "SEMUA" | "GAGAL" | "SEMAK" | "LULUS";
type AuditSubView = "criteria" | "folder" | "privacy";

const DEFAULT_FOLDER_INDEX = [
  { bahagian: "A", tajuk: "Kertas Minit, Izin Mendakwa TPR & Fakta Kes", status: "BELUM DISEMAK" },
  { bahagian: "B", tajuk: "Borang 114 (Pertuduhan) & Borang 143 (Pengaduan)", status: "BELUM DISEMAK" },
  { bahagian: "C", tajuk: "Notis S.32B / S.47, Kompaun & Kad AR Pos", status: "BELUM DISEMAK" },
  { bahagian: "D", tajuk: "Borang Sitaan (S.36) / Perintah S.11, Gambar & Sijil 90A", status: "BELUM DISEMAK" },
  { bahagian: "E", tajuk: "Rakaman Percakapan S.112 KTJ & Senarai Saksi", status: "BELUM DISEMAK" },
  { bahagian: "F", tajuk: "Carian SSM, Kad Kuasa & Laporan Makmal (S.19) / Entomologi", status: "BELUM DISEMAK" },
  { bahagian: "G", tajuk: "Diari Siasatan (Seksyen 119 KTJ)", status: "BELUM DISEMAK" },
];

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
  redaction,
  redactLoading,
  onRunRedaction,
  hasCaseInput,
  activeCaseTitle,
  auditLoading,
  draftLoading,
  onRunAudit,
  onSwitchToInput,
  onLoadSampleCase,
  onJumpToEditor,
  initialSubView = "criteria",
}: AuditPanelProps) {
  const [subView, setSubView] = useState<AuditSubView>(initialSubView);
  const [filter, setFilter] = useState<StatusFilter>("ISSUES");

  useEffect(() => {
    setSubView(initialSubView);
  }, [initialSubView]);

  useEffect(() => {
    if (!report) return;
    const totalIssues = report.counts.GAGAL + report.counts.SEMAK;
    setFilter(totalIssues > 0 ? "ISSUES" : "SEMUA");
  }, [report]);

  const filtered = useMemo(() => {
    if (!report) return [];
    if (filter === "SEMUA") return report.criteria_results;
    if (filter === "ISSUES") {
      return report.criteria_results.filter((c) => c.status !== "LULUS");
    }
    return report.criteria_results.filter((c) => c.status === filter);
  }, [report, filter]);

  if (!report) {
    return (
      <div className="space-y-4">
        {subView === "privacy" ? (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <button
                type="button"
                onClick={() => setSubView("criteria")}
                className="text-xs font-bold text-blue-700 hover:underline"
              >
                ← Kembali ke Semakan 20 Kriteria
              </button>
            </div>
            <RedactionPreview
              redaction={redaction}
              loading={redactLoading}
              onRunRedaction={onRunRedaction}
              hasCaseInput={hasCaseInput}
              onSwitchToInput={onSwitchToInput}
            />
          </div>
        ) : (
          <div className="space-y-4 rounded-2xl border border-dashed border-slate-300 bg-slate-50/70 p-6 text-center sm:p-8">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-[#0f2744]/10 text-[#0f2744]">
              <Scale className="h-6 w-6" />
            </div>
            <div className="space-y-1">
              <h3 className="text-base font-extrabold text-slate-900">
                Semakan Kualiti Fail IP Pra-TPR (20 Perkara Wajib)
              </h3>
              <p className="mx-auto max-w-lg text-xs leading-relaxed text-slate-600">
                Sistem mengesan kesilapan seksyen (contoh: S.38, S.44, Akta 514), percanggahan tarikh, kekurangan Sijil 90A, dan kesempurnaan rantaian eksibit sebelum fail dihantar kepada TPR.
              </p>
            </div>

            {activeCaseTitle && hasCaseInput && (
              <div className="mx-auto max-w-xl rounded-xl border border-blue-200 bg-blue-50 px-3.5 py-2 text-xs text-blue-950">
                Bahan kes sedia: <strong>{activeCaseTitle}</strong>
              </div>
            )}

            <div className="flex flex-col items-center justify-center gap-2.5 sm:flex-row">
              {hasCaseInput ? (
                <button
                  type="button"
                  disabled={auditLoading}
                  onClick={onRunAudit}
                  className="inline-flex min-h-[44px] w-full items-center justify-center gap-2 rounded-xl bg-[#0f2744] px-6 py-2.5 text-sm font-extrabold text-white shadow-sm hover:bg-slate-800 disabled:opacity-60 sm:w-auto"
                >
                  {auditLoading ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Sparkles className="h-4 w-4 text-amber-300" />
                  )}
                  Semak 20 Kriteria Sekarang
                </button>
              ) : (
                <button
                  type="button"
                  onClick={onSwitchToInput}
                  className="inline-flex min-h-[44px] w-full items-center justify-center gap-2 rounded-xl bg-[#0f2744] px-6 py-2.5 text-sm font-extrabold text-white shadow-sm hover:bg-slate-800 sm:w-auto"
                >
                  <FolderOpen className="h-4 w-4 text-amber-300" />
                  Muat Naik Fail / Isi Fakta Kes
                </button>
              )}

              <button
                type="button"
                onClick={onLoadSampleCase}
                className="inline-flex min-h-[44px] w-full items-center justify-center gap-1.5 rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-xs font-bold text-slate-800 hover:bg-slate-100 sm:w-auto"
              >
                <FileText className="h-4 w-4 text-indigo-700" />
                Cuba Contoh Kes Sebenar
              </button>
            </div>
          </div>
        )}
      </div>
    );
  }

  const issueCount = report.counts.GAGAL + report.counts.SEMAK;
  const badgeClass =
    report.readiness_status.includes("SEDIA")
      ? "bg-emerald-100 text-emerald-900 border-emerald-300"
      : report.readiness_status.includes("DITOLAK") || report.readiness_status.includes("KRITIKAL")
        ? "bg-rose-100 text-rose-900 border-rose-300"
        : "bg-amber-100 text-amber-900 border-amber-300";

  const folderItems =
    report.ip_folder_checklist && report.ip_folder_checklist.length > 0
      ? report.ip_folder_checklist
      : DEFAULT_FOLDER_INDEX;

  return (
    <div className="space-y-4">
      {/* Sub-Navigasi 3 Tab Bersih Dalam Keputusan Semak IP */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 pb-2.5">
        <div className="flex gap-1.5 overflow-x-auto no-scrollbar">
          <button
            type="button"
            onClick={() => setSubView("criteria")}
            className={`inline-flex min-h-[38px] shrink-0 items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-bold transition ${
              subView === "criteria"
                ? "bg-[#0f2744] text-white"
                : "bg-slate-100 text-slate-700 hover:bg-slate-200"
            }`}
          >
            <Scale className="h-3.5 w-3.5" />
            Keputusan 20 Kriteria ({report.overall_score}%)
          </button>

          <button
            type="button"
            onClick={() => setSubView("folder")}
            className={`inline-flex min-h-[38px] shrink-0 items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-bold transition ${
              subView === "folder"
                ? "bg-[#0f2744] text-white"
                : "bg-slate-100 text-slate-700 hover:bg-slate-200"
            }`}
          >
            <ClipboardList className="h-3.5 w-3.5" />
            Susunan Fail A–G
          </button>

          <button
            type="button"
            onClick={() => setSubView("privacy")}
            className={`inline-flex min-h-[38px] shrink-0 items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-bold transition ${
              subView === "privacy"
                ? "bg-[#0f2744] text-white"
                : "bg-slate-100 text-slate-700 hover:bg-slate-200"
            }`}
          >
            <Lock className="h-3.5 w-3.5" />
            Privasi Data{redaction ? ` (${redaction.entities.length})` : ""}
          </button>
        </div>
      </div>

      {subView === "privacy" && (
        <RedactionPreview
          redaction={redaction}
          loading={redactLoading}
          onRunRedaction={onRunRedaction}
          hasCaseInput={hasCaseInput}
          onSwitchToInput={onSwitchToInput}
        />
      )}

      {subView === "folder" && (
        <div className="space-y-2.5 rounded-xl border border-slate-200 bg-white p-4">
          <div className="text-xs font-extrabold text-slate-900">
            Semakan Susunan Fail Kertas Siasatan PKD (Bahagian A – G)
          </div>
          <p className="text-xs text-slate-500">
            Semakan automatik kandungan minimum setiap bahagian fail sebelum dihantar ke KPPKP / TPR.
          </p>
          <div className="divide-y divide-slate-100 pt-1">
            {folderItems.map((sec) => (
              <div
                key={sec.bahagian}
                className="flex flex-wrap items-center justify-between gap-2 py-2.5 text-xs"
              >
                <div className="flex items-center gap-2.5">
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-[#0f2744] text-xs font-extrabold text-white">
                    {sec.bahagian}
                  </span>
                  <span className="font-medium text-slate-800">{sec.tajuk}</span>
                </div>
                <span
                  className={`shrink-0 rounded-full px-2.5 py-0.5 text-[11px] font-bold ${
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
        </div>
      )}

      {subView === "criteria" && (
        <div className="space-y-4">
          {/* Kad Skor Ringkasan Bersih */}
          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="text-xs font-semibold text-slate-500">
                  Skor Kesediaan Pra-TPR ({report.akta_utama})
                </div>
                <div className="mt-1 flex flex-wrap items-center gap-2.5">
                  <span className="text-3xl font-extrabold text-slate-900">
                    {report.overall_score}%
                  </span>
                  <span className={`rounded-full border px-3 py-1 text-xs font-bold ${badgeClass}`}>
                    {report.readiness_status}
                  </span>
                </div>
              </div>

              <button
                type="button"
                disabled={draftLoading}
                onClick={() => onJumpToEditor("borang114")}
                className="inline-flex min-h-[42px] items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-xs font-extrabold text-white shadow-sm hover:bg-blue-700 disabled:opacity-60"
              >
                {draftLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <ArrowRight className="h-4 w-4" />
                )}
                {draftLoading ? "Membuka Editor..." : "Baiki & Bina Fail IP (.docx)"}
              </button>
            </div>

            {report.tpr_summary_notes.length > 0 && (
              <ul className="mt-3 list-disc space-y-1 border-t border-slate-100 pl-5 pt-3 text-xs text-slate-700">
                {report.tpr_summary_notes.map((note, idx) => (
                  <li key={idx}>{note}</li>
                ))}
              </ul>
            )}

            {report.kuiri_tpr && report.kuiri_tpr.length > 0 && (
              <div className="mt-3 rounded-xl border border-rose-200 border-l-4 border-l-rose-600 bg-rose-50/40 p-3 space-y-2">
                <div className="text-xs font-extrabold text-rose-950">
                  Kuiri Keutamaan Untuk Diselesaikan ({report.kuiri_tpr.length} Isu)
                </div>
                <div className="space-y-2">
                  {report.kuiri_tpr.map((q) => (
                    <div
                      key={q.code}
                      className="flex flex-wrap items-start justify-between gap-2 rounded-lg bg-white p-2.5 text-xs ring-1 ring-rose-200/70"
                    >
                      <div className="space-y-0.5">
                        <div className="flex flex-wrap items-center gap-1.5">
                          <span
                            className={`rounded px-1.5 py-0.5 text-[11px] font-bold ${
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
                        <div className="text-xs text-slate-600">{q.tindakan_io}</div>
                      </div>
                      <button
                        type="button"
                        disabled={draftLoading}
                        onClick={() => onJumpToEditor(mapCriterionToEditorSection(q.code))}
                        className="inline-flex shrink-0 items-center gap-1 rounded-lg bg-blue-50 px-2.5 py-1.5 text-xs font-bold text-blue-700 hover:bg-blue-100"
                      >
                        Baiki Isu Ini <ArrowRight className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* 1 Bar Penapis Tunggal (Lalai Tunjuk Isu Dahulu supaya Tak Penuh Skrin) */}
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-xs font-extrabold text-slate-700">
              Senarai Kriteria IP ({filtered.length} dipaparkan)
            </span>
            <div className="flex gap-1 overflow-x-auto rounded-xl bg-slate-100 p-1 no-scrollbar">
              {[
                { id: "ISSUES" as StatusFilter, label: `Perlu Baiki (${issueCount})` },
                { id: "GAGAL" as StatusFilter, label: `Gagal (${report.counts.GAGAL})` },
                { id: "SEMAK" as StatusFilter, label: `Semak (${report.counts.SEMAK})` },
                { id: "LULUS" as StatusFilter, label: `Lulus (${report.counts.LULUS})` },
                { id: "SEMUA" as StatusFilter, label: "Semua (20)" },
              ].map((tab) => (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setFilter(tab.id)}
                  className={`shrink-0 rounded-lg px-2.5 py-1.5 text-xs font-bold transition ${
                    filter === tab.id
                      ? "bg-white text-[#0f2744] shadow-sm"
                      : "text-slate-600 hover:text-slate-900"
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          </div>

          {filtered.length === 0 ? (
            <div className="rounded-xl border border-emerald-200 bg-emerald-50/50 p-5 text-center text-xs font-semibold text-emerald-900">
              Tiada isu dalam kategori ini — semua kriteria berkaitan telah lulus!
            </div>
          ) : (
            <div className="space-y-2.5">
              {filtered.map((item) => {
                const isPass = item.status === "LULUS";
                const isFail = item.status === "GAGAL";
                return (
                  <div
                    key={item.code}
                    className={`rounded-xl border border-slate-200 border-l-4 bg-white p-3.5 ${
                      isFail
                        ? "border-l-rose-600"
                        : isPass
                          ? "border-l-emerald-600"
                          : "border-l-amber-500"
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
                          <div className="text-xs font-extrabold text-slate-900">
                            {item.code}: {item.title}
                          </div>
                          <div className="text-[11px] text-slate-500">{item.statute_ref}</div>
                        </div>
                      </div>

                      <span
                        className={`rounded-full px-2.5 py-0.5 text-[11px] font-bold ${
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

                    <div className="mt-2.5 space-y-1.5 text-xs text-slate-700">
                      <div>
                        <strong className="text-slate-900">Penemuan: </strong>
                        {item.evidence_snippet}
                      </div>
                      {!isPass && (
                        <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-slate-50 px-3 py-2">
                          <div>
                            <strong className="text-slate-900">Tindakan IO: </strong>
                            {item.recommendation}
                          </div>
                          <button
                            type="button"
                            onClick={() => onJumpToEditor(mapCriterionToEditorSection(item.code))}
                            className="inline-flex shrink-0 items-center gap-1 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-bold text-white hover:bg-blue-700"
                          >
                            Baiki <ArrowRight className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
