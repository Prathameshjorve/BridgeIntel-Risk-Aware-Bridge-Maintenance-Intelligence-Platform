# Phase 21B: Hyperparameter Tuning, Regularization & Validation Report

**Project:** Risk-Aware Bridge Maintenance Intelligence Platform  
**Target:** Binary Bridge Deck Rating Deterioration ($\text{target\_deterioration} = 1 \text{ if } \text{DECK}_{2025} < \text{DECK}_{2023}$)  
**Execution Date:** 2026-10-14  
**Quality Gate Verdict:** **IMPROVEMENT ESTABLISHED**  

---

## 1. Executive Summary & Predeclared Quality Gate

Phase 21B conducted a systematic, leakage-resistant hyperparameter tuning and regularization search for the bridge deck deterioration model using strictly isolated **5-fold Stratified Cross-Validation inside the training partition ($N = 304,541$)**. 

### Key Findings & Achievements:
1. **Unweighted Loss Superiority over Balanced Reweighting:**
   Across all 60 cross-validation model fits, unweighted native loss models consistently outperformed balanced loss models. While balanced class weighting artificially inflates raw probabilities (necessitating high thresholds like $\tau = 0.680$), the native unweighted loss paired with higher capacity (`max_leaf_nodes=63`) and L2 regularization (`l2=1.0`) discovers cleaner gradient paths and preserves continuous ranking discrimination.
2. **Winning Architecture:** `C10_unweighted_conservative`
   - Hyperparameters: `learning_rate=0.05`, `max_iter=200`, `max_leaf_nodes=63`, `min_samples_leaf=60`, `l2_regularization=1.0`, `class_weight=None`.
   - 5-Fold Cross-Validation PR-AUC: **$0.3096 \pm 0.0076$** (a $+0.0202$ lift over Phase 20 Champion and $+0.0111$ lift over Phase 21 Candidate).
   - 5-Fold Cross-Validation ROC-AUC: **$0.7718 \pm 0.0041$**.
3. **Cross-Fitted Out-of-Sample Calibration:**
   Platt scaling cross-fitted across the 5 folds on training out-of-fold decision margins reduced Expected Calibration Error (ECE) to **$0.0006$** (an $84.7\%$ reduction) and Brier score to **$0.07001$**, with near-zero calibration-in-the-large bias ($\text{CITL} = +0.0000$).
4. **Out-of-Fold Threshold Selection:**
   Derived strictly from training out-of-fold predictions using a Max F1 objective across 181 candidate thresholds: $\tau^* = 0.165$ (Out-of-fold Precision: $29.22\%$, Recall: $41.04\%$, F1: $0.3413$, Balanced Accuracy: $65.78\%$).
5. **Audit Comparison on Held-Out Test Partition ($N = 65,580$):**
   - Test PR-AUC: **$0.3147$** (vs Phase 20 Champion $0.2943$ and Phase 21 Candidate $0.3043$).
   - Test Recall: **$41.83\%$** (vs Phase 20 Champion $36.40\%$ — an absolute gain of $+5.43\%$ in detecting deteriorating structures).
   - Test F1-Score: **$0.3488$** (vs Phase 20 Champion $0.3312$).
   - Test Balanced Accuracy: **$66.12\%$** (vs Phase 20 Champion $64.12\%$).
6. **Artifact Isolation & Zero Production Impact:**
   All Phase 20 and Phase 21 artifacts remain permanently frozen and unmutated. All Phase 21B artifacts are stored in `backend/results/phase21b/`.

---

## 2. Pre-Experiment Verification & Frozen Artifact Audit

Prior to executing any experimental runs, all existing model artifacts were inspected on disk and their SHA-256 cryptographic hashes verified:

