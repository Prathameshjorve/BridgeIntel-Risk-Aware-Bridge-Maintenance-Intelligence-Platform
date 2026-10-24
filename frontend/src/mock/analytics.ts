import { AnalyticsReport, StrategyComparisonMetrics, ModelValidationMetric, SensitivityCurvePoint } from '../types/analytics';

export const MOCK_STRATEGY_COMPARISONS: StrategyComparisonMetrics[] = [
  {
    strategyName: "Risk-Aware Optimization (Proposed)",
    budgetLimitCr: 55.0,
    allocatedBudgetCr: 51.5,
    bridgesSelectedCount: 4,
    totalRiskReduction: 230.0,
    totalConsequenceAvoided: 339.5,
    criticalBridgesAddressed: 4,
    budgetEfficiencyScore: 4.47, // 230.0 / 51.5
    twoYearDeferredRiskLiabilityCr: 14.2
  },
  {
    strategyName: "Worst-Condition-First (Baseline)",
    budgetLimitCr: 55.0,
    allocatedBudgetCr: 53.8,
    bridgesSelectedCount: 3,
    totalRiskReduction: 168.0,
    totalConsequenceAvoided: 204.0,
    criticalBridgesAddressed: 3,
    budgetEfficiencyScore: 3.12, // 168.0 / 53.8
    twoYearDeferredRiskLiabilityCr: 32.6
  },
  {
    strategyName: "Traffic-Volume Heuristic",
    budgetLimitCr: 55.0,
    allocatedBudgetCr: 47.0,
    bridgesSelectedCount: 3,
    totalRiskReduction: 136.0,
    totalConsequenceAvoided: 249.0,
    criticalBridgesAddressed: 2,
    budgetEfficiencyScore: 2.89,
    twoYearDeferredRiskLiabilityCr: 28.4
  }
];

export const MOCK_MODEL_PERFORMANCE: ModelValidationMetric[] = [
  {
    metricName: "Historical Condition Prediction MAE",
    metricValue: 0.32,
    benchmarkValue: 0.65,
    description: "Mean Absolute Error on 10-year longitudinal NBI condition delta prediction (0-9 scale)",
    unit: "pts"
  },
  {
    metricName: "Condition Deterioration RMSE",
    metricValue: 0.44,
    benchmarkValue: 0.82,
    description: "Root Mean Squared Error evaluating predicted vs observed condition decline",
    unit: "pts"
  },
  {
    metricName: "High Deterioration Transition Recall",
    metricValue: 0.88,
    benchmarkValue: 0.71,
    description: "Sensitivity in detecting bridges dropping by ≥1 rating within 24 months",
    unit: "%"
  },
  {
    metricName: "Priority Classification ROC-AUC",
    metricValue: 0.91,
    benchmarkValue: 0.78,
    description: "Area Under ROC curve for distinguishing urgent rehabilitation needs",
    unit: ""
  }
];

export const MOCK_SENSITIVITY_CURVE: SensitivityCurvePoint[] = [
  { weightRatioRiskToImpact: 0.2, riskReductionScore: 160, consequenceAvoidedScore: 370, bridgesSelected: 4 },
  { weightRatioRiskToImpact: 0.4, riskReductionScore: 195, consequenceAvoidedScore: 355, bridgesSelected: 4 },
  { weightRatioRiskToImpact: 0.6, riskReductionScore: 225, consequenceAvoidedScore: 342, bridgesSelected: 4 },
  { weightRatioRiskToImpact: 0.8, riskReductionScore: 242, consequenceAvoidedScore: 310, bridgesSelected: 4 },
  { weightRatioRiskToImpact: 1.0, riskReductionScore: 255, consequenceAvoidedScore: 280, bridgesSelected: 4 },
];

export const MOCK_ANALYTICS_REPORT: AnalyticsReport = {
  baselineComparisons: MOCK_STRATEGY_COMPARISONS,
  modelPerformance: MOCK_MODEL_PERFORMANCE,
  sensitivityAnalysis: MOCK_SENSITIVITY_CURVE
};
