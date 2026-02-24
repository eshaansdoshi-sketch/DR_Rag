"""Evidence Strictness — Configurable rigor enforcement for research quality.

Defines enforceable constraints on evidence quality:
  - Minimum sources per insight
  - Minimum statistics per subtopic
  - Minimum domain diversity threshold

When constraints fail, signals refinement need or annotates deficiency.
All logic is deterministic, bounded, and degrades gracefully.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class StrictnessPreset:
    """Immutable evidence strictness configuration."""

    name: str
    min_sources_per_insight: int      # Each insight should have >= N supporting sources
    min_statistics_per_subtopic: int   # Each subtopic should have >= N statistics
    min_domain_types: int             # Minimum distinct domain types across sources


# ---------------------------------------------------------------------------
# Presets
# ---------------------------------------------------------------------------
RELAXED = StrictnessPreset(
    name="relaxed",
    min_sources_per_insight=1,
    min_statistics_per_subtopic=0,
    min_domain_types=1,
)

# Factoid queries (event winners, entity lookups) — zero statistics required
FACTUAL = StrictnessPreset(
    name="factual",
    min_sources_per_insight=1,
    min_statistics_per_subtopic=0,
    min_domain_types=1,
)

MODERATE = StrictnessPreset(
    name="moderate",
    min_sources_per_insight=2,
    min_statistics_per_subtopic=1,
    min_domain_types=2,
)

STRICT = StrictnessPreset(
    name="strict",
    min_sources_per_insight=3,
    min_statistics_per_subtopic=2,
    min_domain_types=3,
)

STRICTNESS_PRESETS: Dict[str, StrictnessPreset] = {
    "relaxed": RELAXED,
    "factual": FACTUAL,
    "moderate": MODERATE,
    "strict": STRICT,
}

DEFAULT_STRICTNESS = "moderate"


def get_strictness_preset(mode: str) -> StrictnessPreset:
    """Return strictness preset for the given mode. Falls back to MODERATE."""
    return STRICTNESS_PRESETS.get(mode, MODERATE)


# ---------------------------------------------------------------------------
# Enforcement — check constraints, return structured failures
# ---------------------------------------------------------------------------
@dataclass
class StrictnessResult:
    """Result of strictness enforcement check."""

    satisfied: bool
    failures: List[str]           # Human-readable failure descriptions
    details: Dict[str, Any]       # Machine-readable constraint details

    def to_trace_dict(self) -> Dict[str, Any]:
        return {
            "satisfied": self.satisfied,
            "failures": self.failures,
            "failure_count": len(self.failures),
        }


def check_strictness(
    preset: StrictnessPreset,
    insights: list,
    statistics: list,
    sources: list,
    subtopic_names: List[str],
) -> StrictnessResult:
    """Evaluate evidence against strictness constraints.

    Args:
        preset: the active strictness preset
        insights: list of Insight objects
        statistics: list of Statistic objects
        sources: list of SourceMetadata objects
        subtopic_names: list of subtopic name strings

    Returns StrictnessResult with satisfaction flag and failure details.
    """
    failures: List[str] = []
    details: Dict[str, Any] = {
        "preset": preset.name,
        "constraints": {
            "min_sources_per_insight": preset.min_sources_per_insight,
            "min_statistics_per_subtopic": preset.min_statistics_per_subtopic,
            "min_domain_types": preset.min_domain_types,
        },
    }

    # ── Check 1: Sources per insight ─────────────────────────────────
    under_sourced = []
    for insight in insights:
        src_count = len(getattr(insight, "supporting_sources", []))
        if src_count < preset.min_sources_per_insight:
            under_sourced.append(getattr(insight, "subtopic", "unknown"))

    if under_sourced:
        unique = list(set(under_sourced))
        failures.append(
            f"Insights in {len(unique)} subtopic(s) have fewer than "
            f"{preset.min_sources_per_insight} supporting source(s): {', '.join(unique[:5])}"
        )
    details["under_sourced_subtopics"] = list(set(under_sourced))

    # ── Check 2: Statistics per subtopic ─────────────────────────────
    stats_by_subtopic = {}
    for stat in statistics:
        st = getattr(stat, "subtopic", "unknown")
        stats_by_subtopic[st] = stats_by_subtopic.get(st, 0) + 1

    under_stats = [
        name for name in subtopic_names
        if stats_by_subtopic.get(name, 0) < preset.min_statistics_per_subtopic
    ]
    if under_stats:
        failures.append(
            f"{len(under_stats)} subtopic(s) have fewer than "
            f"{preset.min_statistics_per_subtopic} statistic(s): {', '.join(under_stats[:5])}"
        )
    details["under_stats_subtopics"] = under_stats

    # ── Check 3: Domain diversity ────────────────────────────────────
    domain_types = set()
    for source in sources:
        dt = getattr(source, "domain_type", None)
        if dt is not None:
            domain_types.add(str(dt))

    actual_diversity = len(domain_types)
    if actual_diversity < preset.min_domain_types:
        failures.append(
            f"Domain diversity insufficient: {actual_diversity} type(s) found, "
            f"{preset.min_domain_types} required"
        )
    details["domain_types_found"] = actual_diversity

    return StrictnessResult(
        satisfied=len(failures) == 0,
        failures=failures,
        details=details,
    )