| Artifact Name | Relative Path | Verified SHA-256 Checksum | Size | Status |
|---|---|---|---|---|
| **Phase 20 Champion Classifier** | `backend/results/phase17/hist_gradient_boosting_classifier.joblib` | `e2b4e2ec334c18b343a55b1bc26395b3684f76678cfa80d4ccc9edf588b6da0b` | 176,794 B | **IMMUTABLE** |
| **Phase 20 Categorical Encoder** | `backend/results/phase17/cat_encoder.joblib` | `14fe2087570446889226640ebb8508e7e832be9b2241c9f92407f9a3f10c6772` | 1,098 B | **IMMUTABLE** |
| **Phase 20 Metadata** | `backend/results/phase17/inference_metadata.json` | `b48922c28ee102d65f5af55fd6be446586bcc358e564e652455f8c1b8bedea24` | 6,340 B | **IMMUTABLE** |
| **Phase 20 Platt Calibrator** | `backend/results/phase18/calibration/phase18_calibrator.joblib` | `7fb7915aefc952c87a17b347004bd2f3f6061f1ad9172e3a9f6f41e2732cfbd3` | 879 B | **IMMUTABLE** |
| **Phase 21 Candidate Model** | `backend/results/phase21/candidate_2_deep_interactions.joblib` | `210bf46945d6e91c5e7968eb5e96038d38682de3e492a1cba6caffe15a017fde` | 277,419 B | **IMMUTABLE** |
| **Phase 21 Candidate Calibrator** | `backend/results/phase21/candidate_2_deep_interactions_calibrator.joblib` | `103468868d2f4a2e01895127af07549fe868414d89432507af9981eaa6f8eb1c` | 879 B | **IMMUTABLE** |
| **Phase 21 Candidate Encoder** | `backend/results/phase21/phase21_encoder.joblib` | `14fe2087570446889226640ebb8508e7e832be9b2241c9f92407f9a3f10c6772` | 1,098 B | **IMMUTABLE** |

---

## 3. Validation Design & Leakage Audit

### 3.1 Unique-ID Verification & Fold Strategy
- **Dataset Source:** `bridge_deck_condition_2023_2025.csv` ($N = 435,210$ records).
- **Training Partition:** $N = 304,541$ rows ($69.98\%$).
- **Unique Bridge Identifiers in Train:** Exactly $304,541$ ($100\%$ unique 1-to-1 pairs with zero duplicate structures).
- **Rationale for StratifiedKFold:** Because each row represents a strictly unique bridge pair without repeated longitudinal observations per structure, `StratifiedKFold(n_splits=5, shuffle=True, random_state=42)` guarantees an identical $8.71\%$ class prevalence across all 5 folds without bridge identity overlap or group-leakage risks.

### 3.2 Strict In-Fold Preprocessing & Early Stopping Safeguards
1. **In-Fold Encoder Fitting:** `OrdinalEncoder(handle_unknown='use_encoded_value', unknown_value=-1)` was fitted **strictly on each fold's 80% training subset** ($\approx 243,632$ records) and applied to the 20% validation fold ($\approx 60,909$ records). Zero categorical distribution leakage occurred.
2. **Early Stopping Holdout:** For all models, early stopping (`validation_fraction=0.1`, `n_iter_no_change=10`) was configured inside `HistGradientBoostingClassifier`. Scikit-learn internally carved a 10% validation holdout **strictly from that fold's 80% training subset**, completely isolated from the outer 20% validation fold.
3. **Partition Boundary Isolation:** The existing validation ($N = 65,089$) and test ($N = 65,580$) sets were completely excluded from hyperparameter tuning, model ranking, threshold determination, and calibration fitting.

---

## 4. Bounded Hyperparameter Search & 5-Fold Cross-Validation Results

A focused, staged grid of 12 candidate architectures was evaluated across 5 folds (60 total model fits).

### 4.1 Cross-Validation Metric Summary Table (Ranked by 5-Fold Mean PR-AUC)

