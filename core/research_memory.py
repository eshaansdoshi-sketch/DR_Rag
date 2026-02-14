from typing import Dict, List

from schemas import (
    Contradiction,
    EvaluationResult,
    Insight,
    ResearchTraceEntry,
    SourceMetadata,
    Statistic,
)


class ResearchMemory:
    def __init__(self) -> None:
        self.sources: Dict[str, SourceMetadata] = {}
        self.insights: List[Insight] = []
        self.statistics: List[Statistic] = []
        self.contradictions: List[Contradiction] = []
        self.evaluations: List[EvaluationResult] = []
        self.trace: List[ResearchTraceEntry] = []

    def add_sources(self, new_sources: List[SourceMetadata]) -> int:
        added_count = 0
        for source in new_sources:
            url_str = str(source.url)
            if url_str not in self.sources:
                self.sources[url_str] = source
                added_count += 1
        return added_count

    def add_insights(self, new_insights: List[Insight]) -> None:
        self.insights.extend(new_insights)

    def add_statistics(self, new_statistics: List[Statistic]) -> None:
        self.statistics.extend(new_statistics)

    def add_contradictions(self, new_contradictions: List[Contradiction]) -> None:
        self.contradictions.extend(new_contradictions)

    def add_evaluation(self, evaluation: EvaluationResult) -> None:
        self.evaluations.append(evaluation)

    def add_trace_entry(self, entry: ResearchTraceEntry) -> None:
        self.trace.append(entry)

    def get_all_sources(self) -> List[SourceMetadata]:
        return list(self.sources.values())

    def get_sources_by_subtopic(self, subtopic: str) -> List[SourceMetadata]:
        source_urls = set()
        for insight in self.insights:
            if insight.subtopic == subtopic:
                source_urls.update(insight.supporting_sources)
        
        result = []
        for url in source_urls:
            if url in self.sources:
                result.append(self.sources[url])
        
        return result

    def get_insights_by_subtopic(self, subtopic: str) -> List[Insight]:
        return [insight for insight in self.insights if insight.subtopic == subtopic]
