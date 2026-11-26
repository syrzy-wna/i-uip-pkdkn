"use client";

import React, { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
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
import RichLegalText from "@/components/RichLegalText";
import SopQuickModal from "@/components/sop/SopQuickModal";
import type { IPAuditReport, RedactResponse } from "@/lib/types";

export interface AuditFixContext {
  sectionId: string;
  code: string;
  title: string;
  recommendation: string;
}

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
  onJumpToEditor: (sectionId?: string, fixContext?: AuditFixContext) => void;
  initialSubView?: "criteria" | "folder" | "privacy";
  authToken?: string | null;
}

type AuditTabView = "issues" | "all" | "folder" | "privacy";

const DEFAULT_FOLDER_INDEX = [
  { bahagian: "A", tajuk: "Kertas Minit, Izin Mendakwa TPR & Fakta Kes", status: "BELUM DISEMAK" },
  { bahagian: "B", tajuk: "Borang 114 (Pertuduhan) & Borang 143 (Pengaduan)", status: "BELUM DISEMAK" },
  { bahagian: "C", tajuk: "Notis S.32B / S.47, Kompaun & Kad AR Pos", status: "BELUM DISEMAK" },
  { bahagian: "D", tajuk: "Borang Sitaan (S.36) / Perintah S.11, Gambar & Sijil 90A", status: "BELUM DISEMAK" },
  { bahagian: "E", tajuk: "Rakaman Percakapan S.112 KTJ & Senarai Saksi", status: "BELUM DISEMAK" },
  { bahagian: "F", tajuk: "Carian SSM, Kad Kuasa & Laporan Makmal (S.19) / Entomologi", status: "BELUM DISEMAK" },
  { bahagian: "G", tajuk: "Diari Siasatan (Seksyen 119 KTJ)", status: "BELUM DISEMAK" },
];

