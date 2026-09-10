"""
AuditLens - Database Ingestion and SQL Pipeline Orchestrator
Loads raw CSV datasets into SQLite (and PostgreSQL compatible) database,
executes staging CTEs, applies window-function risk models, and creates flagged views.
"""

import os
import sqlite3
import time
import pandas as pd
from sqlalchemy import create_engine, text

DB_PATH = "data/auditlens.db"
DATABASE_URI = os.getenv("DATABASE_URI", f"sqlite:///{DB_PATH}")

def run_sql_script(conn, script_path: str):
    """Executes a multi-statement SQL script using SQLite/SQLAlchemy connection."""
    print(f"  [+] Executing SQL script: {script_path}...")
    with open(script_path, "r", encoding="utf-8") as f:
        sql_content = f.read()
    
    # Use raw sqlite3 connection executescript for robust multi-statement execution
    if "sqlite" in DATABASE_URI:
        cursor = conn.cursor()
        cursor.executescript(sql_content)
        conn.commit()
    else:
        with conn.begin():
            conn.execute(text(sql_content))

def load_and_initialize_database():
    start_time = time.time()
    print("=" * 70)
    print("AuditLens - Database Ingestion & SQL Transformation Pipeline")
    print("=" * 70)
    
    os.makedirs("data", exist_ok=True)
    
    raw_csv = "data/raw/financial_transactions_100k.csv"
    vendor_csv = "data/raw/vendor_master.csv"
    
    if not os.path.exists(raw_csv) or not os.path.exists(vendor_csv):
        raise FileNotFoundError(f"Raw data files not found in data/raw/. Please run src/generate_dataset.py first.")

    # SQLite native connection for blazing fast ingestion
    conn = sqlite3.connect(DB_PATH)
    
    # 1. Apply Schema DDL
    print("\n[Step 1/5] Applying Database DDL Schema...")
    run_sql_script(conn, "sql/01_schema.sql")
    
    # 2. Ingest Vendor Master
    print("\n[Step 2/5] Ingesting Vendor Master...")
    vendor_df = pd.read_csv(vendor_csv)
    vendor_df.to_sql("dim_vendors", conn, if_exists="append", index=False)
    print(f"  [OK] Ingested {len(vendor_df)} vendors into 'dim_vendors'.")
    
    # 3. Ingest Raw Transactions Feed
    print("\n[Step 3/5] Ingesting Raw Transactions Feed (100k+ rows)...")
    raw_df = pd.read_csv(raw_csv)
    raw_df.to_sql("raw_transactions", conn, if_exists="append", index=False, chunksize=10000)
    print(f"  [OK] Ingested {len(raw_df):,} records into 'raw_transactions'.")
    
    # 4. Execute Staging & Deduplication CTEs
    print("\n[Step 4/5] Executing Staging & Deduplication CTEs...")
    run_sql_script(conn, "sql/02_staging_ctes.sql")
    
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM staged_transactions")
    staged_count = cursor.fetchone()[0]
    print(f"  [OK] Successfully cleaned & staged {staged_count:,} transactions (deduplicated).")
    
    # 5. Build Risk-Scoring Engine & Materialized Table
    print("\n[Step 5/5] Building Forensic Risk-Scoring Engine & Flagged Table...")
    run_sql_script(conn, "sql/05_flagged_transactions_view.sql")
    
    # Validation & Summary Report
    cursor.execute("""
        SELECT 
            risk_tier,
            COUNT(*) AS txn_count,
            ROUND(SUM(amount), 2) AS total_spend,
            ROUND(AVG(risk_score), 1) AS avg_risk_score
        FROM flagged_transactions
        GROUP BY risk_tier
        ORDER BY avg_risk_score DESC
    """)
    summary = cursor.fetchall()
    
    cursor.execute("SELECT COUNT(*) FROM flagged_transactions WHERE risk_tier IN ('Medium', 'High', 'Critical')")
    flagged_anomalies_count = cursor.fetchone()[0]
    
    conn.close()
    
    elapsed = time.time() - start_time
    print("\n" + "=" * 70)
    print(f"DATABASE INGESTION & RISK ENGINE COMPLETE ({elapsed:.2f}s)")
    print(f"Database File: {DB_PATH}")
    print(f"Total Staged Transactions: {staged_count:,}")
    print(f"Total Flagged Audit Risks: {flagged_anomalies_count:,} ({(flagged_anomalies_count/staged_count)*100:.2f}%)")
    print("\nRisk Tier Distribution:")
    for tier, count, spend, avg_score in summary:
        print(f"  - {tier:<10}: {count:>6,} txns | ${spend:>14,.2f} | Avg Risk Score: {avg_score}")
    print("=" * 70)

if __name__ == "__main__":
    load_and_initialize_database()
