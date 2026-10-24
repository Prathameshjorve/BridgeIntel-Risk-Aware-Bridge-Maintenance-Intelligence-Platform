import { MOCK_BRIDGES } from './bridges';
import { DeferralPortfolioReport, DeferralBridgeAnalysis, DeferralTrajectoryPoint } from '../types/deferral';

const currentAvgRisk = Number((MOCK_BRIDGES.reduce((sum, b) => sum + b.modeledRiskScore, 0) / MOCK_BRIDGES.length).toFixed(1));
const year1AvgRisk = Number((MOCK_BRIDGES.reduce((sum, b) => sum + b.deferralRisk1Year, 0) / MOCK_BRIDGES.length).toFixed(1));
const year2AvgRisk = Number((MOCK_BRIDGES.reduce((sum, b) => sum + b.deferralRisk2Year, 0) / MOCK_BRIDGES.length).toFixed(1));

export const MOCK_DEFERRAL_TRAJECTORIES: DeferralTrajectoryPoint[] = [
  {
    horizonLabel: 'Current',
    yearOffset: 0,
    averageRiskScore: currentAvgRisk,
    criticalCount: MOCK_BRIDGES.filter(b => b.riskCategory === 'Critical').length,
    projectedPortfolioDegradationCostCr: 0
  },
  {
    horizonLabel: '+1 Year',
    yearOffset: 1,
    averageRiskScore: year1AvgRisk,
    criticalCount: MOCK_BRIDGES.filter(b => b.deferralRisk1Year >= 75).length,
    projectedPortfolioDegradationCostCr: 18.2
  },
  {
    horizonLabel: '+2 Years',
    yearOffset: 2,
    averageRiskScore: year2AvgRisk,
    criticalCount: MOCK_BRIDGES.filter(b => b.deferralRisk2Year >= 75).length,
    projectedPortfolioDegradationCostCr: 46.8
  }
];

export const MOCK_DEFERRAL_ANALYSIS: DeferralBridgeAnalysis[] = MOCK_BRIDGES.map(b => {
  const riskDelta2Year = Number((b.deferralRisk2Year - b.modeledRiskScore).toFixed(1));
  const riskIncreasePercentage = Number(((riskDelta2Year / b.modeledRiskScore) * 100).toFixed(1));
  const costEscalationCr = Number((b.estimatedInterventionCostCr * (b.costOfDelayMultiplier2Year - 1)).toFixed(2));

  return {
    bridge: b,
    currentRisk: b.modeledRiskScore,
    risk1Year: b.deferralRisk1Year,
    risk2Year: b.deferralRisk2Year,
    riskDelta2Year,
    riskIncreasePercentage,
    status: b.deferralSensitivity,
    transitionThresholdExceeded: b.deferralRisk2Year >= 85 || riskIncreasePercentage >= 20,
    costEscalationCr,
    recommendedActionBeforeDeferral: b.recommendedAction
  };
}).sort((a, b) => b.riskDelta2Year - a.riskDelta2Year);

export const MOCK_DEFERRAL_REPORT: DeferralPortfolioReport = {
  trajectories: MOCK_DEFERRAL_TRAJECTORIES,
  highSensitivityCount: MOCK_BRIDGES.filter(b => b.deferralSensitivity === 'High deferral sensitivity').length,
  prioritizeCount: MOCK_BRIDGES.filter(b => b.deferralSensitivity === 'Prioritize before deferral').length,
  monitorCount: MOCK_BRIDGES.filter(b => b.deferralSensitivity === 'Monitor').length,
  stableCount: MOCK_BRIDGES.filter(b => b.deferralSensitivity === 'Stable under modeled assumptions').length,
  urgentTransitions: MOCK_DEFERRAL_ANALYSIS.filter(a => a.transitionThresholdExceeded),
  total2YearCostPenaltyCr: Number(MOCK_DEFERRAL_ANALYSIS.reduce((sum, a) => sum + a.costEscalationCr, 0).toFixed(2))
};
