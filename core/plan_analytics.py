"""Plan Analytics — Deterministic utilities for structural plan analysis.

All functions are pure, side-effect-free, and derive their output
entirely from the serialized report data (report_json). No LLM calls,
no randomness, no orchestrator modifications.
"""

from typing import Any, Dict, List, Set


# ---------------------------------------------------------------------------
# 1. Structural Plan Summary
# ---------------------------------------------------------------------------
def derive_plan_summary(report_data: Dict[str, Any]) -> Dict[str, Any]:
    """Derive a structural plan snapshot from the report trace.

    Extracts initial/final subtopics, addition/removal totals,
    peak concurrency, and a structural complexity score — all
    deterministically from the trace entries.
    """
    trace: List[Dict[str, Any]] = report_data.get("research_trace", [])

    if not trace:
        return _empty_plan_summary()

    # Iteration 1 subtopics — the seed set from the planner
    initial_subtopics: List[str] = sorted(trace[0].get("subtopic_confidences", {}).keys())

    # Accumulate additions and removals across all iterations
    all_added: List[str] = []
    all_removed: List[str] = []

    for entry in trace:
        all_added.extend(entry.get("subtopics_added", []))
        all_removed.extend(entry.get("subtopics_removed", []))

    # All unique subtopics ever encountered
    unique_subtopics: Set[str] = set(initial_subtopics)
    for entry in trace:
        unique_subtopics.update(entry.get("subtopic_confidences", {}).keys())
        unique_subtopics.update(entry.get("subtopics_added", []))

    # Final active = all encountered minus removed
    removed_set: Set[str] = set(all_removed)
    final_active: List[str] = sorted(s for s in unique_subtopics if s not in removed_set)

    # Peak active subtopics across iterations
    max_concurrent = _compute_max_concurrent(initial_subtopics, trace)

    # Structural complexity: ratio of unique to initial, capped at 1.0 minimum
    initial_count = max(len(initial_subtopics), 1)
    structural_complexity = round(len(unique_subtopics) / initial_count, 4)

    return {
        "initial_subtopics": initial_subtopics,
        "final_active_subtopics": final_active,
        "total_subtopics_added": len(all_added),
        "total_subtopics_removed": len(all_removed),
        "total_unique_subtopics": len(unique_subtopics),
        "max_concurrent_active": max_concurrent,
        "planning_iterations": len(trace),
        "structural_complexity_score": structural_complexity,
    }


# ---------------------------------------------------------------------------
# 2. Structural Health Metrics
# ---------------------------------------------------------------------------
def compute_health_metrics(report_data: Dict[str, Any]) -> Dict[str, Any]:
    """Compute structural health metrics from the trace.

    Returns expansion ratio, prune ratio, convergence rate,
    and structural volatility — all deterministic.
    """
    trace: List[Dict[str, Any]] = report_data.get("research_trace", [])

    if not trace:
        return _empty_health_metrics()

    initial_subtopics = list(trace[0].get("subtopic_confidences", {}).keys())
    initial_count = max(len(initial_subtopics), 1)

    total_added = sum(len(e.get("subtopics_added", [])) for e in trace)
    total_removed = sum(len(e.get("subtopics_removed", [])) for e in trace)
    iterations = len(trace)

    # All unique subtopics ever seen
    unique: Set[str] = set(initial_subtopics)
    for entry in trace:
        unique.update(entry.get("subtopic_confidences", {}).keys())
        unique.update(entry.get("subtopics_added", []))
    total_unique = max(len(unique), 1)

    # Expansion ratio: how much the plan grew relative to initial
    plan_expansion_ratio = round(total_added / initial_count, 4)

    # Prune ratio: fraction of all known subtopics that were pruned
    prune_ratio = round(total_removed / total_unique, 4)

    # Convergence rate: average confidence delta per iteration
    confidences = [e.get("global_confidence", 0.0) for e in trace]
    if len(confidences) >= 2:
        deltas = [confidences[i] - confidences[i - 1] for i in range(1, len(confidences))]
        convergence_rate = round(sum(deltas) / len(deltas), 4)
    else:
        convergence_rate = 0.0

    # Structural volatility: total mutations per iteration
    total_mutations = total_added + total_removed
    structural_volatility = round(total_mutations / max(iterations, 1), 4)

    return {
        "plan_expansion_ratio": plan_expansion_ratio,
        "prune_ratio": prune_ratio,
        "convergence_rate": convergence_rate,
        "structural_volatility_score": structural_volatility,
    }


# ---------------------------------------------------------------------------
# 3. Plan Reconstruction from Trace
# ---------------------------------------------------------------------------
def reconstruct_plan_from_trace(report_data: Dict[str, Any]) -> Dict[str, Any]:
    """Replay the trace iteration-by-iteration to reconstruct plan evolution.

    Returns a deterministic reconstruction showing the active subtopic
    set at each iteration, including additions, removals, and confidence.

    This enables:
    - Replay capability
    - Debug introspection
    - Structural verification
    - Research explainability
    """
    trace: List[Dict[str, Any]] = report_data.get("research_trace", [])

    if not trace:
        return {"iterations": [], "final_active": []}

    # Seed active set from first iteration
    active: Set[str] = set(trace[0].get("subtopic_confidences", {}).keys())
    iteration_snapshots: List[Dict[str, Any]] = []

    for entry in trace:
        added = entry.get("subtopics_added", [])
        removed = entry.get("subtopics_removed", [])

        # Apply structural changes
        active.update(added)
        active -= set(removed)

        snapshot: Dict[str, Any] = {
            "iteration": entry.get("iteration", 0),
            "active_subtopics": sorted(active),
            "active_count": len(active),
            "subtopics_added": added,
            "subtopics_removed": removed,
            "global_confidence": entry.get("global_confidence", 0.0),
            "planning_note": entry.get("planning_note", ""),
        }
        iteration_snapshots.append(snapshot)

    return {
        "iterations": iteration_snapshots,
        "final_active": sorted(active),
    }


# ---------------------------------------------------------------------------
# Private Helpers
# ---------------------------------------------------------------------------
def _compute_max_concurrent(
    initial: List[str], trace: List[Dict[str, Any]]
) -> int:
    """Track peak active subtopic count across all iterations."""
    active: Set[str] = set(initial)
    peak = len(active)

    for entry in trace:
        active.update(entry.get("subtopics_added", []))
        active -= set(entry.get("subtopics_removed", []))
        peak = max(peak, len(active))

    return peak


def _empty_plan_summary() -> Dict[str, Any]:
    """Return an empty plan summary when no trace is available."""
    return {
        "initial_subtopics": [],
        "final_active_subtopics": [],
        "total_subtopics_added": 0,
        "total_subtopics_removed": 0,
        "total_unique_subtopics": 0,
        "max_concurrent_active": 0,
        "planning_iterations": 0,
        "structural_complexity_score": 0.0,
    }


def _empty_health_metrics() -> Dict[str, Any]:
    """Return empty health metrics when no trace is available."""
    return {
        "plan_expansion_ratio": 0.0,
        "prune_ratio": 0.0,
        "convergence_rate": 0.0,
        "structural_volatility_score": 0.0,
    }