export function mapCriterionToEditorSection(code: string): string {
  const c = (code || "").toUpperCase();
  if (c === "C01" || c === "C02" || c === "C14" || c === "C15") return "borang114";
  if (c === "C05" || c === "C06" || c === "C07") return "rakaman112";
  if (c === "C08") return "diari";
  if (c === "C09" || c === "C10" || c === "C11" || c === "C18") return "eksibit";
  if (c === "C12" || c === "C13") return "sijil90a";
  if (c === "C03" || c === "C04" || c === "C16" || c === "C17" || c === "C19" || c === "C20") {
    return "fakta";
  }
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
  authToken,
}: AuditPanelProps) {
  const [view, setView] = useState<AuditTabView>(
    initialSubView === "privacy" ? "privacy" : initialSubView === "folder" ? "folder" : "issues"
  );
  const [expandedCode, setExpandedCode] = useState<string | null>(null);
  const [modalSopCode, setModalSopCode] = useState<string | null>(null);

  useEffect(() => {
    if (initialSubView === "privacy") {
      setView("privacy");
    } else if (initialSubView === "folder") {
      setView("folder");
    } else {
      const totalIssues = report ? report.counts.GAGAL + report.counts.SEMAK : 0;
      setView(report && totalIssues === 0 ? "all" : "issues");
    }
    if (report) {
      const firstIssue = report.criteria_results.find((c) => c.status !== "LULUS");
      setExpandedCode(firstIssue ? firstIssue.code : null);
    }
  }, [initialSubView, report]);

  const priorityCodes = useMemo(() => {
    const map = new Map<string, string>();
    for (const q of report?.kuiri_tpr || []) {
      map.set(q.code, q.tahap || "KUIRI WAJIB");
    }
    return map;
  }, [report]);

  const sortedItems = useMemo(() => {
    if (!report) return [];
    const list =
      view === "issues"
        ? report.criteria_results.filter((c) => c.status !== "LULUS")
        : report.criteria_results;
    return [...list].sort((a, b) => {
      const aPri = priorityCodes.has(a.code) ? 0 : a.status === "GAGAL" ? 1 : a.status === "SEMAK" ? 2 : 3;
      const bPri = priorityCodes.has(b.code) ? 0 : b.status === "GAGAL" ? 1 : b.status === "SEMAK" ? 2 : 3;
      if (aPri !== bPri) return aPri - bPri;
      return a.code.localeCompare(b.code);
    });
  }, [report, view, priorityCodes]);

  if (!report) {
    return (
      <div className="mx-auto max-w-3xl space-y-4">
        {view === "privacy" ? (
          <div className="space-y-3">
            <button
              type="button"
              onClick={() => setView("issues")}
              className="inline-flex min-h-[44px] items-center text-xs font-bold text-[#0f2744] hover:underline"
            >
              ← Kembali ke 20 Semakan Pra-TPR
            </button>
            <RedactionPreview
              redaction={redaction}
              loading={redactLoading}
              onRunRedaction={onRunRedaction}
              hasCaseInput={hasCaseInput}
              onSwitchToInput={onSwitchToInput}
            />
          </div>
        ) : (
          <div className="space-y-4 rounded-2xl border border-dashed border-slate-300 bg-white p-6 text-center sm:p-8">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-100 text-[#0f2744]">
              <Scale className="h-6 w-6" />
            </div>
            <div className="space-y-1.5">
              <h3 className="text-base font-extrabold text-slate-900">
                20 Semakan Pra-TPR Belum Dijalankan
              </h3>
              <p className="mx-auto max-w-lg text-sm leading-relaxed text-slate-600">
                Sistem akan mengesan salah seksyen (cth. S.38, S.44, Akta 514), percanggahan tarikh, kekurangan Sijil 90A dan rantaian barang bukti sebelum fail dihantar kepada TPR.
              </p>
            </div>

            {activeCaseTitle && hasCaseInput && (
              <div className="mx-auto max-w-xl rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-xs text-slate-800">
                Bahan kes sedia: <strong>{activeCaseTitle}</strong>
              </div>
            )}

            <div className="flex flex-col items-center justify-center gap-2.5 sm:flex-row">
              {hasCaseInput ? (
                <button
                  type="button"
                  disabled={auditLoading}
                  onClick={onRunAudit}
                  className="inline-flex min-h-[46px] w-full items-center justify-center gap-2 rounded-xl bg-[#0f2744] px-6 py-2.5 text-sm font-extrabold text-white shadow-sm hover:bg-slate-800 disabled:opacity-60 sm:w-auto"
                >
                  {auditLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                  {auditLoading ? "Sedang menyemak..." : "Semak Pra-TPR Sekarang"}
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
                onClick={onLoadSampleCase}
                className="inline-flex min-h-[46px] w-full items-center justify-center gap-1.5 rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-xs font-bold text-slate-800 hover:bg-slate-50 sm:w-auto"
              >
                <FileText className="h-4 w-4 text-[#0f2744]" />
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
    <div className="mx-auto max-w-3xl space-y-4">
      {/* Kad Skor Ringkas + 1 CTA Utama */}
      <section className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="text-xs font-semibold text-slate-500">
              Keputusan 20 Semakan Pra-TPR ({report.akta_utama})
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
            className="inline-flex min-h-[46px] w-full items-center justify-center gap-2 rounded-xl bg-[#0f2744] px-5 py-2.5 text-sm font-extrabold text-white shadow-sm hover:bg-slate-800 disabled:opacity-60 sm:w-auto"
          >
            {draftLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowRight className="h-4 w-4" />}
            {draftLoading ? "Menyediakan Draf..." : "Baiki & Sunting Fail IP (.docx)"}
          </button>
        </div>

        {report.tpr_summary_notes.length > 0 && (
          <ul className="list-disc space-y-1 border-t border-slate-200 pl-5 pt-3 text-xs leading-relaxed text-slate-700 sm:text-sm">
            {report.tpr_summary_notes.map((note, idx) => (
              <li key={idx}>{note}</li>
            ))}
          </ul>
        )}

        {report.sop_audit_pra_tpr && (
          <div className="space-y-2.5 rounded-xl border border-indigo-200 bg-indigo-50/40 p-3.5 text-xs">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="font-extrabold text-indigo-950">
                Semakan SOP KKM Pra-TPR ({report.sop_audit_pra_tpr.lampiran_ks_wajib})
              </div>
              {report.sop_audit_pra_tpr.sops_dirujuk.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {report.sop_audit_pra_tpr.sops_dirujuk.map((s) => (
                    <button
                      key={s.sop_id}
                      type="button"
                      onClick={() => setModalSopCode(s.file_stem || s.sop_id)}
                      className="rounded-full bg-white px-2.5 py-0.5 text-[10px] font-bold text-indigo-800 ring-1 ring-indigo-300 transition hover:bg-indigo-100"
                    >
                      {s.sop_id} ↗
                    </button>
                  ))}
                </div>
              )}
            </div>

            {report.sop_audit_pra_tpr.butiran_lampiran_ks && (
              <div className="rounded-lg border border-indigo-200/80 bg-white px-3 py-2 text-[11px] leading-relaxed text-slate-700">
                <span className="font-bold text-indigo-950">Keperluan Lampiran K/S: </span>
                {report.sop_audit_pra_tpr.butiran_lampiran_ks}
              </div>
            )}

            {report.sop_audit_pra_tpr.dapatan_sop.length > 0 && (
              <div className="space-y-1.5">
                {report.sop_audit_pra_tpr.dapatan_sop.map((d, i) => {
                  const isCrit = d.status.includes("KRITIKAL");
                  const isWarn = d.status.includes("AMARAN");
                  return (
                    <div
                      key={i}
                      className="rounded-lg border border-slate-200/80 bg-white px-3 py-2"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-1.5">
                        <span className="font-bold text-slate-900">
                          {d.kategori} · <span className="font-semibold text-indigo-900">{d.rujukan_sop}</span>
                        </span>
                        <span
                          className={`rounded-full px-2 py-0.5 text-[10px] font-extrabold ${
                            isCrit
                              ? "bg-rose-100 text-rose-900"
                              : isWarn
                                ? "bg-amber-100 text-amber-950"
                                : "bg-emerald-100 text-emerald-900"
                          }`}
                        >
                          {d.status}
                        </span>
                      </div>
                      <p className="mt-1 leading-relaxed text-slate-700">{d.perincian}</p>
                    </div>
                  );
                })}
              </div>
            )}

            {report.sop_audit_pra_tpr.ulasan_pra_tpr && (
              <details className="rounded-lg border border-indigo-200 bg-white px-3 py-2">
                <summary className="cursor-pointer font-extrabold text-indigo-950">
                  Lihat Ulasan Penuh Juruaudit Pra-TPR (SOP KKM 2024)
                </summary>
                <div className="mt-2">
                  <RichLegalText
                    text={report.sop_audit_pra_tpr.ulasan_pra_tpr}
                    className="text-xs"
                    onOpenSop={(code) => setModalSopCode(code)}
                  />
                </div>
              </details>
            )}
          </div>
        )}

        {report.statutory_citations && report.statutory_citations.length > 0 && (
          <details className="rounded-xl border border-slate-200 bg-slate-50/70 px-3.5 py-2.5 text-xs">
            <summary className="cursor-pointer font-extrabold text-[#0f2744]">
              Rujukan Seksyen Akta Berkaitan ({report.statutory_citations.length})
            </summary>
            <div className="mt-2 space-y-2">
              {report.statutory_citations.map((cit, cIdx) => (
                <div
                  key={`${cit.akta_code}-${cit.section}-${cIdx}`}
                  className="rounded-lg border border-slate-200 bg-white p-2.5"
                >
                  <div className="font-bold text-[#0f2744]">
                    {cit.akta_code} • {cit.section}
                  </div>
                  <p className="mt-0.5 line-clamp-4 whitespace-pre-line leading-relaxed text-slate-700">
                    {cit.text}
                  </p>
                </div>
              ))}
            </div>
          </details>
        )}

        {/* 1 Bar Sub-Tab Tunggal */}
        <div className="flex gap-1.5 overflow-x-auto border-t border-slate-200 pt-3 no-scrollbar">
          {[
            { id: "issues" as AuditTabView, label: `Perlu Dibaiki (${issueCount})`, icon: AlertTriangle },
            { id: "all" as AuditTabView, label: `Semua (${report.criteria_results.length})`, icon: Scale },
            { id: "folder" as AuditTabView, label: "Susunan Fail A–G", icon: ClipboardList },
            {
              id: "privacy" as AuditTabView,
              label: `Perlindungan Data${redaction ? ` (${redaction.entities.length})` : ""}`,
              icon: Lock,
            },
          ].map((tab) => {
            const Icon = tab.icon;
            const active = view === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setView(tab.id)}
                className={`inline-flex min-h-[44px] shrink-0 items-center gap-1.5 rounded-xl px-3.5 py-2 text-xs font-bold transition ${
                  active
                    ? "bg-[#0f2744] text-white"
                    : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                }`}
              >
                <Icon className="h-3.5 w-3.5" />
                {tab.label}
              </button>
            );
          })}
        </div>
      </section>

      {view === "privacy" && (
        <RedactionPreview
          redaction={redaction}
          loading={redactLoading}
          onRunRedaction={onRunRedaction}
          hasCaseInput={hasCaseInput}
          onSwitchToInput={onSwitchToInput}
        />
      )}

      {view === "folder" && (
        <section className="space-y-3 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div>
            <h4 className="text-sm font-extrabold text-slate-900">
              Susunan Fail Kertas Siasatan Pejabat Kesihatan (Bahagian A – G)
            </h4>
            <p className="mt-0.5 text-xs text-slate-600">
              Semakan automatik kandungan minimum setiap bahagian fail sebelum dihantar kepada TPR.
            </p>
          </div>
          <div className="divide-y divide-slate-200">
            {folderItems.map((sec) => (
              <div
                key={sec.bahagian}
                className="flex flex-wrap items-center justify-between gap-2 py-3 text-sm"
              >
                <div className="flex items-center gap-3">
                  <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-[#0f2744] text-xs font-extrabold text-white">
                    {sec.bahagian}
                  </span>
                  <span className="font-medium text-slate-800">{sec.tajuk}</span>
                </div>
                <span
                  className={`shrink-0 rounded-full px-3 py-1 text-xs font-bold ${
                    sec.status === "LENGKAP"
                      ? "bg-emerald-100 text-emerald-800"
                      : sec.status.includes("KUIRI")
                        ? "bg-rose-100 text-rose-800"
                        : "bg-amber-100 text-amber-900"
                  }`}
                >
                  {sec.status}
                </span>
              </div>
            ))}
          </div>
        </section>
      )}

      {(view === "issues" || view === "all") && (
        <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          {sortedItems.length === 0 ? (
            <div className="p-6 text-center text-sm font-semibold text-emerald-900">
              Semua 20 semakan Pra-TPR telah lulus! Anda boleh terus muat turun fail Word di Langkah 3.
            </div>
          ) : (
            <div className="divide-y divide-slate-200">
              {sortedItems.map((item, idx) => {
                const isPass = item.status === "LULUS";
                const isFail = item.status === "GAGAL";
                const isExpanded = expandedCode === item.code;
                const isPriority = priorityCodes.has(item.code);
                const isPrivacyItem = item.code === "C20";
                return (
                  <div
                    key={item.code}
                    className={`border-l-4 ${
                      isFail
                        ? "border-l-rose-600"
                        : isPass
                          ? "border-l-emerald-600"
                          : "border-l-amber-500"
                    }`}
                  >
                    <button
                      type="button"
                      onClick={() => setExpandedCode(isExpanded ? null : item.code)}
                      className="flex min-h-[56px] w-full items-center justify-between gap-3 px-4 py-3.5 text-left transition hover:bg-slate-50"
                    >
                      <div className="flex min-w-0 items-start gap-2.5">
                        {isPass ? (
                          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
                        ) : isFail ? (
                          <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-600" />
                        ) : (
                          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
                        )}
                        <div className="min-w-0">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[11px] font-bold text-[#0f2744]">
                              {item.code}
                            </span>
                            <span className="text-sm font-bold text-slate-900">
                              {idx + 1}. {item.title}
                            </span>
                            {isPriority && !isPass && (
                              <span className="rounded-full bg-rose-100 px-2 py-0.5 text-xs font-bold text-rose-800">
                                Keutamaan TPR
                              </span>
                            )}
                          </div>
                          <div className="text-xs text-slate-500">{item.statute_ref}</div>
                        </div>
                      </div>

                      <div className="flex shrink-0 items-center gap-2">
                        <span
                          className={`rounded-full px-2.5 py-0.5 text-xs font-bold ${
                            isPass
                              ? "bg-emerald-100 text-emerald-800"
                              : isFail
                                ? "bg-rose-100 text-rose-800"
                                : "bg-amber-100 text-amber-900"
                          }`}
                        >
                          {item.status}
                        </span>
                        {isExpanded ? (
                          <ChevronUp className="h-4 w-4 text-slate-400" />
                        ) : (
                          <ChevronDown className="h-4 w-4 text-slate-400" />
                        )}
                      </div>
                    </button>

                    {isExpanded && (
                      <div className="space-y-3 border-t border-slate-100 bg-slate-50/70 px-4 py-3.5 text-sm text-slate-700">
                        <div>
                          <strong className="text-slate-900">Hasil Semakan: </strong>
                          {item.evidence_snippet}
                        </div>
                        {!isPass && (
                          <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white p-3">
                            <div className="min-w-0 flex-1 text-xs leading-relaxed sm:text-sm">
                              <strong className="text-slate-900">Tindakan Perlu Diambil: </strong>
                              {item.recommendation}
                            </div>
                            {isPrivacyItem ? (
                              <button
                                type="button"
                                onClick={() => setView("privacy")}
                                className="inline-flex min-h-[44px] shrink-0 items-center gap-1.5 rounded-xl bg-[#0f2744] px-3.5 py-2 text-xs font-bold text-white hover:bg-slate-800"
                              >
                                <Lock className="h-3.5 w-3.5" />
                                Lihat Perlindungan Data
                              </button>
                            ) : (
                              <button
                                type="button"
                                disabled={draftLoading}
                                onClick={() =>
                                  onJumpToEditor(mapCriterionToEditorSection(item.code), {
                                    sectionId: mapCriterionToEditorSection(item.code),
                                    code: item.code,
                                    title: item.title,
                                    recommendation: item.recommendation,
                                  })
                                }
                                className="inline-flex min-h-[44px] shrink-0 items-center gap-1.5 rounded-xl bg-[#0f2744] px-3.5 py-2 text-xs font-bold text-white hover:bg-slate-800 disabled:opacity-60"
                              >
                                {draftLoading ? (
                                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                ) : (
                                  <ArrowRight className="h-3.5 w-3.5" />
                                )}
                                {draftLoading ? "Menyediakan..." : "Baiki pada Draf"}
                              </button>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </section>
      )}

      <SopQuickModal
        sopCode={modalSopCode}
        authToken={authToken}
        onClose={() => setModalSopCode(null)}
      />
    </div>
  );
}
