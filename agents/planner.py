from core.llm_client import LLMClient
from schemas import ResearchPlan


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
