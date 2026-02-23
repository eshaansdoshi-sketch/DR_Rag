import asyncio
import logging
from contextlib import asynccontextmanager
from functools import partial
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agents.analyst import AnalystAgent
from agents.evaluator import EvaluatorAgent
from agents.planner import PlannerAgent
from agents.searcher import SearcherAgent
from agents.writer import WriterAgent
from core.cloud_database import CloudDatabaseManager
from core.llm_client import LLMClient
from core.plan_analytics import (
    compute_health_metrics,
    derive_plan_summary,
    reconstruct_plan_from_trace,
)
from core.structured_logger import setup_logging
from orchestrator import Orchestrator
from tools.web_search import WebSearchTool

load_dotenv()

# Configure structured JSON logging (idempotent)
setup_logging()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Database instance (created at startup, closed at shutdown)
# ---------------------------------------------------------------------------
db: Optional[CloudDatabaseManager] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage database lifecycle with FastAPI startup/shutdown."""
    global db
    try:
        db = CloudDatabaseManager()
        logger.info("Database connected successfully.")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        db = None
    yield
    if db is not None:
        db.close()
        logger.info("Database connection closed.")


# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Deep Research Agent API",
    description="Structured autonomous research engine — API service",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------
class ResearchRequest(BaseModel):
    query: str = Field(..., min_length=3, description="The research query to investigate")
    depth_mode: str = Field(
        default="standard",
        description="Research depth mode: quick_scan, standard, or deep_investigation",
    )
    confidence_threshold: float | None = Field(
        default=None,
        description="Optional confidence threshold override (clamped to 0.65–0.90). If omitted, uses the depth_mode default.",
    )
    contradiction_sensitivity: str = Field(
        default="flag_all",
        description="Contradiction handling mode: ignore_minor, flag_all, or escalate_on_any",
    )
    evidence_strictness: str = Field(
        default="moderate",
        description="Evidence rigor level: relaxed, moderate, or strict",
    )
    max_iterations: int | None = Field(
        default=None,
        description="Optional iteration cap override (clamped to 1–5). If omitted, uses depth_mode default.",
    )
    report_mode: str = Field(
        default="technical_whitepaper",
        description="Report format: executive_summary, technical_whitepaper, risk_assessment, or academic_structured",
    )
    max_concurrent_tasks: int = Field(
        default=3,
        description="Max parallel subtopic tasks per iteration (clamped to 1–10)",
    )
    max_tokens_per_iteration: int | None = Field(
        default=None,
        description="Optional token budget per iteration (default: 8000)",
    )
    max_tokens_per_run: int | None = Field(
        default=None,
        description="Optional token budget for entire run (default: 30000)",
    )
    max_run_timeout: float = Field(
        default=300.0,
        description="Global timeout in seconds for the entire run (default: 300)",
    )


class ResearchResponse(BaseModel):
    run_id: int
    confidence_score: float
    iterations: int
    report_json: Optional[Dict[str, Any]] = None


class RunSummary(BaseModel):
    id: int
    query: str
    confidence_score: Optional[float] = None
    iterations: Optional[int] = None
    run_mode: Optional[str] = None
    structural_complexity_score: Optional[float] = None
    created_at: Optional[str] = None


class RunDetail(BaseModel):
    id: int
    query: str
    plan_json: Optional[Dict[str, Any]] = None
    report_json: Optional[Dict[str, Any]] = None
    confidence_score: Optional[float] = None
    iterations: Optional[int] = None
    run_mode: Optional[str] = None
    total_subtopics_encountered: Optional[int] = None
    total_subtopics_added: Optional[int] = None
    total_subtopics_removed: Optional[int] = None
    max_active_subtopics: Optional[int] = None
    structural_complexity_score: Optional[float] = None
    plan_expansion_ratio: Optional[float] = None
    prune_ratio: Optional[float] = None
    convergence_rate: Optional[float] = None
    structural_volatility_score: Optional[float] = None
    created_at: Optional[str] = None


# ---------------------------------------------------------------------------
# Helper — build orchestrator (per-request, no shared state)
# ---------------------------------------------------------------------------
def _build_orchestrator() -> Orchestrator:
    llm_client = LLMClient()
    web_search_tool = WebSearchTool()

    return Orchestrator(
        planner=PlannerAgent(llm_client),
        searcher=SearcherAgent(web_search_tool),
        analyst=AnalystAgent(llm_client),
        evaluator=EvaluatorAgent(llm_client),
        writer=WriterAgent(llm_client),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.post("/research", response_model=ResearchResponse, status_code=201)
async def create_research(request: ResearchRequest):
    """Run a full research pipeline and optionally persist the results."""
    try:
        orchestrator = _build_orchestrator()

        # Call async orchestrator directly — no run_in_executor needed
        report = await orchestrator.run_async(
            query=request.query,
            depth_mode=request.depth_mode,
            confidence_threshold=request.confidence_threshold,
            contradiction_sensitivity=request.contradiction_sensitivity,
            evidence_strictness=request.evidence_strictness,
            max_iterations=request.max_iterations,
            report_mode=request.report_mode,
            max_concurrent_tasks=request.max_concurrent_tasks,
            max_tokens_per_iteration=request.max_tokens_per_iteration,
            max_tokens_per_run=request.max_tokens_per_run,
            max_run_timeout=request.max_run_timeout,
        )

        # Serialize the full report for response (and optional JSONB storage)
        report_data = report.model_dump(mode="json")

        iterations = len(report.research_trace)
        confidence = report.confidence_score

        run_id = 0  # default when DB is unavailable

        # ── Try to persist to DB if available ─────────────────────────
        if db is not None:
            try:
                loop = asyncio.get_event_loop()

                plan_summary = derive_plan_summary(report_data)
                plan_summary["query"] = request.query

                health = compute_health_metrics(report_data)

                metadata: Dict[str, Any] = {
                    "run_mode": "stateless",
                    "total_subtopics_encountered": plan_summary.get("total_unique_subtopics"),
                    "total_subtopics_added": plan_summary.get("total_subtopics_added"),
                    "total_subtopics_removed": plan_summary.get("total_subtopics_removed"),
                    "max_active_subtopics": plan_summary.get("max_concurrent_active"),
                    "structural_complexity_score": plan_summary.get("structural_complexity_score"),
                    "plan_expansion_ratio": health.get("plan_expansion_ratio"),
                    "prune_ratio": health.get("prune_ratio"),
                    "convergence_rate": health.get("convergence_rate"),
                    "structural_volatility_score": health.get("structural_volatility_score"),
                }

                run_id = await loop.run_in_executor(
                    None,
                    db.save_run,
                    request.query,
                    plan_summary,
                    report_data,
                    confidence,
                    iterations,
                    metadata,
                )
            except Exception as db_err:
                logger.warning(f"DB persistence skipped: {db_err}")
        else:
            logger.info("Database unavailable — returning report without persistence.")

        return ResearchResponse(
            run_id=run_id,
            confidence_score=confidence,
            iterations=iterations,
            report_json=report_data,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Research pipeline failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Research failed: {str(e)}")


@app.get("/research", response_model=List[RunSummary])
async def list_research_runs():
    """List all completed research runs (lightweight)."""
    if db is None:
        raise HTTPException(status_code=503, detail="Database is unavailable.")

    try:
        loop = asyncio.get_event_loop()
        runs = await loop.run_in_executor(None, db.list_runs)
        return runs
    except Exception as e:
        logger.error(f"Failed to list runs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list runs: {str(e)}")


@app.get("/research/{run_id}", response_model=RunDetail)
async def get_research_run(run_id: int):
    """Retrieve the full report for a specific research run."""
    if db is None:
        raise HTTPException(status_code=503, detail="Database is unavailable.")

    try:
        loop = asyncio.get_event_loop()
        run = await loop.run_in_executor(None, db.get_run, run_id)

        if run is None:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found.")

        return run
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get run {run_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get run: {str(e)}")


@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "healthy", "database": "connected" if db else "disconnected"}
