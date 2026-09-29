import { Badge, type BadgeTone } from "./ui/Badge";
import type { GapSeverity } from "@/types";

const TONE: Record<GapSeverity, BadgeTone> = {
  Critical: "crit",
  High: "warn",
  Medium: "gov",
  Low: "ok",
};

export function SeverityBadge({ severity }: { severity: GapSeverity | string }) {
  const tone = TONE[severity as GapSeverity] ?? "neutral";
  return <Badge tone={tone}>{severity}</Badge>;
}
