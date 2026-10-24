# FHWA National Bridge Inventory (NBI) Longitudinal Cross-Year Comparison

**Date:** 2026-10-12 23:45:40  
**Scope:** Multi-year tracking across 2023, 2024, and 2025 NBI releases  

---

## 1. Inventory Overlap & Attrition Overview

| Comparison Period | Earlier Year Unique IDs | Later Year Unique IDs | 1-to-1 Matched IDs | Retired / Omitted | Newly Added | Inspection Date Changed |
|---|---|---|---|---|---|---|
| **2023 → 2024** | 621,579 | 623,215 | 617,287 | 4,292 | 5,928 | 312,346 (50.6%) |
| **2024 → 2025** | 623,215 | 624,191 | 619,242 | 3,973 | 4,949 | 313,000 (50.55%) |
| **2023 → 2025** | 621,579 | 624,191 | 613,574 | 8,005 | 10,617 | 574,037 (93.56%) |

> **Key Finding on Inspection Cycles:**
> - **1-Year Snapshots (2023→2024 and 2024→2025):** Exactly ~50.6% of matched bridges experienced an inspection date change. This confirms that half of the bridge population is inspected on odd years and the other half on even years, reflecting the biennial NBIS inspection cycle.
> - **2-Year Interval (2023→2025):** 93.56% (574,037 bridges) experienced a date update, capturing a virtually complete national routine inspection cycle.

---

## 2. Deck Condition Longitudinal Stability & Change

| Comparison Period | Numeric Observations in Both | Unchanged Rating | Degraded (Lower) | Improved (Maintenance) | Changed WITH Date Change | Changed WITHOUT Date Change |
|---|---|---|---|---|---|---|
| **2023 → 2024** | 465,971 | 438,741 (94.16%) | 19,030 (4.08%) | 8,200 (1.76%) | 25,920 | 1,310 |
| **2024 → 2025** | 466,100 | 434,057 (93.13%) | 20,654 (4.43%) | 11,389 (2.44%) | 30,714 | 1,329 |
| **2023 → 2025** | 461,915 | 404,615 (87.6%) | 38,290 (8.29%) | 19,010 (4.12%) | 57,011 | 289 |

> **Crucial Modeling Implication: The Severe Class Imbalance Challenge**
> - Over a 2-year window (2023→2025), **87.60% of bridges remain at the exact same condition rating**.
> - Only **8.29% degrade** by 1 or more points, while **4.12% improve** due to structural maintenance or rehabilitation.
> - A naive persistent baseline ($y_{t+1} = y_t$) achieves **87.6% accuracy**. Any predictive ML model must be evaluated on **deterioration recall, macro-F1, and ordinal MAE**, rather than raw classification accuracy.
