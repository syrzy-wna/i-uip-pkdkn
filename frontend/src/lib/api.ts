import type {
  ActiveSopDetail,
  ActiveSopSummary,
  AdvisorAnsweredListResponse,
  AdvisorConsultResult,
  AdvisorScenarioItem,
  CompoundCheckResult,
  DemoAccountSummary,
  DevOverviewResponse,
  DevVaultCategory,
  DevVaultExportMode,
  DevVaultListResponse,
  DevVaultRecordDetail,
  DevVaultStorageHealth,
  DraftGenerationResponse,
  EvidenceExtractionResponse,
  IPAuditReport,
  IPCaseRecord,
  LegalCoverageReport,
  LegalLibrarySnapshot,
  LegalValidationResult,
  MasterOffenceRecord,
  NotisKompaunData,
  OffenderCategory,
  OfficerProfile,
  RedactResponse,
  RepealedProvisionRecord,
  RuntimeSettings,
  SampleCase,
  StatuteSectionVerbatim,
  StatutoryCitation,
  SystemStatus,
} from "./types";

const API_BASE = (() => {
  const configured = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (configured) return configured.replace(/\/$/, "");
  if (typeof window !== "undefined") {
    if (window.location.port === "3000") {
      return `${window.location.protocol}//${window.location.hostname}:8000`;
    }
    return "";
  }
  return "http://127.0.0.1:8000";
})();

function getAuthHeader(explicitToken?: string | null): Record<string, string> {
  const token =
    explicitToken ||
    (typeof window !== "undefined" ? window.localStorage.getItem("uip_auth_token") : null);
  if (!token) return {};
  return {
    Authorization: `Bearer ${token}`,
    "X-Auth-Token": token,
  };
}

async function fetchWithTimeout(
  url: string,
  init: RequestInit = {},
  timeoutMs = 20000
): Promise<Response> {
  const controller = new AbortController();
  const timer = globalThis.setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...init, signal: controller.signal });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new Error(
        "Sambungan ke sistem mengambil masa terlalu lama. Sila semak talian internet anda dan cuba semula."
      );
    }
    throw new Error(
      "Tidak dapat berhubung dengan sistem buat masa ini. Sila semak sambungan internet anda dan cuba semula."
    );
  } finally {
    globalThis.clearTimeout(timer);
  }
}

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function notifySessionExpiredIfNeeded(status: number, url: string): void {
  if (
    status === 401 &&
    typeof window !== "undefined" &&
    !url.includes("/api/auth/login") &&
    !url.includes("/api/auth/register") &&
    !url.includes("/api/auth/google")
  ) {
    window.dispatchEvent(new CustomEvent("uip:session-expired"));
  }
}

async function parseJsonOrThrow<T>(res: Response): Promise<T> {
  const rawText = await res.text();
  let parsed: Record<string, unknown> | null = null;
  if (rawText) {
    try {
      parsed = JSON.parse(rawText) as Record<string, unknown>;
    } catch {
      parsed = null;
    }
  }

  if (!res.ok) {
    notifySessionExpiredIfNeeded(res.status, res.url || "");
    let msg = `Sistem menghadapi gangguan sementara (Kod ${res.status}). Sila cuba sebentar lagi.`;
    if (res.status === 413) {
      msg = "Saiz fail melebihi had maksimum 15 MB. Sila kecilkan saiz fail dan cuba semula.";
    } else if (res.status >= 500) {
      msg = "Perkhidmatan sedang sibuk atau diselenggara buat sementara. Sila cuba semula sebentar lagi.";
    } else if (parsed && typeof parsed.detail === "string" && parsed.detail.trim()) {
      msg = parsed.detail;
    } else if (parsed && Array.isArray(parsed.detail)) {
      if (typeof console !== "undefined") {
        console.warn("Butiran pengesahan borang (422):", parsed.detail);
      }
      msg = "Maklumat yang dimasukkan tidak lengkap atau tidak sah. Sila semak semula semua ruangan wajib.";
    } else if (parsed && typeof parsed.message === "string" && parsed.message.trim()) {
      msg = parsed.message;
    } else if (rawText.trim()) {
      const stripped = rawText.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
      if (stripped && !/^(502|503|504|bad gateway|service unavailable)/i.test(stripped)) {
        msg = stripped.slice(0, 220);
      }
    }
    throw new ApiError(msg, res.status);
  }

  if (parsed !== null) {
    return parsed as T;
  }
  throw new ApiError(
    "Sistem gagal memproses maklum balas daripada pelayan. Sila cuba semula sebentar lagi.",
    res.status
  );
}

