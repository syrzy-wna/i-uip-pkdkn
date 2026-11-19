"use client";

import React, { useState } from "react";
import {
  Check,
  Copy,
  Eye,
  EyeOff,
  FolderOpen,
  Loader2,
  Lock,
  RefreshCw,
  ShieldCheck,
} from "lucide-react";
import type { RedactResponse } from "@/lib/types";

interface RedactionPreviewProps {
  redaction: RedactResponse | null;
  loading: boolean;
  onRunRedaction: () => void;
  hasCaseInput?: boolean;
  onSwitchToInput?: () => void;
}

export default function RedactionPreview({
  redaction,
  loading,
  onRunRedaction,
  hasCaseInput = true,
  onSwitchToInput,
}: RedactionPreviewProps) {
  const [copied, setCopied] = useState(false);
  const [mobileView, setMobileView] = useState<"redacted" | "original">("redacted");
  const [highlightedToken, setHighlightedToken] = useState<string | null>(null);

  const handleCopy = () => {
    if (!redaction?.redacted_text) return;
    navigator.clipboard?.writeText(redaction.redacted_text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };

  const renderHighlightedTokens = (text: string): React.ReactNode => {
    const parts = text.split(/(\[[A-Z_]+_\d+\])/g);
    return parts.map((part, i) => {
      if (/^\[[A-Z_]+_\d+\]$/.test(part)) {
        const active = highlightedToken === part;
        return (
          <button
            key={i}
            type="button"
            onClick={() => setHighlightedToken(active ? null : part)}
            title="Klik untuk serlahkan maklumat asal di jadual bawah"
            className={`mx-0.5 inline-block rounded px-1 py-0.5 font-mono text-[11px] font-bold ring-1 transition ${
              active
                ? "bg-blue-600 text-white ring-blue-700"
                : "bg-amber-200 text-amber-950 ring-amber-400 hover:bg-amber-300"
            }`}
          >
            {part}
          </button>
        );
      }
      return <React.Fragment key={i}>{part}</React.Fragment>;
    });
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-200 bg-slate-50 p-3.5">
        <div className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-emerald-100 text-emerald-700">
            <Lock className="h-4 w-4" />
          </div>
          <div>
            <div className="text-xs font-extrabold text-slate-900">
              Privasi Data Peribadi (Patuh OSA 1972 &amp; PDPA)
            </div>
            <div className="text-[11px] text-slate-600">
              {redaction
                ? `${redaction.entities.length} maklumat peribadi ditutup secara automatik (nama PPKP IO dikekalkan).`
                : "Menutup nama OKT, saksi, No. K/P, Pasport, premis & SSM sebelum diproses AI awan."}
            </div>
          </div>
        </div>

        {hasCaseInput ? (
          <button
            type="button"
            disabled={loading}
            onClick={onRunRedaction}
            className="inline-flex min-h-[40px] items-center gap-1.5 rounded-lg bg-[#0f2744] px-3.5 py-2 text-xs font-bold text-white hover:bg-slate-800 disabled:opacity-60"
          >
            {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
            Semak &amp; Tutup Data Peribadi
          </button>
        ) : (
          onSwitchToInput && (
            <button
              type="button"
              onClick={onSwitchToInput}
              className="inline-flex min-h-[40px] items-center gap-1.5 rounded-lg bg-[#0f2744] px-3.5 py-2 text-xs font-bold text-white hover:bg-slate-800"
            >
              <FolderOpen className="h-3.5 w-3.5 text-amber-300" />
              Isi Fakta Kes Dahulu
            </button>
          )
        )}
      </div>

      {/* Panduan Jelas Apa Ditutup vs Dikekalkan */}
      <div className="grid grid-cols-1 gap-2 text-[11px] sm:grid-cols-2">
        <div className="rounded-lg border border-amber-200 bg-amber-50/70 px-3 py-2 text-amber-950">
          <strong>🔒 Ditutup Automatik:</strong> Nama OKT/Suspek, Saksi, No. K/P, Pasport, No. Telefon, Nama Premis &amp; No. SSM.
        </div>
        <div className="rounded-lg border border-emerald-200 bg-emerald-50/70 px-3 py-2 text-emerald-950">
          <strong>✓ Dikekalkan:</strong> Nama PPKP Penyiasat (IO), Seksyen Akta, Tarikh Kejadian &amp; Fakta Operasi untuk tujuan dokumen Word.
        </div>
      </div>

      {redaction?.warnings && redaction.warnings.length > 0 && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-2.5 text-xs text-amber-900">
          {redaction.warnings.map((w, idx) => (
            <div key={idx}>{w}</div>
          ))}
        </div>
      )}

      {!redaction ? (
        <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50/70 p-8 text-center text-xs text-slate-600">
          {hasCaseInput
            ? "Tekan 'Semak & Tutup Data Peribadi' di atas atau jalankan Semakan IP untuk melihat perbandingan teks yang ditutup."
            : "Sila masukkan catatan kes atau muat naik fail kes di Langkah 1 terlebih dahulu."}
        </div>
      ) : (
        <>
          {/* Penukar Paparan Mobile supaya tiada perangkap skrol */}
          <div className="grid grid-cols-2 gap-1 rounded-lg bg-slate-100 p-1 lg:hidden">
            <button
              type="button"
              onClick={() => setMobileView("redacted")}
              className={`min-h-[38px] rounded-md text-xs font-bold transition ${
                mobileView === "redacted"
                  ? "bg-white text-emerald-800 shadow-sm"
                  : "text-slate-600"
              }`}
            >
              Teks Disamarkan ({redaction.entities.length})
            </button>
            <button
              type="button"
              onClick={() => setMobileView("original")}
              className={`min-h-[38px] rounded-md text-xs font-bold transition ${
                mobileView === "original"
                  ? "bg-white text-slate-900 shadow-sm"
                  : "text-slate-600"
              }`}
            >
              Teks Asal Penuh
            </button>
          </div>

          <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
            <div
              className={`${
                mobileView === "redacted" ? "block" : "hidden lg:block"
              } rounded-lg border border-slate-200 bg-white p-3`}
            >
              <div className="mb-2 flex items-center justify-between border-b border-slate-100 pb-1.5">
                <span className="inline-flex items-center gap-1.5 text-xs font-bold text-emerald-800">
                  <EyeOff className="h-3.5 w-3.5" />
                  Teks Dihantar ke AI (Data Sulit Ditutup)
                </span>
                <button
                  type="button"
                  onClick={handleCopy}
                  className="inline-flex items-center gap-1 rounded bg-emerald-50 px-2 py-1 text-[10px] font-bold text-emerald-800 hover:bg-emerald-100"
                >
                  {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                  {copied ? "Disalin" : "Salin Teks"}
                </button>
              </div>
              <div className="max-h-72 overflow-y-auto whitespace-pre-wrap text-xs leading-relaxed text-slate-800">
                {renderHighlightedTokens(redaction.redacted_text)}
              </div>
            </div>

            <div
              className={`${
                mobileView === "original" ? "block" : "hidden lg:block"
              } rounded-lg border border-slate-200 bg-white p-3`}
            >
              <div className="mb-2 flex items-center justify-between border-b border-slate-100 pb-1.5">
                <span className="inline-flex items-center gap-1.5 text-xs font-bold text-slate-700">
                  <Eye className="h-3.5 w-3.5" />
                  Teks Asal (Dipulihkan dalam Word .docx)
                </span>
                <span className="inline-flex items-center gap-1 rounded bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-700">
                  <ShieldCheck className="h-3 w-3 text-blue-600" />
                  Selamat
                </span>
              </div>
              <div className="max-h-72 overflow-y-auto whitespace-pre-wrap text-xs leading-relaxed text-slate-700">
                {redaction.original_text}
              </div>
            </div>
          </div>

          <div className="rounded-lg border border-slate-200 bg-white p-3">
            <h4 className="mb-2 text-xs font-bold text-slate-800">
              Senarai Kod Penutup &amp; Maklumat Asal ({redaction.entities.length} Item — klik cip kuning di atas untuk sorot)
            </h4>
            {redaction.entities.length === 0 ? (
              <p className="text-xs text-slate-500">
                Tiada nama OKT, No. K/P, atau nama syarikat dijumpai dalam teks.
              </p>
            ) : (
              <>
                {/* Paparan Kad Mesra Mobile (< sm) */}
                <div className="space-y-1.5 sm:hidden">
                  {redaction.entities.map((ent) => {
                    const active = highlightedToken === ent.token;
                    return (
                      <div
                        key={ent.token}
                        className={`rounded-lg border p-2 text-xs ${
                          active ? "border-blue-500 bg-blue-50" : "border-slate-200 bg-slate-50/60"
                        }`}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-mono font-bold text-amber-800">{ent.token}</span>
                          <span className="rounded bg-white px-1.5 py-0.5 text-[10px] font-semibold text-slate-600 ring-1 ring-slate-200">
                            {ent.category}
                          </span>
                        </div>
                        <div className="mt-1 font-semibold text-slate-900">{ent.original}</div>
                      </div>
                    );
                  })}
                </div>

                {/* Paparan Jadual Desktop (>= sm) */}
                <div className="hidden overflow-x-auto sm:block">
                  <table className="w-full border-collapse text-left text-xs">
                    <thead>
                      <tr className="border-b border-slate-200 bg-slate-50 text-[11px] text-slate-600">
                        <th className="px-2.5 py-1.5">Kod Ganti</th>
                        <th className="px-2.5 py-1.5">Kategori</th>
                        <th className="px-2.5 py-1.5">Maklumat Asal (Dipulihkan dalam Word)</th>
                        <th className="px-2.5 py-1.5">Pengesan</th>
                      </tr>
                    </thead>
                    <tbody>
                      {redaction.entities.map((ent) => {
                        const active = highlightedToken === ent.token;
                        return (
                          <tr
                            key={ent.token}
                            className={`border-b border-slate-100 ${active ? "bg-blue-50" : ""}`}
                          >
                            <td className="px-2.5 py-1.5 font-mono font-bold text-amber-800">
                              {ent.token}
                            </td>
                            <td className="px-2.5 py-1.5 text-slate-600">{ent.category}</td>
                            <td className="px-2.5 py-1.5 font-medium text-slate-900">
                              {ent.original}
                            </td>
                            <td className="px-2.5 py-1.5">
                              <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-semibold text-slate-700">
                                {ent.source}
                              </span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </>
            )}
          </div>
        </>
      )}
    </div>
  );
}
