# NBI Duplicate Identifier & Malformed Record Report

## 1. Overview
This audit examines record collisions and structural syntax errors across authentic FHWA NBI datasets for 2023, 2024, and 2025.

---

## 2. Malformed Row Audit

| Year | Total Data Rows Read | Expected Column Count | Malformed Rows | Valid Parse Rate |
|---|---|---|---|---|
| **2023** | 621,581 | 123 | **0** | **100.00%** |
| **2024** | 623,218 | 123 | **1** | **99.9998%** |
| **2025** | 624,193 | 123 | **0** | **100.00%** |

### 2.1 Diagnosis of the Single 2024 Malformed Record
- **File:** `backend/2024/2024HwyBridgesDelimitedAllStates.txt`
- **Line Number:** 459,987
- **Bridge Identifier:** State `42` (Pennsylvania), Structure `000000000021795` (PA Turnpike I-76 Ramp AB)
- **Error Description:** Line 459,987 yields **124 columns** (1 extra column) when parsed with single-quote text qualifiers.
- **Root Cause Analysis:**
  In Pennsylvania DOT's 2024 data submission, text fields around Item 99/100 (`OTHR_STATE_STRUC_NO_099` and `STRAHNET_HIGHWAY_100`) contain an unquoted internal comma:
  ```text
  ...9,423,24,N  ,N  ,N  ,,,,0,0,0,,,0,1sDPG, 2sDIB   ,0,N,2,,1,0,0,1,1,0,0,16...
  ```
  The literal substring `1sDPG, 2sDIB` was split into two tokens, causing an off-by-one field shift across all downstream columns (including condition items and coordinates).
- **Corrective Handling:**
  In `audit_nbi_records.py` and `compare_nbi_years.py`, lines where `len(row) != len(header)` are identified, accurately counted, and isolated into a diagnostic quarantine log. The remaining 623,217 records parse cleanly without corruption.

---

## 3. Duplicate Identifier Audit (`STATE_CODE_001` + `STRUCTURE_NUMBER_008`)

Under federal NBI specifications, every physical bridge record is uniquely identified by the combination of its FIPS State Code (`STATE_CODE_001`, Item 1) and Structure Number (`STRUCTURE_NUMBER_008`, Item 8).

| Year | Total Rows | Unique Bridge Keys | Duplicate Key Groups | Total Rows in Duplicate Groups |
|---|---|---|---|---|
| **2023** | 621,581 | 621,579 | **2** | **4** |
| **2024** | 623,217* | 623,215 | **2** | **4** |
| **2025** | 624,193 | 624,191 | **2** | **4** |

*\*Excluding the 1 malformed row at line 459,987.*

### 3.1 Group 1: State `25` (Massachusetts), Structure `N100108PDDOTNBI`
- **2023 Dataset (Lines 246,723 & 246,724):** Exact duplicate records. Both rows possess identical inspection dates (`721` = July 2021) and identical component ratings (Deck 7, Super 7, Sub 7).
- **2024 Dataset (Lines 247,253 & 247,254):** Discrepant inspection dates. Line 247,253 lists `DATE_OF_INSPECT_090 = '723'`, while Line 247,254 lists `DATE_OF_INSPECT_090 = '823'`. Condition ratings remain identical (Deck 7, Super 7, Sub 7).
- **2025 Dataset (Lines 247,564 & 247,565):** Retains the two entries from 2024 with identical dates (`723` and `823`).
- **Nature of Collision:** Administrative dual-submission by the reporting state authority.

### 3.2 Group 2: State `51` (Virginia), Structure `00000000001826`
- **2023 Dataset (Lines 572,609 & 572,610):**
  - Line 572,609: `DECK_COND_058 = 'N'`, `CULVERT_COND_062 = '6'`, inspected in February 2022 (`222`).
  - Line 572,610: `DECK_COND_058 = '7'`, `CULVERT_COND_062 = 'N'`, inspected in September 2022 (`922`).
- **2024 Dataset (Lines 574,023 & 574,024):**
  - Line 574,023: Bridge deck (`DECK_COND_058 = '7'`), inspected September 2022 (`922`).
  - Line 574,024: Culvert structure (`DECK_COND_058 = 'N'`), inspected February 2024 (`224`).
- **2025 Dataset (Lines 574,874 & 574,875):**
  - Line 574,874: Bridge deck (`DECK_COND_058 = '6'`), inspected September 2024 (`924`).
  - Line 574,875: Culvert structure (`DECK_COND_058 = 'N'`), inspected February 2024 (`224`).
- **Nature of Collision:** Conflicting physical asset representation. Two distinct structural entities (a culvert and an adjacent roadway bridge) share the same structure number under state recording conventions.

---

## 4. Exclusion & Harmonization Policy
1. **Never Silently Deduplicate:** Automatically deduplicating via `first()` or `last()` would arbitrarily drop either the bridge deck or the culvert in Group 2.
2. **Defensible Exclusion Rule:** In `compare_nbi_years.py` and downstream feature pipelines, bridge keys with $>1$ occurrence in any annual file are explicitly quarantined (`HAVING COUNT(*) = 1`).
3. **Statistical Impact:** Because only 2 bridge keys (4 rows out of 620,000+, or 0.0006% of the national inventory) exhibit collisions, excluding them preserves 100% data integrity with zero loss of statistical power.
