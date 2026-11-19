"use client";

import React from "react";
import { CheckCircle2, Circle } from "lucide-react";
import type { ActiveAppMode } from "@/components/TopNavbar";

interface WorkspaceStepperProps {
  activeMode: ActiveAppMode;
  hasInput: boolean;
  hasAudit: boolean;
  hasDraft: boolean;
  hasCompound: boolean;
  onJumpInput?: () => void;
  onJumpResult?: () => void;
}

interface StepDef {
  num: number;
  label: string;
  hint: string;
  done: boolean;
  onClick?: () => void;
}

export default function WorkspaceStepper({
  activeMode,
  hasInput,
  hasAudit,
  hasDraft,
  hasCompound,
  onJumpInput,
  onJumpResult,
}: WorkspaceStepperProps) {
  let subtitle = "";
  let steps: StepDef[] = [];

  if (activeMode === "advisor") {
    subtitle =
      "Taip apa yang anda jumpa di lokasi atau klik mana-mana kad situasi untuk dapatkan seksyen caj, had denda dan langkah SOP.";
    steps = [
      { num: 1, label: "Cerita Situasi / Pilih Contoh", hint: "Taip atau klik kad", done: true },
      { num: 2, label: "Baca Keputusan & Seksyen", hint: "Jawapan dalam < 1 saat", done: false },
      { num: 3, label: "Terus Buka Borang Kes", hint: "1-klik pindah ke IP/Kompaun", done: false },
    ];
  } else if (activeMode === "compound") {
    subtitle =
      "Isi borang di bawah (atau tarik automatik daripada kes aktif / foto SSM), semak 10 perkara wajib, kemudian muat turun notis Word (.docx).";
    steps = [
      {
        num: 1,
        label: "Bahan Kes / Foto (Pilihan)",
        hint: "Tarik data atau isi terus",
        done: hasInput || hasCompound,
        onClick: onJumpInput,
      },
      {
        num: 2,
        label: "Isi & Semak 10 Perkara",
        hint: "Sahkan MyKad, RM & saksi",
        done: hasCompound,
        onClick: onJumpResult,
      },
      {
        num: 3,
        label: "Simpan & Muat Turun .docx",
        hint: "Sedia untuk serahan",
        done: hasCompound,
        onClick: onJumpResult,
      },
    ];
  } else if (activeMode === "draft") {
    subtitle =
      "Masukkan fakta kes (atau tarik fail PDF / foto bukti), jana 11 dokumen IP automatik, klik mana-mana kotak putih untuk edit, dan muat turun Word (.docx).";
    steps = [
      {
        num: 1,
        label: "Fakta Kes / Tarik Fail",
        hint: "Teks, PDF, Word atau Foto",
        done: hasInput,
        onClick: onJumpInput,
      },
      {
        num: 2,
        label: "Jana & Edit Borang 114 / IP",
        hint: "Semua kotak boleh diedit",
        done: hasDraft,
        onClick: onJumpResult,
      },
      {
        num: 3,
        label: "Simpan & Muat Turun .docx",
        hint: "Pakej IP lengkap Mahkamah",
        done: hasDraft,
        onClick: onJumpResult,
      },
    ];
  } else if (activeMode === "audit" || activeMode === "redaction") {
    subtitle =
      "Tarik masuk PDF Kertas Siasatan, gambar bukti atau catatan kes untuk semakan 20 perkara wajib Pra-TPR serta penutupan data peribadi (PDPA).";
    steps = [
      {
        num: 1,
        label: "Muat Naik Fail IP / Teks",
        hint: "PDF, Word, Gambar atau Teks",
        done: hasInput,
        onClick: onJumpInput,
      },
      {
        num: 2,
        label: "Semak 20 Kriteria Pra-TPR",
        hint: "Kesan kuiri & seksyen salah",
        done: hasAudit,
        onClick: onJumpResult,
      },
      {
        num: 3,
        label: "Baiki dalam Editor / Privasi",
        hint: "Klik mana-mana isu untuk baiki",
        done: hasAudit && hasDraft,
        onClick: onJumpResult,
      },
    ];
  } else {
    return null;
  }

  return (
    <div className="mx-auto w-full max-w-[1680px] px-3 pt-2.5 sm:px-4">
      <div className="rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 shadow-sm">
        <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
          <div className="grid grid-cols-3 gap-1.5 sm:gap-2">
            {steps.map((step) => {
              const Wrapper = step.onClick ? "button" : "div";
              return (
                <Wrapper
                  key={step.num}
                  {...(step.onClick ? { type: "button" as const, onClick: step.onClick } : {})}
                  className={`flex items-center gap-2 rounded-lg border px-2 py-1.5 text-left transition ${
                    step.done
                      ? "border-emerald-200 bg-emerald-50/70 text-emerald-950"
                      : "border-slate-200 bg-slate-50/70 text-slate-700"
                  } ${step.onClick ? "cursor-pointer hover:border-blue-400 hover:bg-blue-50/40" : ""}`}
                >
                  {step.done ? (
                    <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600" />
                  ) : (
                    <span className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-[#0f2744] text-[10px] font-extrabold text-white">
                      {step.num}
                    </span>
                  )}
                  <div className="min-w-0">
                    <div className="truncate text-[11px] font-bold leading-tight">
                      {step.label}
                    </div>
                    <div className="hidden truncate text-[10px] opacity-75 sm:block">
                      {step.hint}
                    </div>
                  </div>
                </Wrapper>
              );
            })}
          </div>
          <p className="text-[11px] leading-snug text-slate-600 lg:max-w-md lg:text-right">
            <span className="inline-flex items-center gap-1 font-bold text-[#0f2744]">
              <Circle className="h-2 w-2 fill-blue-600 text-blue-600" />
              Panduan Ringkas:
            </span>{" "}
            {subtitle}
          </p>
        </div>
      </div>
    </div>
  );
}
