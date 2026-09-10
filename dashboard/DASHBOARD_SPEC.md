# AuditLens - Power BI Dashboard Architecture & Specification Guide

This specification provides a complete blueprint for constructing the **AuditLens Financial Transaction Anomaly Detection & Forensic Audit Analytics Dashboard** in Microsoft Power BI.

---

## 1. Data Model & Star-Schema Relationships

The data model is organized as a Kimball-style Star Schema located in `/dashboard/data/` (available in both `.csv` and `.parquet`):

```
                       +-------------------+
                       |      DimDate      |
                       +-------------------+
                       | DateKey (PK)      |
                       | Year              |
                       | MonthYear         |
                       | IsWeekend         |
                       +---------+---------+
                                 | 1
                                 |
                                 | *
+-------------------+  * +-------+-----------+ *  +-------------------+
|   DimDepartment   +----+ FactTransactions  +----+     DimVendor     |
+-------------------+ 1  +-------------------+  1 +-------------------+
| Department (PK)   |    | Transaction_ID PK |    | Vendor_ID (PK)    |
| Risk_Tier         |    | DateKey (FK)      |    | Vendor_Name       |
| Total_Spend       |    | Department (FK)   |    | Risk_Tier         |
+-------------------+    | Vendor_ID (FK)    |    | Duplicate_Count   |
                         | Amount            |    +-------------------+
                         | Risk_Score        |
                         | Risk_Tier         |
                         +-------------------+
```

### Relationship Mapping:
1. `DimDate[DateKey]` **1 -> \*** `FactTransactions[DateKey]` (Single direction, Active)
2. `DimDepartment[department]` **1 -> \*** `FactTransactions[department]` (Both directions / Single direction)
3. `DimVendor[vendor_id]` **1 -> \*** `FactTransactions[vendor_id]` (Single direction, Active)

---

## 2. Complete DAX Measure Library (Copy & Paste Ready)

Create a dedicated measures table in Power BI named `_AuditMeasures` and insert the following exact DAX expressions:

### Core Financial & Audit KPI Measures

```dax
// 1. Total Gross Portfolio Spend
Total Spend = 
SUM(FactTransactions[amount])
```

```dax
// 2. Total Transaction Volume
Total Transactions = 
COUNTROWS(FactTransactions)
```

```dax
// 3. Total Flagged Anomaly Spend
Total Flagged Spend = 
CALCULATE(
    [Total Spend],
    FactTransactions[risk_tier] IN {"Medium", "High", "Critical"}
)
```

```dax
// 4. Critical & High Risk Spend (Value at Risk - VaR)
Value at Risk (VaR) = 
CALCULATE(
    [Total Spend],
    FactTransactions[risk_tier] IN {"High", "Critical"}
)
```

```dax
// 5. Overall Portfolio Anomaly Rate (%)
Anomaly Rate % = 
DIVIDE([Total Flagged Spend], [Total Spend], 0)
```

```dax
// 6. Total High & Critical Transaction Count
High Risk Transaction Count = 
CALCULATE(
    [Total Transactions],
    FactTransactions[risk_tier] IN {"High", "Critical"}
)
```

```dax
// 7. Critical Risk Transaction Count
Critical Risk Count = 
CALCULATE(
    [Total Transactions],
    FactTransactions[risk_tier] = "Critical"
)
```

```dax
// 8. Average Transaction Value (Ticket Size)
Average Transaction Amount = 
AVERAGE(FactTransactions[amount])
```

```dax
// 9. Composite Risk Score Index
Average Risk Score = 
AVERAGE(FactTransactions[risk_score])
```

---

### Anomaly Typology Specific Measures

```dax
// 10. Duplicate Invoices Identified Count
Duplicate Invoice Count = 
CALCULATE(
    [Total Transactions],
    FactTransactions[flag_duplicate_invoice] = 1
)
```

```dax
// 11. Duplicate Invoice Exposure ($)
Duplicate Invoice Exposure $ = 
CALCULATE(
    [Total Spend],
    FactTransactions[flag_duplicate_invoice] = 1
)
```

