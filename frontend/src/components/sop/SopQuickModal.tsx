"use client";

import React, { useEffect, useRef, useState } from "react";
import { X, Loader2, AlertCircle, RefreshCw, BookOpen } from "lucide-react";
import type { ActiveSopDetail } from "@/lib/types";
import { fetchActiveSopDetail } from "@/lib/api";
import { useLockBodyScroll, useModalFocusTrap } from "@/lib/uiHelpers";
import SopInteractiveViewer from "./SopInteractiveViewer";

// Kongsi cache butiran SOP merentas modal & direktori untuk muatan segera
const _sharedSopDetailCache = new Map<string, ActiveSopDetail>();

export function getCachedSopDetail(stem: string): ActiveSopDetail | undefined {
  return _sharedSopDetailCache.get(stem.toUpperCase());
}

export function setCachedSopDetail(stem: string, detail: ActiveSopDetail): void {
  _sharedSopDetailCache.set(stem.toUpperCase(), detail);
  if (detail.sop_id) {
    _sharedSopDetailCache.set(detail.sop_id.toUpperCase(), detail);
  }
}

interface SopQuickModalProps {
  sopCode: string | null;
  authToken?: string | null;
  onClose: () => void;
  onAskExpertWithSop?: (promptText: string) => void;
}

export default function SopQuickModal({
  sopCode,
  authToken,
  onClose,
  onAskExpertWithSop,
}: SopQuickModalProps) {
  const [currentCode, setCurrentCode] = useState<string | null>(sopCode);
  const [detail, setDetail] = useState<ActiveSopDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [retryTick, setRetryTick] = useState(0);
  const dialogRef = useRef<HTMLDivElement | null>(null);

  const isOpen = Boolean(sopCode);
  useLockBodyScroll(isOpen);
  useModalFocusTrap(dialogRef, isOpen, onClose);

  useEffect(() => {
    setCurrentCode(sopCode);
  }, [sopCode]);

  useEffect(() => {
    if (!currentCode) {
      setDetail(null);
      setError(null);
      return;
    }
    const cleanCode = currentCode.trim().split(/\s+/)[0].toUpperCase();
    const cached = getCachedSopDetail(cleanCode);
    if (cached && retryTick === 0) {
      setDetail(cached);
      setError(null);
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchActiveSopDetail(cleanCode, authToken)
      .then((res) => {
        if (cancelled) return;
        setCachedSopDetail(res.file_stem || cleanCode, res);
        setDetail(res);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setDetail(null);
        setError(
          err instanceof Error
            ? err.message
            : "Gagal memuatkan butiran SOP KKM. Sila cuba semula."
        );
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [currentCode, authToken, retryTick]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-slate-900/55 p-0 backdrop-blur-sm sm:items-center sm:p-4"
      onClick={onClose}
      role="presentation"
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label={`Rujukan Pantas SOP ${currentCode || ""}`}
        tabIndex={-1}
        onClick={(e) => e.stopPropagation()}
        className="flex h-[92vh] w-full max-w-4xl flex-col overflow-hidden rounded-t-2xl border border-slate-200 bg-slate-50 shadow-2xl sm:h-[88vh] sm:rounded-2xl"
      >
        <div className="flex items-center justify-between gap-3 border-b border-slate-200 bg-white px-4 py-3">
          <div className="flex items-center gap-2 text-sm font-bold text-slate-900">
            <BookOpen className="h-4 w-4 text-indigo-600" />
            <span>Rujukan Pantas SOP KKM</span>
            {currentCode && (
              <span className="rounded bg-indigo-50 px-2 py-0.5 font-mono text-xs text-indigo-700">
                {currentCode}
              </span>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Tutup tetingkap SOP"
            className="inline-flex h-8 w-8 items-center justify-center rounded-lg text-slate-500 hover:bg-slate-100 hover:text-slate-900"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 sm:p-5">
          {loading ? (
            <div className="flex flex-col items-center justify-center gap-3 py-16 text-slate-500">
              <Loader2 className="h-7 w-7 animate-spin text-indigo-600" />
              <p className="text-sm font-medium">Memuatkan SOP {currentCode}...</p>
            </div>
          ) : error ? (
            <div className="mx-auto max-w-lg rounded-xl border border-rose-200 bg-rose-50 p-5 text-center">
              <AlertCircle className="mx-auto h-7 w-7 text-rose-600" />
              <p className="mt-2 text-sm font-semibold text-rose-900">{error}</p>
              <button
                type="button"
                onClick={() => setRetryTick((t) => t + 1)}
                className="mt-3 inline-flex items-center gap-1.5 rounded-lg bg-rose-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-rose-700"
              >
                <RefreshCw className="h-3.5 w-3.5" />
                Cuba Semula
              </button>
            </div>
          ) : detail ? (
            <SopInteractiveViewer
              detail={detail}
              onOpenSop={(nextCode) => {
                setRetryTick(0);
                setCurrentCode(nextCode);
              }}
              onAskExpertWithSop={
                onAskExpertWithSop
                  ? (prompt) => {
                      onClose();
                      onAskExpertWithSop(prompt);
                    }
                  : undefined
              }
            />
          ) : null}
        </div>
      </div>
    </div>
  );
}
