# Data Dictionary: FHWA National Bridge Inventory & Derived Metrics

## 1. Primary FHWA NBI Fields (Core)

| Field Name | NBI Item | Description | Valid Range / Format |
|---|---|---|---|
| `STRUCTURE_NUMBER` | Item 8 | Official unique inventory identification | Alphanumeric (15 chars) |
| `YEAR_BUILT` | Item 27 | Year of original structure construction | YYYY (e.g. 1968) |
| `ADT` | Item 29 | Average Daily Traffic volume | Integer (vehicles/day) |
| `DETOUR_KILOMETERS` | Item 19 | Bypass detour length if bridge is closed | Decimal (km) |
| `STRUCTURE_TYPE` | Item 43 | Kind of material/design (Steel, Concrete, etc.) | Coded string |
| `MAX_SPAN_LEN_MT` | Item 48 | Maximum length of single span | Decimal (meters) |
| `STRUCTURE_LEN_MT` | Item 49 | Overall length of structure | Decimal (meters) |
| `DECK_COND_058` | Item 58 | Deck condition rating | Discrete 0–9 (9=Excellent, 0=Failed) |
| `SUPERSTRUCTURE_COND_059`| Item 59 | Superstructure condition rating | Discrete 0–9 (9=Excellent, 0=Failed) |
| `SUBSTRUCTURE_COND_060` | Item 60 | Substructure condition rating | Discrete 0–9 (9=Excellent, 0=Failed) |
| `PERCENT_ADT_TRUCK` | Item 109 | Average Daily Truck Traffic percentage | Integer % (e.g. 24%) |
| `LATITUDE` | Item 16 | Geographic latitude in degrees | Decimal degrees |
| `LONGITUDE` | Item 17 | Geographic longitude in degrees | Decimal degrees |

---

## 2. Derived Engineering & Decision Metrics

| Metric Name | Type | Range | Mathematical Derivation / Description |
|---|---|---|---|
| `modeledRiskScore` | Float | 0.0 – 100.0 | Estimated probability of transition to Poor condition (≤4) within 24 months, scaled by structural fatigue and scour vulnerability. |
| `riskCategory` | Enum | Low, Moderate, High, Critical | Qualitative binning: Low (<30), Moderate (30–65), High (65–80), Critical (≥80). |
| `consequenceScore` | Float | 0.0 – 100.0 | Composite impact index: $f(\text{ADT}, \text{ADTT}, \text{Detour Km}, \text{Critical Facilities Connected})$. |
| `dailyDetourDelayVehicleHours` | Float | ≥ 0 | Estimated daily cumulative delay hours inflicted on traveling public if bridge is closed: $\text{ADT} \times (\text{Detour Km} / 60 \text{ km/h})$. |
| `priorityScore` | Float | 0.0 – 100.0 | Integrated decision score: $0.35 \times \text{Risk} + 0.25 \times \text{Consequence} + 0.20 \times \text{Exposure} + 0.20 \times \text{DeferralPenalty}$. |
| `estimatedInterventionCostCr` | Float | ≥ 0 | Parametric intervention cost in INR Crores estimated from deck area ($m^2$), structural type factor, and required intervention category. |
| `costOfDelayMultiplier2Year` | Float | 1.0 – 3.0x | Estimated capital expenditure escalation if preventative intervention is postponed into heavy rehabilitation/replacement phase. |
