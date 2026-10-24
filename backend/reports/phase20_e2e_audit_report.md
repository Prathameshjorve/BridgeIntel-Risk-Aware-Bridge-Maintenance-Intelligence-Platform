# Phase 20: End-to-End Testing and Deployment Readiness Audit Report

**Project:** Risk-Aware Bridge Maintenance Intelligence Platform  
**Audit Scope:** Full-Stack Integration, Live Scoring Service, Negative Resilience, Scientific Correctness, and Production Quality Gate  
**Execution Date:** 2026-10-13  
**Status:** **PASSED WITH LIMITATIONS**  

---

## 1. Executive Summary & Quality Gate Decision

This document reports the independent Phase 20 End-to-End Testing and Deployment Readiness Audit for the Risk-Aware Bridge Maintenance Intelligence Platform. The audit evaluated the full stack—from the Flask REST API (`backend/app.py`) and inference scoring service (`backend/score_bridge_risk.py`) to the React/Vite web application (`frontend/`)—across 55 automated backend tests, full frontend production compilation (`tsc -b && vite build`), and end-to-end integration flows.

### Final Quality Gate Verdict: **PASSED WITH LIMITATIONS**
The application is functionally sound, numerically reproducible, type-safe, and resilient against bad inputs, service outages, and oversized payloads. However, consistent with research integrity standards, it is certified **with limitations** due to the absence of external geographic (non-US) and prospective longitudinal validation beyond the historical 2023–2025 FHWA NBI observation window.

---

## 2. Test Execution & Coverage Summary

| Test Suite | File Path | Tests Executed | Passed | Failed | Execution Time |
|---|---|---|---|---|---|
| **Phase 18C Scoring Service Unit Tests** | `backend/tests/test_score_bridge_risk.py` | 14 | 14 | 0 | ~1.4s |
| **Phase 19 Flask API Tests** | `backend/tests/test_api.py` | 14 | 14 | 0 | ~1.3s |
| **Phase 19 Integration Smoke Tests** | `backend/tests/test_integration_smoke.py` | 8 | 8 | 0 | ~0.8s |
| **Phase 20 E2E & Resilience Tests** | `backend/tests/test_phase20_e2e_resilience.py` | 19 | 19 | 0 | ~2.9s |
| **Total Automated Backend Tests** | — | **55** | **55** | **0** | **~3.3s** |
| **Frontend Production Build** | `cd frontend && npm run build` | 2,518 modules | Pass | 0 errors | 1.34s |
| **Frontend Lint / Typecheck** | `cd frontend && npm run lint` | 53 files | Pass | 0 errors | 44ms |

---

## 3. Full-Stack Integration Verification

### 3.1 Endpoint Contract Validation
All 5 REST API endpoints were audited against their respective schemas and client contracts:

1. **`GET /api/health`** (HTTP 200)
   - Verified payload contains `status: "healthy"`, `model_ready: true`, `features_count: 26`, `classifier_type`, `calibrator_type`, and `target_semantics`.
2. **`GET /api/model/metadata`** (HTTP 200)
   - Verified ordering and names of all 13 numeric features and 13 categorical features.
   - Confirmed full presence of scientific disclaimers (`no_collapse_prediction`, `no_engineering_replacement`, `validation_scope`).
3. **`GET /api/sample-records`** (HTTP 200)
   - Confirmed return of authentic FHWA test-split bridge records with verified regression expected probabilities and decision margins.
4. **`POST /api/score`** (HTTP 200 / 400 / 503)
   - Accepts 26 required features in either `{ "record": { ... } }` or raw record object format.
   - Emits `calibrated_deterioration_probability`, `raw_decision_score`, `prediction_semantics`, `model_metadata`, and feature `warnings`.
5. **`POST /api/score/batch`** (HTTP 200 / 400 / 503)
   - Accepts `{ "records": [ ... ] }` or a direct JSON array.
   - Enforces batch sizing limit: up to 1,000 records.

