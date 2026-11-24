"use client";

import React, { useEffect, useRef, useState } from "react";
import {
  BadgeCheck,
  Building2,
  Eye,
  EyeOff,
  KeyRound,
  Loader2,
  LogOut,
  Save,
  ShieldCheck,
  UserCheck,
  UserPlus,
  X,
} from "lucide-react";
import {
  fetchRuntimeSettings,
  googleSignInOfficer,
  loginOfficer,
  logoutOfficer,
  registerOfficer,
  updateOfficerProfile,
} from "@/lib/api";
import { useLockBodyScroll } from "@/lib/uiHelpers";
import type { OfficerProfile } from "@/lib/types";

const DEFAULT_GOOGLE_CLIENT_ID =
  "290203327893-b7f42feigfscdd4rfo1eh1a3n5age7ev.apps.googleusercontent.com";

export const MALAYSIA_JKN_OPTIONS: Array<{ value: string; label: string }> = [
  { value: "", label: "— Pilih Jabatan Kesihatan Negeri (JKN / JKWP) —" },
  { value: "Jabatan Kesihatan Negeri Johor", label: "JKN Johor (PKD)" },
  { value: "Jabatan Kesihatan Negeri Kedah", label: "JKN Kedah (PKD)" },
  { value: "Jabatan Kesihatan Negeri Kelantan", label: "JKN Kelantan (PKD)" },
  { value: "Jabatan Kesihatan Negeri Melaka", label: "JKN Melaka (PKD)" },
  { value: "Jabatan Kesihatan Negeri Sembilan", label: "JKN Negeri Sembilan (PKD)" },
  { value: "Jabatan Kesihatan Negeri Pahang", label: "JKN Pahang (PKD)" },
  { value: "Jabatan Kesihatan Negeri Perak", label: "JKN Perak (PKD)" },
  { value: "Jabatan Kesihatan Negeri Perlis", label: "JKN Perlis (PKD)" },
  { value: "Jabatan Kesihatan Negeri Pulau Pinang", label: "JKN Pulau Pinang (PKD)" },
  { value: "Jabatan Kesihatan Negeri Sabah", label: "JKN Sabah (Pejabat Kesihatan Kawasan / PKK)" },
  { value: "Jabatan Kesihatan Negeri Sarawak", label: "JKN Sarawak (Pejabat Kesihatan Bahagian / PKB)" },
  { value: "Jabatan Kesihatan Negeri Selangor", label: "JKN Selangor (PKD)" },
  { value: "Jabatan Kesihatan Negeri Terengganu", label: "JKN Terengganu (PKD)" },
  {
    value: "Jabatan Kesihatan Wilayah Persekutuan Kuala Lumpur & Putrajaya",
    label: "JKWPKL&P — WP Kuala Lumpur & Putrajaya",
  },
  {
    value: "Jabatan Kesihatan Wilayah Persekutuan Labuan",
    label: "JKWP Labuan — WP Labuan",
  },
];

const SSPA_GRADE_GROUPS: Array<{
  label: string;
  items: Array<{ value: string; text: string }>;
}> = [
  {
    label: "Skim PPKP (Kumpulan Pelaksana — SSPA)",
    items: [
      { value: "U5", text: "U5 — PPKP (dahulu U29)" },
      { value: "U6", text: "U6 — PPKP Penyelia / Kanan (dahulu U32)" },
      { value: "U7", text: "U7 — PPKP Kanan / KPPKP (dahulu U36/U38)" },
      { value: "U8", text: "U8 — Ketua PPKP / KPPKP (dahulu U40)" },
    ],
  },
  {
    label: "Skim PKP (Pengurusan & Profesional — SSPA)",
    items: [
      { value: "U9", text: "U9 — PKP (dahulu U41/U42)" },
      { value: "U10", text: "U10 — PKP Kanan (dahulu U44)" },
      { value: "U12", text: "U12 — PKP Kanan (dahulu U48)" },
      { value: "U13", text: "U13 — PKP Kanan (dahulu U52)" },
      { value: "U14", text: "U14 — PKP Kanan (dahulu U54)" },
    ],
  },
  {
    label: "Pegawai Perubatan / PKD (SSPA)",
    items: [
      { value: "UD9", text: "UD9 — Pegawai Perubatan (dahulu UD41/43)" },
      { value: "UD10", text: "UD10 — Pegawai Perubatan (dahulu UD44)" },
      { value: "UD12", text: "UD12 — Pegawai Perubatan (dahulu UD48)" },
      { value: "UD13", text: "UD13 — Pakar / Pegawai Perubatan (dahulu UD52)" },
      { value: "UD14", text: "UD14 — Pakar / PKD (dahulu UD54)" },
    ],
  },
  {
    label: "Pegawai Sains Entomologi / Mikrobiologi (SSPA)",
    items: [
      { value: "C9", text: "C9 — Pegawai Sains (dahulu C41)" },
      { value: "C10", text: "C10 — Pegawai Sains (dahulu C44)" },
      { value: "C12", text: "C12 — Pegawai Sains (dahulu C48)" },
      { value: "C13", text: "C13 — Pegawai Sains (dahulu C52)" },
      { value: "C14", text: "C14 — Pegawai Sains (dahulu C54)" },
    ],
  },
];

function renderSspaGradeOptions() {
  return SSPA_GRADE_GROUPS.map((grp) => (
    <optgroup key={grp.label} label={grp.label}>
      {grp.items.map((opt) => (
        <option key={opt.value} value={opt.value}>
          {opt.text}
        </option>
      ))}
    </optgroup>
  ));
}

declare global {
  interface Window {
    google?: {
      accounts?: {
        id?: {
          initialize: (cfg: Record<string, unknown>) => void;
          renderButton: (el: HTMLElement, opts: Record<string, unknown>) => void;
        };
        oauth2?: {
          initTokenClient: (cfg: Record<string, unknown>) => {
            requestAccessToken: (opts?: Record<string, unknown>) => void;
          };
        };
      };
    };
  }
}

