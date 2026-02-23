# 🗺️ Deep Research Agent — PRD Roadmap

> **Last Updated:** 2026-02-23  
> **Legend:** ✅ Done &nbsp;|&nbsp; 🟡 Partial &nbsp;|&nbsp; ❌ Not Started

---

## 5️⃣ System Architecture (Core Pipeline)

| Component | Status | Implementation |
|-----------|--------|----------------|
| User Query → Planner | ✅ | `main.py` CLI, `orchestrator.py` |
| Planner → Searcher | ✅ | `orchestrator.py` loop |
| Searcher (Tool) | ✅ | `tools/web_search.py` (Tavily) |
| Analyst | ✅ | `agents/analyst.py` |
| Evaluator (Hybrid scoring + LLM reflection) | ✅ | `agents/evaluator.py` |
| Memory | ✅ | `core/research_memory.py` |
| Writer → Final Report | ✅ | `agents/writer.py` |
| Trace Logging | ✅ | `ResearchTraceEntry` in `schemas.py` |
| **FastAPI API** | ✅ | `api.py` — POST/GET endpoints |
| **Cloud Database** | ✅ | `core/cloud_database.py` — PostgreSQL/Supabase |

---

## 6️⃣ Functional Requirements

### A. Planning Layer — `agents/planner.py`

| Requirement | Status | Notes |
|-------------|--------|-------|
| Decompose query into subtopics | ✅ | 4–6 subtopics via LLM |
| Assign priority | ✅ | Priority 1/2/3 in `Subtopic` schema |
| Generate key questions | ✅ | `key_questions` field |
| Define metrics required | ✅ | `metrics_required` field |
| Dynamic addition of subtopics | ✅ | `PlanManager.spawn_subtopics()` — constrained expansion with 6 safety gates |
| Removal of irrelevant subtopics | ✅ | `PlanManager.prune_subtopics()` — safe pruning with oscillation prevention |

---

### B. Retrieval Layer — `tools/web_search.py`, `agents/searcher.py`

| Requirement | Status | Notes |
|-------------|--------|-------|
| Tavily search integration | ✅ | Official client + requests fallback |
| Summary truncation | ✅ | Truncated to 400 chars |
| Domain type classification | ✅ | `.edu`, `.gov`, `news`, `blog`, `other` |
| Domain-specific search biasing (.edu/.gov weighting) | 🟡 | Domain credibility scoring exists in evaluator, but search queries are not biased toward `.edu/.gov` |
| Multi-tool support (arXiv, PubMed, etc.) | ❌ | Only Tavily web search |
| Embedding-based semantic retrieval | ❌ | No vector store / embeddings |
| Source recency filtering | ✅ | Soft temporal awareness via `core/temporal.py` — no hard filtering |
| Configurable source counts | ✅ | `max_results_initial` / `max_results_refined` via depth presets |

---

### C. Analysis Layer — `agents/analyst.py`

| Requirement | Status | Notes |
|-------------|--------|-------|
| Extract structured insights | ✅ | `Insight` model with subtopic, statement, confidence |
| Extract statistics | ✅ | `Statistic` model with value, context, source |
| Detect contradictions | ✅ | `Contradiction` model with severity scoring |
| Numeric severity scoring | ✅ | Float 0.0–1.0 |
| Citation-level mapping per section | 🟡 | `supporting_sources` on insights; not per report section |
| Stance classification (pro/contra/neutral) | ✅ | Rule-based in `core/bias_detector.py`, wired into `analyst.py` |
| Bias detection | ✅ | Heuristic `opinion_score` computed from summary text in `web_search.py` |
| Confidence calibration per insight | ✅ | `confidence` field on each `Insight` |

---

### D. Evaluation Layer — `agents/evaluator.py`

| Requirement | Status | Notes |
|-------------|--------|-------|
| Deterministic scoring (coverage, credibility, diversity) | ✅ | 5 metrics computed deterministically |
| Weighted scoring model | ✅ | 0.25/0.25/0.15/0.20/0.15 weights |
| Subtopic confidence | ✅ | Per-subtopic `SubtopicScore` |
| Global confidence | ✅ | Weighted average with weak-subtopic penalty |
| Weak subtopic detection | ✅ | `confidence < 0.6` → `weak` status |
| Refined query generation | ✅ | LLM-generated `refined_queries` |
| Diagnostic breakdown (why confidence low) | 🟡 | Individual metric scores exist, but no human-readable diagnostic string |
| Strategy-level adaptation | 🟡 | Plan priority adjustment exists; no search strategy switching |
| Confidence delta tracking | ✅ | `convergence_rate` in `plan_analytics.py`, persisted in DB |
| Multi-iteration performance analytics | ✅ | Structural health metrics: expansion ratio, prune ratio, volatility |
| Contradiction sensitivity control | ✅ | 3 modes (`ignore_minor`, `flag_all`, `escalate_on_any`) in `core/depth_config.py` — affects reaction, not detection |
| Evidence strictness enforcement | ✅ | 3 levels (`relaxed`, `moderate`, `strict`) in `core/evidence_strictness.py` — sources/insight, stats/subtopic, domain diversity |

---

### E. Memory Layer — `core/research_memory.py`

| Requirement | Status | Notes |
|-------------|--------|-------|
| Source deduplication | ✅ | URL-keyed dict in `ResearchMemory` |
| Structured memory storage | ✅ | Typed lists for insights, stats, contradictions |
| Trace logging | ✅ | `ResearchTraceEntry` list |
| Cross-session persistent memory | ✅ | `core/cloud_database.py` — PostgreSQL via Supabase |
| Knowledge graph memory | ❌ | Not implemented |
| Embedding-indexed memory | ❌ | Not implemented |

---

### F. Writing Layer — `agents/writer.py`

