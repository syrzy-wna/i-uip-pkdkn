import type {
  AdvisorConsultResult,
  AdvisorScenarioItem,
  CompoundCheckResult,
  DemoAccountSummary,
  DevOverviewResponse,
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
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function parseJsonOrThrow<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let msg = `Ralat pelayan (${res.status})`;
    try {
      const errData = await res.json();
      msg = errData.detail || msg;
    } catch {
      msg = await res.text();
    }
    throw new Error(msg);
  }
  return res.json() as Promise<T>;
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
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseJsonOrThrow(res);
}

export async function fetchSampleCases(): Promise<SampleCase[]> {
  const res = await fetch(`${API_BASE}/api/samples`, { cache: "no-store" });
  const data = await parseJsonOrThrow<{ samples: SampleCase[] }>(res);
  return data.samples;
}

export async function fetchCases(): Promise<IPCaseRecord[]> {
  const res = await fetch(`${API_BASE}/api/cases`, { cache: "no-store" });
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
  });
  await parseJsonOrThrow<{ deleted: boolean }>(res);
}

export async function runRedaction(
  text: string,
  useOllama: boolean
): Promise<RedactResponse> {
  const res = await fetch(`${API_BASE}/api/redact`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
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
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (params.authToken) {
    headers["Authorization"] = `Bearer ${params.authToken}`;
  }
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
): Promise<void> {
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
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.URL.revokeObjectURL(url);
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
  const res = await fetch(`${API_BASE}/api/advisor/scenarios`, { cache: "no-store" });
  const data = await parseJsonOrThrow<{ scenarios: AdvisorScenarioItem[] }>(res);
  return data.scenarios;
}

export async function consultUipAdvisor(params: {
  question: string;
  aktaHint: string;
  scenarioId?: string;
  useAi?: boolean;
  authToken?: string | null;
  officerProfile?: OfficerProfile | null;
}): Promise<AdvisorConsultResult> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (params.authToken) {
    headers["Authorization"] = `Bearer ${params.authToken}`;
  }
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

// ---------------- Konsol Pembangun (Dev g.dev/syrzy) ----------------

export async function fetchDevOverview(): Promise<DevOverviewResponse> {
  const res = await fetch(`${API_BASE}/api/dev/overview`, { cache: "no-store" });
  return parseJsonOrThrow<DevOverviewResponse>(res);
}
