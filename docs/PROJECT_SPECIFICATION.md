# Project Specification: Risk-Aware Infrastructure Maintenance Decision Engine

## 1. System Identity & Mission
The **Bridge Maintenance Intelligence Platform** is an explainable AI-assisted decision-support platform designed to assist bridge engineers, transportation agencies, and municipal authorities in prioritizing maintenance across large bridge inventories subject to strict budget ceilings.

Rather than relying purely on an oversimplified "worst condition first" heuristic, the system combines:
- **Current Structural Condition** (NBI ratings for Deck, Superstructure, Substructure, Culverts)
- **Historical Deterioration Trends** (Multi-year longitudinal degradation rates)
- **Traffic Exposure** (Average Daily Traffic [ADT], Average Daily Truck Traffic [ADTT])
- **Network Criticality & Detour Penalty** (Detour length, route classification, bypass viability)
- **Public & Emergency Service Impact** (Access to regional trauma centers, fire routes, evacuation corridors)
- **Maintenance Urgency & Deferral Risk** (Compounding degradation rate and exponential future cost under delayed intervention)
- **Intervention Cost & Budget Optimization** (Knapsack-style constrained multi-objective allocation)

The platform explicitly maintains that the **engineer remains the ultimate certified authority**. The engine generates transparent, defensible, prioritized recommendations with auditable attribution.

---

## 2. Research Questions
1. **Primary Research Question**: Does a multi-dimensional, risk-aware, budget-constrained decision engine yield higher aggregate portfolio risk reduction and lower consequence burdens than a conventional condition-only ("worst first") maintenance allocation strategy under identical budget constraints?
2. **Secondary Research Question**: Can maintenance-deferral analysis quantitatively identify high-consequence transition thresholds where delaying maintenance by 12–24 months significantly elevates future risk and life-cycle intervention expenditures?

---

## 3. Data Integration Strategy (FHWA NBI)
The empirical pipeline relies on the **Federal Highway Administration (FHWA) National Bridge Inventory (NBI)** data standard.
- **Condition Ratings (Items 58, 59, 60, 62)**: Discrete 0–9 condition ratings for Deck, Superstructure, Substructure, and Culvert.
- **Traffic Exposure (Item 29, 109)**: ADT and percent truck traffic.
- **Detour Length (Item 19)**: Direct bypass distance in kilometers/miles.
- **Structure Characteristics (Items 27, 43, 48, 49)**: Year built, design main span material/type, maximum span length, total structure length.
- **Maintenance Costs (Item 094/096 or Parametric Derived Models)**: Clearly attributed parametric cost estimation based on deck area and structural type, pending verified historical cost records.

### Scientific Guardrails
- **No Fabricated Measurements**: Data presented as real must originate from authentic NBI inspection records.
- **No Unsubstantiated Claims**: The model does not output generic "probability of bridge collapse" unless trained and validated on verified structural collapse target datasets. Instead, outputs represent **deterioration risk indices**, **priority scores**, and **deferral sensitivity indices**.
- **Clear Isolation**: Demo and simulation datasets used for interface responsiveness must be unequivocally labeled `[DEMO / SIMULATION]`.

---

## 4. Analytical Pipeline & Formulation
```
[ NBI Longitudinal Records ]
             │
             ▼
[ Data Preprocessing & Validation ]
             │
             ▼
[ Structural Deterioration / Transition Modeling ] (Markov / Gradient Boosting)
             │
             ▼
[ Consequence & Network Exposure Analysis ]
  • Exposure = f(ADT, ADTT)
  • Detour Burden = f(Detour Km, Volume)
  • Public Impact = Criticality Index
             │
             ▼
[ Multi-Attribute Priority Engine ]
  Priority = w1·Risk + w2·Consequence + w3·Urgency + w4·DeferralSensitivity
             │
             ▼
[ Knapsack Budget Optimization ]
  Maximize Σ (Risk Reduction_i · Consequence_i)
  Subject to: Σ Cost_i ≤ Budget_Available
             │
             ▼
[ Explainability & Audit Layer ] (SHAP / Contribution Breakdown)
             │
             ▼
[ Engineering Decision Support Dashboard ]
```

---

## 5. Decision-Support Language Standards
To ensure professional credibility and avoid overclaiming AI autonomy, all interface copy and reports adhere to the following terminology:
- Use **"Modeled Risk"** instead of "Actual Probability of Failure".
- Use **"Recommended Priority"** instead of "Mandatory Action".
- Use **"Sensitivity under 2-Year Deferral"** instead of "Safe to delay".
- Use **"Parametric Cost Estimate"** instead of "Guaranteed Contractor Price".
