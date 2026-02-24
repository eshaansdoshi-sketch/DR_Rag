"""Deterministic Fallback Extractor — Last-resort insight extraction from raw snippets.

When the LLM analyst fails to produce valid Insight objects (schema validation
failure, empty output, hallucination), this module extracts factual answers
directly from raw source summaries using pattern matching.

Design:
  - Pure regex + heuristic — no LLM calls
  - Only activates for FACTUAL_EVENT_WINNER intent
  - Only runs when analyst produced zero insights
  - Constructs minimal valid Insight objects from raw text
  - CLAUSE-BOUND: winner verb and year must appear in the same clause
"""

import logging
import re
from datetime import datetime
from typing import List, Optional, Tuple

from schemas import Insight

logger = logging.getLogger(__name__)


# ── Winner verb patterns (must match event_filter.py) ──────────────────────

_WINNER_RE = re.compile(
    r"\bwon\b|\bdefeated\b|\bclaimed\b|\bsecured\b|\bcaptured\b"
    r"|\blifted\b|\btriumphed\b|\bcrowned\b|\bawarded\b|\belected\b"
    r"|\bbeat\b|\bconquered\b|\bprevailed\b"
    r"|\bwas\s+won\b|\bwas\s+awarded\b|\bwas\s+elected\b"
    r"|\bvictorious\b|\bchampion\b|\bwinning\b|\bvictory\b"
    r"|\btook\s+home\b|\bclinched\b|\bearned\b",
    re.IGNORECASE,
)

# Entity extraction: capitalized word sequences
_ENTITY_RE = re.compile(
    r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b"
)

# Year extraction
_YEAR_RE = re.compile(r"\b((?:19|20)\d{2})\b")

# Future indicator (to reject future-tense statements)
_FUTURE_RE = re.compile(
    r"\bwill\s+(?:be|win|host|take)\b|\bexpected\s+to\s+win\b"
    r"|\bupcoming\b|\bscheduled\b",
    re.IGNORECASE,
)

# Clause separators — commas, semicolons, em-dashes, conjunctions
_CLAUSE_SPLIT_RE = re.compile(
    r"[;]|\s+but\s+|\s+while\s+|\s+whereas\s+|\s+although\s+"
    r"|\s+however[,]?\s+|\s+meanwhile\s+"
)


def _clause_bound_check(sentence: str, current_year: int) -> bool:
    """Verify that a winner verb and a past year co-occur in the same clause.

    Returns True if:
      - Winner verb and year ≤ current_year appear in the same clause, OR
      - Winner verb exists and no year at all (query already constrains year)

    Returns False if:
      - Year is in a different clause from the winner verb
      - All years in the sentence are future
    """
    # Split into clauses
    clauses = _CLAUSE_SPLIT_RE.split(sentence)
    if not clauses:
        clauses = [sentence]

    has_any_year = bool(_YEAR_RE.search(sentence))

    for clause in clauses:
        clause = clause.strip()
        if not clause:
            continue

        has_verb = bool(_WINNER_RE.search(clause))
        if not has_verb:
            continue

        # This clause has a winner verb.
        clause_years = [int(m.group(1)) for m in _YEAR_RE.finditer(clause)]
        past_years = [y for y in clause_years if y <= current_year]

        if past_years:
            # Winner verb + past year in same clause → valid
            return True

        if not clause_years and not has_any_year:
            # No year anywhere in sentence, but verb present → acceptable
            # (query already constrains the year)
            return True

        if not clause_years and has_any_year:
            # Year exists elsewhere in sentence but NOT in this clause
            # Check if it's in an adjacent clause containing the event name
            # (e.g. "In 2022, Argentina won the FIFA World Cup")
            idx = clauses.index(clause) if clause in clauses else -1
            if idx > 0:
                prev_clause = clauses[idx - 1].strip()
                prev_years = [int(m.group(1)) for m in _YEAR_RE.finditer(prev_clause)]
                prev_past = [y for y in prev_years if y <= current_year]
                if prev_past:
                    return True

    return False