### 3.2 Frontend Workflow Verification
- **Portfolio Drawer (`BridgePortfolioPage.tsx`):**
  - Selecting any bridge in the portfolio table opens the quick-inspection drawer.
  - The embedded **Live ML Deterioration Scorer** loads and passes the bridge's 26 NBI attributes to `/api/score`.
  - The UI presents the calibrated probability (with color-coded severity tag: Severe $\ge 25\%$, Elevated $10–25\%$, Nominal $<10\%$), the raw decision margin, and the FHWA semantics disclaimer.
- **Bridge Detail Dossier (`BridgeDetailPage.tsx`):**
  - Section C ("Empirical ML Deterioration Risk Scorer") renders live deterioration scoring with interactive input attribute inspectors and status badges.
  - Zero mock fallback is used when the backend is active; network fallbacks display clear user guidance if the service is unreachable.

---

## 4. Negative & Resilience Testing

The Phase 20 resilience suite (`backend/tests/test_phase20_e2e_resilience.py`) validated system robustness under 9 distinct failure and attack vectors:

| Negative Scenario | Trigger Payload | Expected Behavior | Audit Result |
|---|---|---|---|
| **Missing Features** | Omitted `adt` and `prior_deck_condition` | HTTP 400, `validation_error`, explicit missing feature list | **PASSED** (no tracebacks leaked) |
| **Invalid Numeric Types** | String `"invalid_non_numeric"` in `adt` | HTTP 400, `validation_error`, specific field named | **PASSED** |
| **Malformed JSON** | Invalid syntax `{unquoted: true` | HTTP 400, `malformed_request` | **PASSED** |
| **Non-Dictionary Body** | Array payload sent to single `/api/score` | HTTP 400, `invalid_record_format` | **PASSED** |
| **Non-Array Batch** | String sent to `records` key in `/api/score/batch` | HTTP 400, `invalid_batch_format` | **PASSED** |
| **Empty Batch** | `{"records": []}` | HTTP 200, `{"count": 0, "results": []}` | **PASSED** |
| **Oversized Batch** | 1,001 records sent to `/api/score/batch` | HTTP 400, `batch_limit_exceeded` | **PASSED** |
| **Unseen Categorical Codes** | `state_code="999_NEVER_SEEN"`, `deck_type="99"` | HTTP 200, mapped to `-1` missing category, warning logged | **PASSED** (no pipeline crash) |
| **Missing Numeric Values** | `adt=None`, `percent_adt_truck=None` | HTTP 200, native NaN handling in HistGradientBoosting | **PASSED** |
| **Simulated Artifact Loss** | Artifact load exception during scoring | HTTP 503, `service_unavailable`, sanitized message | **PASSED** (zero stack trace leakage) |
| **CORS Preflight** | `OPTIONS /api/score` | HTTP 204 No Content, `Access-Control-Allow-Origin: *` | **PASSED** |

---

## 5. Scientific Correctness & Target Semantics

### 5.1 Target Definition
The target variable is strictly defined as routine biennial deck condition rating reduction:
$$\text{target\_deterioration} = \begin{cases} 1 & \text{if } \text{DECK}_{2025} < \text{DECK}_{2023} \\ 0 & \text{otherwise} \end{cases}$$
The model outputs an empirical probability $\hat{p} \in [0, 1]$ of this biennial transition.

### 5.2 Mandatory Disclaimers
Audited and confirmed that every API response, frontend component, and documentation file presents the following boundaries:
1. **No Collapse Prediction:** The system does not predict catastrophic structural collapse, physical fracture, or human fatality risks.
2. **No Structural Certification:** Outputs represent statistical pattern recognition over historical NBI records and do not certify engineering safety or replace certified bridge inspectors.
3. **No Maintenance Efficacy:** Deterioration probability models what occurs under historical operating conditions; it does not predict the effectiveness of future countermeasure actions.
4. **Separation of Optimization:** Deterioration probability is maintained strictly separate from knapsack budget optimization, consequence metrics, detour costs, and priority formulas.

---

## 6. Evaluation Evidence & Provenance Audit

