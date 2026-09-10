-- ==============================================================================
-- AuditLens: 05_flagged_transactions_view.sql
-- Forensic Risk-Scoring Engine and Flagged Transactions View/Table
-- ==============================================================================

DROP VIEW IF EXISTS vw_flagged_transactions;
DROP TABLE IF EXISTS flagged_transactions;

-- Step 1: Create Comprehensive Forensic Analysis View
CREATE VIEW vw_flagged_transactions AS
WITH duplicate_invoice_flags AS (
    SELECT
        transaction_id,
        CASE 
            WHEN COUNT(*) OVER (PARTITION BY vendor_id, invoice_number, amount) > 1 
                 AND invoice_number IS NOT NULL THEN 1 
            ELSE 0 
        END AS is_duplicate_invoice,
        ROW_NUMBER() OVER (
            PARTITION BY vendor_id, invoice_number, amount
            ORDER BY transaction_date ASC, transaction_id ASC
        ) AS duplicate_occurrence_rank
    FROM staged_transactions
),
department_baseline_stats AS (
    SELECT
        department,
        AVG(amount) AS dept_mean_amt
    FROM staged_transactions
    GROUP BY department
),
scored_transactions AS (
    SELECT
        st.transaction_id,
        st.transaction_date,
        st.transaction_year,
        st.transaction_month,
        st.day_of_week,
        st.day_name,
        st.is_weekend,
        st.account_id,
        st.department,
        st.vendor_id,
        st.vendor_name,
        st.amount,
        st.currency,
        st.payment_method,
        st.invoice_number,
        st.approver_id,
        st.transaction_type,
        st.description,
        st.ground_truth_anomaly,
        st.ground_truth_type,
        
        -- Forensic Rule Flags (1 = Triggered, 0 = Clean)
        dup.is_duplicate_invoice AS flag_duplicate_invoice,
        
        -- Rule 2: Round Amount Flag
        CASE 
            WHEN st.amount >= 5000.00 
                 AND (st.amount = ROUND(st.amount, 0)) 
                 AND (CAST(st.amount AS INTEGER) % 5000 = 0) THEN 1
            ELSE 0
        END AS flag_round_amount,
        
        -- Rule 3: Approval Threshold Structuring Flag
        CASE 
            WHEN (st.amount BETWEEN 4800.00 AND 4999.99)
              OR (st.amount BETWEEN 9500.00 AND 9999.99)
              OR (st.amount BETWEEN 48000.00 AND 49999.99) THEN 1
            ELSE 0
        END AS flag_threshold_structuring,
        
        -- Rule 4: Weekend / Off-Hours Posting Flag
        CASE 
            WHEN st.is_weekend = 1 AND st.amount >= 15000.00 THEN 1
            ELSE 0
        END AS flag_weekend_posting,
        
        -- Rule 5: Missing Governance (Approver or Invoice) Flag
        CASE 
            WHEN st.approver_id IS NULL OR st.invoice_number IS NULL THEN 1
            ELSE 0
        END AS flag_missing_governance,
        
        -- Rule 6: Statistical Spend Spike (> 5x Department Baseline Mean)
        CASE 
            WHEN st.amount > (dbs.dept_mean_amt * 5.0) THEN 1
            ELSE 0
        END AS flag_spend_spike,
        
        dbs.dept_mean_amt AS dept_baseline_mean,
        ROUND(st.amount / dbs.dept_mean_amt, 2) AS dept_spend_multiplier
        
    FROM staged_transactions st
    JOIN duplicate_invoice_flags dup ON st.transaction_id = dup.transaction_id
    JOIN department_baseline_stats dbs ON st.department = dbs.department
),
composite_risk_engine AS (
    SELECT
        *,
        -- Multi-Factor Composite Risk Score (0 to 100 Points)
        (
            (flag_duplicate_invoice * 35) +
            (flag_threshold_structuring * 30) +
            (flag_missing_governance * 25) +
            (flag_spend_spike * 30) +
            (flag_round_amount * 20) +
            (flag_weekend_posting * 20)
        ) AS raw_risk_score
    FROM scored_transactions
)
SELECT
    transaction_id,
    transaction_date,
    transaction_year,
    transaction_month,
    day_of_week,
    day_name,
    is_weekend,
    account_id,
    department,
    vendor_id,
    vendor_name,
    amount,
    currency,
    payment_method,
    invoice_number,
    approver_id,
    transaction_type,
    description,
    dept_baseline_mean,
    dept_spend_multiplier,
    flag_duplicate_invoice,
    flag_round_amount,
    flag_threshold_structuring,
    flag_weekend_posting,
    flag_missing_governance,
    flag_spend_spike,
    -- Audit Risk Rule Count
    (flag_duplicate_invoice + flag_round_amount + flag_threshold_structuring + 
     flag_weekend_posting + flag_missing_governance + flag_spend_spike) AS total_rules_triggered,
    -- Normalized Risk Score Capped at 100
    CASE 
        WHEN raw_risk_score > 100 THEN 100 
        ELSE raw_risk_score 
    END AS risk_score,
    -- Categorical Risk Tier
    CASE 
        WHEN raw_risk_score >= 60 THEN 'Critical'
        WHEN raw_risk_score >= 35 THEN 'High'
        WHEN raw_risk_score >= 20 THEN 'Medium'
        ELSE 'Low'
    END AS risk_tier,
    -- Primary Audit Risk Reason Summary
    CASE 
        WHEN flag_duplicate_invoice = 1 THEN 'Potential Duplicate Invoice Payment'
        WHEN flag_threshold_structuring = 1 THEN 'Approval Limit Structuring / Split Purchase'
        WHEN flag_spend_spike = 1 THEN 'Extreme Statistical Spend Outlier'
        WHEN flag_missing_governance = 1 THEN 'Unverified Transaction - Missing Governance'
        WHEN flag_round_amount = 1 THEN 'Suspicious Round-Sum Billing'
        WHEN flag_weekend_posting = 1 THEN 'High-Value Off-Hours / Weekend Posting'
        ELSE 'Normal Verified Business Spend'
    END AS primary_flag_reason,
    ground_truth_anomaly,
    ground_truth_type
FROM composite_risk_engine;

-- Step 2: Materialize Flagged Transactions Table for Ultra-Fast Downstream Ingestion
CREATE TABLE flagged_transactions AS
SELECT * FROM vw_flagged_transactions;

-- Step 3: Index Risk Scores and Categories
CREATE INDEX IF NOT EXISTS idx_flagged_risk_tier ON flagged_transactions (risk_tier);
CREATE INDEX IF NOT EXISTS idx_flagged_risk_score ON flagged_transactions (risk_score);
CREATE INDEX IF NOT EXISTS idx_flagged_vendor ON flagged_transactions (vendor_id);
CREATE INDEX IF NOT EXISTS idx_flagged_dept ON flagged_transactions (department);
