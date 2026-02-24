from typing import List, Tuple

import logging

from pydantic import BaseModel, ValidationError

from core.bias_detector import classify_insight_stance
from core.llm_client import LLMClient, StructuredOutputError
from schemas import (
    Contradiction,
    Insight,
    ResearchPlan,
    SourceMetadata,
    Statistic,
)

logger = logging.getLogger(__name__)

from pydantic import ConfigDict

class AnalysisOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    insights: List[Insight]
    statistics: List[Statistic]
    contradictions: List[Contradiction]


class AnalystAgent:
    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client

    def analyze(
        self,
        plan: ResearchPlan,
        sources: List[SourceMetadata]
    ) -> Tuple[List[Insight], List[Statistic], List[Contradiction]]:
        all_insights = []
        all_statistics = []
        all_contradictions = []
        
        for subtopic in plan.subtopics:
            prompt = self._build_analysis_prompt(subtopic.name, sources)
            
            try:
                analysis_output = self.llm_client.generate_structured(
                    prompt=prompt,
                    response_model=AnalysisOutput,
                    max_retries=1
                )
            except (StructuredOutputError, ValidationError) as e:
                logger.error(
                    "analyst_extraction_failed | subtopic=%s error=%s",
                    subtopic.name, e,
                )
                continue

            # Post-process: assign stance to each insight (rule-based, no LLM)
            for insight in analysis_output.insights:
                insight.stance = classify_insight_stance(insight.statement)
            
            all_insights.extend(analysis_output.insights)
            all_statistics.extend(analysis_output.statistics)
            all_contradictions.extend(analysis_output.contradictions)
        
        return all_insights, all_statistics, all_contradictions

    def analyze_subtopic(
        self,
        subtopic_name: str,
        sources: List[SourceMetadata],
    ) -> Tuple[List[Insight], List[Statistic], List[Contradiction]]:
        """Analyze a single subtopic against provided sources.

        Used by async runner for per-subtopic parallelism.
        """
        prompt = self._build_analysis_prompt(subtopic_name, sources)

        try:
            analysis_output = self.llm_client.generate_structured(
                prompt=prompt,
                response_model=AnalysisOutput,
                max_retries=1,
            )
        except (StructuredOutputError, ValidationError) as e:
            logger.error(
                "analyst_subtopic_extraction_failed | subtopic=%s error=%s",
                subtopic_name, e,
            )
            return ([], [], [])

        logger.info(
            "analyst_subtopic_complete | subtopic=%s insights=%d stats=%d",
            subtopic_name, len(analysis_output.insights),
            len(analysis_output.statistics),
        )

        for insight in analysis_output.insights:
            insight.stance = classify_insight_stance(insight.statement)
        return (
            analysis_output.insights,
            analysis_output.statistics,
            analysis_output.contradictions,
        )

    def _build_analysis_prompt(self, subtopic: str, sources: List[SourceMetadata]) -> str:
        sources_text = "\n".join([
            f"- Title: {s.title}\n  URL: {s.url}\n  Summary: {s.summary[:300]}"
            for s in sources
        ])
        
        prompt = f"""
You are a research analyst synthesizing evidence from multiple sources.

SUBTOPIC: {subtopic}

AVAILABLE SOURCES:
{sources_text}

ANALYSIS TASK:
From these sources, identify and extract information relevant to the subtopic:
1. Key insights (3–6 statements with confidence scores 0.0–1.0)
2. Quantitative statistics where available
3. Explicit contradictions between sources (if any)
   Assign severity as a float between 0.0 (minor) and 1.0 (critical).
   Only include a contradiction if both claims come from valid sources with real URLs.
   If no valid contradiction exists, return an empty list.

When extracting insights and statistics, only include supporting_sources and source_urls that are actually relevant to the subtopic.
If no relevant information exists for this subtopic, return empty lists.

STRICT OUTPUT RULES:
- Respond ONLY with valid JSON.
- Insights must have: subtopic, statement, supporting_sources (list of URLs), confidence
- Statistics must have: subtopic, value, context, source_url
- Contradictions must have: subtopic, claim_a, source_a, claim_b, source_b, severity
- Do NOT include explanations or markdown.
- severity must be a numeric value between 0.0 and 1.0.
- Do NOT use words like "low", "medium", or "high".
- severity must be a float (e.g., 0.2, 0.5, 0.9).
- source_a and source_b must be valid absolute URLs.
- Do NOT use placeholders like "Not found", "N/A", or empty strings.
- If a valid second source URL is not available, do NOT include the contradiction.
- Only include contradictions when both sources have valid URLs.
"""
        return prompt
