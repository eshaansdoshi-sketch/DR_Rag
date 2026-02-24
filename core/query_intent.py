"""Query Intent Classifier — Deterministic, rule-based intent detection.

Classifies queries into semantic intent categories to enable
lifecycle-aware factual resolution.  All logic is pure string-pattern
matching; no LLM calls, no embeddings, no external APIs.

Key design choices
──────────────────
• Fail-open:  winner signal alone → still FACTUAL_EVENT_WINNER.
• Recency modifier is *optional* — explicit year or event noun suffices.
• Word-boundary-safe matching via regex (avoids "open source" → tennis Open).
• Reformulation only when recency modifier present AND no explicit year.
"""

import re
from datetime import datetime
from enum import Enum
from typing import Optional, Tuple


# ── Intent enum ────────────────────────────────────────────────────────────

class QueryIntent(str, Enum):
    FACTUAL_EVENT_WINNER = "FACTUAL_EVENT_WINNER"
    FACTUAL_ENTITY_LOOKUP = "FACTUAL_ENTITY_LOOKUP"
    TREND_ANALYSIS = "TREND_ANALYSIS"
    OPEN_RESEARCH = "OPEN_RESEARCH"
    TEMPORAL_RECENT_INFO = "TEMPORAL_RECENT_INFO"
    OTHER = "OTHER"


# ── Signal groups ──────────────────────────────────────────────────────────

# Winner-action signals (word-boundary)
_WINNER_SIGNALS = [
    r"\bwho\s+won\b",
    r"\bwinner\b",
    r"\bchampion(?:s)?\b",
    r"\bwho\s+is\s+the\s+champion\b",
    r"\bwho\s+claimed\b",
    r"\bwho\s+secured\b",
    r"\bwho\s+defeated\b",
    r"\bmedal(?:ist|lists?)?\b",
    r"\bgold\s+medal\b",
]
_WINNER_RE = re.compile("|".join(_WINNER_SIGNALS), re.IGNORECASE)

# Recency modifiers
_RECENCY_SIGNALS = [
    r"\blast\b",
    r"\blatest\b",
    r"\bmost\s+recent\b",
    r"\bcurrent\b",
    r"\breigning\b",
    r"\bdefending\b",
]
_RECENCY_RE = re.compile("|".join(_RECENCY_SIGNALS), re.IGNORECASE)

