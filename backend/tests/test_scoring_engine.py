import pytest
from decimal import Decimal
from backend.app.services.scoring_engine import ScoringEngine


def test_normalize_criterion_score_valid():
    norm = ScoringEngine.normalize_criterion_score(Decimal("30.0"), Decimal("40.0"))
    assert norm == Decimal("75.00")

    norm_zero = ScoringEngine.normalize_criterion_score(Decimal("0.0"), Decimal("50.0"))
    assert norm_zero == Decimal("0.00")

    norm_max = ScoringEngine.normalize_criterion_score(Decimal("50.0"), Decimal("50.0"))
    assert norm_max == Decimal("100.00")


def test_normalize_criterion_score_clamping():
    # Above max points clamps to 100
    norm_high = ScoringEngine.normalize_criterion_score(Decimal("60.0"), Decimal("50.0"))
    assert norm_high == Decimal("100.00")

    # Below 0 clamps to 0
    norm_neg = ScoringEngine.normalize_criterion_score(Decimal("-10.0"), Decimal("50.0"))
    assert norm_neg == Decimal("0.00")


def test_normalize_criterion_score_zero_max_raises():
    with pytest.raises(ValueError, match="Maximum points must be greater than zero"):
        ScoringEngine.normalize_criterion_score(Decimal("10.0"), Decimal("0.0"))


def test_calculate_weighted_points_fraction_and_percent():
    # Weight as fraction <= 1.0 (e.g. 0.40)
    w_frac = ScoringEngine.calculate_weighted_points(Decimal("80.00"), Decimal("0.40"))
    assert w_frac == Decimal("32.0000")

    # Weight as percentage > 1.0 (e.g. 40.0)
    w_pct = ScoringEngine.calculate_weighted_points(Decimal("80.00"), Decimal("40.0"))
    assert w_pct == Decimal("32.0000")


def test_calculate_relative_lowest_price_empty():
    res = ScoringEngine.calculate_relative_lowest_price_scores({}, Decimal("0.30"))
    assert res == {}


def test_calculate_relative_lowest_price_scores_all_cases():
    prices = {
        "v1": Decimal("100000.00"),
        "v2": Decimal("200000.00"),
        "v3": Decimal("0.00"),  # Zero price edge case
    }
    scores = ScoringEngine.calculate_relative_lowest_price_scores(
        vendor_prices=prices,
        commercial_weight=Decimal("30.0"),  # 30%
        eligible_vendor_ids=["v1", "v2"],
    )

    # v1 is lowest eligible -> 100 normalized, 30 weighted
    assert scores["v1"]["normalized_commercial_score"] == Decimal("100.00")
    assert scores["v1"]["weighted_commercial_score"] == Decimal("30.0000")

    # v2 is double the price -> 50 normalized, 15 weighted
    assert scores["v2"]["normalized_commercial_score"] == Decimal("50.00")
    assert scores["v2"]["weighted_commercial_score"] == Decimal("15.0000")

    # v3 zero price -> 0 score
    assert scores["v3"]["normalized_commercial_score"] == Decimal("0.00")
    assert scores["v3"]["weighted_commercial_score"] == Decimal("0.0000")


def test_calculate_relative_lowest_price_no_eligible_fallback():
    prices = {
        "v1": Decimal("150000.00"),
        "v2": Decimal("300000.00"),
    }
    # No eligible vendor IDs passed in
    scores = ScoringEngine.calculate_relative_lowest_price_scores(
        vendor_prices=prices,
        commercial_weight=Decimal("0.30"),
        eligible_vendor_ids=[],
    )
    assert scores["v1"]["lowest_eligible_price"] == Decimal("150000.00")
    assert scores["v1"]["normalized_commercial_score"] == Decimal("100.00")


def test_calculate_composite_score():
    comp = ScoringEngine.calculate_composite_score(Decimal("58.2540"), Decimal("28.1250"))
    assert comp == Decimal("86.38")


def test_rank_vendors_with_ties_and_disqualification():
    vendors = [
        {"vendor_id": "v-disqualified", "is_disqualified": True, "composite_score": Decimal("99.00"), "technical_score": Decimal("70.0")},
        {"vendor_id": "v-tie-lower-tech", "is_disqualified": False, "composite_score": Decimal("85.00"), "technical_score": Decimal("55.0")},
        {"vendor_id": "v-winner", "is_disqualified": False, "composite_score": Decimal("90.00"), "technical_score": Decimal("60.0")},
        {"vendor_id": "v-tie-higher-tech", "is_disqualified": False, "composite_score": Decimal("85.00"), "technical_score": Decimal("62.0")},
    ]

    ranked = ScoringEngine.rank_vendors(vendors)

    # 1. Winner
    assert ranked[0]["vendor_id"] == "v-winner"
    assert ranked[0]["rank"] == 1

    # 2. Tie broken by higher technical score
    assert ranked[1]["vendor_id"] == "v-tie-higher-tech"
    assert ranked[1]["rank"] == 2

    # 3. Lower technical score
    assert ranked[2]["vendor_id"] == "v-tie-lower-tech"
    assert ranked[2]["rank"] == 3

    # 4. Disqualified placed at bottom with rank None
    assert ranked[3]["vendor_id"] == "v-disqualified"
    assert ranked[3]["rank"] is None
