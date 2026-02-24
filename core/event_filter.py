"""Event Completion Filter — Deterministic future-event rejection and resolution validation.

Applied during the analysis phase when ``query_intent == FACTUAL_EVENT_WINNER``.
All logic is pure, rule-based, and deterministic.  No LLM calls.

Design priorities (in order):
  1. Year-based rejection  (strongest — ``event_year > current_year``)
  2. Keyword-based future-event indicators  (secondary)
  3. Resolution validation  (relaxed — single source accepted as fallback)

Anti-pattern avoided:
  Over-constraining causes false-negative resolution — rejecting correct
  answers is worse than accepting mild noise.  The filter must be
  permissive enough that legitimate past-event insights survive.
"""

import logging
import re
from datetime import datetime
from typing import List, Optional, Tuple

from core.query_intent import QueryIntent

logger = logging.getLogger(__name__)


# ── Future-event keyword indicators (secondary to year check) ──────────────

FUTURE_EVENT_INDICATORS = [
    "upcoming",
    "will be held",
    "scheduled for",
    "preview",
    "qualification stage",
    "to be played",
    "is expected to win",
    "will take place",
    "set to begin",
    "preparations for",
    "bid to host",
    "expected to win",
    "projected to win",
    "will compete",
    "qualifying round",
    "draw ceremony",
]

# Winner-action verbs — BOTH active and passive voice
_WINNER_VERBS_RE = re.compile(
    # Active: "Argentina won", "Messi defeated"
    r"\bwon\b|\bdefeated\b|\bclaimed\b|\bsecured\b|\bcaptured\b"
    r"|\blifted\b|\btriumphed\b|\bcrowned\b|\bawarded\b|\belected\b"
    r"|\bbeat\b|\bconquered\b|\bprevailed\b"
    # Passive: "was won by", "were crowned", "has been awarded"
    r"|\bwas\s+won\b|\bwere\s+crowned\b|\bwas\s+awarded\b"
    r"|\bwas\s+elected\b|\bwas\s+defeated\b|\bwas\s+claimed\b"
    # Past participles that appear without auxiliary in LLM extractions
    r"|\bvictorious\b|\bchampion\b|\bwinning\b|\bvictory\b"
    # Common phrasings in factual summaries
    r"|\btook\s+home\b|\bclinched\b|\bearned\b|\blifted\s+the\b"
    r"|\bhoisted\b|\bdominated\b",
    re.IGNORECASE,
)

# Future tense indicators (for resolution validation)
# Made more specific to reduce false positives on historical statements
_FUTURE_TENSE_RE = re.compile(
    r"\bwill\s+(?:be\s+)?(?:held|played|hosted|take\s+place)\b"
    r"|\bgoing\s+to\s+(?:be\s+)?(?:held|hosted)\b"
    r"|\bis\s+expected\s+to\s+win\b"
    r"|\bupcoming\s+(?:tournament|edition|event|cup|games)\b"
    r"|\bscheduled\s+(?:for|to)\b",
    re.IGNORECASE,
)

# Year extraction
_YEAR_RE = re.compile(r"\b((?:19|20)\d{2})\b")


# ── Primary: Year-based rejection ─────────────────────────────────────────

def _extract_years(text: str) -> List[int]:
    """Extract all 4-digit years from text."""
    return [int(m.group(1)) for m in _YEAR_RE.finditer(text)]


def _is_primarily_future(statement: str, current_year: int) -> bool:
    """Determine if an insight's primary statement concerns a future event.

    PERMISSIVE by design — only rejects statements that are CLEARLY about
    future events.  Mixed statements (past result + future mention) are KEPT.

    Criteria (evaluated in priority order):
      1. ALL years in statement > current_year  →  future
      2. Statement has future keyword AND zero past-year anchors AND
         zero winner verbs  →  future
      3. Otherwise  →  NOT future (kept)
    """
    years = _extract_years(statement)
    has_winner_verb = bool(_WINNER_VERBS_RE.search(statement))

    # Priority 1: year-based — strongest signal
    if years:
        past_years = [y for y in years if y <= current_year]
        future_years = [y for y in years if y > current_year]

        # If ALL years are future → reject
        if future_years and not past_years:
            return True

        # If there's ANY past year → keep (even if future years also present)
        # This prevents rejecting "Argentina won 2022 WC; 2026 WC will be in USA"
        if past_years:
            return False

    # Priority 2: keyword-based — only reject if NO past-year anchor AND
    #             NO winner verb (be very permissive)
    statement_lower = statement.lower()
    has_future_keyword = any(ind in statement_lower for ind in FUTURE_EVENT_INDICATORS)
    if has_future_keyword and not has_winner_verb:
        return True

    return False


# ── Public API ─────────────────────────────────────────────────────────────

