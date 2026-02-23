"use client";

import { useState } from "react";
import type { FinalReport } from "@/lib/types";
import { cn } from "@/lib/utils";

export function FinalReportTab({ report }: { report: FinalReport }) {
    return (
        <div className="max-w-4xl space-y-6">
            {/* Executive Summary */}
            <section className="rounded-lg border border-border bg-card p-6">
                <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-3">
                    Executive Summary
                </h3>
                <p className="text-sm text-card-foreground leading-relaxed whitespace-pre-wrap">
                    {report.executive_summary}
                </p>
            </section>

            {/* Structured Sections */}
            <section className="space-y-3">
                <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    Report Sections
                </h3>
                {report.structured_sections.map((section, i) => (
                    <CollapsibleSection
                        key={i}
                        heading={section.heading}
                        content={section.content}
                        sources={section.supporting_sources}
                        defaultOpen={i === 0}
                    />
                ))}
            </section>

            {/* Risk Assessment */}
            {report.risk_assessment.length > 0 && (
                <section className="rounded-lg border border-border bg-card p-6">
                    <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-3">
                        Risk Assessment
                    </h3>
                    <ul className="space-y-2">
                        {report.risk_assessment.map((risk, i) => (
                            <li key={i} className="flex items-start gap-2 text-sm text-card-foreground">
                                <span className="text-warning mt-0.5">⚠</span>
                                <span>{risk}</span>
                            </li>
                        ))}
                    </ul>
                </section>
            )}

            {/* Recommendations */}
            {report.recommendations.length > 0 && (
                <section className="rounded-lg border border-border bg-card p-6">
                    <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-3">
                        Recommendations
                    </h3>
                    <ul className="space-y-2">
                        {report.recommendations.map((rec, i) => (
                            <li key={i} className="flex items-start gap-2 text-sm text-card-foreground">
                                <span className="text-info mt-0.5">→</span>
                                <span>{rec}</span>
                            </li>
                        ))}
                    </ul>
                </section>
            )}

            {/* References */}
            {report.references.length > 0 && (
                <section className="rounded-lg border border-border bg-card p-6">
                    <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-3">
                        References ({report.references.length})
                    </h3>
                    <ul className="space-y-1">
                        {report.references.map((ref, i) => (
                            <li key={i} className="text-xs text-muted-foreground font-mono truncate">
                                <a
                                    href={ref}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="hover:text-foreground transition-colors"
                                >
                                    [{i + 1}] {ref}
                                </a>
                            </li>
                        ))}
                    </ul>
                </section>
            )}
        </div>
    );
}

function CollapsibleSection({
    heading,
    content,
    sources,
    defaultOpen = false,
}: {
    heading: string;
    content: string;
    sources: string[];
    defaultOpen?: boolean;
}) {
    const [open, setOpen] = useState(defaultOpen);

    return (
        <div className="rounded-lg border border-border bg-card overflow-hidden">
            <button
                onClick={() => setOpen(!open)}
                className="w-full flex items-center justify-between px-6 py-4 text-left hover:bg-accent/50 transition-colors"
            >
                <h4 className="text-sm font-semibold text-card-foreground">{heading}</h4>
                <svg
                    className={cn("w-4 h-4 text-muted-foreground transition-transform", open && "rotate-180")}
                    fill="none" viewBox="0 0 24 24" stroke="currentColor"
                >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
            </button>
            {open && (
                <div className="px-6 pb-5 border-t border-border pt-4">
                    <p className="text-sm text-card-foreground leading-relaxed whitespace-pre-wrap">
                        {content}
                    </p>
                    {sources.length > 0 && (
                        <div className="mt-3 pt-3 border-t border-border">
                            <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">
                                Sources
                            </p>
                            {sources.map((s, i) => (
                                <a
                                    key={i}
                                    href={s}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="block text-xs text-muted-foreground font-mono truncate hover:text-foreground transition-colors"
                                >
                                    {s}
                                </a>
                            ))}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
