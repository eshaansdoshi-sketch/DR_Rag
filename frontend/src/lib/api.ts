import type {
    ResearchRequest,
    ResearchResponse,
    RunSummary,
    RunDetail,
} from "./types";

const API_BASE = (
    process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:10000"
).replace(/\/+$/, "");

// ─── Generic fetch wrapper ────────────────────────────────────────────────

async function apiFetch<T>(
    path: string,
    options?: RequestInit
): Promise<T> {
    const res = await fetch(`${API_BASE}${path}`, {
        headers: { "Content-Type": "application/json" },
        ...options,
    });

    if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        const detail =
            (body as Record<string, string>).detail ?? res.statusText;
        throw new ApiError(res.status, detail);
    }

    return res.json() as Promise<T>;
}

// ─── Typed error ──────────────────────────────────────────────────────────

export class ApiError extends Error {
    constructor(
        public status: number,
        public detail: string
    ) {
        super(detail);
        this.name = "ApiError";
    }
}

// ─── Endpoints ────────────────────────────────────────────────────────────

export async function runResearch(
    req: ResearchRequest
): Promise<ResearchResponse> {
    return apiFetch<ResearchResponse>("/research", {
        method: "POST",
        body: JSON.stringify(req),
    });
}

export async function listRuns(): Promise<RunSummary[]> {
    return apiFetch<RunSummary[]>("/research");
}

export async function getRunDetail(runId: number): Promise<RunDetail> {
    return apiFetch<RunDetail>(`/research/${runId}`);
}

export async function healthCheck(): Promise<{
    status: string;
    database: string;
}> {
    return apiFetch("/health");
}
