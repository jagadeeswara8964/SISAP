import * as React from "react";
import { cn } from "@/utils/cn";

export type BadgeTone =
  | "neutral"
  | "primary"
  | "testing"
  | "safety"
  | "reference"
  | "installation"
  | "terminology"
  | "related"
  | "ok"
  | "gov"
  | "warn"
  | "crit";

const TONES: Record<BadgeTone, string> = {
  neutral: "bg-ink-100 text-ink-700 border-ink-300",
  primary: "bg-gov-600 text-white border-gov-700",
  testing: "bg-[#2E6F9E] text-white border-[#2E6F9E]",
  safety: "bg-[#8A2E2E] text-white border-[#8A2E2E]",
  reference: "bg-ink-500 text-white border-ink-600",
  installation: "bg-[#4A6B2A] text-white border-[#4A6B2A]",
  terminology: "bg-[#5C4B8A] text-white border-[#5C4B8A]",
  related: "bg-[#7A6A55] text-white border-[#7A6A55]",
  ok: "bg-ok-50 text-ok-700 border-ok-100",
  gov: "bg-gov-50 text-gov-700 border-gov-100",
  warn: "bg-warn-50 text-warn-700 border-warn-100",
  crit: "bg-crit-50 text-crit-700 border-crit-100",
};

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  tone?: BadgeTone;
}

export function Badge({ className, tone = "neutral", ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded border px-2 py-0.5 text-[11px] font-semibold tracking-wide whitespace-nowrap",
        TONES[tone],
        className,
      )}
      {...props}
    />
  );
}
