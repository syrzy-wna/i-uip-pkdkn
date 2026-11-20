"use client";

import React, { useEffect, useRef, useState } from "react";
import {
  AlertTriangle,
  ArrowRightCircle,
  BookOpen,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  ClipboardCheck,
  ClipboardList,
  Copy,
  Gavel,
  Loader2,
  MessageSquareQuote,
  Search,
  ShieldAlert,
  Sparkles,
  Zap,
} from "lucide-react";
import { consultUipAdvisor, fetchAdvisorScenarios } from "@/lib/api";
import type {
  AdvisorConsultResult,
  AdvisorScenarioItem,
  OfficerProfile,
} from "@/lib/types";

interface UIPAdvisorPanelProps {
  aktaUtama: string;
  authToken: string | null;
  officer: OfficerProfile | null;
  onApplyToCaseBuilder: (draftText: string, aktaDisyorkan: string, bukaIp: boolean) => void;
}

type AdvisorResultTab = "sop" | "charges" | "statutes";

const QUICK_CHIPS = [
  "Budak sekolah hisap vape di tepi jalan",
  "Restoran kotor ada najis tikus & tiada tifoid",
  "Kedai pamer vape secara terbuka di kaunter",
];

export default function UIPAdvisorPanel({
  authToken,
  officer,
  onApplyToCaseBuilder,
}: UIPAdvisorPanelProps) {
  const [question, setQuestion] = useState("");
  const [aktaFilter, setAktaFilter] = useState<string>("Semua");
  const [scenarios, setScenarios] = useState<AdvisorScenarioItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [deepLoading, setDeepLoading] = useState(false);
  const [copiedSummary, setCopiedSummary] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AdvisorConsultResult | null>(null);
  const [showLibrary, setShowLibrary] = useState(false);
  const [resultTab, setResultTab] = useState<AdvisorResultTab>("sop");
  const resultRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    fetchAdvisorScenarios()
      .then(setScenarios)
      .catch(() => setScenarios([]));
  }, []);

  const handleConsult = async (
    customQuestion?: string,
    scenarioId?: string,
    forceAi = false
  ) => {
    const q = (customQuestion ?? question).trim();
    if (!q && !scenarioId) {
      setError("Sila taip situasi kesalahan atau pilih daripada pustaka situasi lazim.");
      return;
    }
    if (forceAi) setDeepLoading(true);
    else setLoading(true);
    setError(null);
    setCopiedSummary(false);

    try {
      const res = await consultUipAdvisor({
        question: q || "Rujuk templat situasi ini",
        aktaHint: aktaFilter,
        scenarioId,
        useAi: forceAi,
        authToken,
        officerProfile: officer,
      });
      setResult(res);
      setResultTab("sop");
      setShowLibrary(false);
      window.setTimeout(() => {
        resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 90);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gagal mendapatkan nasihat pakar UIP.");
    } finally {
      setLoading(false);
      setDeepLoading(false);
    }
  };

  const handleCopySummary = () => {
    if (!result) return;
    const primary = result.cadangan_pertuduhan[0];
    const text = [
      `RUJUKAN UIP KKM: ${result.tajuk_nasihat} (${result.akta_disyorkan})`,
      `KEPUTUSAN: ${result.keputusan_tindakan}`,
      primary ? `CAJ KESALAHAN: ${primary.seksyen_kesalahan}` : "",
      primary ? `HUKUMAN: ${primary.seksyen_hukuman} (${primary.hukuman_maksimum})` : "",
      `SOP LAPANGAN:\n${result.sop_lapangan.map((s, i) => `${i + 1}. ${s}`).join("\n")}`,
      `EKSIBIT WAJIB:\n${result.eksibit_wajib.map((e) => `- ${e}`).join("\n")}`,
    ]
      .filter(Boolean)
      .join("\n\n");
    navigator.clipboard?.writeText(text);
    setCopiedSummary(true);
    setTimeout(() => setCopiedSummary(false), 2000);
  };

  const filteredScenarios =
    aktaFilter === "Semua"
      ? scenarios
      : scenarios.filter((s) => s.akta_utama === aktaFilter);

  const primaryCharge = result?.cadangan_pertuduhan?.[0];

  return (
    <div className="mx-auto max-w-5xl space-y-4">
      {/* 1. KOTAK SOALAN TENANG & BERPUSAT */}
      <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-6">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-700">
              <MessageSquareQuote className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-sm font-extrabold text-slate-900 sm:text-base">
                Tanya Pakar UIP (Seksyen &amp; SOP Lapangan)
              </h2>
              <p className="text-xs text-slate-500">
                Ceritakan situasi yang anda jumpa di lokasi untuk semak seksyen caj, had kompaun dan langkah SOP.
              </p>
            </div>
          </div>

          <select
            aria-label="Tapis Akta KKM"
            value={aktaFilter}
            onChange={(e) => setAktaFilter(e.target.value)}
            className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-base font-semibold text-slate-800 sm:w-auto sm:text-sm"
          >
            <option value="Semua">Semua Akta KKM</option>
            <option value="Akta 852">Akta 852 (Merokok/Vape)</option>
            <option value="Akta 281">Akta 281 &amp; PPKM 2009</option>
            <option value="Akta 154">Akta 154 (Aedes)</option>
            <option value="Akta 342">Akta 342 (Tibi/Berjangkit)</option>
          </select>
        </div>

        <div className="mt-3 space-y-3">
          <textarea
            rows={3}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
                handleConsult();
              }
            }}
            placeholder="Contoh: Ada budak sekolah hisap rokok di tepi jalan, nak guna seksyen mana dan apa prosedur?"
            className="w-full rounded-xl border border-slate-300 bg-slate-50/40 p-3 text-base leading-relaxed text-slate-900 transition focus:border-indigo-500 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-100 sm:text-sm"
          />

          {/* Cip Pantas + Butang Pustaka */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-semibold text-slate-500">Contoh pantas:</span>
            {QUICK_CHIPS.map((chip) => (
              <button
                key={chip}
                type="button"
                onClick={() => {
                  setQuestion(chip);
                  handleConsult(chip);
                }}
                className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-700 transition hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-900"
              >
                {chip}
              </button>
            ))}
          </div>

          <div className="flex flex-col gap-2 pt-1 sm:flex-row sm:items-center sm:justify-between">
            <button
              type="button"
              onClick={() => setShowLibrary((v) => !v)}
              className="inline-flex min-h-[40px] items-center justify-center gap-1.5 rounded-xl border border-slate-300 bg-white px-3.5 py-2 text-xs font-bold text-slate-700 hover:bg-slate-50 sm:w-auto"
            >
              <BookOpen className="h-4 w-4 text-indigo-600" />
              <span>Pustaka {filteredScenarios.length} Situasi Lazim</span>
              {showLibrary ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </button>

            <button
              type="button"
              disabled={loading || deepLoading}
              onClick={() => handleConsult()}
              className="inline-flex min-h-[44px] items-center justify-center gap-2 rounded-xl bg-[#0f2744] px-6 py-2.5 text-sm font-extrabold text-white shadow-sm hover:bg-slate-800 disabled:opacity-60"
            >
              {loading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Search className="h-4 w-4 text-amber-300" />
              )}
              Tanya Pakar Sekarang
            </button>
          </div>

          {error && (
            <div className="rounded-xl border border-rose-300 bg-rose-50 px-3.5 py-2.5 text-xs font-semibold text-rose-800">
              {error}
            </div>
          )}
        </div>

        {/* Pustaka Situasi Boleh Lipat */}
        {showLibrary && (
          <div className="mt-4 border-t border-slate-200 pt-4">
            <div className="mb-2.5 text-xs font-bold text-slate-700">
              Klik mana-mana situasi di bawah untuk paparan keputusan segera:
            </div>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {filteredScenarios.map((sc) => {
                const selected = result?.scenario_id === sc.id;
                return (
                  <button
                    key={sc.id}
                    type="button"
                    onClick={() => {
                      setQuestion(sc.tajuk);
                      handleConsult(sc.tajuk, sc.id);
                    }}
                    className={`flex flex-col items-start rounded-xl border p-3 text-left transition ${
                      selected
                        ? "border-indigo-500 bg-indigo-50/70 ring-1 ring-indigo-500"
                        : "border-slate-200 bg-slate-50/50 hover:border-indigo-300 hover:bg-indigo-50/30"
                    }`}
                  >
                    <div className="flex w-full items-center justify-between gap-2">
                      <span className="rounded bg-[#0f2744] px-2 py-0.5 text-[11px] font-bold text-white">
                        {sc.akta_utama}
                      </span>
                      <span
                        className={`text-[11px] font-bold ${
                          sc.sesuai_buka_ip ? "text-amber-800" : "text-emerald-700"
                        }`}
                      >
                        {sc.sesuai_buka_ip ? "Buka IP" : "Kompaun"}
                      </span>
                    </div>
                    <span className="mt-1.5 text-xs font-bold text-slate-900">{sc.tajuk}</span>
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </section>

      {/* 2. KEPUTUSAN BERSIH & TERATUR */}
      {result && (
        <section
          ref={resultRef}
          className="space-y-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-6"
        >
          {/* Header Keputusan & 1 CTA Utama */}
          <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-200 pb-4">
            <div className="space-y-1">
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-md bg-[#0f2744] px-2.5 py-0.5 text-[11px] font-bold text-white">
                  {result.akta_disyorkan}
                </span>
                {result.ai_succeeded ? (
                  <span className="inline-flex items-center gap-1 rounded-full border border-indigo-200 bg-indigo-50 px-2.5 py-0.5 text-[11px] font-bold text-indigo-800">
                    <Sparkles className="h-3 w-3" /> {result.engine_used}
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-0.5 text-[11px] font-semibold text-emerald-800">
                    <Zap className="h-3 w-3" /> {result.engine_used || "Mod Pantas — Rujukan Statutori UIP"}
                  </span>
                )}
              </div>
              <h3 className="text-base font-extrabold text-slate-900">{result.tajuk_nasihat}</h3>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={handleCopySummary}
                className="inline-flex min-h-[40px] items-center gap-1.5 rounded-xl border border-slate-300 bg-white px-3.5 py-2 text-xs font-bold text-slate-700 hover:bg-slate-50"
              >
                {copiedSummary ? (
                  <ClipboardCheck className="h-4 w-4 text-emerald-600" />
                ) : (
                  <Copy className="h-4 w-4" />
                )}
                {copiedSummary ? "Disalin!" : "Salin Ringkasan"}
              </button>

              <button
                type="button"
                onClick={() =>
                  onApplyToCaseBuilder(
                    result.draf_teks_kes_cadangan,
                    result.akta_disyorkan,
                    result.sesuai_buka_ip
                  )
                }
                className="inline-flex min-h-[40px] items-center gap-1.5 rounded-xl bg-blue-600 px-4 py-2 text-xs font-extrabold text-white shadow-sm hover:bg-blue-700"
              >
                <ArrowRightCircle className="h-4 w-4" />
                {result.sesuai_buka_ip
                  ? "Terus Buka Editor Fail IP"
                  : "Isi ke Borang Notis Kompaun"}
              </button>
            </div>
          </div>

          {result.ai_attempted && result.ai_succeeded === false && result.fallback_reason && (
            <div className="flex flex-wrap items-center justify-between gap-2.5 rounded-xl border border-amber-300 bg-amber-50 px-3.5 py-2.5 text-xs text-amber-950">
              <div className="flex min-w-0 flex-1 items-start gap-2.5">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-700" />
                <div>
                  <span className="font-bold">Mod Rujukan Tempatan Aktif:</span>{" "}
                  {result.fallback_reason}
                </div>
              </div>
              <button
                type="button"
                disabled={loading || deepLoading}
                onClick={() => {
                  const typed = question.trim();
                  handleConsult(
                    typed ? undefined : result.tajuk_nasihat,
                    typed ? undefined : result.scenario_id,
                    true
                  );
                }}
                className="inline-flex shrink-0 items-center gap-1 rounded-lg border border-amber-400 bg-white px-2.5 py-1.5 text-[11px] font-bold text-amber-900 shadow-xs hover:bg-amber-100 disabled:opacity-50"
              >
                <Sparkles className="h-3 w-3" />
                {deepLoading ? "Mencuba AI..." : "Cuba Semula AI"}
              </button>
            </div>
          )}

          {/* Ringkasan Eksekutif Bersih: 1 Keputusan + 2 Kad Garis Sisi */}
          <div
            className={`rounded-xl border border-slate-200 border-l-4 p-4 ${
              result.sesuai_buka_ip
                ? "border-l-amber-500 bg-amber-50/40"
                : "border-l-emerald-600 bg-emerald-50/40"
            }`}
          >
            <div className="text-[11px] font-extrabold uppercase tracking-wide text-slate-600">
              Keputusan Tindakan Segera
            </div>
            <div className="mt-1 text-sm font-extrabold text-slate-900">
              {result.keputusan_tindakan}
            </div>
            <p className="mt-1.5 text-xs leading-relaxed text-slate-700">
              {result.alasan_keputusan}
            </p>
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="rounded-xl border border-slate-200 border-l-4 border-l-blue-600 bg-white p-3.5">
              <div className="text-[11px] font-extrabold uppercase tracking-wide text-blue-800">
                Seksyen Kesalahan &amp; Hukuman Utama
              </div>
              <div className="mt-1 text-sm font-bold text-slate-900">
                {primaryCharge?.seksyen_kesalahan || result.akta_disyorkan}
              </div>
              <div className="mt-1 text-xs text-slate-600">
                <strong>Hukuman:</strong> {primaryCharge?.seksyen_hukuman || "-"} —{" "}
                {primaryCharge?.hukuman_maksimum || "-"}
              </div>
            </div>

            <div className="rounded-xl border border-slate-200 border-l-4 border-l-teal-600 bg-white p-3.5">
              <div className="text-[11px] font-extrabold uppercase tracking-wide text-teal-800">
                Bukti &amp; Borang Kritikal Di Lokasi
              </div>
              <ul className="mt-1.5 list-disc space-y-1 pl-4 text-xs font-medium text-slate-700">
                {result.eksibit_wajib.slice(0, 3).map((item, i) => (
                  <li key={i}>{item}</li>
                ))}
              </ul>
            </div>
          </div>

          {/* 3 Tab Kemas Untuk Perincian (Elak Dinding Kotak Serentak) */}
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 pb-2 pt-1">
            <div className="flex gap-1.5 overflow-x-auto no-scrollbar">
              {[
                { id: "sop" as AdvisorResultTab, label: "SOP, Eksibit & Amaran" },
                {
                  id: "charges" as AdvisorResultTab,
                  label: `Pertuduhan Penuh (${result.cadangan_pertuduhan.length})`,
                },
                {
                  id: "statutes" as AdvisorResultTab,
                  label: `Petikan Akta (${result.statutory_citations.length})`,
                },
              ].map((t) => (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => setResultTab(t.id)}
                  className={`shrink-0 rounded-lg px-3 py-2 text-xs font-bold transition ${
                    resultTab === t.id
                      ? "bg-[#0f2744] text-white"
                      : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>

            <button
              type="button"
              disabled={loading || deepLoading}
              onClick={() => {
                const typed = question.trim();
                handleConsult(
                  typed ? undefined : result.tajuk_nasihat,
                  typed ? undefined : result.scenario_id,
                  true
                );
              }}
              className="inline-flex items-center gap-1.5 text-xs font-bold text-indigo-700 hover:underline disabled:opacity-50"
            >
              {deepLoading ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Sparkles className="h-3.5 w-3.5" />
              )}
              {deepLoading
                ? "Sedang Analisa AI..."
                : result.ai_succeeded
                  ? "Analisa Semula dengan AI"
                  : "Perlu jawapan lebih terperinci? Cuba AI (~15s)"}
            </button>
          </div>

          {resultTab === "sop" && (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <h4 className="flex items-center gap-1.5 text-xs font-extrabold text-slate-900">
                  <ClipboardList className="h-4 w-4 text-emerald-700" />
                  Langkah Tindakan (SOP Lapangan)
                </h4>
                <ol className="list-decimal space-y-2 pl-5 text-xs leading-relaxed text-slate-700">
                  {result.sop_lapangan.map((step, i) => (
                    <li key={i}>{step}</li>
                  ))}
                </ol>
              </div>

              <div className="space-y-4">
                <div>
                  <h4 className="mb-2 flex items-center gap-1.5 text-xs font-extrabold text-slate-900">
                    <CheckCircle2 className="h-4 w-4 text-teal-700" />
                    Senarai Penuh Barang Bukti &amp; Borang
                  </h4>
                  <ul className="list-disc space-y-1.5 pl-5 text-xs leading-relaxed text-slate-700">
                    {result.eksibit_wajib.map((ex, i) => (
                      <li key={i}>{ex}</li>
                    ))}
                  </ul>
                </div>

                <div className="rounded-xl border border-rose-200 border-l-4 border-l-rose-600 bg-rose-50/40 p-3">
                  <h4 className="mb-1.5 flex items-center gap-1.5 text-xs font-extrabold text-rose-950">
                    <ShieldAlert className="h-4 w-4 text-rose-700" />
                    Elak Kesilapan Biasa PPKP
                  </h4>
                  <ul className="space-y-1.5 text-xs text-rose-900">
                    {result.perangkap_kesilapan.map((trap, i) => (
                      <li key={i} className="flex items-start gap-1.5">
                        <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-rose-600" />
                        <span>{trap}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          )}

          {resultTab === "charges" && (
            <div className="space-y-2.5">
              {result.cadangan_pertuduhan.map((c, idx) => (
                <div
                  key={idx}
                  className="rounded-xl border border-slate-200 bg-slate-50/40 p-3.5 text-xs"
                >
                  <div className="flex items-center gap-2 font-extrabold text-slate-900">
                    <Gavel className="h-4 w-4 text-blue-700" />
                    <span>{c.perihal}</span>
                  </div>
                  <div className="mt-2 grid grid-cols-1 gap-1.5 sm:grid-cols-2">
                    <div>
                      <span className="font-semibold text-slate-500">Seksyen Kesalahan: </span>
                      <span className="font-bold text-blue-900">{c.seksyen_kesalahan}</span>
                    </div>
                    <div>
                      <span className="font-semibold text-slate-500">Seksyen Hukuman: </span>
                      <span className="font-bold text-indigo-900">{c.seksyen_hukuman}</span>
                    </div>
                    <div>
                      <span className="font-semibold text-slate-500">Penalti Maksimum: </span>
                      <span className="text-slate-800">{c.hukuman_maksimum}</span>
                    </div>
                    <div>
                      <span className="font-semibold text-slate-500">Status Kompaun: </span>
                      <span className="font-bold text-emerald-800">{c.boleh_kompaun}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {resultTab === "statutes" && (
            <div className="space-y-2.5">
              {result.statutory_citations.length === 0 ? (
                <p className="text-xs text-slate-500">
                  Tiada petikan akta tambahan dilampirkan untuk pertanyaan ini.
                </p>
              ) : (
                result.statutory_citations.map((cit, i) => (
                  <div
                    key={i}
                    className="rounded-xl border border-slate-200 bg-slate-50/40 p-3 text-xs text-slate-700"
                  >
                    <div className="font-extrabold text-teal-800">
                      {cit.section.toLowerCase().includes(cit.akta_code.toLowerCase())
                        ? cit.section
                        : `${cit.akta_code} — ${cit.section}`}
                    </div>
                    <p className="mt-1 whitespace-pre-line leading-relaxed">{cit.text}</p>
                  </div>
                ))
              )}
            </div>
          )}
        </section>
      )}
    </div>
  );
}