| Rank | Config ID | Architecture Hypothesis | Hyperparameters (`lr`, `iter`, `leaves`, `min_leaf`, `l2`, `weights`) | Mean 5-Fold PR-AUC | Mean 5-Fold ROC-AUC | Pooled OOF PR-AUC | Avg Iterations | Runtime (5 Folds) |
|---|---|---|---|---|---|---|---|---|
| **1** | **`C10_unweighted_conservative`** | **Unweighted Conservative (Winning Model)** | `lr=0.05, iter=200, leaves=63, min_leaf=60, l2=1.0, None` | **0.3096 ± 0.0076** | **0.7718 ± 0.0041** | **0.3093** | 200.0 | 28.69s |
| 2 | `C9_unweighted_p21` | Unweighted Native Baseline | `lr=0.08, iter=150, leaves=63, min_leaf=40, l2=0.5, None` | 0.3091 ± 0.0067 | 0.7708 ± 0.0038 | 0.3088 | 150.0 | 21.37s |
| 3 | `C11_heavy_reg_stress` | Extreme Regularization Stress-Test | `lr=0.08, iter=150, leaves=63, min_leaf=100, l2=10.0, balanced` | 0.2998 ± 0.0083 | 0.7711 ± 0.0045 | 0.2996 | 138.2 | 21.98s |
| 4 | `C3_deep_heavy_l2` | High Capacity + Heavy L2 | `lr=0.08, iter=200, leaves=63, min_leaf=40, l2=5.0, balanced` | 0.2995 ± 0.0084 | 0.7707 ± 0.0045 | 0.2993 | 148.6 | 23.47s |
| 5 | `C1_p21_candidate` | Phase 21 Candidate Architecture | `lr=0.08, iter=150, leaves=63, min_leaf=40, l2=0.5, balanced` | 0.2985 ± 0.0075 | 0.7692 ± 0.0039 | 0.2982 | 133.0 | 20.61s |
| 6 | `C2_deep_mod_l2` | Higher Capacity + Moderate L2 | `lr=0.08, iter=200, leaves=63, min_leaf=60, l2=1.0, balanced` | 0.2979 ± 0.0067 | 0.7696 ± 0.0044 | 0.2974 | 148.2 | 23.70s |
| 7 | `C6_slow_deep` | Slow Conservative Learning | `lr=0.03, iter=300, leaves=63, min_leaf=40, l2=0.5, balanced` | 0.2974 ± 0.0077 | 0.7700 ± 0.0042 | 0.2970 | 231.4 | 36.19s |
| 8 | `C5_mod_capacity_high_support` | Moderate Capacity + High Support | `lr=0.05, iter=200, leaves=31, min_leaf=100, l2=1.0, balanced` | 0.2907 ± 0.0069 | 0.7653 ± 0.0037 | 0.2904 | 141.0 | 17.58s |
| 9 | `C4_mod_capacity_fine_l2` | Moderate Capacity + Fine L2 | `lr=0.05, iter=200, leaves=31, min_leaf=40, l2=0.5, balanced` | 0.2901 ± 0.0071 | 0.7650 ± 0.0039 | 0.2898 | 138.8 | 17.38s |
| 10| `C7_slow_compact` | Slow Conservative + Compact | `lr=0.03, iter=300, leaves=31, min_leaf=60, l2=1.0, balanced` | 0.2895 ± 0.0071 | 0.7648 ± 0.0040 | 0.2891 | 215.8 | 26.79s |
| 11| `C0_p20_champion` | Phase 20 Champion Baseline | `lr=0.10, iter=100, leaves=31, min_leaf=20, l2=0.0, balanced` | 0.2894 ± 0.0073 | 0.7642 ± 0.0037 | 0.2890 | 100.0 | 13.06s |
| 12| `C8_shallow_ensemble` | Shallow Low Complexity | `lr=0.10, iter=150, leaves=15, min_leaf=40, l2=0.1, balanced` | 0.2844 ± 0.0070 | 0.7606 ± 0.0040 | 0.2840 | 114.2 | 11.23s |

### 4.2 Regularization & Architectural Analysis
1. **Impact of Loss Weighting:** Both unweighted configurations (`C10` and `C9`) occupied ranks 1 and 2, achieving $+0.010$ to $+0.020$ higher cross-validated PR-AUC than balanced configurations.
2. **Impact of Tree Capacity (`max_leaf_nodes`):** Increasing leaf nodes from 31 to 63 yielded consistent improvements across all learning rates ($+0.008$ to $+0.010$ PR-AUC), confirming that higher capacity allows the trees to resolve non-linear geographic and structural interaction terms.
3. **Impact of L2 Regularization & Leaf Support:** Combining `max_leaf_nodes=63` with `min_samples_leaf=60` and `l2_regularization=1.0` prevented the deep trees from overfitting rare structural types, producing the highest stability across folds.

---

## 5. Threshold Selection & Cross-Fitted Calibration

