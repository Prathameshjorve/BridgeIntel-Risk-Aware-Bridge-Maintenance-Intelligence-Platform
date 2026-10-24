export interface StrategyComparisonMetrics {
  strategyName: 'Risk-Aware Optimization (Proposed)' | 'Worst-Condition-First (Baseline)' | 'Traffic-Volume Heuristic';
  budgetLimitCr: number;
  allocatedBudgetCr: number;
  bridgesSelectedCount: number;
  totalRiskReduction: number;
  totalConsequenceAvoided: number;
  criticalBridgesAddressed: number;
  budgetEfficiencyScore: number; // Risk Reduction per Crore spent
  twoYearDeferredRiskLiabilityCr: number;
}

export interface ModelValidationMetric {
  metricName: string;
  metricValue: number;
  benchmarkValue: number;
  description: string;
  unit?: string;
}

export interface SensitivityCurvePoint {
  weightRatioRiskToImpact: number;
  riskReductionScore: number;
  consequenceAvoidedScore: number;
  bridgesSelected: number;
}

export interface AnalyticsReport {
  baselineComparisons: StrategyComparisonMetrics[];
  modelPerformance: ModelValidationMetric[];
  sensitivityAnalysis: SensitivityCurvePoint[];
}
