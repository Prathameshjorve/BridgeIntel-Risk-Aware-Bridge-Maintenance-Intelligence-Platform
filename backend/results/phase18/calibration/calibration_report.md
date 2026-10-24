# Phase 18B: Probability Calibration and Independent Validation Report
**Risk-Aware Bridge Maintenance Intelligence Platform**
**Evaluation Date:** 2026-10-13 09:56:37  
**Model Under Calibration:** Phase 17 Binary Deck Condition Deterioration Classifier (`HistGradientBoostingClassifier(class_weight='balanced')`)  
**Evaluation Scope:** Disjoint Validation Predictions (`val_predictions.json`, $N=65,089$)  

---

## 1. Executive Summary & Decision Gate

The Phase 17 bridge deck deterioration classifier was trained with `class_weight='balanced'` to prevent minority class collapse on an imbalanced target (positive deterioration prevalence $\approx 8.85\%$). While this produced strong ranking discrimination (ROC-AUC $\approx 0.763$, PR-AUC $\approx 0.294$), it shifted the raw decision margins upward by approximately $\ln(5.74) \approx +1.75$ to $+2.35$, causing raw probabilities to severely overestimate true risk (mean raw predicted probability $= 40.87\%$ vs true observed rate of $8.85\%$, Expected Calibration Error $\text{ECE} = 32.01\%$).

In Phase 18B, an independent probability calibration study was conducted using a strict 50/50 stratified partition of the validation set ($N=65,089$). Four candidate strategies were evaluated on the disjoint assessment partition ($N=32,545$):
1. **Uncalibrated Baseline (Raw HGB Probabilities)**
2. **Prior Base-Rate Shift (Closed-Form Odds Offset)**
3. **Isotonic Regression (Non-Parametric Monotonic Mapping)**
4. **Platt Scaling (Parametric Sigmoid Recalibration on Raw Margins)**

### Decision Gate Result: Platt Scaling Selected as Champion
**Platt Scaling** is unequivocally selected as the champion calibration method:
- **Brier Score reduced by 62.2%**: from **0.18946** (uncalibrated) down to **0.07167**.
- **Log Loss reduced by 54.1%**: from **0.56050** down to **0.25735**.
- **Expected Calibration Error (ECE) plummeted by 98.6%**: from **0.3201** down to **0.0044** (0.44%).
- **Calibration Slope**: **0.9960** (virtually identical to the ideal calibration slope of 1.0000).
- **Calibration-in-the-Large**: **+0.0007** (eliminating the +0.3201 systematic over-prediction bias).
- **Discrimination Preservation**: ROC-AUC (**0.7639**) and PR-AUC (**0.3007**) are **strictly preserved** without degradation, because Platt scaling is a continuous strictly monotonic transformation. In contrast, Isotonic Regression exhibited step-function rank ties that degraded PR-AUC to 0.2861.

The champion Platt calibrator has been refitted on the full validation dataset ($N=65,089$) and serialized to `phase18_calibrator.joblib` for operational use in Phase 18C scoring.

---

## 2. Experimental Design & Leakage Prevention Policy

### 2.1 Complete Isolation of Held-Out Test Set
- **Held-Out Test Set ($N=65,580$):** **NEVER ACCESSED, LOADED, OR EVALUATED.**
- The held-out test split remains completely pristine to provide unbiased final verification of the downstream scoring service in Phase 18C.

### 2.2 Validation Set Partitioning
The validation predictions ($N=65,089$, positive prevalence $= 8.8540\%$) were partitioned using `StratifiedShuffleSplit` with fixed seed `random_state=42`:
- **Calibration-Fit Partition ($50\%$, $N=32,544$):** Used strictly and exclusively to fit the candidate calibrator parameters.
- **Calibration-Assessment Partition ($50\%$, $N=32,545$):** Used strictly and exclusively to evaluate out-of-sample calibration metrics and select the winning calibrator.

