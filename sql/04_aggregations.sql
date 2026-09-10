-- ==============================================================================
-- AuditLens: 04_aggregations.sql
-- Financial Summaries & Multi-Dimensional Audit Aggregations
-- ==============================================================================

-- 1. Department Spending & Risk Profile
SELECT
    department,
    COUNT(*) AS total_transactions,
    ROUND(SUM(amount), 2) AS total_spend,
    ROUND(AVG(amount), 2) AS avg_transaction_amount,
    ROUND(MIN(amount), 2) AS min_amount,
    ROUND(MAX(amount), 2) AS max_amount,
    SUM(CASE WHEN is_weekend = 1 THEN 1 ELSE 0 END) AS weekend_transaction_count,
    SUM(CASE WHEN approver_id IS NULL THEN 1 ELSE 0 END) AS unapproved_transaction_count,
    ROUND(SUM(CASE WHEN is_weekend = 1 THEN amount ELSE 0 END), 2) AS weekend_spend_total
FROM staged_transactions
GROUP BY department
ORDER BY total_spend DESC;

-- 2. Top Vendor Spend & Concentration (with Running % of Total Spend)
WITH vendor_totals AS (
    SELECT
        vendor_id,
        vendor_name,
        department,
        COUNT(*) AS transaction_count,
        SUM(amount) AS vendor_spend
    FROM staged_transactions
    GROUP BY vendor_id, vendor_name, department
),
ranked_vendors AS (
    SELECT
        vendor_id,
        vendor_name,
        department,
        transaction_count,
        ROUND(vendor_spend, 2) AS total_vendor_spend,
        ROUND(vendor_spend * 100.0 / SUM(vendor_spend) OVER (), 2) AS pct_of_global_spend,
        ROUND(SUM(vendor_spend) OVER (ORDER BY vendor_spend DESC) * 100.0 / SUM(vendor_spend) OVER (), 2) AS cumulative_spend_pct
    FROM vendor_totals
)
SELECT * 
FROM ranked_vendors
ORDER BY total_vendor_spend DESC
LIMIT 25;

-- 3. Monthly Financial Velocity & Year-over-Year Trajectory
SELECT
    transaction_year,
    transaction_month,
    COUNT(*) AS transaction_volume,
    ROUND(SUM(amount), 2) AS monthly_spend,
    ROUND(AVG(amount), 2) AS monthly_avg_ticket,
    ROUND(
        (SUM(amount) - LAG(SUM(amount), 1) OVER (ORDER BY transaction_year, transaction_month)) * 100.0 /
        LAG(SUM(amount), 1) OVER (ORDER BY transaction_year, transaction_month), 
        2
    ) AS mom_growth_pct
FROM staged_transactions
GROUP BY transaction_year, transaction_month
ORDER BY transaction_year, transaction_month;

-- 4. Payment Method Exposure Breakdown
SELECT
    payment_method,
    COUNT(*) AS total_transactions,
    ROUND(SUM(amount), 2) AS total_amount,
    ROUND(AVG(amount), 2) AS avg_amount,
    ROUND(SUM(amount) * 100.0 / (SELECT SUM(amount) FROM staged_transactions), 2) AS spend_share_pct
FROM staged_transactions
GROUP BY payment_method
ORDER BY total_amount DESC;
