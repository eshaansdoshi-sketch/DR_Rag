"use client";

import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ReferenceLine,
    ResponsiveContainer,
    Dot,
} from "recharts";
import type { ResearchTraceEntry } from "@/lib/types";

export function TimelineTab({ trace }: { trace: ResearchTraceEntry[] }) {
    const data = trace.map((t) => ({
        iteration: t.iteration,
        confidence: +(t.global_confidence * 100).toFixed(1),
        threshold: +(t.applied_confidence_threshold * 100).toFixed(1),
        sources: t.new_sources_added,
    }));

    const threshold = trace[0]?.applied_confidence_threshold
        ? trace[0].applied_confidence_threshold * 100
        : 75;

    if (data.length === 0) {
        return (
            <div className="text-sm text-muted-foreground text-center py-12">
                No iteration data available.
            </div>
        );
    }

    return (
        <div className="space-y-6 max-w-4xl">
            <div>
                <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1">
                    Confidence Over Iterations
                </h3>
                <p className="text-xs text-muted-foreground mb-4">
                    Global confidence trajectory with threshold reference line
                </p>
            </div>

            <div className="rounded-lg border border-border bg-card p-6">
                <ResponsiveContainer width="100%" height={320}>
                    <LineChart data={data} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                        <XAxis
                            dataKey="iteration"
                            tickLine={false}
                            axisLine={false}
                            tick={{ fill: "var(--muted-foreground)", fontSize: 12 }}
                            label={{ value: "Iteration", position: "bottom", offset: -5, fill: "var(--muted-foreground)", fontSize: 11 }}
                        />
                        <YAxis
                            domain={[0, 100]}
                            tickLine={false}
                            axisLine={false}
                            tick={{ fill: "var(--muted-foreground)", fontSize: 12 }}
                            label={{ value: "Confidence %", angle: -90, position: "insideLeft", offset: 15, fill: "var(--muted-foreground)", fontSize: 11 }}
                        />
                        <Tooltip
                            contentStyle={{
                                background: "var(--card)",
                                border: "1px solid var(--border)",
                                borderRadius: "8px",
                                fontSize: "12px",
                            }}
                            labelFormatter={(l) => `Iteration ${l}`}
                        />
                        <ReferenceLine
                            y={threshold}
                            stroke="var(--success)"
                            strokeDasharray="6 3"
                            label={{
                                value: `Threshold ${threshold.toFixed(0)}%`,
                                position: "right",
                                fill: "var(--success)",
                                fontSize: 11,
                            }}
                        />
                        <Line
                            type="monotone"
                            dataKey="confidence"
                            stroke="var(--primary)"
                            strokeWidth={2}
                            dot={(props: Record<string, unknown>) => {
                                const { cx, cy, index } = props as { cx: number; cy: number; index: number };
                                const isLast = index === data.length - 1;
                                return (
                                    <Dot
                                        cx={cx}
                                        cy={cy}
                                        r={isLast ? 6 : 4}
                                        fill={isLast ? "var(--chart-1)" : "var(--primary)"}
                                        stroke={isLast ? "var(--chart-1)" : "var(--primary)"}
                                    />
                                );
                            }}
                            name="Confidence"
                        />
                    </LineChart>
                </ResponsiveContainer>
            </div>

            {/* Per-iteration stats table */}
            <div className="rounded-lg border border-border overflow-hidden">
                <table className="w-full text-sm">
                    <thead className="bg-muted">
                        <tr>
                            <th className="text-left px-4 py-2.5 text-xs font-medium text-muted-foreground uppercase">Iter</th>
                            <th className="text-left px-4 py-2.5 text-xs font-medium text-muted-foreground uppercase">Confidence</th>
                            <th className="text-left px-4 py-2.5 text-xs font-medium text-muted-foreground uppercase">Sources Added</th>
                            <th className="text-left px-4 py-2.5 text-xs font-medium text-muted-foreground uppercase">Weak Subtopics</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                        {trace.map((t) => (
                            <tr key={t.iteration} className="hover:bg-accent/50 transition-colors">
                                <td className="px-4 py-2.5 font-mono text-xs">{t.iteration}</td>
                                <td className="px-4 py-2.5 font-mono text-xs">
                                    {(t.global_confidence * 100).toFixed(1)}%
                                </td>
                                <td className="px-4 py-2.5 font-mono text-xs">{t.new_sources_added}</td>
                                <td className="px-4 py-2.5 text-xs">
                                    {t.weak_subtopics.length > 0 ? (
                                        <span className="text-warning">{t.weak_subtopics.join(", ")}</span>
                                    ) : (
                                        <span className="text-muted-foreground">—</span>
                                    )}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
