import { Badge, type BadgeTone } from "./ui/Badge";
import type { RecommendationType } from "@/types";

const TONE: Record<RecommendationType, BadgeTone> = {
  Primary: "primary",
  Testing: "testing",
  Safety: "safety",
  Reference: "reference",
  Installation: "installation",
  Terminology: "terminology",
  Related: "related",
};

export function TypeBadge({ type }: { type: RecommendationType | string }) {
  const tone = TONE[type as RecommendationType] ?? "neutral";
  return <Badge tone={tone}>{type}</Badge>;
}
