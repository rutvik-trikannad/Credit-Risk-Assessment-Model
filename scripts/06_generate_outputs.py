"""Generate summary charts and an Excel workbook from the credit risk
database: a rating comparison chart, a per-company rating trend chart,
a covenant/stress test chart, and a multi-tab Excel summary.
"""

import os
import sqlite3

import matplotlib.pyplot as plt
import pandas as pd
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "data"))
OUTPUT_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "output"))
DB_PATH = os.path.join(DATA_DIR, "credit_risk.db")

RATING_ORDER = ["CCC", "B", "BB", "BBB", "A", "AA", "AAA"]
SCENARIO_ORDER = ["base", "optimistic", "neutral", "pessimist"]

# Ordinal ramp (light -> dark), one step per rating tier, worst to best.
RATING_COLORS = dict(zip(RATING_ORDER, [
    "#86b6ef", "#6da7ec", "#5598e7", "#2a78d6", "#256abf", "#184f95", "#0d366b",
]))
# Ordinal ramp (light -> dark), one step per scenario, mild to severe.
SCENARIO_COLORS = dict(zip(SCENARIO_ORDER, ["#86b6ef", "#5598e7", "#256abf", "#104281"]))
CATEGORICAL = {"leverage": "#2a78d6", "coverage": "#eb6834", "liquidity": "#1baf7a"}

INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRIDLINE = "#e1e0d9"
SURFACE = "#fcfcfb"

plt.rcParams.update({
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "axes.edgecolor": GRIDLINE,
    "axes.labelcolor": INK_SECONDARY,
    "text.color": INK_PRIMARY,
    "xtick.color": INK_MUTED,
    "ytick.color": INK_MUTED,
    "grid.color": GRIDLINE,
    "font.family": "sans-serif",
    "font.size": 10,
})


def load_data(conn: sqlite3.Connection) -> dict:
    companies = pd.read_sql_query("SELECT * FROM companies", conn)
    ratios = pd.read_sql_query("SELECT * FROM ratios", conn)
    ratings = pd.read_sql_query("SELECT * FROM ratings", conn)
    covenants = pd.read_sql_query("SELECT * FROM covenant_checks", conn)
    return {"companies": companies, "ratios": ratios, "ratings": ratings, "covenants": covenants}


def chart_rating_by_company(data: dict) -> None:
    ratings = data["ratings"].merge(data["companies"], on="ticker")
    latest = ratings.sort_values("fiscal_year_end").groupby("ticker").tail(1)
    latest = latest.sort_values("composite_score")

    fig, ax = plt.subplots(figsize=(9, 6))
    colors = [RATING_COLORS[t] for t in latest["rating_tier"]]
    bars = ax.barh(latest["company_name"], latest["composite_score"], color=colors)

    for bar, tier in zip(bars, latest["rating_tier"]):
        ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height() / 2, tier,
                 va="center", fontsize=9, color=INK_SECONDARY)

    ax.set_xlabel("Composite Score (0-100)")
    ax.set_title("Credit Rating by Company — Most Recent Fiscal Year", fontsize=13, color=INK_PRIMARY, pad=12)
    ax.set_xlim(0, 110)
    ax.grid(axis="x", linewidth=0.6)
    ax.set_axisbelow(True)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)

    fig.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, "rating_by_company.png"), dpi=150)
    plt.close(fig)


def chart_rating_trend(data: dict) -> None:
    ratings = data["ratings"].merge(data["companies"], on="ticker").sort_values(["ticker", "fiscal_year_end"])
    ratings["period"] = ratings.groupby("ticker").cumcount() + 1

    tickers = sorted(ratings["ticker"].unique())
    fig, axes = plt.subplots(2, 5, figsize=(16, 6), sharey=True)

    for ax, ticker in zip(axes.flat, tickers):
        subset = ratings[ratings.ticker == ticker]
        ax.plot(subset["period"], subset["composite_score"], marker="o",
                 color=CATEGORICAL["leverage"], linewidth=2, markersize=5)
        ax.set_title(ticker, fontsize=10, color=INK_PRIMARY)
        ax.set_xticks([1, 2, 3, 4])
        ax.set_xticklabels(["Yr 1", "Yr 2", "Yr 3", "Yr 4"], fontsize=8)
        ax.set_ylim(0, 100)
        ax.grid(linewidth=0.5)
        ax.set_axisbelow(True)
        for spine in ["top", "right"]:
            ax.spines[spine].set_visible(False)

    fig.suptitle("Composite Score Trend by Company (relative fiscal-year sequence, not aligned calendar dates)",
                  fontsize=12, color=INK_PRIMARY)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(os.path.join(OUTPUT_DIR, "rating_trend_by_company.png"), dpi=150)
    plt.close(fig)


