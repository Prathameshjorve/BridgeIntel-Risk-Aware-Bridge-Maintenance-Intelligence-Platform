export interface SystemSettings {
  weights: {
    structuralRisk: number; // e.g. 0.35
    trafficExposure: number; // e.g. 0.20
    networkCriticality: number; // e.g. 0.25
    deferralUrgency: number; // e.g. 0.20
  };
  budgetCapCr: number; // Default e.g. 85
  planningHorizonYears: number; // e.g. 2
  currencyUnit: 'INR (Crores)' | 'USD (Millions)';
  dataSourceMode: 'Simulation / Demo Mode' | 'Live NBI Backend Pipeline';
  riskThresholdCritical: number; // e.g. 70
}
