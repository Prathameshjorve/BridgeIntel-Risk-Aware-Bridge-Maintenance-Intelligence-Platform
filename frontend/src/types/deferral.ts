import { BridgeAsset, DeferralSensitivity } from './bridge';

export interface DeferralTrajectoryPoint {
  horizonLabel: 'Current' | '+1 Year' | '+2 Years';
  yearOffset: number;
  averageRiskScore: number;
  criticalCount: number;
  projectedPortfolioDegradationCostCr: number;
}

export interface DeferralBridgeAnalysis {
  bridge: BridgeAsset;
  currentRisk: number;
  risk1Year: number;
  risk2Year: number;
  riskDelta2Year: number;
  riskIncreasePercentage: number;
  status: DeferralSensitivity;
  transitionThresholdExceeded: boolean;
  costEscalationCr: number;
  recommendedActionBeforeDeferral: string;
}

export interface DeferralPortfolioReport {
  trajectories: DeferralTrajectoryPoint[];
  highSensitivityCount: number;
  stableCount: number;
  monitorCount: number;
  prioritizeCount: number;
  urgentTransitions: DeferralBridgeAnalysis[];
  total2YearCostPenaltyCr: number;
}
