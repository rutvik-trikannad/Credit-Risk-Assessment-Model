"""Run covenant checks under the base case and three stress scenarios,
writing results to the covenant_checks table.

Only the EBITDA shock feeds the covenant math (both covenants are
EBITDA-driven); the revenue shock is scenario narrative rather than a
model input. See covenant_checks.sql for the breach logic.
"""

import os
import sqlite3

import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "data"))
DB_PATH = os.path.join(DATA_DIR, "credit_risk.db")
QUERY_PATH = os.path.join(SCRIPT_DIR, "covenant_checks.sql")

COVENANT_THRESHOLDS = {
    "leverage_max": 4.0,
    "coverage_min": 3.0,
    "liquidity_min_default": 0.8,
    "liquidity_min_lenient": 0.4,
}

# (scenario name, revenue shock, EBITDA shock). Revenue shock is narrative
# only; EBITDA shock is what the covenant math actually uses.
SCENARIOS = [
    ("base", 0.0, 0.0),
    ("optimistic", 0.10, 0.15),
    ("neutral", 0.20, 0.30),
    ("pessimist", 0.37, 0.473),
]

RESULT_COLUMNS = [
    "ticker", "fiscal_year_end", "scenario", "stressed_ebitda",
    "debt_to_ebitda", "ebitda_to_interest", "current_ratio",
    "leverage_breach", "coverage_breach", "liquidity_breach", "any_breach",
]


def run_scenario(conn: sqlite3.Connection, query: str, name: str, ebitda_shock: float) -> pd.DataFrame:
    params = {"ebitda_shock": ebitda_shock, **COVENANT_THRESHOLDS}
    df = pd.read_sql_query(query, conn, params=params)
    df["scenario"] = name
    df["any_breach"] = (
        (df["leverage_breach"] == 1) | (df["coverage_breach"] == 1) | (df["liquidity_breach"] == 1)
    ).astype(int)
    return df


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")

    with open(QUERY_PATH) as f:
        query = f.read()

    all_results = [
        run_scenario(conn, query, name, ebitda_shock)
        for name, _, ebitda_shock in SCENARIOS
    ]
    combined = pd.concat(all_results, ignore_index=True)

    placeholders = ", ".join("?" for _ in RESULT_COLUMNS)
    conn.executemany(
        f"INSERT OR REPLACE INTO covenant_checks ({', '.join(RESULT_COLUMNS)}) VALUES ({placeholders})",
        combined[RESULT_COLUMNS].itertuples(index=False, name=None),
    )
    conn.commit()

    count = conn.execute("SELECT COUNT(*) FROM covenant_checks").fetchone()[0]

    print(f"Covenant checks stored: {count} rows ({len(SCENARIOS)} scenarios x 40 company-years)")
    print()
    print("Companies breaching any covenant, by scenario:")
    for name, _, _ in SCENARIOS:
        breach_count = conn.execute(
            "SELECT COUNT(*) FROM covenant_checks WHERE scenario=? AND any_breach=1", (name,)
        ).fetchone()[0]
        print(f"  {name}: {breach_count} / 40 company-years breach")

    base_pass = pd.read_sql_query(
        "SELECT ticker, fiscal_year_end FROM covenant_checks WHERE scenario='base' AND any_breach=0", conn
    )
    print()
    print(f"Passing every covenant at baseline: {len(base_pass)} / 40")
    print()
    print("Of those, newly breaching under stress:")
    for name, _, _ in SCENARIOS[1:]:
        stressed = pd.read_sql_query(
            "SELECT ticker, fiscal_year_end FROM covenant_checks WHERE scenario=? AND any_breach=1", conn, params=(name,)
        )
        newly = stressed.merge(base_pass, on=["ticker", "fiscal_year_end"])
        print(f"  {name}: {len(newly)} —", list(newly.itertuples(index=False, name=None)))

    conn.close()


if __name__ == "__main__":
    main()
