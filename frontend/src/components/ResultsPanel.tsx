"use client";

import { useState } from "react";
import type { FinalReport, TransparencyMode } from "@/lib/types";
import { TerminationBadge } from "./TerminationBadge";
import { LoadingState } from "./LoadingState";
import { FinalReportTab } from "./tabs/FinalReportTab";
import { TimelineTab } from "./tabs/TimelineTab";
import { SubtopicConfidenceTab } from "./tabs/SubtopicConfidenceTab";
import { ContradictionsTab } from "./tabs/ContradictionsTab";
import { SourcesTab } from "./tabs/SourcesTab";
import { TokenUsageTab } from "./tabs/TokenUsageTab";
import { TraceTab } from "./tabs/TraceTab";

interface Props {
    report: FinalReport | null;
    status: "idle" | "running" | "success" | "error";
    runMeta: { runId: number; iterations: number } | null;
    transparencyMode: TransparencyMode;
}

type TabId =
    | "report"
    | "timeline"
    | "subtopics"
    | "contradictions"
    | "sources"
    | "tokens"
    | "trace";

interface TabDef {
    id: TabId;
    label: string;
    minMode: TransparencyMode;
}

const TABS: TabDef[] = [
    { id: "report", label: "Final Report", minMode: "final_only" },
    { id: "timeline", label: "Timeline", minMode: "standard" },
    { id: "subtopics", label: "Subtopics", minMode: "standard" },
    { id: "contradictions", label: "Contradictions", minMode: "standard" },
    { id: "sources", label: "Sources", minMode: "standard" },
    { id: "tokens", label: "Token Usage", minMode: "full" },
    { id: "trace", label: "Trace", minMode: "full" },
];

const MODE_RANK: Record<TransparencyMode, number> = {
    final_only: 0,
    standard: 1,
    full: 2,
};

export function ResultsPanel({ report, status, runMeta, transparencyMode }: Props) {
    const [activeTab, setActiveTab] = useState<TabId>("report");

    const visibleTabs = TABS.filter(
        (t) => MODE_RANK[transparencyMode] >= MODE_RANK[t.minMode]
    );

    if (status === "running") {
        return <LoadingState />;
    }

    if (!report) {
        return (
            <div className="flex items-center justify-center min-h-96 text-muted-foreground">
                <div className="text-center space-y-2">
                    <svg className="w-12 h-12 mx-auto opacity-30" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <p className="text-sm">No Research Results</p>
                    <p className="text-xs opacity-60">Enter a query below and run research to see results</p>
                </div>
            </div>
        );
    }

    return (
        <div className="flex flex-col">
            {/* Header bar */}
            <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-card">
                <div className="flex items-center gap-4">
                    <TerminationBadge reason={report.termination_reason} />
                    {runMeta && (
                        <span className="text-xs text-muted-foreground">
                            Run #{runMeta.runId} · {runMeta.iterations} iteration{runMeta.iterations !== 1 ? "s" : ""}
                        </span>
                    )}
                </div>
                <div className="flex items-center gap-2">
                    <span className="text-xs text-muted-foreground">Confidence</span>
                    <span className="text-lg font-semibold font-mono tabular-nums text-foreground">
                        {(report.confidence_score * 100).toFixed(1)}%
                    </span>
                </div>
            </div>

            {/* Tab bar */}
            <div className="px-6 border-b border-border bg-card overflow-x-auto">
                <div className="flex gap-1">
                    {visibleTabs.map((tab) => (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id)}
                            className={
                                activeTab === tab.id
                                    ? "px-4 py-2.5 text-sm font-medium border-b-2 border-primary text-foreground"
                                    : "px-4 py-2.5 text-sm font-medium text-muted-foreground hover:text-foreground border-b-2 border-transparent transition-colors"
                            }
                        >
                            {tab.label}
                        </button>
                    ))}
                </div>
            </div>

            {/* Tab content */}
            <div className="p-6">
                {activeTab === "report" && <FinalReportTab report={report} />}
                {activeTab === "timeline" && <TimelineTab trace={report.research_trace} />}
                {activeTab === "subtopics" && <SubtopicConfidenceTab trace={report.research_trace} />}
                {activeTab === "contradictions" && <ContradictionsTab report={report} />}
                {activeTab === "sources" && <SourcesTab report={report} />}
                {activeTab === "tokens" && <TokenUsageTab trace={report.research_trace} />}
                {activeTab === "trace" && <TraceTab trace={report.research_trace} />}
            </div>
        </div>
    );
}
