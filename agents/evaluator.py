from typing import List

from pydantic import BaseModel, ConfigDict

from core.depth_config import ContradictionSensitivity, FLAG_ALL
from core.event_filter import compute_future_drift_penalty, contains_completed_result
from core.llm_client import LLMClient
from core.query_intent import QueryIntent
from core.temporal import compute_recency_penalty, compute_temporal_distribution
from schemas import (
    Contradiction,
    DomainType,
    EvaluationResult,
    Insight,
    ResearchPlan,
    SourceMetadata,
    Statistic,
    SubtopicEvaluationStatus,
    SubtopicScore,
)


class QualitativeAnalysisOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    refined_queries: List[str]
    missing_aspects: List[str]
    plan_updates: List[str]


class EvaluatorAgent:
    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client
        self.domain_credibility = {
            DomainType.edu: 1.0,
            DomainType.gov: 1.0,
            DomainType.news: 0.7,
            DomainType.blog: 0.4,
            DomainType.other: 0.5,
        }

    def evaluate(
        self,
        plan: ResearchPlan,
        insights: List[Insight],
        statistics: List[Statistic],
        contradictions: List[Contradiction],
        sources: List[SourceMetadata],
        is_temporally_sensitive: bool = False,
        contradiction_sensitivity: ContradictionSensitivity = FLAG_ALL,
        query_intent: QueryIntent = QueryIntent.OTHER,
    ) -> EvaluationResult:
        subtopic_scores = []
        
        for subtopic in plan.subtopics:
            score = self._compute_subtopic_score(
                subtopic.name,
                insights,
                statistics,
                contradictions,
                sources
            )
            subtopic_scores.append(score)
        
        global_confidence = self._compute_global_confidence(subtopic_scores)
        
        # ── Soft temporal recency penalty (bounded, max 0.05) ────────
        # Skip for FACTUAL_EVENT_WINNER — recency bias is counterproductive
        recency_penalty = 0.0
        if query_intent != QueryIntent.FACTUAL_EVENT_WINNER:
            temporal_dist = compute_temporal_distribution(sources)
            recency_penalty = compute_recency_penalty(temporal_dist, is_temporally_sensitive)
            global_confidence = max(0.0, round(global_confidence - recency_penalty, 4))

        # ── Future-drift penalty for factual event queries ────────────
        drift_penalty = compute_future_drift_penalty(insights, query_intent)
        if drift_penalty > 0:
            global_confidence = max(0.0, round(global_confidence - drift_penalty, 4))

        # ── Contradiction sensitivity policy (affects reaction, not detection) ──
        qualifying = [
            c for c in contradictions
            if c.severity >= contradiction_sensitivity.min_severity
        ]
        if qualifying:
            penalty = len(qualifying) * contradiction_sensitivity.confidence_penalty
            penalty = min(penalty, 0.15)  # Hard cap to prevent runaway
            global_confidence = max(0.0, round(global_confidence - penalty, 4))

        contradiction_escalation = (
            contradiction_sensitivity.force_refinement and len(qualifying) > 0
        )
        
        # ── Factual confidence floor (FACTUAL_EVENT_WINNER) ───────────
        # Prevents structural metrics from crushing factoid resolution.
        # STRICTLY SCOPED — only applies to FACTUAL_EVENT_WINNER intent.
        confidence_floor_applied = False
        if query_intent == QueryIntent.FACTUAL_EVENT_WINNER and insights:
            has_completed = contains_completed_result(insights)
            has_contradictions = len(qualifying) > 0  # from contradiction check above
            has_source_url = any(
                getattr(i, 'supporting_sources', None)
                for i in insights
            )

            if has_completed and not has_contradictions and has_source_url:
                # Strong resolution with no contradictions → floor at 0.85
                if global_confidence < 0.85:
                    global_confidence = 0.85
                    confidence_floor_applied = True
            elif has_completed and has_contradictions:
                # Resolution found but contradictions exist → softer floor
                if global_confidence < 0.55:
                    global_confidence = 0.55
                    confidence_floor_applied = True
            elif not has_completed:
                # Insights exist but no resolution yet → floor at 0.55
                if global_confidence < 0.55:
                    global_confidence = 0.55
                    confidence_floor_applied = True

            # Zero-collapse guard: never 0.00 for factoid with insights
            if global_confidence < 0.20:
                global_confidence = 0.20
                confidence_floor_applied = True

        weak_subtopics = [s.subtopic for s in subtopic_scores if s.status == SubtopicEvaluationStatus.weak]
        
        qualitative_output = self._generate_qualitative_analysis(
            plan,
            subtopic_scores,
            weak_subtopics,
            insights,
            contradictions
        )
        
        # Inject recency gap signal for PlanManager spawning
        missing_aspects = list(qualitative_output.missing_aspects)
        if recency_penalty > 0:
            missing_aspects.append("Recent data or updated statistics missing.")
        
        # For FACTUAL_EVENT_WINNER, if resolution is found,
        # override needs_more_research to False.
        if (
            query_intent == QueryIntent.FACTUAL_EVENT_WINNER
            and insights
            and contains_completed_result(insights)
        ):
            needs_more = False
        else:
            needs_more = (
                global_confidence < 0.7
                or bool(weak_subtopics)
                or contradiction_escalation
            )

        evaluation = EvaluationResult(
            subtopic_scores=subtopic_scores,
            global_confidence=global_confidence,
            needs_more_research=needs_more,
            refined_queries=qualitative_output.refined_queries,
            missing_aspects=missing_aspects,
            plan_updates=qualitative_output.plan_updates,
            contradiction_escalation=contradiction_escalation,
        )
        
        return evaluation

    def _compute_subtopic_score(
        self,
        subtopic: str,
        insights: List[Insight],
        statistics: List[Statistic],
        contradictions: List[Contradiction],
        sources: List[SourceMetadata]
    ) -> SubtopicScore:
        subtopic_insights = [i for i in insights if i.subtopic == subtopic]
        subtopic_statistics = [s for s in statistics if s.subtopic == subtopic]
        subtopic_contradictions = [c for c in contradictions if c.subtopic == subtopic]
        
        supporting_urls = set()
        for insight in subtopic_insights:
            supporting_urls.update(insight.supporting_sources)
        
        subtopic_sources = [
            s for s in sources
            if str(s.url) in supporting_urls
        ]
        
        coverage = self._compute_coverage(len(subtopic_insights))
        credibility = self._compute_credibility(subtopic_sources)
        diversity = self._compute_diversity(subtopic_sources)
        evidence_strength = self._compute_evidence_strength(subtopic_insights, subtopic_statistics)
        consistency = self._compute_consistency(subtopic_contradictions)
        
        confidence = (
            coverage * 0.25 +
            credibility * 0.25 +
            diversity * 0.15 +
            evidence_strength * 0.20 +
            consistency * 0.15
        )
        
        status = (
            SubtopicEvaluationStatus.weak
            if confidence < 0.6
            else SubtopicEvaluationStatus.sufficient
        )
        
        return SubtopicScore(
            subtopic=subtopic,
            coverage=coverage,
            credibility=credibility,
            diversity=diversity,
            evidence_strength=evidence_strength,
            consistency=consistency,
            confidence=confidence,
            status=status
        )

    def _compute_coverage(self, insight_count: int) -> float:
        if insight_count >= 3:
            return min(1.0, 0.8 + (insight_count - 3) * 0.05)
        elif insight_count >= 1:
            return 0.5 + insight_count * 0.1
        else:
            return 0.1

    def _compute_credibility(self, sources: List[SourceMetadata]) -> float:
        if not sources:
            return 0.0
        
        total_credibility = sum(self.domain_credibility[s.domain_type] for s in sources)
        return total_credibility / len(sources)

    def _compute_diversity(self, sources: List[SourceMetadata]) -> float:
        if not sources:
            return 0.0
        
        domain_counts = {}
        for source in sources:
            domain = source.domain_type
            domain_counts[domain] = domain_counts.get(domain, 0) + 1
        
        max_count = max(domain_counts.values())
        diversity_ratio = max_count / len(sources)
        
        if diversity_ratio > 0.5:
            return max(0.0, 1.0 - (diversity_ratio - 0.5))
        else:
            return 1.0

    def _compute_evidence_strength(self, insights: List[Insight], statistics: List[Statistic]) -> float:
        if not insights:
            return 0.0
        
        score = 0.7
        
        sources_per_insight = [len(i.supporting_sources) for i in insights]
        if sources_per_insight:
            avg_sources = sum(sources_per_insight) / len(sources_per_insight)
            if avg_sources >= 2:
                score += 0.2
            elif avg_sources >= 1:
                score += 0.1
        
        if statistics:
            score += 0.1
        
        return min(1.0, score)

    def _compute_consistency(self, contradictions: List[Contradiction]) -> float:
        if not contradictions:
            return 1.0
        
        penalty = sum(c.severity for c in contradictions) / len(contradictions)
        return max(0.0, 1.0 - penalty)

    def _compute_global_confidence(self, subtopic_scores: List[SubtopicScore]) -> float:
        if not subtopic_scores:
            return 0.0
        
        avg_confidence = sum(s.confidence for s in subtopic_scores) / len(subtopic_scores)
        
        weak_count = sum(1 for s in subtopic_scores if s.confidence < 0.5)
        if weak_count > 0:
            penalty = weak_count * 0.05
            avg_confidence = max(0.0, avg_confidence - penalty)
        
        return min(1.0, avg_confidence)

    def _generate_qualitative_analysis(
        self,
        plan: ResearchPlan,
        subtopic_scores: List[SubtopicScore],
        weak_subtopics: List[str],
        insights: List[Insight],
        contradictions: List[Contradiction]
    ) -> QualitativeAnalysisOutput:
        subtopic_list = ", ".join([s.name for s in plan.subtopics])
        weak_list = ", ".join(weak_subtopics) if weak_subtopics else "None"
        
        prompt = f"""
You are a research evaluation expert performing gap analysis.

RESEARCH OBJECTIVE: {plan.research_objective}

SUBTOPICS: {subtopic_list}

WEAK SUBTOPICS (status == weak): {weak_list}

TOTAL INSIGHTS EXTRACTED: {len(insights)}
TOTAL CONTRADICTIONS FOUND: {len(contradictions)}

EVALUATION TASK:
Analyze the research completeness and gaps:

1) Generate 2-4 refined_queries to address weaknesses.
2) Identify 2-5 missing_aspects not covered by current sources.
3) Suggest 1-3 plan_updates for the research strategy.

Focus on:
- Filling gaps in weak subtopics.
- Addressing contradictions.
- Improving breadth and credibility.

STRICT OUTPUT RULES:
- Respond ONLY with valid JSON.
- refined_queries must be a list of plain strings.
- Each refined_query must be a single search query string.
- Do NOT return objects inside refined_queries.
- Do NOT include keys like "query", "type", or "description".
- missing_aspects must be a list of plain strings.
- plan_updates must be a list of plain strings.
- Do NOT add extra fields.
- Do NOT include markdown.
- Do NOT include commentary.
"""
        
        qualitative_output = self.llm_client.generate_structured(
            prompt=prompt,
            response_model=QualitativeAnalysisOutput,
            max_retries=1
        )
        
        return qualitative_output
