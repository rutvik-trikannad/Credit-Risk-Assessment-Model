"""Build the SQLite database from schema.sql and load companies.csv and
raw_financials.csv into it.
"""

import os
import sqlite3

import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "data"))

SCHEMA_PATH = os.path.join(SCRIPT_DIR, "schema.sql")
COMPANIES_CSV = os.path.join(DATA_DIR, "companies.csv")
FINANCIALS_CSV = os.path.join(DATA_DIR, "raw_financials.csv")
DB_PATH = os.path.join(DATA_DIR, "credit_risk.db")

FINANCIALS_COLUMNS = [
    "ticker", "fiscal_year_end", "revenue", "ebitda", "ebit", "interest_expense",
    "total_debt", "cash_and_equivalents", "current_assets", "current_liabilities",
    "inventory", "stockholders_equity", "operating_cash_flow", "capital_expenditure",
]


def build_schema(conn: sqlite3.Connection) -> None:
    with open(SCHEMA_PATH) as f:
        conn.executescript(f.read())


def load_companies(conn: sqlite3.Connection) -> int:
    companies = pd.read_csv(COMPANIES_CSV)
    conn.executemany(
        "INSERT OR REPLACE INTO companies (ticker, company_name, sector) VALUES (?, ?, ?)",
        companies[["ticker", "company_name", "sector"]].itertuples(index=False, name=None),
    )
    return len(companies)


def load_financials(conn: sqlite3.Connection) -> int:
    financials = pd.read_csv(FINANCIALS_CSV)
    placeholders = ", ".join("?" for _ in FINANCIALS_COLUMNS)
    columns = ", ".join(FINANCIALS_COLUMNS)
    conn.executemany(
        f"INSERT OR REPLACE INTO financials ({columns}) VALUES ({placeholders})",
        financials[FINANCIALS_COLUMNS].itertuples(index=False, name=None),
    )
    return len(financials)


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")

    build_schema(conn)
    company_count = load_companies(conn)
    financials_count = load_financials(conn)
    conn.commit()

    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()

    conn.close()

    print(f"Database: {DB_PATH}")
    print(f"Tables: {[t[0] for t in tables]}")
    print(f"Companies loaded: {company_count}")
    print(f"Financial statement rows loaded: {financials_count}")


if __name__ == "__main__":
    main()
