from enum import Enum
from typing import Annotated, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


Score = Annotated[float, Field(ge=0.0, le=1.0)]


class SubtopicStatus(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    sufficient = "sufficient"
    weak = "weak"
    complete = "complete"
    removed = "removed"


class SubtopicEvaluationStatus(str, Enum):
    weak = "weak"
    sufficient = "sufficient"


class DomainType(str, Enum):
    edu = "edu"
    gov = "gov"
    news = "news"
    blog = "blog"
    other = "other"


class TerminationReason(str, Enum):
    confidence_threshold_reached = "confidence_threshold_reached"
    max_iterations_reached = "max_iterations_reached"
    evidence_strictness_unsatisfied = "evidence_strictness_unsatisfied"
    token_budget_exceeded = "token_budget_exceeded"
    timeout_exceeded = "timeout_exceeded"
    manual_interrupt = "manual_interrupt"
    error_abort = "error_abort"
    unknown = "unknown"


class Subtopic(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="Name of the research subtopic")
    priority: int = Field(..., ge=1, le=3, description="Priority level: 1=high, 2=medium, 3=low")
    status: SubtopicStatus = Field(..., description="Current research status of this subtopic")


class ResearchPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    research_objective: str = Field(..., description="Primary research objective")
    subtopics: List[Subtopic] = Field(..., min_length=1, description="List of research subtopics to investigate")
    key_questions: List[str] = Field(..., description="Critical questions to answer")
    metrics_required: List[str] = Field(..., description="Metrics needed for evaluation")


class SourceMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., description="Title of the source document")
    url: HttpUrl = Field(..., description="URL of the source")
    summary: str = Field(..., description="Brief summary of the source content")
    publication_date: Optional[str] = Field(None, description="Publication date if available")
    publication_year: Optional[int] = Field(None, description="Extracted publication year (derived from publication_date)")
    domain_type: DomainType = Field(..., description="Classification of domain type")
    author_present: bool = Field(..., description="Whether author information is present")
    opinion_score: Score = Field(..., description="Opinion vs fact score: 0.0=factual, 1.0=opinion")


