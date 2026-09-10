# Forensic Audit & Internal Controls Investigation Report

**Entity:** Enterprise Global Operations  
**Period Under Review:** Fiscal Years 2024 – 2025  
**Audit Scope:** 101,050 Staged General Ledger & Procurement Transactions ($1.18 Billion Gross Spend)  
**Audit Status:** Completed — Actionable Exceptions Identified  

---

## 1. Executive Summary & Value at Risk (VaR)

An end-to-end forensic audit analytics pipeline was executed across all departmental disbursements and vendor procurement records. Out of **101,050 audited transactions**, **14,054 records (13.91%)** exhibited one or more forensic risk indicators, representing **$187.8 Million in Value at Risk (VaR)** across Critical and High-risk tiers.

### Key Audit Metrics:
| Metric | Quantified Outcome | Audit Significance |
| :--- | :--- | :--- |
| **Total Audited Spend** | **$1,189,380,700** | Full corporate procurement and operational ledger |
| **Critical Risk Exposure** | **$27,403,542** (448 txns) | High-probability fraudulent, duplicate, or rogue transactions |
| **High Risk Exposure** | **$160,456,970** (3,266 txns) | Multi-factor policy breaches and unapproved disbursements |
| **Duplicate Invoices** | **1,050 instances** | Overpayment leakage requiring immediate vendor clawbacks |
| **Threshold Structuring** | **1,450 transactions** | Deliberate split-purchases circumventing approval matrix |
| **Off-Hours / Weekend Spend** | **1,050 transactions** | High-value overrides posted outside standard control windows |

---

## 2. Forensic Typology Deep-Dive & Findings

### Finding 1: Duplicate Invoicing & Dual-Disbursement Schemes
- **Mechanism:** Vendors or internal requisitioners submitted duplicate vouchers with identical invoice numbers and amounts within 0 to 3 days of original payment.
- **Evidence:** Identified 1,050 duplicate invoice payments totaling over $12.3M across top technology, consulting, and marketing vendors.
- **Root Cause:** Enterprise ERP lack of strict pre-payment composite unique constraints on `(Vendor_ID, Invoice_Number, Amount)`.

### Finding 2: Approval Threshold Structuring / Split-Purchase Evasion
- **Mechanism:** Multiple disbursements priced systematically at $4,950 (under $5,000 threshold), $9,900 (under $10,000 threshold), and $49,850 (under $50,000 threshold) within short intervals by the same departmental approver.
- **Evidence:** 1,450 transactions triggered structuring rules, verified by window-function `LAG/LEAD` sequence analysis.
- **Root Cause:** Intentional fragmentation of contracts to bypass senior executive and VP authorization limits.

### Finding 3: Benford's Law Digital Anomalies & Round-Sum Billings
- **Mechanism:** Fictitious professional services retainers submitted as exact round figures ($5,000, $10,000, $25,000, $50,000) lacking itemized deliverables.
- **Evidence:** First-digit analysis revealed significant excess concentration in digits `4` and `5` relative to Benford's theoretical probability ($+1.10\%$ deviation in digit 4), pointing to artificially generated payment amounts.

### Finding 4: Unverified & Missing Governance Disbursements
- **Mechanism:** High-value disbursements processed with `NULL` or blank `approver_id` and non-PO emergency vouchers.
- **Evidence:** 1,000 transactions executed without formal sign-off, representing significant compliance vulnerabilities.

---

## 3. High-Priority Action Items (Top 10 Flagged Cases)

| Txn ID | Date | Department | Vendor Name | Amount ($) | Risk Tier | Primary Flag Reason | Audit Action Required |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `TXN-DUP-819201` | 2024-04-14 | Corporate Legal | Latham & Watkins LLP | $49,950.00 | **Critical** | Duplicate Invoice & Structuring | Issue clawback demand; review partner billing |
| `TXN-DUP-642109` | 2024-08-22 | Information Tech | Snowflake Data Inc | $49,900.00 | **Critical** | Duplicate Invoice & Structuring | Verify Cloud SaaS provisioning and credit note |
| `TXN-2024-041920` | 2024-11-28 | Marketing & Sales | Meta Platforms Ads | $89,450.00 | **Critical** | Weekend/Holiday & Spend Spike | Investigate Thanksgiving off-cycle payment |
| `TXN-2025-010482` | 2025-01-01 | Corporate Legal | Skadden Arps Slate | $94,200.00 | **Critical** | Holiday Posting & Missing Approver | Freeze vendor disbursement account pending review |
| `TXN-DUP-194029` | 2025-03-15 | Finance & Admin | Deloitte & Touche LLP | $50,000.00 | **Critical** | Duplicate Invoice & Round Sum | Verify statutory audit engagement letter scope |
| `TXN-2024-098412` | 2024-07-04 | Operations & Log | FedEx Enterprise Log | $78,500.00 | **Critical** | July 4 Holiday Post & Spike | Review freight manifests for duplicate billings |
| `TXN-2025-082104` | 2025-09-01 | Human Resources | Korn Ferry Exec Search | $49,980.00 | **Critical** | Labor Day Post & Threshold Evasion | Audit executive search placement milestones |
| `TXN-DUP-519204` | 2024-10-12 | Information Tech | CrowdStrike Security | $48,500.00 | **Critical** | Duplicate Invoicing | Reconcile endpoint security license counts |
| `TXN-2025-061920` | 2025-06-19 | Marketing & Sales | Ogilvy & Mather | $75,000.00 | **Critical** | Round Sum & Juneteenth Holiday | Review creative agency timesheets and deliverables |
| `TXN-2024-122501` | 2024-12-25 | Operations & Log | Maersk Shipping Line | $91,300.00 | **Critical** | Christmas Day Post & Extreme Spike | Confirm container demurrage legitimacy |

---

## 4. Remediation & Internal Controls Recommendations

1. **ERP Hard Validation Controls:** Implement automated pre-payment duplicate blocks on `(Vendor_ID, Invoice_Number, Amount)` combinations in accounts payable.
2. **Cumulative Structuring Monitoring:** Configure real-time SQL / Event-stream alert triggers that aggregate vendor/department spending over 7-day rolling windows to eliminate split-transaction threshold circumvention.
3. **Automated ML Isolation Forest Screening:** Integrate the developed `IsolationForest` model as a batch job prior to weekly ACH release cycles.
4. **Mandatory Approver Hard Gates:** Enforce database foreign-key constraints requiring active `approver_id` for all payments $> \$1,000$.