| Requirement | Status | Notes |
|-------------|--------|-------|
| Executive summary | ✅ | 2–3 paragraph summary |
| Structured sections | ✅ | 3–5 sections with headings |
| Risk assessment | ✅ | List of risk items |
| Recommendations | ✅ | List of recommendation items |
| References | ✅ | Deduplicated URL list |
| Research trace | ✅ | Full iteration trace in report |
| Per-section citation mapping | ✅ | `supporting_sources` on `ReportSection` |
| Report mode control | ✅ | 4 modes (`executive_summary`, `technical_whitepaper`, `risk_assessment`, `academic_structured`) in `core/report_modes.py` |
| PDF export | ❌ | Not implemented |
| Version comparison | ❌ | Not implemented |

---

### G. Iteration Logic — `orchestrator.py`

| Requirement | Status | Notes |
|-------------|--------|-------|
| Confidence-based stopping | ✅ | Stops at preset-driven threshold |
| Max iteration cap | ✅ | Preset-driven via `core/depth_config.py` |
| User-defined iteration cap | ✅ | `max_iterations` override (clamped 1–5) — hard ceiling, Explicit > Preset > Threshold |
| Plan priority adjustment | ✅ | `_apply_plan_updates()` boosts priority |
| Adaptive iteration count | ✅ | `deep_investigation` mode uses 4 iter (bounded) |
| Confidence threshold override | ✅ | User-configurable (clamped 0.65–0.90), logged per iteration |
| Strategy switching based on diagnostic | ❌ | No strategy switching logic |
| Escalation mode (deep research mode) | ✅ | `depth_mode="deep_investigation"` preset |

---

## 7️⃣ Non-Functional Requirements

### Performance

| Requirement | Status | Notes |
|-------------|--------|-------|
| Token size optimization | ✅ | Token budgeting in `core/token_budget.py` — configurable per-iteration + per-run ceilings, estimation, BudgetExceeded |
| Free-tier compatibility | ✅ | Uses Groq free tier (Llama 3.1 8B) |
| Parallel subtopic execution | ✅ | Two-phase async parallelism in `core/async_runner.py` — semaphore-bounded |
| Async execution | ✅ | `orchestrator.run_async()` canonical, `run()` is thin wrapper |

### Reliability

| Requirement | Status | Notes |
|-------------|--------|-------|
| Strict schema enforcement | ✅ | Pydantic `extra="forbid"` on all models |
| Retry logic | ✅ | `max_retries` in `LLMClient` |
| Backoff strategy | ✅ | Exponential backoff in `core/rate_limiter.py` — retries 429/5xx/timeout, skips 4xx |
| Error logging system | ✅ | Structured JSON logging in `core/structured_logger.py` — all events machine-parseable |

### Scalability

| Requirement | Status | Notes |
|-------------|--------|-------|
| Caching layer | ✅ | Deterministic LRU + TTL in `core/cache.py` — search (512 entries) + LLM (256 entries) |
| Database persistence | ✅ | PostgreSQL via `core/cloud_database.py` |
| Rate limit management | ✅ | Token-bucket in `core/rate_limiter.py` — Groq 25/min, Tavily 20/min |

### Explainability

| Requirement | Status | Notes |
|-------------|--------|-------|
| Research trace | ✅ | Full trace in final report |
| Confidence score | ✅ | Global + per-subtopic |
| Termination reason tracking | ✅ | Explicit `TerminationReason` enum stamped on every report — 6 reasons, deterministic |
| Confidence trend visualization | ❌ | No UI/visualization |
| Diagnostic dashboard | ❌ | No dashboard |

---

## 8️⃣ Agentic Expansion Plan (Next Evolution)

| Requirement | Status | Notes |
|-------------|--------|-------|
| Diagnostic-driven retrieval strategy | ❌ | |
| Adaptive search biasing (credibility vs breadth) | ❌ | |
| Subtopic spawning | ✅ | `PlanManager` with constrained adaptive expansion |
| Dynamic goal rewriting | ❌ | |
| Tool selection agent | ❌ | |
| Self-critique before report generation | ❌ | |
| Long-term learning memory | ❌ | |
| Strategy performance tracking | ✅ | Structural health metrics in `core/plan_analytics.py` |

---

## 📊 Summary

| Category | ✅ Done | 🟡 Partial | ❌ Not Started | Total |
|----------|---------|-----------|---------------|-------|
| **Architecture** | 10 | 0 | 0 | 10 |
| **A. Planning** | 6 | 0 | 0 | 6 |
| **B. Retrieval** | 5 | 1 | 2 | 8 |
| **C. Analysis** | 7 | 1 | 0 | 8 |
| **D. Evaluation** | 10 | 2 | 0 | 12 |
| **E. Memory** | 4 | 0 | 2 | 6 |
| **F. Writing** | 8 | 0 | 2 | 10 |
| **G. Iteration** | 7 | 0 | 1 | 8 |
| **Non-Functional** | 12 | 1 | 2 | 15 |
| **Agentic Expansion** | 2 | 0 | 6 | 8 |
| **TOTAL** | **71** | **5** | **15** | **91** |

> **Overall Progress: ~85% complete** (71 fully done + 5 partial out of 91 requirements)

---

## 🎯 Recommended Next Priorities

1. **Embedding-based Retrieval** — Add a vector store (FAISS/ChromaDB) for semantic memory & retrieval
2. **Multi-tool Search** — Add arXiv, PubMed, or Google Scholar adapters
3. **PDF Export** — Use `reportlab` or `weasyprint` to generate downloadable reports
4. **Diagnostic Dashboard** — Build a simple Streamlit/Gradio UI for visualizing research traces
5. **Strategy Switching** — Diagnostic-driven retrieval strategy changes based on evaluation feedback
