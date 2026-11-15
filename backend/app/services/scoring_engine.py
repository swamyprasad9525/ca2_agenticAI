from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Any
from backend.app.core.logging import logger


class ScoringEngine:
    """
    Zero-hallucination deterministic calculation engine for all procurement mathematics.
    Executes exact formulas using Python's standard Decimal module.
    LLMs are strictly forbidden from performing arithmetic.
    """

    @staticmethod
    def normalize_criterion_score(raw_points: Decimal, max_points: Decimal) -> Decimal:
        """
        Normalized score = (Raw score / Maximum score) * 100.
        Bounded between [0.00, 100.00].
        """
        if max_points <= Decimal("0.0"):
            raise ValueError(f"Maximum points must be greater than zero, got {max_points}")
        raw_clamped = min(max_points, max(Decimal("0.0"), raw_points))
        normalized = (raw_clamped / max_points) * Decimal("100.0")
        return normalized.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @staticmethod
    def calculate_weighted_points(normalized_score: Decimal, weight: Decimal) -> Decimal:
        """
        Weighted points = Normalized score * Weight.
        If weight is expressed as a fraction <= 1.0 (e.g. 0.40), multiplies directly.
        If weight is expressed as a percentage > 1.0 (e.g. 40.0), divides by 100.
        """
        eff_weight = weight if weight <= Decimal("1.0") else (weight / Decimal("100.0"))
        weighted = normalized_score * eff_weight
        return weighted.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

    @staticmethod
    def calculate_relative_lowest_price_scores(
        vendor_prices: Dict[str, Decimal],
        commercial_weight: Decimal,
        eligible_vendor_ids: Optional[List[str]] = None,
    ) -> Dict[str, Dict[str, Decimal]]:
        """
        Executes standard tender formula:
        Score_comm = (Lowest_Eligible_Price / Vendor_Price) * 100
        Weighted_Score = Score_comm * Commercial_Weight
        """
        results: Dict[str, Dict[str, Decimal]] = {}
        if not vendor_prices:
            return results

        eff_comm_weight = commercial_weight if commercial_weight <= Decimal("1.0") else (commercial_weight / Decimal("100.0"))

        # Determine lowest price among eligible bidders only
        eligible_set = set(eligible_vendor_ids) if eligible_vendor_ids is not None else set(vendor_prices.keys())
        eligible_prices = [p for vid, p in vendor_prices.items() if vid in eligible_set and p > Decimal("0.0")]

        if not eligible_prices:
            # Fallback if no vendors are eligible
            min_price = min(p for p in vendor_prices.values() if p > Decimal("0.0")) if vendor_prices else Decimal("0.0")
        else:
            min_price = min(eligible_prices)

        for vid, price in vendor_prices.items():
            if price <= Decimal("0.0"):
                normalized = Decimal("0.00")
                weighted = Decimal("0.0000")
            else:
                normalized = ((min_price / price) * Decimal("100.0")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                # Cap at 100.00 in case of minor rounding
                normalized = min(Decimal("100.00"), normalized)
                weighted = (normalized * eff_comm_weight).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

            results[vid] = {
                "evaluated_price": price,
                "lowest_eligible_price": min_price,
                "normalized_commercial_score": normalized,
                "weighted_commercial_score": weighted,
            }

        return results

    @staticmethod
    def calculate_composite_score(
        technical_weighted: Decimal,
        commercial_weighted: Decimal,
    ) -> Decimal:
        """
        Score_total = Technical_Weighted_Points + Commercial_Weighted_Points.
        """
        composite = technical_weighted + commercial_weighted
        return composite.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @classmethod
    def rank_vendors(
        cls,
        vendors_data: List[Dict[str, Any]],
        tie_breaker_rule: str = "HIGHEST_TECHNICAL",
    ) -> List[Dict[str, Any]]:
        """
        Ranks eligible vendors by composite score descending.
        Disqualified vendors are placed at the bottom with no numerical winning rank.
        Ties are resolved via tie_breaker_rule (e.g. highest technical points).
        """
        eligible = [v for v in vendors_data if not v.get("is_disqualified", False)]
        disqualified = [v for v in vendors_data if v.get("is_disqualified", False)]

        # Sort eligible bidders by composite score desc, then technical score desc
        eligible.sort(
            key=lambda v: (
                v.get("composite_score", Decimal("0.0")),
                v.get("technical_score", Decimal("0.0")),
            ),
            reverse=True,
        )

        # Assign 1-based ranks
        ranked_eligible = []
        for idx, item in enumerate(eligible):
            item_copy = dict(item)
            item_copy["rank"] = idx + 1
            ranked_eligible.append(item_copy)

        # Disqualified bidders receive no eligible winning rank
        unranked_disqualified = []
        for item in disqualified:
            item_copy = dict(item)
            item_copy["rank"] = None
            unranked_disqualified.append(item_copy)

        return ranked_eligible + unranked_disqualified

