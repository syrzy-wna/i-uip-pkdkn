"use client";

import React, { useState } from "react";
import {
  Check,
  ChevronDown,
  ChevronUp,
  Copy,
  Eye,
  EyeOff,
  FolderOpen,
  Loader2,
  Lock,
  RefreshCw,
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
  const [textView, setTextView] = useState<"redacted" | "original">("redacted");
  const [highlightedToken, setHighlightedToken] = useState<string | null>(null);
  const [showRuleHint, setShowRuleHint] = useState(false);

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
            title="Klik untuk serlahkan maklumat asal di senarai bawah"
            className={`mx-0.5 inline-block rounded px-1.5 py-0.5 font-mono text-xs font-bold ring-1 transition ${
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
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-slate-50/70 p-4">
        <div className="flex items-start gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-emerald-100 text-emerald-700">
            <Lock className="h-4 w-4" />
          </div>
          <div>
            <div className="text-sm font-extrabold text-slate-900">
              Penyamaran Data Peribadi (OSA 1972 &amp; PDPA)
            </div>
            <p className="mt-0.5 text-xs text-slate-600">
              {redaction
                ? `${redaction.entities.length} maklumat peribadi ditutup sementara dan dipulihkan automatik dalam fail Word (.docx).`
                : "Maklumat sulit ditutup sementara semasa analisis kes dan dipulihkan semula dalam fail Word."}
            </p>
            <button
              type="button"
              onClick={() => setShowRuleHint((v) => !v)}
              className="mt-1 inline-flex items-center gap-1 text-xs font-semibold text-blue-700 hover:underline"
            >
              Apa maklumat yang dilindungi?
              {showRuleHint ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
            </button>
          </div>
        </div>

        {hasCaseInput ? (
          <button
            type="button"
            disabled={loading}
            onClick={onRunRedaction}
            className="inline-flex min-h-[40px] items-center gap-1.5 rounded-xl bg-[#0f2744] px-4 py-2 text-xs font-bold text-white hover:bg-slate-800 disabled:opacity-60"
          >
            {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
            Semak Penyamaran Data
          </button>
        ) : (
          onSwitchToInput && (
            <button
              type="button"
              onClick={onSwitchToInput}
              className="inline-flex min-h-[40px] items-center gap-1.5 rounded-xl bg-[#0f2744] px-4 py-2 text-xs font-bold text-white hover:bg-slate-800"
            >
              <FolderOpen className="h-3.5 w-3.5 text-amber-300" />
              Isi Fakta Kes Dahulu
            </button>
          )
        )}
      </div>

      {showRuleHint && (
        <div className="grid grid-cols-1 gap-2.5 text-xs sm:grid-cols-2">
          <div className="rounded-xl border border-amber-200 bg-amber-50/70 p-3 text-amber-950">
            <strong>Ditutup Automatik:</strong> Nama OKT/Suspek, Saksi, No. K/P, Pasport, No. Telefon, Nama Premis &amp; No. SSM.
          </div>
          <div className="rounded-xl border border-emerald-200 bg-emerald-50/70 p-3 text-emerald-950">
            <strong>Dikekalkan:</strong> Nama PPKP Penyiasat (IO), Seksyen Akta, Tarikh Kejadian &amp; Fakta Operasi untuk dokumen Word.
          </div>
        </div>
      )}

      {redaction?.warnings && redaction.warnings.length > 0 && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900">
          {redaction.warnings.map((w, idx) => (
            <div key={idx}>{w}</div>
          ))}
        </div>
      )}

      {!redaction ? (
        <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50/70 p-8 text-center text-xs text-slate-600">
          {hasCaseInput
            ? "Tekan 'Semak Penyamaran Data' di atas untuk melihat maklumat sulit yang dilindungi."
            : "Masukkan fakta kes atau muat naik fail kes dahulu untuk melihat perlindungan privasi data."}
        </div>
      ) : (
        <>
          {/* Paparan Tab Bersih (Sama Untuk Desktop & Mobile supaya teks tidak terhimpit) */}
          <div className="rounded-xl border border-slate-200 bg-white">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 px-3.5 py-2.5">
              <div className="inline-flex rounded-lg bg-slate-100 p-1">
                <button
                  type="button"
                  onClick={() => setTextView("redacted")}
                  className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-bold transition ${
                    textView === "redacted"
                      ? "bg-white text-emerald-800 shadow-sm"
                      : "text-slate-600 hover:text-slate-900"
                  }`}
                >
                  <EyeOff className="h-3.5 w-3.5" />
                  Teks Disamarkan ({redaction.entities.length})
                </button>
                <button
                  type="button"
                  onClick={() => setTextView("original")}
                  className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-bold transition ${
                    textView === "original"
                      ? "bg-white text-slate-900 shadow-sm"
                      : "text-slate-600 hover:text-slate-900"
                  }`}
                >
                  <Eye className="h-3.5 w-3.5" />
                  Teks Asal Penuh
                </button>
              </div>

              {textView === "redacted" && (
                <button
                  type="button"
                  onClick={handleCopy}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-bold text-slate-700 hover:bg-slate-50"
                >
                  {copied ? <Check className="h-3.5 w-3.5 text-emerald-600" /> : <Copy className="h-3.5 w-3.5" />}
                  {copied ? "Disalin" : "Salin Teks Selamat"}
                </button>
              )}
            </div>

            <div className="max-h-72 overflow-y-auto whitespace-pre-wrap p-4 text-xs leading-relaxed text-slate-800 sm:text-sm">
              {textView === "redacted"
                ? renderHighlightedTokens(redaction.redacted_text)
                : redaction.original_text}
            </div>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h4 className="mb-3 text-xs font-extrabold text-slate-800">
              Senarai Maklumat Dilindungi ({redaction.entities.length} Item)
            </h4>
            {redaction.entities.length === 0 ? (
              <p className="text-xs text-slate-500">
                Tiada nama OKT, No. K/P, atau nama syarikat dijumpai dalam teks.
              </p>
            ) : (
              <>
                <div className="space-y-2 sm:hidden">
                  {redaction.entities.map((ent) => {
                    const active = highlightedToken === ent.token;
                    return (
                      <div
                        key={ent.token}
                        className={`rounded-lg border p-2.5 text-xs ${
                          active ? "border-blue-500 bg-blue-50" : "border-slate-200 bg-slate-50/50"
                        }`}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-mono font-bold text-amber-800">{ent.token}</span>
                          <span className="rounded bg-white px-2 py-0.5 text-[11px] font-semibold text-slate-600 ring-1 ring-slate-200">
                            {ent.category}
                          </span>
                        </div>
                        <div className="mt-1 font-semibold text-slate-900">{ent.original}</div>
                      </div>
                    );
                  })}
                </div>

                <div className="hidden overflow-x-auto sm:block">
                  <table className="w-full border-collapse text-left text-xs">
                    <thead>
                      <tr className="border-b border-slate-200 bg-slate-50 text-xs font-bold text-slate-600">
                        <th className="px-3 py-2">Penyamaran</th>
                        <th className="px-3 py-2">Kategori</th>
                        <th className="px-3 py-2">Maklumat Asal (Dipulihkan dalam Word)</th>
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
                            <td className="px-3 py-2 font-mono font-bold text-amber-800">
                              {ent.token}
                            </td>
                            <td className="px-3 py-2 text-slate-600">{ent.category}</td>
                            <td className="px-3 py-2 font-medium text-slate-900">
                              {ent.original}
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