def filter_future_event_insights(
    insights: list,
    intent: QueryIntent,
    current_year: Optional[int] = None,
) -> Tuple[list, int]:
    """Filter out future-event insights when intent is FACTUAL_EVENT_WINNER.

    PERMISSIVE: Only rejects insights that are CLEARLY about future events.
    When in doubt, the insight is KEPT.

    Args:
        insights: list of Insight objects (must have .statement attribute)
        intent: detected QueryIntent
        current_year: override for testing; defaults to datetime.now().year

    Returns:
        (kept_insights, rejected_count)
    """
    if intent != QueryIntent.FACTUAL_EVENT_WINNER:
        return insights, 0

    if current_year is None:
        current_year = datetime.now().year

    kept = []
    rejected = 0

    for insight in insights:
        if _is_primarily_future(insight.statement, current_year):
            rejected += 1
            logger.debug(
                "Event filter REJECTED insight: %.100s...",
                insight.statement,
            )
        else:
            kept.append(insight)

    # Safety net: if filter would reject ALL insights, keep them all.
    # An answer with noise is better than no answer at all.
    if not kept and insights:
        logger.warning(
            "Event filter would reject ALL %d insights — disabling filter "
            "to prevent total information loss.",
            len(insights),
        )
        return insights, 0

    logger.info(
        "Event filter: kept=%d, rejected=%d (of %d total)",
        len(kept), rejected, len(insights),
    )
    return kept, rejected


def contains_completed_result(
    insights: list,
    current_year: Optional[int] = None,
) -> bool:
    """Check if insights contain a credible completed-event resolution.

    Resolution succeeds if ANY of these tiers match:

    Tier 1 (strong):
      - Insight has past year + winner verb + ≥2 sources

    Tier 2 (acceptable — single source fallback):
      - Insight has past year + winner verb + ≥1 source

    Tier 3 (weak but valid — extracted fact without source metadata):
      - Insight has past year + winner verb
      - (Sources may be empty if analyst didn't link them)

    The multi-source requirement was causing false negatives in early
    iterations where the analyst only has 1-2 sources per subtopic.
    """
    if current_year is None:
        current_year = datetime.now().year

    for insight in insights:
        stmt = insight.statement

        # Condition 1: past year present
        years = _extract_years(stmt)
        past_years = [y for y in years if y <= current_year]
        if not past_years:
            continue

        # Condition 2: winner-action verb present
        if not _WINNER_VERBS_RE.search(stmt):
            continue

        # Condition 3: no STRONG future tense (relaxed — only reject
        # statements primarily about future events)
        if _is_primarily_future(stmt, current_year):
            continue

        # If we get here, this is a valid completed-result insight.
        # Source count is a nice-to-have, not a gate.
        logger.debug(
            "Completed result found: %.100s... (sources=%d)",
            stmt,
            len(getattr(insight, "supporting_sources", [])),
        )
        return True

    return False


def count_agreeing_sources(insights: list, current_year: Optional[int] = None) -> int:
    """Count the number of sources that support a completed-event resolution.

    Counts unique supporting source URLs across insights that pass the
    completed-result criteria (past year + winner verb + not primarily future).
    """
    if current_year is None:
        current_year = datetime.now().year

    agreeing_urls: set = set()

    for insight in insights:
        stmt = insight.statement
        years = _extract_years(stmt)
        past_years = [y for y in years if y <= current_year]

        if not past_years:
            continue
        if not _WINNER_VERBS_RE.search(stmt):
            continue
        if _is_primarily_future(stmt, current_year):
            continue

        sources = getattr(insight, "supporting_sources", [])
        agreeing_urls.update(str(s) for s in sources)

    return len(agreeing_urls)


def compute_future_drift_penalty(
    insights: list,
    intent: QueryIntent,
    current_year: Optional[int] = None,
) -> float:
    """Compute confidence penalty for future-event drift.

    Penalty tiers:
      • ≥50% future insights AND no completed result  →  0.15 (strong)
      • ≥50% future insights AND completed result found →  0.03 (mild)
      • <50% future insights AND no completed result   →  0.08 (moderate)
      • Otherwise → 0.0

    Penalties are softer than the original design because over-penalizing
    causes confidence collapse when the system HAS the correct answer
    but also retrieved some future-event noise.

    Returns 0.0 for non-FACTUAL_EVENT_WINNER intents.
    """
    if intent != QueryIntent.FACTUAL_EVENT_WINNER:
        return 0.0

    if not insights:
        return 0.0

    if current_year is None:
        current_year = datetime.now().year

    # Count future vs total
    future_count = sum(
        1 for i in insights if _is_primarily_future(i.statement, current_year)
    )
    total = len(insights)
    future_ratio = future_count / total if total > 0 else 0.0

    has_completed = contains_completed_result(insights, current_year)

    # Penalty tiers — softer to prevent confidence collapse
    if future_ratio >= 0.5 and not has_completed:
        return 0.15  # Strong but not crushing
    elif future_ratio >= 0.5 and has_completed:
        return 0.03  # Very mild — we have the answer
    elif not has_completed and future_count > 0:
        return 0.08  # Moderate
    else:
        return 0.0


def build_factual_refinement_query(
    event_name: Optional[str],
    jurisdiction: Optional[str] = None,
    is_election: bool = False,
) -> str:
    """Build a refinement query targeting completed event results.

    Used when contains_completed_result() returns False to guide
    the next search iteration toward factual resolution.
    """
    if is_election:
        if jurisdiction and event_name:
            return f"most recent completed {jurisdiction} {event_name} winner result"
        elif event_name:
            return f"most recent completed {event_name} winner result"
        else:
            return "most recent completed election winner result"

    if event_name:
        return f"{event_name} most recent completed winner final result"

    return "most recent completed event winner result"
