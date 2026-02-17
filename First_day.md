deep_research_agent/
│
├── agents/
│   ├── planner.py
│   ├── searcher.py
│   ├── analyst.py
│   ├── evaluator.py
│   ├── writer.py
│
├── tools/
│   ├── base_tool.py
│   ├── web_search.py
│
├── core/
│   ├── research_memory.py
│   ├── trace_logger.py
│
├── schemas.py
├── config.py
├── orchestrator.py
├── main.py   <-- CLI entry
└── requirements.txt


We are building:

A Planner-Governed, Memory-Aware, Confidence-Driven Autonomous Research Engine.

Primary Objective: Depth
Secondary: Correctness
Tertiary: Cost
Not optimizing for speed.

FINAL LOCKED ARCHITECTURE
0️⃣ Core Principles

Max 2 iterations

Confidence-driven stopping

Memory merge (never discard)

Semi-adaptive planner

Mandatory research trace

Penalize weak evidence

Structured contradictions

This is now internally consistent.

1️⃣ Planner — Semi-Adaptive Governance Layer
First pass:

Creates:

{
  "research_objective": "",
  "subtopics": [
    {
      "name": "",
      "priority": 1-3,
      "status": "pending"
    }
  ],
  "key_questions": [],
  "metrics_required": []
}
After evaluation:

Planner can:

Add missing subtopics

Reprioritize

Mark subtopics complete

But cannot delete entire structure.

This prevents chaotic restructuring.

This is controlled intelligence.

2️⃣ Research Memory — Structured Knowledge Base

Instead of loose arrays, we define a strong schema.

research_memory = {
    "sources": [],
    "insights": [],
    "statistics": [],
    "contradictions": [],
    "knowledge_gaps": [],
    "subtopic_coverage": {},
    "iterations": [],
    "trace_log": []
}
Why this matters

Enables coverage scoring

Enables contradiction tracking

Enables trace display

Enables credibility aggregation

This is where architectural quality shows.

3️⃣ Searcher — Breadth-First, Controlled Expansion
Iteration 1:

Search across all subtopics.

Iteration 2:

Search only:

Missing aspects

Weakly supported claims

Contradictions

Data reinforcement

Sources must return metadata:

{
  "title": "",
  "url": "",
  "summary": "",
  "publication_date": "",
  "domain_type": "edu/gov/news/blog/other",
  "author_present": true,
  "opinion_score": 0-1
}

Opinion score can be heuristic.

This supports evaluator penalties.

4️⃣ Analyst — Evidence-Weighted Synthesis

Now we elevate analyst:

It must:

Map insights to subtopics

Attach supporting sources

Extract statistics

Detect contradictions

Assign internal confidence to insights

Contradictions must be explicit:

{
  "claim_a": "",
  "source_a": "",
  "claim_b": "",
  "source_b": "",
  "severity": 0-1
}

Severity helps evaluator assess risk.

5️⃣ Evaluator — Critical Scoring Engine

This is now the heart of autonomy.

It must compute:

Coverage Score

Are all subtopics addressed?

Credibility Score

Weighted by:

Domain type

Recency

Author presence

Diversity Score

Penalty if:

40% sources from same domain

Too many opinion pieces

Single-source insights

Evidence Strength Score

Penalty if:

Insights lack multiple citations

No quantitative backing

Consistency Score

Penalty if:

Severe unresolved contradictions

Confidence Formula (Final Version)

Conceptual:

confidence =
    coverage * 0.25
  + credibility * 0.25
  + diversity * 0.15
  + evidence_strength * 0.20
  + consistency * 0.15

Threshold: 0.75

If below:

Return:

{
  "confidence_score": 0.68,
  "needs_more_research": true,
  "refined_queries": [],
  "missing_aspects": [],
  "plan_updates": []
}
6️⃣ Planner Adaptation Rules

Evaluator can:

Add new subtopic

Increase priority of weak subtopic

Mark subtopic complete

But cannot:

Delete original objective

Remove major subtopics

Overwrite entire plan

This maintains stability.

7️⃣ Iteration Policy

Loop:

iteration = 0

while iteration < 2:
    search
    analyze
    merge memory
    evaluate
    log trace

    if confidence >= 0.75:
        break

    apply planner updates
    iteration += 1

If after 2 iterations confidence < 0.75:

Generate report

Include unresolved gaps

Include low-confidence warning

This is realistic and honest.

8️⃣ Research Trace — Mandatory Transparency Layer

Each iteration logs:

{
  "iteration": 1,
  "confidence": 0.64,
  "coverage_summary": "",
  "new_sources_added": 8,
  "weak_areas": [],
  "plan_adjustments": []
}

Final report must include:

Research Process Summary

Iterations performed

Confidence progression

Major refinements made

Remaining uncertainties

This is extremely strong architecturally.

Very few student systems include process transparency.

🔍 What Makes This System Mature

You now have:

Governance (planner)

Execution (searcher + analyst)

Oversight (evaluator)

Memory

Iterative reflection

Transparency trace

Confidence scoring

Contradiction detection

Evidence weighting

Diversity penalty

This is not toy-level.

What ChatGPT DOESN’T Give You

When you use ChatGPT:

❌ You don’t see which sources were merged

❌ You don’t see coverage scoring

❌ You don’t see contradiction detection

❌ You don’t see confidence computation

❌ You don’t see research iteration logic

❌ You don’t control evaluation weighting

❌ You can’t persist structured trace

❌ You can’t embed it into a product pipeline easily

❌ You can’t enforce strict schemas

It’s a black box.

8️⃣ Extensibility

Tomorrow you can:

Add domain-specific scoring

Add financial risk modeling

Add regulatory compliance scoring

Add bias detection

Add stance classification

Add embeddings

Add citation-level attribution

You cannot modify ChatGPT’s internal reasoning.
we also need to add a feature that can know how good the search actually was , and ensure that it was not just a shallow search
