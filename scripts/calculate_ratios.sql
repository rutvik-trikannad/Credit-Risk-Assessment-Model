-- Calculates 10 of the 11 credit ratios directly from financials.
-- NULLIF guards every division against a zero denominator, returning
-- NULL instead of raising a divide-by-zero error. Ratios are computed
-- as their literal value, including when a numerator is negative
-- (e.g. negative EBITDA); the scoring step interprets those cases
-- rather than this query suppressing them.

SELECT
    f.ticker,
    f.fiscal_year_end,

    f.total_debt / NULLIF(f.ebitda, 0)
        AS debt_to_ebitda,
    (f.total_debt - f.cash_and_equivalents) / NULLIF(f.ebitda, 0)
        AS net_debt_to_ebitda,
    f.total_debt / NULLIF(f.stockholders_equity, 0)
        AS debt_to_equity,

    f.ebitda / NULLIF(f.interest_expense, 0)
        AS ebitda_to_interest,
    f.ebit / NULLIF(f.interest_expense, 0)
        AS ebit_to_interest,

    f.current_assets / NULLIF(f.current_liabilities, 0)
        AS current_ratio,
    (f.current_assets - f.inventory) / NULLIF(f.current_liabilities, 0)
        AS quick_ratio,

    (f.operating_cash_flow + f.capital_expenditure) / NULLIF(f.total_debt, 0)
        AS fcf_to_debt,
    f.operating_cash_flow / NULLIF(f.interest_expense, 0)
        AS ocf_to_interest,

    f.ebitda / NULLIF(f.revenue, 0)
        AS ebitda_margin

FROM financials f
JOIN companies c ON f.ticker = c.ticker
ORDER BY f.ticker, f.fiscal_year_end;
