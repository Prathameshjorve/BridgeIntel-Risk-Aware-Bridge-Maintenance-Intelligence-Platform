# Risk-Aware Infrastructure Maintenance Decision Engine
### Bridge Maintenance Intelligence Platform

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen)]()
[![Frontend](https://img.shields.io/badge/frontend-React%2019%20%7C%20TypeScript%20%7C%20Tailwind-blue)]()
[![Standard](https://img.shields.io/badge/standard-FHWA%20NBI%20Compliant-slate)]()

An explainable AI-assisted decision-support platform designed to assist bridge engineers and infrastructure authorities in prioritizing bridge maintenance under constrained budgets.

---

## 1. Why This Platform Exists
When managing hundreds or thousands of bridges, relying on an oversimplified **"worst condition first"** strategy produces suboptimal outcomes. A bridge in "fair" condition carrying 75,000 vehicles daily over a critical river corridor without nearby detours often represents far greater systemic risk and public disruption than a rural timber bridge in "poor" condition carrying 800 vehicles with a parallel bypass 5 km away.

This system combines:
1. **Structural Condition & Historical Deterioration** (NBI Items 58, 59, 60 longitudinal rates)
2. **Traffic & Freight Exposure** (Average Daily Traffic [ADT] and Truck Percent [ADTT])
3. **Network Criticality & Detour Penalty** (Bypass distance and daily delay hours)
4. **Public & Emergency Impact** (Trauma centers, fire routes, evacuation corridors)
5. **Maintenance Deferral Sensitivity** (Compounding degradation and exponential cost-of-delay)
6. **Constrained Knapsack Budget Optimization** (Maximizing net portfolio benefit within capital ceilings)

---

## 2. Platform Architecture & Screens

```
                                  [ BRIDGE ASSET DATA ]
                                            │
                                            ▼
                             [ STRUCTURAL DETERIORATION ]
                                            │
                     ┌──────────────────────┴──────────────────────┐
                     ▼                                             ▼
          [ RISK PREDICTION ]                           [ CONSEQUENCE ANALYSIS ]
          (Markov / GBDT Rate)                          (ADT, Detour, Emergency)
                     └──────────────────────┬──────────────────────┘
                                            ▼
                               [ RISK-AWARE PRIORITY ENGINE ]
                                            │
                                            ▼
                           [ CONSTRAINED BUDGET OPTIMIZATION ]
                                (0-1 Knapsack Multi-Objective)
                                            │
                                            ▼
                         [ LIFE-CYCLE DEFERRAL INTELLIGENCE ]
                                            │
                                            ▼
                        [ AUDITABLE EXPLAINABILITY DASHBOARD ]
```

### The 10 Core Application Screens
| Screen | Route | Description |
|---|---|---|
| **Overview Dashboard** | `/dashboard` | High-level portfolio KPIs, risk distribution, urgent deferral alerts, top priority table. |
| **Bridge Portfolio** | `/bridges` | Comprehensive asset registry with search, multi-criteria filters, and quick-inspect drawer. |
| **Bridge Detail** | `/bridges/:id` | Deep-dive dossier: Physical specs, component health (0-9), trend charts, factor attribution. |
| **Priority Ranking** | `/priority` | 1-to-N ranked queue with transparent mathematical attribution breakdown for each asset. |
| **Budget Optimization** | `/optimization` | Interactive capital budget slider (₹15–₹120 Cr), real-time knapsack solver, funded vs deferred plans. |
| **Deferral Intelligence**| `/deferral` | Multi-horizon projections (Current, +1 Yr, +2 Yrs), sensitivity classifications, delay cost multipliers. |
| **Network Impact** | `/network` | Interactive GIS/spatial topology map, bypass detour bottlenecks, emergency facility access. |
| **Analytics & Baselines**| `/analytics` | Head-to-head empirical comparison: Risk-Aware Optimization vs. Condition-Only baseline. |
| **Methodology** | `/methodology` | End-to-end 8-step pipeline, mathematical equations, data standards, and safety guardrails. |
| **Settings** | `/settings` | Decision weight calibration sliders ($w_1, w_2, w_3, w_4$), normalization checks, currency units. |

---

## 3. Quickstart & Local Execution

### Prerequisites
- Node.js (v18+)
- npm (v9+)

### Installation & Launch
```bash
# Navigate to the frontend project
cd frontend

# Install dependencies (already prepared)
npm install

# Start development server
npm run dev

# Run production build & type check
npm run build
```

---

## 4. Scientific Guardrails & Defensibility
- **Decision-Support Standard**: The system acts strictly as an advisory intelligence engine. The licensed professional engineer remains the ultimate certified authority.
- **Non-Fabrication Rule**: Real data originates strictly from verified FHWA NBI records. Demo and simulation assets are unequivocally badged `[SIMULATION DATASET]`.
- **Target Integrity**: Model outputs are termed *Modeled Risk Scores* and *Deterioration Rates*, never arbitrary or unsubstantiated "collapse probabilities."

---

## 5. Documentation Directory
- [`PROJECT_STATUS.md`](PROJECT_STATUS.md) – Persistent multi-session execution tracker.
- [`docs/PROJECT_SPECIFICATION.md`](docs/PROJECT_SPECIFICATION.md) – Formal platform specification and research questions.
- [`docs/UI_SPECIFICATION.md`](docs/UI_SPECIFICATION.md) – UI design system, color tokens, and layout guidelines.
- [`docs/SYSTEM_ARCHITECTURE.md`](docs/SYSTEM_ARCHITECTURE.md) – Module breakdown and pipeline flow.
- [`docs/DATA_DICTIONARY.md`](docs/DATA_DICTIONARY.md) – NBI data elements, derived indices, and field definitions.
- [`docs/OPTIMIZATION.md`](docs/OPTIMIZATION.md) – 0-1 Knapsack mathematical formulation.
- [`docs/DEFERRAL_INTELLIGENCE.md`](docs/DEFERRAL_INTELLIGENCE.md) – Multi-cycle delay escalation curves.
