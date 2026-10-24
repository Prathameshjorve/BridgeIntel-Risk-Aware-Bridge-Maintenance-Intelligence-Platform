# Independent Senior ML Audit Report: Phase 17 Model Evaluation
**Platform:** Risk-Aware Bridge Maintenance Intelligence Platform  
**Target:** Condition Prediction & Deterioration Modeling Evaluation (Phase 17)  
**Auditor Role:** Independent Senior Machine Learning Auditor & Research Scientist  
**Date of Audit:** 2026-10-13  
**Audit Scope:** Codebase, machine-readable JSON metrics, confusion matrices, feature importances, dataset manifests, and research reports.

---

### Executive Summary & Audit Mandate

An exhaustive, adversarial audit of Phase 17 was performed. This audit verifies the mathematical correctness of reported metrics, evaluates experimental leakage safeguards, tests statistical uncertainty, inspects probability calibration, and reconciles all reported claims against empirical evidence.

| Audit Category | Checked Items | Status | Key Audit Finding |
|---|---|:---:|---|
| **1. Dataset Integrity & Partitioning** | Row counts, chronology, bridge-ID isolation, allowlist | **PASS** | 435,210 rows, zero duplicate IDs, zero cross-split overlap. All features strictly prior. |
| **2. Task 1 (Condition Rating)** | 10x10 matrix sums, recalculations, model comparison | **QUALIFIED PASS** | Matrix sums to 65,580. Persistence strictly beats HistGBM on Accuracy and MAE. |
| **3. Task 2 (Deterioration Event)** | 2x2 matrix sums, precision, recall, F1, PR-AUC, ROC-AUC | **PASS** | Recalculated metrics match to 4 decimal places. PR-AUC 0.2943 (3.30x lift over 0.0891 base). |
| **4. Statistical Significance** | Uncertainty intervals, bootstrap CIs, McNemar test | **PASS** | PR-AUC 95% CI: [0.2837, 0.3060]; ROC-AUC 95% CI: [0.7566, 0.7684]. Lift is statistically significant. |
| **5. Probability Calibration** | Brier score, probability shifts, reliability diagram | **FAIL / DEFICIENCY** | **Critical Defect:** Balanced weights inflate mean predicted probability to 41.0% (actual: 8.91%). Raw probabilities cannot be used directly in Phase 18. |
| **6. Reproducibility from Artifacts** | Deterministic pipeline, seeds, dependencies | **PASS** | Pipeline reproduces deterministically upon independent execution. |

**Phase 18 Authorization Verdict:** **CONDITIONALLY AUTHORIZED WITH MANDATORY CALIBRATION SAFEGUARD.**

---

### 1. Verification of the Condition Prediction Task (Task 1)

**Target:** `target_deck_condition` $\in \{0, 1, \dots, 9\}$ on the held-out test split ($N = 65,580$).

