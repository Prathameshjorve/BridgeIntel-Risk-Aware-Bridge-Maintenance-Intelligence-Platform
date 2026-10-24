import { PortfolioSummary } from '../types/bridge';
import { MOCK_BRIDGES } from './bridges';

export const MOCK_SUMMARY: PortfolioSummary = {
  totalBridges: MOCK_BRIDGES.length,
  highPriorityCount: MOCK_BRIDGES.filter(b => b.priorityLevel === 'Urgent' || b.priorityLevel === 'High').length,
  criticalRiskCount: MOCK_BRIDGES.filter(b => b.riskCategory === 'Critical').length,
  availableBudgetCr: 55.0, // e.g. ₹55 Cr budget allocated
  recommendedAllocationCr: 51.5,
  remainingBudgetCr: 3.5,
  estimatedPortfolioRiskReductionPercent: 44.8,
  averageBridgeAge: Math.round(MOCK_BRIDGES.reduce((acc, b) => acc + b.ageYears, 0) / MOCK_BRIDGES.length),
  deferralUrgentCount: MOCK_BRIDGES.filter(b => b.deferralSensitivity === 'High deferral sensitivity' || b.deferralSensitivity === 'Prioritize before deferral').length,
  dataSourceLabel: 'SIMULATED / DEMO DATA'
};
