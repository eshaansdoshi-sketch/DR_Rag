"use client";

import { useState } from "react";
import type { ResearchTraceEntry } from "@/lib/types";
import { cn } from "@/lib/utils";

export function TraceTab({ trace }: { trace: ResearchTraceEntry[] }) {
    const [expandedIdx, setExpandedIdx] = useState<number | null>(null);
    const [showRaw, setShowRaw] = useState(false);

    return (
        <div className="space-y-4 max-w-5xl">
            <div className="flex items-center justify-between">
                <div>
                    <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1">
                        Full Research Trace
                    </h3>
                    <p className="text-xs text-muted-foreground">
                        Detailed per-iteration diagnostics ({trace.length} entries)
                    </p>
                </div>
                <button
                    onClick={() => setShowRaw(!showRaw)}
                    className="text-xs font-medium text-muted-foreground hover:text-foreground transition-colors border border-border rounded-md px-3 py-1.5"
                >
                    {showRaw ? "Structured View" : "Raw JSON"}
                </button>
            </div>

            {showRaw ? (
                <div className="rounded-lg border border-border bg-card p-4 overflow-x-auto">
                    <pre className="text-xs font-mono text-card-foreground whitespace-pre-wrap">
                        {JSON.stringify(trace, null, 2)}
                    </pre>
                </div>
            ) : (
                <div className="space-y-2">
                    {trace.map((entry, i) => (
                        <div key={i} className="rounded-lg border border-border bg-card overflow-hidden">
                            <button
                                onClick={() => setExpandedIdx(expandedIdx === i ? null : i)}
                                className="w-full flex items-center justify-between px-5 py-3 text-left hover:bg-accent/50 transition-colors"
                            >
                                <div className="flex items-center gap-4">
                                    <span className="text-sm font-semibold font-mono text-foreground">
                                        Iteration {entry.iteration}
                                    </span>
                                    <span className="text-xs text-muted-foreground">
                                        Confidence: {(entry.global_confidence * 100).toFixed(1)}%
                                    </span>
                                    <span className="text-xs text-muted-foreground">
                                        Sources: +{entry.new_sources_added}
                                    </span>
                                    <span className="text-xs font-mono text-muted-foreground">
                                        {entry.iteration_tokens.toLocaleString()} tok
                                    </span>
                                </div>
                                <svg
                                    className={cn(
                                        "w-4 h-4 text-muted-foreground transition-transform",
                                        expandedIdx === i && "rotate-180"
                                    )}
                                    fill="none"
                                    viewBox="0 0 24 24"
                                    stroke="currentColor"
                                >
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                </svg>
                            </button>

                            {expandedIdx === i && (
                                <div className="px-5 pb-4 border-t border-border pt-3 space-y-4">
                                    {/* Subtopic confidences */}
                                    <TraceSection title="Subtopic Confidences">
                                        <div className="grid grid-cols-2 gap-x-6 gap-y-1.5">
                                            {Object.entries(entry.subtopic_confidences).map(([name, conf]) => (
                                                <div key={name} className="flex items-center justify-between">
                                                    <span className="text-xs text-card-foreground truncate mr-2">{name}</span>
                                                    <span
                                                        className={cn(
                                                            "text-xs font-mono font-medium",
                                                            conf < 0.6 ? "text-warning" : "text-foreground"
                                                        )}
                                                    >
                                                        {(conf * 100).toFixed(1)}%
                                                    </span>
                                                </div>
                                            ))}
                                        </div>
                                    </TraceSection>

                                    {/* Plan updates */}
                                    {entry.plan_updates.length > 0 && (
                                        <TraceSection title="Plan Updates">
                                            <ul className="space-y-1">
                                                {entry.plan_updates.map((u, j) => (
                                                    <li key={j} className="text-xs text-card-foreground">• {u}</li>
                                                ))}
                                            </ul>
                                        </TraceSection>
                                    )}

                                    {/* Subtopics added / removed */}
                                    {(entry.subtopics_added.length > 0 || entry.subtopics_removed.length > 0) && (
                                        <TraceSection title="Structural Changes">
                                            {entry.subtopics_added.length > 0 && (
                                                <p className="text-xs text-card-foreground">
                                                    <span className="text-success font-medium">Added:</span>{" "}
                                                    {entry.subtopics_added.join(", ")}
                                                </p>
                                            )}
                                            {entry.subtopics_removed.length > 0 && (
                                                <p className="text-xs text-card-foreground">
                                                    <span className="text-destructive font-medium">Removed:</span>{" "}
                                                    {entry.subtopics_removed.join(", ")}
                                                </p>
                                            )}
                                        </TraceSection>
                                    )}

                                    {/* Planning note */}
                                    {entry.planning_note && (
                                        <TraceSection title="Planning Note">
                                            <p className="text-xs text-card-foreground">{entry.planning_note}</p>
                                        </TraceSection>
                                    )}

                                    {/* Strictness */}
                                    <TraceSection title="Evidence Strictness">
                                        <div className="flex items-center gap-4 text-xs">
                                            <span>
                                                Mode: <span className="font-mono font-medium">{entry.evidence_strictness}</span>
                                            </span>
                                            <span>
                                                Satisfied:{" "}
                                                <span className={entry.strictness_satisfied ? "text-success" : "text-destructive"}>
                                                    {entry.strictness_satisfied ? "Yes" : "No"}
                                                </span>
                                            </span>
                                        </div>
                                        {entry.strictness_failures.length > 0 && (
                                            <ul className="mt-1 space-y-0.5">
                                                {entry.strictness_failures.map((f, j) => (
                                                    <li key={j} className="text-xs text-destructive">• {f}</li>
                                                ))}
                                            </ul>
                                        )}
                                    </TraceSection>

                                    {/* Config used */}
                                    <TraceSection title="Configuration">
                                        <div className="grid grid-cols-2 gap-x-6 gap-y-1 text-xs font-mono">
                                            <div>depth_mode: {entry.depth_mode}</div>
                                            <div>contradiction_sensitivity: {entry.contradiction_sensitivity}</div>
                                            <div>confidence_threshold: {entry.applied_confidence_threshold}</div>
                                            <div>max_iterations: {entry.configured_max_iterations}</div>
                                            <div>cumulative_tokens: {entry.run_tokens_cumulative.toLocaleString()}</div>
                                            <div>temporal_sensitive: {entry.is_temporally_sensitive ? "yes" : "no"}</div>
                                        </div>
                                    </TraceSection>
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

function TraceSection({
    title,
    children,
}: {
    title: string;
    children: React.ReactNode;
}) {
    return (
        <div>
            <h5 className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider mb-1.5">
                {title}
            </h5>
            {children}
        </div>
    );
}
