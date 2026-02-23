"use client";

import { useState, useCallback } from "react";
import { ResearchConfigPanel } from "@/components/ResearchConfig";
import { ResultsPanel } from "@/components/ResultsPanel";
import { ErrorAlert } from "@/components/ErrorAlert";
import { runResearch, getRunDetail, ApiError } from "@/lib/api";
import type {
    ResearchConfig,
    FinalReport,
} from "@/lib/types";
import { DEFAULT_CONFIG } from "@/lib/types";

type RunStatus = "idle" | "running" | "success" | "error";

export default function HomePage() {
    const [config, setConfig] = useState<ResearchConfig>(DEFAULT_CONFIG);
    const [status, setStatus] = useState<RunStatus>("idle");
    const [report, setReport] = useState<FinalReport | null>(null);
    const [error, setError] = useState<{ status: number; detail: string } | null>(
        null
    );
    const [runMeta, setRunMeta] = useState<{
        runId: number;
        iterations: number;
    } | null>(null);

    const handleRun = useCallback(async () => {
        if (!config.query.trim()) return;

        setStatus("running");
        setError(null);
        setReport(null);

        try {
            const res = await runResearch({
                query: config.query,
                depth_mode: config.depth_mode,
                confidence_threshold: config.confidence_threshold,
                contradiction_sensitivity: config.contradiction_sensitivity,
                evidence_strictness: config.evidence_strictness,
                max_iterations: config.max_iterations,
                report_mode: config.report_mode,
                max_concurrent_tasks: config.max_concurrent_tasks,
                max_tokens_per_iteration: config.max_tokens_per_iteration,
                max_tokens_per_run: config.max_tokens_per_run,
                max_run_timeout: config.max_run_timeout,
            });

            setRunMeta({ runId: res.run_id, iterations: res.iterations });

            if (res.report_json) {
                setReport(res.report_json as FinalReport);
                setStatus("success");
            } else if (res.run_id > 0) {
                const detail = await getRunDetail(res.run_id);
                if (detail.report_json) {
                    setReport(detail.report_json);
                    setStatus("success");
                } else {
                    setError({ status: 0, detail: "Report data unavailable." });
                    setStatus("error");
                }
            } else {
                setError({ status: 0, detail: "Report data unavailable." });
                setStatus("error");
            }
        } catch (err) {
            if (err instanceof ApiError) {
                setError({ status: err.status, detail: err.detail });
            } else {
                setError({
                    status: 0,
                    detail: err instanceof Error ? err.message : "Unknown error",
                });
            }
            setStatus("error");
        }
    }, [config]);

    return (
        <div className="flex flex-col md:flex-row h-screen overflow-hidden bg-background">
            {/* Left Panel — Config (320px fixed, scrolls at panel level) */}
            <aside className="w-full md:w-[320px] md:min-w-[320px] border-b md:border-b-0 md:border-r border-border bg-sidebar overflow-y-auto">
                <ResearchConfigPanel
                    config={config}
                    onChange={setConfig}
                    onRun={handleRun}
                    isRunning={status === "running"}
                />
            </aside>

            {/* Right Panel — Results + bottom input (fluid, scrolls at panel level) */}
            <main className="flex-1 flex flex-col min-h-0">
                {/* Scrollable results region */}
                <div className="flex-1 overflow-y-auto">
                    {error && (
                        <div className="p-6">
                            <ErrorAlert
                                status={error.status}
                                detail={error.detail}
                                onDismiss={() => setError(null)}
                            />
                        </div>
                    )}
                    <ResultsPanel
                        report={report}
                        status={status}
                        runMeta={runMeta}
                        transparencyMode={config.transparency_mode}
                    />
                </div>

                {/* Bottom input bar — spans full right-panel width */}
                <div className="border-t border-border bg-background px-4 py-3">
                    <div className="relative flex items-end rounded-2xl border border-input bg-card shadow-sm focus-within:ring-2 focus-within:ring-ring focus-within:border-transparent transition-all">
                        <textarea
                            value={config.query}
                            onChange={(e) => setConfig({ ...config, query: e.target.value })}
                            onKeyDown={(e) => {
                                if (e.key === "Enter" && !e.shiftKey) {
                                    e.preventDefault();
                                    handleRun();
                                }
                            }}
                            placeholder="Enter your research question..."
                            rows={1}
                            onInput={(e) => {
                                const target = e.target as HTMLTextAreaElement;
                                target.style.height = "auto";
                                target.style.height = Math.min(target.scrollHeight, 200) + "px";
                            }}
                            className="flex-1 bg-transparent px-4 py-3 pr-14 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none resize-none max-h-[200px] leading-relaxed"
                        />
                        <button
                            onClick={handleRun}
                            disabled={status === "running" || !config.query.trim()}
                            className="absolute right-2 bottom-2 rounded-xl p-2 transition-all disabled:opacity-30 disabled:cursor-not-allowed bg-primary text-primary-foreground hover:opacity-90"
                            title="Run Research"
                        >
                            {status === "running" ? (
                                <svg className="w-5 h-5 animate-spin" viewBox="0 0 24 24" fill="none">
                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                                </svg>
                            ) : (
                                <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                    <path d="M22 2L11 13" />
                                    <path d="M22 2L15 22L11 13L2 9L22 2Z" />
                                </svg>
                            )}
                        </button>
                    </div>
                    <p className="text-[11px] text-muted-foreground text-center mt-2 opacity-60">
                        Enter to run · Shift + Enter for new line
                    </p>
                </div>
            </main>
        </div>
    );
}
