"use client";

import { useState } from "react";
import type { ResearchConfig } from "@/lib/types";
import { cn } from "@/lib/utils";

interface Props {
    config: ResearchConfig;
    onChange: (c: ResearchConfig) => void;
    onRun: () => void;
    isRunning: boolean;
}

const DEPTH_MODES = [
    { value: "quick_scan" as const, label: "Quick", desc: "1 iteration, fast" },
    { value: "standard" as const, label: "Standard", desc: "2 iterations" },
    { value: "deep_investigation" as const, label: "Deep", desc: "5 iterations, thorough" },
];

const STRICTNESS_OPTIONS = [
    { value: "relaxed" as const, label: "Relaxed" },
    { value: "moderate" as const, label: "Moderate" },
    { value: "strict" as const, label: "Strict" },
];

const CONTRADICTION_OPTIONS = [
    { value: "ignore_minor" as const, label: "Ignore Minor" },
    { value: "flag_all" as const, label: "Flag All" },
    { value: "escalate_on_any" as const, label: "Escalate" },
];

const REPORT_MODES = [
    { value: "executive_summary" as const, label: "Executive Summary" },
    { value: "technical_whitepaper" as const, label: "Technical Whitepaper" },
    { value: "risk_assessment" as const, label: "Risk Assessment" },
    { value: "academic_structured" as const, label: "Academic" },
];

const TRANSPARENCY_OPTIONS = [
    { value: "final_only" as const, label: "Final Only" },
    { value: "standard" as const, label: "Standard" },
    { value: "full" as const, label: "Full" },
];

