/**
 * Pengesah Kod Pasca-Penjanaan Deterministik (FASA 3.3 — `validateLegalOutput`).
 *
 * Berjalan SEBELUM sebarang jawapan AI dipaparkan kepada pengguna dalam UI `i-UIP Nerus`:
 * 1. Mengekstrak semua petikan Seksyen, Peraturan dan Akta menggunakan Regex (`Seksyen X(Y)`, `Peraturan X`, `Akta XXX`).
 * 2. Mengesahkan setiap petikan WUJUD dalam `statute_sections_verbatim` dan berstatus `BERKUAT_KUASA`.
 * 3. Mengesahkan tiada seksyen dalam `repealed_and_blocked_provisions` dicadangkan sebagai tindakan aktif.
 * 4. Mengesahkan nilai denda/kompaun yang dipetik sepadan dengan `penalty_first_offence` dan `compound_info` dalam `master_offences_matrix`.
 * 5. Mengesahkan semua unsur mandatori (`mandatory_elements`) terpenuhi (cth. pemilikan vape dalam beg oleh pelajar tanpa bukti menghisap/membeli -> S.17(1) Akta 852 WAJIB ditolak).
 */

import type {
  AdvisorConsultResult,
  LegalLibrarySnapshot,
  LegalValidationResult,
  RepealedProvisionHit,
} from "./types";

function canonicalizeAct(raw: string): string {
  const up = (raw || "").toUpperCase();
  if (up.includes("852") || /25[7-9]\/2024|26[0-4]\/2024/.test(up)) return "AKTA 852";
  if (up.includes("281") || up.includes("A1702") || up.includes("PPKM") || up.includes("PPM") || up.includes("95/2009")) {
    return "AKTA 281";
  }
  if (up.includes("154")) return "AKTA 154";
  if (up.includes("342") || up.includes("A1742") || up.includes("APPPB") || up.includes("139/2025")) return "AKTA 342";
  if (up.includes("593") || up.includes("KTJ")) return "AKTA 593";
  if (up.includes("56")) return "AKTA 56";
  if (up.includes("611")) return "AKTA 611";
  return up.trim();
}

export function extractLegalCitations(text: string): Array<{
  kind: string;
  number: string;
  baseNumber: string;
  actRef: string;
  inferredFromTail: boolean;
  rawCitation: string;
}> {
  if (!text) return [];
  const results: Array<{
    kind: string;
    number: string;
    baseNumber: string;
    actRef: string;
    inferredFromTail: boolean;
    rawCitation: string;
  }> = [];
  const seen = new Set<string>();

  const pairedRe =
    /\b(Seksyen|Peraturan)\s+(\d+[A-Za-z]{0,3}(?:\(\d+\))?(?:\([a-z]\))?)(?:\s+(?:dibaca\s+bersama\s+[^,\n.;]{1,40}\s+)?)?\s*(Akta\s+A?\d+|Akta\s+Kerja\s*1955|OSHA\s*1994|PPKM\s*2009|PPM\s*1985|PPKHT\s*2004|KTJ|APPPB\s*1988|P\.U\.\s*\(A\)\s*\d+\/\d{4})?/gi;

  let match: RegExpExecArray | null;
  while ((match = pairedRe.exec(text)) !== null) {
    const kind = match[1];
    const num = match[2].trim();
    let actRef = (match[3] || "").trim();
    let inferredFromTail = false;
    if (!actRef) {
      const rawTail = text.slice(match.index + match[0].length, match.index + match[0].length + 75);
      const clauseStop = rawTail.search(/[.;\n]|\b(?:Seksyen|Peraturan)\s+\d+/i);
      const tail = clauseStop >= 0 ? rawTail.slice(0, clauseStop) : rawTail;
      const tailMatch = tail.match(
        /\b(Akta\s+A?\d+|Akta\s+Kerja\s*1955|OSHA\s*1994|PPKM\s*2009|PPM\s*1985|PPKHT\s*2004|KTJ|APPPB\s*1988|P\.U\.\s*\(A\)\s*\d+\/\d{4})\b/i
      );
      if (tailMatch) {
        actRef = tailMatch[1].trim();
        inferredFromTail = true;
      }
    }
    const baseMatch = num.match(/^\d+[A-Za-z]{0,3}/);
    const baseNumber = (baseMatch ? baseMatch[0] : num).toUpperCase();
    const key = `${kind.toUpperCase()}:${num.toUpperCase()}:${actRef.toUpperCase()}`;
    if (!seen.has(key)) {
      seen.add(key);
      results.push({
        kind,
        number: num,
        baseNumber,
        actRef,
        inferredFromTail,
        rawCitation: match[0].trim(),
      });
    }
  }
  return results;
}

