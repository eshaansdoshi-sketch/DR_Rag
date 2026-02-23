"use client";

import type { TerminationReason } from "@/lib/types";
import { cn } from "@/lib/utils";

const REASON_MAP: Record<
    TerminationReason,
    { label: string; icon: string; variant: "success" | "warning" | "error" }
> = {
    confidence_threshold_reached: {
        label: "Confidence Threshold Reached",
        icon: "✅",
        variant: "success",
    },
    max_iterations_reached: {
        label: "Max Iterations Reached",
        icon: "⚠",
        variant: "warning",
    },
    evidence_strictness_unsatisfied: {
        label: "Evidence Strictness Unmet",
        icon: "⚠",
        variant: "warning",
    },
    token_budget_exceeded: {
        label: "Token Budget Exceeded",
        icon: "🛑",
        variant: "error",
    },
    timeout_exceeded: {
        label: "Timeout Exceeded",
        icon: "🛑",
        variant: "error",
    },
    manual_interrupt: {
        label: "Manual Interrupt",
        icon: "⚠",
        variant: "warning",
    },
    error_abort: {
        label: "Error Abort",
        icon: "🛑",
        variant: "error",
    },
    unknown: {
        label: "Unknown",
        icon: "?",
        variant: "warning",
    },
};

const VARIANT_CLASSES = {
    success: "bg-success/10 text-success border-success/30",
    warning: "bg-warning/10 text-warning border-warning/30",
    error: "bg-destructive/10 text-destructive border-destructive/30",
};

export function TerminationBadge({
    reason,
}: {
    reason: TerminationReason;
}) {
    const info = REASON_MAP[reason] ?? REASON_MAP.unknown;
    return (
        <span
            className={cn(
                "inline-flex items-center gap-1.5 rounded-md border px-3 py-1 text-xs font-medium",
                VARIANT_CLASSES[info.variant]
            )}
        >
            <span>{info.icon}</span>
            {info.label}
        </span>
    );
}
