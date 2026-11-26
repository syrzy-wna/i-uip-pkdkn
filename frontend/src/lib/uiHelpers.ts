import { useEffect } from "react";

/**
 * Salin teks ke papan keratan dengan sokongan sandaran (fallback) pada rangkaian HTTP tempatan (LAN PKD).
 */
export async function copyTextSafe(text: string): Promise<boolean> {
  if (typeof window === "undefined") return false;
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch {
    // Teruskan ke kaedah sandaran textarea
  }
  try {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.setAttribute("readonly", "true");
    ta.style.position = "fixed";
    ta.style.left = "-9999px";
    ta.style.top = "0";
    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    const ok = document.execCommand("copy");
    document.body.removeChild(ta);
    return ok;
  } catch {
    return false;
  }
}

/**
 * Kunci skrol latar belakang halaman apabila modal atau laci (drawer) dibuka.
 */
let _activeModalLocks = 0;
let _savedBodyOverflow = "";

export function useLockBodyScroll(active: boolean): void {
  useEffect(() => {
    if (!active || typeof document === "undefined") return;
    if (_activeModalLocks === 0) {
      _savedBodyOverflow = document.body.style.overflow;
      document.body.style.overflow = "hidden";
    }
    _activeModalLocks += 1;
    return () => {
      _activeModalLocks = Math.max(0, _activeModalLocks - 1);
      if (_activeModalLocks === 0) {
        document.body.style.overflow = _savedBodyOverflow;
      }
    };
  }, [active]);
}

/**
 * Mengekstrak amaun kompaun lazim yang SAH mengikut Akta/Seksyen — mengelak tersalah ambil nilai denda mahkamah.
 */
export function extractRecommendedCompoundRm(
  sectionText: string,
  compoundDesc: string
): string {
  const sec = (sectionText || "").toLowerCase();
  const desc = (compoundDesc || "").trim();
  const descLow = desc.toLowerCase();

  // 1. Semak kadar rasmi khusus yang sering bercanggah dengan angka denda mahkamah / siling maksimum dalam teks penerangan
  if (sec.includes("852") || /25[7-9]\/2024|26[0-4]\/2024/.test(sec)) {
    if (sec.includes("17(1)") || sec.includes("13(3)")) {
      return "RM 50.00";
    }
    if (sec.includes("16(2)") || sec.includes("18(1)")) {
      return "RM 250.00";
    }
  }
  if (sec.includes("154")) {
    return "RM 500.00";
  }
  if (sec.includes("ppkm") || sec.includes("95/2009")) {
    if (/(?<!\w)(?:8|30|31|32|33)(?:\([123]\))?(?!\w)/.test(sec)) {
      return "RM 250.00";
    }
    if (/(?<!\w)11(?:\(1\))?(?!\w)/.test(sec)) {
      return "RM 500.00";
    }
  }
  if (sec.includes("342") || sec.includes("139/2025")) {
    return "RM 1,000.00";
  }

  // 2. Utamakan 'tawaran lazim' / 'kompaun lazim' dahulu sebelum 'kompaun maksimum'
  const lazyRateMatch = desc.match(
    /(?:tawaran\s+(?:lazim|kompaun)|kompaun\s+lazim|kadar\s+lazim)\s*:?\s*RM\s*([\d,]+(?:\.\d{1,2})?)/i
  );
  if (lazyRateMatch) {
    const val = parseFloat(lazyRateMatch[1].replace(/,/g, ""));
    if (!Number.isNaN(val) && val > 0) {
      return `RM ${val.toFixed(2)}`;
    }
  }

  const targetedMatch =
    desc.match(/(?:kompaun(?:\s+maks(?:imum)?)?|iaitu|=)\s*:?\s*RM\s*([\d,]+(?:\.\d{1,2})?)/i) ||
    desc.match(/RM\s*([\d,]+(?:\.\d{1,2})?)\s*(?:\(\s*individu|\s*bagi\s+individu|\s*di\s+bawah|\s*—|\s*\[)/i);

  if (targetedMatch) {
    const val = parseFloat(targetedMatch[1].replace(/,/g, ""));
    if (!Number.isNaN(val) && val > 0) {
      // Jika hanya siling RM5,000 PPKM/Akta 281 ditemui tanpa kadar khusus, guna kadar tawaran lazim lapangan RM 250.00
      if (val >= 5000 && (sec.includes("ppkm") || sec.includes("281") || descLow.includes("seksyen 33"))) {
        return "RM 250.00";
      }
      return `RM ${val.toFixed(2)}`;
    }
  }

  // 3. Fallback: ambil nilai RM terakhir jika terdapat ungkapan "50% daripada denda RMX ... RMY"
  const allMatches = Array.from(desc.matchAll(/RM\s*([\d,]+(?:\.\d{1,2})?)/gi));
  if (allMatches.length >= 2 && (descLow.includes("50%") || descLow.includes("separuh") || descLow.includes("denda"))) {
    const lastVal = parseFloat(allMatches[allMatches.length - 1][1].replace(/,/g, ""));
    if (!Number.isNaN(lastVal) && lastVal > 0) {
      return `RM ${lastVal.toFixed(2)}`;
    }
  }
  if (allMatches.length >= 1) {
    const firstVal = parseFloat(allMatches[0][1].replace(/,/g, ""));
    if (!Number.isNaN(firstVal) && firstVal > 0 && firstVal < 5000) {
      return `RM ${firstVal.toFixed(2)}`;
    }
  }

  return "RM 250.00";
}

const MALAY_MONTHS = [
  "Januari",
  "Februari",
  "Mac",
  "April",
  "Mei",
  "Jun",
  "Julai",
  "Ogos",
  "September",
  "Oktober",
  "November",
  "Disember",
];

/**
 * Format tarikh & masa semasa dalam Bahasa Melayu rasmi (cth: "24 November 2026, 10.30 pagi").
 */
export function formatDateTimeNowMalay(includeTime = true): string {
  const now = new Date();
  const dd = now.getDate();
  const month = MALAY_MONTHS[now.getMonth()] || "";
  const yyyy = now.getFullYear();
  if (!includeTime) {
    return `${dd} ${month} ${yyyy}`;
  }
  const h24 = now.getHours();
  const mins = String(now.getMinutes()).padStart(2, "0");
  const period = h24 < 12 ? "pagi" : h24 < 14 ? "tengah hari" : h24 < 19 ? "petang" : "malam";
  const h12 = h24 % 12 === 0 ? 12 : h24 % 12;
  return `${dd} ${month} ${yyyy}, ${h12}.${mins} ${period}`;
}
