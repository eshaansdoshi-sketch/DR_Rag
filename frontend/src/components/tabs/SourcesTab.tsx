"use client";

import { useMemo } from "react";
import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    PieChart,
    Pie,
    Cell,
    Legend,
} from "recharts";
import type { FinalReport } from "@/lib/types";

const DOMAIN_COLORS = [
    "var(--chart-1)",
    "var(--chart-2)",
    "var(--chart-3)",
    "var(--chart-4)",
    "var(--chart-5)",
];

export function SourcesTab({ report }: { report: FinalReport }) {
    const sources = report.references;

    const domainData = useMemo(() => {
        const counts: Record<string, number> = {};
        for (const url of sources) {
            const domain = classifyDomain(url);
            counts[domain] = (counts[domain] || 0) + 1;
        }
        return Object.entries(counts)
            .map(([name, value]) => ({ name, value }))
            .sort((a, b) => b.value - a.value);
    }, [sources]);

    if (sources.length === 0) {
        return (
            <div className="text-sm text-muted-foreground text-center py-12">
                No source data available.
            </div>
        );
    }

    return (
        <div className="space-y-6 max-w-4xl">
            <div>
                <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1">
                    Source Analytics
                </h3>
                <p className="text-xs text-muted-foreground mb-4">
                    Distribution of {sources.length} referenced sources by domain type
                </p>
            </div>

            <div className="grid grid-cols-2 gap-6">
                {/* Bar chart */}
                <div className="rounded-lg border border-border bg-card p-5">
                    <h4 className="text-xs font-medium text-muted-foreground uppercase mb-4">
                        Domain Distribution
                    </h4>
                    <ResponsiveContainer width="100%" height={220}>
                        <BarChart data={domainData}>
                            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                            <XAxis
                                dataKey="name"
                                tickLine={false}
                                axisLine={false}
                                tick={{ fill: "var(--muted-foreground)", fontSize: 11 }}
                            />
                            <YAxis
                                tickLine={false}
                                axisLine={false}
                                tick={{ fill: "var(--muted-foreground)", fontSize: 11 }}
                                allowDecimals={false}
                            />
                            <Tooltip
                                contentStyle={{
                                    background: "var(--card)",
                                    border: "1px solid var(--border)",
                                    borderRadius: "8px",
                                    fontSize: "12px",
                                }}
                            />
                            <Bar dataKey="value" radius={[4, 4, 0, 0]} barSize={30}>
                                {domainData.map((_, i) => (
                                    <Cell
                                        key={i}
                                        fill={DOMAIN_COLORS[i % DOMAIN_COLORS.length]}
                                    />
                                ))}
                            </Bar>
                        </BarChart>
                    </ResponsiveContainer>
                </div>

                {/* Pie chart */}
                <div className="rounded-lg border border-border bg-card p-5">
                    <h4 className="text-xs font-medium text-muted-foreground uppercase mb-4">
                        Proportion
                    </h4>
                    <ResponsiveContainer width="100%" height={220}>
                        <PieChart>
                            <Pie
                                data={domainData}
                                cx="50%"
                                cy="50%"
                                outerRadius={80}
                                dataKey="value"
                                nameKey="name"
                                label={({ name, percent }: { name?: string; percent?: number }) =>
                                    `${name ?? ""} ${((percent ?? 0) * 100).toFixed(0)}%`
                                }
                                labelLine={false}
                            >
                                {domainData.map((_, i) => (
                                    <Cell
                                        key={i}
                                        fill={DOMAIN_COLORS[i % DOMAIN_COLORS.length]}
                                    />
                                ))}
                            </Pie>
                            <Legend
                                wrapperStyle={{ fontSize: "11px" }}
                            />
                        </PieChart>
                    </ResponsiveContainer>
                </div>
            </div>

            {/* Source list */}
            <div className="rounded-lg border border-border overflow-hidden">
                <table className="w-full text-sm">
                    <thead className="bg-muted">
                        <tr>
                            <th className="text-left px-4 py-2.5 text-xs font-medium text-muted-foreground uppercase w-12">
                                #
                            </th>
                            <th className="text-left px-4 py-2.5 text-xs font-medium text-muted-foreground uppercase">
                                URL
                            </th>
                            <th className="text-left px-4 py-2.5 text-xs font-medium text-muted-foreground uppercase w-24">
                                Type
                            </th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                        {sources.map((url, i) => (
                            <tr key={i} className="hover:bg-accent/50 transition-colors">
                                <td className="px-4 py-2 font-mono text-xs text-muted-foreground">
                                    {i + 1}
                                </td>
                                <td className="px-4 py-2 text-xs font-mono truncate max-w-xs">
                                    <a
                                        href={url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="text-foreground hover:underline"
                                    >
                                        {url}
                                    </a>
                                </td>
                                <td className="px-4 py-2 text-xs text-muted-foreground">
                                    {classifyDomain(url)}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

function classifyDomain(url: string): string {
    try {
        const hostname = new URL(url).hostname.toLowerCase();
        if (hostname.endsWith(".edu")) return ".edu";
        if (hostname.endsWith(".gov")) return ".gov";
        if (hostname.endsWith(".org")) return ".org";
        if (
            hostname.includes("news") ||
            hostname.includes("reuters") ||
            hostname.includes("bbc") ||
            hostname.includes("cnn") ||
            hostname.includes("nyt")
        )
            return "news";
        if (
            hostname.includes("blog") ||
            hostname.includes("medium") ||
            hostname.includes("substack")
        )
            return "blog";
        if (hostname.includes("wikipedia")) return "wiki";
        if (hostname.includes("arxiv") || hostname.includes("scholar"))
            return "academic";
        return "other";
    } catch {
        return "other";
    }
}
