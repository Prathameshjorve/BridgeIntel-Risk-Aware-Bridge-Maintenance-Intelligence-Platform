export type ConditionCategory = 'Good' | 'Fair' | 'Poor' | 'Critical';
export type RiskLevel = 'Low' | 'Moderate' | 'High' | 'Critical';
export type PriorityLevel = 'Urgent' | 'High' | 'Medium' | 'Routine' | 'Deferred';
export type DeferralSensitivity = 
  | 'Stable under modeled assumptions' 
  | 'Monitor' 
  | 'Prioritize before deferral' 
  | 'High deferral sensitivity';

export interface ComponentConditions {
  deck: number; // NBI scale 0-9
  superstructure: number; // NBI scale 0-9
  substructure: number; // NBI scale 0-9
  culvert?: number; // NBI scale 0-9
  overallCondition: number; // min(deck, super, sub)
}

export interface HistoricalInspection {
  year: number;
  conditionRating: number;
  modeledRiskScore: number;
  actionTaken?: string;
}

export interface RiskFactorAttribution {
  factor: string;
  contributionPercent: number; // e.g. 35
  description: string;
  category: 'Structural' | 'Traffic' | 'Network' | 'Aging';
}

export interface BridgeAsset {
  id: string; // e.g., "NBI-US40-0291"
  name: string; // "Passaic River Crossing"
  route: string; // "US Route 40"
  featureIntersected: string; // "Passaic River / Rail Corridor"
  state: string;
  county: string;
  latitude: number;
  longitude: number;
  yearBuilt: number;
  ageYears: number;
  bridgeType: string; // e.g. "Steel Continuous Beam", "Prestressed Concrete Girder"
  totalLengthMeters: number;
  maxSpanMeters: number;
  deckAreaSqM: number;
  
  // Traffic Exposure
  adt: number; // Average Daily Traffic
  adttPercent: number; // Average Daily Truck Traffic %
  detourLengthKm: number; // Bypass detour distance
  bypassViability: 'Immediate Alternate' | 'Constrained Detour' | 'Severe Bottleneck';

  // NBI Condition
  condition: ComponentConditions;
  conditionCategory: ConditionCategory;
  historicalInspections: HistoricalInspection[];

  // Risk & Deterioration Metrics (Model Output)
  modeledRiskScore: number; // 0 to 100
  riskCategory: RiskLevel;
  confidenceInterval: [number, number]; // [lower, upper]
  projectedAnnualDeteriorationRate: number; // e.g., -0.22 condition points / year
  riskFactors: RiskFactorAttribution[];

  // Public & Network Consequence Metrics
  networkCriticalityScore: number; // 0 to 100
  criticalFacilitiesConnected: string[]; // e.g., ["County General Trauma I", "Regional Logistics Hub"]
  dailyDetourDelayVehicleHours: number;
  consequenceScore: number; // 0 to 100

  // Decision & Maintenance Metrics
  priorityScore: number; // 0 to 100
  priorityLevel: PriorityLevel;
  urgencyIndex: number; // 0 to 100
  estimatedInterventionCostCr: number; // in INR Crores (or millions, parameterizable)
  recommendedAction: 'Superstructure Replacement' | 'Deck Rehabilitation' | 'Substructure Repair' | 'Routine Preventative' | 'Comprehensive Reconstruction';
  expectedRiskReductionScore: number; // delta in risk if maintained

  // Maintenance Deferral Metrics
  deferralRisk1Year: number;
  deferralRisk2Year: number;
  deferralSensitivity: DeferralSensitivity;
  costOfDelayMultiplier2Year: number; // e.g. 1.8x if delayed 24 months
  deferralNarrative: string;
}

export interface PortfolioSummary {
  totalBridges: number;
  highPriorityCount: number;
  criticalRiskCount: number;
  availableBudgetCr: number;
  recommendedAllocationCr: number;
  remainingBudgetCr: number;
  estimatedPortfolioRiskReductionPercent: number;
  averageBridgeAge: number;
  deferralUrgentCount: number;
  dataSourceLabel: 'SIMULATED / DEMO DATA' | 'VERIFIED NBI RECORDS';
}
