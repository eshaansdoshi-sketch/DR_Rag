"""Temporal Awareness — Deterministic utilities for time-aware research reasoning.

Provides query temporal sensitivity detection, source date extraction,
temporal distribution analysis, and bounded recency penalty computation.

All functions are pure, rule-based, and deterministic.
No LLM calls, no randomness, no hard date filtering.
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MIN_DATED_SOURCES = 3       # Minimum sources with known dates before penalty applies
RECENCY_THRESHOLD_YEARS = 5  # Sources older than this are considered "older"
MAX_RECENCY_PENALTY = 0.05   # Bounded ceiling for confidence reduction
MIN_DATED_COVERAGE = 0.50    # At least 50% of sources must have dates for penalty

# Strong recency indicators — trigger sensitivity on their own
_STRONG_RECENCY_TERMS = [
    "latest",
    "recent",
    "current",
    "today",
    "this year",
    "updated",
    "new developments",
    "as of",
]

# Trend terms — only trigger when combined with a present-tense qualifier
_TREND_TERMS = [
    "trend",
    "growth rate",
    "market size",
    "regulation changes",
    "emerging",
]

# Present-tense qualifiers required alongside trend terms
_PRESENT_QUALIFIERS = [
    "current",
    "recent",
    "latest",
    "today",
    "now",
    "this year",
]


# ---------------------------------------------------------------------------
# 1. Query Temporal Sensitivity Detection
# ---------------------------------------------------------------------------
def detect_temporal_sensitivity(query: str) -> bool:
    """Determine if a query is temporally sensitive using rule-based detection.

    A query is temporally sensitive ONLY if at least ONE condition is met:
      A) Contains a strong recency indicator
      B) Contains a year within [current_year - 1, current_year + 1]
      C) Contains a trend term AND a present-tense qualifier

    Returns True if temporally sensitive, False otherwise.
    Fully deterministic, no LLM calls.
    """
    query_lower = query.lower()

    # ── Condition A: Strong recency indicators ───────────────────────
    for term in _STRONG_RECENCY_TERMS:
        if term in query_lower:
            return True

    # ── Condition B: Explicit year reference (recent years only) ─────
    current_year = datetime.now().year
    year_pattern = re.compile(r"\b((?:19|20)\d{2})\b")
    for match in year_pattern.finditer(query_lower):
        year = int(match.group(1))
        if year >= current_year - 1:
            return True

    # ── Condition C: Trend term + present-tense qualifier ────────────
    has_trend_term = any(term in query_lower for term in _TREND_TERMS)
    if has_trend_term:
        has_qualifier = any(qual in query_lower for qual in _PRESENT_QUALIFIERS)
        if has_qualifier:
            return True

    return False


# ---------------------------------------------------------------------------
# 2. Source Date Extraction
# ---------------------------------------------------------------------------
def extract_publication_year(publication_date: Optional[str]) -> Optional[int]:
    """Extract a 4-digit year from a date string.

    Handles common formats: ISO 8601, YYYY-MM-DD, Month YYYY, etc.
    Returns int year or None if unparseable. Never guesses.
    """
    if not publication_date:
        return None

    date_str = str(publication_date).strip()
    if not date_str:
        return None

    # Try direct 4-digit year extraction first
    year_match = re.search(r"\b((?:19|20)\d{2})\b", date_str)
    if year_match:
        return int(year_match.group(1))

    return None


# ---------------------------------------------------------------------------
# 3. Temporal Distribution Analysis
# ---------------------------------------------------------------------------
def compute_temporal_distribution(
    sources: List[Any],
    current_year: Optional[int] = None,
    threshold_years: int = RECENCY_THRESHOLD_YEARS,
) -> Dict[str, int]:
    """Analyze the temporal distribution of research sources.

    Args:
        sources: list of SourceMetadata objects (must have publication_date)
        current_year: override for testing; defaults to datetime.now().year
        threshold_years: sources older than this are counted as "older"

    Returns dict with counts: sources_with_dates, recent_sources,
    older_sources, unknown_date_sources, total_sources.
    """
    if current_year is None:
        current_year = datetime.now().year

    cutoff_year = current_year - threshold_years

    sources_with_dates = 0
    recent_sources = 0
    older_sources = 0
    unknown_date_sources = 0

    for source in sources:
        pub_date = getattr(source, "publication_date", None)
        year = extract_publication_year(pub_date)

        if year is not None:
            sources_with_dates += 1
            if year >= cutoff_year:
                recent_sources += 1
            else:
                older_sources += 1
        else:
            unknown_date_sources += 1

    return {
        "total_sources": len(sources),
        "sources_with_dates": sources_with_dates,
        "recent_sources": recent_sources,
        "older_sources": older_sources,
        "unknown_date_sources": unknown_date_sources,
    }


# ---------------------------------------------------------------------------
# 4. Bounded Recency Penalty
# ---------------------------------------------------------------------------
def compute_recency_penalty(
    distribution: Dict[str, int],
    is_temporally_sensitive: bool,
) -> float:
    """Compute a bounded recency penalty for confidence adjustment.

    Applies penalty ONLY IF ALL conditions are satisfied:
      1. is_temporally_sensitive == True
      2. sources_with_dates >= MIN_DATED_SOURCES (3)
      3. At least 50% of total sources have known dates
      4. Majority of dated sources are older than threshold

    Returns 0.0 if conditions not met, otherwise bounded by MAX_RECENCY_PENALTY (0.05).
    """
    # Gate 1: not temporally sensitive → no penalty
    if not is_temporally_sensitive:
        return 0.0

    total = distribution.get("total_sources", 0)
    dated = distribution.get("sources_with_dates", 0)
    older = distribution.get("older_sources", 0)

    # Gate 2: insufficient dated sources
    if dated < MIN_DATED_SOURCES:
        return 0.0

    # Gate 3: insufficient date coverage (< 50% of total have dates)
    if total > 0 and (dated / total) < MIN_DATED_COVERAGE:
        return 0.0

    # Gate 4: majority of dated sources must be older
    if dated > 0 and (older / dated) > 0.5:
        # Scale penalty proportionally, bounded at MAX_RECENCY_PENALTY
        old_ratio = older / dated
        penalty = old_ratio * MAX_RECENCY_PENALTY
        return round(min(penalty, MAX_RECENCY_PENALTY), 4)

    return 0.0