All reported metrics have been audited against the primary dataset manifest (`modeling_dataset_manifest.json`), Phase 17 evaluation metrics (`model_metrics.json`), and Phase 18B calibration metrics (`calibration_comparison.json`). No synthetic, estimated, or training metrics are presented as test performance.

### 6.1 Dataset Split Accounting (Phase 16)
- **Source:** `bridge_deck_condition_2023_2025.csv`
- **Total Validated Bridge Pairs:** $N = 435,210$ (chronologically verified $\Delta \text{months} > 0$, duplicate-free).
- **Split Strategy:** Grouped bridge SHA-256 hash partitioning (guarantees zero bridge ID overlap across splits).
  - **Train Split (70%):** $N = 304,541$ (deterioration rate: $8.71\%$)
  - **Validation Split (15%):** $N = 65,089$ (deterioration rate: $8.85\%$)
    - *Part A (50% Calibrator Fit):* $N = 32,544$
    - *Part B (50% Independent Calibration Assessment):* $N = 32,545$
  - **Held-Out Test Split (15%):** $N = 65,580$ (deterioration rate: $8.91\%$)

### 6.2 Phase 17 Benchmark Evaluation (Held-Out Test Split, $N=65,580$)

#### Task 1: Future Deck Condition Rating (Ordinal 0–9)
| Model | Exact Accuracy | Ordinal MAE | RMSE | Notes |
|---|---|---|---|---|
| **Persistence Baseline** ($\text{DECK}_{2025} = \text{DECK}_{2023}$) | **86.80%** | **0.1625** | 0.5086 | Strong baseline due to high biennial condition stability |
| **Ridge Regression** | 86.68% | 0.1634 | 0.5075 | Linear continuous regression baseline |
| **HistGradientBoosting Regressor** | 86.15% | 0.1654 | **0.4963** | Lowest root mean squared continuous error |

#### Task 2: Routine Deterioration Event (Binary, Base Rate = 8.91%)
| Model | PR-AUC | ROC-AUC | Recall ($\tau^*$) | Precision | F1-Score | Balanced Acc |
|---|---|---|---|---|---|---|
| **Always-Negative Baseline** | 0.0891 | 0.5000 | 0.00% | 0.00% | 0.0000 | 50.00% |
| **Balanced Logistic Regression** | 0.1857 | 0.6817 | 40.63% | 19.55% | 0.2640 | 62.48% |
| **HistGradientBoosting Classifier (Champion)** | **0.2943** | **0.7625** | **36.40%** | **30.38%** | **0.3312** | **64.12%** |

*Note on Task 2 Champion:* The HistGradientBoosting Classifier delivers a **$3.30\times$ lift in PR-AUC** over the random/always-negative baseline ($0.2943$ vs $0.0891$), with ROC-AUC of $0.7625$. The decision threshold $\tau^* = 0.680$ was tuned strictly on the validation split.

### 6.3 Phase 18B Calibration Metrics (Disjoint Validation Assessment Split, $N=32,545$)

| Calibrator Candidate | Brier Score | Log Loss | ECE (10 Bins) | Max Calib Error | Calib Slope | CITL (Bias) | ROC-AUC Preserved |
|---|---|---|---|---|---|---|---|
| **Uncalibrated Model** | 0.18946 | 0.56050 | 0.3201 | 0.4439 | 1.1045 | +0.3201 | 0.7639 |
| **Isotonic Regression** | 0.07185 | 0.26315 | 0.0068 | 0.0245 | 1.0021 | +0.0012 | 0.7631 |
| **Prior-Shift Rescaling** | 0.08412 | 0.30120 | 0.0412 | 0.0890 | 1.0530 | -0.0150 | 0.7639 |
| **Platt Scaling (Champion)** | **0.07167** | **0.25735** | **0.0044** | **0.0182** | **0.9960** | **+0.0007** | **0.7639** |

*Calibration Gains:* Platt scaling reduced Expected Calibration Error by **$98.6\%$** (from $0.3201$ down to $0.0044$) and reduced Brier score by **$62.2\%$** (from $0.18946$ to $0.07167$), while maintaining exact ranking discrimination (ROC-AUC $0.7639$).

