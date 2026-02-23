"""Research Orchestrator — Async-first execution engine.

run_async() is the canonical execution path containing all orchestration logic.
run() is a thin synchronous wrapper that calls asyncio.run(run_async(...)).

Within each iteration:
  Phase 1: Parallel search per subtopic/query (semaphore-bounded)
  Phase 2: Parallel analysis per subtopic with ALL sources (semaphore-bounded)
  Sequential: Memory merge → Evaluation → Trace → Stopping condition

Planning, evaluation, trace, and writing are always sequential.
"""

import asyncio
import logging
import uuid
from typing import List, Optional

from agents.planner import PlannerAgent, PlanManager
from agents.searcher import SearcherAgent
from agents.analyst import AnalystAgent
from agents.evaluator import EvaluatorAgent
from agents.writer import WriterAgent
from core.async_runner import (
    SubtopicResult,
    clamp_concurrent,
    execute_iteration,
)
from core.depth_config import (
    ContradictionSensitivity,
    DepthPreset,
    clamp_confidence_threshold,
    clamp_iteration_cap,
    get_contradiction_preset,
    get_depth_preset,
)
from core.evidence_strictness import (
    StrictnessPreset,
    StrictnessResult,
    check_strictness,
    get_strictness_preset,
)
from core.report_modes import ReportModePreset, get_report_mode
from core.research_memory import ResearchMemory
from core.structured_logger import EventType, log_event
from core.temporal import compute_temporal_distribution, detect_temporal_sensitivity
from core.token_budget import BudgetExceeded, TokenBudget
from schemas import (
    FinalReport,
    ResearchPlan,
    ResearchTraceEntry,
    SubtopicEvaluationStatus,
    SubtopicStatus,
    TerminationReason,
)

logger = logging.getLogger(__name__)


