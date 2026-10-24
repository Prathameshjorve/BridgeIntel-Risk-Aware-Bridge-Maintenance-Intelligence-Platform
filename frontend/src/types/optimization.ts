import { BridgeAsset } from './bridge';

export interface BudgetScenario {
  id: string;
  name: string;
  budgetCr: number;
  description: string;
}

export interface OptimizationResultItem {
  bridge: BridgeAsset;
  selected: boolean;
  allocationCr: number;
  expectedRiskReduction: number;
  consequenceAvoided: number;
  benefitCostRatio: number;
  selectionRank: number;
  deferralConsequenceRisk: number;
}

export interface OptimizationPortfolioResult {
  budgetLimitCr: number;
  totalAllocatedCr: number;
  remainingBudgetCr: number;
  bridgesSelectedCount: number;
  totalCandidateBridges: number;
  totalRiskReduction: number;
  totalConsequenceAvoided: number;
  portfolioRiskReductionPercentage: number;
  items: OptimizationResultItem[];
  solverMethod: '0-1 Knapsack Dynamic Programming' | 'Multi-Objective Pareto Heuristic';
  timestamp: string;
}
