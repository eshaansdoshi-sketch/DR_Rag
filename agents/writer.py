from typing import List

from pydantic import BaseModel, ConfigDict

from core.llm_client import LLMClient
from core.research_memory import ResearchMemory
from schemas import (
    EvaluationResult,
    FinalReport,
    ResearchPlan,
    ReportSection,
)
from schemas import Insight, Statistic, Contradiction

class ReportGenerationOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    executive_summary: str
    structured_sections: List[ReportSection]
    risk_assessment: List[str]
    recommendations: List[str]


class WriterAgent:
    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client

    def generate_report(
        self,
        plan: ResearchPlan,
        memory: ResearchMemory,
        evaluation: EvaluationResult
    ) -> FinalReport:
        references = self._collect_references(memory)
        
        prompt = self._build_report_prompt(plan, memory, evaluation)
        
        report_output = self.llm_client.generate_structured(
            prompt=prompt,
            response_model=ReportGenerationOutput,
            max_retries=1
        )
        
        final_report = FinalReport(
            executive_summary=report_output.executive_summary,
            structured_sections=report_output.structured_sections,
            risk_assessment=report_output.risk_assessment,
            recommendations=report_output.recommendations,
            references=references,
            confidence_score=evaluation.global_confidence,
            research_trace=memory.trace
        )
        
        return final_report

    def _collect_references(self, memory: ResearchMemory) -> List[str]:
        reference_urls = set()
        for source in memory.get_all_sources():
            reference_urls.add(str(source.url))
        return sorted(list(reference_urls))

    def _build_report_prompt(
        self,
        plan: ResearchPlan,
        memory: ResearchMemory,
        evaluation: EvaluationResult
    ) -> str:
        subtopic_names = ", ".join([s.name for s in plan.subtopics])
        
        insights_summary = self._group_insights_by_subtopic(memory.insights)
        statistics_summary = self._group_statistics_by_subtopic(memory.statistics)
        contradictions_summary = self._group_contradictions_by_subtopic(memory.contradictions)
        
        scores_summary = "\n".join([
            f"- {s.subtopic}: confidence={s.confidence:.2f}, status={s.status.value}"
            for s in evaluation.subtopic_scores
        ])
        
        prompt = f"""
You are a senior research consultant synthesizing a decision-grade research report.

RESEARCH OBJECTIVE:
{plan.research_objective}

SUBTOPICS RESEARCHED:
{subtopic_names}

KEY INSIGHTS EXTRACTED:
{insights_summary if insights_summary else "No insights extracted"}

STATISTICS FOUND:
{statistics_summary if statistics_summary else "No statistics found"}

CONTRADICTIONS IDENTIFIED:
{contradictions_summary if contradictions_summary else "No contradictions found"}

EVALUATION SCORES:
{scores_summary}

GLOBAL CONFIDENCE: {evaluation.global_confidence:.2f}

REPORT GENERATION TASK:
Using ONLY the above structured data:

1) Write a concise executive_summary (2-3 paragraphs) synthesizing key findings.
2) Generate 3-5 structured_sections with clear headings and evidence-based content.
3) Identify 2-4 risk_assessment items addressing limitations and uncertainties.
4) Provide 2-4 recommendations based on findings.

CONSTRAINTS:
- Do NOT invent new facts.
- Do NOT include sources or citations beyond what's provided.
- Focus on synthesis, not speculation.
- Keep tone formal and analytical.

STRICT OUTPUT RULES:
- Respond ONLY with valid JSON matching this EXACT structure.
- executive_summary must be a SINGLE STRING value (not a list).
- Do NOT wrap executive_summary in an array.
- Do NOT split paragraphs into multiple elements.
- Do NOT add extra fields.
- Do NOT include markdown.
- Do NOT include commentary.

{{
  "executive_summary": "string",
  "structured_sections": [
    {{
      "heading": "string",
      "content": "string",
      "supporting_sources": ["url1", "url2"]
    }}
  ],
  "risk_assessment": ["risk1 as string", "risk2 as string"],
  "recommendations": ["rec1 as string", "rec2 as string"]
}}
"""
        return prompt

    def _group_insights_by_subtopic(self, insights: List[Insight]) -> str:
        subtopic_insights = {}
        for insight in insights:
            if insight.subtopic not in subtopic_insights:
                subtopic_insights[insight.subtopic] = []
            subtopic_insights[insight.subtopic].append(insight)
        
        result_lines = []
        for subtopic in sorted(subtopic_insights.keys()):
            result_lines.append(f"\n{subtopic}:")
            for insight in subtopic_insights[subtopic][:3]:
                result_lines.append(f"  - {insight.statement} (confidence: {insight.confidence})")
            
            if len(subtopic_insights[subtopic]) > 3:
                result_lines.append(f"  ... and {len(subtopic_insights[subtopic]) - 3} more")
        
        return "\n".join(result_lines)

    def _group_statistics_by_subtopic(self, statistics: List[Statistic]) -> str:
        subtopic_statistics = {}
        for stat in statistics:
            if stat.subtopic not in subtopic_statistics:
                subtopic_statistics[stat.subtopic] = []
            subtopic_statistics[stat.subtopic].append(stat)
        
        result_lines = []
        for subtopic in sorted(subtopic_statistics.keys()):
            result_lines.append(f"\n{subtopic}:")
            for stat in subtopic_statistics[subtopic][:2]:
                result_lines.append(f"  - {stat.value}: {stat.context}")
            
            if len(subtopic_statistics[subtopic]) > 2:
                result_lines.append(f"  ... and {len(subtopic_statistics[subtopic]) - 2} more")
        
        return "\n".join(result_lines)

    def _group_contradictions_by_subtopic(self, contradictions: List[Contradiction]) -> str:
        subtopic_contradictions = {}
        for contra in contradictions:
            if contra.subtopic not in subtopic_contradictions:
                subtopic_contradictions[contra.subtopic] = []
            subtopic_contradictions[contra.subtopic].append(contra)
        
        result_lines = []
        for subtopic in sorted(subtopic_contradictions.keys()):
            result_lines.append(f"\n{subtopic}:")
            for contra in subtopic_contradictions[subtopic][:2]:
                result_lines.append(f"  - {contra.claim_a} vs {contra.claim_b} (severity: {contra.severity})")
            
            if len(subtopic_contradictions[subtopic]) > 2:
                result_lines.append(f"  ... and {len(subtopic_contradictions[subtopic]) - 2} more")
        
        return "\n".join(result_lines)