### 5.1 Training Out-of-Fold Threshold Selection
The decision threshold was derived strictly from the $304,541$ out-of-fold training predictions across 181 candidate thresholds ($0.05 \le \tau \le 0.95$):
- **Documented Objective:** Maximum F1 score.
- **Derived Operational Threshold:** **$\tau^* = 0.165$** (reflecting native unweighted event prevalence).
- **Out-of-Fold Metrics at $\tau^* = 0.165$:**
  - Precision: **$29.22\%$** | Recall: **$41.04\%$** | F1-Score: **$0.3413$**
  - Binary Accuracy: **$86.20\%$** | Balanced Accuracy: **$65.78\%$** | Specificity: **$90.51\%$**
  - Confusion Matrix: $\text{TN} = 251,629, \; \text{FP} = 26,382, \; \text{FN} = 15,641, \; \text{TP} = 10,889$

### 5.2 Cross-Fitted Out-of-Sample Platt Calibration
To eliminate calibration leakage, Platt scaling was cross-fitted across the 5 folds: for each fold $k$, Platt `LogisticRegression` was fitted on the raw decision scores of the other 4 folds and evaluated on fold $k$.

| Calibration Metric | Uncalibrated Model | Cross-Fitted Platt Calibrator |
|---|---|---|
| **Brier Score** | 0.07006 | **0.07001** |
| **Log Loss** | 0.25202 | **0.25181** |
| **Expected Calibration Error (ECE)** | 0.0042 | **0.0006** ($84.7\%$ reduction) |
| **Maximum Calibration Error (MCE)**| 0.0476 | **0.0157** |
| **Calibration Slope** | 1.0945 | **1.0823** |
| **Calibration-in-the-Large (CITL)** | +0.0004 | **+0.0000** (Zero bias) |

---

## 6. State Subgroup Analysis (Top 5 State DOT Portfolios)

Subgroup performance was evaluated on out-of-fold training predictions across the 5 largest state portfolios:

| State | Total Bridges | Positive Events | Event Prevalence | PR-AUC | ROC-AUC | F1 ($\tau^* = 0.165$) | Precision | Recall |
|---|---|---|---|---|---|---|---|---|
| **Texas (48)** | 22,499 | 1,504 | 6.68% | **0.3829** | **0.8121** | **0.4129** | 38.62% | 44.35% |
| **Ohio (39)** | 16,914 | 1,735 | 10.26% | **0.2718** | **0.6988** | **0.2892** | 27.64% | 30.32% |
| **California (06)** | 13,986 | 895 | 6.40% | **0.2124** | **0.7677** | **0.2371** | 27.60% | 20.78% |
| **Missouri (29)** | 12,877 | 1,269 | 9.85% | **0.3155** | **0.7599** | **0.3442** | 28.79% | 42.79% |
| **Pennsylvania (42)** | 12,473 | 863 | 6.92% | **0.2852** | **0.7591** | **0.3075** | 29.04% | 32.68% |

### Subgroup Insights & Limitations:
- The model exhibits strong discrimination in large highway networks with high de-icing salt exposure (Texas, Missouri, Pennsylvania).
- Performance in California is constrained by lower overall event prevalence ($6.40\%$) and regional seismic retrofits.
- **Explicit Limitation:** Generalization cannot be assumed for smaller state DOTs, municipal bridge inventories, or international infrastructure without local validation.

---

## 7. Labelled Audit Comparison on Held-Out Test Partition ($N = 65,580$)

> [!IMPORTANT]
> **Audit Disclaimer:** The validation ($N = 65,089$) and test ($N = 65,580$) sets were previously examined in earlier phases. These evaluations are strictly **audit comparisons**, NOT pristine independent confirmation sets. Model selection, threshold tuning, and calibrator fitting were frozen before inspecting this partition.