def chart_covenant_stress_test(data: dict) -> None:
    covenants = data["covenants"]
    summary = covenants.groupby("scenario")[["leverage_breach", "coverage_breach", "liquidity_breach"]].sum()
    summary = summary.reindex(SCENARIO_ORDER)

    fig, ax = plt.subplots(figsize=(9, 6))
    x = range(len(SCENARIO_ORDER))
    width = 0.25

    ax.bar([i - width for i in x], summary["leverage_breach"], width, label="Leverage", color=CATEGORICAL["leverage"])
    ax.bar(x, summary["coverage_breach"], width, label="Coverage", color=CATEGORICAL["coverage"])
    ax.bar([i + width for i in x], summary["liquidity_breach"], width, label="Liquidity", color=CATEGORICAL["liquidity"])

    ax.set_xticks(list(x))
    ax.set_xticklabels([s.capitalize() for s in SCENARIO_ORDER])
    ax.set_ylabel("Company-years breaching (of 40)")
    ax.set_title("Covenant Breaches by Stress Scenario", fontsize=13, color=INK_PRIMARY, pad=12)
    ax.legend(frameon=False)
    ax.grid(axis="y", linewidth=0.6)
    ax.set_axisbelow(True)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)

    fig.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, "covenant_stress_test.png"), dpi=150)
    plt.close(fig)


def style_sheet(worksheet, df: pd.DataFrame) -> None:
    """Bold headers, professional font, sensible column widths."""
    for cell in worksheet[1]:
        cell.font = Font(name="Arial", bold=True)
    for row in worksheet.iter_rows(min_row=2):
        for cell in row:
            cell.font = Font(name="Arial")
    for i, column in enumerate(df.columns, start=1):
        max_len = max(df[column].astype(str).map(len).max(), len(column)) + 2
        worksheet.column_dimensions[get_column_letter(i)].width = min(max_len, 40)
    worksheet.freeze_panes = "A2"


def build_excel_summary(data: dict) -> None:
    companies = data["companies"]
    ratings = data["ratings"].merge(companies, on="ticker")
    ratios = data["ratios"].merge(companies, on="ticker")
    covenants = data["covenants"].merge(companies, on="ticker")

    latest = ratings.sort_values("fiscal_year_end").groupby("ticker").tail(1)
    summary = latest[["ticker", "company_name", "sector", "fiscal_year_end", "composite_score", "rating_tier"]]
    summary = summary.sort_values("composite_score", ascending=False)

    sheets = {
        "Summary": summary,
        "Ratings by Year": ratings[["ticker", "company_name", "sector", "fiscal_year_end",
                                     "leverage_score", "coverage_score", "liquidity_score",
                                     "cash_flow_score", "stability_score", "composite_score", "rating_tier"]],
        "Ratios": ratios.drop(columns=["id"]),
        "Covenant Stress Test": covenants.drop(columns=["id"]),
    }

    for name, df in sheets.items():
        sheets[name] = df.round(2)

    path = os.path.join(OUTPUT_DIR, "credit_risk_summary.xlsx")
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for name, df in sheets.items():
            df.to_excel(writer, sheet_name=name, index=False)
            style_sheet(writer.sheets[name], df)


def main() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    data = load_data(conn)
    conn.close()

    chart_rating_by_company(data)
    chart_rating_trend(data)
    chart_covenant_stress_test(data)
    build_excel_summary(data)

    print(f"Charts and workbook written to {OUTPUT_DIR}")
    for f in sorted(os.listdir(OUTPUT_DIR)):
        print(f"  {f}")


if __name__ == "__main__":
    main()