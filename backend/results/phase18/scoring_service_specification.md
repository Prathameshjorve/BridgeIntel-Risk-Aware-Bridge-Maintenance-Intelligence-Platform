# Phase 18C: Inference Scoring Service Specification & Gate Audit
**Risk-Aware Bridge Maintenance Intelligence Platform**
**Service File:** `backend/score_bridge_risk.py`  
**Test Suite:** `backend/tests/test_score_bridge_risk.py`  
**Regression Fixtures:** `backend/tests/fixtures/regression_test_fixture.json`  
**Gate Decision:** **PASSED** (Ready for downstream decision-support integration)  

---

## 1. Executive Summary & Gate Status

Phase 18C delivers a hardened, inference-only scoring service ([`backend/score_bridge_risk.py`](file:///d:/sem%203/Deep%20Learning/project/backend/score_bridge_risk.py)) that connects the recovered Phase 17 classifier artifact (`HistGradientBoostingClassifier`) with the Phase 18B calibrated Platt scaling estimator (`LogisticRegression`).

### Scoring-Service Quality Gate: PASS
All 14 automated unit and regression tests pass without warnings or regressions.
- **Contract Adherence:** Reusable class `BridgeRiskScorer` and entrypoint `score_bridges()` enforce the canonical 26-feature schema.
- **Leakage & Retraining Prevention:** The service strictly loads pre-trained artifacts once. Importing or calling the module does not trigger training. The held-out test split ($N=65,580$) remains unaccessed.
- **Calibrator Integrity:** Raw logit margins from `classifier.decision_function(X)` are reshaped to `(N, 1)` and passed into `phase18_calibrator.joblib`. Neither raw `predict_proba` nor duplicate base-rate adjustments are applied.
- **Separation of Concerns:** Model deterioration scores are kept strictly isolated from network criticality, detour costs, maintenance costs, and budget optimization logic.

---

## 2. Model Semantics & Explicit Limitations

### 2.1 Model Semantics
The service outputs `calibrated_deterioration_probability`: the estimated 2-year probability that a bridge's deck condition rating on the Federal Highway Administration (FHWA) National Bridge Inventory (NBI) 0–9 ordinal scale will decline by $\ge 1$ point between consecutive biennial inspection cycles:
$$\text{Target} = 1 \iff \text{DECK}_{2025} < \text{DECK}_{2023}$$

### 2.2 Prohibited Interpretations & Disclaimers
1. **No Collapse Prediction:** This probability does **NOT** measure the likelihood of bridge collapse, catastrophic structural failure, or loss of life.
2. **No Structural Safety Certification:** It cannot replace, override, or certify the professional judgment of qualified bridge inspection engineers or state DOT structural authorities.
3. **No Maintenance Efficacy:** The model predicts baseline deterioration trajectory; it does not predict the efficacy or longevity of maintenance interventions.
4. **Validation Scope Disclosure:** Probability calibration was evaluated on an independent 50% partition ($N=32,545$) of the internal validation predictions (`val_predictions.json`). This confirms out-of-sample statistical calibration on the NBI historical dataset, but does **not** represent external temporal deployment validation across unobserved future decades or non-US infrastructure systems.

---

## 3. Input Schema & Preprocessing Contract

The scoring service requires exactly 26 features. Any omitted feature immediately raises `SchemaValidationError`.

### 3.1 Numeric Features (13 Features)
Missing values (`None`, `np.nan`) are preserved as `np.nan` and natively processed by `HistGradientBoostingClassifier` without imputation distortion. Non-numeric values raise `SchemaValidationError`.

| Feature Name | Type | Description |
| :--- | :--- | :--- |
| `prior_deck_condition` | float/int | Baseline NBI deck rating (0–9) |
| `structure_len_mt` | float | Structure length in meters |
| `max_span_len_mt` | float | Maximum span length in meters |
| `deck_width_mt` | float | Out-to-out deck width in meters |
| `traffic_lanes_on` | float/int | Number of traffic lanes on structure |
| `adt` | float | Average daily traffic count |
| `percent_adt_truck` | float | Percentage of average daily traffic that is trucks |
| `detour_kilos` | float | Bypass detour length in kilometers |
| `year_built` | float/int | Year bridge was originally constructed |
| `structure_age_at_inspection` | float | Age of bridge in years at baseline inspection |
| `prior_inspect_month` | float/int | Month of baseline inspection (1–12) |
| `prior_inspect_year` | float/int | Year of baseline inspection |
| `inspect_freq_months` | float/int | Routine inspection interval in months |

### 3.2 Categorical Features (13 Features)
Categorical values are cast to strings. Missing or empty values are filled with `"MISSING"`. Two-digit FHWA codes (e.g. `state_code="01"`, `structure_type_043b="02"`) are normalized with leading zeros. Values are transformed using the saved `cat_encoder.joblib` (`OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)`). Unseen categories map safely to `-1` and generate informative warnings.

| Feature Name | Expected Values | Leading Zero Padding |
| :--- | :--- | :--- |
| `prior_superstructure_condition` | "0"–"9", "N" | No |
| `prior_substructure_condition` | "0"–"9", "N" | No |
| `prior_culvert_condition` | "5"–"8", "N", "n" | No |
| `structure_kind_043a` | "0"–"9" | No |
| `structure_type_043b` | "00"–"22" | **Yes (2 digits)** |
| `deck_structure_type_107` | "1"–"9", "N" | No |
| `surface_type_108a` | "0"–"9", "N" | No |
| `membrane_type_108b` | "0"–"3", "8", "9", "N" | No |
| `deck_protection_108c` | "0"–"4", "6"–"9", "N" | No |
| `functional_class` | "01"–"19" | **Yes (2 digits)** |
| `maintenance_responsibility` | "01"–"80" | **Yes (2 digits)** |
| `owner` | "01"–"80" | **Yes (2 digits)** |
| `state_code` | "01"–"78" | **Yes (2 digits)** |

---

## 4. Inference Formulation & Output Structure

### 4.1 Mathematical Execution Pipeline
1. **Feature Matrix Construction:**
   $$X = [X_{\text{num}}, X_{\text{cat\_enc}}] \in \mathbb{R}^{N \times 26}$$
2. **Raw Score Generation:**
   $$z = \text{classifier.decision\_function}(X)$$
3. **Calibrated Probability Generation:**
   $$\hat{P} = \text{calibrator.predict\_proba}(z.reshape(-1, 1))[:, 1] = \frac{1}{1 + \exp(-(1.10668950 \cdot z - 2.27886141))}$$
4. **Boundary Enforcement:**
   $$\hat{P}_{\text{bounded}} = \max(0.0, \min(1.0, \hat{P}))$$

### 4.2 Output Payload Schema
```json
{
  "bridge_id": "01_000043660-00015",
  "raw_decision_score": -0.35141475380027665,
  "calibrated_deterioration_probability": 0.06490218329419137,
  "prediction_semantics": "Estimated 2-year probability that subsequent NBI deck condition rating drops below baseline rating (routine biennial degradation on NBI 0-9 scale). Does NOT predict bridge collapse, physical structural failure, or maintenance efficacy.",
  "model_metadata": {
    "classifier_type": "HistGradientBoostingClassifier",
    "calibrator_type": "Platt Scaling (LogisticRegression)",
    "target_name": "target_deterioration",
    "features_count": 26,
    "service_phase": "Phase 18C"
  },
  "warnings": []
}
```

---

## 5. Automated Test Suite Execution

The automated test suite (`backend/tests/test_score_bridge_risk.py`) runs natively using Python's standard `unittest` framework.

### Test Execution Command & Results
```powershell
python -m unittest backend/tests/test_score_bridge_risk.py
```
```text
..............
----------------------------------------------------------------------
Ran 14 tests in 3.230s

OK
```

### Test Case Verification Matrix
1. `test_01_import_does_not_train`: Confirmed importing the module does not trigger training or refitting.
2. `test_02_regression_fixture_reproduction`: Confirmed exact reproduction of verified authentic bridge records within $10^{-5}$ tolerance.
3. `test_03_column_order_invariance`: Confirmed reversed and permuted dictionary keys yield identical scores.
4. `test_04_batch_vs_single_record_equivalence`: Confirmed batch inference and single record inference give bitwise identical results.
5. `test_05_dataframe_input_support`: Confirmed pandas DataFrames are supported transparently.
6. `test_06_deterministic_repeated_predictions`: Confirmed 5 consecutive sequential invocations produce identical floats.
7. `test_07_probability_bounds_and_calibrator_composition`: Confirmed probability strictly bounded in $[0, 1]$ and matches Platt logistic formula.
8. `test_08_missing_numeric_values_handling`: Confirmed `None` and `np.nan` in numeric fields are handled natively by HistGradientBoosting.
9. `test_09_missing_and_unknown_categorical_values`: Confirmed missing categoricals are filled with `"MISSING"` and unknown codes produce actionable warnings while encoding as `-1`.
10. `test_10_missing_required_column_fails`: Confirmed omitting features raises `SchemaValidationError` with the missing column names.
11. `test_11_wrong_data_type_fails`: Confirmed strings in numeric columns fail safely with `SchemaValidationError`.
12. `test_12_non_dict_record_fails`: Confirmed malformed non-dict records fail safely with `SchemaValidationError`.
13. `test_13_artifact_load_failure`: Confirmed non-existent directory raises `ArtifactLoadError`.
14. `test_14_functional_entrypoint`: Confirmed top-level `score_bridges()` handles single dicts and batch lists seamlessly.

---

## 6. Artifact Cryptographic Provenance

All artifacts consumed by the scoring service were verified against their SHA-256 hashes:

| Artifact | Location | Size (Bytes) | SHA-256 Checksum |
| :--- | :--- | :--- | :--- |
| Classifier | `backend/results/phase17/hist_gradient_boosting_classifier.joblib` | 176,794 | `e2b4e2ec334c18b343a55b1bc26395b3684f76678cfa80d4ccc9edf588b6da0b` |
| Encoder | `backend/results/phase17/cat_encoder.joblib` | 1,098 | `14fe2087570446889226640ebb8508e7e832be9b2241c9f92407f9a3f10c6772` |
| Metadata | `backend/results/phase17/inference_metadata.json` | 6,340 | `b48922c28ee102d65f5af55fd6be446586bcc358e564e652455f8c1b8bedea24` |
| Calibrator | `backend/results/phase18/calibration/phase18_calibrator.joblib` | 879 | `7fb7915aefc952c87a17b347004bd2f3f6061f1ad9172e3a9f6f41e2732cfbd3` |
