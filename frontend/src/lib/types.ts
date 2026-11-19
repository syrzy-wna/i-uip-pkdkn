export type WorkflowMode = "audit_ip" | "ip_builder" | "notis_kompaun";

export interface SystemStatus {
  system: string;
  version: string;
  ollama: {
    connected: boolean;
    base_url: string;
    configured_model: string;
    available_models: string[];
    fallback_active: boolean;
  };
  gemini: {
    sdk_installed: boolean;
    api_key_configured: boolean;
    masked_api_key?: string;
    decision_model: string;
    multimodal_model: string;
    reasoning_model: string;
    standard_fallback_model?: string;
    mode: string;
  };
  rag: {
    engine: string;
    chunks_indexed: number;
    acts_loaded: Array<{
      akta_code: string;
      akta_title: string;
      source_file: string;
    }>;
  };
}

export interface RuntimeSettings {
  gemini_api_key_configured: boolean;
  masked_gemini_api_key: string;
  google_client_id?: string;
  google_client_id_configured?: boolean;
  ollama_base_url: string;
  ollama_model: string;
  decision_model: string;
  multimodal_model: string;
  reasoning_model: string;
  standard_fallback_model: string;
}

export interface SampleCase {
  id: string;
  title: string;
  akta_utama: string;
  workflow: WorkflowMode;
  badge: string;
  summary: string;
  text: string;
}

export interface IPCaseRecord {
  id: string;
  no_ip: string;
  tajuk_kes: string;
  akta_utama: string;
  workflow: WorkflowMode;
  badge: string;
  nama_okt: string;
  no_kp_okt: string;
  nama_premis: string;
  no_ssm: string;
  alamat_kejadian: string;
  tarikh_kejadian: string;
  masa_kejadian: string;
  pegawai_io: string;
  no_kad_kuasa: string;
  status_kes: string;
  skor_audit: number;
  case_text: string;
  checklist?: Record<string, string>;
  audit_report?: IPAuditReport | null;
  draft?: DraftGenerationResponse | null;
  created_at?: string;
  updated_at?: string;
}

export interface RedactedEntity {
  token: string;
  category: string;
  original: string;
  source: string;
}

export interface RedactResponse {
  original_text: string;
  redacted_text: string;
  token_map: Record<string, string>;
  entities: RedactedEntity[];
  engine_used: string;
  ollama_available: boolean;
  warnings: string[];
}

export interface CriterionAuditResult {
  code: string;
  title: string;
  category: string;
  status: "LULUS" | "SEMAK" | "GAGAL";
  answer: string;
  calibrated_score: number;
  threshold: number;
  evidence_snippet: string;
  statute_ref: string;
  recommendation: string;
}

export interface KuiriTprItem {
  code: string;
  tahap: string;
  isu: string;
  tindakan_io: string;
}

export interface IPFolderSectionStatus {
  bahagian: string;
  tajuk: string;
  status: string;
}

export interface StatutoryCitation {
  chunk_id?: string;
  akta_code: string;
  akta_title: string;
  section: string;
  text: string;
  source_file?: string;
  score: number;
}

export interface IPAuditReport {
  filename: string;
  akta_utama: string;
  overall_score: number;
  readiness_status: string;
  counts: {
    LULUS: number;
    SEMAK: number;
    GAGAL: number;
  };
  criteria_results: CriterionAuditResult[];
  tpr_summary_notes: string[];
  kuiri_tpr?: KuiriTprItem[];
  ip_folder_checklist?: IPFolderSectionStatus[];
  statutory_citations: StatutoryCitation[];
  redaction_summary: {
    engine_used: string;
    ollama_available: boolean;
    entities_masked: number;
    token_map: Record<string, string>;
    entities: RedactedEntity[];
    redacted_text: string;
    warnings: string[];
  };
  models_used: Record<string, string>;
  extracted_text: string;
}

export interface EvidenceExtractionResponse {
  filename: string;
  extracted_fields: Record<string, string | number>;
  structured_summary: string;
  raw_text: string;
  confidence: number;
  model_used: string;
  warnings: string[];
}

export interface MinitEntry {
  bil: string;
  tarikh: string;
  daripada: string;
  kepada: string;
  kandungan: string;
}

export interface Borang114Data {
  mahkamah: string;
  negeri?: string;
  no_kes: string;
  nama_tertuduh: string;
  no_kp_tertuduh: string;
  umur_jantina?: string;
  pekerjaan?: string;
  alamat_tertuduh: string;
  tarikh_kejadian: string;
  masa_kejadian: string;
  tempat_kejadian: string;
  daerah?: string;
  akta_dan_seksyen: string;
  seksyen_hukuman: string;
  hukuman_maksimum?: string;
  pegawai_pengadu?: string;
  teks_pertuduhan: string;
}

