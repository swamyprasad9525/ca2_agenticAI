# SCORECARD_CALCULATION.md — Zero-Hallucination Deterministic Calculation Engine

## 1. Engine Principles

All mathematical calculations, weighting, price normalizations, and rankings within the Tender and Procurement Evaluation System are executed by `ScoringEngine` (`backend/app/services/scoring_engine.py`).

1. **Zero LLM Arithmetic**: LLMs are strictly forbidden from performing mental math. All arithmetic is executed in standard Python using the `decimal.Decimal` module with explicit `ROUND_HALF_UP` rounding.
2. **Quality- and Cost-Based Selection (QCBS)**: Conforms to international standards (World Bank, UNCITRAL, Federal Acquisition Regulation / FAR).
3. **Exact Bounding**: Scores are bounded: $0.00 \le \text{NormalizedScore} \le 100.00$.

---

## 2. Mathematical Formulas

### 2.1 Technical Criterion Normalization
For each technical criterion $i$ with raw awarded points $R_i$ and maximum points $M_i$:
$$\text{NormalizedScore}_i = \left( \frac{\min(M_i, \max(0, R_i))}{M_i} \right) \times 100$$

### 2.2 Weighted Technical Score
Each criterion carries a normalized weight $w_i \in [0.0, 1.0]$, such that $\sum_{i=1}^K w_i = 1.0000$:
$$\text{WeightedPoints}_i = \text{NormalizedScore}_i \times w_i$$
The vendor's total technical score out of 100 is:
$$\text{TechScore}_{\text{total}} = \sum_{i=1}^K \text{WeightedPoints}_i$$

### 2.3 Relative Lowest Price Commercial Formula
Let $P_v$ be the total evaluated bid price of vendor $v$.
The lowest eligible price among compliant bidders is:
$$P_{min} = \min_{u \in \text{EligibleBidders}} P_u$$

For any vendor $v$:
$$\text{CommercialScore}_v = \left( \frac{P_{min}}{P_v} \right) \times 100$$
The commercial score is capped at $100.00$.
If a vendor has price $\le 0$, their commercial score is $0.00$.

### 2.4 Composite Score
Given tender weights $W_{\text{tech}}$ (e.g. 0.70) and $W_{\text{comm}}$ (e.g. 0.30) where $W_{\text{tech}} + W_{\text{comm}} = 1.0000$:
$$\text{TechnicalWeighted} = \text{TechScore}_{\text{total}} \times W_{\text{tech}}$$
$$\text{CommercialWeighted} = \text{CommercialScore}_v \times W_{\text{comm}}$$
$$\text{CompositeScore}_v = \text{TechnicalWeighted} + \text{CommercialWeighted}$$

---

## 3. Ranking & Tie-Breaking Rules

`ScoringEngine.rank_vendors()` executes deterministic sorting:
1. **Eligible Bidders**: Sorted descending by `composite_score`.
2. **Tie-Breaking**: If two eligible vendors have identical composite scores, the tie is resolved by the highest `technical_score`.
3. **Disqualified Bidders**: Assigned `rank = None` and placed at the bottom of the scorecard with clear disqualification justifications.

---

## 4. Worked Calculation Example

Consider an RFP with weights **70% Technical / 30% Commercial**:

| Vendor | Compliance | Quoted Price | Tech Score (100) | Comm Score (100) | Tech Weighted (70) | Comm Weighted (30) | Composite (100) | Final Rank |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Alpha Cloud** | PASS | \$3,100,000 | 92.00 | 93.55 | 64.40 | 28.07 | **92.47** | **Rank 1 (Winner)** |
| **Beta Data** | PASS | \$3,700,000 | 85.00 | 78.38 | 59.50 | 23.51 | **83.01** | **Rank 2 (Runner-Up)** |
| **Gamma Net** | UNCLEAR | \$2,900,000 | 80.00 | 100.00 | 56.00 | 30.00 | **86.00** | **Pending Review** |
| **Delta Tech** | FAIL | \$2,200,000 | N/A | N/A | 0.00 | 0.00 | **0.00** | **Disqualified** |

- Lowest eligible price is established by **Gamma Net** (\$2,900,000).
- Delta Tech quoted \$2,200,000 (cheapest), but was **disqualified** for missing mandatory ISO 27001; its bid was excluded from setting the benchmark.
- Alpha Cloud won with composite score **92.47**, outperforming Beta Data (**83.01**).