#### 1.1 Matrix Sums & Sample Count Reconciliation
The $10 \times 10$ confusion matrices in [`confusion_matrices.json`](file:///d:/sem%203/Deep%20Learning/project/backend/results/phase17/confusion_matrices.json) were summed independently:
- `task1_persistence`: $\sum_{i,j} M_{i,j} = \mathbf{65,580}$
- `task1_ridge`: $\sum_{i,j} M_{i,j} = \mathbf{65,580}$
- `task1_hgb_regressor`: $\sum_{i,j} M_{i,j} = \mathbf{65,580}$
- **Reconciliation:** Exactly equals the 65,580 test records in [`bridge_deck_condition_2023_2025.csv`](file:///d:/sem%203/Deep%20Learning/project/backend/data/processed/bridge_deck_condition_2023_2025.csv). All models evaluate the exact same test partition.

#### 1.2 Independent Recalculation of Metrics
Metrics were recomputed directly from the confusion matrix cells:
$$\text{Accuracy} = \frac{\sum_{i=0}^9 M_{i,i}}{N}, \quad \text{MAE} = \frac{\sum_{i,j} |i - j| M_{i,j}}{N}, \quad \text{RMSE} = \sqrt{\frac{\sum_{i,j} (i - j)^2 M_{i,j}}{N}}$$

| Model | Reported Accuracy | Recomputed Accuracy | Reported MAE | Recomputed MAE | Reported RMSE | Recomputed RMSE |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Persistence Baseline** | 86.80% | **86.7963%** | 0.1625 | **0.16247** | 0.5086 | **0.50862** |
| **Ridge Regression** | 86.68% | **86.6758%** | 0.1634 | **0.16340** | 0.5075 | **0.50752** |
| **HistGradientBoosting** | 86.15% | **86.1543%** | 0.1654 | **0.16542** | 0.4963 | **0.49628** |

#### 1.3 Comparative Superiority Assessment
> [!IMPORTANT]
> **Audit Finding: HistGradientBoosting is NOT Superior to Persistence for Task 1.**
> - Under **Exact Match Accuracy**: Persistence (**86.80%**) strictly outperforms Ridge (86.68%) and HistGBM (86.15%).
> - Under **Ordinal MAE**: Persistence (**0.1625**) strictly achieves lower average error than Ridge (0.1634) and HistGBM (0.1654).
> - HistGradientBoosting only achieves lower error on continuous squared loss (**RMSE = 0.4963 vs. 0.5086**), as continuous gradient boosting penalizes large $\ge 2$-point outliers more heavily than the identity function.
> - **Auditor Recommendation:** For Task 1, the **Persistence Baseline remains the authoritative operational standard**. Claims that ML replaces or improves upon persistence for exact 0–9 condition ratings must be explicitly rejected.

---

### 2. Verification of the Deterioration Event Task (Task 2)

**Target:** `target_deterioration` $\in \{0, 1\}$ ($1$ = active degradation over 2-year interval).

#### 2.1 Confusion Matrix Recalculation
From [`confusion_matrices.json`](file:///d:/sem%203/Deep%20Learning/project/backend/results/phase17/confusion_matrices.json), the test confusion matrix for HistGradientBoosting ($\tau^* = 0.680$) is:
$$\begin{bmatrix} TN & FP \\ FN & TP \end{bmatrix} = \begin{bmatrix} 54,862 & 4,875 \\ 3,716 & 2,127 \end{bmatrix}$$
- Total samples: $54,862 + 4,875 + 3,716 + 2,127 = \mathbf{65,580}$ (Exact match).
- True Negatives ($TN$): 54,862 | False Positives ($FP$): 4,875
- False Negatives ($FN$): 3,716 | True Positives ($TP$): 2,127
- Actual Positives ($P$): $2,127 + 3,716 = \mathbf{5,843}$ (Prevalence: **8.9097%**).
- Actual Negatives ($N$): $54,862 + 4,875 = \mathbf{59,737}$ (Prevalence: **91.0903%**).

**Recomputed Binary Metrics:**
- **Precision:** $\frac{TP}{TP + FP} = \frac{2,127}{7,002} = \mathbf{0.303770}$ (Reported: 30.38%) — **PASSED**
- **Recall (Sensitivity):** $\frac{TP}{TP + FN} = \frac{2,127}{5,843} = \mathbf{0.363991}$ (Reported: 36.40%) — **PASSED**
- **Specificity:** $\frac{TN}{TN + FP} = \frac{54,862}{59,737} = \mathbf{0.918392}$ (91.84%) — **PASSED**
- **Balanced Accuracy:** $\frac{\text{Recall} + \text{Specificity}}{2} = \mathbf{0.641192}$ (Reported: 64.12%) — **PASSED**
- **$F_1$-Score:** $\frac{2 \times P \times R}{P + R} = \mathbf{0.331179}$ (Reported: 0.3312) — **PASSED**
- **Exact Accuracy:** $\frac{54,862 + 2,127}{65,580} = \mathbf{0.868999}$ (Reported: 86.90%) — **PASSED**

#### 2.2 Threshold Selection Verification
In [`backend/train_condition_models.py`](file:///d:/sem%203/Deep%20Learning/project/backend/train_condition_models.py#L480-L488), the threshold $\tau^* = 0.680$ was identified by sweeping 81 evenly spaced thresholds on the **Validation set** ($N = 65,089$, Val F1 = 0.3384). The held-out test split was evaluated **strictly once** at this fixed threshold. Zero test feedback was used in threshold optimization.

#### 2.3 Always-Negative Baseline Verification
The Always-Negative baseline classifies all test bridges as $0$:
- $TN = 59,737, \ FP = 0, \ FN = 5,843, \ TP = 0$.
- Accuracy: **91.09%**, Recall: **0.00%**, Precision: **0.00%**, $F_1$: **0.0000**.
- **PR-AUC Baseline Value:** The theoretical average precision of an uninformative random or always-negative classifier equals the positive class prevalence:
  $$\text{PR-AUC}_{\text{base}} = \frac{5,843}{65,580} = \mathbf{0.089097}$$
  Reported baseline PR-AUC matches this exact fraction.

---

### 3. Statistical Significance & Uncertainty Analysis

To determine whether the observed performance lift of HistGradientBoosting over baselines is statistically significant or merely a descriptive artifact, rigorous uncertainty tests were executed:

#### 3.1 95% Wilson Score Confidence Intervals (Test Split, $N = 65,580$)
- **Test Recall:** $36.40\%$ $\implies$ **95% CI: [35.18%, 37.64%]**
- **Test Precision:** $30.38\%$ $\implies$ **95% CI: [29.31%, 31.46%]**
- *Observation:* The lower bound of precision ($29.31\%$) is more than $3.2\times$ higher than the baseline prevalence ($8.91\%$), indicating consistent, tight precision bounds on unseen bridges.

#### 3.2 Non-Parametric Bootstrap Evaluation (500 iterations)
- **PR-AUC (Average Precision):** Mean = $0.2946$ $\implies$ **95% Bootstrap CI: [0.2837, 0.3060]**
  - Baseline Prevalence: $0.0891$
  - *Conclusion:* The lower bound ($0.2837$) is strictly separated from the $0.0891$ baseline by more than 17 standard errors. The lift is **statistically significant ($p < 10^{-15}$)**.
- **ROC-AUC:** Mean = $0.7624$ $\implies$ **95% Bootstrap CI: [0.7566, 0.7684]**
  - Random Baseline: $0.5000$
  - *Conclusion:* The lower bound ($0.7566$) is strictly separated from $0.5000$.

#### 3.3 McNemar's Paired Test
Comparing HistGradientBoosting predictions against the Always-Negative baseline:
$$\chi^2 = \frac{(|2,127 - 4,875| - 1)^2}{2,127 + 4,875} = \mathbf{1,077.7}, \quad p = 2.33 \times 10^{-236}$$
The distribution of correct classifications differs significantly from the uninformative baseline.

---

### 4. Experimental Integrity & Leakage Audit

#### 4.1 Partition Isolation
- Hash algorithm: SHA-256 of `bridge_id` + salt string modulo 100.
- Result: Each physical bridge ID is strictly quarantined to a single partition.
  $$\text{Train} \cap \text{Val} = \emptyset, \quad \text{Train} \cap \text{Test} = \emptyset, \quad \text{Val} \cap \text{Test} = \emptyset$$
  Verified: **Zero cross-partition identity leakage.**

#### 4.2 Preprocessing Pipeline Encapsulation
- `OrdinalEncoder`: Fitted strictly on `X_train_cat` (`cat_encoder.fit_transform(X_train_cat)`). Validation and test sets transformed via `transform()` with unknown values mapped to $-1$.
- `StandardScaler`: Fitted strictly on training data (`scaler.fit_transform(X_train_num_imp)`).
- Median Imputation: Medians computed strictly on training data (`num_medians = X_train_num.median()`).
- Verified: **Zero statistics or information leaked from validation or test splits during preprocessing.**

#### 4.3 Feature Allowlist & Target Leakage
- Features inspected: 26 baseline variables.
- Verified: No 2025 ratings (`2025_DECK_COND_058`, `2025_LOWEST_RATING`, `2025_BRIDGE_CONDITION`), no concurrent component ratings (`2025_SUPERSTRUCTURE_COND_059`), and no post-inspection maintenance items (`WORK_PROPOSED_*`, `WORK_DONE_*`) enter the feature matrix.

#### 4.4 Inspection Age Calculation
- Inspection in [`backend/build_modeling_dataset.py`](file:///d:/sem%203/Deep%20Learning/project/backend/build_modeling_dataset.py#L526-L527):
  ```python
  m23, y23, status23 = parse_date_090(dt23)
  if cleaned_yb and 1700 <= cleaned_yb <= y23:
      struct_age = y23 - cleaned_yb
  ```
- Verified: Age is computed using the **actual baseline routine inspection year** (`y23`, from Item 90, e.g. 2021 or 2022), **not** the arbitrary dataset release year 2023.

---

### 5. Critical Technical Deficiency: Probability Calibration Audit

> [!CAUTION]
> **CRITICAL DEFICIENCY: Uncalibrated Model Probabilities from Balanced Class Weighting.**
> - **Cause:** `HistGradientBoostingClassifier` was instantiated with `class_weight='balanced'`. This artificially reweights positive instances by $\frac{N}{2 N_+} \approx 5.74\times$, shifting the model's logits by $\ln(5.74) \approx +1.75$.
> - **Impact on Output Probabilities:**
>   - Actual Test Set Prevalence: **8.91%** ($0.0891$)
>   - Model Mean Predicted Probability: **41.00%** ($0.4100$) — an artificial $4.6\times$ inflation!
>   - Brier Score (Balanced Model): **0.1901** (Substantially worse than the naive climatological base-rate Brier score of **0.0812**).
> - **Calibration Decile Breakdown on Test Set:**
> 
> | Predicted Probability Decile | Bridge Count | Mean Predicted Probability | Actual Empirical Positive Rate | Calibration Error |
> |:---:|:---:|:---:|:---:|:---:|
> | $[0.2, 0.3)$ | 11,751 | **25.2%** | **3.0%** | $+22.2\%$ (Overestimated) |
> | $[0.4, 0.5)$ | 10,798 | **44.9%** | **7.5%** | $+37.4\%$ (Overestimated) |
> | $[0.6, 0.7)$ | 6,096 | **64.7%** | **16.6%** | $+48.1\%$ (Overestimated) |
> | $[0.7, 0.8)$ | 3,960 | **74.7%** | **25.9%** | $+48.8\%$ (Overestimated) |
> 
> **Operational Risk for Phase 18:**
> If Phase 18 directly plugs `predict_proba[:, 1]` into an expected risk formula:
> $$\text{Risk} = P(\text{deterioration}) \times \text{ConsequenceCost}$$
> the optimization knapsack solver will compute monetary risks that are **$4\times$ to $5\times$ too high**, distorting capital allocation.
> 
> **Auditor Condition:** The probabilities **must be recalibrated** using Platt scaling (`CalibratedClassifierCV(method='sigmoid')`), isotonic regression, or an empirical log-odds base-rate shift before being utilized by the decision engine.

---

### 6. Discrepancy Reconciliation

1. **Standalone Test Probability Arrays:** Test prediction probabilities were not saved to disk as a separate `.npy` or `.csv` column during Phase 17. The confusion matrices and summary metrics are recorded, but full continuous probability arrays were re-generated deterministically using fixed seeds for calibration analysis.
2. **Task 1 Model Selection Framing:** The narrative in `model_comparison_report.md` initially presented HistGradientBoosting alongside persistence without clearly highlighting that Persistence strictly defeats it on Exact Accuracy and MAE. This audit explicitly establishes that **Persistence is the superior benchmark for Task 1**.
3. **Statistical Significance Language:** Claims of "statistically verifiable predictive capability" in earlier reports were descriptive assertions without confidence intervals. This audit provides the formal empirical confidence intervals and McNemar statistics to substantiate the claim.

---

### 7. Audit Verdict & Single Recommended Next Action

## **Verdict: CONDITIONALLY AUTHORIZED**

1. **Authorization Grounds:**
   - Active deterioration detection is genuinely achieved (PR-AUC 0.2943, 95% CI [0.2837, 0.3060], ROC-AUC 0.7625, Recall 36.40% at Precision 30.38%).
   - All experimental leakage boundaries, partition isolations, and chronology constraints passed 100%.
2. **Mandatory Precondition for Phase 18:**
   - **Phase 18 must implement calibrated probability scaling.** Raw model probabilities from the balanced classifier cannot enter the budget optimization solver without Platt scaling or base-rate log-odds calibration.

### Single Next Recommended Action
**Implement `backend/score_bridge_risk.py` with an integrated probability calibrator (`CalibratedClassifierCV` or Platt sigmoid scaling)** to ensure that output deterioration risk probabilities match authentic empirical event rates ($~8.9\%$) before feeding the decision engine's multi-criteria prioritization and knapsack budget solver.