export async function fetchSystemStatus(): Promise<SystemStatus> {
  const res = await fetchWithTimeout(`${API_BASE}/api/status`, { cache: "no-store", headers: { ...getAuthHeader() } }, 15000);
  return parseJsonOrThrow<SystemStatus>(res);
}

export async function fetchRuntimeSettings(): Promise<RuntimeSettings> {
  const res = await fetchWithTimeout(
    `${API_BASE}/api/settings`,
    { cache: "no-store", headers: { ...getAuthHeader() } },
    15000
  );
  return parseJsonOrThrow<RuntimeSettings>(res);
}

export async function saveRuntimeSettings(payload: {
  gemini_api_key?: string;
  google_client_id?: string;
  ollama_base_url?: string;
  ollama_model?: string;
  standard_fallback_model?: string;
}): Promise<{ status: string; system_status: SystemStatus; settings: RuntimeSettings }> {
  const res = await fetchWithTimeout(`${API_BASE}/api/settings`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeader() },
    body: JSON.stringify(payload),
  });
  return parseJsonOrThrow(res);
}

export async function fetchSampleCases(): Promise<SampleCase[]> {
  const res = await fetchWithTimeout(`${API_BASE}/api/samples`, {
    cache: "no-store",
    headers: { ...getAuthHeader() },
  });
  const data = await parseJsonOrThrow<{ samples: SampleCase[] }>(res);
  return data.samples;
}

export async function fetchCases(): Promise<IPCaseRecord[]> {
  const res = await fetchWithTimeout(`${API_BASE}/api/cases`, {
    cache: "no-store",
    headers: { ...getAuthHeader() },
  });
  const data = await parseJsonOrThrow<{ cases: IPCaseRecord[] }>(res);
  return data.cases;
}

export async function saveCaseRecord(
  payload: Partial<IPCaseRecord>
): Promise<IPCaseRecord> {
  const res = await fetchWithTimeout(`${API_BASE}/api/cases`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeader() },
    body: JSON.stringify(payload),
  });
  const data = await parseJsonOrThrow<{ case: IPCaseRecord }>(res);
  return data.case;
}

export async function deleteCaseRecord(caseId: string): Promise<void> {
  const res = await fetchWithTimeout(`${API_BASE}/api/cases/${encodeURIComponent(caseId)}`, {
    method: "DELETE",
    headers: { ...getAuthHeader() },
  });
  await parseJsonOrThrow<{ deleted: boolean }>(res);
}

export async function runRedaction(
  text: string,
  useOllama: boolean
): Promise<RedactResponse> {
  const res = await fetchWithTimeout(
    `${API_BASE}/api/redact`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getAuthHeader() },
      body: JSON.stringify({ text, use_ollama: useOllama }),
    },
    30000
  );
  return parseJsonOrThrow<RedactResponse>(res);
}

export async function runIpAudit(params: {
  text: string;
  aktaUtama: string;
  useOllama: boolean;
  fastMode?: boolean;
  caseId?: string;
  file?: File | null;
}): Promise<IPAuditReport> {
  const form = new FormData();
  if (params.text) form.append("text", params.text);
  form.append("akta_utama", params.aktaUtama);
  form.append("use_ollama", String(params.useOllama));
  form.append("fast_mode", String(Boolean(params.fastMode)));
  if (params.caseId) form.append("case_id", params.caseId);
  if (params.file) form.append("file", params.file);
  const res = await fetchWithTimeout(
    `${API_BASE}/api/audit-ip`,
    {
      method: "POST",
      headers: { ...getAuthHeader() },
      body: form,
    },
    65000
  );
  return parseJsonOrThrow<IPAuditReport>(res);
}

export async function extractEvidence(
  file: File,
  docHint: string
): Promise<EvidenceExtractionResponse> {
  const form = new FormData();
  form.append("file", file);
  form.append("doc_hint", docHint);
  const res = await fetchWithTimeout(
    `${API_BASE}/api/extract-evidence`,
    {
      method: "POST",
      headers: { ...getAuthHeader() },
      body: form,
    },
    65000
  );
  return parseJsonOrThrow<EvidenceExtractionResponse>(res);
}

