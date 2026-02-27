// ─── Enums ────────────────────────────────────────────────────────────────

export type DepthMode = "quick_scan" | "standard" | "deep_investigation";
export type EvidenceStrictness = "relaxed" | "moderate" | "strict";
export type ContradictionSensitivity =
    | "ignore_minor"
    | "flag_all"
    | "escalate_on_any";
export type ReportMode =
    | "executive_summary"
    | "technical_whitepaper"
    | "risk_assessment"
    | "academic_structured";
export type TransparencyMode = "final_only" | "standard" | "full";

export type TerminationReason =
    | "confidence_threshold_reached"
    | "max_iterations_reached"
    | "evidence_strictness_unsatisfied"
    | "token_budget_exceeded"
    | "timeout_exceeded"
    | "manual_interrupt"
    | "error_abort"
    | "unknown";

// ─── Request / Response ───────────────────────────────────────────────────

export interface ResearchRequest {
    query: string;
    depth_mode: DepthMode;
    confidence_threshold?: number | null;
    contradiction_sensitivity: ContradictionSensitivity;
    evidence_strictness: EvidenceStrictness;
    max_iterations?: number | null;
    report_mode: ReportMode;
    max_concurrent_tasks: number;
    max_tokens_per_iteration?: number | null;
    max_tokens_per_run?: number | null;
    max_run_timeout: number;
}

export interface ResearchResponse {
    run_id: number;
    confidence_score: number;
    iterations: number;
    report_json?: FinalReport | null;
}

// ─── Report Models ────────────────────────────────────────────────────────

export interface ReportSection {
    heading: string;
    content: string;
    supporting_sources: string[];
}

export interface Contradiction {
    subtopic: string;
    claim_a: string;
    source_a: string;
    claim_b: string;
    source_b: string;
    severity: number;
}

export interface ResearchTraceEntry {
    iteration: number;
    subtopic_confidences: Record<string, number>;
    global_confidence: number;
    weak_subtopics: string[];
    plan_updates: string[];
    new_sources_added: number;
    subtopics_added: string[];
    subtopics_removed: string[];
    planning_note: string;
    is_temporally_sensitive: boolean;
    temporal_distribution: Record<string, number>;
    depth_mode: string;
    applied_confidence_threshold: number;
    contradiction_sensitivity: string;
    evidence_strictness: string;
    strictness_satisfied: boolean;
    strictness_failures: string[];
    configured_max_iterations: number;
    iteration_tokens: number;
    run_tokens_cumulative: number;
}

export interface FinalReport {
    executive_summary: string;
    structured_sections: ReportSection[];
    risk_assessment: string[];
    recommendations: string[];
    references: string[];
    confidence_score: number;
    research_trace: ResearchTraceEntry[];
    report_mode: string;
    termination_reason: TerminationReason;
}

// ─── API List / Detail Models ─────────────────────────────────────────────

export interface RunSummary {
    id: number;
    query: string;
    confidence_score: number | null;
    iterations: number | null;
    run_mode: string | null;
    structural_complexity_score: number | null;
    created_at: string | null;
}

export interface RunDetail {
    id: number;
    query: string;
    plan_json: Record<string, unknown> | null;
    report_json: FinalReport | null;
    confidence_score: number | null;
    iterations: number | null;
    run_mode: string | null;
    total_subtopics_encountered: number | null;
    total_subtopics_added: number | null;
    total_subtopics_removed: number | null;
    max_active_subtopics: number | null;
    structural_complexity_score: number | null;
    plan_expansion_ratio: number | null;
    prune_ratio: number | null;
    convergence_rate: number | null;
    structural_volatility_score: number | null;
    created_at: string | null;
}

// ─── UI State ─────────────────────────────────────────────────────────────

export interface ResearchConfig {
    query: string;
    depth_mode: DepthMode;
    confidence_threshold: number;
    max_iterations: number;
    evidence_strictness: EvidenceStrictness;
    contradiction_sensitivity: ContradictionSensitivity;
    report_mode: ReportMode;
    transparency_mode: TransparencyMode;
    max_concurrent_tasks: number;
    max_tokens_per_run: number;
    max_tokens_per_iteration: number;
    max_run_timeout: number;
}

export const DEFAULT_CONFIG: ResearchConfig = {
    query: "",
    depth_mode: "standard",
    confidence_threshold: 0.75,
    max_iterations: 2,
    evidence_strictness: "moderate",
    contradiction_sensitivity: "flag_all",
    report_mode: "technical_whitepaper",
    transparency_mode: "standard",
    max_concurrent_tasks: 3,
    max_tokens_per_run: 30000,
    max_tokens_per_iteration: 8000,
    max_run_timeout: 300,
};