export function ResearchConfigPanel({ config, onChange, onRun, isRunning }: Props) {
    const [advancedOpen, setAdvancedOpen] = useState(false);

    const set = <K extends keyof ResearchConfig>(key: K, value: ResearchConfig[K]) =>
        onChange({ ...config, [key]: value });

    return (
        <div className="flex flex-col">
            {/* Header */}
            <div className="px-6 py-5 border-b border-sidebar-border">
                <h1 className="text-lg font-semibold text-sidebar-foreground tracking-tight">
                    Deep Research Agent
                </h1>
                <p className="text-xs text-muted-foreground mt-1">
                    Configure and execute research runs
                </p>
            </div>

            {/* Scrollable config body */}
            <div className="px-4 py-4 space-y-5">
                {/* Depth Mode */}
                <div>
                    <label className="block text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">
                        Research Depth
                    </label>
                    <div className="flex gap-1.5">
                        {DEPTH_MODES.map((mode) => (
                            <button
                                key={mode.value}
                                onClick={() => set("depth_mode", mode.value)}
                                className={cn(
                                    "flex-1 rounded-md border px-2 py-1.5 text-center text-xs font-medium transition-all",
                                    config.depth_mode === mode.value
                                        ? "border-primary bg-primary text-primary-foreground"
                                        : "border-border bg-card text-card-foreground hover:bg-accent"
                                )}
                                title={mode.desc}
                            >
                                {mode.label}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Confidence Threshold */}
                <div>
                    <div className="flex items-center justify-between mb-2">
                        <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                            Confidence Threshold
                        </label>
                        <span className="text-sm font-mono font-medium text-foreground">
                            {config.confidence_threshold.toFixed(2)}
                        </span>
                    </div>
                    <input
                        type="range"
                        min={0.65}
                        max={0.90}
                        step={0.01}
                        value={config.confidence_threshold}
                        onChange={(e) => set("confidence_threshold", parseFloat(e.target.value))}
                        className="w-full accent-primary"
                    />
                    <div className="flex justify-between text-[10px] text-muted-foreground mt-1">
                        <span>0.65</span>
                        <span>0.90</span>
                    </div>
                </div>

                {/* Max Iterations */}
                <div>
                    <label className="block text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">
                        Max Iterations
                    </label>
                    <div className="flex items-center gap-1.5">
                        {[1, 2, 3, 4, 5].map((n) => (
                            <button
                                key={n}
                                onClick={() => set("max_iterations", n)}
                                className={cn(
                                    "w-8 h-8 rounded-md border text-xs font-medium transition-all",
                                    config.max_iterations === n
                                        ? "border-primary bg-primary text-primary-foreground"
                                        : "border-border bg-card text-card-foreground hover:bg-accent"
                                )}
                            >
                                {n}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Evidence Strictness */}
                <div>
                    <label className="block text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">
                        Evidence Strictness
                    </label>
                    <div className="flex gap-1.5">
                        {STRICTNESS_OPTIONS.map((opt) => (
                            <button
                                key={opt.value}
                                onClick={() => set("evidence_strictness", opt.value)}
                                className={cn(
                                    "flex-1 rounded-md border px-2 py-1.5 text-xs font-medium text-center transition-all",
                                    config.evidence_strictness === opt.value
                                        ? "border-primary bg-primary text-primary-foreground"
                                        : "border-border bg-card text-card-foreground hover:bg-accent"
                                )}
                            >
                                {opt.label}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Contradiction Sensitivity */}
                <div>
                    <label className="block text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">
                        Contradiction Sensitivity
                    </label>
                    <div className="flex gap-1.5">
                        {CONTRADICTION_OPTIONS.map((opt) => (
                            <button
                                key={opt.value}
                                onClick={() => set("contradiction_sensitivity", opt.value)}
                                className={cn(
                                    "flex-1 rounded-md border px-2 py-1.5 text-xs font-medium text-center transition-all",
                                    config.contradiction_sensitivity === opt.value
                                        ? "border-primary bg-primary text-primary-foreground"
                                        : "border-border bg-card text-card-foreground hover:bg-accent"
                                )}
                            >
                                {opt.label}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Report Mode */}
                <div>
                    <label className="block text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">
                        Report Mode
                    </label>
                    <select
                        value={config.report_mode}
                        onChange={(e) => set("report_mode", e.target.value as ResearchConfig["report_mode"])}
                        className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                    >
                        {REPORT_MODES.map((m) => (
                            <option key={m.value} value={m.value}>{m.label}</option>
                        ))}
                    </select>
                </div>

                {/* Transparency Mode */}
                <div>
                    <label className="block text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">
                        Transparency
                    </label>
                    <div className="flex gap-1.5">
                        {TRANSPARENCY_OPTIONS.map((opt) => (
                            <button
                                key={opt.value}
                                onClick={() => set("transparency_mode", opt.value)}
                                className={cn(
                                    "flex-1 rounded-md border px-2 py-1.5 text-xs font-medium text-center transition-all",
                                    config.transparency_mode === opt.value
                                        ? "border-primary bg-primary text-primary-foreground"
                                        : "border-border bg-card text-card-foreground hover:bg-accent"
                                )}
                            >
                                {opt.label}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Advanced Section */}
                <div className="border border-border rounded-lg">
                    <button
                        onClick={() => setAdvancedOpen(!advancedOpen)}
                        className="w-full flex items-center justify-between px-4 py-3 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
                    >
                        <span>Advanced Settings</span>
                        <svg
                            className={cn("w-4 h-4 transition-transform", advancedOpen && "rotate-180")}
                            fill="none" viewBox="0 0 24 24" stroke="currentColor"
                        >
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                        </svg>
                    </button>
                    {advancedOpen && (
                        <div className="px-4 pb-4 space-y-4 border-t border-border pt-3">
                            <NumberField
                                label="Max Tokens / Run"
                                value={config.max_tokens_per_run}
                                onChange={(v) => set("max_tokens_per_run", v)}
                                min={1000} max={100000} step={1000}
                            />
                            <NumberField
                                label="Max Tokens / Iteration"
                                value={config.max_tokens_per_iteration}
                                onChange={(v) => set("max_tokens_per_iteration", v)}
                                min={500} max={20000} step={500}
                            />
                            <NumberField
                                label="Concurrent Tasks"
                                value={config.max_concurrent_tasks}
                                onChange={(v) => set("max_concurrent_tasks", v)}
                                min={1} max={10} step={1}
                            />
                            <NumberField
                                label="Run Timeout (sec)"
                                value={config.max_run_timeout}
                                onChange={(v) => set("max_run_timeout", v)}
                                min={30} max={1800} step={30}
                            />
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

function NumberField({
    label, value, onChange, min, max, step,
}: {
    label: string; value: number; onChange: (v: number) => void;
    min: number; max: number; step: number;
}) {
    return (
        <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">{label}</label>
            <input
                type="number"
                value={value}
                onChange={(e) => onChange(Number(e.target.value))}
                min={min} max={max} step={step}
                className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm font-mono text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            />
        </div>
    );
}
