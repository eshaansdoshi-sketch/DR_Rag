"""Bias Detection — Rule-based stance classification and heuristic opinion scoring.

Provides deterministic, lightweight text analysis for:
  1. Stance detection (pro / contra / neutral) via hedging, negation, and polarity
  2. Heuristic opinion/bias scoring via adjective density, emotional lexicon,
     modal verb count, and citation absence penalty

All functions are pure, numeric, and bounded [0.0, 1.0]. No LLM calls.
"""

import re
from typing import List, Literal


# ---------------------------------------------------------------------------
# Lexicons (deterministic, fixed)
# ---------------------------------------------------------------------------

# Hedging language — signals uncertainty / neutrality
_HEDGING_TERMS = [
    "might", "may", "could", "possibly", "perhaps", "arguably",
    "it seems", "appears to", "tends to", "likely", "unlikely",
    "suggest", "suggests", "suggested", "indicate", "indicates",
    "some experts", "some argue", "it is possible", "remains unclear",
    "debatable", "uncertain", "questionable", "preliminary",
]

# Strong claim markers — signals conviction / bias
_STRONG_CLAIM_TERMS = [
    "clearly", "obviously", "undeniably", "certainly", "definitely",
    "without question", "proven", "undoubtedly", "always", "never",
    "must", "absolutely", "inevitably", "unquestionably", "indisputably",
    "the fact is", "it is clear", "there is no doubt",
]

# Negation patterns for stance reversal detection
_NEGATION_PREFIXES = [
    "not ", "no ", "never ", "neither ", "nor ", "cannot ", "isn't ",
    "doesn't ", "don't ", "won't ", "wouldn't ", "shouldn't ", "hasn't ",
    "haven't ", "hadn't ", "wasn't ", "weren't ", "couldn't ",
]

# Polarity lexicon — positive and negative stance indicators
_POSITIVE_TERMS = [
    "benefit", "advantage", "improvement", "growth", "success",
    "effective", "efficient", "promising", "breakthrough", "innovation",
    "progress", "opportunity", "strength", "positive", "gain",
    "superior", "excellent", "remarkable", "significant achievement",
]

_NEGATIVE_TERMS = [
    "risk", "danger", "threat", "decline", "failure", "harmful",
    "ineffective", "problematic", "concern", "drawback", "weakness",
    "negative", "loss", "inferior", "deterioration", "crisis",
    "obstacle", "limitation", "adverse", "detrimental",
]

# Emotional lexicon — signals opinion over fact
_EMOTIONAL_TERMS = [
    "amazing", "terrible", "shocking", "alarming", "exciting",
    "horrifying", "incredible", "devastating", "wonderful", "tragic",
    "outrageous", "brilliant", "disastrous", "magnificent", "appalling",
    "stunning", "awful", "fantastic", "dreadful", "marvelous",
    "concerning", "disturbing", "inspiring", "disgraceful", "phenomenal",
]

# Modal verbs — high count signals subjective framing
_MODAL_VERBS = [
    "should", "would", "could", "might", "may", "must", "shall",
    "ought", "need to", "have to",
]

# Common adjective suffixes for density estimation
_ADJECTIVE_SUFFIXES = [
    "ous", "ive", "ful", "less", "able", "ible", "ical", "ial",
    "ent", "ant", "ing",
]