# Recurring event nouns — word-boundary-safe regex patterns
# Each entry is (regex_pattern, canonical_name)
_EVENT_PATTERNS: list[Tuple[str, str]] = [
    # Football / Soccer
    (r"\bfifa\s+world\s+cup\b", "FIFA World Cup"),
    (r"\bworld\s+cup\b", "World Cup"),
    (r"\bchampions\s+league\b", "Champions League"),
    (r"\beuropean\s+championship\b", "European Championship"),
    (r"\beuro(?:s)?\s+\d{4}\b", "European Championship"),
    (r"\bcopa\s+america\b", "Copa America"),
    (r"\bpremier\s+league\b", "Premier League"),
    (r"\bla\s+liga\b", "La Liga"),
    (r"\bbundesliga\b", "Bundesliga"),
    (r"\bserie\s+a\b", "Serie A"),
    # Olympics
    (r"\bolympic(?:s|games)?\b", "Olympics"),
    (r"\bwinter\s+olympics\b", "Winter Olympics"),
    (r"\bsummer\s+olympics\b", "Summer Olympics"),
    (r"\bparalympic(?:s|games)?\b", "Paralympics"),
    # US Sports
    (r"\bsuper\s+bowl\b", "Super Bowl"),
    (r"\bnba\s+finals?\b", "NBA Finals"),
    (r"\bnba\s+championship\b", "NBA Championship"),
    (r"\bworld\s+series\b", "World Series"),
    (r"\bstanley\s+cup\b", "Stanley Cup"),
    (r"\bmarch\s+madness\b", "March Madness"),
    # Tennis
    (r"\bwimbledon\b", "Wimbledon"),
    (r"\bus\s+open\b", "US Open"),
    (r"\bfrench\s+open\b", "French Open"),
    (r"\baustralian\s+open\b", "Australian Open"),
    (r"\brolland?\s+garros\b", "French Open"),
    (r"\bgrand\s+slam\b", "Grand Slam"),
    # Motorsport
    (r"\bgrand\s+prix\b", "Grand Prix"),
    (r"\bformula\s+(?:1|one)\b", "Formula 1"),
    (r"\bf1\s+championship\b", "Formula 1"),
    (r"\bindy\s*500\b", "Indy 500"),
    (r"\ble\s+mans\b", "Le Mans"),
    # Cricket
    (r"\bcricket\s+world\s+cup\b", "Cricket World Cup"),
    (r"\bipl\b", "IPL"),
    (r"\bashes\b", "The Ashes"),
    (r"\bt20\s+world\s+cup\b", "T20 World Cup"),
    # Awards / Prizes
    (r"\bnobel\s+prize\b", "Nobel Prize"),
    (r"\bnobel\b", "Nobel Prize"),
    (r"\boscar(?:s)?\b", "Oscars"),
    (r"\bacademy\s+awards?\b", "Academy Awards"),
    (r"\bgolden\s+globe(?:s)?\b", "Golden Globes"),
    (r"\bgrammy(?:s|awards?)?\b", "Grammy Awards"),
    (r"\bemmy(?:s|awards?)?\b", "Emmy Awards"),
    (r"\bballon\s+d.?or\b", "Ballon d'Or"),
    (r"\bpulitzer\b", "Pulitzer Prize"),
    (r"\bbooker\s+prize\b", "Booker Prize"),
    (r"\bfields\s+medal\b", "Fields Medal"),
    (r"\bturing\s+award\b", "Turing Award"),
    # Elections / Politics
    (r"\bpresidential\s+election\b", "Presidential Election"),
    (r"\bgeneral\s+election\b", "General Election"),
    (r"\belection\b", "Election"),
    (r"\bprime\s+minister\b", "Election"),
    # Generic sport championships (last — low priority fallback)
    (r"\bchampionship\b", "Championship"),
]
_EVENT_COMPILED = [(re.compile(pat, re.IGNORECASE), name) for pat, name in _EVENT_PATTERNS]

# Trend terms (for TREND_ANALYSIS classification)
_TREND_TERMS = [
    r"\btrend(?:s|ing)?\b",
    r"\bgrowth\s+rate\b",
    r"\bmarket\s+size\b",
    r"\bregulation\s+change(?:s)?\b",
    r"\bemerging\b",
    r"\bviewership\b",
    r"\bpopularity\b",
    r"\bstatistic(?:s)?\b",
    r"\banalysis\b",
    r"\bimpact\b",
    r"\bhistory\s+of\b",
    r"\bevolution\s+of\b",
]
_TREND_RE = re.compile("|".join(_TREND_TERMS), re.IGNORECASE)

# Present-tense qualifiers (required alongside trend terms)
_PRESENT_QUALIFIERS_RE = re.compile(
    r"\bcurrent\b|\brecent\b|\blatest\b|\btoday\b|\bnow\b|\bthis\s+year\b",
    re.IGNORECASE,
)

# Year extraction
_YEAR_RE = re.compile(r"\b((?:19|20)\d{2})\b")

# Election-related jurisdiction hints
_JURISDICTION_TERMS = [
    r"\bus\b", r"\bu\.s\.\b", r"\bunited\s+states\b", r"\bamerican\b",
    r"\buk\b", r"\bu\.k\.\b", r"\bbritish\b", r"\bindia(?:n)?\b",
    r"\bfrench\b", r"\bfrance\b", r"\bgerman(?:y)?\b",
    r"\bbrazil(?:ian)?\b", r"\bcanad(?:a|ian)\b", r"\baustrali(?:a|an)\b",
    r"\bmexico\b", r"\bmexican\b", r"\bnigeria(?:n)?\b",
    r"\bjapan(?:ese)?\b", r"\bsouth\s+korea(?:n)?\b",
    r"\bresidential\b", r"\bcongressional\b", r"\bparliamentary\b",
    r"\bmidterm\b", r"\bstate\b", r"\bfederal\b",
]
_JURISDICTION_RE = re.compile("|".join(_JURISDICTION_TERMS), re.IGNORECASE)


# ── Public API ─────────────────────────────────────────────────────────────

