"""Calculate the 11 credit ratios and write them to the ratios table.

Ten ratios are computed directly in SQL (calculate_ratios.sql). Revenue
growth volatility requires a standard deviation across each company's
fiscal years, which is computed here in pandas rather than in SQLite,
since standard deviation is not a portable built-in SQL function.
"""

import os
import sqlite3

import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "data"))

DB_PATH = os.path.join(DATA_DIR, "credit_risk.db")
RATIO_SQL_PATH = os.path.join(SCRIPT_DIR, "calculate_ratios.sql")

RATIO_COLUMNS = [
    "debt_to_ebitda", "net_debt_to_ebitda", "debt_to_equity",
    "ebitda_to_interest", "ebit_to_interest",
    "current_ratio", "quick_ratio",
    "fcf_to_debt", "ocf_to_interest",
    "ebitda_margin", "revenue_growth_volatility",
]


def compute_sql_ratios(conn: sqlite3.Connection) -> pd.DataFrame:
    with open(RATIO_SQL_PATH) as f:
        query = f.read()
    return pd.read_sql_query(query, conn)


def compute_revenue_growth_volatility(conn: sqlite3.Connection) -> pd.DataFrame:
    financials = pd.read_sql_query(
        "SELECT ticker, fiscal_year_end, revenue FROM financials ORDER BY ticker, fiscal_year_end",
        conn,
    )
    financials["growth_rate"] = financials.groupby("ticker")["revenue"].pct_change()
    volatility = (
        financials.groupby("ticker")["growth_rate"]
        .std()
        .reset_index()
        .rename(columns={"growth_rate": "revenue_growth_volatility"})
    )
    return volatility


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")

    ratios = compute_sql_ratios(conn)
    volatility = compute_revenue_growth_volatility(conn)
    ratios = ratios.merge(volatility, on="ticker", how="left")

    rows = ratios[["ticker", "fiscal_year_end"] + RATIO_COLUMNS].itertuples(index=False, name=None)
    columns = ", ".join(["ticker", "fiscal_year_end"] + RATIO_COLUMNS)
    placeholders = ", ".join("?" for _ in range(len(RATIO_COLUMNS) + 2))

    conn.executemany(f"INSERT OR REPLACE INTO ratios ({columns}) VALUES ({placeholders})", rows)
    conn.commit()

    count = conn.execute("SELECT COUNT(*) FROM ratios").fetchone()[0]
    conn.close()

    print(f"Ratios calculated and stored: {count} rows")


if __name__ == "__main__":
    main()