export async function generateDrafts(params: {
  caseText: string;
  aktaUtama: string;
  workflow: string;
  useOllama: boolean;
  fastMode?: boolean;
  caseId?: string;
  authToken?: string | null;
  officerProfile?: OfficerProfile | null;
}): Promise<DraftGenerationResponse> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...getAuthHeader(params.authToken),
  };
  const res = await fetchWithTimeout(
    `${API_BASE}/api/generate-draft`,
    {
      method: "POST",
      headers,
      body: JSON.stringify({
        case_text: params.caseText,
        akta_utama: params.aktaUtama,
        workflow: params.workflow,
        use_ollama: params.useOllama,
        fast_mode: params.fastMode ?? true,
        case_id: params.caseId,
        officer_profile: params.officerProfile || undefined,
      }),
    },
    65000
  );
  return parseJsonOrThrow<DraftGenerationResponse>(res);
}

export async function checkCompoundNotice(
  payload: NotisKompaunData
): Promise<CompoundCheckResult> {
  const res = await fetchWithTimeout(`${API_BASE}/api/check-compound`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeader() },
    body: JSON.stringify(payload),
  });
  return parseJsonOrThrow<CompoundCheckResult>(res);
}

export async function queryStatutoryRag(
  query: string,
  akta?: string
): Promise<{ engine: string; results: StatutoryCitation[] }> {
  const search = new URLSearchParams({ q: query, top_k: "4" });
  if (akta && akta !== "Semua") {
    search.set("akta", akta);
  }
  const res = await fetchWithTimeout(`${API_BASE}/api/rag/query?${search.toString()}`, {
    headers: { ...getAuthHeader() },
  });
  return parseJsonOrThrow<{ engine: string; results: StatutoryCitation[] }>(res);
}

export async function downloadDocx(
  docType:
    | "borang_114"
    | "saman_111"
    | "diari_siasatan"
    | "rakaman_112"
    | "pakej_ip"
    | "notis_kompaun",
  payload: Record<string, unknown>
): Promise<string> {
  const res = await fetchWithTimeout(
    `${API_BASE}/api/export-docx`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getAuthHeader() },
      body: JSON.stringify({ doc_type: docType, payload }),
    },
    45000
  );
  if (!res.ok) {
    notifySessionExpiredIfNeeded(res.status, res.url || "");
    await throwBlobResponseError(res, "Gagal memuat turun fail Word .docx");
  }
  const blob = await res.blob();
  const filename = extractFilenameFromDisposition(
    res.headers.get("Content-Disposition"),
    `${docType}.docx`
  );
  triggerBrowserBlobDownload(blob, filename);
  return filename;
}

// ---------------- Akaun Pegawai KKM Sebenar ----------------

export async function fetchDemoAccounts(): Promise<DemoAccountSummary[]> {
  const res = await fetchWithTimeout(`${API_BASE}/api/auth/demo-accounts`, { cache: "no-store" }, 15000);
  const data = await parseJsonOrThrow<{ accounts: DemoAccountSummary[] }>(res);
  return data.accounts;
}

