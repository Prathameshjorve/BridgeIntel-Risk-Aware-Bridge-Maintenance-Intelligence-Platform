import { OptimizationPortfolioResult, BudgetScenario } from '../../types/optimization';
import { solveOptimization, DEFAULT_BUDGET_SCENARIOS, INITIAL_OPTIMIZATION_RESULT } from '../../mock/optimization';

export const optimizationService = {
  async getScenarios(): Promise<BudgetScenario[]> {
    return [...DEFAULT_BUDGET_SCENARIOS];
  },

  async runOptimization(budgetCr: number, candidateBridges?: any[]): Promise<OptimizationPortfolioResult> {
    await new Promise(resolve => setTimeout(resolve, 150));
    return solveOptimization(budgetCr, candidateBridges);
  },

  async getInitialOptimization(candidateBridges?: any[]): Promise<OptimizationPortfolioResult> {
    return solveOptimization(55.0, candidateBridges);
  }
};
