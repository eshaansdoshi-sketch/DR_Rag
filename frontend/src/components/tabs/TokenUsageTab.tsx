"use client";

import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    ReferenceLine,
    Line,
    ComposedChart,
} from "recharts";
import type { ResearchTraceEntry } from "@/lib/types";

export function TokenUsageTab({ trace }: { trace: ResearchTraceEntry[] }) {
    const data = trace.map((t) => ({
        iteration: `Iter ${t.iteration}`,
        tokens: t.iteration_tokens,
        cumulative: t.run_tokens_cumulative,
    }));

    // Try to find budget ceiling from the first trace entry
    const maxBudget = 30000; // default

    if (data.length === 0) {
        return (
            <div className="text-sm text-muted-foreground text-center py-12">
                No token usage data available.
            </div>
        );
    }

    const totalTokens = data[data.length - 1]?.cumulative ?? 0;
    const avgPerIteration = data.length > 0 ? Math.round(totalTokens / data.length) : 0;
    const budgetUsed = maxBudget > 0 ? ((totalTokens / maxBudget) * 100).toFixed(1) : "N/A";

    return (
        <div className="space-y-6 max-w-4xl">
            <div>
                <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1">
                    Token Consumption
                </h3>
                <p className="text-xs text-muted-foreground mb-4">
                    Per-iteration usage with cumulative overlay and budget ceiling
                </p>
            </div>

            {/* Summary stats */}
            <div className="grid grid-cols-3 gap-4">
                <StatCard label="Total Tokens" value={totalTokens.toLocaleString()} />
                <StatCard label="Avg / Iteration" value={avgPerIteration.toLocaleString()} />
                <StatCard label="Budget Used" value={`${budgetUsed}%`} />
            </div>

            {/* Chart */}
            <div className="rounded-lg border border-border bg-card p-6">
                <ResponsiveContainer width="100%" height={320}>
                    <ComposedChart data={data} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                        <XAxis
                            dataKey="iteration"
                            tickLine={false}
                            axisLine={false}
                            tick={{ fill: "var(--muted-foreground)", fontSize: 11 }}
                        />
                        <YAxis
                            yAxisId="left"
                            tickLine={false}
                            axisLine={false}
                            tick={{ fill: "var(--muted-foreground)", fontSize: 11 }}
                            label={{
                                value: "Tokens",
                                angle: -90,
                                position: "insideLeft",
                                offset: 15,
                                fill: "var(--muted-foreground)",
                                fontSize: 11,
                            }}
                        />
                        <YAxis
                            yAxisId="right"
                            orientation="right"
                            tickLine={false}
                            axisLine={false}
                            tick={{ fill: "var(--muted-foreground)", fontSize: 11 }}
                        />
                        <Tooltip
                            contentStyle={{
                                background: "var(--card)",
                                border: "1px solid var(--border)",
                                borderRadius: "8px",
                                fontSize: "12px",
                            }}
                        />
                        <ReferenceLine
                            yAxisId="right"
                            y={maxBudget}
                            stroke="var(--destructive)"
                            strokeDasharray="6 3"
                            label={{
                                value: `Budget: ${maxBudget.toLocaleString()}`,
                                position: "right",
                                fill: "var(--destructive)",
                                fontSize: 10,
                            }}
                        />
                        <Bar
                            yAxisId="left"
                            dataKey="tokens"
                            fill="var(--chart-2)"
                            radius={[4, 4, 0, 0]}
                            barSize={35}
                            name="Iteration Tokens"
                        />
                        <Line
                            yAxisId="right"
                            type="monotone"
                            dataKey="cumulative"
                            stroke="var(--chart-1)"
                            strokeWidth={2}
                            dot={{ r: 4, fill: "var(--chart-1)" }}
                            name="Cumulative"
                        />
                    </ComposedChart>
                </ResponsiveContainer>
            </div>

            {/* Per-iteration breakdown */}
            <div className="rounded-lg border border-border overflow-hidden">
                <table className="w-full text-sm">
                    <thead className="bg-muted">
                        <tr>
                            <th className="text-left px-4 py-2.5 text-xs font-medium text-muted-foreground uppercase">
                                Iteration
                            </th>
                            <th className="text-right px-4 py-2.5 text-xs font-medium text-muted-foreground uppercase">
                                Tokens Used
                            </th>
                            <th className="text-right px-4 py-2.5 text-xs font-medium text-muted-foreground uppercase">
                                Cumulative
                            </th>
                            <th className="text-right px-4 py-2.5 text-xs font-medium text-muted-foreground uppercase">
                                Budget %
                            </th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                        {trace.map((t) => (
                            <tr key={t.iteration} className="hover:bg-accent/50 transition-colors">
                                <td className="px-4 py-2.5 font-mono text-xs">{t.iteration}</td>
                                <td className="px-4 py-2.5 font-mono text-xs text-right">
                                    {t.iteration_tokens.toLocaleString()}
                                </td>
                                <td className="px-4 py-2.5 font-mono text-xs text-right">
                                    {t.run_tokens_cumulative.toLocaleString()}
                                </td>
                                <td className="px-4 py-2.5 font-mono text-xs text-right">
                                    {maxBudget > 0
                                        ? `${((t.run_tokens_cumulative / maxBudget) * 100).toFixed(1)}%`
                                        : "—"}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

function StatCard({ label, value }: { label: string; value: string }) {
    return (
        <div className="rounded-lg border border-border bg-card p-4">
            <p className="text-xs text-muted-foreground uppercase tracking-wider">{label}</p>
            <p className="text-xl font-semibold font-mono text-foreground mt-1">{value}</p>
        </div>
    );
}
