# UI Specification: Bridge Maintenance Intelligence Platform

## 1. Design Philosophy & Visual Language
The interface represents a high-trust, mission-critical engineering intelligence workstation.
- **Tone**: Restrained, objective, data-dense, highly legible.
- **Palette**: Deep navy/slate foundation (`#0f172a`, `#1e293b`), slate card surfaces (`#ffffff`, `#f8fafc`, `#f1f5f9`), subtle borders (`#e2e8f0`).
- **Semantic Indicators**:
  - **Good / Low Risk**: Emerald / Slate-Green (`#059669`, `#10b981`)
  - **Moderate / Monitor**: Amber / Warm Gold (`#d97706`, `#f59e0b`)
  - **High / Urgent**: Orange-Red (`#ea580c`, `#f97316`)
  - **Critical / Priority**: Crimson / Ruby (`#dc2626`, `#ef4444`)
- **Typography**: Clean tabular monospace for numeric IDs and metrics (`font-mono`), legible geometric sans-serif for interface prose.
- **Accessibility**: Dual encoding on all alerts (Icon + Color + Text Label). Full keyboard tab index on tables, interactive drawers, and controls.

---

## 2. Global Layout
```
+---------------------------------------------------------------------------------------+
|  [Logo & Platform Title]   [Search Bridge / Route]    [Demo Status: SIMULATION] [User] | Topbar
+-------------------+-------------------------------------------------------------------+
|  Navigation       |  Page Header (Title, Subtitle, Context Filters, Action Buttons)   |
|  - Overview       +-------------------------------------------------------------------+
|  - Portfolio      |                                                                   |
|  - Priority       |  Main Content Workspace                                           |
|  - Optimization   |  (KPI Grid, Charts, Interactive Data Tables, Inspection Drawers)  |
|  - Deferral       |                                                                   |
|  - Network        |                                                                   |
|  - Analytics      |                                                                   |
|  - Methodology    |                                                                   |
|  - Settings       |                                                                   |
+-------------------+-------------------------------------------------------------------+
```

---

## 3. Screen Specifications (10 Core Modules)

### Screen 1: Overview Dashboard (`/dashboard` or `/`)
- **KPI Row**: Total Bridges Monitored, High/Critical Priority Assets, Available Budget, Recommended Allocation, Aggregate Portfolio Risk Reduction.
- **Risk Distribution Chart**: Donut / Bar breakdown across condition ratings (Good: 7-9, Fair: 5-6, Poor: 3-4, Critical: 0-2).
- **Priority Trend & Deferral Urgency Alert Banner**: Flags bridges with exponential projected deterioration if unaddressed within 24 months.
- **Top Priority Candidates Table**: Quick-inspection cards linking directly to detail view.
- **Budget Utilization Gauge**: Remaining vs. allocated funds under current scenario.

### Screen 2: Bridge Portfolio (`/bridges`)
- **Data Table**: Columns: Bridge ID, Structure Name / Route, State/County, Built/Age, Condition Category, ADT Exposure, Modeled Risk, Consequence, Priority Score, Parametric Cost, Deferral Flag, Actions.
- **Filtering & Controls**: Search by ID/Route, multi-select condition status, slider for ADT volume, sort by any column.
- **Interactive Inspection**: Quick-view drawer on row selection with full drilldown link.

### Screen 3: Bridge Detail Deep-Dive (`/bridges/:id`)
- **Header**: Bridge ID, Route Name, Facility Carried, Feature Intersected, Priority Badge, Quick Action Buttons.
- **Section A: Profile & Physical Asset Specs**: Built year, structural type, total length, deck area, design load, inspection date.
- **Section B: Component Condition Health**: NBI ratings (Deck, Superstructure, Substructure, Culvert) with historical degradation sparklines.
- **Section C: Risk Assessment & Factor Attribution**: Modeled Risk Score (0–100), confidence bound, SHAP-style factor contributions (Deterioration rate, Truck load, Age).
- **Section D: Network & Public Impact**: Detour distance (km), daily vehicle detour delay hours, proximity to emergency hospitals/fire stations.
- **Section E: Recommendation & Cost-of-Delay**: Recommended intervention, parametric cost, expected risk reduction, consequence of 2-year deferral.

### Screen 4: Priority Ranking (`/priority`)
- **Ranked Matrix**: Explicit rank 1 to N ordering bridges by integrated multi-criteria score.
- **Explainability Panel**: Interactive side pane explaining the specific mathematical composition of the selected bridge's ranking.

### Screen 5: Budget Optimization (`/optimization`)
- **Dynamic Scenario Controls**: Budget input field and slider (e.g. ₹25 Cr to ₹250 Cr), preset buttons (Conservative, Baseline, Expanded).
- **Knapsack Selection Summary**: Bridges funded vs deferred, total cost allocated, portfolio risk reduction achieved, unspent budget.
- **Comparison Table**: Clear visual distinction for "Funded in Scenario" vs "Deferred".

### Screen 6: Maintenance Deferral Intelligence (`/deferral`)
- **Trajectory Visualizer**: Multi-horizon trajectory chart: Current vs. +1 Year vs. +2 Years across portfolio.
- **Deferral Sensitivity Matrix**: Categorization into *Stable under modeled assumptions*, *Monitor*, *Prioritize before deferral*, *High deferral sensitivity*.
- **Cost of Delay Multiplier**: Estimated cost escalation when maintenance is delayed into structural rehabilitation phase.

### Screen 7: Network Impact & Geo Overview (`/network`)
- **Interactive Spatial/GIS Simulation Map**: Rendered bridge nodes color-coded by priority, connecting arterial corridors, and detour penalty overlays.
- **Detour Burden Inspector**: Shows critical bypass bottlenecks and emergency access vulnerability.

### Screen 8: Analytics & Baseline Comparison (`/analytics`)
- **Head-to-Head Comparison**: Risk-Aware Optimization vs. Condition-Only ("Worst-First") strategy.
- **Key Metrics**: Avoided Consequence, Portfolio Risk Reduction, Budget Efficiency (Risk Reduction per ₹ Cr).
- **Model Evaluation Specs**: Validation metrics on historical condition prediction (MAE, RMSE, Accuracy).

### Screen 9: Methodology & System Architecture (`/methodology`)
- **Visual Pipeline Flow**: Clear interactive flowchart of the data, modeling, and optimization pipeline.
- **Mathematical Formulations**: LaTeX formulations for Risk, Consequence, Priority Score, and Knapsack optimization.
- **Data Source Standards**: Documented FHWA NBI fields, element-level references, and scientific limitations.

### Screen 10: Settings & Weights Calibration (`/settings`)
- **Weight Calibration**: Sliders for Risk Weight ($w_1$), Consequence Weight ($w_2$), Detour Weight ($w_3$), and Deferral Urgency ($w_4$).
- **Currency & Units**: Regional unit switching (Metric/Imperial, Currency display).
- **Data Source Simulator**: Toggle between demo simulation datasets and future production API endpoints.

---

## 4. Frontend State & Error Handling
All screens strictly implement:
- **Loading State**: Clean skeleton loaders avoiding layout shifts.
- **Empty State**: Explanatory message and reset filter buttons when zero assets match.
- **Error State**: Non-blocking alert banners with retry triggers.
- **Simulation Badge**: Persistent indication that data displayed is currently running on the verified simulation contract.
