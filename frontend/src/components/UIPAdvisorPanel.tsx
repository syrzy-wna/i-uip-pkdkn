"use client";

import React, { useEffect, useState } from "react";
import {
  AlertTriangle,
  ArrowRightCircle,
  BookOpen,
  CheckCircle2,
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

const EXAMPLE_PROMPTS = [
  "Ada budak sekolah hisap rokok / vape di tepi jalan",
  "Restoran kotor ada najis tikus di dapur dan 2 pekerja tiada suntikan tifoid",
  "Kedai serbaneka pamer vape secara terbuka di kaunter",
  "Tapak pembinaan ada 2 bekas air bertakung berjentik-jentik Aedes",
  "Pesakit Tibi kahak positif cicir rawatan walau sudah serah Notis Arahan",
];

export default function UIPAdvisorPanel({
  aktaUtama,
  authToken,
  officer,
  onApplyToCaseBuilder,
}: UIPAdvisorPanelProps) {
  const [question, setQuestion] = useState("");
  const [aktaFilter, setAktaFilter] = useState<string>("Semua");
  const [useAiDeep, setUseAiDeep] = useState<boolean>(false);
  const [scenarios, setScenarios] = useState<AdvisorScenarioItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [copiedSummary, setCopiedSummary] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AdvisorConsultResult | null>(null);

  useEffect(() => {
    fetchAdvisorScenarios()
      .then(setScenarios)
      .catch(() => setScenarios([]));
  }, []);

  const handleConsult = async (customQuestion?: string, scenarioId?: string) => {
    const q = (customQuestion ?? question).trim();
    if (!q && !scenarioId) {
      setError("Sila taip soalan situasi kesalahan atau pilih salah satu kad situasi di sebelah.");
      return;
    }
    setLoading(true);
    setError(null);
    setCopiedSummary(false);
    try {
      const res = await consultUipAdvisor({
        question: q || "Rujuk templat situasi ini",
        aktaHint: aktaFilter !== "Semua" ? aktaFilter : aktaUtama || "Semua",
        scenarioId,
        useAi: useAiDeep,
        authToken,
        officerProfile: officer,
      });
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gagal mendapatkan nasihat pakar UIP.");
    } finally {
      setLoading(false);
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
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
      {/* LAJUR KIRI (5 col): Input Soalan + Pustaka Situasi */}
      <div className="space-y-4 lg:col-span-5">
        <div className="rounded-xl border border-indigo-200 bg-gradient-to-br from-indigo-50/80 to-blue-50/40 p-4 shadow-xs">
          <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <MessageSquareQuote className="h-5 w-5 text-indigo-700" />
              <h3 className="text-xs font-bold text-slate-900">
                Tanya Pakar UIP (Lapangan &amp; Perundangan)
              </h3>
            </div>
            <select
              value={aktaFilter}
              onChange={(e) => setAktaFilter(e.target.value)}
              className="rounded-lg border border-indigo-200 bg-white px-2.5 py-1 text-xs font-semibold text-slate-800"
            >
              <option value="Semua">Semua Akta KKM</option>
              <option value="Akta 852">Akta 852 (Merokok/Vape)</option>
              <option value="Akta 281">Akta 281 &amp; PPKM 2009</option>
              <option value="Akta 154">Akta 154 (Aedes)</option>
              <option value="Akta 342">Akta 342 (Tibi/Berjangkit)</option>
            </select>
          </div>

          <p className="mb-2 text-[11px] text-slate-600">
            Ceritakan situasi yang anda jumpa di lokasi (cth: budak sekolah hisap rokok, premis kotor + tiada tifoid, tapak bina ada Aedes) — dapatkan seksyen caj &amp; SOP serta-merta.
          </p>

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
            className="w-full rounded-lg border border-indigo-200 bg-white p-2.5 text-xs leading-relaxed focus:border-indigo-500 focus:outline-none"
          />

          {/* Suis Mod Pantas (< 0.1s) vs Mod AI Gemini Flash */}
          <div className="mt-2.5 flex flex-wrap items-center justify-between gap-2 rounded-lg border border-indigo-100 bg-white/90 px-2.5 py-1.5">
            <div className="flex items-center gap-1.5 text-[11px] font-semibold text-slate-700">
              {useAiDeep ? (
                <Sparkles className="h-3.5 w-3.5 text-indigo-600" />
              ) : (
                <Zap className="h-3.5 w-3.5 text-emerald-600" />
              )}
              <span>
                {useAiDeep
                  ? "Mod AI Mendalam (Gemini Cloud ~10–25s)"
                  : "Mod Pantas Statutori (< 0.1 Saat — Serta-Merta)"}
              </span>
            </div>
            <button
              type="button"
              onClick={() => setUseAiDeep(!useAiDeep)}
              className={`rounded-full px-2.5 py-0.5 text-[10px] font-bold transition ${useAiDeep
                ? "bg-indigo-600 text-white"
                : "bg-emerald-100 text-emerald-800 hover:bg-emerald-200"
                }`}
            >
              {useAiDeep ? "Tukar ke Mod Pantas" : "Aktifkan AI Flash"}
            </button>
          </div>

          <div className="mt-2.5">
            <span className="text-[10px] font-bold uppercase text-slate-500">Soalan Contoh Pantas:</span>
            <div className="mt-1 flex flex-wrap gap-1.5">
              {EXAMPLE_PROMPTS.map((ex, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => {
                    setQuestion(ex);
                    handleConsult(ex);
                  }}
                  className="rounded-full border border-indigo-200 bg-white px-2.5 py-1 text-[10px] font-medium text-indigo-800 hover:bg-indigo-100"
                >
                  {ex}
                </button>
              ))}
            </div>
          </div>

          <button
            type="button"
            disabled={loading}
            onClick={() => handleConsult()}
            className="mt-3 flex w-full items-center justify-center gap-1.5 rounded-lg bg-[#0f2744] px-4 py-2.5 text-xs font-bold text-white shadow-sm hover:bg-slate-800 disabled:opacity-60"
          >
            {loading ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Search className="h-3.5 w-3.5 text-amber-300" />
            )}
            Tanya Pakar &amp; Semak Prosedur
          </button>

          {error && (
            <div className="mt-2 rounded-lg border border-rose-300 bg-rose-50 px-3 py-2 text-xs font-semibold text-rose-800">
              {error}
            </div>
          )}
        </div>

        {/* Pustaka Pantas Situasi Lazim */}
        <div className="rounded-xl border border-slate-200 bg-white p-3.5">
          <div className="mb-2 flex items-center justify-between">
            <h4 className="text-xs font-bold text-slate-900">
              Pustaka Pantas ({filteredScenarios.length} Situasi Lapangan)
            </h4>
            <span className="text-[10px] text-slate-500">Klik 1-kali (0.05s)</span>
          </div>
          <div className="max-h-[420px] space-y-1.5 overflow-y-auto pr-1">
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
                  className={`flex w-full flex-col items-start rounded-lg border p-2.5 text-left transition ${selected
                    ? "border-indigo-500 bg-indigo-50/70 ring-1 ring-indigo-500"
                    : "border-slate-200 bg-slate-50/40 hover:border-indigo-300 hover:bg-indigo-50/30"
                    }`}
                >
                  <div className="flex w-full items-center justify-between gap-2">
                    <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] font-bold text-white">
                      {sc.akta_utama}
                    </span>
                    <span
                      className={`text-[10px] font-bold ${sc.sesuai_buka_ip ? "text-amber-700" : "text-emerald-700"
                        }`}
                    >
                      {sc.sesuai_buka_ip ? "Sesuai Buka IP" : "Kompaun Dahulu"}
                    </span>
                  </div>
                  <span className="mt-1 text-xs font-bold text-slate-900">
                    {sc.tajuk}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* LAJUR KANAN (7 col): Kad Ringkasan 5-Saat + SOP & Pertuduhan */}
      <div className="lg:col-span-7">
        {!result ? (
          <div className="flex h-full min-h-[380px] flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center">
            <MessageSquareQuote className="mb-3 h-10 w-10 text-indigo-400" />
            <h3 className="text-sm font-bold text-slate-800">
              Jawapan Pantas &amp; Ringkas Untuk Pegawai Lapangan (PPKP)
            </h3>
            <p className="mt-1 max-w-md text-xs text-slate-500">
              Pilih mana-mana contoh soalan di sebelah kiri atau taip situasi kes yang sedang anda kendalikan. Sistem akan memaparkan <strong>Kad Ringkasan 5-Saat</strong> (Seksyen Caj, Hukuman, Kompaun vs Buka IP, dan Eksibit Wajib).
            </p>
          </div>
        ) : (
          <div className="space-y-4 rounded-xl border border-slate-200 bg-white p-4 shadow-xs">
            {/* Bar Tajuk & Aksi Pantas */}
            <div className="flex flex-wrap items-start justify-between gap-2 border-b border-slate-200 pb-3">
              <div>
                <div className="flex flex-wrap items-center gap-1.5">
                  <span className="rounded bg-[#0f2744] px-2 py-0.5 text-[10px] font-bold text-white">
                    {result.akta_disyorkan}
                  </span>
                  <span className="inline-flex items-center gap-1 rounded bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-600">
                    <Zap className="h-3 w-3 text-emerald-600" />
                    {result.engine_used}
                  </span>
                </div>
                <h4 className="mt-1.5 text-sm font-bold text-slate-900">{result.tajuk_nasihat}</h4>
              </div>

              <div className="flex flex-wrap gap-1.5">
                <button
                  type="button"
                  onClick={handleCopySummary}
                  className="inline-flex items-center gap-1 rounded-lg bg-slate-100 px-2.5 py-1.5 text-xs font-bold text-slate-700 hover:bg-slate-200"
                >
                  {copiedSummary ? (
                    <ClipboardCheck className="h-3.5 w-3.5 text-emerald-600" />
                  ) : (
                    <Copy className="h-3.5 w-3.5" />
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
                  className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-700 px-3 py-1.5 text-xs font-bold text-white shadow-sm hover:bg-emerald-800"
                >
                  <ArrowRightCircle className="h-3.5 w-3.5" />
                  Jana Draf Kes Ini dalam Editor IP
                </button>
              </div>
            </div>

            {/* KAD RINGKASAN EKSEKUTIF "5-SAAT FAHAM" (4 KOTAK UTAMA) */}
            <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
              <div className="rounded-lg border border-blue-200 bg-blue-50/70 p-3">
                <div className="text-[10px] font-bold uppercase tracking-wide text-blue-700">
                  1. Seksyen Boleh Dicaj
                </div>
                <div className="mt-1 text-xs font-bold text-blue-950">
                  {primaryCharge?.seksyen_kesalahan || result.akta_disyorkan}
                </div>
                <div className="mt-0.5 text-[11px] text-blue-800 line-clamp-2">
                  {primaryCharge?.perihal || result.tajuk_nasihat}
                </div>
              </div>

              <div className="rounded-lg border border-indigo-200 bg-indigo-50/70 p-3">
                <div className="text-[10px] font-bold uppercase tracking-wide text-indigo-700">
                  2. Seksyen Hukuman &amp; Had Denda
                </div>
                <div className="mt-1 text-xs font-bold text-indigo-950">
                  {primaryCharge?.seksyen_hukuman || "-"}
                </div>
                <div className="mt-0.5 text-[11px] text-indigo-800 line-clamp-2">
                  {primaryCharge?.hukuman_maksimum || "-"}
                </div>
              </div>

              <div
                className={`rounded-lg border p-3 ${result.sesuai_buka_ip
                  ? "border-amber-300 bg-amber-50/80"
                  : "border-emerald-300 bg-emerald-50/80"
                  }`}
              >
                <div
                  className={`text-[10px] font-bold uppercase tracking-wide ${result.sesuai_buka_ip ? "text-amber-800" : "text-emerald-800"
                    }`}
                >
                  3. Keputusan Segera (Kompaun vs IP)
                </div>
                <div className="mt-1 text-xs font-bold text-slate-900">
                  {result.keputusan_tindakan}
                </div>
              </div>

              <div className="rounded-lg border border-teal-200 bg-teal-50/70 p-3">
                <div className="text-[10px] font-bold uppercase tracking-wide text-teal-800">
                  4. Bukti &amp; Borang Paling Kritikal
                </div>
                <ul className="mt-1 list-disc space-y-0.5 pl-4 text-[11px] font-medium text-teal-950">
                  {result.eksibit_wajib.slice(0, 2).map((item, i) => (
                    <li key={i} className="line-clamp-1">{item}</li>
                  ))}
                </ul>
              </div>
            </div>

            <p className="rounded-lg bg-slate-50 p-2.5 text-xs leading-relaxed text-slate-700">
              <strong>Justifikasi Pakar: </strong>
              {result.alasan_keputusan}
            </p>

            {/* Senarai Lengkap Seksyen Pertuduhan */}
            <div className="space-y-2">
              <h5 className="flex items-center gap-1.5 text-xs font-bold text-slate-900">
                <Gavel className="h-4 w-4 text-blue-700" />
                Perincian Pertuduhan &amp; Kompaun
              </h5>
              <div className="space-y-2">
                {result.cadangan_pertuduhan.map((c, idx) => (
                  <div
                    key={idx}
                    className="rounded-lg border border-slate-200 bg-slate-50/50 p-2.5 text-xs"
                  >
                    <div className="font-bold text-slate-900">{c.perihal}</div>
                    <div className="mt-1 grid grid-cols-1 gap-1 sm:grid-cols-2">
                      <div>
                        <span className="font-semibold text-slate-600">Kesalahan: </span>
                        <span className="font-bold text-blue-900">{c.seksyen_kesalahan}</span>
                      </div>
                      <div>
                        <span className="font-semibold text-slate-600">Hukuman: </span>
                        <span className="font-bold text-indigo-900">{c.seksyen_hukuman}</span>
                      </div>
                      <div>
                        <span className="font-semibold text-slate-600">Penalti: </span>
                        <span className="text-slate-800">{c.hukuman_maksimum}</span>
                      </div>
                      <div>
                        <span className="font-semibold text-slate-600">Kompaun/IP: </span>
                        <span className="font-medium text-emerald-800">{c.boleh_kompaun}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* SOP Lapangan, Eksibit & Perangkap Kesilapan */}
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              <div className="rounded-lg border border-slate-200 bg-slate-50/60 p-3">
                <h5 className="mb-1.5 flex items-center gap-1.5 text-xs font-bold text-slate-900">
                  <ClipboardList className="h-4 w-4 text-emerald-700" />
                  Langkah SOP Lapangan
                </h5>
                <ol className="list-decimal space-y-1.5 pl-4 text-xs text-slate-700">
                  {result.sop_lapangan.map((step, i) => (
                    <li key={i}>{step}</li>
                  ))}
                </ol>
              </div>

              <div className="space-y-3">
                <div className="rounded-lg border border-teal-200 bg-teal-50/50 p-3">
                  <h5 className="mb-1.5 flex items-center gap-1.5 text-xs font-bold text-teal-950">
                    <CheckCircle2 className="h-4 w-4 text-teal-700" />
                    Senarai Penuh Eksibit Wajib
                  </h5>
                  <ul className="list-disc space-y-1 pl-4 text-xs text-slate-700">
                    {result.eksibit_wajib.map((ex, i) => (
                      <li key={i}>{ex}</li>
                    ))}
                  </ul>
                </div>

                <div className="rounded-lg border border-rose-200 bg-rose-50/60 p-3">
                  <h5 className="mb-1.5 flex items-center gap-1.5 text-xs font-bold text-rose-950">
                    <ShieldAlert className="h-4 w-4 text-rose-700" />
                    Elak Perangkap Kesilapan Biasa
                  </h5>
                  <ul className="space-y-1 text-xs text-rose-900">
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

            {result.statutory_citations.length > 0 && (
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                <div className="mb-1.5 flex items-center gap-1.5 text-xs font-bold text-slate-800">
                  <BookOpen className="h-4 w-4 text-teal-700" />
                  Teks Akta Sebenar Dirujuk (Strict RAG)
                </div>
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                  {result.statutory_citations.slice(0, 2).map((cit, i) => (
                    <div key={i} className="rounded border border-slate-200 bg-white p-2 text-[11px] text-slate-700">
                      <div className="font-bold text-teal-800">
                        {cit.akta_code} — {cit.section}
                      </div>
                      <p className="mt-0.5 line-clamp-3">{cit.text}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
