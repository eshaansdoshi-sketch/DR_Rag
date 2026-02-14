import sys

from dotenv import load_dotenv

from agents.analyst import AnalystAgent
from agents.evaluator import EvaluatorAgent
from agents.planner import PlannerAgent
from agents.searcher import SearcherAgent
from agents.writer import WriterAgent
from core.llm_client import LLMClient
from orchestrator import Orchestrator
from tools.web_search import WebSearchTool


def main() -> None:
    load_dotenv()
    
    if len(sys.argv) < 2:
        print("Usage: python main.py '<research query>'")
        sys.exit(1)
    
    query = " ".join(sys.argv[1:])
    
    llm_client = LLMClient()
    web_search_tool = WebSearchTool()
    
    planner = PlannerAgent(llm_client)
    searcher = SearcherAgent(web_search_tool)
    analyst = AnalystAgent(llm_client)
    evaluator = EvaluatorAgent(llm_client)
    writer = WriterAgent(llm_client)
    
    orchestrator = Orchestrator(
        planner=planner,
        searcher=searcher,
        analyst=analyst,
        evaluator=evaluator,
        writer=writer
    )
    
    report = orchestrator.run(query)
    
    print("\n" + "=" * 80)
    print("RESEARCH REPORT")
    print("=" * 80 + "\n")
    
    print("EXECUTIVE SUMMARY")
    print("-" * 80)
    print(report.executive_summary)
    print()
    
    print("FINDINGS")
    print("-" * 80)
    for section in report.structured_sections:
        print(f"\n{section.heading}")
        print(section.content)
    print()
    
    print("RISK ASSESSMENT")
    print("-" * 80)
    for i, risk in enumerate(report.risk_assessment, 1):
        print(f"{i}. {risk}")
    print()
    
    print("RECOMMENDATIONS")
    print("-" * 80)
    for i, recommendation in enumerate(report.recommendations, 1):
        print(f"{i}. {recommendation}")
    print()
    
    print("RESEARCH QUALITY METRICS")
    print("-" * 80)
    print(f"Overall Confidence Score: {report.confidence_score:.2%}")
    print(f"Total Iterations: {len(report.research_trace)}")
    
    if report.research_trace:
        last_trace = report.research_trace[-1]
        print(f"Final Global Confidence: {last_trace.global_confidence:.2%}")
        print(f"Total Sources Added: {sum(t.new_sources_added for t in report.research_trace)}")
    print()
    
    print("REFERENCES")
    print("-" * 80)
    for i, ref in enumerate(report.references, 1):
        print(f"{i}. {ref}")
    print()


if __name__ == "__main__":
    main()