export async function loginOfficer(
  email: string,
  password: string
): Promise<{ user: OfficerProfile; token: string }> {
  const res = await fetchWithTimeout(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  return parseJsonOrThrow<{ user: OfficerProfile; token: string }>(res);
}

export async function registerOfficer(
  payload: Record<string, string>
): Promise<{ user: OfficerProfile; token: string }> {
  const res = await fetchWithTimeout(`${API_BASE}/api/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseJsonOrThrow<{ user: OfficerProfile; token: string }>(res);
}

export async function googleSignInOfficer(payload: {
  id_token?: string;
  access_token?: string;
  kkm_authority_card_no?: string;
  grade?: string;
  designation?: string;
  district_pkd?: string;
  state_jkn?: string;
}): Promise<{ user: OfficerProfile; token: string; is_new_account?: boolean }> {
  const res = await fetchWithTimeout(`${API_BASE}/api/auth/google`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseJsonOrThrow<{ user: OfficerProfile; token: string; is_new_account?: boolean }>(res);
}

export async function fetchCurrentOfficer(token: string): Promise<OfficerProfile> {
  const res = await fetchWithTimeout(`${API_BASE}/api/auth/me`, {
    cache: "no-store",
    headers: { ...getAuthHeader(token) },
  });
  const data = await parseJsonOrThrow<{ user: OfficerProfile }>(res);
  return data.user;
}

export async function updateOfficerProfile(
  token: string,
  payload: Partial<OfficerProfile>
): Promise<OfficerProfile> {
  const res = await fetchWithTimeout(`${API_BASE}/api/auth/profile`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeader(token),
    },
    body: JSON.stringify(payload),
  });
  const data = await parseJsonOrThrow<{ user: OfficerProfile }>(res);
  return data.user;
}

export async function logoutOfficer(token: string): Promise<void> {
  await fetchWithTimeout(`${API_BASE}/api/auth/logout`, {
    method: "POST",
    headers: { ...getAuthHeader(token) },
  });
}

// ---------------- Tanya Pakar UIP ----------------

export async function fetchAdvisorScenarios(): Promise<AdvisorScenarioItem[]> {
  const res = await fetchWithTimeout(`${API_BASE}/api/advisor/scenarios`, {
    cache: "no-store",
    headers: { ...getAuthHeader() },
  });
  const data = await parseJsonOrThrow<{ scenarios: AdvisorScenarioItem[] }>(res);
  return data.scenarios;
}

export async function fetchAdvisorAnsweredQuestions(
  params: {
    akta?: string;
    q?: string;
    limit?: number;
    authToken?: string | null;
  } = {}
): Promise<AdvisorAnsweredListResponse> {
  const search = new URLSearchParams();
  if (params.akta && params.akta !== "Semua") search.set("akta", params.akta);
  if (params.q?.trim()) search.set("q", params.q.trim());
  search.set("limit", String(params.limit ?? 120));
  const res = await fetchWithTimeout(`${API_BASE}/api/advisor/answered?${search.toString()}`, {
    cache: "no-store",
    headers: { ...getAuthHeader(params.authToken) },
  });
  return parseJsonOrThrow<AdvisorAnsweredListResponse>(res);
}

export async function consultUipAdvisor(params: {
  question: string;
  aktaHint: string;
  scenarioId?: string;
  useAi?: boolean;
  authToken?: string | null;
  officerProfile?: OfficerProfile | null;
  conversationHistory?: Array<{ role: string; content: string }>;
}): Promise<AdvisorConsultResult> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...getAuthHeader(params.authToken),
  };
  const res = await fetchWithTimeout(
    `${API_BASE}/api/advisor/consult`,
    {
      method: "POST",
      headers,
      body: JSON.stringify({
        question: params.question,
        akta_hint: params.aktaHint,
        scenario_id: params.scenarioId || undefined,
        use_ai: Boolean(params.useAi),
        officer_profile: params.officerProfile || undefined,
        conversation_history:
          params.conversationHistory && params.conversationHistory.length > 0
            ? params.conversationHistory
            : undefined,
      }),
    },
    65000
  );
  return parseJsonOrThrow<AdvisorConsultResult>(res);
}

// ---------------- Konsol Pembangun & Arkib Vault Eksklusif (Dev g.dev/syrzy) ----------------

function extractFilenameFromDisposition(disposition: string | null, fallback: string): string {
  if (!disposition) return fallback;
  const utf8Match = disposition.match(/filename\*=UTF-8''([^;\n]+)/i);
  if (utf8Match?.[1]) {
    try {
      return decodeURIComponent(utf8Match[1].replace(/["']/g, ""));
    } catch {
      return fallback;
    }
  }
  const asciiMatch = disposition.match(/filename="?([^";\n]+)"?/i);
  return asciiMatch?.[1] || fallback;
}

async function throwBlobResponseError(res: Response, fallbackMsg: string): Promise<never> {
  const rawText = await res.text().catch(() => "");
  if (rawText) {
    try {
      const parsed = JSON.parse(rawText) as { detail?: string; message?: string };
      if (parsed.detail) throw new Error(parsed.detail);
      if (parsed.message) throw new Error(parsed.message);
    } catch (err) {
      if (err instanceof Error && err.message !== rawText) throw err;
    }
  }
  throw new Error(`${fallbackMsg} (${res.status})`);
}

function triggerBrowserBlobDownload(blob: Blob, filename: string): void {
  const url = window.URL.createObjectURL(blob);
  try {
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    anchor.rel = "noopener noreferrer";
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
  } finally {
    window.setTimeout(() => window.URL.revokeObjectURL(url), 1000);
  }
}

export async function fetchDevOverview(authToken?: string | null): Promise<DevOverviewResponse> {
  const res = await fetchWithTimeout(`${API_BASE}/api/dev/overview`, {
    cache: "no-store",
    headers: { ...getAuthHeader(authToken) },
  });
  return parseJsonOrThrow<DevOverviewResponse>(res);
}

export async function fetchDevVaultHealth(
  authToken?: string | null
): Promise<DevVaultStorageHealth> {
  const res = await fetchWithTimeout(`${API_BASE}/api/dev/vault/health`, {
    cache: "no-store",
    headers: { ...getAuthHeader(authToken) },
  });
  return parseJsonOrThrow<DevVaultStorageHealth>(res);
}

export async function fetchDevVaultRecords(
  params: {
    category?: DevVaultCategory;
    q?: string;
    userEmail?: string;
    hasFile?: boolean;
    limit?: number;
    offset?: number;
    authToken?: string | null;
  } = {}
): Promise<DevVaultListResponse> {
  const search = new URLSearchParams();
  if (params.category && params.category !== "ALL") search.set("category", params.category);
  if (params.q?.trim()) search.set("q", params.q.trim());
  if (params.userEmail?.trim()) search.set("user_email", params.userEmail.trim());
  if (params.hasFile) search.set("has_file", "true");
  search.set("limit", String(params.limit ?? 30));
  search.set("offset", String(params.offset ?? 0));

  const res = await fetchWithTimeout(`${API_BASE}/api/dev/vault/records?${search.toString()}`, {
    cache: "no-store",
    headers: { ...getAuthHeader(params.authToken) },
  });
  return parseJsonOrThrow<DevVaultListResponse>(res);
}

export async function fetchDevVaultRecordDetail(
  recordId: string,
  authToken?: string | null
): Promise<DevVaultRecordDetail> {
  const res = await fetchWithTimeout(
    `${API_BASE}/api/dev/vault/records/${encodeURIComponent(recordId)}`,
    {
      cache: "no-store",
      headers: { ...getAuthHeader(authToken) },
    }
  );
  return parseJsonOrThrow<DevVaultRecordDetail>(res);
}

export async function downloadDevVaultFile(
  recordId: string,
  fallbackFilename?: string,
  kind: "attachment" | "json" = "attachment",
  authToken?: string | null
): Promise<void> {
  const res = await fetchWithTimeout(
    `${API_BASE}/api/dev/vault/records/${encodeURIComponent(recordId)}/file?kind=${kind}`,
    {
      method: "GET",
      cache: "no-store",
      headers: { ...getAuthHeader(authToken) },
    },
    45000
  );
  if (!res.ok) {
    await throwBlobResponseError(res, "Gagal memuat turun fail dari Arkib Dev");
  }
  const blob = await res.blob();
  const filename = extractFilenameFromDisposition(
    res.headers.get("Content-Disposition"),
    fallbackFilename || (kind === "json" ? `${recordId}_dossier.json` : `arkib-${recordId}.bin`)
  );
  triggerBrowserBlobDownload(blob, filename);
}

export async function fetchDevVaultFilePreviewUrl(
  recordId: string,
  authToken?: string | null
): Promise<{ objectUrl: string; contentType: string }> {
  const res = await fetchWithTimeout(
    `${API_BASE}/api/dev/vault/records/${encodeURIComponent(recordId)}/file?kind=attachment`,
    {
      method: "GET",
      cache: "no-store",
      headers: { ...getAuthHeader(authToken) },
    },
    45000
  );
  if (!res.ok) {
    await throwBlobResponseError(res, "Gagal memuatkan pratonton imej");
  }
  const blob = await res.blob();
  return {
    objectUrl: window.URL.createObjectURL(blob),
    contentType: blob.type || res.headers.get("Content-Type") || "application/octet-stream",
  };
}

export async function exportDevVaultBundle(params: {
  mode: DevVaultExportMode;
  format?: "zip" | "jsonl";
  category?: DevVaultCategory;
  q?: string;
  userEmail?: string;
  includeFiles?: boolean;
  authToken?: string | null;
}): Promise<void> {
  const fmt = params.format || "zip";
  const res = await fetchWithTimeout(
    `${API_BASE}/api/dev/vault/export`,
    {
      method: "POST",
      cache: "no-store",
      headers: {
        "Content-Type": "application/json",
        ...getAuthHeader(params.authToken),
      },
      body: JSON.stringify({
        mode: params.mode,
        format: fmt,
        category: params.category && params.category !== "ALL" ? params.category : undefined,
        q: params.q?.trim() || undefined,
        user_email: params.userEmail?.trim() || undefined,
        include_files: params.includeFiles ?? true,
      }),
    },
    65000
  );
  if (!res.ok) {
    await throwBlobResponseError(res, "Gagal mengeksport pakej dokumentasi Arkib Dev");
  }
  const blob = await res.blob();
  const stamp = new Date().toISOString().slice(0, 10);
  const fallback =
    params.mode === "redacted"
      ? `iuip-dev-vault-redacted-${stamp}.${fmt}`
      : `iuip-dev-vault-full-${stamp}.${fmt}`;
  const filename = extractFilenameFromDisposition(
    res.headers.get("Content-Disposition"),
    fallback
  );
  triggerBrowserBlobDownload(blob, filename);
}

export async function retryDevVaultS3Sync(
  authToken?: string | null
): Promise<{ synced: number; failed: number; message: string }> {
  const res = await fetchWithTimeout(`${API_BASE}/api/dev/vault/retry-s3-sync`, {
    method: "POST",
    cache: "no-store",
    headers: { ...getAuthHeader(authToken) },
  }, 45000);
  return parseJsonOrThrow(res);
}

// ---------------- Pustaka Akta Penuh & Daftar Semua Kesalahan ----------------

export async function fetchLegalRegistry(
  authToken?: string | null
): Promise<LegalCoverageReport> {
  const res = await fetchWithTimeout(`${API_BASE}/api/legal/registry`, {
    cache: "no-store",
    headers: { ...getAuthHeader(authToken) },
  });
  return parseJsonOrThrow<LegalCoverageReport>(res);
}

export async function fetchLegalSnapshot(
  authToken?: string | null
): Promise<LegalLibrarySnapshot> {
  const res = await fetchWithTimeout(`${API_BASE}/api/legal/snapshot`, {
    cache: "no-store",
    headers: { ...getAuthHeader(authToken) },
  }, 30000);
  return parseJsonOrThrow<LegalLibrarySnapshot>(res);
}

export async function fetchLegalSections(
  params: {
    statuteId?: string;
    akta?: string;
    q?: string;
    authToken?: string | null;
  } = {}
): Promise<{
  total: number;
  sections: StatuteSectionVerbatim[];
  statute_library_version: string;
}> {
  const search = new URLSearchParams();
  if (params.statuteId) search.set("statute_id", params.statuteId);
  if (params.akta && params.akta !== "Semua") search.set("akta", params.akta);
  if (params.q?.trim()) search.set("q", params.q.trim());
  const res = await fetchWithTimeout(`${API_BASE}/api/legal/sections?${search.toString()}`, {
    cache: "no-store",
    headers: { ...getAuthHeader(params.authToken) },
  });
  return parseJsonOrThrow(res);
}

export async function fetchLegalOffences(
  params: {
    statuteId?: string;
    akta?: string;
    offenderCategory?: OffenderCategory | "SEMUA";
    isCompoundable?: boolean | null;
    q?: string;
    authToken?: string | null;
  } = {}
): Promise<{
  total: number;
  offences: MasterOffenceRecord[];
  statute_library_version: string;
}> {
  const search = new URLSearchParams();
  if (params.statuteId) search.set("statute_id", params.statuteId);
  if (params.akta && params.akta !== "Semua") search.set("akta", params.akta);
  if (params.offenderCategory && params.offenderCategory !== "SEMUA") {
    search.set("target_offender", params.offenderCategory);
  }
  if (typeof params.isCompoundable === "boolean") {
    search.set("is_compoundable", String(params.isCompoundable));
  }
  if (params.q?.trim()) search.set("q", params.q.trim());
  const res = await fetchWithTimeout(`${API_BASE}/api/legal/offences?${search.toString()}`, {
    cache: "no-store",
    headers: { ...getAuthHeader(params.authToken) },
  });
  return parseJsonOrThrow(res);
}

export async function fetchRepealedProvisions(
  authToken?: string | null
): Promise<{
  statute_library_version: string;
  provisions: RepealedProvisionRecord[];
}> {
  const res = await fetchWithTimeout(`${API_BASE}/api/legal/repealed`, {
    cache: "no-store",
    headers: { ...getAuthHeader(authToken) },
  });
  return parseJsonOrThrow(res);
}

export async function validateLegalOutputApi(
  aiResponse: unknown,
  questionContext?: string,
  authToken?: string | null
): Promise<LegalValidationResult> {
  const res = await fetchWithTimeout(`${API_BASE}/api/legal/validate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeader(authToken),
    },
    body: JSON.stringify({
      ai_response: aiResponse,
      question_context: questionContext || "",
    }),
  });
  return parseJsonOrThrow<LegalValidationResult>(res);
}

