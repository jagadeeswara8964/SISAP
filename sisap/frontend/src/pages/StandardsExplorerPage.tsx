import * as React from "react";
import { Link } from "react-router-dom";
import { LibraryBig, Search as SearchIcon } from "lucide-react";
import { api, ApiError } from "@/services/api";
import { useDebounced } from "@/hooks/useApi";
import { Card, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input, Select } from "@/components/ui/Input";
import { Skeleton } from "@/components/ui/Skeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import { truncate } from "@/utils/cn";
import type { StandardsPage, StandardSummary } from "@/types";

const PAGE_SIZE = 20;

export default function StandardsExplorerPage() {
  const [query, setQuery] = React.useState("");
  const [category, setCategory] = React.useState("");
  const [status, setStatus] = React.useState("");
  const [page, setPage] = React.useState(1);
  const [data, setData] = React.useState<StandardsPage | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const debouncedQuery = useDebounced(query, 400);

  const categories = React.useMemo(() => {
    if (!data) return [];
    return [...new Set(data.standards.map((std) => std.category))].sort();
  }, [data]);

  React.useEffect(() => {
    setPage(1);
  }, [debouncedQuery, category, status]);

  React.useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api
      .standards({ query: debouncedQuery, category, status, page, page_size: PAGE_SIZE })
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Could not load the standards catalogue.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [debouncedQuery, category, status, page]);

  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-bold tracking-tight text-navy-900 sm:text-2xl">Standards Explorer</h1>
        <p className="mt-1 max-w-3xl text-sm leading-relaxed text-ink-600">
          Search the curated standards database by standard number, title, product or keyword. Open a
          standard to inspect its scope, relationships, version history and related standards.
        </p>
      </div>

      <Card>
        <CardContent className="pt-4">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <div className="relative">
              <SearchIcon className="pointer-events-none absolute top-2.5 left-2.5 h-3.5 w-3.5 text-ink-400" aria-hidden="true" />
              <Input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Standard number, title, product or keyword"
                className="pl-8"
                aria-label="Search standards"
              />
            </div>
            <Select value={category} onChange={(event) => setCategory(event.target.value)} aria-label="Filter by category">
              <option value="">All categories</option>
              {categories.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </Select>
            <Select value={status} onChange={(event) => setStatus(event.target.value)} aria-label="Filter by status">
              <option value="">Any status</option>
              <option value="Active">Active</option>
              <option value="Superseded">Superseded</option>
            </Select>
            <Button
              variant="outline"
              onClick={() => {
                setQuery("");
                setCategory("");
                setStatus("");
              }}
            >
              Reset filters
            </Button>
          </div>
          <p className="mt-3 text-xs text-ink-500">
            {data ? (
              <>
                <span className="font-semibold text-ink-800">{data.total}</span> standard
                {data.total === 1 ? "" : "s"} in the curated dataset
              </>
            ) : (
              "Loading catalogue..."
            )}
          </p>
        </CardContent>
      </Card>

      {error && (
        <div className="rounded border border-crit-100 bg-crit-50 px-4 py-3 text-sm text-crit-700">{error}</div>
      )}

      {loading ? (
        <div className="space-y-2">
          {Array.from({ length: 8 }).map((_, index) => (
            <Skeleton key={index} className="h-16 w-full" />
          ))}
        </div>
      ) : !data || data.standards.length === 0 ? (
        <Card>
          <CardContent>
            <EmptyState
              icon={<LibraryBig className="h-8 w-8" />}
              title="No standards match your search"
              description="Try a different keyword, clear the filters, or search by standard number such as IS 8623."
            />
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {data.standards.map((std) => (
              <StandardCard key={std.id} standard={std} />
            ))}
          </div>

          {/* Pagination */}
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-xs text-ink-500">
              Page {data.page} of {totalPages}
            </p>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={data.page <= 1}
                onClick={() => setPage((value) => Math.max(1, value - 1))}
              >
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={data.page >= totalPages}
                onClick={() => setPage((value) => Math.min(totalPages, value + 1))}
              >
                Next
              </Button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function StandardCard({ standard }: { standard: StandardSummary }) {
  return (
    <Card className="transition-shadow hover:shadow-md">
      <CardContent className="flex h-full flex-col pt-4">
        <div className="flex items-start justify-between gap-2">
          <p className="font-mono text-sm font-semibold text-navy-900">{standard.standard_number}</p>
          <Badge tone={standard.status === "Active" ? "ok" : "crit"}>{standard.status}</Badge>
        </div>
        <p className="mt-1.5 flex-1 text-xs leading-relaxed text-ink-600">{truncate(standard.title, 130)}</p>
        <div className="mt-3 flex flex-wrap items-center gap-1.5">
          <Badge tone="gov">{standard.category}</Badge>
          {standard.standard_types.slice(0, 2).map((type) => (
            <Badge key={type} tone="neutral">
              {type}
            </Badge>
          ))}
          {standard.version && <Badge tone="neutral">v{standard.version}</Badge>}
        </div>
        <Link to={`/standards/${encodeURIComponent(standard.id)}`} className="mt-3">
          <Button variant="outline" size="sm" className="w-full">
            View details
          </Button>
        </Link>
      </CardContent>
    </Card>
  );
}
