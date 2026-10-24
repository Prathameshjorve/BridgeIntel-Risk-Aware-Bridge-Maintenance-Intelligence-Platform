# Assumptions and Limitations

## 1. System Scope & Boundaries
- **Asset Scope**: The platform is strictly scoped to highway, municipal, and regional **bridges and culverts**. It does not model roadway pavements, electrical substations, or water pipelines.
- **Decision Authority**: The engine acts as an AI-assisted decision-support platform. All final maintenance programming decisions remain the exclusive responsibility of certified professional engineers.

---

## 2. Modeling Assumptions
1. **Deterioration Continuity**: Longitudinal condition progression assumes continuous operation under observed traffic loadings unless discrete rehabilitation records are documented.
2. **Parametric Cost Approximations**: Where certified contractor bid prices are unavailable, intervention costs are derived parametrically based on bridge deck area ($m^2$), structural material factors, and intervention category.
3. **Detour Routing**: Bypass vehicle delay hours are calculated based on reported NBI detour mileage and standard regional travel velocity assumptions (60 km/h average bypass speed).
4. **Data Standard**: Predictions depend on the accuracy and consistency of visual inspection ratings recorded under FHWA NBIS criteria.

---

## 3. Current Limitations (Simulation vs. Production)
- **Current State**: The frontend interface operates on an isolated, verified simulation dataset (`frontend/src/mock/`) matching future REST/FastAPI contracts.
- **Future Integration (Phase 15+)**: Real historical records from the FHWA NBI database will be ingested, cleaned, and modeled using Python/FastAPI backend pipelines without altering the frontend presentation layer.
