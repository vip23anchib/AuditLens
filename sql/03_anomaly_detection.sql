-- ==============================================================================
-- AuditLens: 03_anomaly_detection.sql
-- Advanced Forensic Audit Detection Engine using Window Functions & Analytical CTEs
-- ==============================================================================

-- 1. Duplicate Invoice Analysis (Same Vendor, Invoice Number & Amount)
WITH duplicate_invoice_cte AS (
    SELECT
        transaction_id,
        transaction_date,
        vendor_id,
        vendor_name,
        invoice_number,
        amount,
        ROW_NUMBER() OVER (
            PARTITION BY vendor_id, invoice_number, amount
            ORDER BY transaction_date ASC, transaction_id ASC
        ) AS duplicate_instance_num,
        COUNT(*) OVER (
            PARTITION BY vendor_id, invoice_number, amount
        ) AS total_duplicate_occurrences
    FROM staged_transactions
    WHERE invoice_number IS NOT NULL
)
SELECT * 
FROM duplicate_invoice_cte
WHERE total_duplicate_occurrences > 1
ORDER BY vendor_id, invoice_number, transaction_date;

-- 2. Threshold Structuring & Split-Transaction Detection
-- Flags transactions split intentionally just below $5,000, $10,000, and $50,000 approval limits
WITH structuring_lead_lag_cte AS (
    SELECT
        transaction_id,
        transaction_date,
        department,
        approver_id,
        vendor_name,
        amount,
        -- Check proximity to approval thresholds
        CASE 
            WHEN amount BETWEEN 4800.00 AND 4999.99 THEN 5000
            WHEN amount BETWEEN 9500.00 AND 9999.99 THEN 10000
            WHEN amount BETWEEN 48000.00 AND 49999.99 THEN 50000
            ELSE NULL 
        END AS threshold_limit_targeted,
        -- Previous transaction by same department/approver
        LAG(amount, 1) OVER (
            PARTITION BY department, approver_id 
            ORDER BY transaction_date
        ) AS prev_txn_amount,
        LAG(transaction_date, 1) OVER (
            PARTITION BY department, approver_id 
            ORDER BY transaction_date
        ) AS prev_txn_date,
        -- Next transaction by same department/approver
        LEAD(amount, 1) OVER (
            PARTITION BY department, approver_id 
            ORDER BY transaction_date
        ) AS next_txn_amount
    FROM staged_transactions
)
SELECT 
    transaction_id,
    transaction_date,
    department,
    approver_id,
    amount,
    threshold_limit_targeted,
    prev_txn_amount,
    prev_txn_date,
    next_txn_amount
FROM structuring_lead_lag_cte
WHERE threshold_limit_targeted IS NOT NULL
ORDER BY department, transaction_date;

-- 3. Department Spend Profiling & Percentile Ranking (NTILE & Running Totals)
WITH department_stats_cte AS (
    SELECT
        transaction_id,
        transaction_date,
        department,
        vendor_name,
        amount,
        AVG(amount) OVER (PARTITION BY department) AS dept_avg_spend,
        MIN(amount) OVER (PARTITION BY department) AS dept_min_spend,
        MAX(amount) OVER (PARTITION BY department) AS dept_max_spend,
        NTILE(100) OVER (PARTITION BY department ORDER BY amount) AS dept_amount_percentile,
        SUM(amount) OVER (
            PARTITION BY department 
            ORDER BY transaction_date 
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS dept_cumulative_ytd_spend
    FROM staged_transactions
)
SELECT 
    transaction_id,
    transaction_date,
    department,
    vendor_name,
    amount,
    ROUND(dept_avg_spend, 2) AS dept_avg_spend,
    ROUND(amount / dept_avg_spend, 2) AS ratio_to_dept_avg,
    dept_amount_percentile,
    ROUND(dept_cumulative_ytd_spend, 2) AS dept_cumulative_ytd_spend
FROM department_stats_cte
WHERE dept_amount_percentile >= 99
ORDER BY amount DESC;
