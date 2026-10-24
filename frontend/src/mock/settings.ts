import { SystemSettings } from '../types/settings';

export const DEFAULT_SYSTEM_SETTINGS: SystemSettings = {
  weights: {
    structuralRisk: 0.35,
    trafficExposure: 0.20,
    networkCriticality: 0.25,
    deferralUrgency: 0.20
  },
  budgetCapCr: 55.0,
  planningHorizonYears: 2,
  currencyUnit: 'INR (Crores)',
  dataSourceMode: 'Simulation / Demo Mode',
  riskThresholdCritical: 75
};