export async function ingestGazettePdf(params: {
  file: File;
  statuteId?: string;
  officialTitleBm?: string;
  actNumberOrPu?: string;
  verifiedByAdmin?: boolean;
  authToken?: string | null;
}): Promise<{
  status: string;
  filename: string;
  total_chunks_indexed: number;
  legal_library_ingest: {
    status: string;
    statute_id: string;
    canonical_akta_code: string;
    filename: string;
    source_pdf_hash: string;
    sections_extracted: number;
    new_offences_swept: number;
    total_sections_indexed: number;
    total_offences_indexed: number;
    verified_by_admin: boolean;
    statute_library_version: string;
  };
  stale_qa_cache_marked: number;
}> {
  const form = new FormData();
  form.append("file", params.file);
  if (params.statuteId) form.append("statute_id", params.statuteId);
  if (params.officialTitleBm) form.append("official_title_bm", params.officialTitleBm);
  if (params.actNumberOrPu) form.append("act_number_or_pu", params.actNumberOrPu);
  form.append("verified_by_admin", String(Boolean(params.verifiedByAdmin)));

  const res = await fetchWithTimeout(
    `${API_BASE}/api/legal/ingest`,
    {
      method: "POST",
      headers: { ...getAuthHeader(params.authToken) },
      body: form,
    },
    120000
  );
  return parseJsonOrThrow(res);
}

