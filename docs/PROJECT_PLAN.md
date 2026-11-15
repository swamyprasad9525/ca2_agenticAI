# Project Plan — Tender and Procurement Evaluation System

## Executive Overview

This document defines the complete engineering roadmap for the **Tender and Procurement Evaluation System**, an enterprise-grade multi-agent AI application designed to evaluate multiple vendor bids against complex tender requirements using evidence-anchored retrieval, deterministic mathematical scoring, and human-in-the-loop governance.

In accordance with architectural standards, the implementation roadmap is divided into **exactly two major parts**:

* **Part 1**: Core Multi-Agent Architecture, RAG Pipeline, Deterministic Scoring Engine, Persistent Storage & Backend API.
* **Part 2**: Frontend Dashboard, Real-Time Orchestration Visualizer, Evidence Inspector, Human Sign-Off Workflow & Production Hardening.

---

```
                       PROJECT IMPLEMENTATION ROADMAP
========================================================================================

PART 1: CORE ENGINE, AGENTS, RAG & BACKEND API
  ├── Phase 1.1: Project Initialization & Environment Scaffolding
  ├── Phase 1.2: Domain Models, Pydantic Schemas & Data Contracts
  ├── Phase 1.3: Document Ingestion, Parsing & Citation-Aware RAG Engine
  ├── Phase 1.4: Deterministic Mathematical Scoring Engine & Validation Logic
  ├── Phase 1.5: Five Specialised Agents Implementation (Microsoft Agent Framework)
  ├── Phase 1.6: Multi-Agent Orchestrator & Persistent Shared Scorecard
  ├── Phase 1.7: FastAPI Application & Real-Time SSE Streaming Endpoints
  └── Phase 1.8: Verification, Test Suite & Baseline Benchmarking

PART 2: USER EXPERIENCE, CITATION INSPECTION, GOVERNANCE & PRODUCTION HARDENING
  ├── Phase 2.1: React + TypeScript Project Setup & Component Architecture
  ├── Phase 2.2: Tender & Vendor Upload Management Interface
  ├── Phase 2.3: Real-Time Multi-Agent Execution Pipeline Visualizer
  ├── Phase 2.4: Dynamic Weighted Scorecard & Multi-Vendor Comparison Matrix
  ├── Phase 2.5: Evidence & Citation Drill-Down Drawer
  ├── Phase 2.6: Human-in-the-Loop Review & Award Sign-Off Interface
  ├── Phase 2.7: PostgreSQL Migration Verification & Dockerization
  └── Phase 2.8: Comprehensive End-to-End System Testing & Acceptance Audit
========================================================================================
```

---

## PART 1: Core Multi-Agent Architecture, RAG Pipeline, Deterministic Scoring Engine, Persistent Storage & Backend API

### Phase 1.1: Project Initialization & Environment Scaffolding
- **Goal**: Establish a rock-solid, isolated Python 3.12+ development environment with all required dependencies, configuration management, and directory structures.
- **Tasks**:
  1. Create virtual environment using Python 3.12.
  2. Configure dependency specifications (`pyproject.toml` and `requirements.txt`) with exact pinned dependencies:
     - `agent-framework` (Microsoft Agent Framework)
     - `fastapi`, `uvicorn[standard]`
     - `pydantic>=2.10`, `pydantic-settings`
     - `sqlalchemy[asyncio]>=2.0`, `aiosqlite`, `asyncpg`, `alembic`
     - `chromadb`, `sentence-transformers`
     - `pypdf`, `pdfplumber`, `python-docx`
     - `pytest`, `pytest-asyncio`, `pytest-mock`, `httpx`
  3. Initialize application folder hierarchy (`backend/app/{api,agents,rag,db,schemas,services,core}`).
  4. Build centralized configuration module (`core/config.py`) using `pydantic-settings` to manage API keys, database URLs, embedding models, and file upload limits.
  5. Setup structured JSON logging with correlation IDs (`core/logging.py`) for end-to-end tracing across agent invocations.

