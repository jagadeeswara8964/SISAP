import * as React from "react";
import { Network } from "lucide-react";
import { Badge } from "./ui/Badge";
import { Button } from "./ui/Button";
import { EmptyState } from "./ui/EmptyState";
import { Skeleton } from "./ui/Skeleton";
import type { GraphNode } from "@/types";

const RELATIONSHIP_LABELS: Record<string, string> = {
  references: "references",
  referenced_by: "referenced by",
  related: "related",
  testing: "testing",
  safety: "safety",
  installation: "installation",
  terminology: "terminology",
  supersedes: "supersedes",
  superseded_by: "superseded by",
};

const TYPE_STYLES: Record<string, string> = {
  Primary: "border-gov-600 bg-gov-50",
  Testing: "border-[#2E6F9E] bg-[#2E6F9E]/8",
  Safety: "border-[#8A2E2E] bg-[#8A2E2E]/8",
  Reference: "border-ink-500 bg-ink-100",
  Installation: "border-[#4A6B2A] bg-[#4A6B2A]/8",
  Terminology: "border-[#5C4B8A] bg-[#5C4B8A]/8",
  Related: "border-[#7A6A55] bg-[#7A6A55]/8",
};

const TYPE_TEXT: Record<string, string> = {
  Primary: "text-gov-700",
  Testing: "text-[#2E6F9E]",
  Safety: "text-[#8A2E2E]",
  Reference: "text-ink-600",
  Installation: "text-[#4A6B2A]",
  Terminology: "text-[#5C4B8A]",
  Related: "text-[#7A6A55]",
};

export interface StandardsGraphProps {
  nodes: GraphNode[];
  edges: { source: string; target: string; relationship: string }[];
  rootId?: string;
  loading?: boolean;
  onSelect?: (node: GraphNode) => void;
}

/**
 * Relationship graph rendered as a radial layout around the primary standard.
 * Nodes are keyboard focusable and selecting one opens its details.
 */
export function StandardsGraph({ nodes, edges, rootId, loading = false, onSelect }: StandardsGraphProps) {
  const [selectedId, setSelectedId] = React.useState<string | null>(null);

  React.useEffect(() => {
    setSelectedId(rootId ?? nodes.find((node) => node.is_root)?.id ?? nodes[0]?.id ?? null);
  }, [rootId, nodes]);

  if (loading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-40 w-full" />
        <div className="grid gap-2 sm:grid-cols-3">
          {Array.from({ length: 6 }).map((_, index) => (
            <Skeleton key={index} className="h-16 w-full" />
          ))}
        </div>
      </div>
    );
  }

  if (nodes.length === 0) {
    return (
      <EmptyState
        icon={<Network className="h-8 w-8" />}
        title="No relationship graph available"
        description="Recommend standards for a tender to build the standards relationship graph."
      />
    );
  }

  const root = nodes.find((node) => node.id === (rootId ?? nodes[0]?.id)) ?? nodes[0];
  const children = nodes.filter((node) => node.id !== root.id);
  const selected = nodes.find((node) => node.id === selectedId) ?? root;

  const relationshipFor = (childId: string) =>
    edges.find((edge) => edge.target === childId && edge.source === root.id)?.relationship ?? "related";

  return (
    <div className="space-y-4">
      {/* Radial layout */}
      <div className="relative overflow-x-auto rounded border border-ink-200 bg-ink-50/60 p-4">
        <div className="mx-auto flex min-w-[320px] max-w-3xl flex-col items-center">
          <GraphNodeButton node={root} isRoot selected={selected.id === root.id} onSelect={setSelectedId} />

          {children.length > 0 && (
            <>
              <div aria-hidden="true" className="h-6 w-px bg-ink-300" />
              <div aria-hidden="true" className="h-px w-full max-w-2xl bg-ink-300" />
              <div className="mt-0 grid w-full grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
                {children.map((child) => (
                  <div key={child.id} className="flex flex-col items-center">
                    <div aria-hidden="true" className="h-4 w-px bg-ink-300" />
                    <span className="mb-1 rounded bg-white px-1.5 py-0.5 text-[9px] font-semibold tracking-wide text-ink-500 uppercase ring-1 ring-ink-200">
                      {RELATIONSHIP_LABELS[relationshipFor(child.id)] ?? relationshipFor(child.id)}
                    </span>
                    <GraphNodeButton
                      node={child}
                      selected={selected.id === child.id}
                      onSelect={setSelectedId}
                    />
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-1.5">
        {Object.keys(TYPE_STYLES).map((type) => (
          <span
            key={type}
            className={`inline-flex items-center rounded border px-2 py-0.5 text-[10px] font-semibold ${TYPE_STYLES[type]} ${TYPE_TEXT[type]}`}
          >
            {type}
          </span>
        ))}
      </div>

      {/* Selected node detail */}
      <div className="rounded border border-ink-200 bg-white p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="font-mono text-sm font-semibold text-navy-900">{selected.label}</p>
            <p className="mt-1 max-w-2xl text-xs leading-relaxed text-ink-600">{selected.title}</p>
          </div>
          <div className="flex flex-wrap items-center gap-1.5">
            <Badge tone={selected.is_root ? "primary" : "neutral"}>
              {selected.is_root ? "Root standard" : selected.node_type}
            </Badge>
            <Badge tone="neutral">v{selected.version || "n/a"}</Badge>
            <Badge tone={selected.status === "Active" ? "ok" : "crit"}>{selected.status || "Unknown"}</Badge>
            {selected.score !== null && <Badge tone="gov">Score {Math.round(selected.score)}</Badge>}
          </div>
        </div>

        <dl className="mt-3 grid gap-x-6 gap-y-2 text-xs sm:grid-cols-2">
          <div>
            <dt className="font-semibold tracking-wide text-ink-500 uppercase">Relationship</dt>
            <dd className="mt-0.5 text-ink-800">
              {selected.is_root
                ? "Primary standard for this analysis"
                : RELATIONSHIP_LABELS[relationshipFor(selected.id)] ?? "related"}
            </dd>
          </div>
          <div>
            <dt className="font-semibold tracking-wide text-ink-500 uppercase">Standard ID</dt>
            <dd className="mt-0.5 font-mono text-ink-800">{selected.id}</dd>
          </div>
        </dl>

        {onSelect && (
          <div className="mt-3 border-t border-ink-100 pt-3">
            <Button size="sm" variant="outline" onClick={() => onSelect(selected)}>
              Open full standard details
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}

function GraphNodeButton({
  node,
  isRoot = false,
  selected,
  onSelect,
}: {
  node: GraphNode;
  isRoot?: boolean;
  selected: boolean;
  onSelect: (id: string) => void;
}) {
  const style = TYPE_STYLES[node.node_type] ?? TYPE_STYLES.Related;
  const text = TYPE_TEXT[node.node_type] ?? TYPE_TEXT.Related;

  return (
    <button
      type="button"
      onClick={() => onSelect(node.id)}
      aria-pressed={selected}
      className={`w-full rounded border px-2.5 py-2 text-left transition-shadow ${style} ${
        isRoot ? "ring-2 ring-gov-600 ring-offset-1" : ""
      } ${selected ? "shadow-md" : "hover:shadow-sm"}`}
    >
      <span className={`block truncate font-mono text-[11px] font-bold ${text}`}>{node.label}</span>
      <span className="mt-0.5 block truncate text-[10px] text-ink-500">{node.node_type}</span>
      {node.score !== null && (
        <span className="mt-1 block font-mono text-[10px] text-ink-600">{Math.round(node.score)}</span>
      )}
    </button>
  );
}
