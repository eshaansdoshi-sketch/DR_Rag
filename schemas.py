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


class SubtopicEvaluationStatus(str, Enum):
    weak = "weak"
    sufficient = "sufficient"


class DomainType(str, Enum):
    edu = "edu"
    gov = "gov"
    news = "news"
    blog = "blog"
    other = "other"


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
    domain_type: DomainType = Field(..., description="Classification of domain type")
    author_present: bool = Field(..., description="Whether author information is present")
    opinion_score: Score = Field(..., description="Opinion vs fact score: 0.0=factual, 1.0=opinion")


class Insight(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subtopic: str = Field(..., description="Subtopic this insight belongs to")
    statement: str = Field(..., description="The insight statement")
    supporting_sources: List[str] = Field(..., description="List of source URLs supporting this insight")
    confidence: Score = Field(..., description="Confidence score for this insight")


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


class ResearchTraceEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    iteration: int = Field(..., ge=1, description="Research iteration number")
    subtopic_confidences: Dict[str, float] = Field(..., description="Confidence scores per subtopic")
    global_confidence: Score = Field(..., description="Global confidence at this iteration")
    weak_subtopics: List[str] = Field(..., description="Subtopics identified as weak")
    plan_updates: List[str] = Field(..., description="Plan updates made in this iteration")
    new_sources_added: int = Field(..., ge=0, description="Number of new sources added")

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