import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/** Merge conditional class names, resolving Tailwind conflicts. */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

/** Format a date string for display. */
export function formatDate(value: string | undefined): string {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** Short date only. */
export function formatDay(value: string | undefined): string {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

/** 0-100 score to a display percentage string. */
export function percent(value: number): string {
  return `${Math.round(value)}%`;
}

/** Colour class for a relevance score. */
export function scoreTone(score: number): "ok" | "gov" | "warn" | "crit" {
  if (score >= 70) return "ok";
  if (score >= 45) return "gov";
  if (score >= 25) return "warn";
  return "crit";
}

export const TYPE_TONE: Record<string, "primary" | "testing" | "safety" | "reference" | "installation" | "terminology" | "related"> = {
  Primary: "primary",
  Testing: "testing",
  Safety: "safety",
  Reference: "reference",
  Installation: "installation",
  Terminology: "terminology",
  Related: "related",
};

export const SEVERITY_TONE: Record<string, "ok" | "gov" | "warn" | "crit"> = {
  Critical: "crit",
  High: "warn",
  Medium: "gov",
  Low: "ok",
};

/** Truncate text to a maximum length with an ellipsis. */
export function truncate(text: string, limit = 140): string {
  const value = (text ?? "").trim();
  return value.length <= limit ? value : `${value.slice(0, limit - 1).trimEnd()}…`;
}
