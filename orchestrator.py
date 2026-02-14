from typing import Optional

from agents.planner import PlannerAgent
from agents.searcher import SearcherAgent
from agents.analyst import AnalystAgent
from agents.evaluator import EvaluatorAgent
from agents.writer import WriterAgent
from core.research_memory import ResearchMemory
from schemas import (
    FinalReport,
    ResearchPlan,
    ResearchTraceEntry,
    SubtopicEvaluationStatus,
    SubtopicStatus,
)


class Orchestrator:
    MAX_ITERATIONS = 2
    CONFIDENCE_THRESHOLD = 0.75

    def __init__(
        self,
        planner: PlannerAgent,
        searcher: SearcherAgent,
        analyst: AnalystAgent,
        evaluator: EvaluatorAgent,
        writer: WriterAgent,
    ) -> None:
        self.planner = planner
        self.searcher = searcher
        self.analyst = analyst
        self.evaluator = evaluator
        self.writer = writer

    def run(self, query: str) -> FinalReport:
        plan = self.planner.create_plan(query)
        memory = ResearchMemory()
        
        iteration = 1
        refined_queries: Optional[list] = None
        
        while iteration <= self.MAX_ITERATIONS:
            sources = self.searcher.execute_search(
                plan=plan,
                iteration=iteration,
                refined_queries=refined_queries
            )
            
            new_sources_count = memory.add_sources(sources)
            
            insights, statistics, contradictions = self.analyst.analyze(
                plan=plan,
                sources=sources
            )
            
            memory.add_insights(insights)
            memory.add_statistics(statistics)
            memory.add_contradictions(contradictions)
            
            evaluation = self.evaluator.evaluate(
                plan=plan,
                insights=memory.insights,
                statistics=memory.statistics,
                contradictions=memory.contradictions,
                sources=sources
            )
            
            memory.add_evaluation(evaluation)
            
            trace_entry = ResearchTraceEntry(
                iteration=iteration,
                subtopic_confidences={
                    score.subtopic: score.confidence
                    for score in evaluation.subtopic_scores
                },
                global_confidence=evaluation.global_confidence,
                weak_subtopics=[
                    score.subtopic
                    for score in evaluation.subtopic_scores
                    if score.status == SubtopicEvaluationStatus.weak
                ],
                plan_updates=evaluation.plan_updates,
                new_sources_added=new_sources_count
            )
            
            memory.add_trace_entry(trace_entry)
            
            if evaluation.global_confidence >= self.CONFIDENCE_THRESHOLD:
                break
            
            if evaluation.plan_updates:
                self._apply_plan_updates(plan, evaluation.plan_updates)
            
            refined_queries = evaluation.refined_queries
            iteration += 1
        
        final_report = self.writer.generate_report(
            plan=plan,
            memory=memory,
            evaluation=memory.evaluations[-1]
        )
        
        return final_report

    def _apply_plan_updates(self, plan: ResearchPlan, plan_updates: list) -> None:
        for update in plan_updates:
            update_lower = update.lower()
            for subtopic in plan.subtopics:
                if subtopic.name.lower() in update_lower:
                    subtopic.priority = 1