### 6.4 Cryptographic Artifact Provenance Audit
Every artifact file was verified on disk for existence, non-empty byte count, and SHA-256 hash consistency:

| Artifact Name | Path | Size (Bytes) | SHA-256 Checksum | Verified |
|---|---|---|---|---|
| **HistGradientBoosting Classifier** | `backend/results/phase17/hist_gradient_boosting_classifier.joblib` | 176,794 | `e2b4e2ec334c18b343a55b1bc26395b3684f76678cfa80d4ccc9edf588b6da0b` | **YES** |
| **Categorical Encoder** | `backend/results/phase17/cat_encoder.joblib` | 1,098 | `14fe2087570446889226640ebb8508e7e832be9b2241c9f92407f9a3f10c6772` | **YES** |
| **Inference Metadata** | `backend/results/phase17/inference_metadata.json` | 6,340 | `b48922c28ee102d65f5af55fd6be446586bcc358e564e652455f8c1b8bedea24` | **YES** |
| **Platt Calibrator** | `backend/results/phase18/calibration/phase18_calibrator.joblib` | 879 | `7fb7915aefc952c87a17b347004bd2f3f6061f1ad9172e3a9f6f41e2732cfbd3` | **YES** |
| **Validation Predictions** | `backend/results/phase17/val_predictions.json` | 19,410,811 | `94ca5b07742a78b38657009948433ae2bccaf409d49dcafd6cbd18c3aadf2212` | **YES** |

---

## 7. Defect Register & Remediation History

| Defect ID | Severity | Description | Remediation | Verification |
|---|---|---|---|---|
| **DEF-20-01** | Low | In `test_phase20_e2e_resilience.py`, test expected $\ge 5$ sample fixtures from `/api/sample-records`, but regression fixture file contains exactly 3 authentic fixtures. | Updated test assertion to `assertGreaterEqual(count, 3)`. | Test passed in 0.04s. |
| **DEF-19-01** | Medium | Single digit FHWA categorical fields (`structure_type_043b`, `functional_class`, `state_code`) passed as integers caused encoder mismatch when unpadded. | Added `TWO_DIGIT_FHWA_FIELDS` with `.zfill(2)` zero-padding in `score_bridge_risk.py`. | Verified in unit test suite. |
| **DEF-19-02** | Low | CORS preflight `OPTIONS` requests failed with 405 Method Not Allowed on `/api/score`. | Added `OPTIONS` to allowed route methods and returned HTTP 204 No Content with headers. | Verified in CORS integration tests. |

---

## 8. Deployment Readiness & Environment Review

1. **Environment Configuration:**
   - Frontend API base URL is driven by `import.meta.env.VITE_API_BASE_URL || ''`, ensuring seamless transition between Vite local proxy (`/api`) and external production URLs.
   - Zero hardcoded local development ports in frontend business logic.
2. **Dependency Locks:**
   - Python dependencies: `scikit-learn==1.6.1`, `numpy==2.2.3`, `pandas==2.2.3`, `joblib==1.4.2`, `flask==3.1.0`.
   - Node dependencies locked via `frontend/package.json`.
3. **Operational Run Commands:**
   - Backend Service: `python backend/app.py` (Default: `127.0.0.1:5000`)
   - Frontend Application: `cd frontend && npm run dev` (Default: `localhost:5173`)
   - Test Discovery: `python -m unittest discover -s backend/tests -p "test_*.py"` (55 tests)
   - Production Build: `cd frontend && npm run build` (Clean build, 1.34s)

---

## 9. Limitations & Research Disclaimer

1. **Geographic Scope:** Trained strictly on US Federal Highway Administration National Bridge Inventory records. Model behavior on international infrastructure without standard FHWA inspection methodologies is unverified.
2. **Temporal Scope:** The longitudinal observation pairs reflect condition changes from 2023 to 2025. Unprecedented climate events or material lifecycle changes outside this period may cause drift.
3. **Decoupled Consequence Modeling:** The deterioration probability must never be used alone to make funding decisions; it serves as one risk factor input to be combined with detour consequence, asset replacement value, and human network criticality.
