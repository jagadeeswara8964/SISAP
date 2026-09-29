import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "./ui/Card";
import type { Recommendation } from "@/types";

const COLOURS: Record<string, string> = {
  Primary: "#1B4F8A",
  Testing: "#2E6F9E",
  Safety: "#8A2E2E",
  Reference: "#5B6570",
  Installation: "#4A6B2A",
  Terminology: "#5C4B8A",
  Related: "#7A6A55",
};

export interface ConfidenceChartProps {
  recommendations: Recommendation[];
}

/** Average relevance score per standard type (spec section 30). */
export function ConfidenceChart({ recommendations }: ConfidenceChartProps) {
  const buckets = new Map<string, number[]>();
  recommendations.forEach((rec) => {
    const values = buckets.get(rec.type) ?? [];
    values.push(rec.score);
    buckets.set(rec.type, values);
  });

  const data = [...buckets.entries()]
    .map(([type, values]) => ({
      type,
      score: Math.round(values.reduce((sum, value) => sum + value, 0) / values.length),
      count: values.length,
    }))
    .sort((a, b) => b.score - a.score);

  if (data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Recommendation confidence</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-ink-400">No recommendations to chart yet.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Recommendation confidence</CardTitle>
        <CardDescription>Average relevance score by standard type (0-100)</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-52 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} layout="vertical" margin={{ top: 4, right: 16, bottom: 4, left: 8 }}>
              <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 11, fill: "#5B6570" }} stroke="#C2C9D2" />
              <YAxis
                type="category"
                dataKey="type"
                width={86}
                tick={{ fontSize: 11, fill: "#333B45" }}
                stroke="#C2C9D2"
              />
              <Tooltip
                contentStyle={{
                  border: "1px solid #C9D2DB",
                  borderRadius: 4,
                  fontSize: 12,
                  boxShadow: "0 4px 12px rgba(15,42,71,0.12)",
                }}
                formatter={(value: unknown) => [
                  `${String(value)}`,
                  "Avg relevance",
                ]}
              />
              <Bar dataKey="score" radius={[0, 2, 2, 0]} maxBarSize={18}>
                {data.map((entry) => (
                  <Cell key={entry.type} fill={COLOURS[entry.type] ?? "#1B4F8A"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
