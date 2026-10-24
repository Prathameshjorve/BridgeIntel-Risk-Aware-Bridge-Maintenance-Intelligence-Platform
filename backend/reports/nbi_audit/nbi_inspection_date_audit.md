# Inspection-Date (`DATE_OF_INSPECT_090`) Interpretation & Validation Report

## 1. Executive Summary
Field `DATE_OF_INSPECT_090` was analyzed across 1,868,992 total records from the 2023, 2024, and 2025 FHWA National Bridge Inventory (NBI) datasets.
The audit confirmed that **1,868,988 records (99.9998%) contain valid, non-blank dates** adhering strictly to the official Federal Highway Administration specification. Only 4 blank dates exist in the entire 3-year collection (1 in 2024, 3 in 2025).

---

## 2. Official FHWA Specification & Coding Standards
- **Authoritative Standard:** FHWA *Recording and Coding Guide for the Structure Inventory and Appraisal of the Nation's Bridges* (Report No. FHWA-PD-96-001), Item 90: "Date of Inspection".
- **Documentation Definition:** "Record the month and year that the last routine inspection of the structure was performed."
- **Raw Field Format:** A 4-digit number representing $MMYY$.
- **Delimiter / ASCII Behavior:** In the comma-delimited files, leading zeroes were omitted during data export.
  - Months 1–9 (January–September) are recorded as **3-character strings** `MYY` (e.g., `223` = February 2023, `822` = August 2022).
  - Months 10–12 (October–December) are recorded as **4-character strings** `MMYY` (e.g., `1021` = October 2021, `1123` = November 2023).
- **Day Information:** The official standard **does not track or record the calendar day** of routine inspections. Any date parser that introduces an arbitrary calendar day (e.g. defaulting to day 1 or 15) must explicitly flag that the day is an imputed placeholder, not an empirical observation.

---

## 3. Parsing Logic & Two-Digit Year Interpretation
The validated parser implemented in `audit_nbi_records.py` operates as follows:
```python
def parse_date_090(val: str):
    s = val.strip()
    if not s:
        return None, None, "BLANK"
    if not s.isdigit():
        return None, None, "NON_DIGIT"

    if len(s) == 3:
        month = int(s[0])
        yy = int(s[1:])
    elif len(s) == 4:
        month = int(s[:2])
        yy = int(s[2:])
    else:
        return None, None, f"INVALID_LENGTH_{len(s)}"

    if month < 1 or month > 12:
        return None, None, f"INVALID_MONTH_{month}"

    # Century boundary: 00-35 -> 2000-2035; 36-99 -> 1936-1999
    full_year = (2000 + yy) if yy <= 35 else (1900 + yy)
    return month, full_year, "VALID"
```

---

## 4. Observed Year & Month Distributions

### 4.1 Month Distribution
Across all years, inspections are distributed across all 12 calendar months, peaking during mild-weather construction and field inspection seasons (March through November):
- October: ~10.2% (~64,000 / year)
- September: ~9.2% (~57,000 / year)
- August: ~9.0% (~56,000 / year)
- December: ~5.8% (~36,000 / year - winter trough)

### 4.2 Inspection Year Distribution by Annual Snapshot
| Snapshot Release | Total Records | Valid Dates | Top Inspection Year 1 | Top Inspection Year 2 | Older Routine Inspections |
|---|---|---|---|---|---|
| **2023 NBI** | 621,581 | 621,581 (100.0%) | 2022: 310,805 (50.0%) | 2021: 251,210 (40.4%) | 2020: 20,990 (3.4%), 2019: 9,849 (1.6%) |
| **2024 NBI** | 623,218 | 623,216 (99.99%) | 2023: 310,765 (49.9%) | 2022: 254,385 (40.8%) | 2021: 18,520 (3.0%), 2020: 12,271 (2.0%) |
| **2025 NBI** | 624,193 | 624,190 (99.99%) | 2024: 313,241 (50.2%) | 2023: 253,082 (40.5%) | 2022: 20,960 (3.4%), 2021: 11,745 (1.9%) |

---

## 5. Domain Implication: The Biennial NBIS Inspection Cycle
Under the National Bridge Inspection Standards (NBIS, 23 CFR 650.311), public highway bridges are required to undergo routine safety inspections at intervals **not to exceed 24 months** (with certain low-risk structures eligible for 48 months, and distressed structures inspected every 12 months).

This regulatory fact explains the longitudinal matching data:
1. **Between 2023 and 2024 (1-year step):** Exactly **50.60% (312,346)** of matched bridges had a new inspection date recorded, while **49.40% (304,941)** had the identical inspection date from the prior year.
2. **Between 2023 and 2025 (2-year step):** **93.56% (574,037)** of matched bridges had a new inspection date recorded, reflecting the completion of the 2-year inspection cycle.

### Modeling Impact
An annual NBI snapshot is an **inventory database update**, not an event log where every bridge is re-evaluated every year.
If an ML model treated each annual snapshot as an annual re-evaluation step, it would erroneously predict transitions on ~50% of records where no physical inspection took place. Any longitudinal dataset must explicitly filter on records where `DATE_OF_INSPECT_090(t+1) > DATE_OF_INSPECT_090(t)`.
