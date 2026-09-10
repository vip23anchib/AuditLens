"""
AuditLens - High-Performance Financial Transaction Generator with Injected Audit Anomalies
Generates 105,000+ realistic enterprise financial transactions spanning FY2024 - FY2025.
Controlled anomaly injection simulates real-world forensic audit typologies.
"""

import os
import random
import datetime
import numpy as np
import pandas as pd
from faker import Faker

RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)
random.seed(RANDOM_SEED)
fake = Faker()
Faker.seed(RANDOM_SEED)

# ==========================================
# 1. ENTERPRISE MASTER DATA DEFINITIONS
# ==========================================

DEPARTMENTS = {
    "Information Technology": {
        "accounts": ["GL-50100", "GL-50110", "GL-50120"],
        "account_descs": ["Cloud & SaaS Infrastructure", "Hardware & Peripherals", "Cybersecurity Services"],
        "base_mean": 8500.0,
        "base_sigma": 1.1,
        "approvers": ["EMP-IT-101", "EMP-IT-102", "EMP-IT-103"],
        "typical_vendors": ["Amazon Web Services Inc", "Microsoft Azure Cloud", "Snowflake Data Inc", "CrowdStrike Security", "Cisco Systems Inc", "Dell Enterprise Direct"]
    },
    "Marketing & Sales": {
        "accounts": ["GL-50200", "GL-50210", "GL-50220"],
        "account_descs": ["Digital Advertising & Media", "Brand Events & Sponsorship", "PR & Creative Agencies"],
        "base_mean": 6200.0,
        "base_sigma": 1.2,
        "approvers": ["EMP-MKT-201", "EMP-MKT-202", "EMP-MKT-203"],
        "typical_vendors": ["Google Advertising LLC", "Meta Platforms Ads", "Ogilvy & Mather Creative", "HubSpot Inc", "Gartner Research", "Salesforce CRM Direct"]
    },
    "Corporate Legal": {
        "accounts": ["GL-50300", "GL-50310", "GL-50320"],
        "account_descs": ["Outside Legal Counsel", "Regulatory & Compliance Filing", "IP & Patent Prosecution"],
        "base_mean": 12500.0,
        "base_sigma": 1.3,
        "approvers": ["EMP-LEG-301", "EMP-LEG-302", "EMP-LEG-303"],
        "typical_vendors": ["Latham & Watkins LLP", "Skadden Arps Slate", "Thomson Reuters Westlaw", "LexisNexis Compliance", "DLA Piper International"]
    },
    "Human Resources": {
        "accounts": ["GL-50400", "GL-50410", "GL-50420"],
        "account_descs": ["Recruitment & Headhunting", "Employee Benefits & Health", "Training & Leadership Dev"],
        "base_mean": 4500.0,
        "base_sigma": 0.9,
        "approvers": ["EMP-HR-401", "EMP-HR-402", "EMP-HR-403"],
        "typical_vendors": ["Korn Ferry Executive Search", "Workday Human Capital", "LinkedIn Talent Solutions", "Aetna Corporate Health", "BetterUp Coaching Inc"]
    },
    "Operations & Logistics": {
        "accounts": ["GL-50500", "GL-50510", "GL-50520"],
        "account_descs": ["Freight & Global Logistics", "Warehousing & Distribution", "Fleet Maintenance & Fuel"],
        "base_mean": 7800.0,
        "base_sigma": 1.0,
        "approvers": ["EMP-OPS-501", "EMP-OPS-502", "EMP-OPS-503"],
        "typical_vendors": ["FedEx Enterprise Logistics", "DHL Express Global", "Maersk Shipping Line", "Penske Truck Leasing", "Grainger Industrial Supply"]
    },
    "Finance & Administration": {
        "accounts": ["GL-50600", "GL-50610", "GL-50620"],
        "account_descs": ["Statutory Audit & Tax Services", "Facilities & Lease Payments", "Office Supplies & SaaS"],
        "base_mean": 9200.0,
        "base_sigma": 1.15,
        "approvers": ["EMP-FIN-601", "EMP-FIN-602", "EMP-FIN-603"],
        "typical_vendors": ["Deloitte & Touche LLP", "PwC Advisory LLC", "WeWork Global Operations", "Staples Business Advantage", "Bloomberg Finance LP"]
    }
}

