"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  ArrowRightCircle,
  BookOpen,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  ClipboardCheck,
  ClipboardList,
  Clock,
  Copy,
  Gavel,
  History,
  Loader2,
  MessageSquareQuote,
  RefreshCw,
  Search,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  X,
  Zap,
} from "lucide-react";
import {
  consultUipAdvisor,
  fetchAdvisorAnsweredQuestions,
  fetchAdvisorScenarios,
} from "@/lib/api";
import type {
  AdvisorAnsweredItem,
  AdvisorAnsweredListResponse,
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

const CORE_ACT_CODES = ["Akta 852", "Akta 281", "Akta 154", "Akta 342"] as const;
const SECONDARY_ACT_CODES = [
  "Akta 593",
  "Akta 56",
  "Akta Lain / Rujukan Silang",
] as const;

function getActBadgeStyle(aktaCode: string): {
  badge: string;
  headerBg: string;
  pillActive: string;
} {
  switch (aktaCode) {
    case "Akta 852":
      return {
        badge: "bg-indigo-700 text-white",
        headerBg: "border-indigo-200 bg-indigo-50/70",
        pillActive: "bg-indigo-700 text-white border-indigo-700",
      };
    case "Akta 281":
      return {
        badge: "bg-amber-700 text-white",
        headerBg: "border-amber-200 bg-amber-50/70",
        pillActive: "bg-amber-700 text-white border-amber-700",
      };
    case "Akta 154":
      return {
        badge: "bg-emerald-700 text-white",
        headerBg: "border-emerald-200 bg-emerald-50/70",
        pillActive: "bg-emerald-700 text-white border-emerald-700",
      };
    case "Akta 342":
      return {
        badge: "bg-rose-700 text-white",
        headerBg: "border-rose-200 bg-rose-50/70",
        pillActive: "bg-rose-700 text-white border-rose-700",
      };
    default:
      return {
        badge: "bg-slate-700 text-white",
        headerBg: "border-slate-200 bg-slate-100/80",
        pillActive: "bg-slate-800 text-white border-slate-800",
      };
  }
}

function formatShortTimestamp(raw: string): string {
  const clean = (raw || "").trim();
  if (!clean) return "";
  const m = clean.match(/^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}:\d{2})/);
  if (!m) return clean;
  const months = [
    "Jan",
    "Feb",
    "Mac",
    "Apr",
    "Mei",
    "Jun",
    "Jul",
    "Ogs",
    "Sep",
    "Okt",
    "Nov",
    "Dis",
  ];
  const monthIdx = Number(m[2]) - 1;
  const mon = months[monthIdx] || m[2];
  return `${Number(m[3])} ${mon}, ${m[4]}`;
}

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
  const [answeredData, setAnsweredData] = useState<AdvisorAnsweredListResponse | null>(null);
  const [answeredLoading, setAnsweredLoading] = useState(false);
  const [answeredActFilter, setAnsweredActFilter] = useState<string>("Semua");
  const [answeredSearch, setAnsweredSearch] = useState("");
  const [selectedAnsweredId, setSelectedAnsweredId] = useState<string | null>(null);
  const [expandedActGroups, setExpandedActGroups] = useState<Record<string, boolean>>({});
  const resultRef = useRef<HTMLDivElement | null>(null);
  const answeredSectionRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    fetchAdvisorScenarios()
      .then(setScenarios)
      .catch(() => setScenarios([]));
  }, []);

  const loadAnsweredQuestions = useCallback(async () => {
    setAnsweredLoading(true);
    try {
      const data = await fetchAdvisorAnsweredQuestions({ authToken, limit: 150 });
      setAnsweredData(data);
    } catch {
      // Abaikan jika senarai soalan dijawab gagal dimuat sementara
    } finally {
      setAnsweredLoading(false);
    }
  }, [authToken]);

  useEffect(() => {
    void loadAnsweredQuestions();
  }, [loadAnsweredQuestions]);

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
      setSelectedAnsweredId(null);
      void loadAnsweredQuestions();
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

  const handleSelectAnsweredItem = (item: AdvisorAnsweredItem) => {
    setQuestion(item.question);
    setSelectedAnsweredId(item.id);
    setError(null);
    setCopiedSummary(false);
    setShowLibrary(false);
    if (item.answer) {
      setResult(item.answer);
      setResultTab("sop");
      window.setTimeout(() => {
        resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 90);
      return;
    }
    void handleConsult(item.question);
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

  const visibleActFilterCodes = useMemo(() => {
    const counts = answeredData?.act_counts || {};
    const extra = SECONDARY_ACT_CODES.filter((code) => (counts[code] || 0) > 0);
    return [...CORE_ACT_CODES, ...extra];
  }, [answeredData]);

  const filteredAnsweredGroups = useMemo(() => {
    const groups = answeredData?.groups || [];
    const qLow = answeredSearch.trim().toLowerCase();
    return groups
      .filter(
        (grp) => answeredActFilter === "Semua" || grp.akta_code === answeredActFilter
      )
      .map((grp) => {
        if (!qLow) return grp;
        const matchedItems = grp.items.filter((item) => {
          const hay = [
            item.question,
            item.tajuk_nasihat,
            item.keputusan_tindakan,
            item.seksyen_utama,
            item.akta_group,
            item.akta_disyorkan,
          ]
            .join(" ")
            .toLowerCase();
          return hay.includes(qLow);
        });
        return { ...grp, count: matchedItems.length, items: matchedItems };
      })
      .filter((grp) => grp.items.length > 0);
  }, [answeredData, answeredActFilter, answeredSearch]);

  const activeActsCount = useMemo(() => {
    const counts = answeredData?.act_counts || {};
    return Object.values(counts).filter((c) => c > 0).length;
  }, [answeredData]);

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
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={() => setShowLibrary((v) => !v)}
                className="inline-flex min-h-[40px] items-center justify-center gap-1.5 rounded-xl border border-slate-300 bg-white px-3.5 py-2 text-xs font-bold text-slate-700 hover:bg-slate-50"
              >
                <BookOpen className="h-4 w-4 text-indigo-600" />
                <span>Pustaka {filteredScenarios.length} Situasi Lazim</span>
                {showLibrary ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </button>

              <button
                type="button"
                onClick={() =>
                  answeredSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" })
                }
                className="inline-flex min-h-[40px] items-center justify-center gap-1.5 rounded-xl border border-emerald-200 bg-emerald-50/70 px-3.5 py-2 text-xs font-bold text-emerald-900 hover:bg-emerald-100/70"
              >
                <History className="h-4 w-4 text-emerald-700" />
                <span>Soalan Dijawab ({answeredData?.total_questions ?? 0})</span>
              </button>
            </div>

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

      {/* 3. SENARAI SOALAN TELAH DIJAWAB PAKAR (DIKUMPUL DARI SEMUA PENGGUNA & DIKELASKAN MENGIKUT AKTA) */}
      <section
        ref={answeredSectionRef}
        className="space-y-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-6"
      >
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex items-start gap-2.5">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-emerald-50 text-emerald-700">
              <History className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-sm font-extrabold text-slate-900 sm:text-base">
                Senarai Soalan Telah Dijawab Pakar (Mengikut Akta)
              </h3>
              <p className="mt-0.5 flex flex-wrap items-center gap-1.5 text-xs text-slate-500">
                <span>
                  Himpunan soalan pengguna yang telah dijawab Pakar UIP &amp; dikelaskan mengikut Akta.
                </span>
                <span className="inline-flex items-center gap-1 rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-semibold text-slate-700">
                  <ShieldCheck className="h-3 w-3 text-emerald-700" /> Data Peribadi Disamarkan (PDPA)
                </span>
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="rounded-lg bg-slate-100 px-2.5 py-1.5 text-xs font-extrabold text-slate-800">
              {answeredData?.total_questions ?? 0} Soalan · {activeActsCount} Akta
            </span>
            <button
              type="button"
              onClick={() => void loadAnsweredQuestions()}
              disabled={answeredLoading}
              title="Muat semula senarai soalan"
              className="inline-flex min-h-[36px] min-w-[36px] items-center justify-center rounded-lg border border-slate-300 bg-white px-2.5 text-xs font-bold text-slate-700 hover:bg-slate-50 disabled:opacity-60"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${answeredLoading ? "animate-spin" : ""}`} />
              <span className="ml-1.5 hidden sm:inline">Segar Semula</span>
            </button>
          </div>
        </div>

        {/* Carian & Tapisan Mengikut Akta */}
        <div className="space-y-3">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={answeredSearch}
              onChange={(e) => setAnsweredSearch(e.target.value)}
              placeholder="Cari soalan pengguna terdahulu, seksyen atau keputusan..."
              className="w-full rounded-xl border border-slate-300 bg-slate-50/50 py-2 pl-9 pr-9 text-sm text-slate-900 placeholder:text-slate-400 focus:border-indigo-500 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-100"
            />
            {answeredSearch && (
              <button
                type="button"
                onClick={() => setAnsweredSearch("")}
                aria-label="Kosongkan carian"
                className="absolute right-2.5 top-1/2 -translate-y-1/2 rounded p-1 text-slate-400 hover:bg-slate-200 hover:text-slate-700"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-1.5">
            <button
              type="button"
              onClick={() => setAnsweredActFilter("Semua")}
              className={`inline-flex min-h-[34px] items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-bold transition ${
                answeredActFilter === "Semua"
                  ? "border-[#0f2744] bg-[#0f2744] text-white shadow-xs"
                  : "border-slate-200 bg-slate-50 text-slate-700 hover:bg-slate-100"
              }`}
            >
              <span>Semua Akta</span>
              <span
                className={`rounded-full px-1.5 py-0.5 text-[10px] font-extrabold ${
                  answeredActFilter === "Semua"
                    ? "bg-white/20 text-white"
                    : "bg-slate-200 text-slate-800"
                }`}
              >
                {answeredData?.total_questions ?? 0}
              </span>
            </button>

            {visibleActFilterCodes.map((code) => {
              const count = answeredData?.act_counts?.[code] ?? 0;
              const active = answeredActFilter === code;
              const st = getActBadgeStyle(code);
              return (
                <button
                  key={code}
                  type="button"
                  onClick={() => setAnsweredActFilter(code)}
                  className={`inline-flex min-h-[34px] items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-bold transition ${
                    active
                      ? st.pillActive
                      : "border-slate-200 bg-slate-50 text-slate-700 hover:bg-slate-100"
                  }`}
                >
                  <span>{code}</span>
                  <span
                    className={`rounded-full px-1.5 py-0.5 text-[10px] font-extrabold ${
                      active ? "bg-white/20 text-white" : "bg-slate-200 text-slate-800"
                    }`}
                  >
                    {count}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Senarai Soalan Dikelompok Mengikut Akta */}
        {answeredLoading && !answeredData ? (
          <div className="flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-slate-50/50 py-8 text-xs font-semibold text-slate-600">
            <Loader2 className="h-4 w-4 animate-spin text-indigo-600" />
            Memuatkan himpunan soalan telah dijawab Pakar UIP...
          </div>
        ) : !answeredData || answeredData.total_questions === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50/50 px-4 py-8 text-center">
            <p className="text-xs font-bold text-slate-700">
              Belum ada soalan pengguna yang direkodkan setakat ini.
            </p>
            <p className="mt-1 text-xs text-slate-500">
              Setiap soalan yang dijawab di atas akan dikumpulkan di sini dan dikelaskan mengikut
              Akta secara automatik untuk rujukan semua pegawai.
            </p>
          </div>
        ) : filteredAnsweredGroups.length === 0 ? (
          <div className="flex flex-col items-center gap-2 rounded-xl border border-slate-200 bg-slate-50/50 px-4 py-7 text-center">
            <p className="text-xs font-bold text-slate-700">
              Tiada soalan direkodkan bagi tapisan ini.
            </p>
            <button
              type="button"
              onClick={() => {
                setAnsweredActFilter("Semua");
                setAnsweredSearch("");
              }}
              className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-bold text-slate-700 hover:bg-slate-100"
            >
              Reset Tapisan
            </button>
          </div>
        ) : (
          <div className="space-y-5">
            {filteredAnsweredGroups.map((group) => {
              const st = getActBadgeStyle(group.akta_code);
              const isExpanded = Boolean(expandedActGroups[group.akta_code]);
              const shownItems = isExpanded ? group.items : group.items.slice(0, 6);
              const hiddenCount = group.items.length - shownItems.length;

              return (
                <div
                  key={group.akta_code}
                  className="overflow-hidden rounded-xl border border-slate-200 bg-slate-50/30"
                >
                  <div
                    className={`flex flex-wrap items-center justify-between gap-2 border-b px-3.5 py-2.5 ${st.headerBg}`}
                  >
                    <div className="flex min-w-0 flex-wrap items-center gap-2">
                      <span
                        className={`shrink-0 rounded-md px-2.5 py-0.5 text-[11px] font-extrabold ${st.badge}`}
                      >
                        {group.akta_code}
                      </span>
                      <span className="truncate text-xs font-bold text-slate-900">
                        {group.akta_title}
                      </span>
                    </div>
                    <span className="shrink-0 rounded-full bg-white px-2.5 py-0.5 text-[11px] font-extrabold text-slate-700 ring-1 ring-slate-200">
                      {group.items.length} soalan
                    </span>
                  </div>

                  <div className="grid grid-cols-1 gap-2.5 p-3 md:grid-cols-2">
                    {shownItems.map((item) => {
                      const isSelected = selectedAnsweredId === item.id;
                      const tsLabel = formatShortTimestamp(item.last_asked_at);
                      return (
                        <button
                          key={item.id}
                          type="button"
                          onClick={() => handleSelectAnsweredItem(item)}
                          className={`flex flex-col justify-between rounded-xl border p-3.5 text-left transition ${
                            isSelected
                              ? "border-indigo-500 bg-indigo-50/60 ring-1 ring-indigo-500"
                              : "border-slate-200 bg-white hover:border-indigo-300 hover:bg-indigo-50/20"
                          }`}
                        >
                          <div>
                            <div className="flex flex-wrap items-center justify-between gap-1.5">
                              <div className="flex flex-wrap items-center gap-1.5">
                                <span
                                  className={`rounded px-2 py-0.5 text-[10px] font-extrabold ${
                                    item.sesuai_buka_ip
                                      ? "bg-amber-100 text-amber-900"
                                      : "bg-emerald-100 text-emerald-800"
                                  }`}
                                >
                                  {item.sesuai_buka_ip ? "Buka IP" : "Kompaun / Rujukan"}
                                </span>
                                <span
                                  className={`inline-flex items-center gap-1 rounded px-2 py-0.5 text-[10px] font-bold ${
                                    item.is_ai_answered
                                      ? "bg-indigo-100 text-indigo-800"
                                      : "bg-slate-100 text-slate-700"
                                  }`}
                                >
                                  {item.is_ai_answered ? (
                                    <>
                                      <Sparkles className="h-2.5 w-2.5" /> Analisa AI
                                    </>
                                  ) : (
                                    "Statutori"
                                  )}
                                </span>
                                {item.ask_count > 1 && (
                                  <span className="rounded bg-blue-50 px-2 py-0.5 text-[10px] font-bold text-blue-800">
                                    Ditanya {item.ask_count}×
                                  </span>
                                )}
                              </div>

                              {tsLabel && (
                                <span className="inline-flex items-center gap-1 text-[10px] font-medium text-slate-500">
                                  <Clock className="h-3 w-3" />
                                  {tsLabel}
                                </span>
                              )}
                            </div>

                            <p className="mt-2 line-clamp-2 text-xs font-extrabold leading-snug text-slate-900 sm:text-[13px]">
                              &ldquo;{item.question}&rdquo;
                            </p>

                            {item.seksyen_utama && (
                              <p className="mt-1.5 text-[11px] font-bold text-blue-900">
                                Seksyen: {item.seksyen_utama}
                              </p>
                            )}

                            <p className="mt-1 line-clamp-2 text-[11px] leading-relaxed text-slate-600">
                              {item.keputusan_tindakan}
                            </p>
                          </div>

                          <div className="mt-2.5 flex items-center justify-between border-t border-slate-100 pt-2 text-[11px] font-bold">
                            <span
                              className={
                                isSelected ? "text-indigo-700" : "text-blue-700"
                              }
                            >
                              {isSelected
                                ? "Sedang dipaparkan ✓"
                                : "Klik untuk lihat jawapan penuh →"}
                            </span>
                          </div>
                        </button>
                      );
                    })}
                  </div>

                  {group.items.length > 6 && (
                    <div className="border-t border-slate-200 bg-white px-3.5 py-2 text-center">
                      <button
                        type="button"
                        onClick={() =>
                          setExpandedActGroups((prev) => ({
                            ...prev,
                            [group.akta_code]: !prev[group.akta_code],
                          }))
                        }
                        className="inline-flex items-center gap-1 text-xs font-bold text-indigo-700 hover:underline"
                      >
                        {isExpanded ? (
                          <>
                            Lipat senarai {group.akta_code} <ChevronUp className="h-3.5 w-3.5" />
                          </>
                        ) : (
                          <>
                            Papar {hiddenCount} lagi soalan {group.akta_code}{" "}
                            <ChevronDown className="h-3.5 w-3.5" />
                          </>
                        )}
                      </button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
