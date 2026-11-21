import type {
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
  NotisKompaunData,
  OfficerProfile,
  RedactResponse,
  RuntimeSettings,
  SampleCase,
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
    let msg = `Ralat pelayan (${res.status})`;
    if (parsed && typeof parsed.detail === "string" && parsed.detail.trim()) {
      msg = parsed.detail;
    } else if (parsed && typeof parsed.message === "string" && parsed.message.trim()) {
      msg = parsed.message;
    } else if (rawText.trim()) {
      const stripped = rawText.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
      if (stripped) {
        msg = stripped.slice(0, 220);
      }
    }
    throw new Error(msg);
  }

  if (parsed !== null) {
    return parsed as T;
  }
  throw new Error("Respons pelayan bukan format JSON yang sah.");
}

export async function fetchSystemStatus(): Promise<SystemStatus> {
  const res = await fetch(`${API_BASE}/api/status`, { cache: "no-store" });
  return parseJsonOrThrow<SystemStatus>(res);
}

export async function fetchRuntimeSettings(): Promise<RuntimeSettings> {
  const res = await fetch(`${API_BASE}/api/settings`, { cache: "no-store" });
  return parseJsonOrThrow<RuntimeSettings>(res);
}

export async function saveRuntimeSettings(payload: {
  gemini_api_key?: string;
  google_client_id?: string;
  ollama_base_url?: string;
  ollama_model?: string;
  standard_fallback_model?: string;
}): Promise<{ status: string; system_status: SystemStatus; settings: RuntimeSettings }> {
  const res = await fetch(`${API_BASE}/api/settings`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeader() },
    body: JSON.stringify(payload),
  });
  return parseJsonOrThrow(res);
}

export async function fetchSampleCases(): Promise<SampleCase[]> {
  const res = await fetch(`${API_BASE}/api/samples`, {
    cache: "no-store",
    headers: { ...getAuthHeader() },
  });
  const data = await parseJsonOrThrow<{ samples: SampleCase[] }>(res);
  return data.samples;
}

export async function fetchCases(): Promise<IPCaseRecord[]> {
  const res = await fetch(`${API_BASE}/api/cases`, {
    cache: "no-store",
    headers: { ...getAuthHeader() },
  });
  const data = await parseJsonOrThrow<{ cases: IPCaseRecord[] }>(res);
  return data.cases;
}

export async function saveCaseRecord(
  payload: Partial<IPCaseRecord>
): Promise<IPCaseRecord> {
  const res = await fetch(`${API_BASE}/api/cases`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeader() },
    body: JSON.stringify(payload),
  });
  const data = await parseJsonOrThrow<{ case: IPCaseRecord }>(res);
  return data.case;
}

