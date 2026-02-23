"""Research Depth Configuration — Deterministic preset layer.

Defines three research depth modes that configure iteration behavior,
source acquisition intensity, and refinement strictness. Acts as a
parameter orchestration layer over existing controls — no logic duplication.

All presets are frozen, deterministic, and bounded.
"""

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class DepthPreset:
    """Immutable configuration preset for research depth."""

    name: str
    max_iterations: int
    confidence_threshold: float
    source_count_initial: int    # max_results for iteration-1 per-subtopic search
    source_count_refined: int    # max_results for refined query searches
    enable_contradiction_escalation: bool
    enable_subtopic_expansion: bool

    def to_trace_dict(self) -> Dict[str, object]:
        """Serialize preset for trace logging."""
        return {
            "depth_mode": self.name,
            "max_iterations": self.max_iterations,
            "confidence_threshold": self.confidence_threshold,
            "source_count_initial": self.source_count_initial,
            "source_count_refined": self.source_count_refined,
            "enable_contradiction_escalation": self.enable_contradiction_escalation,
            "enable_subtopic_expansion": self.enable_subtopic_expansion,
        }


# ---------------------------------------------------------------------------
# Presets (frozen, deterministic, reuse existing internal controls)
# ---------------------------------------------------------------------------

QUICK_SCAN = DepthPreset(
    name="quick_scan",
    max_iterations=1,
    confidence_threshold=0.55,
    source_count_initial=3,
    source_count_refined=2,
    enable_contradiction_escalation=False,
    enable_subtopic_expansion=False,
)

STANDARD = DepthPreset(
    name="standard",
    max_iterations=2,
    confidence_threshold=0.75,
    source_count_initial=5,
    source_count_refined=4,
    enable_contradiction_escalation=False,
    enable_subtopic_expansion=True,
)

DEEP_INVESTIGATION = DepthPreset(
    name="deep_investigation",
    max_iterations=4,
    confidence_threshold=0.85,
    source_count_initial=7,
    source_count_refined=5,
    enable_contradiction_escalation=True,
    enable_subtopic_expansion=True,
)

# ---------------------------------------------------------------------------
# Lookup
# ---------------------------------------------------------------------------
DEPTH_PRESETS: Dict[str, DepthPreset] = {
    "quick_scan": QUICK_SCAN,
    "standard": STANDARD,
    "deep_investigation": DEEP_INVESTIGATION,
}

DEFAULT_DEPTH_MODE = "standard"

# ---------------------------------------------------------------------------
# Confidence threshold bounds (user-controllable, clamped)
# ---------------------------------------------------------------------------
MIN_CONFIDENCE_THRESHOLD = 0.65
MAX_CONFIDENCE_THRESHOLD = 0.90

# ---------------------------------------------------------------------------
# Iteration cap bounds (user-controllable, clamped)
# ---------------------------------------------------------------------------
MIN_ITERATION_CAP = 1
MAX_ITERATION_CAP = 5


def clamp_iteration_cap(value: int) -> int:
    """Clamp a user-supplied iteration cap to safe bounds [1, 5]."""
    return max(MIN_ITERATION_CAP, min(MAX_ITERATION_CAP, int(value)))


def get_depth_preset(mode: str) -> DepthPreset:
    """Return the preset for the given mode name.

    Falls back to STANDARD if mode is unrecognised.
    """
    return DEPTH_PRESETS.get(mode, STANDARD)


def clamp_confidence_threshold(value: float) -> float:
    """Clamp a user-supplied confidence threshold to safe bounds [0.65, 0.90].

    Returns the clamped value, rounded to 4 decimal places.
    """
    clamped = max(MIN_CONFIDENCE_THRESHOLD, min(MAX_CONFIDENCE_THRESHOLD, value))
    return round(clamped, 4)


# ---------------------------------------------------------------------------
# Contradiction Sensitivity Presets
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ContradictionSensitivity:
    """Policy preset for contradiction reaction (not detection)."""

    name: str
    min_severity: float        # Only contradictions >= this affect confidence
    confidence_penalty: float  # Per-contradiction penalty on global confidence
    force_refinement: bool     # Whether any qualifying contradiction forces extra iteration


IGNORE_MINOR = ContradictionSensitivity(
    name="ignore_minor",
    min_severity=0.7,
    confidence_penalty=0.02,
    force_refinement=False,
)

FLAG_ALL = ContradictionSensitivity(
    name="flag_all",
    min_severity=0.0,
    confidence_penalty=0.03,
    force_refinement=False,
)

ESCALATE_ON_ANY = ContradictionSensitivity(
    name="escalate_on_any",
    min_severity=0.0,
    confidence_penalty=0.04,
    force_refinement=True,
)

CONTRADICTION_PRESETS: Dict[str, ContradictionSensitivity] = {
    "ignore_minor": IGNORE_MINOR,
    "flag_all": FLAG_ALL,
    "escalate_on_any": ESCALATE_ON_ANY,
}

DEFAULT_CONTRADICTION_MODE = "flag_all"


def get_contradiction_preset(mode: str) -> ContradictionSensitivity:
    """Return the contradiction sensitivity preset for the given mode.

    Falls back to FLAG_ALL if mode is unrecognised.
    """
    return CONTRADICTION_PRESETS.get(mode, FLAG_ALL)
