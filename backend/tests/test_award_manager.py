import pytest
from decimal import Decimal
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from backend.app.db.base import Base
from backend.app.db.models.tender import Tender
from backend.app.db.models.vendor import Vendor
from backend.app.db.models.criteria import EvaluationPlan, MandatoryRequirement
from backend.app.schemas.compliance import ComplianceResultCreate, ComplianceStatusEnum
from backend.app.schemas.scorecard import ScorecardCreate, ScoreTypeEnum
from backend.app.services.scorecard_service import ScorecardService
from backend.app.agents.award_manager import AwardManager
from backend.app.schemas.award import AwardRecommendationStatusEnum


@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_award_manager_deterministic_evaluation(db_session):
    scorecard_service = ScorecardService(db_session)
    award_manager = AwardManager(scorecard_service)

    # 1. Create Tender and Plan
    tender = Tender(
        id="tender-award-001",
        reference_number="TND-2026-AWD",
        title="Enterprise Data Warehouse Procurement",
        issuing_organization="Ministry of Finance",
    )
    db_session.add(tender)
    await db_session.commit()

    plan = EvaluationPlan(
        id="plan-award-001",
        tender_id=tender.id,
        version=1,
        technical_weight=Decimal("0.70"),
        commercial_weight=Decimal("0.30"),
        price_methodology="RELATIVE_LOWEST_COST",
        price_formula_desc="Relative lowest price formula",
        plan_data="{}",
    )
    db_session.add(plan)

    req = MandatoryRequirement(
        id="req-award-001",
        tender_id=tender.id,
        requirement_code="MR-01",
        category="SECURITY",
        title="ISO 27001 Certification",
        description="Valid certificate required",
        pass_criteria="Certificate provided",
    )
    db_session.add(req)
    await db_session.commit()

    # 2. Create 3 Vendors
    vendor_a = Vendor(id="vendor-a", name="Vendor Alpha Ltd", registration_number="REG-A")
    vendor_b = Vendor(id="vendor-b", name="Vendor Beta Corp", registration_number="REG-B")
    vendor_c = Vendor(id="vendor-c", name="Vendor Gamma Systems", registration_number="REG-C")
    db_session.add_all([vendor_a, vendor_b, vendor_c])
    await db_session.commit()

    # 3. Initialize Run
    run = await scorecard_service.initialize_run(tender.id)

    # 4. Record Compliance: A: Pass, B: Pass, C: Disqualified
    await scorecard_service.record_compliance_result(
        ComplianceResultCreate(
            run_id=run.id,
            vendor_id=vendor_a.id,
            requirement_id=req.id,
            status=ComplianceStatusEnum.PASS,
            findings="Certificate verified.",
            is_disqualified=False,
            requires_human_review=False,
        )
    )
    await scorecard_service.record_compliance_result(
        ComplianceResultCreate(
            run_id=run.id,
            vendor_id=vendor_b.id,
            requirement_id=req.id,
            status=ComplianceStatusEnum.PASS,
            findings="Certificate verified.",
            is_disqualified=False,
            requires_human_review=False,
        )
    )
    await scorecard_service.record_compliance_result(
        ComplianceResultCreate(
            run_id=run.id,
            vendor_id=vendor_c.id,
            requirement_id=req.id,
            status=ComplianceStatusEnum.FAIL,
            findings="Missing mandatory certificate.",
            is_disqualified=True,
            requires_human_review=False,
        )
    )

    # 5. Record Technical Scores (Tech weight 0.70)
    # Vendor A: Tech 90.00
    await scorecard_service.record_scorecard_entry(
        ScorecardCreate(
            run_id=run.id,
            vendor_id=vendor_a.id,
            score_type=ScoreTypeEnum.TECHNICAL,
            raw_points=Decimal("90.00"),
            max_points=Decimal("100.00"),
            weight=Decimal("1.0000"),
            weighted_score=Decimal("90.00"),
            normalized_score=Decimal("90.00"),
        )
    )
    # Vendor B: Tech 75.00
    await scorecard_service.record_scorecard_entry(
        ScorecardCreate(
            run_id=run.id,
            vendor_id=vendor_b.id,
            score_type=ScoreTypeEnum.TECHNICAL,
            raw_points=Decimal("75.00"),
            max_points=Decimal("100.00"),
            weight=Decimal("1.0000"),
            weighted_score=Decimal("75.00"),
            normalized_score=Decimal("75.00"),
        )
    )
    # Vendor C: Tech 98.00 (High tech, but disqualified)
    await scorecard_service.record_scorecard_entry(
        ScorecardCreate(
            run_id=run.id,
            vendor_id=vendor_c.id,
            score_type=ScoreTypeEnum.TECHNICAL,
            raw_points=Decimal("98.00"),
            max_points=Decimal("100.00"),
            weight=Decimal("1.0000"),
            weighted_score=Decimal("98.00"),
            normalized_score=Decimal("98.00"),
        )
    )

    # 6. Record Commercial Prices
    # Vendor A: $3,200,000
    await scorecard_service.record_scorecard_entry(
        ScorecardCreate(
            run_id=run.id,
            vendor_id=vendor_a.id,
            score_type=ScoreTypeEnum.COMMERCIAL,
            raw_points=Decimal("3200000.00"),
            max_points=Decimal("100.00"),
            weight=Decimal("0.30"),
        )
    )
    # Vendor B: $2,800,000 (Lowest eligible price)
    await scorecard_service.record_scorecard_entry(
        ScorecardCreate(
            run_id=run.id,
            vendor_id=vendor_b.id,
            score_type=ScoreTypeEnum.COMMERCIAL,
            raw_points=Decimal("2800000.00"),
            max_points=Decimal("100.00"),
            weight=Decimal("0.30"),
        )
    )
    # Vendor C: $2,000,000 (Lowest overall, but DISQUALIFIED, so it cannot set the benchmark)
    await scorecard_service.record_scorecard_entry(
        ScorecardCreate(
            run_id=run.id,
            vendor_id=vendor_c.id,
            score_type=ScoreTypeEnum.COMMERCIAL,
            raw_points=Decimal("2000000.00"),
            max_points=Decimal("100.00"),
            weight=Decimal("0.30"),
        )
    )

    # 7. Execute AwardManager
    recommendation = await award_manager.run(run_id=run.id, tender_id=tender.id)

    # 8. Assertions
    assert recommendation is not None
    assert recommendation.status == AwardRecommendationStatusEnum.RECOMMENDED_AWAITING_APPROVAL
    # Vendor C must not be winner
    assert recommendation.recommended_vendor_id == vendor_a.id
    assert recommendation.recommended_vendor_name == "Vendor Alpha Ltd"
    assert recommendation.runner_up_vendor_id == vendor_b.id
    assert recommendation.runner_up_vendor_name == "Vendor Beta Corp"

    # Verify deterministic arithmetic:
    # Lowest eligible price is Vendor B at 2,800,000 (NOT Vendor C at 2,000,000)
    # Vendor B commercial score: (2.8 / 2.8) * 100 * 0.30 = 30.00 weighted pts
    # Vendor B technical score: 75.0 * 0.70 = 52.50 weighted pts
    # Vendor B composite: 52.50 + 30.00 = 82.50
    #
    # Vendor A commercial score: (2.8 / 3.2) * 100 = 87.50 * 0.30 = 26.25 weighted pts
    # Vendor A technical score: 90.0 * 0.70 = 63.00 weighted pts
    # Vendor A composite: 63.00 + 26.25 = 89.25
    #
    # 89.25 > 82.50 -> Vendor A wins!
    assert float(recommendation.winning_composite_score) == pytest.approx(89.25, 0.01)

    # 9. Verify scorecard records in DB
    final_card = await scorecard_service.get_shared_scorecard(run.id)
    summaries = {s.vendor_id: s for s in final_card.vendor_summaries}

    assert summaries[vendor_a.id].rank == 1
    assert float(summaries[vendor_a.id].composite_score) == pytest.approx(89.25, 0.01)

    assert summaries[vendor_b.id].rank == 2
    assert float(summaries[vendor_b.id].composite_score) == pytest.approx(82.50, 0.01)

    assert summaries[vendor_c.id].is_disqualified is True
    assert summaries[vendor_c.id].rank is None