### Phase 1.2: Domain Models, Pydantic Schemas & Data Contracts
- **Goal**: Implement runtime-validated data transfer objects (DTOs) and SQLAlchemy ORM entities based on `docs/DATA_CONTRACTS.md`.
- **Tasks**:
  1. Implement core Pydantic schemas in `schemas/`:
     - `schemas/evidence.py`: Citation model (`document_id`, `page_number`, `section_reference`, `verbatim_quote`, `confidence_score`).
     - `schemas/criteria.py`: `TenderCriteriaSpec`, `MandatoryRequirement`, `TechnicalCriterion`, `CommercialFormulaSpec`.
     - `schemas/compliance.py`: `ComplianceItem`, `ComplianceResult` (Pass/Fail/Unclear flags, disqualification status).
     - `schemas/technical.py`: `TechnicalCriterionScore`, `TechnicalEvaluationResult`.
     - `schemas/commercial.py`: `PricingScheduleItem`, `CommercialEvaluationResult`.
     - `schemas/scorecard.py`: `VendorScorecard`, `CompositeScore`, `SharedScorecardState`.
     - `schemas/award.py`: `AwardRecommendation`, `HumanSignOffRecord`.
  2. Implement SQLAlchemy 2.0 async database models in `db/models/`:
     - `TenderModel`, `TenderDocumentModel`
     - `VendorModel`, `BidDocumentModel`
     - `EvaluationRunModel`, `ScorecardModel`, `ScorecardItemModel`
     - `AuditLogModel`
  3. Configure Alembic migration scripts to manage database schemas.

### Phase 1.3: Document Ingestion, Parsing & Citation-Aware RAG Engine
- **Goal**: Construct an ingestion pipeline that extracts text from tender and bid documents (PDF, DOCX) while retaining exact structural metadata and page numbers.
- **Tasks**:
  1. Build multi-format document parser (`rag/document_parser.py`) supporting PDF and DOCX, capturing page numbers, tables, and section headings.
  2. Implement structural & recursive chunker (`rag/chunker.py`) with configurable chunk sizes (e.g., 500-800 tokens) and overlap (100 tokens), preserving page boundaries and clause headers.
  3. Define vector store interface protocol (`rag/vector_store.py`) enabling pluggable backends:
     - Local development implementation: ChromaDB (in-process).
     - Production implementation: `pgvector` via SQLAlchemy/psycopg3.
  4. Develop hybrid retrieval engine (`rag/retriever.py`) combining dense semantic embeddings with metadata filtering (`document_type`, `tender_id`, `vendor_id`, `section`).

### Phase 1.4: Deterministic Mathematical Scoring Engine & Validation Logic
- **Goal**: Implement a zero-hallucination, strictly deterministic calculation service for all procurement mathematics.
- **Tasks**:
  1. Build formula evaluator (`services/scoring_engine.py`):
     - Weighted Technical Score calculation: $S_{tech} = \sum (Points_i \times Weight_i)$.
     - Commercial Score evaluation using standard tender procurement formulas:
       - Relative Lowest Cost: $S_{comm} = \left(\frac{P_{lowest}}{P_{vendor}}\right) \times W_{comm}$.
       - Linear inverse normalization and custom tender-specified rate curves.
     - Composite Score computation: $S_{total} = S_{tech} + S_{comm}$.
  2. Implement mandatory requirement compliance validator:
     - Disqualification trigger: If any mandatory requirement has status `FAIL`, mark vendor as `disqualified = True`.
     - Ambiguity flag: If any mandatory requirement has status `UNCLEAR`, mark `flagged_for_human_review = True`.
  3. Unit test scoring engine against edge cases (division by zero, equal prices, negative weights, missing line items).