PAYMENT_METHODS = ["ACH / Wire Transfer", "Corporate Credit Card", "Electronic Check", "Purchase Order Net-30", "Virtual Card"]
PAYMENT_METHOD_WEIGHTS = [0.45, 0.25, 0.15, 0.10, 0.05]

TRANSACTION_TYPES = ["Vendor Invoice", "Expense Reimbursement", "Procurement Contract", "Subscription Renewal", "Utility Bill"]
TRANSACTION_TYPE_WEIGHTS = [0.60, 0.15, 0.15, 0.07, 0.03]

CURRENCIES = ["USD", "EUR", "GBP", "CAD"]
CURRENCY_WEIGHTS = [0.94, 0.03, 0.02, 0.01]

HOLIDAYS = [
    "2024-01-01", "2024-01-15", "2024-02-19", "2024-05-27", "2024-06-19", "2024-07-04",
    "2024-09-02", "2024-11-28", "2024-12-25",
    "2025-01-01", "2025-01-20", "2025-02-17", "2025-05-26", "2025-06-19", "2025-07-04",
    "2025-09-01", "2025-11-27", "2025-12-25"
]

def build_vendor_master():
    vendors = []
    v_id = 1001
    for dept_name, meta in DEPARTMENTS.items():
        for v_name in meta["typical_vendors"]:
            vendors.append({
                "vendor_id": f"VND-{v_id}",
                "vendor_name": v_name,
                "primary_department": dept_name,
                "risk_tier": "Low" if v_id % 5 != 0 else "Medium"
            })
            v_id += 1
            
    for _ in range(70):
        dept_name = random.choice(list(DEPARTMENTS.keys()))
        company_name = f"{fake.company()} {random.choice(['LLC', 'Inc', 'Corp', 'Solutions', 'Group', 'Services'])}"
        vendors.append({
            "vendor_id": f"VND-{v_id}",
            "vendor_name": company_name,
            "primary_department": dept_name,
            "risk_tier": random.choices(["Low", "Medium", "High"], weights=[0.80, 0.16, 0.04])[0]
        })
        v_id += 1
    return pd.DataFrame(vendors)

