-- Credit risk assessment database schema.
-- Raw inputs (companies, financials) are normalized. Derived outputs
-- (ratios, ratings) are stored one row per company-year for direct
-- consumption by the scoring and reporting scripts.

CREATE TABLE IF NOT EXISTS companies (
    ticker TEXT PRIMARY KEY,
    company_name TEXT NOT NULL,
    sector TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS financials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL REFERENCES companies(ticker),
    fiscal_year_end DATE NOT NULL,
    revenue REAL,
    ebitda REAL,
    ebit REAL,
    interest_expense REAL,
    total_debt REAL,
    cash_and_equivalents REAL,
    current_assets REAL,
    current_liabilities REAL,
    inventory REAL,
    stockholders_equity REAL,
    operating_cash_flow REAL,
    capital_expenditure REAL,
    UNIQUE (ticker, fiscal_year_end)
);

CREATE TABLE IF NOT EXISTS ratios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL REFERENCES companies(ticker),
    fiscal_year_end DATE NOT NULL,

    -- Leverage
    debt_to_ebitda REAL,
    net_debt_to_ebitda REAL,
    debt_to_equity REAL,

    -- Coverage
    ebitda_to_interest REAL,
    ebit_to_interest REAL,

    -- Liquidity
    current_ratio REAL,
    quick_ratio REAL,

    -- Cash flow strength
    fcf_to_debt REAL,
    ocf_to_interest REAL,

    -- Profitability & stability
    ebitda_margin REAL,
    revenue_growth_volatility REAL,

    UNIQUE (ticker, fiscal_year_end)
);

CREATE TABLE IF NOT EXISTS ratings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL REFERENCES companies(ticker),
    fiscal_year_end DATE NOT NULL,

    leverage_score REAL,
    coverage_score REAL,
    liquidity_score REAL,
    cash_flow_score REAL,
    stability_score REAL,

    composite_score REAL,
    rating_tier TEXT,

    UNIQUE (ticker, fiscal_year_end)
);

CREATE TABLE IF NOT EXISTS covenant_checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL REFERENCES companies(ticker),
    fiscal_year_end DATE NOT NULL,
    scenario TEXT NOT NULL,

    stressed_ebitda REAL,
    debt_to_ebitda REAL,
    ebitda_to_interest REAL,
    current_ratio REAL,

    leverage_breach INTEGER NOT NULL,
    coverage_breach INTEGER NOT NULL,
    liquidity_breach INTEGER NOT NULL,
    any_breach INTEGER NOT NULL,

    UNIQUE (ticker, fiscal_year_end, scenario)
);