```dax
// 12. Structuring / Split-Purchase Transactions Count
Structuring Transaction Count = 
CALCULATE(
    [Total Transactions],
    FactTransactions[flag_threshold_structuring] = 1
)
```

```dax
// 13. Structuring Spend Exposure ($)
Structuring Spend Exposure $ = 
CALCULATE(
    [Total Spend],
    FactTransactions[flag_threshold_structuring] = 1
)
```

```dax
// 14. Weekend / Off-Hours Posting Count
Weekend Flagged Count = 
CALCULATE(
    [Total Transactions],
    FactTransactions[flag_weekend_posting] = 1
)
```

```dax
// 15. Weekend High-Value Spend ($)
Weekend High-Value Spend $ = 
CALCULATE(
    [Total Spend],
    FactTransactions[flag_weekend_posting] = 1
)
```

```dax
// 16. Missing Governance Vouchers Count
Missing Governance Count = 
CALCULATE(
    [Total Transactions],
    FactTransactions[flag_missing_governance] = 1
)
```

```dax
// 17. Extreme Statistical Spikes Count
Statistical Spikes Count = 
CALCULATE(
    [Total Transactions],
    FactTransactions[flag_spend_spike] = 1
)
```

```dax
// 18. Isolation Forest ML Flagged Count
ML Isolation Forest Detections = 
CALCULATE(
    [Total Transactions],
    FactTransactions[ml_iso_forest_flag] = 1
)
```

---

### Time Intelligence & Velocity Measures

```dax
// 19. Prior Year Spend
Spend Previous Year = 
CALCULATE(
    [Total Spend],
    SAMEPERIODLASTYEAR(DimDate[Date])
)
```

```dax
// 20. Year-over-Year Spend Growth %
YoY Spend Growth % = 
VAR PrevYear = [Spend Previous Year]
RETURN
DIVIDE([Total Spend] - PrevYear, PrevYear, 0)
```

```dax
// 21. Month-over-Month Velocity %
MoM Spend Growth % = 
VAR CurrentSpend = [Total Spend]
VAR PrevMonthSpend = CALCULATE([Total Spend], DATEADD(DimDate[Date], -1, MONTH))
RETURN
DIVIDE(CurrentSpend - PrevMonthSpend, PrevMonthSpend, 0)
```

---

## 3. Detailed Page-by-Page Visual Specifications

### Page 1: Executive Audit Summary & KPI Overview
- **Objective:** High-level summary of gross corporate spend, portfolio health, audit exposure, and risk distribution.
- **Top Header Bar:** AuditLens Title, Refresh Timestamp, Global Date Slicer (Year/Quarter), Department Dropdown Slicer.
- **KPI Card Row (Top 5 Cards):**
  1. `[Total Spend]` (Formatted as `$1.18B`)
  2. `[Value at Risk (VaR)]` (Formatted as `$187.8M`, Status Indicator Red)
  3. `[Anomaly Rate %]` (Formatted as `15.8%`)
  4. `[Critical Risk Count]` (Formatted as `448`)
  5. `[Duplicate Invoice Count]` (Formatted as `1,050`)
