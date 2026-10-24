# Preliminary Feature and Target Specification: Bridge Condition Prediction

## 1. Problem Formulation & Task Definition

### 1.1 Objective
Predict a bridge structure's next observed deck-condition rating ($y_{t+1} \in \{0, 1, \dots, 9\}$) from inspection history, physical structural characteristics, and traffic exposure features available at the baseline inspection time $t$.

### 1.2 Target Formulations
1. **Primary Formulation (Ordinal Regression / Multi-Class Classification):**
   $$y \in \{0, 1, 2, 3, 4, 5, 6, 7, 8, 9\}$$
   Represents `DECK_COND_058` recorded at the subsequent biennial inspection ($t+1$).
2. **Secondary Formulation (Deterioration Event Classification):**
   $$y_{\text{degrade}} = \begin{cases} 1 & \text{if } \text{DECK}_{t+1} < \text{DECK}_t \\ 0 & \text{if } \text{DECK}_{t+1} \ge \text{DECK}_t \end{cases}$$
   Specifically targets identifying the ~8.3% minority of bridges undergoing active degradation over the 2-year horizon.

---

## 2. Target Leakage Audit & Prohibited Fields

Strict leakage boundaries are enforced. Under no circumstances may features be ingested that encode information from or after the target inspection event.

### 2.1 Absolutely Prohibited Fields (Target Leakage)
| Prohibited Field | NBI Item | Leakage Rationale |
|---|---|---|
| `DECK_COND_058(t+1)` | Item 58 | **Direct Target Leakage.** |
| `LOWEST_RATING(t+1)` | Derived | Encodes `min(Deck, Super, Sub, Culvert)` at time $t+1$; directly reveals target when deck is lowest rating. |
| `BRIDGE_CONDITION(t+1)` | Derived | Encodes federal Good/Fair/Poor classification at time $t+1$; directly discloses rating range. |
| `SUPERSTRUCTURE_COND_059(t+1)` | Item 59 | Observed concurrently during target inspection; co-dependent component condition. |
| `SUBSTRUCTURE_COND_060(t+1)` | Item 60 | Observed concurrently during target inspection; co-dependent component condition. |
| `CULVERT_COND_062(t+1)` | Item 62 | Observed concurrently during target inspection. |
| `DATE_OF_INSPECT_090(t+1)` | Item 90 | Inspection timestamp of target observation; unknown prior to inspection completion. |
| `WORK_PROPOSED_*` / `WORK_DONE_*` | Administrative | Proposed or completed maintenance entries generated in response to observed target condition. |

---

## 3. Permitted Feature Specification (Available at Time $t$)

All inputs must represent verified historical data recorded at or before baseline inspection time $t$.

| Category | Field Name | NBI Item | Type | Description |
|---|---|---|---|---|
| **Baseline Condition** | `DECK_COND_058` | Item 58 | Ordinal (0–9) | Current deck rating at baseline inspection $t$. |
| | `SUPERSTRUCTURE_COND_059` | Item 59 | Ordinal (0–9) | Current superstructure rating at baseline inspection $t$. |
| | `SUBSTRUCTURE_COND_060` | Item 60 | Ordinal (0–9) | Current substructure rating at baseline inspection $t$. |
| **Physical Structure** | `STRUCTURE_KIND_043A` | Item 43A | Categorical | Kind of material (Steel, Concrete, Prestressed, Timber). |
| | `STRUCTURE_TYPE_043B` | Item 43B | Categorical | Type of design (Beam, Truss, Arch, Box Girder, Slab). |
| | `DECK_STRUCTURE_TYPE_107` | Item 107 | Categorical | Concrete cast-in-place, precast, steel grid, timber. |
| | `SURFACE_TYPE_108A` | Item 108A | Categorical | Monolithic concrete, latex concrete, bituminous, epoxy. |
| | `MEMBRANE_TYPE_108B` | Item 108B | Categorical | Preformed fabric, built-up, epoxy, none. |
| **Geometry** | `STRUCTURE_LEN_MT_049` | Item 49 | Continuous (m) | Total structural length. |
| | `MAX_SPAN_LEN_MT_048` | Item 48 | Continuous (m) | Maximum span length. |
| | `DECK_WIDTH_MT_052` | Item 52 | Continuous (m) | Out-to-out deck width. |
| **Age & Climate** | `YEAR_BUILT_027` | Item 27 | Integer (YYYY) | Year structure was constructed. |
| | `STRUCTURE_AGE_YEARS` | Derived | Continuous | Calculated age at baseline: $\text{InspectYear}_t - \text{YearBuilt}$. |
| | `STATE_CODE_001` | Item 1 | Categorical | FIPS State code (regional climate, freeze-thaw severity). |
| | `LATITUDE` / `LONGITUDE` | Items 16 / 17 | Continuous | Spatial coordinates for climate zone stratification. |
| **Traffic Exposure** | `ADT_029` | Item 29 | Integer | Average Daily Traffic volume. |
| | `PERCENT_ADT_TRUCK_109` | Item 109 | Integer (%) | Commercial freight truck traffic share. |
| | `DETOUR_KILOMETERS_019` | Item 19 | Continuous (km) | Bypass detour length. |

---

## 4. Leakage-Resistant Data Splitting and Evaluation Plan

### 4.1 Grouped Splitting by Bridge Identifier
- **Requirement:** A bridge structure must never have records appearing in both the training set and the evaluation/test set.
- **Method:** `GroupKFold` or `GroupShuffleSplit` partitioned on `(STATE_CODE_001, STRUCTURE_NUMBER_008)`.
- **Ratio:** 70% Train, 15% Validation, 15% Test.

### 4.2 Pipeline Isolation
- Feature transformers (imputation, standard scalers, categorical encoders) must be fit **exclusively** on the training split, then applied to validation and test splits without refitting.

### 4.3 Mandatory Baselines
1. **Naive Persistence Baseline:**
   $$\hat{y}_{t+1} = \text{DECK}_t$$
   *Empirical Accuracy:* **87.60%**.
   *Note:* Any model must outperform this baseline on deterioration-specific metrics to demonstrate scientific utility.
2. **Mean Degradation / Markov State Transition Baseline:**
   Transition probabilities calculated directly from national historical rate tables.

### 4.4 Evaluation Metrics
- **Mean Absolute Error (MAE):** Measures average ordinal rating deviation.
- **Deterioration Event Recall:** Percentage of actual degrading bridges ($\Delta \le -1$) successfully identified.
- **Precision-Recall AUC (PR-AUC):** Robust evaluation under the 8.3% minority positive class.
- **Macro-Averaged F1:** Balances rare condition classes (ratings 2, 3, 4) against dominant classes (ratings 6, 7).
