# ORCHESTRATION_FLOW.md — Multi-Agent Concurrency & Workflow Gates

## 1. Orchestration Architecture

The multi-agent workflow is orchestrated by `EvaluationOrchestrator` (`backend/app/orchestrator/evaluation_orchestrator.py`), enforcing sequential phase gates, concurrent fan-out parallel vendor evaluation, fan-in synchronization, and transactional scorecard commits.

```mermaid
sequenceDiagram
    autonumber
    actor Officer as Procurement Officer / API
    participant Orch as EvaluationOrchestrator
    participant CA as Criteria Agent
    participant CmpA as Compliance Agent (x N)
    participant TS as Technical Scorer (x N)
    participant CS as Commercial Scorer (x N)
    participant SS as ScorecardService (DB)
    participant AM as Award Manager
    participant Math as ScoringEngine

    Officer->>Orch: execute_evaluation_workflow(run_id, tender_id, vendor_ids)
    
    rect rgb(238, 242, 255)
        Note over Orch,CA: Phase 1: Criteria Extraction & Verification
        Orch->>SS: update_status("EXTRACTING_CRITERIA")
        Orch->>CA: run(tender_id)
        CA->>SS: record_criteria_and_plan(EvaluationPlanDTO)
        CA-->>Orch: EvaluationPlanDTO
    end

    rect rgb(240, 253, 244)
        Note over Orch,CS: Phase 2 & 3: Concurrent Fan-Out Vendor Scoring
        Orch->>SS: update_status("EVALUATING_VENDORS")
        par Across all N Vendors simultaneously (asyncio.gather)
            Orch->>CmpA: run(vendor_id, plan)
            CmpA->>SS: record_compliance_result(PASS/FAIL/UNCLEAR)
            CmpA-->>Orch: compliance_findings
            
            alt Compliant / Eligible Bidder
                par Parallel Technical & Commercial Scoring
                    Orch->>TS: run(vendor_id, plan)
                    TS->>SS: record_scorecard_entry(TECHNICAL)
                    TS-->>Orch: tech_scores
                and
                    Orch->>CS: run(vendor_id, plan)
                    CS->>SS: record_scorecard_entry(COMMERCIAL, price)
                    CS-->>Orch: comm_score
                end
            else Disqualified Bidder (Failed Mandatory Requirement)
                Note over Orch,TS: Compliance Gate Triggered
                Orch->>CS: run(vendor_id, plan) [Extract price only for audit]
                CS->>SS: record_scorecard_entry(COMMERCIAL, price)
                CS-->>Orch: comm_score
            end
        end
    end

    rect rgb(254, 243, 199)
        Note over Orch,SS: Phase 4: Fan-In Synchronization
        Orch->>SS: update_status("SYNCHRONIZING_RESULTS")
        Note over Orch,SS: Verify all N vendor results are committed transactionally
    end

    rect rgb(255, 237, 213)
        Note over Orch,AM: Phase 5: Award Recommendation Dossier
        Orch->>SS: update_status("SYNTHESIZING_AWARD")
        Orch->>AM: run(run_id, tender_id)
        AM->>SS: get_shared_scorecard(run_id)
        AM->>Math: calculate_relative_lowest_price_scores(prices, eligible_vendors)
        Math-->>AM: normalized & weighted commercial scores
        AM->>Math: calculate_composite_score(tech, comm) & rank_vendors()
        Math-->>AM: final ranks & composite points
        AM->>SS: record_scorecard_entry(COMPOSITE for all vendors)
        AM->>SS: save_award_recommendation(AwardRecommendationDTO)
        AM->>SS: update_status("AWAITING_HUMAN_APPROVAL")
        AM-->>Orch: AwardRecommendationDTO
    end

    Orch-->>Officer: Complete Recommendation Dossier (Awaiting Sign-Off)
```

---

## 2. Key Workflow Gates

### Gate 1: Criteria Approved Gate
- Before evaluating vendor bids, the system guarantees that mandatory requirements, technical criteria, weights, and commercial formulas exist and are valid.
- If not present, `CriteriaAgent` parses the RFP via RAG.
- Technical weights must sum to exactly 1.0000 ($\pm 0.0001$). Discrepancies abort the workflow with `CriteriaValidationError`.

### Gate 2: Compliance Screening Gate
- `ComplianceAgent` screens each vendor bid against every mandatory requirement.
- Any requirement evaluated as `FAIL` immediately flags the vendor as `is_disqualified = True`.
- **Compliance Gate Behavior**: Disqualified vendors have qualitative technical scoring bypassed (`len(technical_scores) == 0`). Their pricing is still captured for auditable cost benchmarking, but they cannot win or set the lowest-price benchmark.
- Any requirement evaluated as `UNCLEAR` flags the vendor as `requires_human_review = True` and records an entry in the procurement risk assessment.

### Gate 3: Relative Lowest Price Benchmark Gate
- When executing the commercial formula, the lowest price ($P_{min}$) is computed **strictly among eligible (compliant) bidders**:
  $$P_{min} = \min \{ P_v \mid v \in \text{CompliantVendors} \}$$
- Disqualified vendors submitting low-ball prices are excluded from establishing $P_{min}$, preventing predatory or non-compliant bids from distorting the scoring curve.

### Gate 4: Human Governance Sign-Off Gate
- The multi-agent evaluation pipeline concludes with status `AWAITING_HUMAN_APPROVAL`.
- An authorized procurement officer reviews the dossier and submits a signed decision via `POST /api/v1/evaluations/{run_id}/sign-off`:
  - `APPROVE_AWARD`: Formal award approval. Status advances to `AWARD_APPROVED`.
  - `OVERRIDE_WINNER`: Officer selects alternate compliant vendor with recorded justification. Status advances to `AWARD_OVERRIDDEN`.
  - `REJECT_ALL`: All bids rejected. Status advances to `AWARD_REJECTED`.