- **Visual 1 (Top-Left):** *Donut Chart* — Spend Exposure by Risk Tier (`FactTransactions[risk_tier]`).
  - Colors: Low (#2ecc71), Medium (#f39c12), High (#e67e22), Critical (#e74c3c).
- **Visual 2 (Top-Right):** *Combo Chart (Line and Clustered Column)* — Monthly Spend Velocity vs. Flagged Exposure.
  - X-Axis: `DimDate[MonthYear]`
  - Column Y-Axis: `[Total Spend]`
  - Line Y-Axis: `[Total Flagged Spend]`
- **Visual 3 (Bottom-Left):** *Bar Chart* — Department Value at Risk Ranking.
  - Y-Axis: `FactTransactions[department]`
  - X-Axis: `[Value at Risk (VaR)]`
- **Visual 4 (Bottom-Right):** *Treemap* — Spend Exposure by Payment Method & Risk Category.

---

### Page 2: Anomaly Typology Deep Dive & Forensic Analysis
- **Objective:** Forensic breakdown of the 6 detection typologies (Structuring, Duplicates, Round Sums, Off-Hours, Outliers, Governance Gaps).
- **Slicers:** Anomaly Typology Selector (`FactTransactions[primary_flag_reason]`), Department Slicer, Approver ID Search.
- **Visual 1 (Top-Left):** *Clustered Bar Chart* — Audit Typology Financial Exposure ($).
  - Y-Axis: `[primary_flag_reason]`
  - X-Axis: `[Total Spend]`
  - Tooltip: `[Total Transactions]`, `[Average Transaction Amount]`
- **Visual 2 (Top-Right):** *Scatter Plot* — Structuring & Threshold Proximity Distribution.
  - X-Axis: `FactTransactions[amount]` ($0 to $60,000)
  - Y-Axis: `FactTransactions[risk_score]`
  - Legend: `FactTransactions[department]`
  - Reference Lines: $5,000, $10,000, and $50,000 Thresholds.
- **Visual 3 (Bottom-Left):** *Column Chart* — Weekend & Holiday High-Value Spend Distribution by Day of Week (`DimDate[DayOfWeekName]`).
- **Visual 4 (Bottom-Right):** *Comparison Matrix* — SQL Rule Engine vs. Isolation Forest ML Detections overlap.

---

### Page 3: Department & Vendor Exposure Matrix
- **Objective:** Identify high-risk vendor concentrations, unapproved procurement volume, and departmental governance compliance.
- **Visual 1 (Top-Left):** *Quadrant Scatter Chart (Risk vs. Spend Matrix)*:
  - X-Axis: `DimVendor[Total_Invoiced]` ($ Spend)
  - Y-Axis: `DimVendor[Avg_Risk_Score]` (0 - 100)
  - Bubble Size: `DimVendor[Duplicate_Invoice_Count]`
  - Quadrant Lines: Median Spend & Risk Score 40.
- **Visual 2 (Top-Right):** *Table / Matrix* — Top 20 Exposed Vendors.
  - Columns: Vendor Name, Primary Dept, Invoiced Spend, Duplicate Invoices, Avg Risk Score, Risk Tier.
- **Visual 3 (Bottom):** *Stacked Bar Chart* — Departmental Breakdown of Unapproved vs. Approved Transactions (`flag_missing_governance`).

---

### Page 4: High-Risk Transaction Investigation Ledger (Drill-Through Target)
- **Objective:** Operational workbench for internal forensic auditors to triage, investigate, and document specific suspicious transactions.
- **Interactive Grid (Full Page Table):**
  - Columns:
    1. `transaction_id` (Hyperlinked / Monospace)
    2. `transaction_date`
    3. `department`
    4. `vendor_name`
    5. `amount` (Right-aligned, USD format)
    6. `risk_score` (Conditional data bar / heat map: Red >= 60, Orange >= 35, Yellow >= 20)
    7. `risk_tier` (Color tag)
    8. `ml_anomaly_score`
    9. `primary_flag_reason`
    10. `approver_id`
    11. `invoice_number`
- **Drill-Through Filters:** Configured to accept filters from Page 1, 2, and 3 on `vendor_id`, `department`, and `risk_tier`.
- **Export Feature:** Direct CSV export enabled for external audit committee reporting.

---

## 4. Power BI Color Palette & Theme Configuration

Use the following JSON palette configuration in Power BI (`View > Themes > Browse for Themes`):

```json
{
  "name": "AuditLens Corporate Forensic Theme",
  "dataColors": [
    "#1e293b",
    "#e74c3c",
    "#f59e0b",
    "#0284c7",
    "#10b981",
    "#6366f1",
    "#8b5cf6",
    "#64748b"
  ],
  "background": "#f8fafc",
  "foreground": "#0f172a",
  "tableAccent": "#1e293b"
}
```
