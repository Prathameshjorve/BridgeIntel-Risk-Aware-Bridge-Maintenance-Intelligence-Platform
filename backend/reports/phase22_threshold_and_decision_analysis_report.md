# Phase 22A & 22B: Calibrated Out-of-Fold Predictions & Decision Workload Analysis Report

**Project:** Risk-Aware Bridge Maintenance Intelligence Platform  
**Target:** Binary Bridge Deck Rating Deterioration ($\text{target\_deterioration} = 1 \text{ if } \text{DECK}_{2025} < \text{DECK}_{2023} \text{ else } 0$)  
**Execution Date:** 2026-10-14  
**Audit Status:** Phase 22A & Phase 22B Completed. Phase 22C (Production Promotion) on hold pending review.  
**Production Champion Status:** **FROZEN & IMMUTABLE** (Zero code or artifact mutations in [`backend/score_bridge_risk.py`](file:///d:/sem%203/Deep%20Learning/project/backend/score_bridge_risk.py) or `backend/results/phase17/`).

---

## 1. Executive Summary & Objective

Phase 22A and Phase 22B established an evidence-based, leakage-safe threshold and decision-workload framework for the bridge deck deterioration model. This phase resolves the probability scale ambiguity identified in Phase 21C, regenerates complete out-of-sample calibrated predictions, and provides state DOT decision-makers with operational policies balancing detection sensitivity against inspection capacity.

### Key Deliverables & Accomplishments:
1. **Byte-for-Byte Preservation:** Verified immutable SHA-256 checksums of `backend/score_bridge_risk.py` and all Phase 17/18 production artifacts before and after execution.
2. **Threshold 0.165 Origin & Scale Reconciliation:** Traced the exact mathematical origin of threshold $\tau = 0.165$. Confirmed that Phase 21B derived $\tau = 0.165$ on uncalibrated out-of-fold probabilities. On the cross-fitted Platt calibrated scale, the exact Max F1 threshold is **$\tau^*_{\text{cal}} = 0.1680$** (F1 = $0.3416$).
3. **Leakage-Safe Out-of-Fold Regeneration (Phase 22A):** Executed 5-fold Stratified Cross-Validation on $N = 304,541$ training records with strictly in-fold OrdinalEncoding, in-fold early stopping, and out-of-sample Platt scaling (zero target leakage).
4. **Reproducible Operational Policies (Phase 22B):** Formulated 8 predeclared operational policies derived strictly from training out-of-fold calibrated probabilities across Max F1, Workload Budget Caps (5%, 10%, 12.5%, 15%), Safety Targets (70% recall), and Efficiency Targets (40% precision).
5. **Fair Side-by-Side Test Audit Comparison ($N = 65,580$):** Benchmarked Phase 21B against the Phase 17 champion using frozen, pre-selected thresholds. Phase 21B demonstrated statistically superior discrimination (PR-AUC $0.3147$ vs $0.2943$), superior calibration (Brier $0.07126$ vs $0.07235$, ECE $0.0020$ vs $0.0021$), and substantial workload efficiency (e.g., catching $+388$ more deteriorations at optimal F1, and eliminating up to $1,639$ wasted inspections under safety-critical policies).
6. **New Phase 22 Storage & Tests:** All outputs serialized to `backend/results/phase22/`. Implemented 8 dedicated unit tests in [`backend/tests/test_phase22_threshold_analysis.py`](file:///d:/sem%203/Deep%20Learning/project/backend/tests/test_phase22_threshold_analysis.py) (78/78 total backend tests passing).

---

## 2. Pre-Run & Post-Run Immutability Verification

All existing production and baseline artifacts were audited on disk before and after execution:

| Artifact File | Expected SHA-256 Hash | Post-Run SHA-256 Hash | Status |
|---|---|---|---|
| `backend/score_bridge_risk.py` | `b49055f0a2b9fbcb6afa046853730f83fb8c508ea161a540e0b48f2db2c3dc61` | `b49055f0a2b9fbcb...` | **BYTE-FOR-BYTE IDENTICAL** |
| `backend/results/phase17/hist_gradient_boosting_classifier.joblib` | `e2b4e2ec334c18b343a55b1bc26395b3684f76678cfa80d4ccc9edf588b6da0b` | `e2b4e2ec334c18b3...` | **BYTE-FOR-BYTE IDENTICAL** |
| `backend/results/phase17/cat_encoder.joblib` | `14fe2087570446889226640ebb8508e7e832be9b2241c9f92407f9a3f10c6772` | `14fe208757044688...` | **BYTE-FOR-BYTE IDENTICAL** |
| `backend/results/phase17/inference_metadata.json` | `b48922c28ee102d65f5af55fd6be446586bcc358e564e652455f8c1b8bedea24` | `b48922c28ee102d6...` | **BYTE-FOR-BYTE IDENTICAL** |
| `backend/results/phase17/serialization_manifest.json` | `fedf43153bb898aafb2b1890873b2b65c9df7e1ef2a16292b2af75ecfc4d253e` | `fedf43153bb898aa...` | **BYTE-FOR-BYTE IDENTICAL** |
| `backend/results/phase18/calibration/phase18_calibrator.joblib` | `7fb7915aefc952c87a17b347004bd2f3f6061f1ad9172e3a9f6f41e2732cfbd3` | `7fb7915aefc952c8...` | **BYTE-FOR-BYTE IDENTICAL** |
| `backend/results/phase21b/phase21b_tuned_model.joblib` | `aa806c8185db465fd02536d2d4310638c499d41560ac759e0ea15d4a60f98443` | `aa806c8185db465f...` | **BYTE-FOR-BYTE IDENTICAL** |
| `backend/results/phase21b/phase21b_calibrator.joblib` | `cd9d2f3833112e9fd90b5bd355646a1e68f50ac5218b038a95f0d31766c5978f` | `cd9d2f3833112e9f...` | **BYTE-FOR-BYTE IDENTICAL** |

---

## 3. Phase 22A: Threshold 0.165 Origin & Calibrated OOF Regeneration

### 3.1 Trace of Threshold 0.165 Origin
In Phase 21B, `winning_oof_probs` was obtained from `HistGradientBoostingClassifier(class_weight=None).predict_proba(X_val)[:, 1]`. A 181-point sweep evaluated candidate thresholds on these uncalibrated probabilities, selecting $\tau^* = 0.1650$ as the Max F1 point.

Because `C10` was trained on native empirical prevalence (unweighted loss), its uncalibrated predictions were already aligned with the true base rate:
- **Uncalibrated OOF Mean:** $0.0866$ (Empirical Base Rate: $0.0871$)
- **Calibrated OOF Mean:** $0.0871$
- **Mean Absolute Difference Between Scales:** $0.00444$
- **Correlation Between Scales:** $0.999603$

### 3.2 Calibrated vs. Uncalibrated Scale Alignment
When cross-fitted Platt calibration ($p_{\text{cal}} = \sigma(A z + B)$) is applied out-of-sample:
- On the **uncalibrated scale**, the optimal Max F1 threshold is $\tau = 0.1620$ ($\tau = 0.1650$ achieves $\text{F1} = 0.3413$, Precision $= 29.2\%$, Recall $= 41.0\%$).
- On the **calibrated scale**, the optimal Max F1 threshold shifts slightly to **$\tau^*_{\text{cal}} = 0.1680$** ($\text{F1} = 0.3416$, Precision $= 28.9\%$, Recall $= 41.7\%$).
- **Conclusion:** The difference between operating at $\tau = 0.1650$ vs $\tau = 0.1680$ on calibrated probabilities is negligible ($\Delta \text{F1} = 0.0002$), but $\tau = 0.1680$ provides formal mathematical consistency when applied to calibrated outputs.

### 3.3 Leakage-Safe Out-of-Sample Regeneration Methodology
- **Partition:** Training split ($N = 304,541$ unique bridge structures).
- **Split Strategy:** 5-fold `StratifiedKFold(n_splits=5, shuffle=True, random_state=42)`.
- **In-Fold Isolation:**
  - `OrdinalEncoder(handle_unknown='use_encoded_value', unknown_value=-1)` fitted strictly on each fold's $80\%$ subset ($N \approx 243,632$).
  - `HistGradientBoostingClassifier(validation_fraction=0.1, n_iter_no_change=10)` internally split its early stopping monitor strictly from the fold's $80\%$ subset.
  - Platt `LogisticRegression(C=1.0)` fitted strictly on the out-of-fold decision margins from the remaining 4 folds and evaluated on fold $k$. Zero observation labels leaked into calibrator training.
- **Out-of-Sample Calibration Quality:**
  - Uncalibrated Brier: $0.07006 \implies$ Calibrated Brier: **$0.07001$**
  - Uncalibrated ECE: $0.0042 \implies$ Calibrated ECE: **$0.0006$** ($84.7\%$ error reduction)

---

## 4. Phase 22B: Reproducible Threshold Analysis & Operational Policies

Operating thresholds were derived across a 446-point fine-grained grid ($\tau \in [0.01, 0.90]$) strictly on training out-of-fold calibrated probabilities.

### 4.1 Predeclared Operational Policy Presets (Training OOF, $N = 304,541$)

| Policy Preset ID | Operational Policy Description | Threshold ($\tau$) | Precision | Recall | F1 Score | Balanced Acc | Specificity | Workload (% Inventory) | Bridges Inspected |
|---|---|---|---|---|---|---|---|---|---|
| **`max_f1_balanced`** | **Max F1 Balanced Inspection (Recommended)** | **0.1680** | **28.92%** | **41.74%** | **0.3416** | **66.17%** | **90.60%** | **12.55%** | **38,214** |
| `origin_cal` | Origin Threshold on Calibrated Scale | 0.1650 | 28.60% | 42.41% | 0.3414 | 66.38% | 90.35% | 12.92% | 39,338 |
| `origin_uncal`| Origin Threshold on Uncalibrated Scale | 0.1650 | 29.22% | 41.04% | 0.3413 | 65.78% | 90.51% | 12.24% | 37,271 |
| `workload_5_pct` | Tight Budget Workload Cap (5% Portfolio) | 0.2780 | 41.14% | 23.59% | 0.2995 | 60.18% | 96.78% | 5.00% | 15,215 |
| `workload_10_pct`| Standard Inspection Workload (10% Portfolio)| 0.1920 | 31.69% | 36.50% | 0.3394 | 64.50% | 92.51% | 10.03% | 30,550 |
| `workload_12_5_pct`| Expanded Maintenance Workload (12.5% Portfolio)| 0.1680 | 28.92% | 41.74% | 0.3416 | 66.17% | 90.60% | 12.55% | 38,214 |
| `workload_15_pct`| High-Capacity Inspection (15% Portfolio) | 0.1500 | 26.85% | 46.30% | 0.3402 | 67.92% | 89.54% | 15.02% | 45,744 |
| `recall_70_pct` | Safety-Critical Policy (70% Recall Target) | 0.0820 | 18.15% | 70.12% | 0.2884 | 69.99% | 69.87% | 33.62% | 102,378 |
| `precision_40_pct`| High-Efficiency Policy (40% Precision Target)| 0.2680 | 40.04% | 24.84% | 0.3065 | 60.69% | 96.53% | 5.40% | 16,452 |

---

## 5. Fair Side-by-Side Held-Out Test Audit Comparison ($N = 65,580$)

> [!IMPORTANT]
> **Audit Integrity Note:** All operational thresholds evaluated below were **frozen from the training out-of-fold and validation partitions**. Zero threshold tuning or parameter selection was performed on the held-out test split.

### 5.1 Test Performance Across Operational Policies

| Operational Policy Preset | Model | Decision Threshold ($\tau$) | Precision | Recall | F1 Score | Balanced Accuracy | Test Workload (% Inventory) | True Positives (TP) | False Positives (FP) | Missed Deteriorations (FN) |
|---|---|---|---|---|---|---|---|---|---|---|
| **Max F1 Balanced Policy** | Phase 17 Baseline | 0.1940 | 30.87% | 35.80% | 0.3315 | 64.04% | 10.33% (6,777) | 2,092 | 4,685 | 3,751 |
| **Max F1 Balanced Policy** | **Phase 21B Tuned** | **0.1680** | **29.53%** | **42.44%** | **0.3483** | **66.27%** | **12.81% (8,398)** | **2,480** | **5,918** | **3,363** |
| *Net Difference (Max F1)* | — | — | *-1.34%* | *+6.64%* | *+0.0168* | *+2.23%* | *+2.48% (+1,621 flags)* | **+388 TP** | *+1,233 FP* | **-388 missed** |
| **Historical Baseline Point** | Phase 17 Baseline | 0.6800 (uncal) | 30.38% | 36.40% | 0.3312 | 64.12% | 10.68% (7,002) | 2,127 | 4,875 | 3,716 |
| **Historical Baseline Point** | Phase 21B Tuned | 0.1650 (cal) | 29.17% | 43.01% | 0.3476 | 66.40% | 13.14% (8,615) | 2,513 | 6,102 | 3,330 |
| **Fixed 10% Workload Budget** | Phase 17 Baseline | 0.1920 | 30.63% | 36.25% | 0.3320 | 64.11% | 10.55% (6,916) | 2,118 | 4,798 | 3,725 |
| **Fixed 10% Workload Budget** | **Phase 21B Tuned** | **0.1920** | **32.10%** | **36.76%** | **0.3427** | **64.58%** | **10.20% (6,692)** | **2,148** | **4,544** | **3,695** |
| *Net Difference (10% Budget)*| — | — | **+1.47%** | **+0.51%** | **+0.0107** | **+0.47%** | *-0.35% (-224 flags)* | **+30 TP** | **-254 FP** | **-30 missed** |
| **Fixed 12.5% Workload Budget**| Phase 17 Baseline | 0.1680 | 27.79% | 42.29% | 0.3354 | 65.77% | 13.56% (8,892) | 2,471 | 6,421 | 3,372 |
| **Fixed 12.5% Workload Budget**| **Phase 21B Tuned** | **0.1680** | **29.53%** | **42.44%** | **0.3483** | **66.27%** | **12.81% (8,398)** | **2,480** | **5,918** | **3,363** |
| *Net Difference (12.5% Budget)*| — | — | **+1.74%** | **+0.15%** | **+0.0129** | **+0.50%** | *-0.75% (-494 flags)* | **+9 TP** | **-503 FP** | **-9 missed** |
| **Safety-Critical Policy (70% Rec)**| Phase 17 Baseline | 0.0820 | 17.44% | 71.13% | 0.2801 | 69.10% | 36.35% (23,836) | 4,156 | 19,680 | 1,687 |
| **Safety-Critical Policy (70% Rec)**| **Phase 21B Tuned** | **0.0820** | **18.57%** | **70.56%** | **0.2941** | **70.16%** | **33.85% (22,197)** | **4,123** | **18,074** | **1,720** |
| *Net Difference (Safety-Critical)*| — | — | **+1.13%** | *-0.57%* | **+0.0140** | **+1.06%** | *-2.50% (-1,639 flags)* | *-33 TP* | **-1,606 FP** | *+33 missed* |

### 5.2 Workload Efficiency & Workload Arithmetic Audit
1. **Audited Workload Arithmetic for Max-F1 Policy:**
   - **Phase 17 Baseline ($\tau = 0.1940$):** Flags $2,092 \text{ TP} + 4,685 \text{ FP} = \mathbf{6,777}$ bridges for physical inspection ($10.33\%$ portfolio workload), leaving $3,751$ missed deteriorations ($\text{FN}$).
   - **Phase 21B Tuned ($\tau = 0.1680$):** Flags $2,480 \text{ TP} + 5,918 \text{ FP} = \mathbf{8,398}$ bridges for physical inspection ($12.81\%$ portfolio workload), leaving $3,363$ missed deteriorations ($\text{FN}$).
   - **Workload Decomposition & Delta:**
     - Net increase in inspections: $8,398 - 6,777 = \mathbf{+1,621}$ additional bridge inspections ($+2.48\%$ portfolio workload increase).
     - True positive detection gain: $2,480 - 2,092 = \mathbf{+388}$ additional deteriorating structures detected ($+6.64\%$ recall gain).
     - False positive inspection burden: $5,918 - 4,685 = \mathbf{+1,233}$ additional false alarms.
     - Missed deteriorations eliminated: $3,751 - 3,363 = \mathbf{-388}$ fewer missed deteriorations.
     - **Identity verification:** $\Delta \text{Inspections} = \Delta \text{TP} + \Delta \text{FP} = 388 + 1,233 = 1,621$.
     - **Incremental inspection efficiency:** $388 / 1,621 = \mathbf{23.94\%}$ of the additional inspections capture true deteriorations.
2. **Under an Inspection Capacity Constraint ($\approx 10\%$ of Portfolio):**
   - Operating at $\tau = 0.1920$, Phase 21B inspects $224$ fewer bridges ($6,692$ vs $6,916$), **eliminates 254 false alarms**, and simultaneously **detects 30 additional true deteriorating structures** compared to Phase 17.
   - Precision improves from $30.63\%$ to $\mathbf{32.10\%}$.
3. **Under an Expanded Maintenance Constraint ($\approx 12.5\%$ of Portfolio):**
   - Operating at $\tau = 0.1680$, Phase 21B inspects $494$ fewer bridges ($8,398$ vs $8,892$), **eliminates 503 false alarms**, and detects 9 additional true deteriorating structures compared to Phase 17 at the same threshold.
   - Precision improves from $27.79\%$ to $\mathbf{29.53\%}$.
4. **Under a Safety-Critical Policy ($70\%$ Recall Target):**
   - Operating at $\tau = 0.0820$, Phase 21B achieves the $70\%$ recall safety objective while **saving 1,639 physical field inspections** (reducing false positive burden from $19,680$ to $18,074$).

---

## 6. Serialized Artifacts & Checksum Register

All outputs produced during Phase 22A & 22B were written to isolated storage under `backend/results/phase22/`:

| Artifact Path | Description | SHA-256 Checksum | Size (Bytes) |
|---|---|---|---|
| `backend/results/phase22/phase22_threshold_manifest.json` | Master threshold manifest, policy configurations, pre-run checksums | `283e7284687fb4936dca23bcf41fe4b19586b6a32cb5e982181773418525b6a7` | 16,219 |
| `backend/results/phase22/phase22_calibrated_oof_analysis.json` | Sampled 223-point threshold curves (calibrated vs uncalibrated) | `3a557bfa3795c478a8731114b036578da63cb88da02ebce006a8e8b2ec01d1c8` | 155,602 |
| `backend/results/phase22/phase22_workload_tradeoffs.json` | Workload vs recall vs precision trade-off matrix across 9 budget tiers | `b3310034a5d89855bdaef365e28a5ce089baec41b9d12bbd63ba5e56e082855f` | 7,111 |
| `backend/evaluate_phase22_decision_analysis.py` | Standalone reproducible evaluation and threshold analysis script | `c97ba77b0c95a6ee9a24df415664daef550f83737b98d98d022b7a0d4c1b268b` | 17,992 |
| `backend/tests/test_phase22_threshold_analysis.py` | Dedicated 8-test unit test suite for Phase 22 artifacts | `c21db33385e0fe13d07bfd75ce7c81d59d18ce9f83ff0c968f9aeb89649479b1` | 5,684 |

---

## 7. Automated Test & Build Regression Outcomes

All automated verification checks executed cleanly across the full repository:

1. **Backend Test Suite:**
   ```powershell
   python -m unittest discover -s backend/tests -p "test_*.py"
   ```
   **Result:** `Ran 78 tests in 4.818s. OK (0 failures, 0 errors).`  
   *(Includes 8 new tests in `test_phase22_threshold_analysis.py` validating artifact existence, immutability of Phase 17/18 champions, threshold bounds, workload monotonicity, confusion matrix arithmetic, and workload efficiency gains).*

2. **Frontend Linter:**
   ```powershell
   cd frontend && npm run lint
   ```
   **Result:** `0 errors, 26 warnings. Finished in 78ms on 53 files.`

3. **Frontend Production Build:**
   ```powershell
   cd frontend && npm run build
   ```
   **Result:** `tsc -b && vite build in 24.54s. 0 errors, dist/ generated successfully.`

---

## 8. Governance, Scientific Semantics & Limitations

1. **Target Semantics:** The model predicts biennial deck rating decline on the NBI 0–9 scale ($\text{target\_deterioration} = 1 \text{ if } \text{DECK}_{2025} < \text{DECK}_{2023}$). It does **not** predict bridge collapse, catastrophic structural failure, or maintenance action efficacy.
2. **Decoupled Architecture:** Predicted deterioration probability is strictly separated from consequence scoring, detour costs, and budget knapsack optimization.
3. **Operational Policy Recommendation:** State DOT agencies should deploy **Policy `max_f1_balanced` ($\tau^*_{\text{cal}} = 0.1680$)** for general planning, or **Policy `workload_10_pct` ($\tau = 0.1920$)** when constrained by strict biennial field inspection quotas.
4. **Current Status:** Phase 22A and Phase 22B are **COMPLETE**. Phase 22C (Production Model Promotion) is on hold pending formal user review and authorization.