interface AuthAccountModalProps {
  open: boolean;
  onClose: () => void;
  officer: OfficerProfile | null;
  authToken: string | null;
  initialTab?: "google" | "login" | "register" | "profile";
  onAuthenticated: (officer: OfficerProfile, token: string, isNewAccount?: boolean) => void;
  onProfileUpdated: (officer: OfficerProfile) => void;
  onLoggedOut: () => void;
}

export default function AuthAccountModal({
  open,
  onClose,
  officer,
  authToken,
  initialTab = "google",
  onAuthenticated,
  onProfileUpdated,
  onLoggedOut,
}: AuthAccountModalProps) {
  const [tab, setTab] = useState<"google" | "login" | "register" | "profile">(
    officer ? "profile" : initialTab
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Tetapan & Token Google OAuth 2.0 Sebenar
  const [googleClientId, setGoogleClientId] = useState(DEFAULT_GOOGLE_CLIENT_ID);
  const [gsiReady, setGsiReady] = useState(false);
  const [gsiFailed, setGsiFailed] = useState(false);
  const gsiBtnRef = useRef<HTMLDivElement | null>(null);

  // Borang Log Masuk E-mel Biasa
  const [loginEmail, setLoginEmail] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [showLoginPw, setShowLoginPw] = useState(false);
  const [showForgotHelp, setShowForgotHelp] = useState(false);

  // Borang Daftar Akaun E-mel Biasa (Neutral Seluruh Malaysia)
  const [regForm, setRegForm] = useState({
    email: "",
    password: "",
    confirm_password: "",
    full_name: "",
    ic_number: "",
    designation: "Penolong Pegawai Kesihatan Persekitaran (PPKP)",
    grade: "U5",
    kkm_authority_card_no: "",
    prosecution_authorization_no: "",
    state_jkn: "",
    district_pkd: "",
    office_address: "",
    unit_assignment: "Unit Inspektorat dan Perundangan (UIP)",
    default_magistrate_court: "",
    system_role: "PEGAWAI_PENYIASAT",
    default_computer_desc: "Komputer Meja Rasmi KKM Pejabat Kesihatan",
    default_printer_desc: "Pencetak Laser Warna Pejabat Kesihatan",
    default_camera_desc: "Kamera Digital Rasmi Pejabat Kesihatan",
  });
  const [showRegPw, setShowRegPw] = useState(false);

  // Borang Sunting Profil & Progressive Disclosure Pendaftaran
  const [profileForm, setProfileForm] = useState<Partial<OfficerProfile>>({});
  const [showOfficeDefaults, setShowOfficeDefaults] = useState(false);
  const prevOpenRef = useRef(false);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;
  useLockBodyScroll(open);

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onCloseRef.current();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open]);

  useEffect(() => {
    const justOpened = open && !prevOpenRef.current;
    prevOpenRef.current = open;
    if (!open) return;
    if (justOpened) {
      setError(null);
      setSuccessMsg(null);
      setShowForgotHelp(false);
    }
    if (officer) {
      setTab("profile");
      setProfileForm(officer);
    } else if (justOpened) {
      setTab(initialTab === "profile" ? "google" : initialTab);
      fetchRuntimeSettings()
        .then((s) => {
          const cid = (s.google_client_id || "").trim() || DEFAULT_GOOGLE_CLIENT_ID;
          setGoogleClientId(cid);
        })
        .catch(() => {
          setGoogleClientId(DEFAULT_GOOGLE_CLIENT_ID);
        });
    }
  }, [open, officer, initialTab]);

  useEffect(() => {
    if (!open || officer || tab !== "google" || !googleClientId) {
      setGsiReady(false);
      setGsiFailed(false);
      return;
    }
    let cancelled = false;
    setGsiFailed(false);

    const initGisButton = () => {
      if (cancelled || !window.google?.accounts?.id) return;
      setGsiReady(true);
      setGsiFailed(false);
      if (gsiBtnRef.current) {
        gsiBtnRef.current.innerHTML = "";
        window.google.accounts.id.initialize({
          client_id: googleClientId,
          callback: async (response: { credential?: string }) => {
            if (!response?.credential) return;
            setLoading(true);
            setError(null);
            try {
              const res = await googleSignInOfficer({
                id_token: response.credential,
              });
              onAuthenticated(res.user, res.token, res.is_new_account);
            } catch (err) {
              setError(
                err instanceof Error
                  ? err.message
                  : "Pengesahan akaun Google gagal. Sila cuba lagi."
              );
            } finally {
              setLoading(false);
            }
          },
        });
        const parentW = gsiBtnRef.current.parentElement?.clientWidth || 256;
        const btnWidth = Math.min(300, Math.max(200, parentW - 4));
        window.google.accounts.id.renderButton(gsiBtnRef.current, {
          theme: "outline",
          size: "large",
          text: "continue_with",
          shape: "pill",
          width: btnWidth,
        });
      }
    };

    const failTimer = window.setTimeout(() => {
      if (!cancelled && !window.google?.accounts?.id) {
        setGsiFailed(true);
      }
    }, 4500);

    if (window.google?.accounts?.id) {
      initGisButton();
    } else {
      const existingScript = document.getElementById("google-gsi-client-script");
      if (!existingScript) {
        const script = document.createElement("script");
        script.id = "google-gsi-client-script";
        script.src = "https://accounts.google.com/gsi/client";
        script.async = true;
        script.defer = true;
        script.onload = initGisButton;
        script.onerror = () => {
          if (!cancelled) setGsiFailed(true);
        };
        document.head.appendChild(script);
      } else {
        existingScript.addEventListener("load", initGisButton);
      }
    }
    return () => {
      cancelled = true;
      window.clearTimeout(failTimer);
    };
  }, [open, officer, tab, googleClientId, onAuthenticated]);

  if (!open) return null;

  const handleRealGooglePopup = () => {
    if (!googleClientId) {
      setError("Log masuk Google belum diaktifkan. Sila gunakan pilihan Masuk E-mel.");
      return;
    }
    const oauth2 = window.google?.accounts?.oauth2;
    if (!oauth2) {
      setError("Log masuk Google tidak dapat dimuatkan (mungkin disekat rangkaian pejabat). Sila gunakan pilihan Masuk E-mel di ruangan sebelah.");
      return;
    }
    setError(null);
    const tokenClient = oauth2.initTokenClient({
      client_id: googleClientId,
      scope: "openid email profile",
      callback: async (tokenResp: { access_token?: string; error?: string }) => {
        if (tokenResp.error || !tokenResp.access_token) {
          setError("Log masuk Google dibatalkan atau gagal memberi kebenaran akses.");
          return;
        }
        setLoading(true);
        try {
          const res = await googleSignInOfficer({
            access_token: tokenResp.access_token,
          });
          onAuthenticated(res.user, res.token, res.is_new_account);
        } catch (err) {
          setError(
            err instanceof Error
              ? err.message
              : "Pengesahan akaun Google gagal."
          );
        } finally {
          setLoading(false);
        }
      },
    });
    tokenClient.requestAccessToken({ prompt: "select_account" });
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await loginOfficer(loginEmail, loginPassword);
      onAuthenticated(res.user, res.token, false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gagal log masuk.");
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (regForm.password.length < 8) {
      setError("Kata laluan mestilah sekurang-kurangnya 8 aksara.");
      return;
    }
    if (regForm.password !== regForm.confirm_password) {
      setError("Kata laluan dan pengesahan kata laluan tidak sepadan. Sila semak semula.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const { confirm_password: _unused, ...submitPayload } = regForm;
      void _unused;
      const res = await registerOfficer(submitPayload);
      onAuthenticated(res.user, res.token, true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gagal mendaftar akaun.");
    } finally {
      setLoading(false);
    }
  };

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!authToken) return;
    setLoading(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const updated = await updateOfficerProfile(authToken, profileForm);
      onProfileUpdated(updated);
      setSuccessMsg("Profil pegawai, pejabat kesihatan dan butiran peranti Sijil 90A berjaya dikemas kini.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gagal mengemas kini profil.");
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    if (authToken) {
      await logoutOfficer(authToken).catch(() => {});
    }
    onLoggedOut();
    onClose();
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Akaun Rasmi Pegawai UIP KKM"
      onClick={onClose}
      className="fixed inset-0 z-50 flex items-end justify-center bg-slate-900/65 p-0 backdrop-blur-sm sm:items-center sm:p-4"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="flex max-h-[94dvh] w-full max-w-3xl flex-col overflow-hidden rounded-t-2xl border border-slate-200 bg-white pb-safe shadow-2xl sm:rounded-2xl"
      >
        {/* Header Modal */}
        <div className="flex items-center justify-between gap-2 border-b border-slate-200 bg-[#0f2744] px-4 py-3 text-white sm:px-5 sm:py-3.5">
          <div className="flex items-center gap-2.5 min-w-0">
            <UserCheck className="h-5 w-5 shrink-0 text-amber-300" />
            <div className="min-w-0">
              <h2 className="truncate text-xs font-bold sm:text-sm">
                Akaun Rasmi Pegawai UIP KKM (Seluruh Malaysia)
              </h2>
              <p className="truncate text-[10px] text-slate-300 sm:text-[11px]">
                Mengisi No. Kad Kuasa, pejabat kesihatan, mahkamah dan peranti Sijil 90A secara automatik ke dokumen rasmi.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Tutup tetingkap akaun"
            className="inline-flex min-h-[44px] min-w-[44px] shrink-0 items-center justify-center rounded-lg p-1.5 text-slate-300 hover:bg-white/10 hover:text-white"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Tab Switcher */}
        <div className="border-b border-slate-200 bg-slate-50 px-3 pt-2 pb-2 sm:px-5">
          {!officer ? (
            <div className="grid grid-cols-3 gap-1.5">
              <button
                type="button"
                onClick={() => setTab("google")}
                className={`inline-flex min-h-[40px] items-center justify-center gap-1 rounded-lg px-2 py-1.5 text-[11px] font-bold transition sm:text-xs ${
                  tab === "google"
                    ? "bg-[#0f2744] text-white shadow-sm"
                    : "bg-white text-slate-600 ring-1 ring-slate-200 hover:text-slate-900"
                }`}
              >
                <span className={`font-extrabold ${tab === "google" ? "text-amber-300" : "text-blue-600"}`}>
                  G
                </span>
                Google
              </button>
              <button
                type="button"
                onClick={() => setTab("login")}
                className={`inline-flex min-h-[40px] items-center justify-center gap-1 rounded-lg px-2 py-1.5 text-[11px] font-bold transition sm:text-xs ${
                  tab === "login"
                    ? "bg-[#0f2744] text-white shadow-sm"
                    : "bg-white text-slate-600 ring-1 ring-slate-200 hover:text-slate-900"
                }`}
              >
                <KeyRound className="h-3.5 w-3.5" /> Masuk E-mel
              </button>
              <button
                type="button"
                onClick={() => setTab("register")}
                className={`inline-flex min-h-[40px] items-center justify-center gap-1 rounded-lg px-2 py-1.5 text-[11px] font-bold transition sm:text-xs ${
                  tab === "register"
                    ? "bg-[#0f2744] text-white shadow-sm"
                    : "bg-white text-slate-600 ring-1 ring-slate-200 hover:text-slate-900"
                }`}
              >
                <UserPlus className="h-3.5 w-3.5" /> Daftar E-mel
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setTab("profile")}
              className="inline-flex items-center gap-1.5 rounded-lg bg-white px-3.5 py-2 text-xs font-bold text-[#0f2744] ring-1 ring-slate-200"
            >
              <BadgeCheck className="h-4 w-4 text-emerald-600" /> Profil Pegawai Aktif
            </button>
          )}
        </div>

        <div className="flex-1 overflow-y-auto p-4 sm:p-5 space-y-4">
          {error && (
            <div className="rounded-lg border border-rose-300 bg-rose-50 px-3 py-2 text-xs font-semibold text-rose-800">
              {error}
            </div>
          )}
          {successMsg && (
            <div className="rounded-lg border border-emerald-300 bg-emerald-50 px-3 py-2 text-xs font-semibold text-emerald-800">
              {successMsg}
            </div>
          )}

          {/* TAB 0: GOOGLE OAUTH 2.0 SEBENAR */}
          {tab === "google" && !officer && (
            <div className="space-y-4">
              <div className="rounded-xl border border-blue-200 bg-gradient-to-br from-blue-50/90 to-white p-4 space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2 text-xs font-bold text-slate-900">
                    <svg className="h-4 w-4 shrink-0" viewBox="0 0 24 24" aria-hidden="true">
                      <path fill="#4285F4" d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.665-5.17 3.665-9.17Z" />
                      <path fill="#34A853" d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.11-6.72-4.96H1.29v3.14C3.26 21.3 7.31 24 12 24Z" />
                      <path fill="#FBBC05" d="M5.28 14.24c-.24-.72-.38-1.49-.38-2.24s.14-1.52.38-2.24V6.62H1.29C.47 8.24 0 10.06 0 12s.47 3.76 1.29 5.38l3.99-3.14Z" />
                      <path fill="#EA4335" d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.31 0 3.26 2.7 1.29 6.62l3.99 3.14c.95-2.85 3.6-4.96 6.72-4.96Z" />
                    </svg>
                    <span>Log Masuk Google Rasmi</span>
                  </div>
                  <span
                    className={`rounded-full px-2.5 py-0.5 text-[10px] font-bold ${
                      googleClientId && !gsiFailed
                        ? "bg-emerald-100 text-emerald-800 ring-1 ring-emerald-300"
                        : "bg-amber-100 text-amber-800 ring-1 ring-amber-300"
                    }`}
                  >
                    {!googleClientId
                      ? "Belum Diaktifkan"
                      : gsiFailed
                        ? "Sekatan Rangkaian / Pelayar"
                        : "Google Aktif"}
                  </span>
                </div>

                {googleClientId ? (
                  <div className="space-y-3">
                    <p className="text-xs text-slate-600 leading-relaxed">
                      Klik butang Google rasmi di bawah untuk log masuk pantas dengan akaun Google anda. Selepas masuk kali pertama, anda boleh terus menetapkan pejabat kesihatan dan Negeri anda.
                    </p>
                    {gsiFailed && (
                      <div className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-[11px] text-amber-950 leading-relaxed space-y-2">
                        <p>
                          <strong>Butang Google tidak dapat dimuatkan</strong> (kemungkinan disekat oleh rangkaian pejabat atau penyekat iklan pelayar). Anda masih boleh log masuk terus menggunakan e-mel rasmi.
                        </p>
                        <div className="flex flex-wrap gap-2">
                          <button
                            type="button"
                            onClick={() => setTab("login")}
                            className="inline-flex min-h-[44px] items-center gap-1.5 rounded-lg bg-[#0f2744] px-3 py-1.5 text-xs font-bold text-white hover:bg-slate-800"
                          >
                            <KeyRound className="h-3.5 w-3.5" /> Masuk E-mel
                          </button>
                          <button
                            type="button"
                            onClick={() => setTab("register")}
                            className="inline-flex min-h-[44px] items-center gap-1.5 rounded-lg border border-amber-400 bg-white px-3 py-1.5 text-xs font-bold text-amber-950 hover:bg-amber-100"
                          >
                            <UserPlus className="h-3.5 w-3.5" /> Daftar Akaun E-mel
                          </button>
                        </div>
                      </div>
                    )}
                    <div className="flex flex-col items-start gap-2.5 pt-1">
                      <div className="flex w-full max-w-full justify-start overflow-hidden">
                        <div ref={gsiBtnRef} className="min-h-[44px]" />
                      </div>
                      {!gsiFailed && (
                        <button
                          type="button"
                          disabled={loading || !gsiReady}
                          onClick={handleRealGooglePopup}
                          className="inline-flex min-h-[44px] items-center gap-1.5 text-xs font-bold text-blue-700 hover:underline disabled:opacity-50"
                        >
                          {(loading || !gsiReady) && <Loader2 className="h-3.5 w-3.5 animate-spin text-blue-600" />}
                          <span>
                            {!gsiReady
                              ? "Sedang memuatkan sambungan Google..."
                              : "Atau buka tetingkap Log Masuk Google baharu →"}
                          </span>
                        </button>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <div className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-[11px] text-amber-950 leading-relaxed">
                      <strong>Log masuk Google belum diaktifkan buat masa ini.</strong>{" "}
                      Sila gunakan pilihan <strong>Daftar E-mel</strong> atau <strong>Masuk E-mel</strong> untuk masuk segera.
                    </div>
                    <button
                      type="button"
                      onClick={() => setTab("register")}
                      className="inline-flex min-h-[44px] items-center gap-1.5 rounded-lg bg-emerald-700 px-3.5 py-2 text-xs font-bold text-white hover:bg-emerald-800"
                    >
                      <UserPlus className="h-3.5 w-3.5" /> Daftar Akaun E-mel Pegawai
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 1: LOG MASUK */}
          {tab === "login" && !officer && (
            <div className="space-y-4">
              <form onSubmit={handleLogin} className="space-y-3 rounded-xl border border-slate-200 bg-slate-50/70 p-4">
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  <div>
                    <label className="block text-xs font-bold text-slate-700">
                      E-mel Rasmi Pegawai
                    </label>
                    <input
                      type="email"
                      required
                      placeholder="contoh: nama@moh.gov.my"
                      value={loginEmail}
                      onChange={(e) => setLoginEmail(e.target.value)}
                      className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-base sm:text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-slate-700">
                      Kata Laluan
                    </label>
                    <div className="relative mt-1">
                      <input
                        type={showLoginPw ? "text" : "password"}
                        required
                        placeholder="Masukkan kata laluan"
                        value={loginPassword}
                        onChange={(e) => setLoginPassword(e.target.value)}
                        className="w-full rounded-lg border border-slate-300 bg-white py-2 pl-3 pr-10 text-base sm:text-sm"
                      />
                      <button
                        type="button"
                        onClick={() => setShowLoginPw((v) => !v)}
                        aria-label={showLoginPw ? "Sembunyikan kata laluan" : "Tunjukkan kata laluan"}
                        className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-slate-500 hover:text-slate-800"
                      >
                        {showLoginPw ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </button>
                    </div>
                  </div>
                </div>
                <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
                  <button
                    type="submit"
                    disabled={loading}
                    className="inline-flex min-h-[44px] items-center gap-1.5 rounded-lg bg-[#0f2744] px-4 py-2 text-xs font-bold text-white hover:bg-slate-800 disabled:opacity-60"
                  >
                    {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <KeyRound className="h-3.5 w-3.5" />}
                    Log Masuk ke i-UIP
                  </button>
                  <div className="flex flex-wrap items-center gap-3">
                    <button
                      type="button"
                      onClick={() => setShowForgotHelp((v) => !v)}
                      className="text-xs font-semibold text-slate-600 hover:underline"
                    >
                      Lupa Kata Laluan?
                    </button>
                    <button
                      type="button"
                      onClick={() => setTab("register")}
                      className="text-xs font-bold text-blue-700 hover:underline"
                    >
                      Belum ada akaun? Daftar Akaun Baharu →
                    </button>
                  </div>
                </div>
                {showForgotHelp && (
                  <div className="rounded-lg border border-blue-200 bg-blue-50 p-3 text-xs text-blue-950 leading-relaxed">
                    <strong>Bantuan Pemulihan Akaun:</strong> Jika e-mel anda ialah akaun Google/Workspace, klik tab{" "}
                    <button
                      type="button"
                      onClick={() => setTab("google")}
                      className="font-bold underline"
                    >
                      Google
                    </button>{" "}
                    untuk log masuk terus tanpa kata laluan (sistem akan menyambungkan akaun e-mel anda secara automatik).
                  </div>
                )}
              </form>
            </div>
          )}

          {/* TAB 2: DAFTAR AKAUN BAHARU */}
          {tab === "register" && !officer && (
            <form onSubmit={handleRegister} className="space-y-4">
              <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-4 space-y-3">
                <div>
                  <h4 className="flex items-center gap-1.5 text-sm font-extrabold text-slate-900">
                    <ShieldCheck className="h-4 w-4 text-[#0f2744]" />
                    Daftar Akaun Pegawai UIP (Seluruh Malaysia)
                  </h4>
                  <p className="mt-0.5 text-xs text-slate-600">
                    Isi maklumat asas pegawai dan pilih Negeri / PKD / PKK / PKB anda supaya semua dokumen mahkamah &amp; kompaun dijana mengikut bidang kuasa daerah anda.
                  </p>
                </div>

                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  <div className="sm:col-span-2">
                    <label className="text-xs font-semibold text-slate-700">
                      E-mel Rasmi KKM / Kerja <span className="text-rose-600">*</span>
                    </label>
                    <input
                      type="email"
                      required
                      placeholder="nama@moh.gov.my"
                      value={regForm.email}
                      onChange={(e) => setRegForm({ ...regForm, email: e.target.value })}
                      className="mt-1 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-base text-slate-900 sm:text-sm"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-semibold text-slate-700">
                      Kata Laluan (min. 8 aksara) <span className="text-rose-600">*</span>
                    </label>
                    <div className="relative mt-1">
                      <input
                        type={showRegPw ? "text" : "password"}
                        required
                        minLength={8}
                        maxLength={128}
                        value={regForm.password}
                        onChange={(e) => setRegForm({ ...regForm, password: e.target.value })}
                        className="w-full rounded-xl border border-slate-300 bg-white py-2 pl-3 pr-10 text-base text-slate-900 sm:text-sm"
                      />
                      <button
                        type="button"
                        onClick={() => setShowRegPw((v) => !v)}
                        aria-label={showRegPw ? "Sembunyikan kata laluan" : "Tunjukkan kata laluan"}
                        className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-slate-500 hover:text-slate-800"
                      >
                        {showRegPw ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </button>
                    </div>
                  </div>
                  <div>
                    <label className="text-xs font-semibold text-slate-700">
                      Sahkan Kata Laluan <span className="text-rose-600">*</span>
                    </label>
                    <input
                      type={showRegPw ? "text" : "password"}
                      required
                      minLength={8}
                      maxLength={128}
                      value={regForm.confirm_password}
                      onChange={(e) => setRegForm({ ...regForm, confirm_password: e.target.value })}
                      className="mt-1 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-base text-slate-900 sm:text-sm"
                    />
                  </div>
                  <div className="sm:col-span-2">
                    <label className="text-xs font-semibold text-slate-700">
                      Nama Penuh &amp; Gelaran Pegawai <span className="text-rose-600">*</span>
                    </label>
                    <input
                      type="text"
                      required
                      placeholder="cth: PPKP Mohd Amirul bin Zaki"
                      value={regForm.full_name}
                      onChange={(e) => setRegForm({ ...regForm, full_name: e.target.value })}
                      className="mt-1 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-base text-slate-900 sm:text-sm"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-semibold text-slate-700">
                      Jabatan Kesihatan Negeri (JKN / JKWP)
                    </label>
                    <select
                      value={regForm.state_jkn}
                      onChange={(e) => setRegForm({ ...regForm, state_jkn: e.target.value })}
                      className="mt-1 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-base text-slate-900 sm:text-sm"
                    >
                      {MALAYSIA_JKN_OPTIONS.map((opt) => (
                        <option key={opt.value} value={opt.value}>
                          {opt.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="text-xs font-semibold text-slate-700">
                      Pejabat Kesihatan (PKD / PKK Sabah / PKB Sarawak)
                    </label>
                    <input
                      type="text"
                      placeholder="cth: PKD Petaling / PKK Kota Kinabalu / PKB Kuching"
                      value={regForm.district_pkd}
                      onChange={(e) => setRegForm({ ...regForm, district_pkd: e.target.value })}
                      className="mt-1 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-base text-slate-900 sm:text-sm"
                    />
                  </div>
                </div>
              </div>

              <div className="rounded-xl border border-slate-200 bg-white p-3.5">
                <button
                  type="button"
                  onClick={() => setShowOfficeDefaults((v) => !v)}
                  className="flex min-h-[40px] w-full items-center justify-between gap-2 text-left"
                >
                  <div>
                    <h4 className="flex items-center gap-1.5 text-xs font-bold text-slate-900">
                      <Building2 className="h-4 w-4 text-emerald-700" />
                      Lengkapkan Kad Kuasa, Gred SSPA, Mahkamah &amp; Sijil 90A (Pilihan)
                    </h4>
                    <p className="mt-0.5 text-xs text-slate-500">
                      Boleh diisi sekarang atau dikemas kini bila-bila masa dalam Profil Pegawai
                    </p>
                  </div>
                  <span className="shrink-0 text-xs font-bold text-[#0f2744]">
                    {showOfficeDefaults ? "Tutup ▴" : "Isi Sekarang ▾"}
                  </span>
                </button>
                {showOfficeDefaults && (
                  <div className="mt-3 grid grid-cols-1 gap-3 border-t border-slate-200 pt-3 sm:grid-cols-2">
                    <div>
                      <label className="text-xs font-semibold text-slate-700">No. Kad Kuasa Rasmi KKM</label>
                      <input
                        type="text"
                        placeholder="cth: KKM-SEL-2026-088"
                        value={regForm.kkm_authority_card_no}
                        onChange={(e) => setRegForm({ ...regForm, kkm_authority_card_no: e.target.value })}
                        className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-base sm:text-sm"
                      />
                    </div>
                    <div>
                      <label className="text-xs font-semibold text-slate-700">No. K/P (untuk Sijil 90A)</label>
                      <input
                        type="text"
                        placeholder="890101-10-5511"
                        value={regForm.ic_number}
                        onChange={(e) => setRegForm({ ...regForm, ic_number: e.target.value })}
                        className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-base sm:text-sm"
                      />
                    </div>
                    <div>
                      <label className="text-xs font-semibold text-slate-700">Jawatan</label>
                      <select
                        value={regForm.designation}
                        onChange={(e) => setRegForm({ ...regForm, designation: e.target.value })}
                        className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-base sm:text-sm"
                      >
                        <option>Penolong Pegawai Kesihatan Persekitaran (PPKP)</option>
                        <option>Pegawai Kesihatan Persekitaran (PKP)</option>
                        <option>Pegawai Perubatan Kesihatan Daerah (PKD)</option>
                        <option>Pegawai Sains (Entomologi / Mikrobiologi)</option>
                      </select>
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="text-xs font-semibold text-slate-700">Gred (SSPA)</label>
                        <select
                          value={regForm.grade}
                          onChange={(e) => setRegForm({ ...regForm, grade: e.target.value })}
                          className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-2.5 py-2 text-base sm:text-sm"
                        >
                          {renderSspaGradeOptions()}
                        </select>
                      </div>
                      <div>
                        <label className="text-xs font-semibold text-slate-700">Peranan UIP</label>
                        <select
                          value={regForm.system_role}
                          onChange={(e) => setRegForm({ ...regForm, system_role: e.target.value })}
                          className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-2.5 py-2 text-base sm:text-sm"
                        >
                          <option value="PEGAWAI_PEMERIKSA">Pegawai Pemeriksa</option>
                          <option value="PEGAWAI_PENYIASAT">Pegawai Penyiasat (IO)</option>
                          <option value="PENYEMAK_KANAN_UIP">Penyemak Kanan / KPPKP</option>
                          <option value="PEGAWAI_PENDAKWA">Pegawai Pendakwa (PO)</option>
                        </select>
                      </div>
                    </div>
                    <div className="sm:col-span-2">
                      <label className="text-xs font-semibold text-slate-700">Alamat Lengkap Pejabat Kesihatan (untuk Notis Kompaun &amp; Saman)</label>
                      <input
                        type="text"
                        placeholder="cth: Pejabat Kesihatan Daerah Petaling, No. 101, Persiaran Kayangan, 40000 Shah Alam, Selangor"
                        value={regForm.office_address}
                        onChange={(e) => setRegForm({ ...regForm, office_address: e.target.value })}
                        className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-base sm:text-sm"
                      />
                    </div>
                    <div>
                      <label className="text-xs font-semibold text-slate-700">Unit / Seksyen</label>
                      <input
                        type="text"
                        value={regForm.unit_assignment}
                        onChange={(e) => setRegForm({ ...regForm, unit_assignment: e.target.value })}
                        className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-base sm:text-sm"
                      />
                    </div>
                    <div>
                      <label className="text-xs font-semibold text-slate-700">No. Tauliah S.377(b) KTJ (Jika Pegawai Pendakwa)</label>
                      <input
                        type="text"
                        placeholder="Pilihan"
                        value={regForm.prosecution_authorization_no}
                        onChange={(e) => setRegForm({ ...regForm, prosecution_authorization_no: e.target.value })}
                        className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-base sm:text-sm"
                      />
                    </div>
                    <div className="sm:col-span-2">
                      <label className="text-xs font-semibold text-slate-700">Mahkamah Majistret Bidang Kuasa</label>
                      <input
                        type="text"
                        placeholder="cth: MAHKAMAH MAJISTRET DI SHAH ALAM, DALAM NEGERI SELANGOR"
                        value={regForm.default_magistrate_court}
                        onChange={(e) => setRegForm({ ...regForm, default_magistrate_court: e.target.value })}
                        className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-base sm:text-sm"
                      />
                    </div>
                    <div>
                      <label className="text-xs font-semibold text-slate-700">Kamera / Telefon Rasmi S.90A</label>
                      <input
                        type="text"
                        value={regForm.default_camera_desc}
                        onChange={(e) => setRegForm({ ...regForm, default_camera_desc: e.target.value })}
                        className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-base sm:text-sm"
                      />
                    </div>
                    <div>
                      <label className="text-xs font-semibold text-slate-700">Komputer Pejabat S.90A</label>
                      <input
                        type="text"
                        value={regForm.default_computer_desc}
                        onChange={(e) => setRegForm({ ...regForm, default_computer_desc: e.target.value })}
                        className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-base sm:text-sm"
                      />
                    </div>
                    <div className="sm:col-span-2">
                      <label className="text-xs font-semibold text-slate-700">Pencetak Pejabat S.90A</label>
                      <input
                        type="text"
                        value={regForm.default_printer_desc}
                        onChange={(e) => setRegForm({ ...regForm, default_printer_desc: e.target.value })}
                        className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-base sm:text-sm"
                      />
                    </div>
                  </div>
                )}
              </div>

              <button
                type="submit"
                disabled={loading}
                className="inline-flex min-h-[46px] w-full items-center justify-center gap-2 rounded-xl bg-[#0f2744] px-5 py-2.5 text-sm font-bold text-white hover:bg-slate-800 disabled:opacity-60 sm:w-auto"
              >
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <UserPlus className="h-4 w-4" />}
                Daftar &amp; Mula Guna
              </button>
            </form>
          )}

          {/* TAB 3: PROFIL PEGAWAI AKTIF */}
          {officer && (
            <form onSubmit={handleSaveProfile} className="space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-emerald-200 bg-emerald-50/70 p-3">
                <div>
                  <div className="text-xs font-bold text-emerald-950">
                    {officer.full_name} ({officer.grade})
                  </div>
                  <div className="text-[11px] text-emerald-800">
                    {officer.email} | Kad Kuasa: {officer.kkm_authority_card_no || "Belum diisi"} | {officer.district_pkd || "Sila pilih PKD/PKK/PKB"}
                  </div>
                </div>
                <button
                  type="button"
                  onClick={handleLogout}
                  className="inline-flex min-h-[38px] items-center gap-1 rounded-lg bg-rose-600 px-3 py-1.5 text-xs font-bold text-white hover:bg-rose-700"
                >
                  <LogOut className="h-3.5 w-3.5" /> Log Keluar
                </button>
              </div>

              {(!profileForm.state_jkn || !profileForm.district_pkd) && (
                <div className="rounded-xl border border-amber-300 bg-amber-50 px-3.5 py-2.5 text-xs font-semibold text-amber-950">
                  Sila pilih <strong>Jabatan Kesihatan Negeri (JKN/JKWP)</strong> dan masukkan <strong>Pejabat Kesihatan (PKD / PKK / PKB)</strong> anda di bawah supaya kepala surat Borang 114, Saman 111 dan Notis Kompaun dicetak mengikut daerah anda.
                </div>
              )}

              <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
                <div>
                  <label className="text-xs font-semibold text-slate-700">Nama Penuh Pegawai</label>
                  <input
                    type="text"
                    value={profileForm.full_name || ""}
                    onChange={(e) => setProfileForm({ ...profileForm, full_name: e.target.value })}
                    className="mt-0.5 w-full rounded-lg border border-slate-300 px-2.5 py-2 text-base sm:text-sm"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-700">No. K/P (untuk Sijil 90A)</label>
                  <input
                    type="text"
                    placeholder="cth: 890101-10-5511"
                    value={profileForm.ic_number || ""}
                    onChange={(e) => setProfileForm({ ...profileForm, ic_number: e.target.value })}
                    className="mt-0.5 w-full rounded-lg border border-slate-300 px-2.5 py-2 text-base sm:text-sm"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-700">Jawatan</label>
                  <select
                    value={profileForm.designation || "Penolong Pegawai Kesihatan Persekitaran (PPKP)"}
                    onChange={(e) => setProfileForm({ ...profileForm, designation: e.target.value })}
                    className="mt-0.5 w-full rounded-lg border border-slate-300 bg-white px-2.5 py-2 text-base sm:text-sm"
                  >
                    <option>Penolong Pegawai Kesihatan Persekitaran (PPKP)</option>
                    <option>Pegawai Kesihatan Persekitaran (PKP)</option>
                    <option>Pegawai Perubatan Kesihatan Daerah (PKD)</option>
                    <option>Pegawai Sains (Entomologi / Mikrobiologi)</option>
                  </select>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-xs font-semibold text-slate-700">Gred (SSPA)</label>
                    <select
                      value={profileForm.grade || "U5"}
                      onChange={(e) => setProfileForm({ ...profileForm, grade: e.target.value })}
                      className="mt-0.5 w-full rounded-lg border border-slate-300 bg-white px-2.5 py-2 text-base sm:text-sm"
                    >
                      {renderSspaGradeOptions()}
                    </select>
                  </div>
                  <div>
                    <label className="text-xs font-semibold text-slate-700">Peranan UIP</label>
                    <select
                      value={profileForm.system_role || "PEGAWAI_PENYIASAT"}
                      onChange={(e) => setProfileForm({ ...profileForm, system_role: e.target.value })}
                      className="mt-0.5 w-full rounded-lg border border-slate-300 bg-white px-2.5 py-2 text-base sm:text-sm"
                    >
                      <option value="PEGAWAI_PEMERIKSA">Pegawai Pemeriksa</option>
                      <option value="PEGAWAI_PENYIASAT">Pegawai Penyiasat (IO)</option>
                      <option value="PENYEMAK_KANAN_UIP">Penyemak Kanan / KPPKP</option>
                      <option value="PEGAWAI_PENDAKWA">Pegawai Pendakwa (PO)</option>
                    </select>
                  </div>
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-700">No. Kad Kuasa KKM</label>
                  <input
                    type="text"
                    placeholder="cth: KKM-SEL-2026-088"
                    value={profileForm.kkm_authority_card_no || ""}
                    onChange={(e) => setProfileForm({ ...profileForm, kkm_authority_card_no: e.target.value })}
                    className="mt-0.5 w-full rounded-lg border border-slate-300 px-2.5 py-2 text-base sm:text-sm"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-700">No. Tauliah S.377(b) KTJ (Jika Pegawai Pendakwa)</label>
                  <input
                    type="text"
                    placeholder="Pilihan"
                    value={profileForm.prosecution_authorization_no || ""}
                    onChange={(e) => setProfileForm({ ...profileForm, prosecution_authorization_no: e.target.value })}
                    className="mt-0.5 w-full rounded-lg border border-slate-300 px-2.5 py-2 text-base sm:text-sm"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-700">Jabatan Kesihatan Negeri (JKN / JKWP)</label>
                  <select
                    value={profileForm.state_jkn || ""}
                    onChange={(e) => setProfileForm({ ...profileForm, state_jkn: e.target.value })}
                    className="mt-0.5 w-full rounded-lg border border-slate-300 bg-white px-2.5 py-2 text-base sm:text-sm"
                  >
                    {MALAYSIA_JKN_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                    {profileForm.state_jkn &&
                      !MALAYSIA_JKN_OPTIONS.some((o) => o.value === profileForm.state_jkn) && (
                        <option value={profileForm.state_jkn}>{profileForm.state_jkn}</option>
                      )}
                  </select>
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-700">Pejabat Kesihatan (PKD / PKK Sabah / PKB Sarawak)</label>
                  <input
                    type="text"
                    placeholder="cth: PKD Petaling / PKK Kota Kinabalu / PKB Kuching"
                    value={profileForm.district_pkd || ""}
                    onChange={(e) => setProfileForm({ ...profileForm, district_pkd: e.target.value })}
                    className="mt-0.5 w-full rounded-lg border border-slate-300 px-2.5 py-2 text-base sm:text-sm"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-700">Alamat Lengkap Pejabat Kesihatan</label>
                  <input
                    type="text"
                    placeholder="Untuk bayaran kaunter Notis Kompaun & Saman"
                    value={profileForm.office_address || ""}
                    onChange={(e) => setProfileForm({ ...profileForm, office_address: e.target.value })}
                    className="mt-0.5 w-full rounded-lg border border-slate-300 px-2.5 py-2 text-base sm:text-sm"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-700">Unit / Seksyen</label>
                  <input
                    type="text"
                    value={profileForm.unit_assignment || ""}
                    onChange={(e) => setProfileForm({ ...profileForm, unit_assignment: e.target.value })}
                    className="mt-0.5 w-full rounded-lg border border-slate-300 px-2.5 py-2 text-base sm:text-sm"
                  />
                </div>
                <div className="sm:col-span-2">
                  <label className="text-xs font-semibold text-slate-700">Mahkamah Majistret Bidang Kuasa</label>
                  <input
                    type="text"
                    placeholder="cth: MAHKAMAH MAJISTRET DI SHAH ALAM, DALAM NEGERI SELANGOR"
                    value={profileForm.default_magistrate_court || ""}
                    onChange={(e) => setProfileForm({ ...profileForm, default_magistrate_court: e.target.value })}
                    className="mt-0.5 w-full rounded-lg border border-slate-300 px-2.5 py-2 text-base sm:text-sm"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-700">Kamera Rasmi (Sijil 90A)</label>
                  <input
                    type="text"
                    value={profileForm.default_camera_desc || ""}
                    onChange={(e) => setProfileForm({ ...profileForm, default_camera_desc: e.target.value })}
                    className="mt-0.5 w-full rounded-lg border border-slate-300 px-2.5 py-2 text-base sm:text-sm"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-700">Komputer Pejabat (Sijil 90A)</label>
                  <input
                    type="text"
                    value={profileForm.default_computer_desc || ""}
                    onChange={(e) => setProfileForm({ ...profileForm, default_computer_desc: e.target.value })}
                    className="mt-0.5 w-full rounded-lg border border-slate-300 px-2.5 py-2 text-base sm:text-sm"
                  />
                </div>
                <div className="sm:col-span-2">
                  <label className="text-xs font-semibold text-slate-700">Pencetak Pejabat (Sijil 90A)</label>
                  <input
                    type="text"
                    value={profileForm.default_printer_desc || ""}
                    onChange={(e) => setProfileForm({ ...profileForm, default_printer_desc: e.target.value })}
                    className="mt-0.5 w-full rounded-lg border border-slate-300 px-2.5 py-2 text-base sm:text-sm"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="inline-flex min-h-[44px] w-full items-center justify-center gap-1.5 rounded-xl bg-[#0f2744] px-4 py-2.5 text-xs font-bold text-white hover:bg-slate-800 disabled:opacity-60 sm:w-auto"
              >
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                Simpan Kemas Kini Profil
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
