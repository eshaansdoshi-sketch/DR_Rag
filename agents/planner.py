from typing import List, Set

from core.llm_client import LLMClient
from schemas import Insight, ResearchPlan, Subtopic, SubtopicStatus


class PlannerAgent:
    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client

    def create_plan(self, query: str) -> ResearchPlan:
        prompt = f"""
You are a senior research strategist designing a structured research plan.

USER QUERY:
{query}

OBJECTIVE:
Decompose the query into a rigorous, breadth-first research plan.

PLANNING RULES:
- Provide 4 to 6 distinct subtopics.
- Ensure breadth-first coverage (overview, technical, economic, risks, future outlook, etc.).
- Avoid overly narrow or overly deep decomposition.
- Subtopics must be mutually distinct and non-overlapping.
- Set ALL subtopic statuses to "pending".
- Priority must be:
    1 = high importance
    2 = medium importance
    3 = lower importance

ANALYTICAL REQUIREMENTS:
- Provide 5 to 8 key_questions.
- Provide 3 to 5 measurable metrics_required.
- Research objective must restate the user's goal clearly and formally.

STRICT OUTPUT RULES:
- Respond ONLY with valid JSON.
- Field names must EXACTLY match the ResearchPlan schema.
- Use snake_case field names.
- Do NOT use camelCase.
- Do NOT add extra fields.
- Do NOT rename fields.
- Do NOT include "id", "description", or "importance".
- Subtopics must contain ONLY:
    {{
      "name": "string",
      "priority": 1,
      "status": "pending"
    }}
- research_objective must be a STRING (not an object).
- Do NOT include markdown.
- Do NOT include commentary.

EXPECTED STRUCTURE:

{{
  "research_objective": "string",
  "subtopics": [
    {{
      "name": "string",
      "priority": 1,
      "status": "pending"
    }}
  ],
  "key_questions": ["string"],
  "metrics_required": ["string"]
}}
"""
        
        research_plan = self.llm_client.generate_structured(
            prompt=prompt,
            response_model=ResearchPlan,
            max_retries=1
        )
        
        return research_plan


class PlanManager:
    """Constrained adaptive breadth-first plan manager.

    Handles evaluator-guided subtopic expansion and safe pruning
    while enforcing determinism, bounded growth, oscillation prevention,
    and full trace transparency.
    """

    # ── Hard Safety Constants ──────────────────────────────────────────
    MAX_TOTAL_SUBTOPICS = 10        # Global cap on active subtopics
    MAX_SPAWNS_PER_ITERATION = 2    # Max new subtopics per iteration
    MAX_PRUNES_PER_ITERATION = 2    # Max removals per iteration
    MIN_ACTIVE_SUBTOPICS = 3        # Floor — never prune below this
    MIN_NAME_LENGTH = 5             # Reject vague / too-short names
    EXPANSION_CONFIDENCE_CEILING = 0.85  # Don't expand if confidence >= this

    def __init__(self) -> None:
        self.removed_history: Set[str] = set()  # Normalized names, oscillation prevention

    # ── Public API ─────────────────────────────────────────────────────

    def spawn_subtopics(
        self,
        plan: ResearchPlan,
        missing_aspects: List[str],
        global_confidence: float,
        iteration: int,
    ) -> List[str]:
        """Add new subtopics from evaluator-identified missing aspects.

        Returns list of subtopic names actually added.
        """
        # Gate: never expand on first iteration (let initial plan run)
        if iteration <= 1:
            return []

        # Gate: don't expand if research is already strong
        if global_confidence >= self.EXPANSION_CONFIDENCE_CEILING:
            return []

        active_count = self._count_active(plan)

        # Gate: already at capacity
        if active_count >= self.MAX_TOTAL_SUBTOPICS:
            return []

        slots_available = min(
            self.MAX_SPAWNS_PER_ITERATION,
            self.MAX_TOTAL_SUBTOPICS - active_count,
        )

        added: List[str] = []

        for aspect in missing_aspects:
            if len(added) >= slots_available:
                break

            aspect_clean = aspect.strip()

            # Reject vague / too-short names
            if len(aspect_clean) < self.MIN_NAME_LENGTH:
                continue

            # Reject duplicates or strong overlaps with existing subtopics
            if self._is_duplicate(aspect_clean, plan.subtopics):
                continue

            # Oscillation prevention: don't re-add previously removed subtopics
            if self._was_previously_removed(aspect_clean):
                continue

            new_subtopic = Subtopic(
                name=aspect_clean,
                priority=1,
                status=SubtopicStatus.pending,
            )
            plan.subtopics.append(new_subtopic)
            added.append(aspect_clean)

        return added

    def prune_subtopics(
        self,
        plan: ResearchPlan,
        insights: List[Insight],
        iteration: int,
        prev_confidence: float,
        curr_confidence: float,
    ) -> List[str]:
        """Remove subtopics that consistently produce no insights.

        Returns list of subtopic names actually removed.
        """
        # Gate: never prune on the first iteration
        if iteration <= 1:
            return []

        # Gate: don't prune if confidence is improving
        if curr_confidence > prev_confidence:
            return []

        active_count = self._count_active(plan)

        # Gate: don't prune below the minimum floor
        if active_count <= self.MIN_ACTIVE_SUBTOPICS:
            return []

        # Build set of subtopics that have at least one insight
        subtopics_with_insights: Set[str] = {
            insight.subtopic for insight in insights
        }

        # Collect candidates: active, not sufficient/complete, zero insights
        candidates: List[Subtopic] = []
        for subtopic in plan.subtopics:
            if subtopic.status in (
                SubtopicStatus.removed,
                SubtopicStatus.complete,
                SubtopicStatus.sufficient,
            ):
                continue
            if subtopic.name not in subtopics_with_insights:
                candidates.append(subtopic)

        # Sort by priority descending (low-priority pruned first: 3 before 2 before 1)
        candidates.sort(key=lambda s: s.priority, reverse=True)

        # Compute how many we're allowed to prune
        max_removable = min(
            self.MAX_PRUNES_PER_ITERATION,
            active_count - self.MIN_ACTIVE_SUBTOPICS,
        )

        removed: List[str] = []

        for candidate in candidates:
            if len(removed) >= max_removable:
                break

            candidate.status = SubtopicStatus.removed
            self.removed_history.add(candidate.name.strip().lower())
            removed.append(candidate.name)

        return removed

    def build_planning_note(
        self, added: List[str], removed: List[str]
    ) -> str:
        """Generate a human-readable planning note for trace logging."""
        parts: List[str] = []

        if added:
            parts.append(f"Added {len(added)} subtopic(s): {', '.join(added)}")
        if removed:
            parts.append(f"Pruned {len(removed)} subtopic(s): {', '.join(removed)}")

        if not parts:
            return "No structural plan changes."

        return "; ".join(parts)

    # ── Private Helpers ────────────────────────────────────────────────

    def _count_active(self, plan: ResearchPlan) -> int:
        """Count subtopics that are NOT removed."""
        return sum(
            1 for s in plan.subtopics if s.status != SubtopicStatus.removed
        )

    def _is_duplicate(self, name: str, subtopics: List[Subtopic]) -> bool:
        """Check for case-insensitive substring overlap with existing subtopics."""
        name_lower = name.lower()
        for existing in subtopics:
            existing_lower = existing.name.lower()
            if name_lower in existing_lower or existing_lower in name_lower:
                return True
        return False

    def _was_previously_removed(self, name: str) -> bool:
        """Check oscillation history — was this name ever removed?"""
        return name.strip().lower() in self.removed_history