def _extract_factual_sentences(text: str, current_year: int) -> List[str]:
    """Extract sentences that contain a clause-bound winner verb + past year."""
    # Split into sentences
    sentences = re.split(r'[.!?]+', text)
    results = []

    for sent in sentences:
        sent = sent.strip()
        if not sent or len(sent) < 15:
            continue

        # Must have a winner verb
        if not _WINNER_RE.search(sent):
            continue

        # Must NOT be future tense
        if _FUTURE_RE.search(sent):
            continue

        # Must have a past year (or no year — query may constrain it)
        years = [int(m.group(1)) for m in _YEAR_RE.finditer(sent)]
        future_years = [y for y in years if y > current_year]
        if future_years and not [y for y in years if y <= current_year]:
            continue  # Only future years → skip

        # Clause-binding: winner verb and year must co-occur in same clause
        if not _clause_bound_check(sent, current_year):
            logger.debug(
                "fallback_clause_reject | sentence=%.80s...", sent,
            )
            continue

        results.append(sent)

    return results


def _extract_entity(sentence: str) -> Optional[str]:
    """Extract the most likely winner entity from a sentence.

    Heuristic: find capitalized word sequences, exclude common non-entities.
    """
    non_entities = {
        "The", "This", "That", "In", "On", "At", "For", "With", "From",
        "After", "Before", "During", "Between", "World", "Cup", "Prize",
        "League", "Championship", "Tournament", "Final", "Olympic",
        "Olympics", "Super", "Bowl", "Academy", "Award", "Awards",
    }

    matches = _ENTITY_RE.findall(sentence)
    for match in matches:
        words = match.split()
        if len(words) == 1 and words[0] in non_entities:
            continue
        if all(w in non_entities for w in words):
            continue
        return match

    return None


def fallback_extract_insights(
    sources: list,
    subtopic_name: str = "Winner",
    current_year: Optional[int] = None,
) -> Tuple[List[Insight], int]:
    """Extract factual insights directly from raw source summaries.

    This is a LAST RESORT when the LLM analyst produces zero valid insights.
    It scans source summaries for clause-bound winner-verb + entity + year
    patterns and constructs minimal Insight objects.

    Args:
        sources: list of SourceMetadata objects (must have .summary, .url)
        subtopic_name: subtopic to assign to extracted insights
        current_year: override for testing

    Returns:
        Tuple of (List of Insight objects, count of rescued insights)
    """
    if current_year is None:
        current_year = datetime.now().year

    extracted: List[Insight] = []
    seen_statements: set = set()

    for source in sources:
        summary = getattr(source, "summary", "")
        url = str(getattr(source, "url", ""))

        if not summary:
            continue

        factual_sentences = _extract_factual_sentences(summary, current_year)

        for sentence in factual_sentences:
            norm = sentence.lower().strip()
            if norm in seen_statements:
                continue
            seen_statements.add(norm)

            entity = _extract_entity(sentence)
            if not entity:
                continue

            try:
                insight = Insight(
                    subtopic=subtopic_name,
                    statement=sentence.strip(),
                    supporting_sources=[url] if url else [],
                    confidence=0.80,
                    stance="neutral",
                )
                extracted.append(insight)
                logger.info(
                    "fallback_extract | entity=%s sentence=%.80s... url=%s",
                    entity, sentence, url,
                )
            except Exception as e:
                logger.warning(
                    "fallback_extract_failed | sentence=%.80s... error=%s",
                    sentence, e,
                )

    rescue_count = len(extracted)

    if extracted:
        logger.info(
            "fallback_extract_total | count=%d from %d sources",
            rescue_count, len(sources),
        )
    else:
        logger.warning(
            "fallback_extract_empty | no clause-bound factual patterns found in %d sources",
            len(sources),
        )

    return extracted, rescue_count
