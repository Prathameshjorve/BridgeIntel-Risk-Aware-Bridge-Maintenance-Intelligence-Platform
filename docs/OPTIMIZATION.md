# Budget Optimization: Knapsack Multi-Objective Formulation

## 1. Problem Formulation
Bridge management authorities face discrete intervention choices across $N$ candidate bridges subject to an annual capital budget ceiling $B$.

Let $x_i \in \{0, 1\}$ denote the binary decision variable for bridge $i$:
- $x_i = 1$: Allocate capital to perform recommended maintenance in current fiscal cycle.
- $x_i = 0$: Defer maintenance to subsequent planning cycle.

---

## 2. Objective Function
We maximize the aggregate portfolio **Net Risk Reduction and Avoided Consequence**:

$$\max \sum_{i=1}^{N} x_i \cdot \mathcal{B}_i$$

where the multi-objective intervention benefit $\mathcal{B}_i$ is defined as:

$$\mathcal{B}_i = \Delta R_i \times \left(\frac{C_i}{50}\right)$$

- $\Delta R_i$: Expected immediate reduction in structural risk score achieved by performing the recommended action (e.g., -62 points).
- $C_i$: Public and network consequence score (0 to 100), weighting interventions on vital commercial corridors higher than low-consequence rural crossings.

---

## 3. Constraints
The total capital expenditure across all selected interventions must not exceed the available appropriation ceiling $B$:

$$\sum_{i=1}^{N} x_i \cdot \text{Cost}_i \le B$$

$$\text{with } x_i \in \{0, 1\} \quad \forall i \in \{1, \dots, N\}$$

---

## 4. Algorithmic Solution
The solver employs **0-1 Knapsack Dynamic Programming** with Benefit-to-Cost Ratio (BCR) ranking heuristics:

$$\text{BCR}_i = \frac{\mathcal{B}_i}{\text{Cost}_i}$$

Candidates are evaluated to achieve Pareto optimality. Any unallocated balance $B - \sum x_i \cdot \text{Cost}_i$ is retained as an emergency contingency reserve.