### Phase 1.5: Five Specialised Agents Implementation (Microsoft Agent Framework)
- **Goal**: Implement the five autonomous agents in isolated Python modules using Microsoft Agent Framework (`agent-framework`).
- **Tasks**:
  1. Base agent abstraction (`agents/base.py`) providing common LLM client initialization, prompt formatting with anti-injection fences, and structured Pydantic output validation.
  2. **Criteria Agent** (`agents/criteria_agent.py`):
     - Ingests tender documents via RAG.
     - Extracts mandatory Pass/Fail requirements, technical evaluation criteria with weights and maximum points, and commercial scoring rules into a validated `TenderCriteriaSpec`.
     - Emits `CRITERIA_INCOMPLETE` if critical scoring rules are absent.
  3. **Compliance Agent** (`agents/compliance_agent.py`):
     - Retrieves vendor bid sections matching each mandatory requirement.
     - Evaluates compliance: assigns `PASS`, `FAIL`, or `UNCLEAR`.
     - Attaches exact page references and verbatim evidence quotes.
  4. **Technical Scorer** (`agents/technical_scorer.py`):
     - Retrieves technical proposal content for compliant vendors.
     - Evaluates solution architecture, methodology, SLAs, and team qualifications against the rubric.
     - Allocates points within allowed ranges and documents justification with citations.
  5. **Commercial Scorer** (`agents/commercial_scorer.py`):
     - Extracts vendor pricing, rate cards, and financial schedules.
     - Verifies financial completeness and feeds normalized totals to the deterministic math engine.
  6. **Award Manager** (`agents/award_manager.py`):
     - Aggregates individual scores into the shared scorecard.
     - Ranks eligible vendors, highlights strengths, risks, and anomalies.
     - Generates an evidence-backed executive summary and formal award recommendation with status `AWAITING_HUMAN_APPROVAL`.

### Phase 1.6: Multi-Agent Orchestrator & Persistent Shared Scorecard
- **Goal**: Orchestrate multi-vendor evaluations using Microsoft Agent Framework workflow capabilities with persistent transactional state.
- **Tasks**:
  1. Implement orchestrator engine (`agents/orchestrator.py`):
     - Step 1: Ingest tender & trigger Criteria Agent.
     - Step 2: Validate extracted criteria; persist to database.
     - Step 3: Parallel fan-out: Execute Compliance Agent across all registered vendor bids.
     - Step 4: Compliance Gate: Separate compliant vendors from disqualified/unclear vendors.
     - Step 5: Parallel execution of Technical Scorer and Commercial Scorer for compliant vendors.
     - Step 6: Trigger Award Manager to compute deterministic composite scores, generate rankings, and assemble the final scorecard.
  2. Implement shared scorecard persistence manager (`services/scorecard_manager.py`) storing intermediate agent outputs, execution logs, and final scores.

### Phase 1.7: FastAPI Application & Real-Time SSE Streaming Endpoints
- **Goal**: Expose a clean, asynchronous REST API with real-time Server-Sent Events (SSE) for front-end streaming.
- **Tasks**:
  1. Build API endpoints (`api/v1/`):
     - `POST /api/v1/tenders/upload`: Upload tender document and trigger criteria extraction.
     - `GET /api/v1/tenders/{id}/criteria`: Retrieve and review extracted criteria.
     - `POST /api/v1/tenders/{id}/criteria/confirm`: Confirm or adjust criteria.
     - `POST /api/v1/vendors/upload`: Upload vendor proposals and pricing documents.
     - `POST /api/v1/evaluations/run`: Launch multi-agent evaluation pipeline.
     - `GET /api/v1/evaluations/{run_id}/stream`: Real-time SSE stream of agent actions, logs, and state transitions.
     - `GET /api/v1/evaluations/{run_id}/scorecard`: Retrieve persistent shared scorecard.
     - `POST /api/v1/evaluations/{run_id}/sign-off`: Submit human review decision (approve, reject, override).
  2. Configure CORS, static file serving, and exception handlers.

### Phase 1.8: Verification, Test Suite & Baseline Benchmarking
- **Goal**: Validate Part 1 with a comprehensive Pytest test suite covering all units, contracts, and workflows.
- **Tasks**:
  1. Write unit tests for Pydantic contracts and mathematical scoring engine.
  2. Write integration tests for each agent module using mock LLM completions.
  3. Write orchestrator integration tests simulating a 3-vendor tender evaluation.
  4. Verify that non-compliant vendors are properly disqualified and that all scores include valid evidence citations.

---

## PART 2: Frontend Dashboard, Real-Time Orchestration Visualizer, Evidence Inspector, Human Sign-Off Workflow & Production Hardening

### Phase 2.1: React + TypeScript Project Setup & Component Architecture
- **Goal**: Initialize a responsive, modern frontend using React 19, TypeScript, Vite, and TailwindCSS.
- **Tasks**:
  1. Initialize React + Vite project in `frontend/`.
  2. Configure TailwindCSS, Lucide React icons, and utility classes.
  3. Setup routing (React Router) and data synchronization (TanStack React Query).
  4. Create shared UI primitives (Button, Modal, Drawer, Badge, Card, Progress Bar, Table).

