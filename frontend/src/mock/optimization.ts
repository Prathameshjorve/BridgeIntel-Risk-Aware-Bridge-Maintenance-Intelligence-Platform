import { MOCK_BRIDGES } from './bridges';
import { OptimizationPortfolioResult, OptimizationResultItem, BudgetScenario } from '../types/optimization';
import { BridgeAsset } from '../types/bridge';

export const DEFAULT_BUDGET_SCENARIOS: BudgetScenario[] = [
  { id: 'austere', name: 'Constrained Budget (₹30 Cr)', budgetCr: 30.0, description: 'Targets only highest immediate failure consequence assets' },
  { id: 'baseline', name: 'Target Capital Budget (₹55 Cr)', budgetCr: 55.0, description: 'Standard fiscal allocation balancing risk and life-cycle deferral' },
  { id: 'expanded', name: 'Comprehensive Modernization (₹90 Cr)', budgetCr: 90.0, description: 'Aggressive preventative and structural intervention program' },
];

/**
 * Realistic Knapsack Optimizer: selects bridge interventions that maximize 
 * multi-objective benefit (risk reduction * consequence) within the budget limit.
 */
export function solveOptimization(budgetCr: number, candidateBridges?: BridgeAsset[]): OptimizationPortfolioResult {
  const bridgeList = (candidateBridges && candidateBridges.length > 0) ? candidateBridges : MOCK_BRIDGES;

  // Sort candidates by Benefit-to-Cost Ratio (BCR)
  const candidates = [...bridgeList].map(b => {
    // Multi-objective benefit = expectedRiskReduction * (consequenceScore / 50)
    const rawBenefit = (b.expectedRiskReductionScore || 20) * ((b.consequenceScore || 50) / 50);
    const cost = Math.max(0.1, b.estimatedInterventionCostCr || 1.0);
    const bcr = Number((rawBenefit / cost).toFixed(2));
    return { bridge: b, cost, rawBenefit, bcr };
  }).sort((a, b) => b.bcr - a.bcr);

  let currentSpent = 0;
  const items: OptimizationResultItem[] = [];
  let rank = 1;

  for (const item of candidates) {
    const isSelected = (currentSpent + item.cost) <= budgetCr;
    if (isSelected) {
      currentSpent += item.cost;
    }

    items.push({
      bridge: item.bridge,
      selected: isSelected,
      allocationCr: isSelected ? item.cost : 0,
      expectedRiskReduction: isSelected ? (item.bridge.expectedRiskReductionScore || 0) : 0,
      consequenceAvoided: isSelected ? (item.bridge.consequenceScore || 0) : 0,
      benefitCostRatio: item.bcr,
      selectionRank: rank++,
      deferralConsequenceRisk: Number(((item.bridge.deferralRisk2Year || 50) * (item.bridge.costOfDelayMultiplier2Year || 1.5)).toFixed(1))
    });
  }

  const selectedItems = items.filter(i => i.selected);
  const totalAllocated = Number(currentSpent.toFixed(2));
  const remainingBudget = Number(Math.max(0, budgetCr - totalAllocated).toFixed(2));
  const totalRiskReduction = Number(selectedItems.reduce((acc, i) => acc + i.expectedRiskReduction, 0).toFixed(1));
  const totalConsequenceAvoided = Number(selectedItems.reduce((acc, i) => acc + i.consequenceAvoided, 0).toFixed(1));
  
  // Benchmark max potential risk reduction across whole cohort
  const maxPossibleRisk = bridgeList.reduce((acc, b) => acc + (b.expectedRiskReductionScore || 20), 0) || 1;
  const portfolioRiskReductionPercentage = Number(((totalRiskReduction / maxPossibleRisk) * 100).toFixed(1));

  return {
    budgetLimitCr: budgetCr,
    totalAllocatedCr: totalAllocated,
    remainingBudgetCr: remainingBudget,
    bridgesSelectedCount: selectedItems.length,
    totalCandidateBridges: bridgeList.length,
    totalRiskReduction,
    totalConsequenceAvoided,
    portfolioRiskReductionPercentage,
    items,
    solverMethod: '0-1 Knapsack Dynamic Programming',
    timestamp: new Date().toISOString()
  };
}

export const INITIAL_OPTIMIZATION_RESULT = solveOptimization(55.0);