def generate_full_dataset(n_baseline: int = 100000):
    print(f"Generating vendor master list...")
    vendor_df = build_vendor_master()
    os.makedirs("data/raw", exist_ok=True)
    os.makedirs("data/processed", exist_ok=True)
    vendor_df.to_csv("data/raw/vendor_master.csv", index=False)

    print(f"Generating {n_baseline:,} transactions using fast vectorized generator...")
    start_date = datetime.date(2024, 1, 1)
    
    dept_names = list(DEPARTMENTS.keys())
    dept_probs = [0.24, 0.20, 0.12, 0.14, 0.16, 0.14]
    dept_indices = np.random.choice(len(dept_names), size=n_baseline, p=dept_probs)
    
    # Pre-generate dates (730 days)
    random_day_offsets = np.random.randint(0, 730, size=n_baseline)
    base_dates = [start_date + datetime.timedelta(days=int(d)) for d in random_day_offsets]
    date_strs = [d.isoformat() for d in base_dates]
    
    # Vendor mapping
    dept_vendor_map = {i: vendor_df[vendor_df["primary_department"] == dept_names[i]].to_dict("records") for i in range(len(dept_names))}
    
    # Pre-calculate arrays for max speed
    chosen_depts = [dept_names[i] for i in dept_indices]
    
    vendor_ids = []
    vendor_names = []
    account_ids = []
    approver_ids = []
    amounts = np.zeros(n_baseline, dtype=np.float64)
    
    for i in range(n_baseline):
        d_idx = dept_indices[i]
        d_name = dept_names[d_idx]
        d_meta = DEPARTMENTS[d_name]
        
        v_rec = random.choice(dept_vendor_map[d_idx])
        vendor_ids.append(v_rec["vendor_id"])
        vendor_names.append(v_rec["vendor_name"])
        
        account_ids.append(random.choice(d_meta["accounts"]))
        approver_ids.append(random.choice(d_meta["approvers"]))
        
        # Log-normal distribution
        mu = np.log(d_meta["base_mean"]) - 0.5 * (d_meta["base_sigma"] ** 2)
        raw_amt = np.random.lognormal(mean=mu, sigma=d_meta["base_sigma"])
        amounts[i] = round(float(np.clip(raw_amt, 25.0, 150000.0) + np.random.uniform(0.01, 0.99)), 2)
        
    payment_method_choices = np.random.choice(PAYMENT_METHODS, size=n_baseline, p=PAYMENT_METHOD_WEIGHTS)
    txn_type_choices = np.random.choice(TRANSACTION_TYPES, size=n_baseline, p=TRANSACTION_TYPE_WEIGHTS)
    currency_choices = np.random.choice(CURRENCIES, size=n_baseline, p=CURRENCY_WEIGHTS)
    
    inv_numbers = [f"INV-{base_dates[i].year}-{random.randint(100000, 999999)}" for i in range(n_baseline)]
    txn_ids = [f"TXN-{base_dates[i].year}-{i+1:06d}" for i in range(n_baseline)]
    descriptions = [f"{txn_type_choices[i]} - {vendor_names[i]} (Ref {random.randint(1000,9999)})" for i in range(n_baseline)]
    
    is_anomaly = np.zeros(n_baseline, dtype=np.int32)
    anomaly_types = ["BENIGN_NORMAL"] * n_baseline
    
    # ----------------------------------------------------
    # CONTROLLED ANOMALY INJECTION
    # ----------------------------------------------------
    print("Injecting controlled anomaly typologies...")
    
    # 1. Round Number Amounts (~1,250 rows)
    round_idx = np.random.choice(n_baseline, size=1250, replace=False)
    round_opts = [5000.00, 10000.00, 15000.00, 25000.00, 40000.00, 50000.00, 75000.00, 100000.00]
    for idx in round_idx:
        amt = float(random.choice(round_opts))
        amounts[idx] = amt
        is_anomaly[idx] = 1
        anomaly_types[idx] = "ANOM_ROUND_AMOUNT"
        descriptions[idx] = f"Special Advisory retainer - exact fee agreement (${int(amt):,})"
        
    # 2. Structuring / Threshold (~1,450 rows)
    struct_idx = np.random.choice([i for i in range(n_baseline) if is_anomaly[i] == 0], size=1450, replace=False)
    struct_opts = [4850.00, 4900.00, 4950.00, 4980.00, 4995.00, 9650.00, 9800.00, 9900.00, 9950.00, 9990.00, 48500.00, 49200.00, 49750.00, 49900.00, 49980.00]
    for idx in struct_idx:
        amounts[idx] = float(random.choice(struct_opts))
        is_anomaly[idx] = 1
        anomaly_types[idx] = "ANOM_THRESHOLD_STRUCTURING"
        descriptions[idx] = f"Expedited milestone payment (Under Approval Threshold)"
        
    # 3. Weekend / Off-Hours (~1,050 rows)
    offhours_idx = np.random.choice([i for i in range(n_baseline) if is_anomaly[i] == 0], size=1050, replace=False)
    for idx in offhours_idx:
        if random.random() < 0.65:
            # Shift date to Sunday
            orig_d = base_dates[idx]
            days_to_sun = (6 - orig_d.weekday()) % 7
            if days_to_sun == 0:
                days_to_sun = 7
            new_d = orig_d + datetime.timedelta(days=days_to_sun)
            date_strs[idx] = new_d.isoformat()
        else:
            date_strs[idx] = random.choice(HOLIDAYS)
        amounts[idx] = round(float(np.random.uniform(18000.0, 95000.0)), 2)
        is_anomaly[idx] = 1
        anomaly_types[idx] = "ANOM_WEEKEND_HOLIDAY"
        descriptions[idx] = "Urgent weekend off-cycle processing override"
        
    # 4. Missing Governance Fields (~1,000 rows)
    missing_idx = np.random.choice([i for i in range(n_baseline) if is_anomaly[i] == 0], size=1000, replace=False)
    for idx in missing_idx:
        choice = random.choice(["approver", "invoice", "both"])
        if choice in ["approver", "both"]:
            approver_ids[idx] = None
        if choice in ["invoice", "both"]:
            inv_numbers[idx] = None
        is_anomaly[idx] = 1
        anomaly_types[idx] = "ANOM_MISSING_GOVERNANCE"
        descriptions[idx] = "Non-PO emergency procurement voucher (Unverified)"

    # 5. Statistical Extreme Outliers (~850 rows)
    outlier_idx = np.random.choice([i for i in range(n_baseline) if is_anomaly[i] == 0], size=850, replace=False)
    for idx in outlier_idx:
        d_name = chosen_depts[idx]
        mean_val = DEPARTMENTS[d_name]["base_mean"]
        extreme_amt = round(float(mean_val * np.random.uniform(20.0, 65.0)), 2)
        amounts[idx] = extreme_amt
        is_anomaly[idx] = 1
        anomaly_types[idx] = "ANOM_STATISTICAL_OUTLIER"
        descriptions[idx] = "Enterprise capital acquisition tranche"

    # Assemble baseline DataFrame
    df = pd.DataFrame({
        "transaction_id": txn_ids,
        "transaction_date": date_strs,
        "account_id": account_ids,
        "department": chosen_depts,
        "vendor_id": vendor_ids,
        "vendor_name": vendor_names,
        "amount": amounts,
        "currency": currency_choices,
        "payment_method": payment_method_choices,
        "invoice_number": inv_numbers,
        "approver_id": approver_ids,
        "transaction_type": txn_type_choices,
        "description": descriptions,
        "is_anomaly": is_anomaly,
        "anomaly_type": anomaly_types
    })

    # 6. Duplicate Invoices (~1,050 rows appended)
    print("  [+] Appending duplicate invoice anomalies...")
    dup_sample = df.sample(n=1050, random_state=101).copy()
    dup_records = []
    for _, row in dup_sample.iterrows():
        orig_d = datetime.date.fromisoformat(row["transaction_date"])
        shift = random.choice([0, 1, 2, 3])
        new_d = orig_d + datetime.timedelta(days=shift)
        d_rec = row.to_dict()
        d_rec["transaction_id"] = f"TXN-DUP-{random.randint(100000, 999999)}"
        d_rec["transaction_date"] = new_d.isoformat()
        d_rec["is_anomaly"] = 1
        d_rec["anomaly_type"] = "ANOM_DUPLICATE_INVOICE"
        d_rec["description"] = f"[RE-SUBMITTED] {row['description']}"
        dup_records.append(d_rec)
    df_dup = pd.DataFrame(dup_records)

    # 7. Duplicate Transaction IDs (~500 rows appended)
    print("  [+] Appending duplicate transaction ID ingestion anomalies...")
    df_combined = pd.concat([df, df_dup], ignore_index=True)
    dup_txn_sample = df_combined.sample(n=500, random_state=107).copy()
    dup_txn_sample["is_anomaly"] = 1
    dup_txn_sample["anomaly_type"] = "ANOM_DUPLICATE_TXN_ID"
    dup_txn_sample["amount"] = np.round(dup_txn_sample["amount"] + 1.00, 2)
    dup_txn_sample["description"] = "[DUPLICATE_FEED_RECORD] " + dup_txn_sample["description"].astype(str)
    
    df_final = pd.concat([df_combined, dup_txn_sample], ignore_index=True)
    df_final = df_final.sample(frac=1.0, random_state=RANDOM_SEED).reset_index(drop=True)
    
    # Save CSV
    raw_csv = "data/raw/financial_transactions_100k.csv"
    print(f"Writing {len(df_final):,} rows to {raw_csv}...")
    df_final.to_csv(raw_csv, index=False)
    
    print("\n" + "=" * 70)
    print(f"DATASET GENERATION SUMMARY")
    print(f"Total Transactions Generated : {len(df_final):,}")
    print(f"Date Range                  : {df_final['transaction_date'].min()} to {df_final['transaction_date'].max()}")
    print(f"Total Gross Spend           : ${df_final['amount'].sum():,.2f}")
    print(f"Mean Transaction Amount     : ${df_final['amount'].mean():,.2f}")
    print(f"Median Transaction Amount   : ${df_final['amount'].median():,.2f}")
    print("\nAnomaly Breakdown by Typology:")
    breakdown = df_final["anomaly_type"].value_counts()
    for anom_type, count in breakdown.items():
        pct = (count / len(df_final)) * 100
        print(f"  - {anom_type:<32}: {count:>6,} ({pct:>5.2f}%)")
    print("=" * 70)
    return df_final

if __name__ == "__main__":
    generate_full_dataset()
