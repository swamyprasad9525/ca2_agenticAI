# AGENT_RESPONSIBILITIES.md — Five Specialized Agents & Orchestrator

## 1. Overview

The Tender and Procurement Evaluation System enforces a strict **Single Responsibility Principle** across its five autonomous agents. Each agent resides in its own isolated Python module within `backend/app/agents/`, operates on validated Pydantic contracts, and writes state exclusively through the `ScorecardService`.

---

## 2. Agent Breakdown

### Agent 1: Criteria Agent (`backend/app/agents/criteria_agent.py`)
- **Primary Objective**: Ingests and parses the formal tender / RFP document via RAG, extracting structured evaluation criteria, weights, mandatory eligibility rules, and commercial pricing formulas.
- **Inputs**:
  - `tender_id`: UUID of the tender.
  - `retriever`: `HybridRetriever` configured with tender metadata filters.
- **Outputs**:
  - `EvaluationPlanDTO`: Validated specification containing `mandatory_requirements`, `technical_criteria` (weights summing to 1.0), `commercial_formula`, and `disqualification_rules`.
- **Allowed Actions**:
  - Parse tender documents and extract table rubrics.
  - Normalize technical criterion weights to sum to exactly 1.0.
  - Persist criteria and mandatory requirements into the database.
- **Forbidden Actions**:
  - Must not evaluate vendors or score proposals.
  - Must not modify criteria once approved by the human operator.
  - Must not invent missing formulas silently.

---

### Agent 2: Compliance Agent (`backend/app/agents/compliance_agent.py`)
- **Primary Objective**: Performs mandatory eligibility screening for each vendor submission against the mandatory prerequisites extracted by the Criteria Agent.
- **Inputs**:
  - `run_id`: UUID of the evaluation run.
  - `vendor_id`: UUID of the target vendor.
  - `evaluation_plan`: Approved `EvaluationPlanDTO`.
- **Outputs**:
  - `List[ComplianceResultRead]`: Assessment per mandatory item with status (`PASS`, `FAIL`, `UNCLEAR`), findings, and citations.
- **Allowed Actions**:
  - Retrieve vendor credentials, corporate registrations, and certifications via RAG.
  - Flag vendors with any failed requirement as `is_disqualified = True`.
  - Flag vendors with ambiguous evidence as `requires_human_review = True` with status `UNCLEAR`.
- **Forbidden Actions**:
  - Must not assign technical points or assess commercial pricing.
  - Must not override tender-mandated disqualification rules.

---

### Agent 3: Technical Scorer (`backend/app/agents/technical_scorer.py`)
- **Primary Objective**: Conducts qualitative scoring of compliant vendor technical proposals against approved evaluation rubrics.
- **Inputs**:
  - `run_id`: UUID of the evaluation run.
  - `vendor_id`: UUID of the eligible vendor.
  - `evaluation_plan`: Approved `EvaluationPlanDTO`.
- **Outputs**:
  - `List[ScorecardRead]`: Technical scorecard entries per criterion with raw points bounded by `max_points`, normalized scores, weighted scores, and verbatim citations.
- **Allowed Actions**:
  - Retrieve vendor technical proposal sections via RAG.
  - Score technical design, methodology, SLA response times, and team qualifications against rubric benchmarks.
  - Cite exact source document filenames, page numbers, and verbatim quotes.
- **Forbidden Actions**:
  - Must not evaluate disqualified vendors unless instructed by human operator.
  - Must not evaluate pricing, fee cards, or commercial proposals.
  - Must not allocate points exceeding `max_points`.

---

### Agent 4: Commercial Scorer (`backend/app/agents/commercial_scorer.py`)
- **Primary Objective**: Extracts, normalizes, and verifies vendor financial bids, pricing schedules, and rate cards.
- **Inputs**:
  - `run_id`: UUID of the evaluation run.
  - `vendor_id`: UUID of the target vendor.
  - `evaluation_plan`: Approved `EvaluationPlanDTO`.
- **Outputs**:
  - `ScorecardRead`: Commercial scorecard record containing extracted total evaluated price in `raw_points` and commercial weight.
- **Allowed Actions**:
  - Extract total contract prices, currencies, and cost schedules from commercial proposals via RAG.
  - Validate completeness of quoted line items.
- **Forbidden Actions**:
  - Must not perform LLM mental arithmetic to calculate relative or composite scores.
  - Cross-vendor relative price formulas are strictly delegated to the deterministic calculation engine.

---

### Agent 5: Award Manager (`backend/app/agents/award_manager.py`)
- **Primary Objective**: Aggregates all compliance findings, technical scores, and commercial bids from the shared scorecard, executes deterministic relative pricing and composite weighting, ranks vendors, and synthesizes an executive recommendation dossier.
- **Inputs**:
  - `run_id`: UUID of the evaluation run.
  - `tender_id`: UUID of the evaluated tender.
- **Outputs**:
  - `AwardRecommendationDTO`: Official recommendation dossier with winner, runner-up, executive summary, justification, risk assessment, and status `RECOMMENDED_AWAITING_APPROVAL`.
- **Allowed Actions**:
  - Delegate relative lowest price calculations to `ScoringEngine` among compliant bidders ($Score_{comm} = \frac{P_{min}}{P_v} \times 100 \times W_{comm}$).
  - Delegate composite score calculations ($Score_{composite} = W_{tech} \times Score_{tech} + W_{comm} \times Score_{comm}$).
  - Rank eligible vendors descending; exclude disqualified vendors from winning.
  - Persist `COMPOSITE` scorecard records.
  - Update evaluation run status to `AWAITING_HUMAN_APPROVAL`.
- **Forbidden Actions**:
  - Must not execute external purchase orders or declare legally binding awards.
  - Must not override mandatory disqualifications.

---

### Orchestrator: Evaluation Orchestrator (`backend/app/orchestrator/evaluation_orchestrator.py`)
- **Primary Objective**: Coordinates the multi-agent lifecycle, enforces phase boundaries, manages concurrent fan-out across $N$ vendors, synchronizes fan-in state, and records execution telemetry.
- **Execution Flow**:
  1. Phase 1: Criteria Agent (extracts/verifies criteria).
  2. Phase 2: Fan-out parallel compliance screening across all $N$ vendors.
  3. Phase 3: Compliance gating (bypasses technical scoring for disqualified vendors; executes technical/commercial scoring concurrently for compliant vendors).
  4. Phase 4: Fan-in synchronization across all vendor tasks.
  5. Phase 5: Award Manager synthesis.

