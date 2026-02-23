"use client";

import type { FinalReport } from "@/lib/types";

export function ContradictionsTab({ report }: { report: FinalReport }) {
    // Try to extract contradictions from the report JSON
    // The FinalReport itself doesn't store contradictions directly,
    // but we can check if structured sections contain contradiction info
    // For now, look for contradiction data in the trace entries
    const contradictions = extractContradictions(report);

    if (contradictions.length === 0) {
        return (
            <div className="text-sm text-muted-foreground text-center py-12">
                <div className="space-y-2">
                    <p className="font-medium text-foreground">No Contradictions Detected</p>
                    <p>The research did not identify conflicting claims across sources.</p>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-4 max-w-5xl">
            <div>
                <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1">
                    Detected Contradictions
                </h3>
                <p className="text-xs text-muted-foreground mb-4">
                    Conflicting claims identified during research ({contradictions.length} found)
                </p>
            </div>

            <div className="rounded-lg border border-border overflow-hidden">
                <table className="w-full text-sm">
                    <thead className="bg-muted">
                        <tr>
                            <th className="text-left px-4 py-2.5 text-xs font-medium text-muted-foreground uppercase w-36">
                                Subtopic
                            </th>
                            <th className="text-left px-4 py-2.5 text-xs font-medium text-muted-foreground uppercase">
                                Claim A
                            </th>
                            <th className="text-left px-4 py-2.5 text-xs font-medium text-muted-foreground uppercase">
                                Claim B
                            </th>
                            <th className="text-center px-4 py-2.5 text-xs font-medium text-muted-foreground uppercase w-24">
                                Severity
                            </th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                        {contradictions.map((c, i) => (
                            <tr key={i} className="hover:bg-accent/50 transition-colors">
                                <td className="px-4 py-3 text-xs font-medium text-foreground align-top">
                                    {c.subtopic}
                                </td>
                                <td className="px-4 py-3 text-xs text-card-foreground align-top">
                                    {c.claim_a}
                                </td>
                                <td className="px-4 py-3 text-xs text-card-foreground align-top">
                                    {c.claim_b}
                                </td>
                                <td className="px-4 py-3 text-center align-top">
                                    <SeverityBadge severity={c.severity} />
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

function SeverityBadge({ severity }: { severity: number }) {
    let color = "bg-muted text-muted-foreground";
    if (severity >= 0.7) color = "bg-destructive/10 text-destructive";
    else if (severity >= 0.4) color = "bg-warning/10 text-warning";

    return (
        <span className={`inline-block rounded px-2 py-0.5 text-xs font-mono font-medium ${color}`}>
            {severity.toFixed(2)}
        </span>
    );
}

interface SimpleContradiction {
    subtopic: string;
    claim_a: string;
    claim_b: string;
    severity: number;
}

function extractContradictions(report: FinalReport): SimpleContradiction[] {
    // The report_json from API may have additional data
    const raw = report as unknown as Record<string, unknown>;
    if (Array.isArray(raw.contradictions)) {
        return (raw.contradictions as SimpleContradiction[]).map((c) => ({
            subtopic: c.subtopic ?? "Unknown",
            claim_a: c.claim_a ?? "",
            claim_b: c.claim_b ?? "",
            severity: typeof c.severity === "number" ? c.severity : 0.5,
        }));
    }
    return [];
}
