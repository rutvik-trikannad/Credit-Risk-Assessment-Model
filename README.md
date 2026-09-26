# Corporate Credit Risk Assessment Model

A SQL + Python pipeline that pulls public company financials, computes credit
ratios, scores each company-year on an AAA-to-CCC rating scale, and stress
tests the results against three macroeconomic scenarios.

## What it does

1. Pulls 4 years of income statement, balance sheet, and cash flow data for
   10 public companies across 8 sectors via the Yahoo Finance API.
2. Loads the data into a normalized SQLite database.
3. Computes 11 credit ratios per company-year (leverage, coverage, liquidity,
   cash flow strength, profitability/stability) with SQL.
4. Scores each ratio on a 0-100 scale and rolls them into a weighted
   composite score and a 7-tier letter rating (AAA through CCC).
5. Runs each company-year through 3 covenant checks (leverage, interest
   coverage, liquidity) under a base case and three stress scenarios of
   increasing severity.
6. Outputs summary charts and a multi-tab Excel workbook.

## Methodology

**Ratios (11), grouped into 5 weighted categories:**

| Category | Weight | Ratios |
|---|---|---|
| Leverage | 30% | Debt/EBITDA, Net Debt/EBITDA, Debt/Equity |
| Coverage | 25% | EBITDA/Interest, EBIT/Interest |
| Cash Flow Strength | 20% | FCF/Debt, OCF/Interest |
| Liquidity | 15% | Current Ratio, Quick Ratio |
| Profitability & Stability | 10% | EBITDA Margin, Revenue Growth Volatility |

Each ratio is scored on a linear 0-100 scale between a "worst" and "best"
breakpoint and clamped at both ends. Two adjustments sit on top of the base
scoring:

- **Sign-safety overrides**: A leverage ratio with a negative EBITDA or
  negative equity denominator produces a negative ratio value that a naive
  linear formula would score as artificially strong. These cases are
  explicitly floored to 0 instead.
- **Sector-adjusted liquidity thresholds**: Airlines and cruise lines collect
  cash for travel not yet taken, which books as a current liability and
  structurally depresses their current and quick ratios without reflecting
  real liquidity risk. Those two sectors are scored against a lower
  liquidity floor than the rest of the sample.

Composite scores map to a 7-tier letter rating (AAA, AA, A, BBB, BB, B, CCC).

**Covenant stress testing:** Each company-year is checked against a leverage
cap (Debt/EBITDA), a coverage floor (EBITDA/Interest), and a liquidity floor,
under a base case plus three EBITDA-shock scenarios (optimistic, neutral,
pessimist). The pessimist scenario is calibrated to the sample's own
worst observed year-over-year EBITDA decline. EBITDA is shocked additively
against its own magnitude rather than multiplicatively, so the shock
correctly deepens an already-negative EBITDA instead of shrinking it toward
zero.

## Sample

10 companies across 8 sectors, chosen to span the credit spectrum from
investment-grade to distressed: MSFT, COST, JNJ, SBUX, HD, OXY, F, CCL, AAL,
AMC.

## Known limitation

The stability category weights revenue growth volatility over margin
specifically to catch cyclical, commodity-exposed risk, but it only partially
corrects for it. A company like OXY, whose earnings swing with oil prices,
still scores stronger than its cyclical risk profile would suggest to a
credit analyst reading past the composite score alone.

## Repo structure

```
data/
  companies.csv           company/sector reference list
  raw_financials.csv      raw pulled financials
  credit_risk.db          SQLite database
scripts/
  01_pull_financial_data.py
  02_build_database.py
  03_calculate_ratios.py
  04_score_ratings.py
  05_covenant_stress_test.py
  06_generate_outputs.py
  schema.sql
  calculate_ratios.sql
  covenant_checks.sql
output/
  rating_by_company.png
  rating_trend_by_company.png
  covenant_stress_test.png
  credit_risk_summary.xlsx
```

## Running it

```
pip install yfinance pandas matplotlib openpyxl

python scripts/01_pull_financial_data.py
python scripts/02_build_database.py
python scripts/03_calculate_ratios.py
python scripts/04_score_ratings.py
python scripts/05_covenant_stress_test.py
python scripts/06_generate_outputs.py
```

## Stack

Python, SQLite (`sqlite3`), pandas, yfinance, matplotlib, openpyxl.