export async function verifyGazetteStatuteOrOffence(params: {
  statuteId?: string;
  offenceId?: string;
  verifiedByAdmin?: boolean;
  authToken?: string | null;
}): Promise<{
  updated_statutes: number;
  updated_offences: number;
  statute_library_version: string;
}> {
  const res = await fetchWithTimeout(`${API_BASE}/api/legal/verify`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeader(params.authToken),
    },
    body: JSON.stringify({
      statute_id: params.statuteId || undefined,
      offence_id: params.offenceId || undefined,
      verified: params.verifiedByAdmin ?? true,
    }),
  });
  return parseJsonOrThrow(res);
}

export async function updateMasterOffence(
  offenceId: string,
  payload: Partial<MasterOffenceRecord>,
  authToken?: string | null
): Promise<{
  status: string;
  offence: MasterOffenceRecord;
  statute_library_version: string;
  stale_qa_cache_marked: number;
}> {
  const res = await fetchWithTimeout(
    `${API_BASE}/api/legal/offences/${encodeURIComponent(offenceId)}`,
    {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        ...getAuthHeader(authToken),
      },
      body: JSON.stringify(payload),
    }
  );
  return parseJsonOrThrow(res);
}

export async function purgeAdvisorQaCache(
  aktaCode?: string,
  authToken?: string | null
): Promise<{
  status: string;
  stale_records_marked: number;
  statute_library_version: string;
}> {
  const res = await fetchWithTimeout(`${API_BASE}/api/legal/purge-qa-cache`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeader(authToken),
    },
    body: JSON.stringify({
      akta_code: aktaCode || undefined,
    }),
  });
  return parseJsonOrThrow(res);
}

export async function fetchActiveSops(
  params: {
    q?: string;
    akta?: string;
    authToken?: string | null;
  } = {}
): Promise<{
  total: number;
  quarantined_deprecated_blocked: number;
  sops: ActiveSopSummary[];
}> {
  const search = new URLSearchParams();
  if (params.q?.trim()) search.set("q", params.q.trim());
  if (params.akta && params.akta !== "Semua") search.set("akta", params.akta);
  const res = await fetchWithTimeout(`${API_BASE}/api/legal/sops?${search.toString()}`, {
    cache: "no-store",
    headers: { ...getAuthHeader(params.authToken) },
  });
  return parseJsonOrThrow(res);
}

export async function fetchActiveSopDetail(
  fileStemOrId: string,
  authToken?: string | null
): Promise<ActiveSopDetail> {
  const res = await fetchWithTimeout(
    `${API_BASE}/api/legal/sops/${encodeURIComponent(fileStemOrId)}`,
    {
      cache: "no-store",
      headers: { ...getAuthHeader(authToken) },
    }
  );
  return parseJsonOrThrow<ActiveSopDetail>(res);
}


