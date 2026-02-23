"use client";

import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Cell,
    ReferenceLine,
    ResponsiveContainer,
} from "recharts";
import type { ResearchTraceEntry } from "@/lib/types";
import { useMemo } from "react";

export function SubtopicConfidenceTab({
    trace,
}: {
    trace: ResearchTraceEntry[];
}) {
    // Use the latest iteration's subtopic confidences
    const latest = trace[trace.length - 1];

    const data = useMemo(() => {
        if (!latest) return [];
        return Object.entries(latest.subtopic_confidences)
            .map(([name, conf]) => ({
                name: name.length > 25 ? name.slice(0, 22) + "..." : name,
                fullName: name,
                confidence: +(conf * 100).toFixed(1),
            }))
            .sort((a, b) => b.confidence - a.confidence);
    }, [latest]);

    if (data.length === 0) {
        return (
            <div className="text-sm text-muted-foreground text-center py-12">
                No subtopic data available.
            </div>
        );
    }

    return (
        <div className="space-y-6 max-w-4xl">
            <div>
                <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1">
                    Subtopic Confidence Scores
                </h3>
                <p className="text-xs text-muted-foreground mb-4">
                    Final confidence per subtopic. Below 60% highlighted as weak.
                </p>
            </div>

            <div className="rounded-lg border border-border bg-card p-6">
                <ResponsiveContainer width="100%" height={Math.max(200, data.length * 45 + 60)}>
                    <BarChart
                        data={data}
                        layout="vertical"
                        margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                    >
                        <CartesianGrid
                            strokeDasharray="3 3"
                            stroke="var(--border)"
                            horizontal={false}
                        />
                        <XAxis
                            type="number"
                            domain={[0, 100]}
                            tickLine={false}
                            axisLine={false}
                            tick={{ fill: "var(--muted-foreground)", fontSize: 11 }}
                        />
                        <YAxis
                            type="category"
                            dataKey="name"
                            width={160}
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
                            // eslint-disable-next-line @typescript-eslint/no-explicit-any
                            formatter={(value: any) => [`${value}%`, "Confidence"]}
                            // eslint-disable-next-line @typescript-eslint/no-explicit-any
                            labelFormatter={(label: any) => {
                                const item = data.find((d) => d.name === label);
                                return item?.fullName ?? String(label);
                            }}
                        />
                        <ReferenceLine
                            x={60}
                            stroke="var(--warning)"
                            strokeDasharray="4 2"
                            label={{
                                value: "60% threshold",
                                position: "top",
                                fill: "var(--warning)",
                                fontSize: 10,
                            }}
                        />
                        <Bar dataKey="confidence" radius={[0, 4, 4, 0]} barSize={20}>
                            {data.map((entry, index) => (
                                <Cell
                                    key={index}
                                    fill={
                                        entry.confidence < 60
                                            ? "var(--chart-1)"
                                            : "var(--primary)"
                                    }
                                />
                            ))}
                        </Bar>
                    </BarChart>
                </ResponsiveContainer>
            </div>

            {/* Legend */}
            <div className="flex items-center gap-6 text-xs text-muted-foreground">
                <div className="flex items-center gap-1.5">
                    <span className="w-3 h-3 rounded-sm" style={{ background: "var(--primary)" }} />
                    Sufficient (≥ 60%)
                </div>
                <div className="flex items-center gap-1.5">
                    <span className="w-3 h-3 rounded-sm" style={{ background: "var(--chart-1)" }} />
                    Weak (&lt; 60%)
                </div>
            </div>
        </div>
    );
}
