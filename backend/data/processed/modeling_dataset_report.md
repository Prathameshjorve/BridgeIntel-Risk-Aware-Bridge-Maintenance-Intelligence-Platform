# FHWA NBI Longitudinal Modeling Dataset Report (Phase 16)

**Generated:** 2026-10-13T07:50:34.320915  
**Baseline Source:** 2023 FHWA NBI Dataset (`2023HwyBridgesDelimitedAllStates.txt`)  
**Target Source:** 2025 FHWA NBI Dataset (`2025HwyBridgesDelimitedAllStates.txt`)  
**Primary Dataset:** [`bridge_deck_condition_2023_2025.csv`](file:///backend/data/processed/bridge_deck_condition_2023_2025.csv)  

---

## 1. Executive Summary & Sample Accounting

The longitudinal modeling pipeline bridges authentic FHWA National Bridge Inventory releases from 2023 and 2025 to create a leakage-resistant, chronology-verified modeling dataset for predicting future bridge deck condition.

### Record Attrition & Exclusion Accounting Table

| Processing Stage / Criterion | Records | Description / Policy Rationale |
|---|---|---|
| **Raw 2023 NBI Inventory** | 621,581 | Full baseline snapshot read from official delimited file. |
| **Raw 2025 NBI Inventory** | 624,193 | Full target snapshot read from official delimited file. |
| Malformed Rows (2023 / 2025) | 0 / 0 | Zero malformed rows in both 2023 and 2025 releases. |
| Blank Bridge Identifiers | 0 | Zero blank compound identifiers found. |
| Duplicate ID Group Collisions | 4 rows (2 groups) | Excluded both colliding groups (MA & VA) via `HAVING count(*) = 1`. |
| Unique Valid Bridges in 2023 | 621,577 | Total single-occurrence bridges available in 2023 baseline. |
| Unique Valid Bridges in 2025 | 624,189 | Total single-occurrence bridges available in 2025 release. |
| **1-to-1 Matched Bridges** | **613,574** | Bridges co-occurring in both 2023 and 2025 inventory releases. |
| *Attrition: In 2023 only* | 8,003 | Decommissioned, replaced, or administrative removals. |
| *New additions: In 2025 only* | 10,615 | Newly built or newly filed inventory records. |
| Excluded: Non-numeric 2023 Deck | 150,483 | Culverts and non-deck crossings (`DECK_COND_058 = 'N'`). Preserved semantics. |
| Excluded: Non-numeric 2025 Deck | 1,176 | Structures re-classified to culvert/non-deck in 2025. |
| Excluded: Missing/Invalid Dates | 0 | Records with blank or unparseable Item 90 date strings. |
| Excluded: Equal Inspection Dates | 26,694 | Uninspected carryovers (no routine inspection occurred between releases). |
| Excluded: Reverse/Negative Intervals | 11 | Erroneous reporting where later file records earlier inspection timestamp. |
| **Final Usable Modeling Pairs** | **435,210** | **Chronologically verified future-observation modeling instances.** |

---

## 2. Inspection-Interval Distribution

Every pair in the modeling dataset represents a genuinely subsequent physical inspection ($\Delta \text{months} > 0$).

- **Minimum Interval:** 1 months
- **Maximum Interval:** 213 months
- **Most Frequent Intervals (Reflecting Biennial NBIS Cycles):**
  - **24 Months (~2.0 Years):** 319,552 bridges (73.42%)
  - **23 Months (~1.9 Years):** 29,032 bridges (6.67%)
  - **25 Months (~2.1 Years):** 24,158 bridges (5.55%)
  - **48 Months (~4.0 Years):** 16,670 bridges (3.83%)
  - **22 Months (~1.8 Years):** 7,004 bridges (1.61%)

> **Research Note:** Because highway agencies inspect bridges under 24-month cycles, the distribution strongly concentrates at 23–25 months. Days of inspection are NOT recorded in NBI and were never fabricated.

---

## 3. Strict Feature Allowlist & Target Leakage Prevention

Under no circumstances are target-year observations, subsequent inspection findings, or future maintenance records included in the predictive feature matrix.

### Permitted Features (Derived Strictly from 2023 Baseline)
| Feature Name | Source NBI Item | Data Type | Physical / Domain Role |
|---|---|---|---|
| `prior_deck_condition` | `DECK_COND_058` | `int` | Prior operational/structural attribute at baseline. |
| `prior_superstructure_condition` | `SUPERSTRUCTURE_COND_059` | `str` | Prior operational/structural attribute at baseline. |
| `prior_substructure_condition` | `SUBSTRUCTURE_COND_060` | `str` | Prior operational/structural attribute at baseline. |
| `prior_culvert_condition` | `CULVERT_COND_062` | `str` | Prior operational/structural attribute at baseline. |
| `structure_kind_043a` | `STRUCTURE_KIND_043A` | `str` | Prior operational/structural attribute at baseline. |
| `structure_type_043b` | `STRUCTURE_TYPE_043B` | `str` | Prior operational/structural attribute at baseline. |
| `deck_structure_type_107` | `DECK_STRUCTURE_TYPE_107` | `str` | Prior operational/structural attribute at baseline. |
| `surface_type_108a` | `SURFACE_TYPE_108A` | `str` | Prior operational/structural attribute at baseline. |
| `membrane_type_108b` | `MEMBRANE_TYPE_108B` | `str` | Prior operational/structural attribute at baseline. |
| `deck_protection_108c` | `DECK_PROTECTION_108C` | `str` | Prior operational/structural attribute at baseline. |
| `structure_len_mt` | `STRUCTURE_LEN_MT_049` | `float` | Prior operational/structural attribute at baseline. |
| `max_span_len_mt` | `MAX_SPAN_LEN_MT_048` | `float` | Prior operational/structural attribute at baseline. |
| `deck_width_mt` | `DECK_WIDTH_MT_052` | `float` | Prior operational/structural attribute at baseline. |
| `traffic_lanes_on` | `TRAFFIC_LANES_ON_028A` | `int` | Prior operational/structural attribute at baseline. |
| `adt` | `ADT_029` | `float` | Prior operational/structural attribute at baseline. |
| `percent_adt_truck` | `PERCENT_ADT_TRUCK_109` | `float` | Prior operational/structural attribute at baseline. |
| `detour_kilos` | `DETOUR_KILOS_019` | `float` | Prior operational/structural attribute at baseline. |
| `functional_class` | `FUNCTIONAL_CLASS_026` | `str` | Prior operational/structural attribute at baseline. |
| `maintenance_responsibility` | `MAINTENANCE_021` | `str` | Prior operational/structural attribute at baseline. |
| `owner` | `OWNER_022` | `str` | Prior operational/structural attribute at baseline. |
| `year_built` | `YEAR_BUILT_027` | `int` | Prior operational/structural attribute at baseline. |
| `structure_age_at_inspection` | `DERIVED_AGE` | `int` | Prior operational/structural attribute at baseline. |
| `state_code` | `STATE_CODE_001` | `str` | Prior operational/structural attribute at baseline. |
| `prior_inspect_month` | `DERIVED_MONTH_2023` | `int` | Prior operational/structural attribute at baseline. |
| `prior_inspect_year` | `DERIVED_YEAR_2023` | `int` | Prior operational/structural attribute at baseline. |
| `inspect_freq_months` | `INSPECT_FREQ_MONTHS_091` | `int` | Prior operational/structural attribute at baseline. |

### Strictly Prohibited Leakage Fields (Confirmed Absent from Features)
- `2025_DECK_COND_058` (Kept exclusively as `target_deck_condition`)
- `2025_LOWEST_RATING` & `2025_BRIDGE_CONDITION` (Direct derived leakage)
- `2025_SUPERSTRUCTURE_COND_059`, `2025_SUBSTRUCTURE_COND_060`, `2025_CULVERT_COND_062` (Concurrent inspection leakage)
- `WORK_PROPOSED_*` & `WORK_DONE_*` (Post-hoc maintenance records)
- `bridge_id` (Retained exclusively for grouped partitioning and audits)

---

## 4. Evaluation Strategy & Zero-Overlap Grouped Splitting

To prevent identity leakage, data partitioning is governed by SHA-256 hash hashing of `bridge_id`:

- **Training Set (70%):** 304,541 bridges (69.98%)
- **Validation Set (15%):** 65,089 bridges (14.96%)
- **Test Set (15%):** 65,580 bridges (15.07%)

**Identity Leakage Guarantee:** Zero bridge identifiers overlap between Train, Validation, and Test partitions.

> **Temporal Generalization Boundary:** Because this dataset's target already represents a future observation ($T_{2023} \to T_{2025}$), a bridge-grouped split evaluates generalization to *unseen bridge assets* across the same future horizon, rather than forward generalization across calendar decades.

---

## 5. Descriptive Persistence Baseline Benchmark

The naive persistence baseline predicts no rating change: $\hat{y}_{2025} = y_{2023}$.

- **Test Set Size:** 65,580 bridges
- **Exact Rating Match Accuracy:** **86.8%**
- **Ordinal Mean Absolute Error (MAE):** **0.1625**
- **Active Deterioration Event Recall:** **0.0%**

> **Critical Scientific Finding:** The persistence baseline achieves an ostensibly high 87%+ accuracy purely because bridge deterioration is slow. However, it detects **0.0% of deteriorating structures** ($	ext{Recall} = 0.0\%$). An ML model must be evaluated on its ability to detect the deteriorating minority (Deterioration Recall, PR-AUC, Macro-F1), not raw accuracy.

---

## 6. Formal Data Readiness Decision

### **Decision: READY WITH LIMITATIONS**
- **Ready:** Pipeline produces over 430,000 verified, chronologically separated 1-to-1 bridge pairs with clean feature representations and zero target leakage.
- **Limitations:** Evaluation must use Grouped Splitting and Deterioration Recall / PR-AUC benchmarks against the 87%+ persistence baseline.
