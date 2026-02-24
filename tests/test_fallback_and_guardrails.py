"""Verification test suite for Factual Resolution Collapse fix.

Covers:
  - Fallback extractor clause-binding
  - Scope isolation (non-factoid queries unaffected)
  - Extraction correctness
  - Edge cases

Run: python tests/test_fallback_and_guardrails.py
"""

import sys
import os

# Ensure project root on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.fallback_extractor import (
    _clause_bound_check,
    _extract_factual_sentences,
    _extract_entity,
    fallback_extract_insights,
)
from core.event_filter import contains_completed_result, _is_primarily_future
from core.query_intent import QueryIntent, detect_query_intent
from schemas import Insight

# ── Test infrastructure ─────────────────────────────────────────────────────

passed = 0
failed = 0


def check(name: str, condition: bool, detail: str = ""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS: {name}")
    else:
        failed += 1
        print(f"  FAIL: {name} {('— ' + detail) if detail else ''}")


# ── Phase 2: Clause-Bound Extraction ────────────────────────────────────────

print("\n=== 1. Clause-Binding Tests ===\n")

# Valid: winner verb + year in same clause
check("clause_same_clause",
      _clause_bound_check("Argentina won the 2022 FIFA World Cup", 2026))

# Valid: year in preceding clause (common in news)
check("clause_preceding",
      _clause_bound_check("In 2022, Argentina won the FIFA World Cup", 2026))

# Invalid: winner verb and future year in different clause
check("clause_different_clause_future",
      not _clause_bound_check(
          "Argentina won several matches; the 2026 edition will be in North America", 2025))

# Valid: no year at all (query constrains it)
check("clause_no_year",
      _clause_bound_check("Argentina won the FIFA World Cup", 2026))

# Invalid: year is only future
check("clause_future_only",
      not _clause_bound_check("The team will win the 2030 World Cup", 2026))

# Valid: past year present even though future year in different clause
check("clause_mixed_past_dominant",
      _clause_bound_check("France won in 2018; the 2022 edition was in Qatar", 2026))

# Valid: passive voice with year
check("clause_passive_with_year",
      _clause_bound_check("The 2022 World Cup was won by Argentina", 2026))


# ── Phase 2: Sentence Extraction ────────────────────────────────────────────

print("\n=== 2. Sentence Extraction Tests ===\n")

text1 = "Argentina won the 2022 FIFA World Cup. The 2026 edition will be hosted by USA, Canada, and Mexico."
sents1 = _extract_factual_sentences(text1, 2026)
check("sentence_extracts_past_only",
      len(sents1) == 1 and "Argentina" in sents1[0],
      f"got {sents1}")

text2 = "France defeated Croatia in the 2018 FIFA World Cup final."
sents2 = _extract_factual_sentences(text2, 2026)
check("sentence_defeat_verb",
      len(sents2) == 1 and "France" in sents2[0])

text3 = "Brazil is expected to win the 2026 World Cup."
sents3 = _extract_factual_sentences(text3, 2025)
check("sentence_rejects_future",
      len(sents3) == 0)

text4 = "The champion was crowned champion in front of 80,000 fans"
sents4 = _extract_factual_sentences(text4, 2026)
check("sentence_champion_no_year_ok",
      len(sents4) == 1)

# ── Phase 2: Entity Extraction ──────────────────────────────────────────────

print("\n=== 3. Entity Extraction Tests ===\n")

check("entity_argentina",
      _extract_entity("Argentina won the 2022 FIFA World Cup") == "Argentina")

check("entity_france",
      _extract_entity("France defeated Croatia in the final") == "France")

check("entity_skip_event_name",
      _extract_entity("The World Cup was held in Qatar") is not None)


# ── Phase 3: Full Fallback Extraction ───────────────────────────────────────

print("\n=== 4. Fallback Extraction E2E ===\n")


class FakeSource:
    def __init__(self, summary, url="https://example.com/article"):
        self.summary = summary
        self.url = url


sources_good = [
    FakeSource("Argentina won the 2022 FIFA World Cup, defeating France in the final."),
    FakeSource("Lionel Messi lifted the trophy in Qatar after Argentina's victory in 2022."),
]

insights, rescue_count = fallback_extract_insights(sources_good, "Winner", current_year=2026)
check("fallback_e2e_extracts",
      len(insights) >= 1,
      f"expected ≥1, got {len(insights)}")
check("fallback_e2e_rescue_count",
      rescue_count >= 1)
check("fallback_e2e_confidence",
      all(i.confidence == 0.80 for i in insights))
check("fallback_e2e_has_url",
      all(len(i.supporting_sources) > 0 for i in insights))

# Negative: future-only sources
sources_future = [
    FakeSource("The 2030 World Cup will be hosted by multiple countries."),
]
insights_f, rescue_f = fallback_extract_insights(sources_future, "Winner", current_year=2026)
check("fallback_rejects_future",
      len(insights_f) == 0 and rescue_f == 0)

# Clause-binding negative: winner verb in clause 1, year in clause 2
sources_mixed = [
    FakeSource("Argentina won many titles; the 2026 World Cup is upcoming in North America"),
]
insights_m, rescue_m = fallback_extract_insights(sources_mixed, "Winner", current_year=2025)
check("fallback_clause_rejects_cross_clause",
      len(insights_m) == 0,
      f"expected 0, got {len(insights_m)}")


# ── Phase 3: Scope Isolation ───────────────────────────────────────────────

print("\n=== 5. Scope Isolation Tests ===\n")

check("scope_factoid_detected",
      detect_query_intent("Who won the 2022 FIFA World Cup?") == QueryIntent.FACTUAL_EVENT_WINNER)

check("scope_trend_not_factoid",
      detect_query_intent("Latest trends in FIFA World Cup viewership") != QueryIntent.FACTUAL_EVENT_WINNER)

check("scope_research_not_factoid",
      detect_query_intent("Impact of AI on healthcare diagnostics") == QueryIntent.OTHER)

check("scope_future_not_factoid",
      detect_query_intent("Who will win the 2026 World Cup?") != QueryIntent.FACTUAL_EVENT_WINNER)


# ── Phase 6: Event Filter Validation ───────────────────────────────────────

print("\n=== 6. Event Filter Clause Tests ===\n")

insight_past = Insight(
    subtopic="Winner", statement="Argentina won the 2022 FIFA World Cup",
    supporting_sources=["https://example.com"], confidence=0.9, stance="neutral"
)
check("filter_accepts_past",
      contains_completed_result([insight_past], current_year=2026))

insight_no_verb = Insight(
    subtopic="Host", statement="The 2022 FIFA World Cup was held in Qatar",
    supporting_sources=["https://example.com"], confidence=0.9, stance="neutral"
)
check("filter_rejects_no_winner_verb",
      not contains_completed_result([insight_no_verb], current_year=2026))

insight_future = Insight(
    subtopic="Winner", statement="Brazil will win the 2030 World Cup",
    supporting_sources=["https://example.com"], confidence=0.5, stance="neutral"
)
check("filter_rejects_future",
      not contains_completed_result([insight_future], current_year=2026))


# ── Phase 7: Schema Trace Fields ────────────────────────────────────────────

print("\n=== 7. Schema Trace Fields ===\n")

from schemas import ResearchTraceEntry

# Verify new fields exist with defaults
trace = ResearchTraceEntry(
    iteration=1,
    subtopic_confidences={"Winner": 0.85},
    global_confidence=0.85,
    weak_subtopics=[],
    plan_updates=[],
    new_sources_added=3,
)
check("trace_fallback_rescue_count_default",
      trace.fallback_rescue_count == 0)
check("trace_confidence_floor_applied_default",
      trace.confidence_floor_applied == False)

# Verify they can be set
trace2 = ResearchTraceEntry(
    iteration=1,
    subtopic_confidences={"Winner": 0.85},
    global_confidence=0.85,
    weak_subtopics=[],
    plan_updates=[],
    new_sources_added=3,
    fallback_rescue_count=2,
    confidence_floor_applied=True,
)
check("trace_fallback_rescue_count_set",
      trace2.fallback_rescue_count == 2)
check("trace_confidence_floor_applied_set",
      trace2.confidence_floor_applied == True)


# ── Summary ─────────────────────────────────────────────────────────────────

print(f"\n{'=' * 40}")
print(f"TOTAL: {passed} passed, {failed} failed")
if failed == 0:
    print("All tests passed!")
else:
    print(f"FAILURES DETECTED: {failed}")
    sys.exit(1)