class Orchestrator:

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

    # ------------------------------------------------------------------
    # Sync entry point — thin wrapper
    # ------------------------------------------------------------------
    def run(
        self,
        query: str,
        depth_mode: str = "standard",
        confidence_threshold: float | None = None,
        contradiction_sensitivity: str = "flag_all",
        evidence_strictness: str = "moderate",
        max_iterations: int | None = None,
        report_mode: str = "technical_whitepaper",
        max_concurrent_tasks: int = 3,
        max_tokens_per_iteration: int | None = None,
        max_tokens_per_run: int | None = None,
        max_run_timeout: float = 300.0,
    ) -> FinalReport:
        """Synchronous entry point. Delegates to run_async() via asyncio.run()."""
        return asyncio.run(
            self.run_async(
                query=query,
                depth_mode=depth_mode,
                confidence_threshold=confidence_threshold,
                contradiction_sensitivity=contradiction_sensitivity,
                evidence_strictness=evidence_strictness,
                max_iterations=max_iterations,
                report_mode=report_mode,
                max_concurrent_tasks=max_concurrent_tasks,
                max_tokens_per_iteration=max_tokens_per_iteration,
                max_tokens_per_run=max_tokens_per_run,
                max_run_timeout=max_run_timeout,
            )
        )

    # ------------------------------------------------------------------
    # Async canonical execution path
    # ------------------------------------------------------------------
    async def run_async(
        self,
        query: str,
        depth_mode: str = "standard",
        confidence_threshold: float | None = None,
        contradiction_sensitivity: str = "flag_all",
        evidence_strictness: str = "moderate",
        max_iterations: int | None = None,
        report_mode: str = "technical_whitepaper",
        max_concurrent_tasks: int = 3,
        max_tokens_per_iteration: int | None = None,
        max_tokens_per_run: int | None = None,
        max_run_timeout: float = 300.0,
    ) -> FinalReport:
        """Canonical async execution path — single source of truth."""

        run_id = uuid.uuid4().hex[:12]

        # ── Resolve presets ───────────────────────────────────────────
        preset: DepthPreset = get_depth_preset(depth_mode)
        contradiction_preset: ContradictionSensitivity = get_contradiction_preset(
            contradiction_sensitivity
        )
        strictness_preset: StrictnessPreset = get_strictness_preset(
            evidence_strictness
        )
        report_preset: ReportModePreset = get_report_mode(report_mode)

        effective_threshold = (
            clamp_confidence_threshold(confidence_threshold)
            if confidence_threshold is not None
            else preset.confidence_threshold
        )
        effective_max_iterations = (
            clamp_iteration_cap(max_iterations)
            if max_iterations is not None
            else preset.max_iterations
        )
        effective_concurrent = clamp_concurrent(max_concurrent_tasks)

        # ── Token Budget ──────────────────────────────────────────────
        budget_kwargs = {}
        if max_tokens_per_iteration is not None:
            budget_kwargs["max_tokens_per_iteration"] = max_tokens_per_iteration
        if max_tokens_per_run is not None:
            budget_kwargs["max_tokens_per_run"] = max_tokens_per_run
        token_budget = TokenBudget(**budget_kwargs)

        # ── Planning (sequential) ─────────────────────────────────────
        plan = await asyncio.to_thread(self.planner.create_plan, query)
        memory = ResearchMemory()
        plan_manager = PlanManager()

        is_temporally_sensitive = detect_temporal_sensitivity(query)

        iteration = 1
        refined_queries: Optional[list] = None
        prev_confidence: float = 0.0
        budget_terminated: bool = False
        termination_reason = TerminationReason.unknown

        log_event(logger, logging.INFO, EventType.RUN_START,
                  f"Research run started: {query[:60]}",
                  run_id=run_id, depth_mode=preset.name,
                  max_iterations=effective_max_iterations,
                  max_concurrent=effective_concurrent,
                  timeout_s=max_run_timeout,
                  budget=token_budget.get_run_summary())

        # ── Timeout-guarded execution ─────────────────────────────────
        try:
            async with asyncio.timeout(max_run_timeout):
                # ── Main loop ─────────────────────────────────────────
                while iteration <= effective_max_iterations:
                    token_budget.set_iteration(iteration)

                    try:
                        # Build search queries for this iteration
                        if iteration == 1:
                            search_queries = [
                                (f"{plan.research_objective} - {st.name}", st.name)
                                for st in plan.subtopics
                            ]
                            max_results = preset.source_count_initial
                        elif refined_queries:
                            search_queries = [
                                (q, f"refined_{i}") for i, q in enumerate(refined_queries)
                            ]
                            max_results = preset.source_count_refined
                        else:
                            search_queries = []
                            max_results = preset.source_count_refined

                        # ── Parallel execution (Phase 1: search, Phase 2: analysis)
                        subtopic_results, all_new_sources = await execute_iteration(
                            searcher=self.searcher,
                            analyst=self.analyst,
                            search_queries=search_queries,
                            subtopics=plan.subtopics,
                            existing_sources=list(memory.sources.values()),
                            max_results=max_results,
                            max_concurrent=effective_concurrent,
                            run_id=run_id,
                            iteration=iteration,
                        )

                        # ── Sequential merge (critical section) ───────────
                        new_sources_count = memory.add_sources(all_new_sources)

                        for result in subtopic_results:
                            memory.add_insights(result.insights)
                            memory.add_statistics(result.statistics)
                            memory.add_contradictions(result.contradictions)
                            if result.error:
                                log_event(logger, logging.WARNING, EventType.SUBTOPIC_FAILURE,
                                          f"Subtopic failed: {result.subtopic_name}",
                                          run_id=run_id, iteration=iteration,
                                          subtopic=result.subtopic_name,
                                          error=result.error)

                        # ── Evaluation (sequential) ───────────────────────
                        evaluation = await asyncio.to_thread(
                            self.evaluator.evaluate,
                            plan=plan,
                            insights=memory.insights,
                            statistics=memory.statistics,
                            contradictions=memory.contradictions,
                            sources=all_new_sources,
                            is_temporally_sensitive=is_temporally_sensitive,
                            contradiction_sensitivity=contradiction_preset,
                        )

                        memory.add_evaluation(evaluation)

                        # ── Adaptive Plan Management ──────────────────────
                        added_names: List[str] = []
                        removed_names: List[str] = []

                        if preset.enable_subtopic_expansion:
                            added_names = plan_manager.spawn_subtopics(
                                plan=plan,
                                missing_aspects=evaluation.missing_aspects,
                                global_confidence=evaluation.global_confidence,
                                iteration=iteration,
                            )
                            removed_names = plan_manager.prune_subtopics(
                                plan=plan,
                                insights=memory.insights,
                                iteration=iteration,
                                prev_confidence=prev_confidence,
                                curr_confidence=evaluation.global_confidence,
                            )

                        planning_note = plan_manager.build_planning_note(added_names, removed_names)

                        # ── Evidence Strictness Check ─────────────────────
                        subtopic_names = [st.name for st in plan.subtopics]
                        strictness_result: StrictnessResult = check_strictness(
                            preset=strictness_preset,
                            insights=memory.insights,
                            statistics=memory.statistics,
                            sources=list(memory.sources.values()),
                            subtopic_names=subtopic_names,
                        )

                        # ── Trace Entry ───────────────────────────────────
                        temporal_dist = compute_temporal_distribution(all_new_sources)

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
                            new_sources_added=new_sources_count,
                            subtopics_added=added_names,
                            subtopics_removed=removed_names,
                            planning_note=planning_note,
                            is_temporally_sensitive=is_temporally_sensitive,
                            temporal_distribution=temporal_dist,
                            depth_mode=preset.name,
                            applied_confidence_threshold=effective_threshold,
                            contradiction_sensitivity=contradiction_preset.name,
                            evidence_strictness=strictness_preset.name,
                            strictness_satisfied=strictness_result.satisfied,
                            strictness_failures=strictness_result.failures,
                            configured_max_iterations=effective_max_iterations,
                            iteration_tokens=token_budget.iteration_total(iteration),
                            run_tokens_cumulative=token_budget.run_total,
                        )

                        memory.add_trace_entry(trace_entry)

                        # Track confidence for next iteration's pruning gate
                        prev_confidence = evaluation.global_confidence

                        if evaluation.global_confidence >= effective_threshold and strictness_result.satisfied:
                            termination_reason = TerminationReason.confidence_threshold_reached
                            break

                        if evaluation.plan_updates:
                            self._apply_plan_updates(plan, evaluation.plan_updates)

                        refined_queries = evaluation.refined_queries
                        iteration += 1

                    except BudgetExceeded as exc:
                        log_event(logger, logging.WARNING, EventType.BUDGET_EXCEEDED,
                                  str(exc), run_id=run_id, iteration=iteration,
                                  budget_type=exc.budget_type, limit=exc.limit,
                                  current=exc.current, requested=exc.requested)
                        budget_terminated = True
                        termination_reason = TerminationReason.token_budget_exceeded
                        break

                # If loop ended without break, max iterations reached
                if termination_reason == TerminationReason.unknown:
                    termination_reason = TerminationReason.max_iterations_reached

                # ── Writing (sequential) ──────────────────────────────
                final_report = await asyncio.to_thread(
                    self.writer.generate_report,
                    plan=plan,
                    memory=memory,
                    evaluation=memory.evaluations[-1],
                    report_mode=report_preset,
                )

                # Stamp termination reason onto the report
                final_report.termination_reason = termination_reason.value

                log_event(logger, logging.INFO, EventType.RUN_COMPLETE,
                          f"Research run completed: {termination_reason.value}",
                          run_id=run_id, iteration=iteration,
                          confidence=round(
                              memory.evaluations[-1].global_confidence if memory.evaluations else 0.0, 4),
                          termination_reason=termination_reason.value,
                          tokens=token_budget.get_run_summary())

                return final_report

        except TimeoutError:
            # ── Global timeout exceeded ───────────────────────────────
            log_event(logger, logging.ERROR, EventType.RUN_COMPLETE,
                      f"Run timed out after {max_run_timeout}s",
                      run_id=run_id, iteration=iteration,
                      termination_reason=TerminationReason.timeout_exceeded.value,
                      timeout_s=max_run_timeout)

            # Attempt partial report from whatever data we have
            try:
                partial_eval = memory.evaluations[-1] if memory.evaluations else None
                if partial_eval is not None:
                    final_report = await asyncio.to_thread(
                        self.writer.generate_report,
                        plan=plan, memory=memory,
                        evaluation=partial_eval, report_mode=report_preset,
                    )
                else:
                    # Minimal skeleton when no evaluation exists
                    final_report = FinalReport(
                        executive_summary=f"Research timed out after {max_run_timeout}s with {len(memory.insights)} insights collected.",
                        structured_sections=[{"heading": "Timeout", "content": "Run exceeded global timeout.", "supporting_sources": []}],
                        risk_assessment=["Run terminated due to timeout — results may be incomplete."],
                        recommendations=["Re-run with a longer timeout or fewer iterations."],
                        references=[],
                        confidence_score=0.0,
                        research_trace=[e.model_dump() for e in memory.trace_entries] if memory.trace_entries else [{"iteration": 0, "subtopic_confidences": {}, "global_confidence": 0.0, "weak_subtopics": [], "plan_updates": [], "source_count": 0, "subtopic_count": 0}],
                        report_mode=report_preset.name if hasattr(report_preset, 'name') else str(report_preset),
                    )
            except Exception:
                final_report = FinalReport(
                    executive_summary=f"Research timed out after {max_run_timeout}s. Partial report generation also failed.",
                    structured_sections=[{"heading": "Timeout", "content": "Run exceeded global timeout.", "supporting_sources": []}],
                    risk_assessment=["Run terminated due to timeout."],
                    recommendations=["Re-run with adjusted parameters."],
                    references=[],
                    confidence_score=0.0,
                    research_trace=[{"iteration": 0, "subtopic_confidences": {}, "global_confidence": 0.0, "weak_subtopics": [], "plan_updates": [], "source_count": 0, "subtopic_count": 0}],
                )

            final_report.termination_reason = TerminationReason.timeout_exceeded.value
            return final_report

    def _apply_plan_updates(self, plan: ResearchPlan, plan_updates: list) -> None:
        for update in plan_updates:
            update_lower = update.lower()
            for subtopic in plan.subtopics:
                if subtopic.name.lower() in update_lower:
                    subtopic.priority = 1
