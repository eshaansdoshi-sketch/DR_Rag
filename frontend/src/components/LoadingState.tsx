"use client";

export function LoadingState() {
    return (
        <div className="flex flex-col items-center justify-center h-full min-h-[400px] gap-6">
            <div className="relative">
                <div className="w-16 h-16 rounded-full border-4 border-muted" />
                <div className="absolute top-0 left-0 w-16 h-16 rounded-full border-4 border-transparent border-t-primary animate-spin" />
            </div>
            <div className="text-center space-y-2">
                <p className="text-sm font-medium text-foreground">
                    Research in progress
                </p>
                <p className="text-xs text-muted-foreground">
                    Executing iterations, gathering sources, and analyzing subtopics...
                </p>
            </div>

            {/* Skeleton cards */}
            <div className="w-full max-w-2xl space-y-3 px-8">
                {[1, 2, 3].map((i) => (
                    <div
                        key={i}
                        className="rounded-lg border border-border p-4 space-y-2 animate-pulse"
                    >
                        <div className="h-3 bg-muted rounded w-1/3" />
                        <div className="h-2 bg-muted rounded w-full" />
                        <div className="h-2 bg-muted rounded w-2/3" />
                    </div>
                ))}
            </div>
        </div>
    );
}