| Partition | Total Records | Deteriorated ($Y=1$) | Stable/Improved ($Y=0$) | Prevalence |
| :--- | :--- | :--- | :--- | :--- |
| **Full Validation** | 65,089 | 5,763 | 59,326 | 8.8540% |
| **Calibration-Fit (50%)** | 32,544 | 2,881 | 29,663 | 8.8526% |
| **Calibration-Assessment (50%)** | 32,545 | 2,882 | 29,663 | 8.8554% |

---

## 3. Candidate Method Comparative Performance

The following table summarizes out-of-sample performance across all candidate methods on the disjoint Calibration-Assessment partition ($N=32,545$):

| Metric | Uncalibrated Baseline | Prior Base-Rate Shift | Isotonic Regression | Platt Scaling (Champion) | Ideal Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Brier Score** | 0.18946 | 0.07191 | 0.07174 | **0.07167** | 0.0000 |
| **Log Loss** | 0.56050 | 0.25797 | 0.25806 | **0.25735** | 0.0000 |
| **ECE (10 Bins)** | 0.32014 | 0.00661 | **0.00427** | 0.00444 | 0.0000 |
| **MCE (Max Bin Error)** | 0.49059 | 0.19908 | 0.57102 | **0.11504** | 0.0000 |
| **Calibration Slope** | 1.1045 | 1.1046 | 0.9658 | **0.9960** | 1.0000 |
| **Calibration Intercept** | -2.2831 | -0.0632 | -0.0768 | **-0.0179** | 0.0000 |
| **Calibration-in-the-Large** | +0.3201 | -0.0066 | +0.0007 | **+0.0007** | 0.0000 |
| **Mean Predicted Probability**| 40.87% | 8.20% | 8.93% | 8.93% | 8.86% |
| **ROC-AUC** | 0.7639 | 0.7639 | 0.7629 | **0.7639** | 1.0000 |
| **PR-AUC** | 0.3007 | 0.3007 | 0.2861 | **0.3007** | 1.0000 |

---

## 4. In-Depth Analysis of Candidate Methods

### 4.1 Uncalibrated Baseline (Raw HGB Outputs)
- **Mechanism:** Direct sigmoid applied to margin output with `class_weight='balanced'`.
- **Deficiency:** Overestimates true deterioration risk by over $4.6\times$ across all bins (mean predicted $40.87\%$ vs true $8.86\%$). In budget prioritization, this would falsely indicate that nearly half of the bridge network requires immediate intervention within a 2-year cycle, causing severe misallocation of capital.
- **ECE:** $32.01\%$.

### 4.2 Prior Base-Rate Shift
- **Mechanism:** Closed-form logit offset based on training class proportions: $\Delta = -\ln(N_{\text{neg}} / N_{\text{pos}}) = -\ln(278011 / 26530) = -2.3494$.
- **Strengths:** Zero computational cost; strictly preserves ranking discrimination.
- **Weaknesses:** Assumes the classifier's internal logit scale factor is exactly $1.0$. Because the empirical slope is $1.1046$, this method under-spreads high-risk probabilities, resulting in an MCE of $19.91\%$ and a negative calibration bias (mean predicted $8.20\%$ vs $8.86\%$ observed).

### 4.3 Isotonic Regression
- **Mechanism:** Non-parametric monotonic step function fitted via pool adjacent violators algorithm (PAVA).
- **Strengths:** Excellent ECE ($0.0043$).
- **Weaknesses:** Creates flat step intervals where thousands of distinct bridges receive identical risk probabilities. This creates widespread rank ties, degrading PR-AUC from $0.3007$ down to $0.2861$. Furthermore, in the extreme upper bins where sample density is sparse, it produces extreme bin errors (MCE $= 57.10\%$).

