"use client";

import React, { useState } from "react";
import { Check, Copy, Eye, EyeOff, Loader2, Lock, RefreshCw, ShieldCheck } from "lucide-react";
import type { RedactResponse } from "@/lib/types";

interface RedactionPreviewProps {
  redaction: RedactResponse | null;
  loading: boolean;
  onRunRedaction: () => void;
}

function renderHighlightedTokens(text: string): React.ReactNode {
  const parts = text.split(/(\[[A-Z_]+_\d+\])/g);
  return parts.map((part, i) => {
    if (/^\[[A-Z_]+_\d+\]$/.test(part)) {
      return (
        <span
          key={i}
          className="mx-0.5 inline-block rounded bg-amber-200 px-1 py-0.5 font-mono text-[11px] font-bold text-amber-950 ring-1 ring-amber-400"
        >
          {part}
        </span>
      );
    }
    return <React.Fragment key={i}>{part}</React.Fragment>;
  });
}

export default function RedactionPreview({
  redaction,
  loading,
  onRunRedaction,
}: RedactionPreviewProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (!redaction?.redacted_text) return;
    navigator.clipboard?.writeText(redaction.redacted_text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-200 bg-slate-50 p-3">
        <div className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-emerald-100 text-emerald-700">
            <Lock className="h-4 w-4" />
          </div>
          <div>
            <div className="text-xs font-bold text-slate-900">
              Penyamaran Data Sulit Tempatan (Patuh OSA &amp; PDPA)
            </div>
            <div className="text-[11px] text-slate-600">
              {redaction
                ? `Enjin: ${redaction.engine_used} • ${redaction.entities.length} maklumat peribadi ditutup (nama PPKP IO dikekalkan).`
                : "Menutup nama OKT, saksi, No. K/P, Pasport, nama premis & No. SSM sebelum diproses AI awan."}
            </div>
          </div>
        </div>

        <button
          type="button"
          disabled={loading}
          onClick={onRunRedaction}
          className="inline-flex items-center gap-1.5 rounded-lg bg-[#0f2744] px-3 py-1.5 text-xs font-semibold text-white hover:bg-slate-800 disabled:opacity-60"
        >
          {loading ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <RefreshCw className="h-3.5 w-3.5" />
          )}
          Jalankan Penyamaran Data Sulit (PDPA/OSA)
        </button>
      </div>

      {redaction?.warnings && redaction.warnings.length > 0 && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-2.5 text-xs text-amber-900">
          {redaction.warnings.map((w, idx) => (
            <div key={idx}>{w}</div>
          ))}
        </div>
      )}

      {!redaction ? (
        <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50/70 p-8 text-center text-xs text-slate-500">
          Tekan <strong>Jalankan Penyamaran Data Sulit (PDPA/OSA)</strong> atau jalankan Semakan IP untuk melihat data peribadi yang ditutup.
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
            <div className="rounded-lg border border-slate-200 bg-white p-3">
              <div className="mb-2 flex items-center justify-between border-b border-slate-100 pb-1.5">
                <span className="inline-flex items-center gap-1.5 text-xs font-bold text-emerald-800">
                  <EyeOff className="h-3.5 w-3.5" />
                  Teks Dihantar ke AI Awan (Data Sulit Ditutup)
                </span>
                <button
                  type="button"
                  onClick={handleCopy}
                  className="inline-flex items-center gap-1 rounded bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold text-emerald-800 hover:bg-emerald-100"
                >
                  {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                  {copied ? "Disalin" : "Salin Teks"}
                </button>
              </div>
              <div className="max-h-72 overflow-y-auto whitespace-pre-wrap font-mono text-[11px] leading-relaxed text-slate-800">
                {renderHighlightedTokens(redaction.redacted_text)}
              </div>
            </div>

            <div className="rounded-lg border border-slate-200 bg-white p-3">
              <div className="mb-2 flex items-center justify-between border-b border-slate-100 pb-1.5">
                <span className="inline-flex items-center gap-1.5 text-xs font-bold text-slate-700">
                  <Eye className="h-3.5 w-3.5" />
                  Teks Asal (Dipulihkan dalam Dokumen Word)
                </span>
                <span className="inline-flex items-center gap-1 rounded bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-700">
                  <ShieldCheck className="h-3 w-3 text-blue-600" />
                  Kekal Dalam PC
                </span>
              </div>
              <div className="max-h-72 overflow-y-auto whitespace-pre-wrap font-mono text-[11px] leading-relaxed text-slate-700">
                {redaction.original_text}
              </div>
            </div>
          </div>

          <div className="rounded-lg border border-slate-200 bg-white p-3">
            <h4 className="mb-2 text-xs font-bold text-slate-800">
              Senarai Kod Penutup &amp; Maklumat Asal ({redaction.entities.length} Item)
            </h4>
            {redaction.entities.length === 0 ? (
              <p className="text-xs text-slate-500">
                Tiada nama OKT, No. K/P, atau nama syarikat dijumpai dalam teks.
              </p>
            ) : (
              <div className="overflow-x-auto">
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
                    {redaction.entities.map((ent) => (
                      <tr key={ent.token} className="border-b border-slate-100">
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
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
