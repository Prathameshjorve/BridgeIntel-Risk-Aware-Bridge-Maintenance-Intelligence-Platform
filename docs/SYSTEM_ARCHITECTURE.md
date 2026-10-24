# System Architecture: Bridge Maintenance Intelligence Platform

## 1. Architectural Principles
1. **Separation of Concerns**: Clean isolation between the frontend user interface, typed data transfer contracts, and the future backend data ingestion/ML pipelines.
2. **Defensible Explainability**: Every machine-learning recommendation is decomposed into additive, auditable factor contributions (SHAP-approximated).
3. **Decoupled Service Interfaces**: Frontend pages interact strictly with typed asynchronous API service modules (`src/services/api/`), ensuring zero UI redesign when swapping from simulation mock data to live backend REST endpoints.

---

## 2. Logical Modules
- **Module 1: Asset Registry / Inventory (FHWA NBI)**: Ingestion, normalization, and indexing of physical bridge records.
- **Module 2: Condition Analysis**: Longitudinal monitoring of Deck (58), Superstructure (59), and Substructure (60).
- **Module 3: Risk & Deterioration Prediction**: Gradient Boosting and Markov transition models estimating condition drop velocity.
- **Module 4: Public & Network Impact**: Spatial analysis calculating traffic exposure (ADT, ADTT) and bypass detour vehicle delay hours.
- **Module 5: Priority Engine**: Weighted multi-criteria synthesis combining risk, consequence, urgency, and deferral penalties.
- **Module 6: Constrained Budget Optimization**: 0-1 Knapsack solver selecting interventions to maximize portfolio benefit within appropriation ceilings.
- **Module 7: Maintenance Deferral Intelligence**: Longitudinal modeling of +12 and +24 month delayed capital intervention.
- **Module 8: Explainability & Audit**: Transparent feature attribution breakdown.
- **Module 9: Engineering Workstation UI**: 10 reactive screens providing decision support.
- **Module 10: Evaluation & Benchmarking**: Head-to-head empirical comparison against condition-only ("worst first") heuristics.

---

## 3. Data Pipeline Flow (Phase 15+ Integration)
```
[ Raw NBI ASCII / CSV Files ]
             │
             ▼
[ Data Profiler & Validator (Pandas/Polars) ]
             │
             ▼
[ Temporal Reconstruction (Multi-Year Trajectories) ]
             │
             ▼
[ Feature Engineering (Structural, Age, Traffic, Scour, Detour) ]
             │
             ▼
[ Deterioration Model (XGBoost / Markov Chains) ]
             │
             ▼
[ Multi-Objective Knapsack Solver (OR-Tools / Scipy) ]
             │
             ▼
[ FastAPI Service Layer (/api/bridges, /api/optimization) ]
             │
             ▼
[ React Decision Support Dashboard ]
```
