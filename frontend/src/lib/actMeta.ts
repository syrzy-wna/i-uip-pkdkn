/**
 * Metadata berpusat bagi semua Akta KKM Teras dan Akta Prosedur / Rujukan Silang Persekutuan
 * (Akta 852, 281, 154, 342, 593, 574, 344, 388, 92, 56, 611).
 */

export const OFFLINE_LEGAL_CACHE_KEY = "uip_offline_legal_library_v3";

export interface ActOptionMeta {
  value: string;
  label: string;
  shortLabel: string;
  category: "core_kkm" | "support_legal";
  compoundableByPpkp: boolean;
}

export const CORE_KKM_ACTS: ActOptionMeta[] = [
  {
    value: "Akta 852",
    label: "Akta 852 — Produk Merokok & Vape (2024)",
    shortLabel: "Akta 852 (Merokok/Vape)",
    category: "core_kkm",
    compoundableByPpkp: true,
  },
  {
    value: "Akta 281",
    label: "Akta 281 — Makanan 1983, PPKM 2009 & PPM 1985",
    shortLabel: "Akta 281 & PPKM 2009",
    category: "core_kkm",
    compoundableByPpkp: true,
  },
  {
    value: "Akta 154",
    label: "Akta 154 — Aedes & Serangga Pembawa Penyakit",
    shortLabel: "Akta 154 (Aedes)",
    category: "core_kkm",
    compoundableByPpkp: true,
  },
  {
    value: "Akta 342",
    label: "Akta 342 — Penyakit Berjangkit / Tibi (Pindaan A1742)",
    shortLabel: "Akta 342 (Tibi/Berjangkit)",
    category: "core_kkm",
    compoundableByPpkp: true,
  },
];

export const SUPPORT_LEGAL_ACTS: ActOptionMeta[] = [
  {
    value: "Akta 593",
    label: "Akta 593 — Kanun Tatacara Jenayah (KTJ)",
    shortLabel: "Akta 593 (KTJ)",
    category: "support_legal",
    compoundableByPpkp: false,
  },
  {
    value: "Akta 574",
    label: "Akta 574 — Kanun Keseksaan (Halang/Ugut/Palsu · PDRM)",
    shortLabel: "Akta 574 (Kanun Keseksaan)",
    category: "support_legal",
    compoundableByPpkp: false,
  },
  {
    value: "Akta 344",
    label: "Akta 344 — Akta Polis 1967 (Bantuan/Iringan Polis)",
    shortLabel: "Akta 344 (Akta Polis)",
    category: "support_legal",
    compoundableByPpkp: false,
  },
  {
    value: "Akta 388",
    label: "Akta 388 — Akta Tafsiran 1948 & 1967 (Had Masa/Serahan)",
    shortLabel: "Akta 388 (Tafsiran 1948/1967)",
    category: "support_legal",
    compoundableByPpkp: false,
  },
  {
    value: "Akta 92",
    label: "Akta 92 — Akta Mahkamah Rendah 1948 (Majistret/Sesyen)",
    shortLabel: "Akta 92 (Mahkamah Rendah)",
    category: "support_legal",
    compoundableByPpkp: false,
  },
  {
    value: "Akta 56",
    label: "Akta 56 — Akta Keterangan 1950 (Seksyen 90A)",
    shortLabel: "Akta 56 (Keterangan)",
    category: "support_legal",
    compoundableByPpkp: false,
  },
  {
    value: "Akta 611",
    label: "Akta 611 — Akta Kanak-Kanak 2001 (OBD/Privasi)",
    shortLabel: "Akta 611 (Kanak-Kanak)",
    category: "support_legal",
    compoundableByPpkp: false,
  },
];

export const ALL_ACT_OPTIONS: ActOptionMeta[] = [...CORE_KKM_ACTS, ...SUPPORT_LEGAL_ACTS];

export const CORE_ACT_CODES = ["Akta 852", "Akta 281", "Akta 154", "Akta 342"] as const;

export const SECONDARY_ACT_CODES = [
  "Akta 593",
  "Akta 574",
  "Akta 344",
  "Akta 388",
  "Akta 92",
  "Akta 56",
  "Akta 611",
  "Akta Lain / Rujukan Silang",
] as const;

