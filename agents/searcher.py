from typing import List, Optional

from schemas import ResearchPlan, SourceMetadata
from tools.web_search import WebSearchTool


class SearcherAgent:
    def __init__(self, web_search_tool: WebSearchTool) -> None:
        self.web_search_tool = web_search_tool

    def execute_search(
        self,
        plan: ResearchPlan,
        iteration: int,
        refined_queries: Optional[List[str]] = None,
        max_results_initial: int = 5,
        max_results_refined: int = 4,
    ) -> List[SourceMetadata]:
        all_sources = []
        
        if iteration == 1:
            for subtopic in plan.subtopics:
                query = f"{plan.research_objective} - {subtopic.name}"
                sources = self.web_search_tool.search(
                    query=query,
                    max_results=max_results_initial
                )
                all_sources.extend(sources)
        
        elif iteration > 1 and refined_queries:
            for query in refined_queries:
                sources = self.web_search_tool.search(
                    query=query,
                    max_results=max_results_refined
                )
                all_sources.extend(sources)
        
        return all_sources

    def search_subtopic(self, query: str, max_results: int = 5) -> List[SourceMetadata]:
        """Search for a single query. Used by async runner for per-subtopic parallelism."""
        return self.web_search_tool.search(query=query, max_results=max_results)
