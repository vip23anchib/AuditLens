"""
AuditLens - Python/Pandas & ML Anomaly Detection Engine
Performs Exploratory Data Analysis, Statistical Outlier Detection (IQR & Z-Score),
Benford's Law Forensic Digit Analysis, Unsupervised Machine Learning (Isolation Forest),
and generates audit-ready enriched datasets and visual reports.
"""

import os
import sqlite3
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

# Set aesthetic visual themes
plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.size"] = 10
plt.rcParams["figure.titlesize"] = 14
plt.rcParams["figure.dpi"] = 150

DB_PATH = "data/auditlens.db"
OUTPUT_DIR = "docs/figures"
PROCESSED_DIR = "data/processed"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

# ==========================================
# 1. DATA EXTRACTION & FEATURE ENGINEERING
# ==========================================

def load_data_from_db() -> pd.DataFrame:
    print(f"Connecting to database: {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT * FROM flagged_transactions"
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    df["transaction_date"] = pd.to_datetime(df["transaction_date"])
    print(f"Loaded {len(df):,} staged transactions from database.")
    return df

def engineer_audit_features(df: pd.DataFrame) -> pd.DataFrame:
    print("Engineering statistical & forensic ML features...")
    df = df.copy()
    
    # Feature 1: Log Amount (handles financial long-tail)
    df["log_amount"] = np.log1p(df["amount"])
    
    # Feature 2: Proximity to common approval limits ($5k, $10k, $50k)
    def calc_threshold_proximity(amt):
        limits = [5000.0, 10000.0, 50000.0]
        min_diff = min([abs(amt - lim) for lim in limits])
        return min_diff
    
    df["threshold_dist"] = df["amount"].apply(calc_threshold_proximity)
    df["is_structuring_candidate"] = (
        ((df["amount"] >= 4800) & (df["amount"] < 5000)) |
        ((df["amount"] >= 9500) & (df["amount"] < 10000)) |
        ((df["amount"] >= 48000) & (df["amount"] < 50000))
    ).astype(int)
    
    # Feature 3: First Digit for Benford's Law
    df["first_digit"] = df["amount"].astype(str).str.extract(r"^([1-9])")[0].astype(float).fillna(0).astype(int)
    
    # Feature 4: Round Amount indicator
    df["is_clean_round_sum"] = (
        (df["amount"] >= 1000) & 
        (df["amount"] % 1000 == 0)
    ).astype(int)
    
    return df

# ==========================================
# 2. STATISTICAL OUTLIER DETECTION (IQR & Z-SCORE)
# ==========================================

def apply_statistical_outlier_detection(df: pd.DataFrame) -> pd.DataFrame:
    print("Executing Statistical Outlier Detection (IQR & Robust Z-Score)...")
    df = df.copy()
    
    # ----------------------------------------------------
    # Method 1: Interquartile Range (IQR) per Department
    # ----------------------------------------------------
    df["stat_iqr_flag"] = 0
    df["iqr_upper_bound"] = 0.0
    
    for dept, grp in df.groupby("department"):
        q25 = grp["amount"].quantile(0.25)
        q75 = grp["amount"].quantile(0.75)
        iqr = q75 - q25
        upper_limit = q75 + (2.5 * iqr) # 2.5 IQR for moderate-to-extreme financial outliers
        
        dept_mask = (df["department"] == dept)
        df.loc[dept_mask, "iqr_upper_bound"] = upper_limit
        df.loc[dept_mask & (df["amount"] > upper_limit), "stat_iqr_flag"] = 1
        
    # ----------------------------------------------------
    # Method 2: Robust Z-Score / Modified Z-Score (MAD)
    # ----------------------------------------------------
    df["stat_zscore"] = 0.0
    df["stat_zscore_flag"] = 0
    
    for dept, grp in df.groupby("department"):
        median_amt = grp["amount"].median()
        mad = (grp["amount"] - median_amt).abs().median()
        if mad == 0:
            mad = grp["amount"].std()
            
        modified_z = 0.6745 * (grp["amount"] - median_amt) / (mad + 1e-6)
        dept_mask = (df["department"] == dept)
        df.loc[dept_mask, "stat_zscore"] = modified_z
        df.loc[dept_mask & (modified_z > 4.5), "stat_zscore_flag"] = 1 # 4.5 MAD threshold
        
    print(f"  [+] IQR Method flagged      : {df['stat_iqr_flag'].sum():,} transactions")
    print(f"  [+] Z-Score Method flagged  : {df['stat_zscore_flag'].sum():,} transactions")
    return df

# ==========================================
# 3. MACHINE LEARNING: ISOLATION FOREST
# ==========================================

def apply_isolation_forest(df: pd.DataFrame) -> pd.DataFrame:
    print("Training Unsupervised Machine Learning Model: Isolation Forest...")
    df = df.copy()
    
    # Multi-dimensional feature matrix
    feature_cols = [
        "log_amount", 
        "dept_spend_multiplier", 
        "is_weekend", 
        "is_clean_round_sum", 
        "is_structuring_candidate",
        "day_of_week"
    ]
    
    X = df[feature_cols].copy()
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Contamination set to 4.5% to isolate top high-dimensional anomalies
    iso_forest = IsolationForest(
        n_estimators=150,
        contamination=0.045,
        max_samples="auto",
        random_state=42,
        n_jobs=-1
    )
    
    iso_forest.fit(X_scaled)
    # -1 indicates anomaly, 1 indicates normal
    predictions = iso_forest.predict(X_scaled)
    anomaly_scores = iso_forest.decision_function(X_scaled)
    
    df["ml_iso_forest_flag"] = (predictions == -1).astype(int)
    # Normalize score so higher score = higher anomaly likelihood (0 to 100)
    norm_score = 100.0 * (1.0 - ((anomaly_scores - anomaly_scores.min()) / (anomaly_scores.max() - anomaly_scores.min())))
    df["ml_anomaly_score"] = np.round(norm_score, 1)
    
    print(f"  [+] Isolation Forest flagged: {df['ml_iso_forest_flag'].sum():,} transactions")
    return df

# ==========================================
# 4. BENFORD'S LAW FORENSIC ANALYSIS
# ==========================================

def perform_benfords_law_analysis(df: pd.DataFrame) -> pd.DataFrame:
    print("Performing Benford's Law Leading Digit Distribution Test...")
    digits = list(range(1, 10))
    benford_expected = [np.log10(1 + 1 / d) * 100.0 for d in digits]
    
    valid_digits = df[df["first_digit"].isin(digits)]["first_digit"]
    actual_counts = valid_digits.value_counts(normalize=True).reindex(digits, fill_value=0.0) * 100.0
    
    benford_df = pd.DataFrame({
        "Digit": digits,
        "Expected_Benford_Pct": np.round(benford_expected, 2),
        "Actual_Observed_Pct": np.round(actual_counts.values, 2)
    })
    benford_df["Deviation_Pct"] = np.round(benford_df["Actual_Observed_Pct"] - benford_df["Expected_Benford_Pct"], 2)
    
    # Plot Benford's Law
    fig, ax = plt.subplots(figsize=(8, 4.5))
    bar_width = 0.35
    x = np.arange(len(digits))
    
    ax.bar(x - bar_width/2, benford_df["Expected_Benford_Pct"], bar_width, label="Benford's Law (Theoretical)", color="#34495e", alpha=0.85)
    ax.bar(x + bar_width/2, benford_df["Actual_Observed_Pct"], bar_width, label="AuditLens Transactions (Observed)", color="#e74c3c", alpha=0.85)
    
    ax.set_xlabel("Leading Digit (1 - 9)", fontweight="bold")
    ax.set_ylabel("Frequency Percentage (%)", fontweight="bold")
    ax.set_title("Benford's Law First-Digit Forensic Audit Test", fontsize=12, fontweight="bold", pad=12)
    ax.set_xticks(x)
    ax.set_xticklabels(digits)
    ax.legend(frameon=True)
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/01_benfords_law_analysis.png")
    plt.close()
    
    return benford_df

# ==========================================
# 5. VISUAL EXPLORATORY DATA ANALYSIS (EDA)
# ==========================================

def generate_eda_figures(df: pd.DataFrame):
    print(f"Generating EDA visual figures in {OUTPUT_DIR}...")
    
    # Figure 2: Spend Distribution by Department (Log Scale)
    plt.figure(figsize=(10, 5))
    sns.boxplot(data=df, x="department", y="amount", hue="department", palette="Set2", legend=False)
    plt.yscale("log")
    plt.title("Transaction Amount Distribution by Department (Logarithmic Scale)", fontsize=12, fontweight="bold")
    plt.xlabel("Department", fontweight="bold")
    plt.ylabel("Amount ($ USD - Log Scale)", fontweight="bold")
    plt.xticks(rotation=20, ha="right")
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/02_spend_distribution_by_dept.png")
    plt.close()
    
    # Figure 3: Anomaly Breakdown by Risk Tier & Detection Layer Overlap
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    
    # Subplot A: Risk Tier Share
    tier_counts = df["risk_tier"].value_counts()[["Low", "Medium", "High", "Critical"]]
    colors = ["#2ecc71", "#f39c12", "#e67e22", "#e74c3c"]
    axes[0].pie(tier_counts, labels=tier_counts.index, autopct="%1.1f%%", startangle=140, colors=colors, explode=(0, 0.05, 0.1, 0.15))
    axes[0].set_title("Transaction Portfolio by Audit Risk Tier", fontsize=11, fontweight="bold")
    
    # Subplot B: Monthly Spend Trend & Anomaly Spikes
    monthly = df.groupby(["transaction_year", "transaction_month"]).agg(
        total_spend=("amount", "sum"),
        flagged_spend=("amount", lambda x: df.loc[x.index][df.loc[x.index, "risk_tier"] != "Low"]["amount"].sum())
    ).reset_index()
    monthly["Period"] = monthly["transaction_year"].astype(str) + "-" + monthly["transaction_month"].astype(str).str.zfill(2)
    
    axes[1].plot(monthly["Period"], monthly["total_spend"] / 1e6, marker="o", color="#2980b9", label="Total Spend ($M)", linewidth=2)
    axes[1].bar(monthly["Period"], monthly["flagged_spend"] / 1e6, color="#e74c3c", alpha=0.6, label="Flagged Spend ($M)")
    axes[1].set_title("Monthly Spend Trajectory & Flagged Exposure ($M)", fontsize=11, fontweight="bold")
    axes[1].set_xlabel("Year-Month", fontweight="bold")
    axes[1].set_ylabel("Spend Amount ($ Millions)", fontweight="bold")
    axes[1].tick_params(axis="x", rotation=45)
    axes[1].legend()
    
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/03_risk_tiers_and_monthly_trends.png")
    plt.close()
    
    # Figure 4: Model Comparison Matrix
    plt.figure(figsize=(8, 5))
    method_overlap = pd.DataFrame({
        "SQL Rule Engine": (df["risk_tier"] != "Low").astype(int),
        "Statistical IQR": df["stat_iqr_flag"],
        "Robust Z-Score": df["stat_zscore_flag"],
        "Isolation Forest ML": df["ml_iso_forest_flag"],
        "Ground Truth": df["ground_truth_anomaly"]
    })
    corr = method_overlap.corr()
    sns.heatmap(corr, annot=True, cmap="Blues", fmt=".2f", vmin=0, vmax=1)
    plt.title("Detection Layer Correlation Matrix (SQL vs Stat vs ML vs Ground Truth)", fontsize=11, fontweight="bold")
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/04_detection_methods_correlation.png")
    plt.close()

# ==========================================
# 6. ENRICHED EXPORT & TOP ANOMALIES LEDGER
# ==========================================

def build_top_anomalies_and_exports(df: pd.DataFrame):
    print("Compiling Top 50 Priority Audit Action Items...")
    
    # Top 50 priority candidates: Sort by Composite Risk Score descending, then ML Score descending, then Amount
    top_50 = df.sort_values(by=["risk_score", "ml_anomaly_score", "amount"], ascending=[False, False, False]).head(50).copy()
    
    # Generate contextual narrative explanation for auditors
    def generate_narrative(row):
        reasons = []
        if row["flag_duplicate_invoice"] == 1:
            reasons.append(f"Duplicate invoice detected for vendor '{row['vendor_name']}' (${row['amount']:,.2f})")
        if row["flag_threshold_structuring"] == 1:
            reasons.append(f"Amount ${row['amount']:,.2f} structured immediately below approval threshold")
        if row["flag_spend_spike"] == 1 or row["stat_zscore_flag"] == 1:
            reasons.append(f"Spend spike ({row['dept_spend_multiplier']:.1f}x department norm of ${row['dept_baseline_mean']:,.2f})")
        if row["flag_missing_governance"] == 1:
            reasons.append("Missing mandatory approver ID or invoice voucher")
        if row["flag_weekend_posting"] == 1:
            reasons.append(f"High-value post executed on {row['day_name']}")
        if row["flag_round_amount"] == 1:
            reasons.append("Unusual clean round-sum retainer billing")
        if row["ml_iso_forest_flag"] == 1:
            reasons.append(f"High ML Isolation Forest score ({row['ml_anomaly_score']:.1f}/100)")
            
        return "; ".join(reasons) if reasons else "Elevated risk characteristics"
        
    top_50["audit_investigation_narrative"] = top_50.apply(generate_narrative, axis=1)
    
    top_50_cols = [
        "transaction_id", "transaction_date", "department", "vendor_name", 
        "amount", "risk_tier", "risk_score", "ml_anomaly_score", 
        "primary_flag_reason", "audit_investigation_narrative"
    ]
    
    top_50_file = f"{PROCESSED_DIR}/top_50_audit_anomalies.csv"
    top_50[top_50_cols].to_csv(top_50_file, index=False)
    print(f"  [OK] Saved Top 50 Action Items: {top_50_file}")
    
    # Export fully enriched transactions for Power BI and audit teams
    enriched_file = f"{PROCESSED_DIR}/audit_enriched_transactions.csv"
    print(f"Writing complete enriched transaction dataset ({len(df):,} rows) to {enriched_file}...")
    df.to_csv(enriched_file, index=False)
    
    # Summary Metrics KPI table for Power BI cards
    kpis = {
        "Total_Transactions": [len(df)],
        "Total_Spend_USD": [df["amount"].sum()],
        "Total_Flagged_Transactions": [(df["risk_tier"] != "Low").sum()],
        "Total_Flagged_Spend_USD": [df[df["risk_tier"] != "Low"]["amount"].sum()],
        "Critical_Risk_Count": [(df["risk_tier"] == "Critical").sum()],
        "Critical_Risk_Spend_USD": [df[df["risk_tier"] == "Critical"]["amount"].sum()],
        "High_Risk_Count": [(df["risk_tier"] == "High").sum()],
        "High_Risk_Spend_USD": [df[df["risk_tier"] == "High"]["amount"].sum()],
        "Duplicate_Invoices_Count": [df["flag_duplicate_invoice"].sum()],
        "Structuring_Anomalies_Count": [df["flag_threshold_structuring"].sum()],
        "Weekend_Spend_Anomalies_Count": [df["flag_weekend_posting"].sum()]
    }
    kpi_df = pd.DataFrame(kpis)
    kpi_df.to_csv(f"{PROCESSED_DIR}/audit_summary_metrics.csv", index=False)
    print(f"  [OK] Saved Audit KPI metrics: {PROCESSED_DIR}/audit_summary_metrics.csv")

# ==========================================
# 7. MAIN EXECUTION ROUTINE
# ==========================================

def run_python_analysis():
    print("=" * 70)
    print("AuditLens - Python/Pandas & ML Anomaly Detection Pipeline")
    print("=" * 70)
    
    # 1. Extract & Engineer Features
    df = load_data_from_db()
    df = engineer_audit_features(df)
    
    # 2. Statistical Outlier Detection
    df = apply_statistical_outlier_detection(df)
    
    # 3. Machine Learning Isolation Forest
    df = apply_isolation_forest(df)
    
    # 4. Benford's Law Analysis
    benford_df = perform_benfords_law_analysis(df)
    print("\nBenford's Law First-Digit Comparison:")
    print(benford_df.to_string(index=False))
    
    # 5. Visual EDA Figures
    generate_eda_figures(df)
    
    # 6. Deliverables & Enriched Exports
    build_top_anomalies_and_exports(df)
    
    print("\n" + "=" * 70)
    print("PYTHON & ML ANALYSIS COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    run_python_analysis()