export function canonicalizeActCode(raw: string): string {
  const up = (raw || "").toUpperCase().trim();
  if (!up) return "";
  if (/\b852\b|AKTA_852|25[7-9]\/2024|26[0-4]\/2024/.test(up)) return "Akta 852";
  if (/\b281\b|AKTA_281|A1702|\bPPKM\b|\bPPM\b|95\/2009|437\/1985/.test(up)) return "Akta 281";
  if (/\b154\b|AKTA_154/.test(up)) return "Akta 154";
  if (/\b342\b|AKTA_342|A1742|\bAPPPB\b|139\/2025/.test(up)) return "Akta 342";
  if (/\b593\b|AKTA_593|\bKTJ\b|\bCPC\b|TATACARA\s+JENAYAH/.test(up)) return "Akta 593";
  if (/\b574\b|AKTA_574|KANUN\s+KESEKSAAN|PENAL\s+CODE/.test(up)) return "Akta 574";
  if (/\b344\b|AKTA_344|AKTA\s+POLIS|POLICE\s+ACT/.test(up)) return "Akta 344";
  if (/\b388\b|AKTA_388|TAFSIRAN|INTERPRETATION/.test(up)) return "Akta 388";
  if (/(?:^|[^0-9])(?:AKTA[\s_]*)?92(?:[^0-9]|$)|MAHKAMAH\s+RENDAH|SUBORDINATE\s+COURTS/.test(up)) {
    return "Akta 92";
  }
  if (/(?:^|[^0-9])(?:AKTA[\s_]*)?56(?:[^0-9]|$)|KETERANGAN|EVIDENCE\s+ACT/.test(up)) {
    return "Akta 56";
  }
  if (/\b611\b|AKTA_611|KANAK-KANAK|CHILD\s+ACT/.test(up)) return "Akta 611";
  return raw.trim();
}

export function isCompoundableKkmAct(aktaCode?: string | null): boolean {
  const canon = canonicalizeActCode(aktaCode || "");
  return (
    canon === "Akta 852" ||
    canon === "Akta 281" ||
    canon === "Akta 154" ||
    canon === "Akta 342"
  );
}

export function isPdrmReferralAct(aktaCode?: string | null): boolean {
  const canon = canonicalizeActCode(aktaCode || "");
  return canon === "Akta 574" || canon === "Akta 344";
}

export function getActBadgeStyle(aktaCode: string): {
  badge: string;
  headerBg: string;
  pillActive: string;
} {
  const canon = canonicalizeActCode(aktaCode);
  switch (canon) {
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
    case "Akta 593":
      return {
        badge: "bg-sky-800 text-white",
        headerBg: "border-sky-200 bg-sky-50/70",
        pillActive: "bg-sky-800 text-white border-sky-800",
      };
    case "Akta 574":
      return {
        badge: "bg-red-800 text-white",
        headerBg: "border-red-200 bg-red-50/70",
        pillActive: "bg-red-800 text-white border-red-800",
      };
    case "Akta 344":
      return {
        badge: "bg-blue-800 text-white",
        headerBg: "border-blue-200 bg-blue-50/70",
        pillActive: "bg-blue-800 text-white border-blue-800",
      };
    case "Akta 388":
      return {
        badge: "bg-violet-700 text-white",
        headerBg: "border-violet-200 bg-violet-50/70",
        pillActive: "bg-violet-700 text-white border-violet-700",
      };
    case "Akta 92":
      return {
        badge: "bg-teal-800 text-white",
        headerBg: "border-teal-200 bg-teal-50/70",
        pillActive: "bg-teal-800 text-white border-teal-800",
      };
    case "Akta 56":
      return {
        badge: "bg-cyan-800 text-white",
        headerBg: "border-cyan-200 bg-cyan-50/70",
        pillActive: "bg-cyan-800 text-white border-cyan-800",
      };
    case "Akta 611":
      return {
        badge: "bg-fuchsia-800 text-white",
        headerBg: "border-fuchsia-200 bg-fuchsia-50/70",
        pillActive: "bg-fuchsia-800 text-white border-fuchsia-800",
      };
    default:
      return {
        badge: "bg-slate-700 text-white",
        headerBg: "border-slate-200 bg-slate-100/80",
        pillActive: "bg-slate-800 text-white border-slate-800",
      };
  }
}
