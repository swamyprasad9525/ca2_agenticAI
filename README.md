# Tender and Procurement Evaluation System

Production-oriented, multi-agent AI application designed to evaluate multiple vendor bids against formal tender documents and recommend the most suitable eligible vendor through an evidence-based, mathematically deterministic weighted scorecard.

---

## 1. System Overview

- **Multi-Agent Architecture**: 5 specialized agents (Criteria Agent, Compliance Agent, Technical Scorer, Commercial Scorer, Award Manager) coordinated by an asynchronous `EvaluationOrchestrator` using genuine fan-out/fan-in parallel execution.
- **Zero Arithmetic Hallucinations**: Scoring formulas, criteria weights, composite sums, and rankings are calculated strictly by a deterministic Python calculation engine (`ScoringEngine`) using `decimal.Decimal`.
- **Evidence-First Retrieval**: Every compliance finding and technical score is anchored to an `EvidenceReference` linking to the source document, page number, clause, and verbatim quote.
- **Dual-Stage Persistence**: Clean SQLAlchemy 2.0 async persistence (SQLite with WAL for rapid local dev; zero-code migration to PostgreSQL with `pgvector`).
- **Human Governance**: Produces formal recommendations with status `AWAITING_HUMAN_APPROVAL`; legally binding award authority remains exclusively with authorized human procurement officers.
- **Full-Stack Application**: FastAPI ASGI backend with Server-Sent Events/status streaming and React 18 + TypeScript + TailwindCSS client.
- **Export & Audit Capabilities**: One-click download of official PDF Evaluation Dossiers (via ReportLab), CSV Scorecards, and full JSON audit archives.

---

## 2. Directory Structure

```
.
├── AGENTS.md                               # Permanent multi-agent operating rules & constraints
├── README.md                               # Startup instructions and project overview
├── pytest.ini                              # Pytest configuration
├── requirements.txt                        # Backend dependencies
├── .env.example                            # Template environment configuration
├── docs/
│   ├── FINAL_ARCHITECTURE.md               # Delivered system architecture & diagrams
│   ├── AGENT_RESPONSIBILITIES.md           # 5 agents + orchestrator boundaries & rules
│   ├── RAG_IMPLEMENTATION.md               # Parser, chunker, vector store, and citations
│   ├── ORCHESTRATION_FLOW.md               # Fan-out/fan-in concurrency & workflow gates
│   ├── SCORECARD_CALCULATION.md            # Zero-hallucination deterministic math engine
│   ├── API_DOCUMENTATION.md                # REST API endpoints and sample payloads
│   ├── TESTING_REPORT.md                   # Comprehensive QA and verification report
│   ├── DEMO_GUIDE.md                       # Walkthrough guide and quickstart
│   ├── DATA_CONTRACTS.md                   # Authoritative Pydantic v2 schemas & JSON contracts
│   ├── DECISIONS.md                        # Architecture Decision Records (ADRs 001-008)
│   └── PROJECT_PLAN.md                     # Implementation roadmap
├── backend/
│   ├── app/
│   │   ├── main.py                         # FastAPI ASGI entrypoint, CORS, exception handlers
│   │   ├── api/
│   │   │   ├── deps.py                     # Dependency injection (database, services)
│   │   │   └── v1/
│   │   │       ├── api.py                  # API v1 router aggregator
│   │   │       ├── tenders.py              # Tender creation, retrieval, RFP document upload
│   │   │       ├── vendors.py              # Vendor registration, bid submission, proposal uploads
│   │   │       ├── evaluations.py          # Multi-agent evaluation run, recommendation, sign-off, PDF/CSV/JSON exports
│   │   │       └── scorecards.py           # Shared scorecard retrieval & transactional entries
│   │   ├── core/
│   │   │   ├── config.py                   # Pydantic-settings configuration & environment parsing
│   │   │   ├── logging.py                  # Structured enterprise application logging
│   │   │   └── exceptions.py               # Custom domain exceptions & HTTP error envelopes
│   │   ├── db/
│   │   │   ├── base.py                     # DeclarativeBase & TimestampMixin
│   │   │   ├── session.py                  # Async SQLAlchemy session management & SQLite pragmas
│   │   │   └── models/                     # SQLAlchemy 2.0 ORM Entities
│   │   ├── schemas/                        # Pydantic v2 Data Transfer Objects (DTOs)
│   │   ├── repositories/                   # Transactional Repository Data Access Layer
│   │   ├── services/                       # Business Logic Layer (Scorecard, ScoringEngine, Reports)
│   │   ├── rag/                            # Retrieval-Augmented Generation Subsystem
│   │   ├── agents/                         # 5 Specialized AI Agents (Criteria, Compliance, Technical, Commercial, Award)
│   │   └── orchestrator/                   # EvaluationOrchestrator (Fan-out/fan-in parallel workflow)
│   ├── scripts/
│   │   └── seed_demo.py                    # One-command realistic database & vector store demo seeder
│   └── tests/                              # Pytest Test Suite (32 automated tests, 100% pass, 83% coverage)
└── frontend/                               # React 18 + TypeScript + Vite + TailwindCSS
    ├── src/
    │   ├── types/                          # TypeScript definitions matching backend contracts
    │   ├── services/api.ts                 # Typed API integration client
    │   ├── components/                     # Reusable UI primitives (Card, Badge, Modal, Nav, Sidebar)
    │   └── pages/                          # Enterprise procurement pages (Dashboard, Tenders, Bids, Workspace, Scorecard, Reports)
    ├── package.json
    └── vite.config.ts
```

---

## 3. Quickstart Guide

### 3.1 Backend Setup
```bash
# 1. Activate Virtual Environment
.\.venv\Scripts\activate

# 2. Run All Automated Tests (32/32 tests, 83% coverage)
pytest -v

# 3. Seed Realistic Procurement Demo Data (Optional, recommended for instant UI exploration)
python -m backend.scripts.seed_demo

# 4. Launch Backend ASGI Server
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```
Swagger UI will be live at: `http://localhost:8000/docs`.

### 3.2 Frontend Setup
```bash
# In a separate terminal
cd frontend

# Verify production build
npm run build

# Launch development server
npm run dev
```
Client application will be live at: `http://localhost:5173`.

---

## 4. Automated 4-Vendor E2E Demonstration

Run the automated multi-agent demonstration test:
```bash
pytest backend/tests/test_e2e_demo.py -v -s
```

This simulates a full procurement lifecycle across 4 competing vendors:
- **Vendor A (Alpha Cloud Systems)**: Compliant, superior architecture, competitive price -> **Recommended Winner (Rank 1, 92.47 pts)**.
- **Vendor B (Beta Data Solutions)**: Compliant, good technical proposal, higher price -> **Runner-Up (Rank 2, 78.11 pts)**.
- **Vendor C (Gamma Network Innovations)**: In-progress security certification -> **Flagged for Human Review**.
- **Vendor D (Delta Legacy Technologies)**: Missing mandatory ISO certificate -> **Disqualified** (Technical scoring bypassed).
- **Human Governance Sign-Off**: Simulated statutory sign-off by Chief Procurement Officer Marcus Vance (`APPROVE_AWARD`).
- **Reports Export**: Verifies PDF Dossier, CSV Scorecard, and JSON Audit Archive generation.
