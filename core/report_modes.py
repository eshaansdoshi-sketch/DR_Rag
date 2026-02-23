"""Report Mode Configuration — Deterministic presentation control.

Defines four report modes that control writer tone, section emphasis,
and formatting instructions. Affects presentation only — evaluation
logic and data pipeline are unchanged.

All presets are frozen and deterministic.
"""

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class ReportModePreset:
    """Immutable configuration for report presentation style."""

    name: str
    description: str
    prompt_instructions: str   # Injected into writer prompt


# ---------------------------------------------------------------------------
# Mode Definitions
# ---------------------------------------------------------------------------

EXECUTIVE_SUMMARY = ReportModePreset(
    name="executive_summary",
    description="High-level findings with risk and recommendation focus",
    prompt_instructions="""\
REPORT MODE: Executive Summary
- Write a concise, decision-oriented executive_summary (2-3 paragraphs).
  Focus on actionable findings, key risks, and strategic recommendations.
- Generate 3-4 structured_sections with high-level headings.
  Keep content brief and focused on business implications.
  Avoid technical depth — summarize conclusions, not methodology.
- Provide 2-4 risk_assessment items emphasizing business and strategic risks.
- Provide 2-4 recommendations that are actionable and prioritized.
- Tone: authoritative, concise, decision-grade.
- Minimize trace and methodology exposure.""",
)

TECHNICAL_WHITEPAPER = ReportModePreset(
    name="technical_whitepaper",
    description="Detailed insights with methodology and contradiction discussion",
    prompt_instructions="""\
REPORT MODE: Technical Whitepaper
- Write a thorough executive_summary (3-4 paragraphs) covering scope,
  methodology, key findings, and limitations.
- Generate 4-6 structured_sections covering:
  * Research methodology and approach
  * Detailed findings per subtopic with supporting evidence
  * Contradiction analysis and resolution
  * Confidence breakdown and data quality assessment
- Provide 3-5 risk_assessment items including methodological limitations,
  data gaps, and confidence caveats.
- Provide 3-5 recommendations with technical justification.
- Tone: analytical, detailed, evidence-dense.
- Include confidence scores and source quality discussion.""",
)

RISK_ASSESSMENT = ReportModePreset(
    name="risk_assessment",
    description="Emphasis on uncertainties, contradictions, and scenario analysis",
    prompt_instructions="""\
REPORT MODE: Risk Assessment
- Write an executive_summary (2-3 paragraphs) framed around uncertainty
  and risk landscape. Lead with what is NOT known or contested.
- Generate 3-5 structured_sections emphasizing:
  * Key uncertainties and knowledge gaps
  * Contradictions and conflicting evidence
  * Scenario analysis (best case, worst case, most likely)
  * Confidence limitations per subtopic
- Provide 4-6 risk_assessment items with severity framing.
  Prioritize risks by potential impact and likelihood.
- Provide 2-4 recommendations focused on risk mitigation and contingency.
- Tone: cautious, scenario-aware, risk-focused.
- Highlight every contradiction and data inconsistency.""",
)

ACADEMIC_STRUCTURED = ReportModePreset(
    name="academic_structured",
    description="Formal structure with explicit citations and methodology transparency",
    prompt_instructions="""\
REPORT MODE: Academic Structured Format
- Write an executive_summary (2-3 paragraphs) structured as an abstract:
  background, methods, results, and conclusion.
- Generate 4-6 structured_sections following academic convention:
  * Introduction and Research Questions
  * Methodology (search strategy, source selection, evaluation criteria)
  * Results and Analysis (organized by subtopic)
  * Discussion (synthesis, contradictions, limitations)
  * Conclusion
- Provide 2-4 risk_assessment items framed as study limitations.
- Provide 2-4 recommendations framed as implications and future research.
- Tone: formal, objective, citation-conscious.
- Reference supporting sources explicitly in each section's content.""",
)

# ---------------------------------------------------------------------------
# Lookup
# ---------------------------------------------------------------------------
REPORT_MODE_PRESETS: Dict[str, ReportModePreset] = {
    "executive_summary": EXECUTIVE_SUMMARY,
    "technical_whitepaper": TECHNICAL_WHITEPAPER,
    "risk_assessment": RISK_ASSESSMENT,
    "academic_structured": ACADEMIC_STRUCTURED,
}

DEFAULT_REPORT_MODE = "technical_whitepaper"


def get_report_mode(mode: str) -> ReportModePreset:
    """Return the report mode preset for the given name.

    Falls back to TECHNICAL_WHITEPAPER if mode is unrecognised.
    """
    return REPORT_MODE_PRESETS.get(mode, TECHNICAL_WHITEPAPER)