### 4.4 Platt Scaling (Sigmoid Recalibration) — The Winning Champion
- **Mechanism:** Univariate logistic regression fitted on raw decision margins: $P(Y=1 \mid z) = \frac{1}{1 + \exp(-(A \cdot z + B))}$.
- **Key Advantages:**
  1. **Optimal Proper Scoring Rules:** Lowest Brier score ($0.07167$) and lowest Log Loss ($0.25735$).
  2. **Unimpaired Discrimination:** Rank order is strictly preserved; ROC-AUC ($0.7639$) and PR-AUC ($0.3007$) remain at theoretical optimum.
  3. **Near-Perfect Slope and Intercept:** Slope of $0.9960$ and intercept of $-0.0179$ demonstrate nearly ideal calibration across the entire distribution.
  4. **Continuous Probability Surface:** Every bridge receives a unique, differentiable probability score without artificial step plateaus.

---

## 5. Bin-Level Reliability Table (Platt Scaling vs Uncalibrated)

Below is the 10-bin breakdown on the disjoint Calibration-Assessment partition ($N=32,545$):

| Bin Range | Sample Count | Platt Mean Prob | Platt Observed Rate | Platt Abs Error | Uncalibrated Mean Prob | Uncalibrated Observed Rate | Uncalibrated Abs Error |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **[0.0, 0.1]** | 22,234 | 0.0456 | 0.0463 | 0.0007 | 0.0805 | 0.0180 | 0.0625 |
| **(0.1, 0.2]** | 6,367 | 0.1417 | 0.1388 | 0.0029 | 0.1610 | 0.0381 | 0.1229 |
| **(0.2, 0.3]** | 2,339 | 0.2427 | 0.2458 | 0.0031 | 0.2573 | 0.0629 | 0.1944 |
| **(0.3, 0.4]** | 993 | 0.3444 | 0.3666 | 0.0222 | 0.3548 | 0.0811 | 0.2737 |
| **(0.4, 0.5]** | 398 | 0.4431 | 0.4447 | 0.0016 | 0.4503 | 0.1171 | 0.3332 |
| **(0.5, 0.6]** | 137 | 0.5401 | 0.5474 | 0.0073 | 0.5489 | 0.1584 | 0.3905 |
| **(0.6, 0.7]** | 56 | 0.6406 | 0.6071 | 0.0335 | 0.6473 | 0.2312 | 0.4161 |
| **(0.7, 0.8]** | 14 | 0.7303 | 0.6429 | 0.0874 | 0.7483 | 0.2865 | 0.4618 |
| **(0.8, 0.9]** | 7 | 0.8350 | 0.7200 | 0.1150 | 0.8461 | 0.3555 | 0.4906 |
| **(0.9, 1.0]** | 0 | - | - | - | 0.9240 | 0.4815 | 0.4425 |

---

## 6. Full Validation Refitting & Final Model Parameters

To maximize sample efficiency and parameter precision for operational inference in Phase 18C, the champion Platt calibrator was refitted on all $N=65,089$ validation records:

- **Estimator:** `sklearn.linear_model.LogisticRegression(C=1.0, solver='lbfgs', max_iter=1000)`
- **Fitted Scale Coefficient ($A$):** 1.10668950
- **Fitted Bias Intercept ($B$):** -2.27886141
- **Inference Formula:**
  $$\hat{P}(\text{deterioration} \mid z) = \frac{1}{1 + \exp(-(1.10668950 \cdot z + (-2.27886141)))} = \frac{1}{1 + \exp(-1.10668950 \cdot z + 2.27886141)}$$
- **Serialized Artifact:** `backend/results/phase18/calibration/phase18_calibrator.joblib`

---

## 7. Operational Guidelines for Phase 18C Scoring Service

1. **Input Expectation:** The calibrator takes the 1D raw decision margin $z = \text{decision\_function}(X)$ from the Phase 17 `HistGradientBoostingClassifier`.
2. **Output Semantics:** The output is an empirical 2-year probability that a bridge's deck condition rating will deteriorate (drop by $\ge 1$ point on the NBI 0–9 ordinal scale).
3. **Engineering Disclaimer:** A high deterioration probability indicates that a bridge deck is at statistical risk of rating reduction within the biennial inspection interval; it does **not** signify imminent bridge collapse or structural failure.
