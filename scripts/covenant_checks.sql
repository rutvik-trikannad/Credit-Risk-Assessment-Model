-- Checks each company-year against three maintenance covenants under a
-- given stress scenario. Run once per scenario with :ebitda_shock bound
-- to that scenario's EBITDA decline (0.0 for the base/unstressed case).
--
-- EBITDA is shocked additively against its own magnitude (ebitda - abs(ebitda)
-- * shock) rather than multiplicatively (ebitda * (1 - shock)), because a
-- multiplicative shock on an already-negative EBITDA would incorrectly make
-- a loss smaller instead of larger. The additive form deepens a loss and
-- shrinks a profit correctly regardless of sign.
--
-- A company whose stressed EBITDA is zero or negative automatically
-- breaches leverage and coverage: you cannot satisfy a debt-to-earnings
-- or interest-coverage test with no earnings to measure against.
--
-- The liquidity threshold is sector-dependent. Airlines and cruise lines
-- collect cash for travel not yet taken, which books as a current
-- liability and structurally depresses their current ratio without
-- reflecting real liquidity risk (see ratio scoring methodology). They
-- are held to a lower minimum current ratio than other sectors.

SELECT
    f.ticker,
    f.fiscal_year_end,
    (f.ebitda - (ABS(f.ebitda) * :ebitda_shock)) AS stressed_ebitda,

    f.total_debt / NULLIF((f.ebitda - (ABS(f.ebitda) * :ebitda_shock)), 0)
        AS debt_to_ebitda,
    (f.ebitda - (ABS(f.ebitda) * :ebitda_shock)) / NULLIF(f.interest_expense, 0)
        AS ebitda_to_interest,
    f.current_assets / NULLIF(f.current_liabilities, 0)
        AS current_ratio,

    CASE
        WHEN (f.ebitda - (ABS(f.ebitda) * :ebitda_shock)) <= 0 THEN 1
        WHEN f.total_debt / (f.ebitda - (ABS(f.ebitda) * :ebitda_shock)) > :leverage_max THEN 1
        ELSE 0
    END AS leverage_breach,

    CASE
        WHEN (f.ebitda - (ABS(f.ebitda) * :ebitda_shock)) <= 0 THEN 1
        WHEN (f.ebitda - (ABS(f.ebitda) * :ebitda_shock)) / NULLIF(f.interest_expense, 0) < :coverage_min THEN 1
        ELSE 0
    END AS coverage_breach,

    CASE
        WHEN c.sector IN ('Airlines', 'Travel/Leisure')
             AND f.current_assets / NULLIF(f.current_liabilities, 0) < :liquidity_min_lenient THEN 1
        WHEN c.sector NOT IN ('Airlines', 'Travel/Leisure')
             AND f.current_assets / NULLIF(f.current_liabilities, 0) < :liquidity_min_default THEN 1
        ELSE 0
    END AS liquidity_breach

FROM financials f
JOIN companies c ON f.ticker = c.ticker
ORDER BY f.ticker, f.fiscal_year_end;