# ---------------------------------------------------------------------------
# 1. Stance Detection
# ---------------------------------------------------------------------------
def detect_stance(text: str) -> Literal["pro", "contra", "neutral"]:
    """Classify text stance as pro, contra, or neutral.

    Uses rule-based analysis:
      - Hedging vs strong claims
      - Negation pattern detection
      - Polarity lexicon scoring

    Returns one of: "pro", "contra", "neutral"
    """
    text_lower = text.lower()

    # Count polarity signals
    pos_count = sum(1 for term in _POSITIVE_TERMS if term in text_lower)
    neg_count = sum(1 for term in _NEGATIVE_TERMS if term in text_lower)

    # Negation can flip polarity — check for negated positive/negative terms
    negation_flips = 0
    for neg in _NEGATION_PREFIXES:
        for pos in _POSITIVE_TERMS:
            if f"{neg}{pos}" in text_lower:
                negation_flips += 1
        for n_term in _NEGATIVE_TERMS:
            if f"{neg}{n_term}" in text_lower:
                negation_flips -= 1  # Negated negative ≈ positive

    # Apply negation adjustments
    adjusted_pos = max(0, pos_count - negation_flips)
    adjusted_neg = max(0, neg_count + negation_flips)

    # Hedging raises neutrality threshold
    hedging_count = sum(1 for term in _HEDGING_TERMS if term in text_lower)
    strong_count = sum(1 for term in _STRONG_CLAIM_TERMS if term in text_lower)

    # If heavily hedged, bias toward neutral
    if hedging_count >= 2 and strong_count == 0:
        return "neutral"

    # Determine stance from adjusted polarity
    polarity_diff = adjusted_pos - adjusted_neg

    if polarity_diff >= 2:
        return "pro"
    elif polarity_diff <= -2:
        return "contra"
    elif polarity_diff == 1 and strong_count >= 1:
        return "pro"
    elif polarity_diff == -1 and strong_count >= 1:
        return "contra"
    else:
        return "neutral"


# ---------------------------------------------------------------------------
# 2. Heuristic Opinion / Bias Score
# ---------------------------------------------------------------------------
def compute_opinion_score(
    text: str,
    has_citations: bool = True,
) -> float:
    """Compute a heuristic opinion/bias score for a text passage.

    Score components (all bounded, weighted):
      - Adjective density        (0.0–1.0, weight 0.20)
      - Emotional lexicon hits   (0.0–1.0, weight 0.30)
      - Modal verb density       (0.0–1.0, weight 0.20)
      - Citation absence penalty (0.0–1.0, weight 0.15)
      - Strong claim density     (0.0–1.0, weight 0.15)

    Returns float in [0.0, 1.0]: 0.0 = factual, 1.0 = highly opinionated.
    """
    text_lower = text.lower()
    words = text_lower.split()
    word_count = max(len(words), 1)

    # ── Adjective density ────────────────────────────────────────────
    adj_count = sum(
        1 for w in words
        if any(w.endswith(suffix) for suffix in _ADJECTIVE_SUFFIXES)
    )
    adj_density = min(1.0, adj_count / word_count * 5)  # Scaled: ~20% adj → 1.0

    # ── Emotional lexicon hits ───────────────────────────────────────
    emotional_hits = sum(1 for term in _EMOTIONAL_TERMS if term in text_lower)
    emotional_score = min(1.0, emotional_hits / 3)  # 3+ hits → 1.0

    # ── Modal verb density ───────────────────────────────────────────
    modal_count = sum(1 for modal in _MODAL_VERBS if f" {modal} " in f" {text_lower} ")
    modal_density = min(1.0, modal_count / max(word_count / 20, 1))  # ~1 modal per 20 words → 1.0

    # ── Citation absence penalty ─────────────────────────────────────
    citation_penalty = 0.0 if has_citations else 1.0

    # ── Strong claim density ─────────────────────────────────────────
    strong_hits = sum(1 for term in _STRONG_CLAIM_TERMS if term in text_lower)
    strong_score = min(1.0, strong_hits / 2)  # 2+ strong claims → 1.0

    # ── Weighted combination ─────────────────────────────────────────
    opinion_score = (
        adj_density * 0.20
        + emotional_score * 0.30
        + modal_density * 0.20
        + citation_penalty * 0.15
        + strong_score * 0.15
    )

    return round(min(1.0, max(0.0, opinion_score)), 4)


# ---------------------------------------------------------------------------
# 3. Batch Processing Helpers
# ---------------------------------------------------------------------------
def classify_insight_stance(statement: str) -> Literal["pro", "contra", "neutral"]:
    """Classify the stance of a single insight statement."""
    return detect_stance(statement)


def score_source_bias(summary: str, has_citations: bool = True) -> float:
    """Score the opinion/bias level of a source based on its summary text."""
    return compute_opinion_score(summary, has_citations=has_citations)
