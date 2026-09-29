import * as React from "react";
import { Link } from "react-router-dom";
import { History as HistoryIcon, ScanSearch } from "lucide-react";
import { api, ApiError } from "@/services/api";
import { Card, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Skeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import { Input } from "@/components/ui/Input";
import { useDebounced } from "@/hooks/useApi";
import { truncate } from "@/utils/cn";
import type { RecentAnalysis } from "@/types";

type SortKey = "date" | "standards" | "gaps";

export default function HistoryPage() {
  const [rows, setRows] = React.useState<RecentAnalysis[] | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [query, setQuery] = React.useState("");
  const [sort, setSort] = React.useState<SortKey>("date");
  const [direction, setDirection] = React.useState<"asc" | "desc">("desc");
  const [page, setPage] = React.useState(1);
  const debouncedQuery = useDebounced(query, 300);
  const pageSize = 12;

  React.useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api
      .dashboard()
      .then((stats) => {
        if (!cancelled) setRows(stats.recent_analyses);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Could not load the analysis history.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  React.useEffect(() => setPage(1), [debouncedQuery, sort, direction]);

  const filtered = React.useMemo(() => {
    if (!rows) return [];
    const needle = debouncedQuery.trim().toLowerCase();
    const list = rows.filter(
      (row) =>
        !needle ||
        row.filename.toLowerCase().includes(needle) ||
        row.product.toLowerCase().includes(needle) ||
        row.document_id.toLowerCase().includes(needle),
    );
    return [...list].sort((a, b) => {
      const factor = direction === "asc" ? 1 : -1;
      if (sort === "standards") return (a.standards - b.standards) * factor;
      if (sort === "gaps") return (a.gaps - b.gaps) * factor;
      return a.date.localeCompare(b.date) * factor;
    });
  }, [rows, debouncedQuery, sort, direction]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
  const visible = filtered.slice((page - 1) * pageSize, page * pageSize);

  const toggleSort = (key: SortKey) => {
    if (sort === key) {
      setDirection((value) => (value === "asc" ? "desc" : "asc"));
    } else {
      setSort(key);
      setDirection("desc");
    }
  };

  const sortIndicator = (key: SortKey) => (sort === key ? (direction === "asc" ? " ▲" : " ▼") : "");

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-bold tracking-tight text-navy-900 sm:text-2xl">Recommendation History</h1>
        <p className="mt-1 max-w-3xl text-sm leading-relaxed text-ink-600">
          Every tender analysed by SISAP, with the number of standards identified and the potential
          specification gaps detected.
        </p>
      </div>

      <Card>
        <CardContent className="flex flex-wrap items-center gap-3 pt-4">
          <Input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search by document, product or ID"
            className="max-w-sm"
            aria-label="Search history"
          />
          <p className="text-xs text-ink-500">
            {filtered.length} record{filtered.length === 1 ? "" : "s"}
          </p>
        </CardContent>
      </Card>

      {error && (
        <div className="rounded border border-crit-100 bg-crit-50 px-4 py-3 text-sm text-crit-700">{error}</div>
      )}

      {loading ? (
        <div className="space-y-2">
          {Array.from({ length: 6 }).map((_, index) => (
            <Skeleton key={index} className="h-12 w-full" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <Card>
          <CardContent>
            <EmptyState
              icon={<HistoryIcon className="h-8 w-8" />}
              title={rows && rows.length ? "No records match your search" : "No analyses yet"}
              description={
                rows && rows.length
                  ? "Try a different search term."
                  : "Analyse a tender to build your recommendation history."
              }
              action={
                <Link to="/analyze">
                  <Button>
                    <ScanSearch className="h-4 w-4" aria-hidden="true" />
                    Analyze a tender
                  </Button>
                </Link>
              }
            />
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="px-0 py-0">
            <div className="overflow-x-auto">
              <table className="sisap-table">
                <thead>
                  <tr>
                    <th>Document</th>
                    <th>Product</th>
                    <th>
                      <button type="button" onClick={() => toggleSort("standards")} className="font-semibold hover:underline">
                        Standards{sortIndicator("standards")}
                      </button>
                    </th>
                    <th>
                      <button type="button" onClick={() => toggleSort("gaps")} className="font-semibold hover:underline">
                        Gaps{sortIndicator("gaps")}
                      </button>
                    </th>
                    <th>
                      <button type="button" onClick={() => toggleSort("date")} className="font-semibold hover:underline">
                        Date{sortIndicator("date")}
                      </button>
                    </th>
                    <th>Status</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {visible.map((row) => (
                    <tr key={row.document_id}>
                      <td className="max-w-[220px]">
                        <span className="block truncate font-medium text-ink-900">{row.filename}</span>
                        <span className="font-mono text-[10px] text-ink-400">{row.document_id}</span>
                      </td>
                      <td className="text-ink-700">{truncate(row.product, 40)}</td>
                      <td className="text-right font-mono tabular-nums">{row.standards}</td>
                      <td className="text-right font-mono tabular-nums">{row.gaps}</td>
                      <td className="whitespace-nowrap text-ink-600">{row.date}</td>
                      <td>
                        <Badge tone={row.status === "Standards identified" ? "ok" : "warn"}>{row.status}</Badge>
                      </td>
                      <td>
                        <Link
                          to={`/analyze/${row.document_id}/recommendations`}
                          className="text-xs font-semibold text-gov-700 hover:underline"
                        >
                          Open
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
          {totalPages > 1 && (
            <div className="flex items-center justify-between gap-3 border-t border-ink-200 px-4 py-2.5">
              <p className="text-xs text-ink-500">
                Page {page} of {totalPages}
              </p>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((v) => Math.max(1, v - 1))}>
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page >= totalPages}
                  onClick={() => setPage((v) => Math.min(totalPages, v + 1))}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
