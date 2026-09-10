"""
AuditLens - Master End-to-End Pipeline Runner
Executes the complete financial anomaly detection & audit analytics workflow from scratch.
"""

import time
import sys
import os

from src.generate_dataset import generate_full_dataset
from src.load_database import load_and_initialize_database
from src.anomaly_analysis import run_python_analysis
from src.export_powerbi_model import export_star_schema

def main():
    start_total = time.time()
    
    print("\n" + "=" * 76)
    print("  AUDITLENS: FINANCIAL ANOMALY DETECTION & AUDIT ANALYTICS PIPELINE")
    print("=" * 76)
    
    # Step 1: Generate 100k+ Transactions & Injected Anomalies
    print("\n>>> [STAGE 1/4] Generating 105,000+ Transactions & Anomaly Injection...")
    t0 = time.time()
    generate_full_dataset(n_baseline=100000)
    print(f"--- Stage 1 completed in {time.time() - t0:.2f}s ---")
    
    # Step 2: Database Ingestion & SQL Transformations
    print("\n>>> [STAGE 2/4] Database Loading, DDL Schema & SQL Risk Scoring Engine...")
    t0 = time.time()
    load_and_initialize_database()
    print(f"--- Stage 2 completed in {time.time() - t0:.2f}s ---")
    
    # Step 3: Python EDA, Statistical Outliers & Isolation Forest ML
    print("\n>>> [STAGE 3/4] Python Statistical Analysis, Benford's Law & Isolation Forest...")
    t0 = time.time()
    run_python_analysis()
    print(f"--- Stage 3 completed in {time.time() - t0:.2f}s ---")
    
    # Step 4: Export Power BI Star Schema
    print("\n>>> [STAGE 4/4] Exporting Power BI Dimensional Star Schema Models...")
    t0 = time.time()
    export_star_schema()
    print(f"--- Stage 4 completed in {time.time() - t0:.2f}s ---")
    
    total_elapsed = time.time() - start_total
    
    print("\n" + "=" * 76)
    print(f"  [SUCCESS] AUDITLENS END-TO-END PIPELINE COMPLETED IN {total_elapsed:.2f} SECONDS")
    print("=" * 76)
    print("Deliverables Summary:")
    print("  - Raw Dataset          : data/raw/financial_transactions_100k.csv")
    print("  - SQLite Database      : data/auditlens.db")
    print("  - Enriched Dataset     : data/processed/audit_enriched_transactions.csv")
    print("  - Top 50 Action Items  : data/processed/top_50_audit_anomalies.csv")
    print("  - EDA Figures          : docs/figures/")
    print("  - Power BI Models      : dashboard/data/ (FactTransactions, DimDate, DimVendor, DimDept)")
    print("  - Power BI Spec & DAX  : dashboard/DASHBOARD_SPEC.md")
    print("  - Jupyter Notebook     : notebooks/audit_anomaly_eda.ipynb")
    print("=" * 76 + "\n")

if __name__ == "__main__":
    main()
