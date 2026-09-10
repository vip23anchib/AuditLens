-- ==============================================================================
-- AuditLens: 02_staging_ctes.sql
-- Ingestion, Deduplication, and Staging Pipeline using Common Table Expressions (CTEs)
-- ==============================================================================

DELETE FROM staged_transactions;

INSERT INTO staged_transactions (
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
    ground_truth_anomaly,
    ground_truth_type
)
WITH deduplicated_feed AS (
    -- Deduplicate transactions where identical transaction_id was ingested multiple times
    SELECT
        transaction_id,
        transaction_date,
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
        is_anomaly,
        anomaly_type,
        ROW_NUMBER() OVER (
            PARTITION BY transaction_id 
            ORDER BY rowid ASC
        ) AS txn_occurrence
    FROM raw_transactions
),
cleaned_transactions AS (
    -- Sanitize null representations, clean strings, and cast types
    SELECT
        transaction_id,
        date(transaction_date) AS transaction_date,
        CAST(strftime('%Y', transaction_date) AS INTEGER) AS transaction_year,
        CAST(strftime('%m', transaction_date) AS INTEGER) AS transaction_month,
        CAST(strftime('%w', transaction_date) AS INTEGER) AS day_of_week,
        CASE CAST(strftime('%w', transaction_date) AS INTEGER)
            WHEN 0 THEN 'Sunday'
            WHEN 1 THEN 'Monday'
            WHEN 2 THEN 'Tuesday'
            WHEN 3 THEN 'Wednesday'
            WHEN 4 THEN 'Thursday'
            WHEN 5 THEN 'Friday'
            WHEN 6 THEN 'Saturday'
        END AS day_name,
        CASE 
            WHEN CAST(strftime('%w', transaction_date) AS INTEGER) IN (0, 6) THEN 1 
            ELSE 0 
        END AS is_weekend,
        TRIM(account_id) AS account_id,
        TRIM(department) AS department,
        TRIM(vendor_id) AS vendor_id,
        TRIM(vendor_name) AS vendor_name,
        ROUND(CAST(amount AS REAL), 2) AS amount,
        COALESCE(NULLIF(TRIM(currency), ''), 'USD') AS currency,
        TRIM(payment_method) AS payment_method,
        NULLIF(TRIM(invoice_number), '') AS invoice_number,
        NULLIF(TRIM(approver_id), '') AS approver_id,
        TRIM(transaction_type) AS transaction_type,
        TRIM(description) AS description,
        COALESCE(is_anomaly, 0) AS ground_truth_anomaly,
        COALESCE(anomaly_type, 'BENIGN_NORMAL') AS ground_truth_type
    FROM deduplicated_feed
    WHERE txn_occurrence = 1
      AND amount IS NOT NULL
      AND amount > 0
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
    ground_truth_anomaly,
    ground_truth_type
FROM cleaned_transactions;
