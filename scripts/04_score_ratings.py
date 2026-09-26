"""Convert the 11 stored ratios into 5 weighted category scores, a
composite score, and a final letter rating, written to the ratings table.

Each ratio is scored 0-100 on a linear scale between a "worst" and "best"
breakpoint, clamped at both ends. For leverage ratios (lower is better),
a negative value caused by a negative denominator (EBITDA <= 0 or
stockholders' equity <= 0) is not actually favorable, so those cases are
explicitly floored to 0 rather than left to the linear formula, which
would otherwise score them as artificially strong.
"""

import os
import sqlite3

import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "data"))
DB_PATH = os.path.join(DATA_DIR, "credit_risk.db")

# Category weights. Must sum to 1.0.
WEIGHTS = {
    "leverage_score": 0.30,
    "coverage_score": 0.25,
    "cash_flow_score": 0.20,
    "liquidity_score": 0.15,
    "stability_score": 0.10,
}

# (worst, best, direction) per ratio. "higher" means higher values score
# better; "lower" means lower values score better. Values are clamped to
# the 0-100 range outside the breakpoints.
SCORING_BANDS = {
    "debt_to_ebitda": (8.0, 1.0, "lower"),
    "net_debt_to_ebitda": (8.0, 1.0, "lower"),
    "debt_to_equity": (4.0, 0.5, "lower"),
    "ebitda_to_interest": (1.0, 10.0, "higher"),
    "ebit_to_interest": (1.0, 6.0, "higher"),
    "current_ratio": (0.5, 2.0, "higher"),
    "quick_ratio": (0.3, 1.5, "higher"),
    "fcf_to_debt": (0.0, 0.20, "higher"),
    "ocf_to_interest": (1.0, 10.0, "higher"),
    "ebitda_margin": (0.0, 0.30, "higher"),
    "revenue_growth_volatility": (0.35, 0.03, "lower"),
}

CATEGORY_RATIOS = {
    "leverage_score": ["debt_to_ebitda", "net_debt_to_ebitda", "debt_to_equity"],
    "coverage_score": ["ebitda_to_interest", "ebit_to_interest"],
    "liquidity_score": ["current_ratio", "quick_ratio"],
    "cash_flow_score": ["fcf_to_debt", "ocf_to_interest"],
    "stability_score": ["ebitda_margin", "revenue_growth_volatility"],
}

# Within-category weights. A category not listed here is a plain average
# of its ratios. Stability weights revenue growth volatility above EBITDA
# margin so a high margin can't mask a cyclical revenue profile.
WITHIN_CATEGORY_WEIGHTS = {
    "stability_score": {"ebitda_margin": 0.3, "revenue_growth_volatility": 0.7},
}

# Sector-specific (worst, best) overrides for current_ratio and quick_ratio.
# Airlines and cruise lines collect cash upfront for travel not yet taken,
# which books as a current liability (deferred revenue) and structurally
# depresses their current/quick ratios relative to companies without that
# business model. These bands reflect realistic healthy ranges for those
# sectors rather than penalizing an accounting artifact as if it were
# genuine liquidity risk.
SECTOR_LIQUIDITY_BANDS = {
    "Airlines": {"current_ratio": (0.2, 1.0), "quick_ratio": (0.15, 0.8)},
    "Travel/Leisure": {"current_ratio": (0.2, 1.0), "quick_ratio": (0.15, 0.8)},
}

# Composite score (0-100) cutoffs, highest tier first.
RATING_THRESHOLDS = [
    (88, "AAA"),
    (78, "AA"),
    (68, "A"),
    (55, "BBB"),
    (42, "BB"),
    (28, "B"),
    (0, "CCC"),
]


def score_ratio(value: float, worst: float, best: float, direction: str) -> float:
    """Linearly scale a ratio value to 0-100, clamped at both ends."""
    if pd.isna(value):
        return 0.0
    if direction == "higher":
        low, high = worst, best
    else:
        low, high = best, worst
    if high == low:
        return 100.0
    fraction = (value - low) / (high - low)
    fraction = max(0.0, min(1.0, fraction))
    score = fraction * 100.0 if direction == "higher" else (1 - fraction) * 100.0
    return score


def apply_negative_denominator_overrides(row: pd.Series, ratio_scores: dict) -> dict:
    """Force leverage sub-scores to 0 when the underlying denominator
    (EBITDA or equity) is negative, since a negative ratio here reflects
    distress, not strength."""
    if row["ebitda"] <= 0:
        ratio_scores["debt_to_ebitda"] = 0.0
        ratio_scores["net_debt_to_ebitda"] = 0.0
    if row["stockholders_equity"] <= 0:
        ratio_scores["debt_to_equity"] = 0.0
    return ratio_scores


def rating_tier_for(composite: float) -> str:
    for threshold, tier in RATING_THRESHOLDS:
        if composite >= threshold:
            return tier
    return RATING_THRESHOLDS[-1][1]


def bands_for(ratio: str, sector: str) -> tuple:
    """Return (worst, best, direction) for a ratio, applying a sector-
    specific override for liquidity ratios where one exists."""
    worst, best, direction = SCORING_BANDS[ratio]
    override = SECTOR_LIQUIDITY_BANDS.get(sector, {}).get(ratio)
    if override is not None:
        worst, best = override
    return worst, best, direction


def score_company_year(row: pd.Series, sector: str) -> dict:
    ratio_scores = {
        ratio: score_ratio(row[ratio], *bands_for(ratio, sector))
        for ratio in SCORING_BANDS
    }
    ratio_scores = apply_negative_denominator_overrides(row, ratio_scores)

    category_scores = {}
    for category, ratios in CATEGORY_RATIOS.items():
        within_weights = WITHIN_CATEGORY_WEIGHTS.get(category)
        if within_weights:
            category_scores[category] = sum(
                ratio_scores[r] * within_weights[r] for r in ratios
            )
        else:
            category_scores[category] = sum(ratio_scores[r] for r in ratios) / len(ratios)

    composite = sum(category_scores[cat] * weight for cat, weight in WEIGHTS.items())

    return {
        **category_scores,
        "composite_score": composite,
        "rating_tier": rating_tier_for(composite),
    }


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")

    ratio_columns = ", ".join(f"r.{ratio}" for ratio in SCORING_BANDS)
    query = f"""
        SELECT f.ticker, f.fiscal_year_end, f.ebitda, f.stockholders_equity,
               c.sector, {ratio_columns}
        FROM financials f
        JOIN ratios r ON f.ticker = r.ticker AND f.fiscal_year_end = r.fiscal_year_end
        JOIN companies c ON f.ticker = c.ticker
    """
    df = pd.read_sql_query(query, conn)

    scored_rows = []
    for _, row in df.iterrows():
        scores = score_company_year(row, row["sector"])
        scored_rows.append({
            "ticker": row["ticker"],
            "fiscal_year_end": row["fiscal_year_end"],
            **scores,
        })

    scored_df = pd.DataFrame(scored_rows)
    columns = [
        "ticker", "fiscal_year_end", "leverage_score", "coverage_score",
        "liquidity_score", "cash_flow_score", "stability_score",
        "composite_score", "rating_tier",
    ]
    placeholders = ", ".join("?" for _ in columns)
    conn.executemany(
        f"INSERT OR REPLACE INTO ratings ({', '.join(columns)}) VALUES ({placeholders})",
        scored_df[columns].itertuples(index=False, name=None),
    )
    conn.commit()

    count = conn.execute("SELECT COUNT(*) FROM ratings").fetchone()[0]
    conn.close()

    print(f"Ratings calculated and stored: {count} rows")


if __name__ == "__main__":
    main()