### Phase 2.2: Tender & Vendor Upload Management Interface
- **Goal**: Provide an intuitive interface for uploading RFP documents and managing vendor submissions.
- **Tasks**:
  1. Implement drag-and-drop file upload for tender documents with PDF/DOCX preview.
  2. Build Criteria Confirmation screen: displays extracted mandatory requirements, technical criteria weights, and commercial formulas, allowing human procurement officers to inspect and confirm before vendor evaluation.
  3. Build multi-vendor bid management panel: allows adding multiple vendors dynamically and uploading their technical and commercial proposal files.

### Phase 2.3: Real-Time Multi-Agent Execution Pipeline Visualizer
- **Goal**: Deliver a transparent, visual monitoring experience that streams live agent activity.
- **Tasks**:
  1. Connect to SSE endpoint (`/api/v1/evaluations/{run_id}/stream`).
  2. Implement interactive agent pipeline graph displaying the five agents with live status badges (`Idle`, `Running`, `Completed`, `Failed`, `Flagged`).
  3. Build streaming activity log panel displaying agent thoughts, tool invocations, and intermediate evaluation milestones in real time.

### Phase 2.4: Dynamic Weighted Scorecard & Multi-Vendor Comparison Matrix
- **Goal**: Render the final persistent shared scorecard with detailed comparative views.
- **Tasks**:
  1. Build multi-vendor comparison scorecard table:
     - Eligibility / Compliance status column (`PASS`, `FAIL`, `UNCLEAR`).
     - Technical criterion score breakdown with max points and weighted contributions.
     - Commercial bid price and calculated commercial score.
     - Composite total score and final ranking.
  2. Build interactive radar and bar chart visualisations (e.g., using Chart.js or Recharts) comparing vendor technical competencies side-by-side.

### Phase 2.5: Evidence & Citation Drill-Down Drawer
- **Goal**: Enable procurement auditors to verify the factual basis of every score.
- **Tasks**:
  1. Implement click-to-inspect on any score or compliance verdict.
  2. Open sliding Evidence Drawer displaying:
     - Exact source document name.
     - Page number and section reference.
     - Verbatim excerpt cited by the agent.
     - Agent reasoning and confidence score.

### Phase 2.6: Human-in-the-Loop Review & Award Sign-Off Interface
- **Goal**: Enforce human governance by requiring explicit human sign-off before any award decision is finalised.
- **Tasks**:
  1. Build Human Review Panel highlighting:
     - Disqualified vendors and explicit grounds for disqualification.
     - Items flagged as `UNCLEAR` requiring human determination.
     - Scoring anomalies (e.g., abnormal price deviations).
  2. Implement manual score override controls with mandatory audit justification notes.
  3. Implement digital sign-off workflow: procurement officer enters name, role, decision (`APPROVED`, `REJECTED`, `MODIFIED`), and submits the final record.
  4. Build printable/downloadable PDF Procurement Evaluation Summary Report.

### Phase 2.7: PostgreSQL Migration Verification & Dockerization
- **Goal**: Validate production readiness by transitioning from SQLite to PostgreSQL and packaging the system.
- **Tasks**:
  1. Verify database migration from SQLite to PostgreSQL (`postgresql+asyncpg`) with zero changes to application code.
  2. Verify vector store migration from ChromaDB to `pgvector`.
  3. Create production `Dockerfile` for backend and frontend.
  4. Create `docker-compose.yml` orchestrating PostgreSQL (with `pgvector`), FastAPI backend, and React frontend.

### Phase 2.8: Comprehensive End-to-End System Testing & Acceptance Audit
- **Goal**: Verify full end-to-end functionality, security controls, and performance.
- **Tasks**:
  1. Execute full end-to-end test scenarios with realistic multi-vendor procurement packages (e.g., IT Infrastructure RFP with 3 competing vendors).
  2. Test prompt injection resilience with adversarial vendor bid text attempting to alter scoring rules.
  3. Verify that all scores are 100% reproducible and deterministic.
  4. Final documentation review and deployment readiness checklist.

