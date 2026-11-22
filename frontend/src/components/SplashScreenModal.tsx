"use client";

import React, { useEffect, useRef, useState } from "react";
import {
  ArrowRight,
  CheckCircle2,
  ExternalLink,
  FileCheck2,
  FileText,
  Loader2,
  Mail,
  MessageSquareQuote,
  Scale,
  ShieldCheck,
  UserCheck,
  X,
} from "lucide-react";
import { fetchRuntimeSettings, googleSignInOfficer } from "@/lib/api";
import type { ActiveAppMode } from "@/components/TopNavbar";
import type { OfficerProfile } from "@/lib/types";

const DEFAULT_GOOGLE_CLIENT_ID =
  "290203327893-b7f42feigfscdd4rfo1eh1a3n5age7ev.apps.googleusercontent.com";

interface SplashScreenModalProps {
  open: boolean;
  officer: OfficerProfile | null;
  onEnterApp: (mode: ActiveAppMode) => void;
  onOpenGoogleAuth: () => void;
  onOpenEmailAuth: (initialTab: "login" | "register") => void;
  onAuthenticated?: (officer: OfficerProfile, token: string) => void;
  onClose: () => void;
}

export default function SplashScreenModal({
  open,
  officer,
  onEnterApp,
  onOpenGoogleAuth,
  onOpenEmailAuth,
  onAuthenticated,
  onClose,
}: SplashScreenModalProps) {
  const [googleClientId, setGoogleClientId] = useState(DEFAULT_GOOGLE_CLIENT_ID);
  const [gsiReady, setGsiReady] = useState(false);
  const [gsiFailed, setGsiFailed] = useState(false);
  const [loading, setLoading] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const gsiBtnRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!open || officer) return;
    setAuthError(null);
    fetchRuntimeSettings()
      .then((s) => {
        const cid = (s.google_client_id || "").trim() || DEFAULT_GOOGLE_CLIENT_ID;
        setGoogleClientId(cid);
      })
      .catch(() => {
        setGoogleClientId(DEFAULT_GOOGLE_CLIENT_ID);
      });
  }, [open, officer]);

  useEffect(() => {
    if (!open || !officer) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, officer, onClose]);

  useEffect(() => {
    if (!open || officer || !googleClientId) {
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
            setAuthError(null);
            try {
              const res = await googleSignInOfficer({
                id_token: response.credential,
                district_pkd: "Pejabat Kesihatan Daerah Kuala Nerus",
                state_jkn: "Jabatan Kesihatan Negeri Terengganu",
              });
              if (onAuthenticated) {
                onAuthenticated(res.user, res.token);
              } else {
                onClose();
              }
            } catch (err) {
              setAuthError(
                err instanceof Error ? err.message : "Pengesahan Akaun Google gagal."
              );
            } finally {
              setLoading(false);
            }
          },
        });
        const btnWidth = Math.max(
          240,
          Math.min(340, (gsiBtnRef.current.parentElement?.clientWidth || 320) - 8)
        );
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
  }, [open, officer, googleClientId, onAuthenticated, onClose]);

  const handlePopupGoogle = () => {
    const oauth2 = window.google?.accounts?.oauth2;
    if (!oauth2) {
      onOpenGoogleAuth();
      return;
    }
    setAuthError(null);
    const tokenClient = oauth2.initTokenClient({
      client_id: googleClientId,
      scope: "openid email profile",
      callback: async (tokenResp: { access_token?: string; error?: string }) => {
        if (tokenResp.error || !tokenResp.access_token) {
          setAuthError("Log masuk Google dibatalkan atau gagal memberi akses.");
          return;
        }
        setLoading(true);
        try {
          const res = await googleSignInOfficer({
            access_token: tokenResp.access_token,
            district_pkd: "Pejabat Kesihatan Daerah Kuala Nerus",
            state_jkn: "Jabatan Kesihatan Negeri Terengganu",
          });
          if (onAuthenticated) {
            onAuthenticated(res.user, res.token);
          } else {
            onClose();
          }
        } catch (err) {
          setAuthError(err instanceof Error ? err.message : "Pengesahan Google gagal.");
        } finally {
          setLoading(false);
        }
      },
    });
    tokenClient.requestAccessToken({ prompt: "select_account" });
  };

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Log Masuk i-UIP Nerus"
      onClick={() => {
        if (officer) onClose();
      }}
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-950/80 p-3 backdrop-blur-sm sm:items-center sm:p-6"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="my-auto relative w-full max-w-4xl overflow-hidden rounded-3xl border border-slate-700/60 bg-white shadow-2xl"
      >
        <div className="grid grid-cols-1 md:grid-cols-12">
          {/* BAHAGIAN KIRI: IDENTITI RASMI & MOTO PKDKN (Padat pada telefon supaya butang log masuk terus kelihatan) */}
          <div className="flex flex-col justify-between bg-gradient-to-br from-[#08192e] via-[#0f2744] to-[#133b69] p-4 text-white sm:p-5 md:col-span-5 md:p-7">
            <div className="space-y-3 sm:space-y-4">
              {/* Logo i-UIP Nerus */}
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src="/images/logo-iuip-nerus.png"
                    alt="Logo Rasmi i-UIP Nerus"
                    className="h-12 w-12 shrink-0 rounded-full bg-white p-1 object-contain shadow-md ring-2 ring-amber-400/80 sm:h-14 sm:w-14"
                  />
                  <div>
                    <h2 className="text-lg font-extrabold tracking-tight text-white sm:text-2xl">
                      i-UIP Nerus
                    </h2>
                    <p className="text-xs font-medium text-amber-200">
                      Unit Inspektorat &amp; Perundangan (UIP)
                    </p>
                  </div>
                </div>
                <div className="rounded-xl bg-white/95 px-2 py-1 shadow-sm md:hidden">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src="/images/logo-pkdkn.png"
                    alt="Logo PKD Kuala Nerus"
                    className="h-7 w-auto object-contain"
                  />
                </div>
              </div>

              {/* Logo PKD Kuala Nerus & Moto Rasmi (Penuh di skrin sederhana/desktop) */}
              <div className="hidden rounded-2xl bg-white/95 p-3 text-slate-900 shadow-sm space-y-2 md:block">
                <div className="flex items-center justify-center">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src="/images/logo-pkdkn.png"
                    alt="Logo Pejabat Kesihatan Daerah Kuala Nerus (KN2S)"
                    className="h-11 w-auto object-contain"
                  />
                </div>
                <div className="border-t border-slate-200 pt-1.5 text-center">
                  <p className="text-[11px] font-extrabold italic leading-snug text-[#0f2744]">
                    &ldquo;Satu Hati, Satu Tekad: Memacu Kecemerlangan Kesihatan Kuala Nerus&rdquo;
                  </p>
                </div>
              </div>

              <div className="hidden space-y-1.5 text-xs text-slate-200 md:block">
                <p className="font-semibold text-white">Pembantu Kerja Harian PPKP &amp; IO:</p>
                <ul className="space-y-1 text-slate-300">
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-emerald-400" />
                    Rujuk seksyen &amp; SOP lapangan
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-emerald-400" />
                    Semak &amp; cetak Notis Kompaun (.docx)
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-emerald-400" />
                    Semakan Pra-TPR &amp; bina Kertas Siasatan lengkap
                  </li>
                </ul>
              </div>
            </div>

            <div className="mt-4 hidden border-t border-white/15 pt-3 md:block">
              <a
                href="https://g.dev/syrzy"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center justify-between text-xs text-slate-300 hover:text-white"
              >
                <span>
                  Dibangunkan oleh Dev: <strong className="text-amber-300">g.dev/syrzy</strong>
                </span>
                <ExternalLink className="h-3.5 w-3.5" />
              </a>
            </div>
          </div>

          {/* BAHAGIAN KANAN: 1-TAP SIGN-IN (JIKA BELUM MASUK) ATAU PINTASAN TUGAS (JIKA SUDAH MASUK) */}
          <div className="flex flex-col justify-center bg-slate-50 p-4 sm:p-7 md:col-span-7">
            {officer ? (
              <div className="space-y-4">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="inline-flex items-center gap-1.5 rounded-full bg-emerald-100 px-2.5 py-0.5 text-[11px] font-bold text-emerald-800">
                      <ShieldCheck className="h-3.5 w-3.5" /> Sesi Pegawai Aktif
                    </div>
                    <h3 className="mt-1.5 text-base font-extrabold text-slate-900">
                      Selamat bertugas, {officer.full_name}
                    </h3>
                    <p className="text-xs text-slate-600">
                      {officer.district_pkd} • Gred {officer.grade}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={onClose}
                    aria-label="Tutup"
                    className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-lg text-slate-500 hover:bg-slate-200 hover:text-slate-900"
                    title="Tutup"
                  >
                    <X className="h-5 w-5" />
                  </button>
                </div>

                <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
                  <button
                    type="button"
                    onClick={() => onEnterApp("advisor")}
                    className="flex items-start gap-3 rounded-xl border border-slate-200 bg-white p-3.5 text-left transition hover:border-indigo-400 hover:bg-indigo-50/40"
                  >
                    <div className="rounded-lg bg-indigo-100 p-2 text-indigo-700">
                      <MessageSquareQuote className="h-4 w-4" />
                    </div>
                    <div>
                      <div className="text-xs font-extrabold text-slate-900">Tanya Pakar UIP</div>
                      <div className="text-[11px] text-slate-600">Seksyen kesalahan, had denda &amp; SOP</div>
                    </div>
                  </button>

                  <button
                    type="button"
                    onClick={() => onEnterApp("compound")}
                    className="flex items-start gap-3 rounded-xl border border-slate-200 bg-white p-3.5 text-left transition hover:border-amber-400 hover:bg-amber-50/40"
                  >
                    <div className="rounded-lg bg-amber-100 p-2 text-amber-800">
                      <FileCheck2 className="h-4 w-4" />
                    </div>
                    <div>
                      <div className="text-xs font-extrabold text-slate-900">Notis Kompaun</div>
                      <div className="text-[11px] text-slate-600">Isi, semak &amp; cetak notis Word</div>
                    </div>
                  </button>

                  <button
                    type="button"
                    onClick={() => onEnterApp("audit")}
                    className="flex items-start gap-3 rounded-xl border border-slate-200 bg-white p-3.5 text-left transition hover:border-emerald-400 hover:bg-emerald-50/40"
                  >
                    <div className="rounded-lg bg-emerald-100 p-2 text-emerald-700">
                      <Scale className="h-4 w-4" />
                    </div>
                    <div>
                      <div className="text-xs font-extrabold text-slate-900">Semak IP (Pra-TPR)</div>
                      <div className="text-[11px] text-slate-600">Kesan kuiri &amp; seksyen salah</div>
                    </div>
                  </button>

                  <button
                    type="button"
                    onClick={() => onEnterApp("draft")}
                    className="flex items-start gap-3 rounded-xl border border-slate-200 bg-white p-3.5 text-left transition hover:border-blue-400 hover:bg-blue-50/40"
                  >
                    <div className="rounded-lg bg-blue-100 p-2 text-blue-700">
                      <FileText className="h-4 w-4" />
                    </div>
                    <div>
                      <div className="text-xs font-extrabold text-slate-900">Bina Fail IP (.docx)</div>
                      <div className="text-[11px] text-slate-600">Edit Borang 114, DS, S.112 &amp; S.90A</div>
                    </div>
                  </button>
                </div>

                <div className="flex justify-end pt-1">
                  <button
                    type="button"
                    onClick={onClose}
                    className="inline-flex min-h-[44px] items-center gap-1.5 rounded-xl bg-[#0f2744] px-4 py-2 text-xs font-bold text-white hover:bg-slate-800"
                  >
                    Teruskan <ArrowRight className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-3.5">
                <div>
                  <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2.5 py-0.5 text-[11px] font-bold text-amber-900">
                    Log Masuk Diperlukan
                  </span>
                  <h3 className="mt-1.5 text-lg font-extrabold text-slate-900">
                    Log Masuk Akaun Pegawai UIP
                  </h3>
                  <p className="mt-1 text-xs leading-relaxed text-slate-600">
                    Nama, No. Kad Kuasa &amp; PKD anda diisi secara automatik ke dalam Borang 114, Notis Kompaun &amp; Sijil 90A.
                  </p>
                </div>

                {authError && (
                  <div className="rounded-xl border border-rose-300 bg-rose-50 px-3.5 py-2.5 text-xs font-semibold text-rose-800">
                    {authError}
                  </div>
                )}

                {/* 1-Tap Google Sign-In Rasmi */}
                <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm space-y-3">
                  <div className="text-xs font-bold text-slate-800">
                    Cara Paling Pantas (1 Klik dengan Google)
                  </div>

                  {loading ? (
                    <div className="flex min-h-[44px] items-center justify-center gap-2 rounded-full bg-blue-50 text-xs font-bold text-blue-800">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Mengesahkan akaun Google anda...
                    </div>
                  ) : (
                    <div className="flex flex-col items-start gap-2">
                      <div ref={gsiBtnRef} className={gsiReady ? "min-h-[42px]" : ""} />
                      {!gsiReady && !gsiFailed && (
                        <button
                          type="button"
                          onClick={onOpenGoogleAuth}
                          className="inline-flex min-h-[44px] w-full items-center justify-center gap-2 rounded-full border border-slate-300 bg-white px-4 py-2 text-xs font-bold text-slate-800 hover:bg-slate-50"
                        >
                          Teruskan dengan Akaun Google
                        </button>
                      )}
                      {gsiFailed && (
                        <div className="w-full rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
                          Sistem log masuk Google tidak dapat dimuatkan (mungkin disekat rangkaian pejabat). Sila guna{" "}
                          <strong>Log Masuk E-mel</strong> di bawah.
                        </div>
                      )}
                      {gsiReady && (
                        <button
                          type="button"
                          onClick={handlePopupGoogle}
                          className="text-[11px] font-semibold text-blue-700 hover:underline"
                        >
                          Butang di atas disekat? Buka tetingkap Google →
                        </button>
                      )}
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-3 text-[11px] font-semibold text-slate-500">
                  <div className="h-px flex-1 bg-slate-200" />
                  <span>atau guna e-mel KKM / kerja</span>
                  <div className="h-px flex-1 bg-slate-200" />
                </div>

                <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                  <button
                    type="button"
                    onClick={() => onOpenEmailAuth("login")}
                    className="inline-flex min-h-[44px] items-center justify-center gap-1.5 rounded-xl bg-[#0f2744] px-4 py-2 text-xs font-bold text-white hover:bg-slate-800"
                  >
                    <Mail className="h-4 w-4" />
                    Log Masuk E-mel
                  </button>
                  <button
                    type="button"
                    onClick={() => onOpenEmailAuth("register")}
                    className="inline-flex min-h-[44px] items-center justify-center gap-1.5 rounded-xl border border-slate-300 bg-white px-4 py-2 text-xs font-bold text-slate-800 hover:bg-slate-100"
                  >
                    <UserCheck className="h-4 w-4 text-emerald-700" />
                    Daftar Akaun Baharu
                  </button>
                </div>

                <div className="pt-1 text-center text-[11px] text-slate-600 md:hidden">
                  <a
                    href="https://g.dev/syrzy"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-bold text-slate-700 hover:underline"
                  >
                    Dibangunkan oleh Dev: g.dev/syrzy
                  </a>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
