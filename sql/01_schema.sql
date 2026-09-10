-- ==============================================================================
-- AuditLens: 01_schema.sql
-- Financial Database Schema Definition (Compatible with SQLite & PostgreSQL)
-- ==============================================================================

-- 1. Raw Ingestion Staging Table (Captures raw incoming feed before audit sanitization)
DROP TABLE IF EXISTS raw_transactions;

CREATE TABLE raw_transactions (
    transaction_id TEXT,
    transaction_date TEXT,
    account_id TEXT,
    department TEXT,
    vendor_id TEXT,
    vendor_name TEXT,
    amount REAL,
    currency TEXT,
    payment_method TEXT,
    invoice_number TEXT,
    approver_id TEXT,
    transaction_type TEXT,
    description TEXT,
    is_anomaly INTEGER,
    anomaly_type TEXT
);

-- 2. Master Vendor Table
DROP TABLE IF EXISTS dim_vendors;

CREATE TABLE dim_vendors (
    vendor_id TEXT PRIMARY KEY,
    vendor_name TEXT NOT NULL,
    primary_department TEXT NOT NULL,
    risk_tier TEXT NOT NULL
);

-- 3. Staged & Cleaned Production Transactions Table
DROP TABLE IF EXISTS staged_transactions;

CREATE TABLE staged_transactions (
    transaction_id TEXT PRIMARY KEY,
    transaction_date DATE NOT NULL,
    transaction_year INTEGER NOT NULL,
    transaction_month INTEGER NOT NULL,
    day_of_week INTEGER NOT NULL,
    day_name TEXT NOT NULL,
    is_weekend INTEGER NOT NULL,
    account_id TEXT NOT NULL,
    department TEXT NOT NULL,
    vendor_id TEXT NOT NULL,
    vendor_name TEXT NOT NULL,
    amount REAL NOT NULL,
    currency TEXT NOT NULL,
    payment_method TEXT NOT NULL,
    invoice_number TEXT,
    approver_id TEXT,
    transaction_type TEXT NOT NULL,
    description TEXT,
    ground_truth_anomaly INTEGER,
    ground_truth_type TEXT
);

-- 4. High-Performance Audit Indexes
CREATE INDEX IF NOT EXISTS idx_staged_dept_date ON staged_transactions (department, transaction_date);
CREATE INDEX IF NOT EXISTS idx_staged_vendor_amt ON staged_transactions (vendor_id, amount);
CREATE INDEX IF NOT EXISTS idx_staged_inv_vendor ON staged_transactions (invoice_number, vendor_id);
CREATE INDEX IF NOT EXISTS idx_staged_approver ON staged_transactions (approver_id);
CREATE INDEX IF NOT EXISTS idx_staged_date ON staged_transactions (transaction_date);
CREATE INDEX IF NOT EXISTS idx_raw_txnid ON raw_transactions (transaction_id);
