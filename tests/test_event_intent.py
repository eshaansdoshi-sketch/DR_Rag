"""Comprehensive test for Event Completion Intent Recognition.

Run:  python tests/test_event_intent.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.query_intent import (
    QueryIntent,
    detect_query_intent,
    extract_event_name,
    extract_event_year,
    has_recency_modifier,
    is_election_query,
    extract_jurisdiction,
    reformulate_event_query,
)
from core.event_filter import (
    compute_future_drift_penalty,
    contains_completed_result,
    count_agreeing_sources,
    filter_future_event_insights,
    build_factual_refinement_query,
)


# ── Helpers ────────────────────────────────────────────────────────────────

class FakeInsight:
    """Minimal insight stand-in for testing."""
    def __init__(self, statement: str, supporting_sources: list = None):
        self.statement = statement
        self.supporting_sources = supporting_sources or []


passed = 0
failed = 0

def check(label: str, actual, expected):
    global passed, failed
    if actual == expected:
        passed += 1
        print(f"  PASS: {label}")
    else:
        failed += 1
        print(f"  FAIL: {label}")
        print(f"        expected: {expected}")
        print(f"        actual:   {actual}")


# ── 1. Intent Classification ──────────────────────────────────────────────

print("\n=== 1. Intent Classification ===")

# Mandatory edge cases from requirements
check("who_won_last_fifa",
      detect_query_intent("Who won the last FIFA World Cup?"),
      QueryIntent.FACTUAL_EVENT_WINNER)

check("who_won_2018_fifa",
      detect_query_intent("Who won the 2018 FIFA World Cup?"),
      QueryIntent.FACTUAL_EVENT_WINNER)

check("who_won_fifa_no_qualifier",
      detect_query_intent("Who won FIFA World Cup?"),
      QueryIntent.FACTUAL_EVENT_WINNER)

check("who_won_latest_fifa",
      detect_query_intent("Who won the latest FIFA World Cup?"),
      QueryIntent.FACTUAL_EVENT_WINNER)

check("who_will_win_future_fifa",
      detect_query_intent("Who will win the 2026 FIFA World Cup?"),
      QueryIntent.OTHER)  # No winner signal (will win ≠ won)

check("who_won_last_us_election",
      detect_query_intent("Who won the last US election?"),
      QueryIntent.FACTUAL_EVENT_WINNER)

check("trends_fifa_viewership",
      detect_query_intent("Latest trends in FIFA World Cup viewership"),
      QueryIntent.TREND_ANALYSIS)

check("nobel_prize_2023",
      detect_query_intent("Who won the Nobel Prize in Physics 2023?"),
      QueryIntent.FACTUAL_EVENT_WINNER)

check("quantum_computing",
      detect_query_intent("What is quantum computing?"),
      QueryIntent.OTHER)

check("champions_league_winner",
      detect_query_intent("Who won the latest Champions League?"),
      QueryIntent.FACTUAL_EVENT_WINNER)

check("wimbledon_winner",
      detect_query_intent("Who won Wimbledon?"),
      QueryIntent.FACTUAL_EVENT_WINNER)

check("open_source_false_positive",
      detect_query_intent("open source software trends"),
      QueryIntent.OTHER)  # Must NOT match tennis "Open"

check("latest_oscar_winner",
      detect_query_intent("Who won the latest Oscar for best picture?"),
      QueryIntent.FACTUAL_EVENT_WINNER)

check("super_bowl_champion",
      detect_query_intent("Who is the Super Bowl champion?"),
      QueryIntent.FACTUAL_EVENT_WINNER)

check("ipl_winner_2024",
      detect_query_intent("Who won IPL 2024?"),
      QueryIntent.FACTUAL_EVENT_WINNER)


# ── 2. Event Name & Year Extraction ───────────────────────────────────────

print("\n=== 2. Event Name & Year Extraction ===")

check("event_name_fifa",
      extract_event_name("Who won the 2022 FIFA World Cup?"),
      "FIFA World Cup")

check("event_name_olympics",
      extract_event_name("Who won gold at the Olympics?"),
      "Olympics")

check("event_name_none",
      extract_event_name("What is the meaning of life?"),
      None)

check("event_year_2022",
      extract_event_year("Who won the 2022 FIFA World Cup?"),
      2022)

check("event_year_none",
      extract_event_year("Who won the last FIFA World Cup?"),
      None)

check("event_year_2023",
      extract_event_year("Nobel Prize in Physics 2023"),
      2023)


# ── 3. Recency & Reformulation ────────────────────────────────────────────

print("\n=== 3. Recency & Reformulation ===")

check("has_recency_last",
      has_recency_modifier("Who won the last FIFA World Cup?"),
      True)

check("has_recency_none",
      has_recency_modifier("Who won the 2018 FIFA World Cup?"),
      False)

# Should NOT reformulate when year is provided
check("no_reformulate_with_year",
      reformulate_event_query("Who won the 2018 FIFA World Cup?",
                              QueryIntent.FACTUAL_EVENT_WINNER),
      None)

# Should reformulate when "latest" is used without year
result = reformulate_event_query("Who won the latest FIFA World Cup?",
                                  QueryIntent.FACTUAL_EVENT_WINNER)
check("reformulate_latest_fifa",
      result is not None and "FIFA World Cup" in result,
      True)

# Should NOT reformulate for non-event queries
check("no_reformulate_other",
      reformulate_event_query("What is quantum computing?", QueryIntent.OTHER),
      None)


# ── 4. Election Edge Cases ────────────────────────────────────────────────

print("\n=== 4. Election Edge Cases ===")

check("is_election_us",
      is_election_query("Who won the last US presidential election?"),
      True)

check("is_election_not",
      is_election_query("Who won the FIFA World Cup?"),
      False)

check("jurisdiction_us",
      extract_jurisdiction("Who won the last US presidential election?") is not None,
      True)

check("jurisdiction_india",
      extract_jurisdiction("Who won the Indian general election?") is not None,
      True)


# ── 5. Future Event Filtering ─────────────────────────────────────────────

print("\n=== 5. Future Event Filtering ===")

insights_mixed = [
    FakeInsight("Argentina won the 2022 FIFA World Cup by defeating France.",
                ["src1", "src2"]),
    FakeInsight("The 2026 FIFA World Cup will be held in North America.",
                ["src3"]),
    FakeInsight("The upcoming 2026 World Cup is expected to be the largest ever.",
                ["src4"]),
]

kept, rejected = filter_future_event_insights(
    insights_mixed, QueryIntent.FACTUAL_EVENT_WINNER, current_year=2025
)
check("filter_keeps_past",
      len(kept), 1)
check("filter_rejects_future",
      rejected, 2)

# Should NOT filter for OTHER intent
kept2, rej2 = filter_future_event_insights(
    insights_mixed, QueryIntent.OTHER, current_year=2025
)
check("no_filter_other_intent",
      len(kept2), 3)


# ── 6. Completed Result Validation ────────────────────────────────────────

print("\n=== 6. Completed Result Validation ===")

# Strong: past year + winner verb + multi-source
good_insights = [
    FakeInsight("Argentina won the 2022 FIFA World Cup.",
                ["src1", "src2", "src3"]),
]
check("completed_strong",
      contains_completed_result(good_insights, current_year=2025),
      True)

# Single source — should now PASS (relaxed constraint)
single_source = [
    FakeInsight("Argentina won the 2022 FIFA World Cup.",
                ["src1"]),
]
check("completed_single_source_ok",
      contains_completed_result(single_source, current_year=2025),
      True)

# Passive voice — must also work
passive_insights = [
    FakeInsight("The 2022 FIFA World Cup was won by Argentina.",
                ["src1"]),
]
check("completed_passive_voice",
      contains_completed_result(passive_insights, current_year=2025),
      True)

# "champion" phrasing
champion_insights = [
    FakeInsight("Argentina became champion of the 2022 World Cup.",
                ["src1"]),
]
check("completed_champion_phrasing",
      contains_completed_result(champion_insights, current_year=2025),
      True)

# Future: should NOT count
future_insights = [
    FakeInsight("Brazil is expected to win the 2026 FIFA World Cup.",
                ["src1", "src2"]),
]
check("completed_future_rejected",
      contains_completed_result(future_insights, current_year=2025),
      False)

# No year: should NOT count
no_year_insights = [
    FakeInsight("Someone won some championship.",
                ["src1", "src2"]),
]
check("completed_no_year",
      contains_completed_result(no_year_insights, current_year=2025),
      False)


# ── 7. Source Agreement Count ──────────────────────────────────────────────

print("\n=== 7. Source Agreement ===")

agreeing = [
    FakeInsight("Argentina won the 2022 World Cup.", ["src1", "src2"]),
    FakeInsight("Messi claimed the 2022 trophy.", ["src2", "src3"]),
]
check("agreement_count",
      count_agreeing_sources(agreeing, current_year=2025),
      3)  # src1, src2, src3


# ── 8. Drift Penalty ──────────────────────────────────────────────────────

print("\n=== 8. Drift Penalty ===")

# All future, no completed → strong penalty
all_future = [
    FakeInsight("The 2026 World Cup will take place in North America.", ["s1"]),
    FakeInsight("The upcoming 2026 tournament is being prepared.", ["s2"]),
]
penalty = compute_future_drift_penalty(all_future, QueryIntent.FACTUAL_EVENT_WINNER, 2025)
check("drift_strong_penalty",
      penalty >= 0.10,  # Softened threshold
      True)

# Mixed with completed result → mild penalty
mixed_resolved = [
    FakeInsight("Argentina won the 2022 World Cup.", ["s1", "s2"]),
    FakeInsight("The 2026 World Cup will be held in USA.", ["s3"]),
]
penalty2 = compute_future_drift_penalty(mixed_resolved, QueryIntent.FACTUAL_EVENT_WINNER, 2025)
check("drift_mild_penalty",
      penalty2 <= 0.05,
      True)

# Non-event intent → no penalty
penalty3 = compute_future_drift_penalty(all_future, QueryIntent.OTHER, 2025)
check("drift_no_penalty_other",
      penalty3,
      0.0)


# ── 9. Factual Refinement Query ───────────────────────────────────────────

print("\n=== 9. Refinement Queries ===")

ref = build_factual_refinement_query("FIFA World Cup")
check("refinement_basic",
      "FIFA World Cup" in ref and "winner" in ref,
      True)

ref_election = build_factual_refinement_query("Presidential Election",
                                                jurisdiction="US",
                                                is_election=True)
check("refinement_election",
      "US" in ref_election and "election" in ref_election.lower(),
      True)


# ── Summary ───────────────────────────────────────────────────────────────

print(f"\n{'='*50}")
print(f"TOTAL: {passed} passed, {failed} failed")
if failed > 0:
    sys.exit(1)
else:
    print("All tests passed!")
