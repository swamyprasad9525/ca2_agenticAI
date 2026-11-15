import json
from decimal import Decimal
from typing import Any, Dict, List, Optional
from sqlalchemy import select

from backend.app.core.logging import logger
from backend.app.agents.base import BaseAgent
from backend.app.db.models.criteria import EvaluationPlan
from backend.app.db.models.vendor import Vendor
from backend.app.schemas.award import AwardRecommendationDTO, AwardRecommendationStatusEnum
from backend.app.schemas.scorecard import ScorecardCreate, ScoreTypeEnum
from backend.app.services.scorecard_service import ScorecardService
from backend.app.services.scoring_engine import ScoringEngine


class AwardManager(BaseAgent):
    """
    Agent 5: Award Manager.
    Sole Responsibility:
    1. Aggregates compliance findings, technical scores, and commercial scores from the persistent shared scorecard.
    2. Executes zero-hallucination deterministic cross-vendor commercial formulas and composite weighting.
    3. Ranks eligible vendors, separates disqualified vendors, and persists final composite scorecard entries.
    4. Synthesizes an executive audit recommendation dossier with citations, justifications, and risk assessments.
    5. Preserves human governance: Status is strictly RECOMMENDED_AWAITING_APPROVAL.
    """

    def __init__(self, scorecard_service: ScorecardService):
        super().__init__("AwardManager", scorecard_service)

    async def run(self, run_id: str, tender_id: Optional[str] = None, **kwargs: Any) -> AwardRecommendationDTO:
        logger.info(f"AwardManager started synthesis for EvaluationRun {run_id}")
        exec_id = None
        try:
            exec_rec = await self.scorecard_service.start_agent_execution(
                run_id=run_id,
                agent_name=self.name,
                idempotency_key=f"award-mgr-{run_id}",
            )
            exec_id = exec_rec.id
        except Exception as e:
            logger.warning(f"Could not start agent execution telemetry: {e}")

        # 1. Fetch current shared scorecard state
        shared_card = await self.scorecard_service.get_shared_scorecard(run_id)
        if not tender_id:
            tender_id = shared_card.tender_id

        # 2. Query EvaluationPlan weights
        tech_weight = Decimal("0.70")
        comm_weight = Decimal("0.30")
        tie_rule = "HIGHEST_TECHNICAL"

        stmt = select(EvaluationPlan).where(EvaluationPlan.tender_id == tender_id)
        plan_result = await self.scorecard_service.execute_query(stmt)
        plan = plan_result.scalars().first()
        if plan:
            tech_weight = plan.technical_weight if plan.technical_weight <= Decimal("1.0") else (plan.technical_weight / Decimal("100.0"))
            comm_weight = plan.commercial_weight if plan.commercial_weight <= Decimal("1.0") else (plan.commercial_weight / Decimal("100.0"))
            if plan.tie_breaking_rule:
                tie_rule = plan.tie_breaking_rule

        # 3. Gather per-vendor data
        vendor_prices: Dict[str, Decimal] = {}
        vendor_tech_totals: Dict[str, Decimal] = {}
        vendor_compliance_status: Dict[str, Dict[str, Any]] = {}

        for summary in shared_card.vendor_summaries:
            v_id = summary.vendor_id

            # Technical points: sum of weighted scores of all technical criteria (out of 100)
            tech_pts = sum((s.weighted_score for s in summary.technical_scores if s.weighted_score is not None), Decimal("0.0"))
            vendor_tech_totals[v_id] = tech_pts

            # Commercial price extracted from commercial scorecard entry raw points
            if summary.commercial_score and summary.commercial_score.raw_points:
                vendor_prices[v_id] = summary.commercial_score.raw_points
            else:
                vendor_prices[v_id] = Decimal("1000000.00")

            vendor_compliance_status[v_id] = {
                "name": summary.vendor_name,
                "is_disqualified": summary.is_disqualified,
                "disqualification_reasons": summary.disqualification_reasons,
                "requires_human_review": summary.requires_human_review,
            }

        # 4. Filter eligible vs disqualified
        eligible_v_ids = [vid for vid, info in vendor_compliance_status.items() if not info["is_disqualified"]]
        disqualified_v_ids = [vid for vid, info in vendor_compliance_status.items() if info["is_disqualified"]]

        # 5. Deterministic Commercial Scoring (Relative Lowest Price among eligible bidders)
        comm_results = ScoringEngine.calculate_relative_lowest_price_scores(
            vendor_prices=vendor_prices,
            commercial_weight=comm_weight,
            eligible_vendor_ids=eligible_v_ids,
        )

        # Update commercial score entries in DB with finalized normalized & weighted scores
        for v_id, c_data in comm_results.items():
            norm_c = c_data["normalized_commercial_score"]
            weight_c = c_data["weighted_commercial_score"]

            await self.scorecard_service.record_scorecard_entry(
                ScorecardCreate(
                    run_id=run_id,
                    vendor_id=v_id,
                    score_type=ScoreTypeEnum.COMMERCIAL,
                    raw_points=vendor_prices.get(v_id),
                    max_points=Decimal("100.00"),
                    weight=comm_weight,
                    weighted_score=weight_c,
                    normalized_score=norm_c,
                    justification=f"Deterministic commercial evaluation: Lowest eligible price = {c_data['lowest_eligible_price']:,.2f}, Vendor price = {c_data['evaluated_price']:,.2f}. Score = {norm_c:.2f}/100.",
                    idempotency_key=f"comm-score-{run_id}-{v_id}",
                )
            )

        # 6. Composite Scoring ($W_{tech} \times Score_{tech} + W_{comm} \times Score_{comm}$)
        vendors_to_rank: List[Dict[str, Any]] = []

        for v_id, info in vendor_compliance_status.items():
            is_disq = info["is_disqualified"]
            tech_raw = vendor_tech_totals.get(v_id, Decimal("0.0"))
            tech_weighted = (tech_raw * tech_weight).quantize(Decimal("0.01"))

            comm_info = comm_results.get(v_id, {})
            comm_weighted = comm_info.get("weighted_commercial_score", Decimal("0.0"))

            composite = ScoringEngine.calculate_composite_score(tech_weighted, comm_weighted) if not is_disq else Decimal("0.00")

            vendors_to_rank.append({
                "vendor_id": v_id,
                "vendor_name": info["name"],
                "is_disqualified": is_disq,
                "disqualification_reasons": info["disqualification_reasons"],
                "requires_human_review": info["requires_human_review"],
                "technical_score": tech_raw,
                "technical_weighted": tech_weighted,
                "commercial_weighted": comm_weighted,
                "commercial_price": vendor_prices.get(v_id, Decimal("0.0")),
                "composite_score": composite,
            })

        # 7. Deterministic Ranking
        ranked_vendors = ScoringEngine.rank_vendors(vendors_to_rank, tie_breaker_rule=tie_rule)

        # Persist COMPOSITE scorecards with final ranks
        for item in ranked_vendors:
            v_id = item["vendor_id"]
            comp_score = item["composite_score"]
            v_rank = item["rank"]
            is_disq = item["is_disqualified"]

            if is_disq:
                justification = f"Disqualified during mandatory compliance screening: {'; '.join(item['disqualification_reasons'])}"
            else:
                justification = (
                    f"Composite weighted score: Technical ({item['technical_weighted']:.2f} pts) + "
                    f"Commercial ({item['commercial_weighted']:.2f} pts) = {comp_score:.2f}/100.00. "
                    f"Final Ranking: Rank {v_rank}."
                )

            await self.scorecard_service.record_scorecard_entry(
                ScorecardCreate(
                    run_id=run_id,
                    vendor_id=v_id,
                    score_type=ScoreTypeEnum.COMPOSITE,
                    raw_points=item["technical_score"],
                    max_points=Decimal("100.00"),
                    weight=Decimal("1.0000"),
                    weighted_score=comp_score,
                    normalized_score=comp_score,
                    rank=v_rank,
                    justification=justification,
                    idempotency_key=f"comp-score-{run_id}-{v_id}",
                )
            )

        # 8. Identify Winner & Runner-up
        winner = next((v for v in ranked_vendors if v["rank"] == 1 and not v["is_disqualified"]), None)
        runner_up = next((v for v in ranked_vendors if v["rank"] == 2 and not v["is_disqualified"]), None)

        # 9. Synthesize Executive Dossier & Risk Assessment
        risks: List[str] = []
        if any(v["requires_human_review"] for v in ranked_vendors):
            unclear_names = [v["vendor_name"] for v in ranked_vendors if v["requires_human_review"]]
            risks.append(f"Compliance Ambiguity: Vendor(s) {', '.join(unclear_names)} have items marked UNCLEAR requiring human verification.")

        if winner and runner_up:
            score_diff = winner["composite_score"] - runner_up["composite_score"]
            if score_diff < Decimal("3.0"):
                risks.append(
                    f"Close Margin: Top two vendors differ by only {score_diff:.2f} composite points. High scrutiny recommended."
                )

        if not eligible_v_ids:
            risks.append("Procurement Invalidation Risk: 100% of vendor submissions failed mandatory compliance checks.")

        # Build Executive Summary & Justification
        if winner:
            exec_summary = (
                f"Multi-agent procurement evaluation successfully completed across {len(shared_card.vendor_summaries)} competing vendors. "
                f"{len(eligible_v_ids)} vendor(s) passed all mandatory compliance requirements; {len(disqualified_v_ids)} vendor(s) were disqualified. "
                f"Based on the approved tender weighting ({int(tech_weight * 100)}% Technical / {int(comm_weight * 100)}% Commercial), "
                f"{winner['vendor_name']} achieved the highest composite score of {winner['composite_score']:.2f}/100.00 (Rank 1)."
            )
            award_justification = (
                f"Recommended vendor {winner['vendor_name']} demonstrated superior overall capability with a technical score of "
                f"{winner['technical_score']:.2f}/100.00 (yielding {winner['technical_weighted']:.2f} weighted points) and a competitive commercial "
                f"quotation of {winner['commercial_price']:,.2f} (yielding {winner['commercial_weighted']:.2f} weighted points). "
                f"All mandatory legal, certification, and technical SLA prerequisites were fully satisfied with verified citations."
            )
        else:
            exec_summary = (
                f"Evaluation completed across {len(shared_card.vendor_summaries)} vendors. "
                f"No vendor achieved full compliance with mandatory tender prerequisites. All submissions are disqualified."
            )
            award_justification = "No contract award can be recommended due to zero eligible compliant vendors. Retendering or waiver required."

        # 10. Assemble Recommendation DTO
        recommendation_dto = AwardRecommendationDTO(
            run_id=run_id,
            tender_id=tender_id,
            recommended_vendor_id=winner["vendor_id"] if winner else None,
            recommended_vendor_name=winner["vendor_name"] if winner else None,
            winning_composite_score=winner["composite_score"] if winner else None,
            runner_up_vendor_id=runner_up["vendor_id"] if runner_up else None,
            runner_up_vendor_name=runner_up["vendor_name"] if runner_up else None,
            executive_summary=exec_summary,
            award_justification=award_justification,
            risk_assessment=risks,
            status=AwardRecommendationStatusEnum.RECOMMENDED_AWAITING_APPROVAL,
        )

        # 11. Persist recommendation in DB
        saved_rec = await self.scorecard_service.save_award_recommendation(recommendation_dto)

        # 12. Update evaluation run status
        await self.scorecard_service.update_status(
            run_id=run_id,
            status="AWAITING_HUMAN_APPROVAL",
            current_step="5/5: Evaluation Complete — Awaiting Procurement Officer Sign-Off",
            eligible_count=len(eligible_v_ids),
            disqualified_count=len(disqualified_v_ids),
        )

        if exec_id:
            await self.scorecard_service.complete_agent_execution(
                execution_id=exec_id,
                status="COMPLETED",
                execution_log=f"Award synthesis complete. Recommended Winner: {winner['vendor_name'] if winner else 'None'} ({winner['composite_score'] if winner else 0:.2f} pts). Status: AWAITING_HUMAN_APPROVAL.",
            )

        logger.info(f"AwardManager finalized Run {run_id}. Winner: {winner['vendor_name'] if winner else 'None'}")
        return saved_rec