export async function deleteCaseRecord(caseId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/cases/${encodeURIComponent(caseId)}`, {
    method: "DELETE",
    headers: { ...getAuthHeader() },
  });
  await parseJsonOrThrow<{ deleted: boolean }>(res);
}

export async function runRedaction(
  text: string,
  useOllama: boolean
): Promise<RedactResponse> {
  const res = await fetch(`${API_BASE}/api/redact`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeader() },
    body: JSON.stringify({ text, use_ollama: useOllama }),
  });
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
  const res = await fetch(`${API_BASE}/api/audit-ip`, {
    method: "POST",
    headers: { ...getAuthHeader() },
    body: form,
  });
  return parseJsonOrThrow<IPAuditReport>(res);
}

export async function extractEvidence(
  file: File,
  docHint: string
): Promise<EvidenceExtractionResponse> {
  const form = new FormData();
  form.append("file", file);
  form.append("doc_hint", docHint);
  const res = await fetch(`${API_BASE}/api/extract-evidence`, {
    method: "POST",
    headers: { ...getAuthHeader() },
    body: form,
  });
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
  const res = await fetch(`${API_BASE}/api/generate-draft`, {
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
  });
  return parseJsonOrThrow<DraftGenerationResponse>(res);
}

export async function checkCompoundNotice(
  payload: NotisKompaunData
): Promise<CompoundCheckResult> {
  const res = await fetch(`${API_BASE}/api/check-compound`, {
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
  const res = await fetch(`${API_BASE}/api/rag/query?${search.toString()}`, {
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
  const res = await fetch(`${API_BASE}/api/export-docx`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeader() },
    body: JSON.stringify({ doc_type: docType, payload }),
  });
  if (!res.ok) {
    throw new Error(`Gagal muat turun fail Word .docx (${res.status})`);
  }
  const blob = await res.blob();
  const disposition = res.headers.get("Content-Disposition") || "";
  const match = disposition.match(/filename="([^"]+)"/);
  const filename = match ? match[1] : `${docType}.docx`;

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
    window.setTimeout(() => window.URL.revokeObjectURL(url), 1500);
  }
  return filename;
}

// ---------------- Akaun Pegawai KKM Sebenar ----------------

export async function fetchDemoAccounts(): Promise<DemoAccountSummary[]> {
  const res = await fetch(`${API_BASE}/api/auth/demo-accounts`, { cache: "no-store" });
  const data = await parseJsonOrThrow<{ accounts: DemoAccountSummary[] }>(res);
  return data.accounts;
}

export async function loginOfficer(
  email: string,
  password: string
): Promise<{ user: OfficerProfile; token: string }> {
  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  return parseJsonOrThrow<{ user: OfficerProfile; token: string }>(res);
}

export async function registerOfficer(
  payload: Record<string, string>
): Promise<{ user: OfficerProfile; token: string }> {
  const res = await fetch(`${API_BASE}/api/auth/register`, {
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
  const res = await fetch(`${API_BASE}/api/auth/google`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseJsonOrThrow<{ user: OfficerProfile; token: string; is_new_account?: boolean }>(res);
}

export async function fetchCurrentOfficer(token: string): Promise<OfficerProfile> {
  const res = await fetch(`${API_BASE}/api/auth/me`, {
    cache: "no-store",
    headers: { Authorization: `Bearer ${token}` },
  });
  const data = await parseJsonOrThrow<{ user: OfficerProfile }>(res);
  return data.user;
}

export async function updateOfficerProfile(
  token: string,
  payload: Partial<OfficerProfile>
): Promise<OfficerProfile> {
  const res = await fetch(`${API_BASE}/api/auth/profile`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
  const data = await parseJsonOrThrow<{ user: OfficerProfile }>(res);
  return data.user;
}

export async function logoutOfficer(token: string): Promise<void> {
  await fetch(`${API_BASE}/api/auth/logout`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
}

// ---------------- Tanya Pakar UIP ----------------

export async function fetchAdvisorScenarios(): Promise<AdvisorScenarioItem[]> {
  const res = await fetch(`${API_BASE}/api/advisor/scenarios`, {
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
  const res = await fetch(`${API_BASE}/api/advisor/answered?${search.toString()}`, {
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
}): Promise<AdvisorConsultResult> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...getAuthHeader(params.authToken),
  };
  const res = await fetch(`${API_BASE}/api/advisor/consult`, {
    method: "POST",
    headers,
    body: JSON.stringify({
      question: params.question,
      akta_hint: params.aktaHint,
      scenario_id: params.scenarioId || undefined,
      use_ai: Boolean(params.useAi),
      officer_profile: params.officerProfile || undefined,
    }),
  });
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
  const res = await fetch(`${API_BASE}/api/dev/overview`, {
    cache: "no-store",
    headers: { ...getAuthHeader(authToken) },
  });
  return parseJsonOrThrow<DevOverviewResponse>(res);
}

export async function fetchDevVaultHealth(
  authToken?: string | null
): Promise<DevVaultStorageHealth> {
  const res = await fetch(`${API_BASE}/api/dev/vault/health`, {
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

  const res = await fetch(`${API_BASE}/api/dev/vault/records?${search.toString()}`, {
    cache: "no-store",
    headers: { ...getAuthHeader(params.authToken) },
  });
  return parseJsonOrThrow<DevVaultListResponse>(res);
}

export async function fetchDevVaultRecordDetail(
  recordId: string,
  authToken?: string | null
): Promise<DevVaultRecordDetail> {
  const res = await fetch(
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
  const res = await fetch(
    `${API_BASE}/api/dev/vault/records/${encodeURIComponent(recordId)}/file?kind=${kind}`,
    {
      method: "GET",
      cache: "no-store",
      headers: { ...getAuthHeader(authToken) },
    }
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
  const res = await fetch(
    `${API_BASE}/api/dev/vault/records/${encodeURIComponent(recordId)}/file?kind=attachment`,
    {
      method: "GET",
      cache: "no-store",
      headers: { ...getAuthHeader(authToken) },
    }
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
  const res = await fetch(`${API_BASE}/api/dev/vault/export`, {
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
  });
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
  const res = await fetch(`${API_BASE}/api/dev/vault/retry-s3-sync`, {
    method: "POST",
    cache: "no-store",
    headers: { ...getAuthHeader(authToken) },
  });
  return parseJsonOrThrow(res);
}
