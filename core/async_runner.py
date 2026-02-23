"""Async runner for parallel subtopic execution.

Two-phase parallel execution per iteration:
  Phase 1: Search queries in parallel (semaphore-bounded)
  Phase 2: Analyze subtopics in parallel with ALL sources (semaphore-bounded)

Guarantees:
  - Deterministic ordering by original subtopic index
  - Failure isolation per task (gather with return_exceptions)
  - No shared mutable state during parallel phase
  - Bounded concurrency via asyncio.Semaphore
  - Timeout safety with partial result preservation
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

# Concurrency bounds
MIN_CONCURRENT = 1
MAX_CONCURRENT = 10
DEFAULT_TIMEOUT = 120.0


def clamp_concurrent(value: int) -> int:
    """Clamp max_concurrent_tasks to safe bounds [1, 10]."""
    return max(MIN_CONCURRENT, min(MAX_CONCURRENT, int(value)))


@dataclass
class SubtopicResult:
    """Immutable result bundle from parallel subtopic processing.

    Each async task produces one of these. No global writes inside tasks.
    """

    subtopic_name: str
    subtopic_index: int
    sources: list = field(default_factory=list)
    insights: list = field(default_factory=list)
    statistics: list = field(default_factory=list)
    contradictions: list = field(default_factory=list)
    error: Optional[str] = None
    search_latency_ms: float = 0.0
    analysis_latency_ms: float = 0.0


# ---------------------------------------------------------------------------
# Phase 1: Parallel Search
# ---------------------------------------------------------------------------
async def _search_one(
    searcher, query: str, max_results: int,
    semaphore: asyncio.Semaphore,
    task_key: str, run_id: str, iteration: int,
) -> Tuple[list, float, Optional[str]]:
    """Execute a single search query, bounded by semaphore."""
    async with semaphore:
        start = time.monotonic()
        try:
            logger.info(
                "async_task_start | run_id=%s iter=%d key=%s phase=search",
                run_id, iteration, task_key,
            )
            sources = await asyncio.to_thread(
                searcher.search_subtopic, query, max_results,
            )
            latency = (time.monotonic() - start) * 1000
            logger.info(
                "async_task_complete | run_id=%s iter=%d key=%s phase=search "
                "latency_ms=%.1f count=%d",
                run_id, iteration, task_key, latency, len(sources),
            )
            return (sources, latency, None)
        except Exception as e:
            latency = (time.monotonic() - start) * 1000
            logger.error(
                "async_task_error | run_id=%s iter=%d key=%s phase=search "
                "latency_ms=%.1f error=%s",
                run_id, iteration, task_key, latency, e,
            )
            return ([], latency, str(e))


async def _parallel_search(
    searcher, queries: List[Tuple[str, str]], max_results: int,
    semaphore: asyncio.Semaphore,
    run_id: str, iteration: int, timeout: float,
) -> List[Tuple[list, float, Optional[str]]]:
    """Search multiple queries in parallel. Returns list of (sources, latency, error)."""
    tasks = [
        _search_one(searcher, q, max_results, semaphore, key, run_id, iteration)
        for q, key in queries
    ]
    if not tasks:
        return []
    try:
        return await asyncio.wait_for(asyncio.gather(*tasks), timeout=timeout)
    except asyncio.TimeoutError:
        logger.error("search_phase_timeout | run_id=%s iter=%d", run_id, iteration)
        return [([], 0.0, "timeout")] * len(tasks)


# ---------------------------------------------------------------------------
# Phase 2: Parallel Analysis
# ---------------------------------------------------------------------------
async def _analyze_one(
    analyst, subtopic_name: str, all_sources: list,
    semaphore: asyncio.Semaphore,
    run_id: str, iteration: int,
) -> Tuple[list, list, list, float, Optional[str]]:
    """Analyze a single subtopic, bounded by semaphore."""
    async with semaphore:
        start = time.monotonic()
        try:
            logger.info(
                "async_task_start | run_id=%s iter=%d subtopic=%s phase=analysis",
                run_id, iteration, subtopic_name,
            )
            insights, statistics, contradictions = await asyncio.to_thread(
                analyst.analyze_subtopic, subtopic_name, all_sources,
            )
            latency = (time.monotonic() - start) * 1000
            logger.info(
                "async_task_complete | run_id=%s iter=%d subtopic=%s "
                "phase=analysis latency_ms=%.1f",
                run_id, iteration, subtopic_name, latency,
            )
            return (insights, statistics, contradictions, latency, None)
        except Exception as e:
            latency = (time.monotonic() - start) * 1000
            logger.error(
                "async_task_error | run_id=%s iter=%d subtopic=%s "
                "phase=analysis latency_ms=%.1f error=%s",
                run_id, iteration, subtopic_name, latency, e,
            )
            return ([], [], [], latency, str(e))


async def _parallel_analyze(
    analyst, subtopics, all_sources: list,
    semaphore: asyncio.Semaphore,
    run_id: str, iteration: int, timeout: float,
):
    """Analyze all subtopics in parallel with shared source pool."""
    tasks = [
        _analyze_one(analyst, st.name, all_sources, semaphore, run_id, iteration)
        for st in subtopics
    ]
    if not tasks:
        return []
    try:
        return await asyncio.wait_for(asyncio.gather(*tasks), timeout=timeout)
    except asyncio.TimeoutError:
        logger.error("analysis_phase_timeout | run_id=%s iter=%d", run_id, iteration)
        return [([], [], [], 0.0, "timeout")] * len(tasks)


# ---------------------------------------------------------------------------
# Combined iteration execution
# ---------------------------------------------------------------------------
async def execute_iteration(
    searcher,
    analyst,
    search_queries: List[Tuple[str, str]],
    subtopics: list,
    existing_sources: list,
    max_results: int,
    max_concurrent: int = 3,
    run_id: str = "",
    iteration: int = 1,
    timeout: float = DEFAULT_TIMEOUT,
) -> Tuple[List[SubtopicResult], list]:
    """Execute one full iteration with two-phase parallel execution.

    Phase 1: Parallel search over search_queries
    Phase 2: Parallel analysis per subtopic (each sees ALL sources)

    Returns:
        (subtopic_results, all_new_sources)
        Results are in deterministic subtopic order.
    """
    semaphore = asyncio.Semaphore(max_concurrent)

    # Phase 1: parallel search
    search_raw = await _parallel_search(
        searcher, search_queries, max_results,
        semaphore, run_id, iteration, timeout,
    )

    # Collect new sources in deterministic query order
    per_query_sources = []
    all_new_sources = []
    for sources, _lat, _err in search_raw:
        per_query_sources.append(sources)
        all_new_sources.extend(sources)

    # Phase 2: parallel analysis with full source pool
    combined_sources = list(existing_sources) + all_new_sources
    analysis_raw = await _parallel_analyze(
        analyst, subtopics, combined_sources,
        semaphore, run_id, iteration, timeout,
    )

    # Build SubtopicResult bundles in original subtopic order
    results: List[SubtopicResult] = []
    for i, st in enumerate(subtopics):
        # Search mapping: iteration-1 has 1:1 subtopic-query; refined has shared pool
        if i < len(search_raw):
            st_sources = per_query_sources[i]
            s_latency = search_raw[i][1]
            s_error = search_raw[i][2]
        else:
            st_sources = []
            s_latency = 0.0
            s_error = None

        # Analysis result
        if i < len(analysis_raw):
            insights, statistics, contradictions, a_latency, a_error = analysis_raw[i]
        else:
            insights, statistics, contradictions = [], [], []
            a_latency = 0.0
            a_error = None

        error = s_error or a_error

        results.append(SubtopicResult(
            subtopic_name=st.name,
            subtopic_index=i,
            sources=st_sources,
            insights=insights,
            statistics=statistics,
            contradictions=contradictions,
            error=error,
            search_latency_ms=s_latency,
            analysis_latency_ms=a_latency,
        ))

    return results, all_new_sources
