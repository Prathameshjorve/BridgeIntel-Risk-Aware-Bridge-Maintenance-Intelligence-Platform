# FHWA NBI Data Audit & Longitudinal Engineering Pipeline

This directory contains data audit and longitudinal analysis scripts for the **Risk-Aware Bridge Maintenance Intelligence Platform**.

## 1. Directory Structure

```text
backend/
├── 2023/                                      # Authentic FHWA NBI 2023 Dataset (255 MB)
│   └── 2023HwyBridgesDelimitedAllStates.txt
├── 2024/                                      # Authentic FHWA NBI 2024 Dataset (255 MB)
│   └── 2024HwyBridgesDelimitedAllStates.txt
├── 2025/                                      # Authentic FHWA NBI 2025 Dataset (256 MB)
│   └── 2025HwyBridgesDelimitedAllStates.txt
├── audit_nbi_records.py                       # Single-year record & schema audit script
├── compare_nbi_years.py                       # Longitudinal cross-year comparison script
├── build_modeling_dataset.py                  # Phase 16: Leakage-resistant modeling dataset pipeline
├── train_condition_models.py                  # Phase 17: Baseline & deterioration model evaluation
├── data/
│   └── processed/                             # Processed longitudinal modeling data
│       ├── bridge_deck_condition_2023_2025.csv # Primary modeling dataset (435,210 pairs)
│       ├── modeling_dataset_manifest.json     # Machine-readable schema, splits & accounting
│       └── modeling_dataset_report.md         # Comprehensive engineering report
├── results/
│   └── phase17/                               # Phase 17 Model Evaluation Artifacts
│       ├── model_comparison_report.md         # Comprehensive research & benchmark report
│       ├── model_metrics.json                 # Machine-readable evaluation metrics (JSON)
│       ├── confusion_matrices.json            # Task 1 & Task 2 confusion matrices (JSON)
│       └── feature_importances.json           # Permutation feature importances (JSON)
├── reports/
│   └── nbi_audit/                             # Audit reports and machine-readable data
│       ├── nbi_audit_summary.json             # Comprehensive schema and record stats (JSON)
│       ├── nbi_record_audit_report.md         # Full record-level audit narrative (MD)
│       ├── nbi_inspection_date_audit.md       # Item 90 date interpretation & NBIS cycles (MD)
│       ├── nbi_duplicate_malformed_report.md  # Detailed duplicate ID & line 459987 report (MD)
│       ├── nbi_cross_year_comparison.json     # Longitudinal matching & transition metrics (JSON)
│       ├── nbi_cross_year_report.md           # Cross-year inventory change narrative (MD)
│       ├── nbi_condition_transition_summary.md# 10x10 condition transition matrices (MD)
│       └── feature_target_specification.md    # Leakage prevention & feature definitions (MD)
└── README.md                                  # Execution guide (this file)
```

---

## 2. Running the Data & Modeling Pipelines

All scripts execute reproducibly on Windows with memory-efficient streaming:

```powershell
# From the project root or backend directory:
cd "D:\sem 3\Deep Learning\project\backend"

# 1. Run the Record-Level Schema & Field Audit
python audit_nbi_records.py

# 2. Run the Longitudinal Cross-Year Comparison & Transition Matrix Analysis
python compare_nbi_years.py

# 3. Generate the Leakage-Resistant 2023->2025 Modeling Dataset (Phase 16)
python build_modeling_dataset.py

# 4. Train & Evaluate Condition & Deterioration Models (Phase 17)
python train_condition_models.py
```

---

## 3. Interpreting Script Outputs

### `audit_nbi_records.py`
- Confirms file presence, exact sizes, row counts, and encoding (`utf-8-sig`).
- Validates that all 3 files share identical 123 columns in identical order.
- Confirms that exactly 1 row in 2024 (Line 459,987) has 124 fields due to an unquoted delimiter and quarantines it.
- Confirms exactly 2 duplicate identifier groups (4 records per release) across all 3 years.
- Verifies that `LOWEST_RATING` and `BRIDGE_CONDITION` have 0 mismatches with raw component ratings.

### `compare_nbi_years.py`
- Matches bridge IDs `(STATE_CODE_001, STRUCTURE_NUMBER_008)` across 2023→2024, 2024→2025, and 2023→2025.
- Demonstrates that 1-year snapshots update inspection dates for ~50.6% of bridges, while the 2-year interval updates ~93.6% (reflecting the biennial inspection cycle).
- Computes complete 0–9 deck condition transition matrices.
- Analyzes deterioration rates (8.29% degrade over 2 years, 4.12% improve via maintenance, 87.60% remain unchanged).

### `build_modeling_dataset.py` (Phase 16)
- Links 2023 earlier baseline to 2025 later target observation on `(STATE_CODE_001, STRUCTURE_NUMBER_008)`.
- Enforces strict chronological filtering ($\Delta \text{months} > 0$), eliminating uninspected carryovers (26,694 pairs).
- Produces `bridge_deck_condition_2023_2025.csv` (435,210 verified rows, 35 columns).
- Computes deterministic SHA-256 bridge-grouped splits: Train 70% (304,541), Val 15% (65,089), Test 15% (65,580) with zero ID overlap.
- Establishes descriptive persistence baseline reference: 86.80% exact match accuracy, 0.1625 MAE, 0.00% deterioration recall.

### `train_condition_models.py` (Phase 17)
- Evaluates Task 1 (Future Deck Condition Rating) and Task 2 (Binary Deterioration Event Detection).
- Task 1: Confirms persistence baseline exact accuracy (86.80%) and Ordinal MAE (0.1625); HistGradientBoosting achieves lowest continuous RMSE (0.4963).
- Task 2: Demonstrates active deterioration detection on unseen test bridges: HistGradientBoosting achieves PR-AUC 0.2943 (3.30x lift over 0.0891 base rate), ROC-AUC 0.7625, and identifies 2,127 deteriorating structures (36.40% recall) with 30.38% precision at validation-selected threshold ($\tau = 0.680$).