def detect_query_intent(query: str) -> QueryIntent:
    """Classify query intent using deterministic string-pattern rules.

    Classification priority (first match wins):
      1. TREND_ANALYSIS  — trend term + present qualifier
      2. FACTUAL_EVENT_WINNER — winner signal + (event noun OR explicit year)
         Also: winner signal alone → fail-open to FACTUAL_EVENT_WINNER
      3. OTHER
    """
    q = query.strip()
    q_lower = q.lower()

    # ── 1. TREND_ANALYSIS takes priority over event-winner ────────────
    #    This prevents "latest trends in FIFA World Cup viewership"
    #    from being misclassified as FACTUAL_EVENT_WINNER.
    has_trend = bool(_TREND_RE.search(q_lower))
    if has_trend:
        has_present = bool(_PRESENT_QUALIFIERS_RE.search(q_lower))
        has_recency = bool(_RECENCY_RE.search(q_lower))
        if has_present or has_recency:
            return QueryIntent.TREND_ANALYSIS

    # ── 2. FACTUAL_EVENT_WINNER ───────────────────────────────────────
    has_winner = bool(_WINNER_RE.search(q_lower))
    if has_winner:
        event_name = extract_event_name(q)
        explicit_year = extract_event_year(q)

        # Winner signal + (event noun OR explicit year) → classify
        if event_name is not None or explicit_year is not None:
            return QueryIntent.FACTUAL_EVENT_WINNER

        # Fail-open: winner signal alone → still classify
        return QueryIntent.FACTUAL_EVENT_WINNER

    # ── 3. Fallback ───────────────────────────────────────────────────
    return QueryIntent.OTHER


def extract_event_name(query: str) -> Optional[str]:
    """Extract the canonical recurring-event name from the query.

    Uses word-boundary regex matching against known event patterns.
    Returns the canonical name of the first match, or None.
    """
    for pattern, canonical in _EVENT_COMPILED:
        if pattern.search(query):
            return canonical
    return None


def extract_event_year(query: str) -> Optional[int]:
    """Extract an explicit 4-digit year from the query.

    Returns the first year found in range [1900, 2099], or None.
    """
    match = _YEAR_RE.search(query)
    if match:
        return int(match.group(1))
    return None


def has_recency_modifier(query: str) -> bool:
    """Check if the query contains a recency modifier like 'last', 'latest'."""
    return bool(_RECENCY_RE.search(query))


def is_election_query(query: str) -> bool:
    """Check if the query is about an election / political event."""
    q_lower = query.lower()
    election_re = re.compile(
        r"\belection\b|\bpresidential\b|\bprime\s+minister\b|\bvot(?:e|ing|ed)\b",
        re.IGNORECASE,
    )
    return bool(election_re.search(q_lower))


def extract_jurisdiction(query: str) -> Optional[str]:
    """Extract jurisdiction / country hint from an election query."""
    match = _JURISDICTION_RE.search(query)
    return match.group(0) if match else None


def reformulate_event_query(query: str, intent: QueryIntent) -> Optional[str]:
    """Reformulate query for completed-event retrieval.

    Rules:
    • Only reformulate if intent == FACTUAL_EVENT_WINNER
    • Only reformulate if recency modifier is present AND no explicit year
    • If explicit year is in the query → preserve user specificity, no change
    • Election queries get jurisdiction-aware reformulation

    Returns reformulated query string, or None if no reformulation needed.
    """
    if intent != QueryIntent.FACTUAL_EVENT_WINNER:
        return None

    explicit_year = extract_event_year(query)
    if explicit_year is not None:
        # User specified a year — do not reformulate
        return None

    if not has_recency_modifier(query):
        # No recency modifier and no year — no reformulation needed
        return None

    # Extract event name for targeted reformulation
    event_name = extract_event_name(query)
    if event_name is None:
        # Fallback: cannot identify event, skip reformulation
        return None

    # Election-specific reformulation
    if is_election_query(query):
        jurisdiction = extract_jurisdiction(query)
        if jurisdiction:
            return f"most recent completed {jurisdiction} {event_name} winner result"
        return f"most recent completed {event_name} winner result"

    # General event reformulation
    return f"{event_name} most recent winner result completed"