class Insight(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subtopic: str = Field(..., description="Subtopic this insight belongs to")
    statement: str = Field(..., description="The insight statement")
    supporting_sources: List[str] = Field(..., description="List of source URLs supporting this insight")
    confidence: Score = Field(..., description="Confidence score for this insight")
    stance: str = Field(default="neutral", description="Detected stance: pro, contra, or neutral")


class Statistic(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subtopic: str = Field(..., description="Subtopic this statistic belongs to")
    value: Union[str, int, float] = Field(...,description="The statistical value or metric (can be string, int, or float)")
    context: str = Field(..., description="Context explaining the statistic")
    source_url: HttpUrl = Field(..., description="URL of the source for this statistic")


class Contradiction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subtopic: str = Field(..., description="Subtopic where contradiction was found")
    claim_a: str = Field(..., description="First contradicting claim")
    source_a: HttpUrl = Field(..., description="Source URL for first claim")
    claim_b: str = Field(..., description="Second contradicting claim")
    source_b: HttpUrl = Field(..., description="Source URL for second claim")
    severity: Score = Field(..., description="Severity of contradiction: 0.0=minor, 1.0=critical")


class SubtopicScore(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subtopic: str = Field(..., description="Name of the subtopic being scored")
    coverage: Score = Field(..., description="How well the subtopic is covered")
    credibility: Score = Field(..., description="Average credibility of sources")
    diversity: Score = Field(..., description="Diversity of perspectives and sources")
    evidence_strength: Score = Field(..., description="Strength of supporting evidence")
    consistency: Score = Field(..., description="Consistency across sources")
    confidence: Score = Field(..., description="Overall confidence in subtopic research")
    status: SubtopicEvaluationStatus = Field(..., description="Evaluation status of this subtopic")


class EvaluationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subtopic_scores: List[SubtopicScore] = Field(..., min_length=1, description="Detailed scores for each subtopic")
    global_confidence: Score = Field(..., description="Overall research confidence score")
    needs_more_research: bool = Field(..., description="Whether additional research is required")
    refined_queries: List[str] = Field(..., description="Refined search queries for next iteration")
    missing_aspects: List[str] = Field(..., description="Aspects that need more coverage")
    plan_updates: List[str] = Field(..., description="Suggested updates to research plan")
    contradiction_escalation: bool = Field(default=False, description="Whether contradictions triggered forced refinement")


class ResearchTraceEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    iteration: int = Field(..., ge=1, description="Research iteration number")
    subtopic_confidences: Dict[str, float] = Field(..., description="Confidence scores per subtopic")
    global_confidence: Score = Field(..., description="Global confidence at this iteration")
    weak_subtopics: List[str] = Field(..., description="Subtopics identified as weak")
    plan_updates: List[str] = Field(..., description="Plan updates made in this iteration")
    new_sources_added: int = Field(..., ge=0, description="Number of new sources added")
    subtopics_added: List[str] = Field(default_factory=list, description="Subtopics dynamically added in this iteration")
    subtopics_removed: List[str] = Field(default_factory=list, description="Subtopics pruned in this iteration")
    planning_note: str = Field(default="", description="Explanation of structural plan changes")
    is_temporally_sensitive: bool = Field(default=False, description="Whether the query was detected as time-sensitive")
    temporal_distribution: Dict[str, int] = Field(default_factory=dict, description="Source temporal distribution counts")
    depth_mode: str = Field(default="standard", description="Research depth mode active during this iteration")
    applied_confidence_threshold: float = Field(default=0.75, description="Effective confidence threshold used for stopping")
    contradiction_sensitivity: str = Field(default="flag_all", description="Contradiction sensitivity mode active during this iteration")
    evidence_strictness: str = Field(default="moderate", description="Evidence strictness level active during this iteration")
    strictness_satisfied: bool = Field(default=True, description="Whether evidence strictness constraints were met")
    strictness_failures: List[str] = Field(default_factory=list, description="Evidence strictness constraint failures")
    configured_max_iterations: int = Field(default=2, description="Effective iteration cap for this run")
    iteration_tokens: int = Field(default=0, description="Total tokens consumed in this iteration")
    run_tokens_cumulative: int = Field(default=0, description="Cumulative tokens consumed up to this iteration")

    # Event Completion Intent Recognition fields
    query_intent: str = Field(default="OTHER", description="Detected query intent classification")
    future_event_rejections: int = Field(default=0, description="Number of future-event insights rejected")
    factual_resolution_success: bool = Field(default=True, description="Whether factual event resolution succeeded")
    detected_event_name: str = Field(default="", description="Canonical name of detected recurring event")
    detected_event_year: Optional[int] = Field(default=None, description="Explicit year extracted from query")
    resolution_iteration: Optional[int] = Field(default=None, description="Iteration where factual resolution was achieved")
    agreement_count: int = Field(default=0, description="Number of sources agreeing on event winner")
    fallback_rescue_count: int = Field(default=0, description="Number of insights rescued by deterministic fallback extractor")
    confidence_floor_applied: bool = Field(default=False, description="Whether a factual confidence floor overrode natural scoring")

    @field_validator("subtopic_confidences")
    @classmethod
    def validate_confidence_scores(cls, v: Dict[str, float]) -> Dict[str, float]:
        for subtopic, score in v.items():
            if not 0.0 <= score <= 1.0:
                raise ValueError(f"Confidence score for {subtopic} must be between 0.0 and 1.0")
        return v


class ReportSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    heading: str = Field(..., description="Section heading")
    content: str = Field(..., description="Section content")
    supporting_sources: List[str] = Field(..., description="Source URLs supporting this section")


class FinalReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    executive_summary: str = Field(..., description="Executive summary of research findings")
    structured_sections: List[ReportSection] = Field(..., min_length=1, description="Structured report sections")
    risk_assessment: List[str] = Field(..., description="Identified risks and limitations")
    recommendations: List[str] = Field(..., description="Actionable recommendations")
    references: List[str] = Field(..., description="Complete list of references")
    confidence_score: Score = Field(..., description="Overall report confidence score")
    research_trace: List[ResearchTraceEntry] = Field(..., min_length=1, description="Complete research iteration trace")
    report_mode: str = Field(default="technical_whitepaper", description="Report presentation mode used")
    termination_reason: str = Field(default="unknown", description="Explicit reason the run terminated")