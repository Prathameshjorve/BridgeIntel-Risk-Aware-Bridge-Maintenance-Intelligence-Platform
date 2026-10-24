# Maintenance Deferral Intelligence: Mathematical Formulation & Life-Cycle Modeling

## 1. Why Deferral Analysis is Essential
Bridge deterioration is non-linear. In early stages, preventative maintenance (joint replacement, deck sealants) costs relatively little. However, if water ingress and chloride contamination reach reinforcing steel or prestressed tendons, corrosion and spalling escalate exponentially. Postponing intervention by 12–24 months frequently forces a transition from minor deck repair to full superstructure replacement, doubling or tripling life-cycle capital expenditures.

---

## 2. Deferral Risk Progression
For each asset $i$, we project structural condition degradation over horizons $t \in \{0, 1, 2\}$ years:

$$R_i(t) = R_i(0) + \alpha_i \cdot t + \beta_i \cdot t^2$$

- $R_i(0)$: Current modeled risk score.
- $\alpha_i$: Linear baseline deterioration velocity (derived from historical multi-cycle inspection rates).
- $\beta_i$: Non-linear compounding acceleration factor triggered when key structural thresholds (e.g. NBI rating $\le 4$, high truck volume ADTT $>20\%$, or active fatigue cracking) are active.

---

## 3. Cost-of-Delay Multiplier ($\gamma_i$)
The economic penalty of deferred maintenance is captured by the multiplier $\gamma_i(t)$:

$$\text{Cost}_i(t) = \text{Cost}_i(0) \cdot \gamma_i(t)$$

$$\text{Cost Escalation Penalty} = \text{Cost}_i(t) - \text{Cost}_i(0)$$

Assets where $\gamma_i(2) \ge 1.75$ are categorized as **High Deferral Sensitivity**, indicating that funding intervention immediately avoids massive downstream budget penalties.

---

## 4. Deferral Sensitivity Taxonomy
- **Stable under modeled assumptions**: Linear degradation rate; low immediate penalty if deferred 1 cycle.
- **Monitor**: Moderate degradation; should be re-inspected within 12 months.
- **Prioritize before deferral**: Approaching structural rating threshold (e.g. 4 to 3 drop) where load-posting becomes mandatory.
- **High deferral sensitivity**: Non-linear compounding distress; delaying capital intervention triggers severe structural replacement costs.
