"use client";

const ERROR_MESSAGES: Record<number, { title: string; meaning: string; action: string }> = {
    429: {
        title: "Rate Limit Exceeded",
        meaning: "The API received too many requests in a short period.",
        action: "Wait a moment and try again, or reduce concurrent tasks.",
    },
    503: {
        title: "Service Unavailable",
        meaning: "The database or a required service is not connected.",
        action: "Ensure the backend is running and database is configured.",
    },
    500: {
        title: "Internal Server Error",
        meaning: "The research pipeline encountered an unexpected failure.",
        action: "Check backend logs and try again with simpler parameters.",
    },
    408: {
        title: "Request Timeout",
        meaning: "The research run exceeded the configured timeout.",
        action: "Increase the timeout setting or reduce iterations.",
    },
    0: {
        title: "Connection Error",
        meaning: "Could not reach the research backend.",
        action: "Verify the backend is running at the configured API URL.",
    },
};

export function ErrorAlert({
    status,
    detail,
    onDismiss,
}: {
    status: number;
    detail: string;
    onDismiss: () => void;
}) {
    const info = ERROR_MESSAGES[status] ?? {
        title: `Error ${status}`,
        meaning: "An unexpected error occurred.",
        action: "Review the error details and try again.",
    };

    return (
        <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-5">
            <div className="flex items-start justify-between">
                <div className="space-y-3">
                    <div className="flex items-center gap-2">
                        <span className="text-destructive text-lg">⚠</span>
                        <h3 className="text-sm font-semibold text-destructive">{info.title}</h3>
                    </div>
                    <div className="space-y-1.5 text-sm">
                        <p className="text-muted-foreground">
                            <span className="font-medium text-foreground">Reason: </span>
                            {detail}
                        </p>
                        <p className="text-muted-foreground">
                            <span className="font-medium text-foreground">What it means: </span>
                            {info.meaning}
                        </p>
                        <p className="text-muted-foreground">
                            <span className="font-medium text-foreground">Suggested action: </span>
                            {info.action}
                        </p>
                    </div>
                </div>
                <button
                    onClick={onDismiss}
                    className="text-muted-foreground hover:text-foreground transition-colors p-1"
                >
                    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                        <path d="M18 6L6 18M6 6l12 12" />
                    </svg>
                </button>
            </div>
        </div>
    );
}
