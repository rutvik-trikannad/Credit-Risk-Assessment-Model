# Corporate Credit Risk Assessment Model

A SQL and Python pipeline that pulls public company financials, computes 11 credit ratios, scores every company-year on a 7-tier rating scale (AAA to CCC), and tests each one against three loan covenants under EBITDA stress scenarios. It covers 10 companies and 40 company-years, and finishes with charts and a multi-tab Excel workbook.

## Key results

| Company | Sector | Rating, latest year | Average score (0 to 100) | Covenant breaches in the base case |
|---|---|---|---|---|
| MSFT | Technology | AAA | 96.0 | 0 of 4 years |
| JNJ | Healthcare | AAA | 90.5 | 0 of 4 years |
| COST | Consumer Staples | AA | 86.4 | 0 of 4 years |
| OXY | Energy | A | 80.4 | 0 of 4 years |
| HD | Retail | BBB | 72.2 | 0 of 4 years |
| SBUX | Consumer Discretionary | BB | 62.7 | 4 of 4 years |
| F | Auto | B | 39.1 | 4 of 4 years |
| CCL | Travel/Leisure | B | 23.7 | 4 of 4 years |
| AAL | Airlines | CCC | 21.0 | 4 of 4 years |
| AMC | Media/Leisure | CCC | 7.0 | 4 of 4 years |

Half of the 40 company-years (20) breach at least one covenant before any stress is applied, and all of them belong to SBUX, F, CCL, AAL, and AMC. The five companies that pass in the base case are almost unaffected by stress. Under the most severe scenario, only 3 of those 20 passing company-years newly breach (HD in 2025 and 2026, OXY in 2024), all on the leverage test.

## What it does

1. Pulls 4 years of income statement, balance sheet, and cash flow data for 10 public companies via the Yahoo Finance API.
2. Loads the data into a normalized SQLite database.
3. Computes 11 credit ratios per company-year with SQL.
4. Scores each ratio from 0 to 100, rolls them into a weighted composite score, and maps it to a letter rating.
5. Checks each company-year against 3 covenants under a base case and three stress scenarios of increasing severity.
6. Writes summary charts and an Excel workbook.

## Methodology

**Ratios (11), grouped into 5 weighted categories**

| Category | Weight | Ratios |
|---|---|---|
| Leverage | 30% | Debt/EBITDA, Net Debt/EBITDA, Debt/Equity |
| Coverage | 25% | EBITDA/Interest, EBIT/Interest |
| Cash Flow Strength | 20% | FCF/Debt, OCF/Interest |
| Liquidity | 15% | Current Ratio, Quick Ratio |
| Profitability & Stability | 10% | EBITDA Margin, Revenue Growth Volatility |

Each ratio is scored on a straight line between a "worst" and a "best" breakpoint and capped at 0 and 100. Composite scores map to AAA (88 and above), AA (78), A (68), BBB (55), BB (42), B (28), and CCC (below 28). Inside the stability category, revenue growth volatility carries 70% of the weight and EBITDA margin 30%, so a high margin cannot hide a cyclical revenue profile. Two adjustments sit on top of the base scoring.

- **Sign-safety overrides.** A leverage ratio with a negative EBITDA or negative equity underneath it comes out negative, which a straight-line formula would score as strong. These cases are set to 0 instead.
- **Sector-adjusted liquidity.** Airlines and cruise lines collect cash for travel not yet taken, which books as a current liability and pushes their current and quick ratios down without reflecting real liquidity risk. Those two sectors are scored against a lower liquidity floor.

**Covenant stress testing**

Each company-year is checked against three covenants: Debt/EBITDA no higher than 4.0x, EBITDA/Interest no lower than 3.0x, and a minimum current ratio of 0.8 (0.4 for airlines and cruise lines). The scenarios cut EBITDA by 0% (base), 15% (optimistic), 30% (neutral), and 47.3% (pessimist). Revenue shocks are listed for each scenario as narrative only. Only the EBITDA cut feeds the math, because two of the three covenants depend on EBITDA and the third does not change with it.

The pessimist cut matches OXY's 2023 EBITDA decline of 47.3%, a real drop seen in the sample. It is not the sample's worst, because Ford's EBITDA fell 74% in 2025.

EBITDA is cut by a share of its own size, not multiplied by a factor, so a company with a negative EBITDA gets a deeper loss and not a smaller one. A stressed EBITDA of zero or below breaches the leverage and coverage covenants automatically.

## Sample

MSFT, COST, JNJ, SBUX, HD, OXY, F, CCL, AAL, and AMC. They were chosen to span the credit spectrum from investment grade to distressed, and each one sits in its own sector. The latest year for each company is its most recent fiscal year in the data, which runs from August 2022 to June 2026.

## Limits

- **Small sample.** Ten companies and 40 company-years show how the scoring behaves but are not enough to calibrate a rating model. The breakpoints and weights are judgment calls, not fitted to default data, and the ratings are not agency ratings.
- **Cyclical risk is only partly captured.** A company such as OXY, whose earnings swing with oil prices, still scores stronger than a credit analyst would rate its cyclical risk. Its average score ranks fourth of ten, above HD and SBUX.
- **Stress is mild for strong names.** Only EBITDA is shocked, and the five strongest companies barely move even under the pessimist case. Debt, interest cost, and liquidity are held fixed.
- **Covenant levels are assumed.** The 4.0x, 3.0x, and 0.8 thresholds are illustrative and not taken from any actual loan agreement.
- **Data source.** Yahoo Finance fields can be missing or restated, so a rerun on a later date may give slightly different inputs.

## Repo structure

```
data/
  companies.csv           company and sector reference list
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

The repo already includes the database and outputs, so the scripts only need to be run to refresh the data.

## Stack

Python, SQLite (`sqlite3`), pandas, yfinance, matplotlib, openpyxl.

This is a student project and not investment advice or a credit opinion.
