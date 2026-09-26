"""Pull historical financial statements for a list of tickers via yfinance
and save the extracted line items to a single CSV for downstream loading
into the credit risk SQLite database.
"""

import os
import time
import warnings

import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore", category=FutureWarning)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "data"))
COMPANIES_CSV = os.path.join(DATA_DIR, "companies.csv")
OUTPUT_CSV = os.path.join(DATA_DIR, "raw_financials.csv")

INCOME_STMT_FIELDS = {
    "revenue": ["Total Revenue"],
    "ebitda": ["EBITDA", "Normalized EBITDA"],
    "ebit": ["EBIT", "Operating Income"],
    "interest_expense": ["Interest Expense", "Interest Expense Non Operating"],
}

BALANCE_SHEET_FIELDS = {
    "total_debt": ["Total Debt"],
    "cash_and_equivalents": [
        "Cash And Cash Equivalents",
        "Cash Cash Equivalents And Short Term Investments",
    ],
    "current_assets": ["Current Assets"],
    "current_liabilities": ["Current Liabilities"],
    "inventory": ["Inventory"],
    "stockholders_equity": ["Stockholders Equity", "Common Stock Equity"],
}

CASH_FLOW_FIELDS = {
    "operating_cash_flow": [
        "Operating Cash Flow",
        "Cash Flow From Continuing Operating Activities",
    ],
    "capital_expenditure": ["Capital Expenditure"],
}

YEARS_OF_HISTORY = 4


def _first_available_row(df: pd.DataFrame, candidates: list[str]) -> pd.Series | None:
    """Return the first row in df whose label matches a candidate, or None."""
    if df is None or df.empty:
        return None
    for label in candidates:
        if label in df.index:
            return df.loc[label]
    return None


def extract_fields(df: pd.DataFrame, field_map: dict[str, list[str]]) -> dict[str, pd.Series | None]:
    """Map each output field name to its matching row in a statement DataFrame."""
    return {name: _first_available_row(df, candidates) for name, candidates in field_map.items()}


def pull_company_financials(ticker_symbol: str) -> pd.DataFrame:
    """Return one row per fiscal year of combined statement data for a ticker."""
    ticker = yf.Ticker(ticker_symbol)
    income_stmt = ticker.income_stmt

    if income_stmt is None or income_stmt.empty:
        return pd.DataFrame()

    fields = {
        **extract_fields(income_stmt, INCOME_STMT_FIELDS),
        **extract_fields(ticker.balance_sheet, BALANCE_SHEET_FIELDS),
        **extract_fields(ticker.cash_flow, CASH_FLOW_FIELDS),
    }

    fiscal_years = sorted(income_stmt.columns, reverse=True)[:YEARS_OF_HISTORY]

    rows = []
    for fiscal_year_end in fiscal_years:
        row = {"ticker": ticker_symbol, "fiscal_year_end": fiscal_year_end}
        for field_name, series in fields.items():
            row[field_name] = series.get(fiscal_year_end) if series is not None else None
        rows.append(row)

    return pd.DataFrame(rows)


def main() -> None:
    companies = pd.read_csv(COMPANIES_CSV)
    results = []
    summary = []

    for _, company in companies.iterrows():
        symbol = company["ticker"]
        print(f"Pulling {symbol}...")

        try:
            df = pull_company_financials(symbol)
        except Exception as exc:
            print(f"  failed: {exc}")
            summary.append((symbol, 0))
            continue

        if df.empty:
            summary.append((symbol, 0))
            continue

        results.append(df)
        summary.append((symbol, len(df)))
        time.sleep(1)

    if not results:
        print("No data pulled.")
        return

    pd.concat(results, ignore_index=True).to_csv(OUTPUT_CSV, index=False)

    print(f"\nSaved: {OUTPUT_CSV}")
    print("\nYears of data per company:")
    for symbol, count in summary:
        print(f"  {symbol}: {count}")


if __name__ == "__main__":
    main()