| Metric | Phase 20 Champion | Phase 21 Candidate | Phase 21B Tuned Winner (`C10`) | Net Gain vs. P20 Champion |
|---|---|---|---|---|
| **Architecture** | `max_iter=100, leaves=31` | `max_iter=150, leaves=63` | `max_iter=200, leaves=63` | Higher capacity + L2 regularization |
| **Class Weight** | `balanced` | `balanced` | `None` (Unweighted) | Native loss preserves margin fidelity |
| **L2 Regularization**| `0.0` | `0.5` | `1.0` | Penalizes noisy terminal splits |
| **Learning Rate** | `0.10` | `0.08` | `0.05` | Smoother gradient descent |
| **Test PR-AUC** | 0.2943 (Reported) | 0.3043 (Reported) | **0.3147** | **+0.0204** ($+6.93\%$ relative lift) |
| **Test ROC-AUC** | 0.7625 (Reported) | 0.7714 (Reported) | **0.7712** | **+0.0087** ($+1.14\%$ relative lift) |
| **Decision Threshold**| $\tau = 0.680$ | $\tau = 0.660$ | $\tau^* = 0.165$ | Derived strictly from training OOF |
| **Test Recall** | 36.40% | 40.17% | **41.83%** | **+5.43% absolute recall gain** |
| **Test Precision** | 30.38% | 29.80% | **29.91%** | Maintained within $0.47\%$ |
| **Test F1-Score** | 0.3312 | 0.3422 | **0.3488** | **+0.0176** ($+5.31\%$ relative lift) |
| **Test Balanced Acc**| 64.12% | 65.46% | **66.12%** | **+2.00%** |
| **Test Confusion Matrix**| $\text{TN}=54862, \text{TP}=2127$ | $\text{TN}=54208, \text{TP}=2347$ | $\text{TN}=54010, \text{TP}=2444$ | **$+317$ additional true deterioration events flagged** |

---

## 8. Artifact Serialization & Checksum Register

All Phase 21B artifacts were serialized to versioned storage under `backend/results/phase21b/`:

| Artifact File | Description | SHA-256 Checksum | Size |
|---|---|---|---|
| `phase21b_tuned_model.joblib` | Final HistGradientBoosting model refitted on full train | `aa806c8185db465fd02536d2d4310638c499d41560ac759e0ea15d4a60f98443` | 692,344 B |
| `phase21b_calibrator.joblib` | Production Platt calibrator fitted on OOF scores | `cd9d2f3833112e9fd90b5bd355646a1e68f50ac5218b038a95f0d31766c5978f` | 558 B |
| `phase21b_encoder.joblib` | Categorical encoder fitted on full train | `14fe2087570446889226640ebb8508e7e832be9b2241c9f92407f9a3f10c6772` | 1,098 B |
| `phase21b_experiment_manifest.json` | Complete experiment record and fold logs | `2270546e2d471f17da3f2838c7a9ac71e13123452e1be631c1e02bdaf106da9c` | 26,415 B |

---

## 9. Test Suite, Linter & Build Verification

1. **Backend Automated Tests:**
   ```powershell
   python -m unittest discover -s backend/tests -p "test_*.py"
   Ran 70 tests in 3.781s
   OK (0 failures, 0 errors)
   ```
   Includes 8 dedicated tests in [`backend/tests/test_phase21b_tuning.py`](file:///d:/sem%203/Deep%20Learning/project/backend/tests/test_phase21b_tuning.py) validating artifact integrity, 26-feature schema conformance, missing numeric handling, unseen category encoding, bounded probabilities, batch invariance, and frozen artifact preservation.

2. **Frontend Linter:**
   ```powershell
   cd frontend && npm run lint
   Found 26 warnings and 0 errors. (44ms, exit code: 0)
   ```

3. **Frontend Production Build:**
   ```powershell
   cd frontend && npm run build
   vite v8.3.2 building client environment for production...
   ✓ 2518 modules transformed.
   ✓ built in 2.62s (exit code: 0)
   ```

---

## 10. Governance & Limitations

1. **Promotion Safeguard:** Phase 20 champion files in `backend/results/phase17/` remain active. The Phase 21B artifacts are stored in `backend/results/phase21b/` ready for production promotion during authorized release cycles.
2. **Target Semantics:** The model predicts biennial deck rating decline on the NBI 0–9 scale ($\text{DECK}_{2025} < \text{DECK}_{2023}$). It does **not** predict bridge collapse, catastrophic structural failure, or maintenance action efficacy.
3. **Decoupled Architecture:** Deterioration probability remains strictly isolated from network consequence, detour costs, and budget knapsack optimization logic.
4. **Final Gate Decision:** **IMPROVEMENT ESTABLISHED**.