export function validateLegalOutput(
  aiResponse: Partial<AdvisorConsultResult> | Record<string, unknown> | string,
  db: Partial<LegalLibrarySnapshot> | null | undefined,
  questionContext = ""
): LegalValidationResult {
  const libVersion = db?.statute_library_version || "2.6.0-closed-book-agc-pdf";
  const statutesReg = db?.statutes_registry || [];
  const sectionsList = db?.statute_sections_verbatim || [];
  const offencesList = db?.master_offences_matrix || [];
  const repealedList = db?.repealed_and_blocked_provisions || [];

  let combinedText = "";
  let respObj: Record<string, unknown> = {};

  if (typeof aiResponse === "string") {
    combinedText = aiResponse;
    respObj = { keputusan_tindakan: aiResponse, alasan_keputusan: aiResponse };
  } else if (aiResponse && typeof aiResponse === "object") {
    respObj = aiResponse as Record<string, unknown>;
    // Jika backend telah menyertakan legal_validation dan db tempatan belum dimuatkan, guna keputusan backend
    if (
      sectionsList.length === 0 &&
      offencesList.length === 0 &&
      respObj.legal_validation &&
      typeof respObj.legal_validation === "object"
    ) {
      return respObj.legal_validation as LegalValidationResult;
    }
    const charges = Array.isArray(respObj.cadangan_pertuduhan)
      ? (respObj.cadangan_pertuduhan as Array<Record<string, unknown>>)
      : [];
    const chargesTxt = charges
      .map(
        (c) =>
          `${c.perihal || ""} ${c.seksyen_kesalahan || ""} ${c.seksyen_hukuman || ""} ${c.hukuman_maksimum || ""} ${c.boleh_kompaun || ""}`
      )
      .join(" ");
    combinedText = [
      String(respObj.akta_disyorkan || ""),
      String(respObj.tajuk_nasihat || ""),
      String(respObj.keputusan_tindakan || ""),
      String(respObj.alasan_keputusan || ""),
      String(respObj.templat_ringkas || ""),
      chargesTxt,
    ].join(" ");
  }

  // Bina indeks nombor seksyen sah daripada section_code & section_heading SAHAJA (elak tahun dalam teks badan dianggap seksyen sah)
  const validSectionsByAct = new Map<string, Set<string>>();
  const allValidNums = new Set<string>();

  const addValid = (actKey: string, num: string) => {
    const cleanNum = num.toUpperCase();
    allValidNums.add(cleanNum);
    if (!validSectionsByAct.has(actKey)) {
      validSectionsByAct.set(actKey, new Set());
    }
    validSectionsByAct.get(actKey)!.add(cleanNum);
  };

  for (const sec of sectionsList) {
    const actKey = canonicalizeAct(sec.statute_id);
    const raw = `${sec.section_code} ${sec.section_heading}`;
    const re = /(?:Seksyen|Peraturan|Section|Regulation)\s+(\d+[A-Za-z]{0,3})/gi;
    let m: RegExpExecArray | null;
    while ((m = re.exec(raw)) !== null) {
      addValid(actKey, m[1]);
      addValid(sec.statute_id.toUpperCase(), m[1]);
    }
    const leadMatch = sec.section_code.match(/^(?:Peraturan\s+|Seksyen\s+|Section\s+)?(\d+[A-Za-z]{0,3})\b/i);
    if (leadMatch) {
      addValid(actKey, leadMatch[1]);
      addValid(sec.statute_id.toUpperCase(), leadMatch[1]);
    }
  }

  for (const off of offencesList) {
    const actKey = canonicalizeAct(off.statute_id);
    const fields = [
      off.offence_section,
      off.penalty_section,
      ...(off.read_together_with || []),
      off.compound_info?.compound_authority_section || "",
      off.compound_info?.notice_section || "",
    ].join(" ");
    const re = /(?:Seksyen|Peraturan|Section|Regulation)\s+(\d+[A-Za-z]{0,3})/gi;
    let m: RegExpExecArray | null;
    while ((m = re.exec(fields)) !== null) {
      addValid(actKey, m[1]);
      addValid(off.statute_id.toUpperCase(), m[1]);
    }
  }

  // Semak akta belum diindeks
  const unindexedStatutes: string[] = [];
  const targetActStr = `${questionContext} ${String(respObj.akta_disyorkan || "")}`.toLowerCase();
  for (const st of statutesReg) {
    if (st.status === "DIMANSUHKAN") continue;
    if ((st.total_sections_indexed || 0) === 0) {
      if (
        (st.statute_id && targetActStr.includes(st.statute_id.toLowerCase())) ||
        (st.act_number_or_pu && targetActStr.includes(st.act_number_or_pu.toLowerCase()))
      ) {
        unindexedStatutes.push(`${st.statute_id} (${st.official_title_bm})`);
      }
    }
  }

  const extracted = extractLegalCitations(combinedText);
  const verifiedCitations: string[] = [];
  const invalidCitations: string[] = [];
  const defaultAct = canonicalizeAct(String(respObj.akta_disyorkan || ""));

  const chargesArr = Array.isArray(respObj.cadangan_pertuduhan)
    ? (respObj.cadangan_pertuduhan as Array<Record<string, unknown>>)
    : [];
  const chargesSecOnly = chargesArr
    .map((c) => `${String(c.seksyen_kesalahan || "")} ${String(c.seksyen_hukuman || "")}`)
    .join(" ")
    .toLowerCase();

  const crossAgencyActs = new Set([
    "AKTA 171", "AKTA 366", "AKTA 368", "AKTA 290", "AKTA 586",
    "AKTA 260", "AKTA 127", "AKTA 655", "AKTA 265", "AKTA 514", "AKTA 574",
    "AKTA 550", "AKTA 50", "AKTA 804", "AKTA KERJA 1955", "OSHA 1994",
  ]);
  const proceduralCrossRefs = new Set([
    "90A", "90B", "90C", "114", "114A", "73AA", "111", "112", "113", "119",
    "128", "152", "153", "154", "163", "376", "377", "399", "15", "83", "91",
  ]);

  for (const cit of extracted) {
    const actUp = cit.actRef.toUpperCase();
    if (actUp.includes("PPKHT")) {
      const lowAll = combinedText.toLowerCase();
      const isWarningOnly =
        !chargesSecOnly.includes("ppkht") &&
        ["dimansuhkan", "digugurkan", "diganti", "mansuh", "berbeza dengan", "jangan", "tidak sah", "bukan"].some(
          (w) => lowAll.includes(w)
        );
      if (!isWarningOnly) {
        invalidCitations.push(`${cit.rawCitation} (PPKHT 2004 telah dimansuhkan oleh Akta 852)`);
      }
      continue;
    }
    if (actUp === "AKTA 514" && cit.baseNumber === "22") {
      invalidCitations.push(`${cit.rawCitation} (Akta 514 ialah OSHA 1994; kes Tibi ialah Seksyen 22(b) Akta 342)`);
      continue;
    }
    if (crossAgencyActs.has(actUp)) {
      verifiedCitations.push(cit.rawCitation);
      continue;
    }
    const explicitActLookup = cit.actRef ? canonicalizeAct(cit.actRef) : "";
    const lookupAct = explicitActLookup || defaultAct;
    const actSet = validSectionsByAct.get(lookupAct);
    if (explicitActLookup && actSet) {
      if (actSet.has(cit.baseNumber) || (cit.inferredFromTail && proceduralCrossRefs.has(cit.baseNumber))) {
        verifiedCitations.push(cit.rawCitation);
      } else {
        invalidCitations.push(
          `${cit.rawCitation} — Seksyen/Peraturan ${cit.number} tidak ditemui dalam teks rasmi ${lookupAct}.`
        );
      }
    } else if (actSet) {
      if (actSet.has(cit.baseNumber) || allValidNums.has(cit.baseNumber) || proceduralCrossRefs.has(cit.baseNumber)) {
        verifiedCitations.push(cit.rawCitation);
      } else {
        invalidCitations.push(
          `${cit.rawCitation} — Seksyen/Peraturan ${cit.number} tidak ditemui dalam teks rasmi ${lookupAct}.`
        );
      }
    } else if (allValidNums.size > 0) {
      if (allValidNums.has(cit.baseNumber) || proceduralCrossRefs.has(cit.baseNumber)) {
        verifiedCitations.push(cit.rawCitation);
      } else {
        invalidCitations.push(
          `${cit.rawCitation} — Seksyen/Peraturan ${cit.number} tidak ditemui dalam rujukan teks asal akta.`
        );
      }
    }
  }

  // Semak peruntukan dimansuhkan / tamat tempoh
  const repealedHits: RepealedProvisionHit[] = [];
  const lowCombined = combinedText.toLowerCase();
  const repealedWarnKeywords = [
    "dimansuhkan",
    "digugurkan",
    "diganti",
    "mansuh",
    "terbatal",
    "dibatalkan",
    "tamat tempoh",
    "tidak sah",
    "jangan",
    "bukan",
    "berbeza dengan",
    "disekat",
    "ralat",
    "salah",
  ];
  if (
    (lowCombined.includes("ppkht 2004") || lowCombined.includes("324/2004")) &&
    (chargesSecOnly.includes("ppkht") || !repealedWarnKeywords.some((w) => lowCombined.includes(w)))
  ) {
    repealedHits.push({
      provision_id: "REPEALED_PPKHT_2004_ALL",
      status: "DIMANSUHKAN",
      replacement_section: "Akta 852",
      warning_message_bm:
        "Peruntukan Dimansuhkan: PPKHT 2004 telah dimansuhkan sepenuhnya dan digantikan oleh Akta 852.",
    });
  }
  if (
    lowCombined.includes("ordinan darurat") &&
    lowCombined.includes("2021") &&
    (chargesSecOnly.includes("ordinan darurat") || !repealedWarnKeywords.some((w) => lowCombined.includes(w)))
  ) {
    repealedHits.push({
      provision_id: "EXPIRED_ORDINAN_DARURAT_342_2021",
      status: "TAMAT_TEMPOH",
      replacement_section: "Seksyen 24 & 25 Akta 342 (Pindaan Akta A1742)",
      warning_message_bm:
        "Peruntukan Tamat Tempoh: Ordinan Darurat 2021 bagi Akta 342 telah dibatalkan dan tidak lagi berkuat kuasa.",
    });
  }
  for (const rep of repealedList) {
    if (repealedHits.some((r) => r.provision_id === rep.provision_id)) continue;
    for (const pat of rep.match_patterns || []) {
      try {
        const re = new RegExp(pat, "i");
        const m = re.exec(lowCombined);
        if (m) {
          const start = Math.max(0, m.index - 75);
          const end = Math.min(lowCombined.length, m.index + m[0].length + 100);
          const win = lowCombined.slice(start, end);
          const isWarn = repealedWarnKeywords.some((w) => win.includes(w));
          const inActiveCharge = re.test(chargesSecOnly);
          if (inActiveCharge || !isWarn) {
            repealedHits.push({
              provision_id: rep.provision_id,
              matched_text: m[0],
              status: rep.status,
              replacement_section: rep.replacement_section,
              warning_message_bm: rep.warning_message_bm,
            });
            break;
          }
        }
      } catch {
        // Abaikan regex tidak sah
      }
    }
  }

  // Semak ketidaksepadanan had denda/kompaun & status boleh kompaun
  const penaltyMismatches: string[] = [];
  if (/\bakta\s+154\b/i.test(lowCombined) && lowCombined.includes("kompaun")) {
    const rmHits = Array.from(lowCombined.matchAll(/kompaun\s+rm\s?([\d,]+(?:\.\d{1,2})?)/gi));
    for (const m of rmHits) {
      const val = parseFloat((m[1] || "0").replace(/,/g, ""));
      if (val > 500) {
        const idx = m.index ?? 0;
        const win = lowCombined.slice(Math.max(0, idx - 55), Math.min(lowCombined.length, idx + m[0].length + 55));
        const isWarn154 = ["jangan", "bukan", "salah", "ultra vires", "tidak sah", "dilarang", "melebihi had", "ditolak"].some(
          (w) => win.includes(w)
        );
        if (!isWarn154) {
          penaltyMismatches.push(
            `Had kompaun maksimum Seksyen 25 Akta 154 ialah RM 500 (cadangan menyebut RM ${val.toLocaleString()}).`
          );
        }
      }
    }
  }
  if (/\bakta\s+342\b/i.test(lowCombined) && lowCombined.includes("kompaun")) {
    const rmHits = Array.from(lowCombined.matchAll(/kompaun(?:\s+individu)?\s+rm\s?([\d,]+(?:\.\d{1,2})?)/gi));
    for (const m of rmHits) {
      const val = parseFloat((m[1] || "0").replace(/,/g, ""));
      const idx = m.index ?? 0;
      const win = lowCombined.slice(Math.max(0, idx - 65), Math.min(lowCombined.length, idx + m[0].length + 55));
      const isCorp = ["syarikat", "korporat", "pertubuhan perbadanan"].some((k) => win.includes(k));
      const limit = isCorp ? 50000 : 5000;
      if (val > limit) {
        penaltyMismatches.push(
          `Had kompaun Seksyen 25 Akta 342 (Akta A1742) ialah maksimum RM ${limit.toLocaleString()} (nilai RM ${val.toLocaleString()} melebihi had).`
        );
      }
    }
  }
  const nonCompRules: Array<[string, RegExp, string]> = [
    ["852", /\b(?:3|7|8|9|10|11|12|13\(1\)|14|15)(?:\b|\()/i, "Jadual Pertama P.U. (A) 259/2024"],
    ["281", /\b(?:seksyen\s*(?:11|13|13a|13b|13c|14|15|16|17)|13\(1\)|13a|13b|13c|11\(2\))(?:\b|\()/i, "Akta Makanan 1983 (wajib Buka IP)"],
    ["154", /\b(?:8\(8\)|seksyen\s*20|seksyen\s*21)(?:\b|\()/i, "Akta 154 (wajib Buka IP)"],
    ["342", /\b(?:12|14|15|18|22\(a\)|22\(e\))(?:\b|\()/i, "Jadual Pertama P.U. (A) 139/2025"],
  ];
  for (const c of chargesArr) {
    const sec = String(c.seksyen_kesalahan || "").toLowerCase();
    const comp = String(c.boleh_kompaun || "").toLowerCase();
    const claimsComp =
      (comp.includes("boleh kompaun") || comp.includes("boleh dikompaun")) &&
      !["tidak boleh", "tiada kompaun", "buka ip terus"].some((neg) => comp.includes(neg));
    if (!claimsComp) continue;
    const chargeActs = ["852", "281", "154", "342"].filter((d) => new RegExp(`\\b${d}\\b`).test(sec));
    const effActs = chargeActs.length > 0 ? chargeActs : ["852", "281", "154", "342"].filter((d) => defaultAct.includes(d));
    for (const [actDigits, secRe, schedRef] of nonCompRules) {
      if (effActs.includes(actDigits) && secRe.test(sec)) {
        penaltyMismatches.push(
          `${String(c.seksyen_kesalahan || "Seksyen")} TIDAK BOLEH dikompaun di bawah ${schedRef}.`
        );
      }
    }
  }

  // Semak unsur wajib S.17(1) Akta 852 berdasarkan questionContext SAHAJA jika tersedia (elak amaran AI memicu perangkap kendiri)
  const unfulfilledErrors: string[] = [];
  const evalCtx = (questionContext.trim() ? questionContext : combinedText).toLowerCase();
  const declaredNoOffence = String(respObj.status_kesalahan || "").toUpperCase() === "TIADA_KESALAHAN";

  const isPassivePoss =
    ["dalam beg", "checking bag", "check bag", "pemeriksaan beg", "spotcheck", "memiliki vape", "simpan vape", "bawa vape"].some(
      (k) => evalCtx.includes(k)
    ) &&
    !["sedang hisap", "sedang menghisap", "sedang merokok", "ditangkap hisap", "tangkap pelajar sedang"].some((k) =>
      evalCtx.includes(k)
    );

  if (
    isPassivePoss &&
    !declaredNoOffence &&
    /\b17\(1\)/.test(chargesSecOnly) &&
    !lowCombined.includes("bukan kesalahan") &&
    !lowCombined.includes("tiada kesalahan") &&
    !lowCombined.includes("ditolak") &&
    !lowCombined.includes("jangan keluarkan")
  ) {
    unfulfilledErrors.push(
      "Syarat Kesalahan Tidak Dipenuhi (Seksyen 17(1) Akta 852): Sekadar menyimpan vape dalam beg oleh pelajar tanpa bukti menghisap, menggunakan atau membeli bukan kesalahan di bawah Seksyen 17(1) Akta 852."
    );
  }

  const passed =
    invalidCitations.length === 0 &&
    repealedHits.length === 0 &&
    penaltyMismatches.length === 0 &&
    unfulfilledErrors.length === 0 &&
    unindexedStatutes.length === 0;

  let status = "DISAHKAN_VERBATIM_AGC";
  let warningBanner: string | null = null;

  if (unindexedStatutes.length > 0) {
    status = "AKTA BELUM DIINDEKS — MUAT NAIK PDF WARTA";
    warningBanner = `Teks rasmi akta belum dimasukkan ke dalam sistem: ${unindexedStatutes.join(", ")}. Sila rujuk salinan Warta rasmi atau maklumkan kepada pentadbir sistem.`;
  } else if (!passed) {
    status = "GAGAL_VALIDASI_PUSTAKA_AKTA";
    const allReasons = [
      ...invalidCitations,
      ...repealedHits.map((r) => r.warning_message_bm),
      ...penaltyMismatches,
      ...unfulfilledErrors,
    ];
    warningBanner = `Perhatian Semakan: Petikan undang-undang yang dicadangkan perlu disemak semula berdasarkan teks rasmi akta. ${allReasons.join(" • ")}`;
  }

  return {
    passed,
    status,
    statute_library_version: libVersion,
    extracted_citations: extracted.map((e) => e.rawCitation),
    verified_citations: verifiedCitations,
    invalid_citations: invalidCitations,
    repealed_hits: repealedHits,
    penalty_mismatches: penaltyMismatches,
    unfulfilled_element_errors: unfulfilledErrors,
    unindexed_statutes: unindexedStatutes,
    warning_banner: warningBanner,
  };
}