export interface DiariEntry {
  bil: string;
  tarikh?: string;
  masa?: string;
  tarikh_masa?: string;
  butiran_tindakan: string;
  pegawai: string;
}

export interface SaksiEntry {
  bil: string;
  nama: string;
  no_kp: string;
  jawatan_peranan: string;
  alamat_hubungan?: string;
}

export interface EksibitEntry {
  tanda: string;
  perihal: string;
  no_lak_seal?: string;
  lokasi_simpanan: string;
}

export interface NotisKompaunData {
  no_notis: string;
  nama_penerima: string;
  no_kp: string;
  nama_premis: string;
  alamat_kejadian?: string;
  no_ssm?: string;
  tarikh_masa?: string;
  kesalahan_ringkas: string;
  peruntukan_undang: string;
  peruntukan_kompaun?: string;
  amaun_kompaun_rm: string;
  tempoh_bayaran: string;
  pegawai_pengeluar?: string;
  no_kad_kuasa?: string;
  status_serahan?: string;
  saksi_ppkp?: string;
}

export interface KronologiEntry {
  tarikh: string;
  peristiwa: string;
}

export interface DraftGenerationResponse {
  workflow: string;
  akta_utama: string;
  minit_ip: MinitEntry[] | string;
  kronologi_kes?: KronologiEntry[];
  kertas_cadangan_io?: string;
  saman_111?: Record<string, string>;
  pemberatan_hukuman?: string[];
  borang_143?: Record<string, string>;
  izin_mendakwa?: Record<string, string>;
  borang_114: Borang114Data;
  diari_siasatan: DiariEntry[];
  fakta_kes: string;
  rakaman_112: string;
  senarai_saksi: SaksiEntry[];
  senarai_eksibit: EksibitEntry[];
  sijil_90a: {
    nama_pegawai: string;
    jawatan: string;
    pejabat_pkd?: string;
    peranti_kamera?: string;
    perihal_komputer: string;
    perihal_pencetak?: string;
    senarai_dokumen_digital: string;
  };
  notis_kompaun: NotisKompaunData;
  tpr_simulation_notes: string[];
  statutory_citations: StatutoryCitation[];
  redaction_preview: {
    engine_used: string;
    ollama_available: boolean;
    entities_masked: number;
    rehydrated: boolean;
    redacted_excerpt: string;
    redacted_text?: string;
    token_map: Record<string, string>;
    entities?: RedactedEntity[];
    warnings?: string[];
  };
  models_used: Record<string, string>;
}

export interface CompoundCheckResult {
  readiness_status: string;
  score_percent: number;
  counts: {
    LULUS: number;
    SEMAK: number;
    GAGAL: number;
  };
  checks: Array<{
    code: string;
    label: string;
    status: "LULUS" | "SEMAK" | "GAGAL";
    note: string;
  }>;
  suggested_offense_text: string;
}

export interface OfficerProfile {
  id: string;
  email: string;
  full_name: string;
  ic_number: string;
  designation: string;
  grade: string;
  kkm_authority_card_no: string;
  prosecution_authorization_no?: string;
  state_jkn: string;
  district_pkd: string;
  office_address: string;
  unit_assignment: string;
  default_magistrate_court: string;
  system_role: string;
  default_computer_desc: string;
  default_printer_desc: string;
  default_camera_desc: string;
  auth_provider?: string;
  last_seen_at?: string;
  is_demo?: boolean;
  is_dev_admin?: boolean;
}

export interface DemoAccountSummary {
  email: string;
  full_name: string;
  designation: string;
  grade: string;
  district_pkd: string;
  system_role: string;
}

export interface AdvisorChargeItem {
  perihal: string;
  seksyen_kesalahan: string;
  seksyen_hukuman: string;
  hukuman_maksimum: string;
  boleh_kompaun: string;
}

export interface AdvisorScenarioItem {
  id: string;
  akta_utama: string;
  tajuk: string;
  keputusan_tindakan: string;
  sesuai_buka_ip: boolean;
  cadangan_pertuduhan: AdvisorChargeItem[];
}

export interface AdvisorConsultResult {
  scenario_id: string;
  akta_disyorkan: string;
  tajuk_nasihat: string;
  keputusan_tindakan: string;
  sesuai_buka_ip: boolean;
  alasan_keputusan: string;
  cadangan_pertuduhan: AdvisorChargeItem[];
  sop_lapangan: string[];
  eksibit_wajib: string[];
  perangkap_kesilapan: string[];
  templat_ringkas: string;
  draf_teks_kes_cadangan: string;
  engine_used: string;
  ai_attempted?: boolean;
  ai_succeeded?: boolean;
  fallback_reason?: string | null;
  statutory_citations: StatutoryCitation[];
}

