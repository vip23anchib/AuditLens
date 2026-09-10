"""
AuditLens - Power BI Data Modeling & Star Schema Exporter
Generates star-schema dimensional tables and fact tables formatted for direct Power BI / Tableau ingestion.
"""

import os
import pandas as pd
import numpy as np

OUTPUT_DIR = "dashboard/data"
PROCESSED_DIR = "data/processed"

def export_star_schema():
    print("=" * 70)
    print("AuditLens - Exporting Power BI Star Schema Datasets")
    print("=" * 70)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    
    enriched_file = f"{PROCESSED_DIR}/audit_enriched_transactions.csv"
    if not os.path.exists(enriched_file):
        raise FileNotFoundError(f"Enriched dataset not found: {enriched_file}. Run src/anomaly_analysis.py first.")
        
    df = pd.read_csv(enriched_file)
    df["transaction_date"] = pd.to_datetime(df["transaction_date"])
    
    # ----------------------------------------------------
    # 1. DimDate (Calendar Dimension)
    # ----------------------------------------------------
    print("Building DimDate table...")
    min_date = df["transaction_date"].min()
    max_date = df["transaction_date"].max()
    date_range = pd.date_range(start=min_date, end=max_date, freq="D")
    
    dim_date = pd.DataFrame({"Date": date_range})
    dim_date["DateKey"] = dim_date["Date"].dt.strftime("%Y%m%d").astype(int)
    dim_date["Year"] = dim_date["Date"].dt.year
    dim_date["Quarter"] = "Q" + dim_date["Date"].dt.quarter.astype(str)
    dim_date["MonthNumber"] = dim_date["Date"].dt.month
    dim_date["MonthName"] = dim_date["Date"].dt.strftime("%B")
    dim_date["MonthYear"] = dim_date["Date"].dt.strftime("%b %Y")
    dim_date["DayOfMonth"] = dim_date["Date"].dt.day
    dim_date["DayOfWeekNumber"] = dim_date["Date"].dt.dayofweek + 1
    dim_date["DayOfWeekName"] = dim_date["Date"].dt.strftime("%A")
    dim_date["IsWeekend"] = dim_date["DayOfWeekNumber"].isin([6, 7]).astype(int)
    dim_date["FiscalYear"] = "FY" + dim_date["Year"].astype(str)
    
    dim_date.to_csv(f"{OUTPUT_DIR}/DimDate.csv", index=False)
    print(f"  [OK] Exported {len(dim_date):,} dates -> {OUTPUT_DIR}/DimDate.csv")
    
    # ----------------------------------------------------
    # 2. DimDepartment (Department Dimension)
    # ----------------------------------------------------
    print("Building DimDepartment table...")
    dept_df = df.groupby("department").agg(
        Total_Spend=("amount", "sum"),
        Transaction_Count=("transaction_id", "count"),
        Avg_Transaction_Size=("amount", "mean"),
        High_Risk_Transactions=("risk_tier", lambda x: (x.isin(["High", "Critical"])).sum())
    ).reset_index()
    dept_df["DepartmentKey"] = range(1, len(dept_df) + 1)
    dept_df["Risk_Concentration_Pct"] = np.round((dept_df["High_Risk_Transactions"] / dept_df["Transaction_Count"]) * 100, 2)
    
    dept_df.to_csv(f"{OUTPUT_DIR}/DimDepartment.csv", index=False)
    print(f"  [OK] Exported {len(dept_df)} departments -> {OUTPUT_DIR}/DimDepartment.csv")
    
    # ----------------------------------------------------
    # 3. DimVendor (Vendor Master Dimension)
    # ----------------------------------------------------
    print("Building DimVendor table...")
    vendor_master = pd.read_csv("data/raw/vendor_master.csv")
    vendor_stats = df.groupby("vendor_id").agg(
        Total_Invoiced=("amount", "sum"),
        Invoice_Count=("transaction_id", "count"),
        Duplicate_Invoice_Count=("flag_duplicate_invoice", "sum"),
        Flagged_Count=("risk_tier", lambda x: (x != "Low").sum()),
        Avg_Risk_Score=("risk_score", "mean")
    ).reset_index()
    
    dim_vendor = pd.merge(vendor_master, vendor_stats, on="vendor_id", how="left").fillna(0)
    dim_vendor.to_csv(f"{OUTPUT_DIR}/DimVendor.csv", index=False)
    print(f"  [OK] Exported {len(dim_vendor)} vendors -> {OUTPUT_DIR}/DimVendor.csv")
    
    # ----------------------------------------------------
    # 4. FactTransactions (Core Fact Table)
    # ----------------------------------------------------
    print("Building FactTransactions table...")
    df["DateKey"] = df["transaction_date"].dt.strftime("%Y%m%d").astype(int)
    
    fact_cols = [
        "transaction_id", "DateKey", "transaction_date", "account_id", 
        "department", "vendor_id", "vendor_name", "amount", "currency", 
        "payment_method", "invoice_number", "approver_id", "transaction_type",
        "is_weekend", "dept_spend_multiplier", "risk_score", "risk_tier", 
        "ml_anomaly_score", "primary_flag_reason",
        "flag_duplicate_invoice", "flag_round_amount", "flag_threshold_structuring",
        "flag_weekend_posting", "flag_missing_governance", "flag_spend_spike",
        "stat_iqr_flag", "stat_zscore_flag", "ml_iso_forest_flag",
        "ground_truth_anomaly", "ground_truth_type"
    ]
    
    fact_transactions = df[fact_cols].copy()
    fact_transactions.to_csv(f"{OUTPUT_DIR}/FactTransactions.csv", index=False)
    # Also save as Parquet for high-performance Power BI Direct Query / Python loads
    fact_transactions.to_parquet(f"{OUTPUT_DIR}/FactTransactions.parquet", index=False)
    print(f"  [OK] Exported {len(fact_transactions):,} facts -> {OUTPUT_DIR}/FactTransactions.csv & .parquet")
    
    print("\n" + "=" * 70)
    print("POWER BI STAR SCHEMA EXPORT COMPLETE")
    print(f"All files saved in: {OUTPUT_DIR}/")
    print("=" * 70)

if __name__ == "__main__":
    export_star_schema()
