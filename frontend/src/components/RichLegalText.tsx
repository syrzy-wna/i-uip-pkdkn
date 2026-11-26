"use client";

import React from "react";

interface RichLegalTextProps {
  text: string;
  className?: string;
  onOpenSop?: (sopCode: string) => void;
}

const SOP_CODE_RE = /\b(UIP-(?:AKPMDKA|APSPP|APPPB|UMUM)-\d{2}-\d{2})\b/g;

function renderInlineTokens(
  line: string,
  keyPrefix: string,
  onOpenSop?: (sopCode: string) => void
): React.ReactNode[] {
  // Split inline formatting: **bold**, `code`, [NOTA PINDAAN], [KRITIKAL...], [AMARAN...], [LULUS], and SOP codes
  const tokenRe =
    /(\*\*[^*]+\*\*|`[^`]+`|\[NOTA PINDAAN[^\]]*\]|\[KRITIKAL[^\]]*\]|\[AMARAN[^\]]*\]|\[LULUS\]|\[INFO SOP\]|\bUIP-(?:AKPMDKA|APSPP|APPPB|UMUM)-\d{2}-\d{2}\b)/g;
  const parts = line.split(tokenRe);
  return parts.map((part, idx) => {
    const key = `${keyPrefix}-${idx}`;
    if (!part) return null;

    if (part.startsWith("**") && part.endsWith("**") && part.length > 4) {
      return (
        <strong key={key} className="font-semibold text-slate-900">
          {renderInlineTokens(part.slice(2, -2), `${key}-b`, onOpenSop)}
        </strong>
      );
    }
    if (part.startsWith("`") && part.endsWith("`") && part.length > 2) {
      const inner = part.slice(1, -1);
      if (onOpenSop && /^UIP-(?:AKPMDKA|APSPP|APPPB|UMUM)-\d{2}-\d{2}$/i.test(inner)) {
        return (
          <button
            key={key}
            type="button"
            onClick={() => onOpenSop(inner.toUpperCase())}
            className="mx-0.5 inline-flex items-center rounded bg-indigo-50 px-1.5 py-0.5 font-mono text-[11px] font-semibold text-indigo-700 underline decoration-indigo-300 underline-offset-2 hover:bg-indigo-100"
          >
            {inner}
          </button>
        );
      }
      return (
        <code
          key={key}
          className="mx-0.5 rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[11px] font-medium text-slate-800"
        >
          {inner}
        </code>
      );
    }
    if (part.startsWith("[NOTA PINDAAN")) {
      return (
        <span
          key={key}
          className="mx-0.5 inline-flex items-center rounded-md border border-amber-300 bg-amber-50 px-1.5 py-0.5 text-[11px] font-bold text-amber-900"
        >
          {part}
        </span>
      );
    }
    if (part.startsWith("[KRITIKAL")) {
      return (
        <span
          key={key}
          className="mx-0.5 inline-flex items-center rounded-md border border-rose-300 bg-rose-50 px-1.5 py-0.5 text-[11px] font-bold text-rose-800"
        >
          {part}
        </span>
      );
    }
    if (part.startsWith("[AMARAN")) {
      return (
        <span
          key={key}
          className="mx-0.5 inline-flex items-center rounded-md border border-amber-300 bg-amber-50 px-1.5 py-0.5 text-[11px] font-bold text-amber-800"
        >
          {part}
        </span>
      );
    }
    if (part === "[LULUS]") {
      return (
        <span
          key={key}
          className="mx-0.5 inline-flex items-center rounded-md border border-emerald-300 bg-emerald-50 px-1.5 py-0.5 text-[11px] font-bold text-emerald-800"
        >
          {part}
        </span>
      );
    }
    if (part === "[INFO SOP]") {
      return (
        <span
          key={key}
          className="mx-0.5 inline-flex items-center rounded-md border border-sky-300 bg-sky-50 px-1.5 py-0.5 text-[11px] font-bold text-sky-800"
        >
          {part}
        </span>
      );
    }
    if (onOpenSop && SOP_CODE_RE.test(part)) {
      SOP_CODE_RE.lastIndex = 0;
      return (
        <button
          key={key}
          type="button"
          onClick={() => onOpenSop(part.toUpperCase())}
          className="mx-0.5 inline-flex items-center rounded bg-indigo-50 px-1.5 py-0.5 font-mono text-[11px] font-semibold text-indigo-700 underline decoration-indigo-300 underline-offset-2 hover:bg-indigo-100"
        >
          {part}
        </button>
      );
    }
    SOP_CODE_RE.lastIndex = 0;
    return <React.Fragment key={key}>{part}</React.Fragment>;
  });
}

/**
 * Pemapar teks perundangan & Markdown tulen React (0% dangerouslySetInnerHTML / selamat XSS).
 * Menyokong tajuk, senarai bernombor/peluru, jadual Markdown, lencana [NOTA PINDAAN]/[KRITIKAL],
 * serta pautan klik terus ke kod SOP rasmi KKM.
 */
export default function RichLegalText({
  text,
  className = "",
  onOpenSop,
}: RichLegalTextProps) {
  const normalized = (text || "").replace(/\r\n/g, "\n").trim();
  if (!normalized) return null;

  const lines = normalized.split("\n");
  const blocks: React.ReactNode[] = [];
  let i = 0;

  while (i < lines.length) {
    const raw = lines[i];
    const trimmed = raw.trim();

    if (!trimmed) {
      i += 1;
      continue;
    }

    if (/^-{3,}$/.test(trimmed) || /^\*{3,}$/.test(trimmed)) {
      blocks.push(<hr key={`hr-${i}`} className="my-3 border-slate-200" />);
      i += 1;
      continue;
    }

    // Markdown heading (# / ## / ### / ####)
    const hMatch = trimmed.match(/^(#{1,4})\s+(.+)$/);
    if (hMatch) {
      const level = hMatch[1].length;
      const content = hMatch[2].trim();
      const cls =
        level === 1
          ? "mt-4 mb-2 text-base font-bold text-slate-900 border-b border-slate-200 pb-1"
          : level === 2
          ? "mt-3.5 mb-1.5 text-sm font-bold text-slate-900"
          : "mt-3 mb-1 text-xs font-bold uppercase tracking-wide text-indigo-800";
      blocks.push(
        <div key={`h-${i}`} className={cls}>
          {renderInlineTokens(content, `h-${i}`, onOpenSop)}
        </div>
      );
      i += 1;
      continue;
    }

    // Markdown table
    if (
      trimmed.startsWith("|") &&
      i + 1 < lines.length &&
      /^\|[\s:|-]+\|?$/.test(lines[i + 1].trim())
    ) {
      const headerCells = trimmed
        .split("|")
        .map((c) => c.trim())
        .filter((c, idx, arr) => !(idx === 0 && !c) && !(idx === arr.length - 1 && !c));
      i += 2;
      const bodyRows: string[][] = [];
      while (i < lines.length && lines[i].trim().startsWith("|")) {
        const rowCells = lines[i]
          .trim()
          .split("|")
          .map((c) => c.trim())
          .filter((c, idx, arr) => !(idx === 0 && !c) && !(idx === arr.length - 1 && !c));
        bodyRows.push(rowCells);
        i += 1;
      }
      blocks.push(
        <div key={`tbl-${i}`} className="my-2.5 overflow-x-auto rounded-lg border border-slate-200">
          <table className="min-w-full divide-y divide-slate-200 text-xs">
            <thead className="bg-slate-50">
              <tr>
                {headerCells.map((hc, cIdx) => (
                  <th
                    key={`th-${cIdx}`}
                    className="px-3 py-2 text-left font-semibold text-slate-700"
                  >
                    {renderInlineTokens(hc, `th-${i}-${cIdx}`, onOpenSop)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {bodyRows.map((row, rIdx) => (
                <tr key={`tr-${rIdx}`} className="hover:bg-slate-50/70">
                  {row.map((cell, cIdx) => (
                    <td key={`td-${cIdx}`} className="px-3 py-2 align-top text-slate-700">
                      {renderInlineTokens(cell, `td-${i}-${rIdx}-${cIdx}`, onOpenSop)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
      continue;
    }

    // Bullet list
    if (/^[-*•]\s+/.test(trimmed)) {
      const items: string[] = [];
      const startIdx = i;
      while (i < lines.length && /^[-*•]\s+/.test(lines[i].trim())) {
        items.push(lines[i].trim().replace(/^[-*•]\s+/, ""));
        i += 1;
      }
      blocks.push(
        <ul key={`ul-${startIdx}`} className="my-1.5 list-disc space-y-1 pl-5 text-slate-700">
          {items.map((it, liIdx) => (
            <li key={`li-${startIdx}-${liIdx}`} className="leading-relaxed">
              {renderInlineTokens(it, `li-${startIdx}-${liIdx}`, onOpenSop)}
            </li>
          ))}
        </ul>
      );
      continue;
    }

    // Numbered list
    if (/^\d+\.\s+/.test(trimmed)) {
      const items: Array<{ num: string; body: string }> = [];
      const startIdx = i;
      while (i < lines.length && /^\d+\.\s+/.test(lines[i].trim())) {
        const m = lines[i].trim().match(/^(\d+)\.\s+(.+)$/);
        if (m) items.push({ num: m[1], body: m[2] });
        i += 1;
      }
      blocks.push(
        <ol key={`ol-${startIdx}`} className="my-2 space-y-1.5 text-slate-700">
          {items.map((it, liIdx) => (
            <li key={`oli-${startIdx}-${liIdx}`} className="flex gap-2 leading-relaxed">
              <span className="mt-0.5 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-indigo-50 text-[11px] font-bold text-indigo-700">
                {it.num}
              </span>
              <span className="flex-1">
                {renderInlineTokens(it.body, `oli-${startIdx}-${liIdx}`, onOpenSop)}
              </span>
            </li>
          ))}
        </ol>
      );
      continue;
    }

    // Callout paragraph starting with [NOTA PINDAAN] or [KRITIKAL
    if (trimmed.startsWith("[NOTA PINDAAN") || trimmed.startsWith("[KRITIKAL")) {
      const isCrit = trimmed.startsWith("[KRITIKAL");
      blocks.push(
        <div
          key={`call-${i}`}
          className={`my-2 rounded-lg border px-3 py-2 text-xs leading-relaxed ${
            isCrit
              ? "border-rose-200 bg-rose-50/80 text-rose-900"
              : "border-amber-200 bg-amber-50/80 text-amber-950"
          }`}
        >
          {renderInlineTokens(trimmed, `call-${i}`, onOpenSop)}
        </div>
      );
      i += 1;
      continue;
    }

    // Standard paragraph (join contiguous plain lines)
    const paraLines: string[] = [trimmed];
    const startIdx = i;
    i += 1;
    while (
      i < lines.length &&
      lines[i].trim() !== "" &&
      !/^(#{1,4}\s+|[-*•]\s+|\d+\.\s+|\||-{3,}$|\*{3,}$|\[NOTA PINDAAN|\[KRITIKAL)/.test(
        lines[i].trim()
      )
    ) {
      paraLines.push(lines[i].trim());
      i += 1;
    }
    blocks.push(
      <p key={`p-${startIdx}`} className="my-1.5 leading-relaxed text-slate-700">
        {renderInlineTokens(paraLines.join(" "), `p-${startIdx}`, onOpenSop)}
      </p>
    );
  }

  return <div className={`text-sm ${className}`}>{blocks}</div>;
}