export interface DevUserRecord extends OfficerProfile {
  created_at: string;
  updated_at: string;
  total_actions: number;
  latest_activity_at: string;
  archived_records_count?: number;
}

export interface DevActivityLog {
  id: string;
  user_id: string;
  user_email: string;
  user_name: string;
  district_pkd: string;
  action_type: string;
  action_detail: string;
  model_used: string;
  is_cloud_api: number;
  est_input_tokens: number;
  est_output_tokens: number;
  est_cost_usd: number;
  est_cost_myr: number;
  latency_ms: number;
  created_at: string;
}

export interface DevPricingReference {
  module: string;
  engine: string;
  cost_per_call_myr: string;
  notes: string;
}

export interface DevOverviewResponse {
  developer: string;
  host_office: string;
  google_client_id_configured: boolean;
  gemini_api_key_configured: boolean;
  summary: {
    total_users: number;
    active_sessions: number;
    total_actions: number;
    cloud_api_calls: number;
    local_free_calls: number;
    total_input_tokens: number;
    total_output_tokens: number;
    total_cost_usd: number;
    total_cost_myr: number;
    avg_latency_ms: number;
    usd_to_myr_rate: number;
    action_breakdown: Array<{
      action_type: string;
      count: number;
      cloud_calls: number;
      total_usd: number;
      total_myr: number;
    }>;
  };
  pricing_reference: DevPricingReference[];
  users: DevUserRecord[];
  activities: DevActivityLog[];
  vault_summary?: DevVaultStorageHealth & {
    category_counts?: DevVaultCategoryCounts;
  };
}

// ---------------- Arkib & Bucket Eksklusif Pembangun (Dev Vault) ----------------

export type DevVaultCategory =
  | "ALL"
  | "USER_REGISTER"
  | "ADVISOR_QA"
  | "AUDIT_IP"
  | "OCR_EVIDENCE"
  | "DRAFT_COMPOUND";

export type DevVaultStorageBackend =
  | "s3_neon"
  | "postgres_local_vault"
  | "sqlite_local_vault"
  | "local_vault";

export type DevVaultExportMode = "full" | "redacted";

export interface DevVaultCategoryCounts {
  ALL: number;
  USER_REGISTER: number;
  ADVISOR_QA: number;
  AUDIT_IP: number;
  OCR_EVIDENCE: number;
  DRAFT_COMPOUND: number;
}

export interface DevVaultStorageHealth {
  backend_type: DevVaultStorageBackend;
  backend_label: string;
  db_engine: "postgresql" | "sqlite";
  is_cloud_bucket: boolean;
  is_private_locked: boolean;
  bucket_name?: string | null;
  bucket_prefix?: string | null;
  bucket_endpoint_host?: string | null;
  bucket_region?: string | null;
  local_vault_path?: string | null;
  is_ephemeral_warning: boolean;
  total_records: number;
  total_files: number;
  total_bytes: number;
  unsynced_count?: number;
  last_archived_at?: string | null;
  allowed_dev_emails: string[];
}

export interface DevVaultFileAttachment {
  file_id?: string;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  sha256: string;
  storage_backend: DevVaultStorageBackend;
  object_key: string;
  is_available: boolean;
}

export interface DevVaultRecordSummary {
  id: string;
  category: Exclude<DevVaultCategory, "ALL">;
  action_type: string;
  title: string;
  preview_text: string;
  akta_utama?: string | null;
  user_id?: string | null;
  user_email: string;
  user_name: string;
  district_pkd: string;
  model_used: string;
  is_cloud_api: boolean;
  est_cost_myr: number;
  latency_ms: number;
  has_file: boolean;
  file_name?: string | null;
  file_content_type?: string | null;
  file_size_bytes?: number | null;
  storage_backend: DevVaultStorageBackend;
  pdpa_entities_masked: number;
  created_at: string;
}

export interface DevVaultRecordDetail extends DevVaultRecordSummary {
  raw_input_text: string;
  redacted_input_text: string;
  raw_response_text: string;
  redacted_response_text: string;
  analysis_json: Record<string, unknown> | null;
  redacted_analysis_json: Record<string, unknown> | null;
  user_snapshot?: Partial<OfficerProfile> | null;
  file_attachment?: DevVaultFileAttachment | null;
  storage_metadata: {
    object_key?: string | null;
    bucket_name?: string | null;
    payload_sha256?: string | null;
    source_endpoint?: string | null;
    sync_status?: string | null;
  };
}

export interface DevVaultListResponse {
  developer: string;
  storage_health: DevVaultStorageHealth;
  category_counts: DevVaultCategoryCounts;
  total_matching: number;
  limit: number;
  offset: number;
  items: DevVaultRecordSummary[];
}
