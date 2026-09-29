import * as React from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, LibraryBig, Network } from "lucide-react";
import { api, ApiError } from "@/services/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Skeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import { StandardsGraph } from "@/components/StandardsGraph";
import type { GraphResponse, Standard } from "@/types";

const LIST_SECTIONS = [
  { key: "product_types", label: "Product types" },
  { key: "materials", label: "Materials" },
  { key: "applications", label: "Applications" },
  { key: "requirements", label: "Requirements" },
  { key: "testing", label: "Testing" },
  { key: "safety", label: "Safety" },
  { key: "installation", label: "Installation" },
  { key: "amendments", label: "Amendments" },
  { key: "related_standards", label: "Related standards" },
  { key: "referenced_standards", label: "Referenced standards" },
  { key: "superseded_by", label: "Superseded by" },
] as const;

export default function StandardDetailPage() {
  const { standardId = "" } = useParams();
  const [standard, setStandard] = React.useState<Standard | null>(null);
  const [graph, setGraph] = React.useState<GraphResponse | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    Promise.all([api.standard(standardId), api.standardGraph(standardId, 1).catch(() => null)])
      .then(([detail, graphData]) => {
        if (cancelled) return;
        setStandard(detail);
        setGraph(graphData);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Could not load this standard.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [standardId]);

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-72" />
        <Skeleton className="h-32 w-full" />
        <div className="grid gap-3 lg:grid-cols-2">
          {Array.from({ length: 4 }).map((_, index) => (
            <Skeleton key={index} className="h-40 w-full" />
          ))}
        </div>
      </div>
    );
  }

  if (error || !standard) {
    return (
      <Card>
        <CardContent>
          <EmptyState
            icon={<LibraryBig className="h-8 w-8" />}
            title="Standard not found"
            description={
              error ??
              `${standardId} is not present in the current curated dataset. Information not available in the current dataset.`
            }
            action={
              <Link to="/standards">
                <Button variant="outline">
                  <ArrowLeft className="h-4 w-4" aria-hidden="true" />
                  Back to explorer
                </Button>
              </Link>
            }
          />
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-5">
      <Link to="/standards" className="inline-flex items-center gap-1.5 text-xs font-medium text-gov-700 hover:underline">
        <ArrowLeft className="h-3.5 w-3.5" aria-hidden="true" />
        Back to standards explorer
      </Link>

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="font-mono text-xl font-bold tracking-tight text-navy-900 sm:text-2xl">
              {standard.standard_number}
            </h1>
            <Badge tone={standard.status === "Active" ? "ok" : "crit"}>{standard.status}</Badge>
            {standard.version && <Badge tone="gov">Version {standard.version}</Badge>}
            <Badge tone="neutral">{standard.category}</Badge>
          </div>
          <p className="mt-2 max-w-3xl text-sm leading-relaxed text-ink-700">{standard.title}</p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Scope</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm leading-relaxed text-ink-700">
            {standard.scope || "Not available in the current dataset."}
          </p>
        </CardContent>
      </Card>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <InfoTile label="Source" value={standard.source || "BIS"} />
        <InfoTile label="Certification" value={standard.certification || "Not available in the current dataset"} wide />
        <InfoTile label="Amendments" value={standard.amendments.length ? standard.amendments.join(", ") : "None recorded"} />
        <InfoTile label="BIS verified" value={standard.bis_verified ? "Yes" : "No - curated demo data"} />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        {LIST_SECTIONS.map((section) => {
          const values = standard[section.key] as string[] | undefined;
          if (!values || values.length === 0) return null;
          return (
            <Card key={section.key}>
              <CardHeader className="pb-2">
                <CardTitle>{section.label}</CardTitle>
              </CardHeader>
              <CardContent>
                {section.key === "related_standards" ||
                section.key === "referenced_standards" ||
                section.key === "superseded_by" ? (
                  <ul className="flex flex-wrap gap-1.5">
                    {values.map((value) => (
                      <li key={value}>
                        <Link to={`/standards/${encodeURIComponent(value)}`}>
                          <Badge tone="gov" className="cursor-pointer hover:bg-gov-700">
                            {value}
                          </Badge>
                        </Link>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <ul className="space-y-1.5">
                    {values.map((value, index) => (
                      <li key={index} className="flex gap-2 text-xs leading-relaxed text-ink-700">
                        <span aria-hidden="true" className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-gov-500" />
                        <span>{value}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Network className="h-4 w-4 text-ink-400" aria-hidden="true" />
            Relationship graph
          </CardTitle>
          <CardDescription>Standards linked to this one through the relationship graph</CardDescription>
        </CardHeader>
        <CardContent>
          <StandardsGraph
            nodes={graph?.nodes ?? []}
            edges={graph?.edges ?? []}
            rootId={standardId}
            loading={!graph && loading}
          />
        </CardContent>
      </Card>

      {standard.source_url && (
        <p className="text-[11px] text-ink-400">
          Source reference:{" "}
          <a href={standard.source_url} target="_blank" rel="noreferrer noopener" className="text-gov-700 hover:underline">
            {standard.source_url}
          </a>
        </p>
      )}

      <p className="rounded border border-warn-100 bg-warn-50 px-3 py-2 text-[11px] leading-relaxed text-warn-700">
        This standard record comes from a curated demo dataset and is not verified against the live BIS
        catalogue. Verify the edition, amendments and certification status before citing it in a tender.
      </p>
    </div>
  );
}

function InfoTile({ label, value, wide = false }: { label: string; value: string; wide?: boolean }) {
  return (
    <Card className={wide ? "sm:col-span-2" : ""}>
      <CardContent className="pt-3.5">
        <p className="text-[10px] font-semibold tracking-wide text-ink-500 uppercase">{label}</p>
        <p className="mt-1 text-xs leading-relaxed text-ink-800">{value}</p>
      </CardContent>
    </Card>
  );
}
