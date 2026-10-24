/**
 * Phase 19: Typed Contracts for Bridge Deterioration Risk Scoring API
 * Risk-Aware Bridge Maintenance Intelligence Platform
 *
 * Enforces the exact 26-feature schema and inference payload of backend/score_bridge_risk.py.
 */

export interface BridgeScoringRecord {
  // Optional identifier
  bridge_id?: string;

  // 13 Numeric Features
  prior_deck_condition: number;
  structure_len_mt: number;
  max_span_len_mt: number;
  deck_width_mt: number;
  traffic_lanes_on: number;
  adt: number;
  percent_adt_truck: number;
  detour_kilos: number;
  year_built: number;
  structure_age_at_inspection: number;
  prior_inspect_month: number;
  prior_inspect_year: number;
  inspect_freq_months: number;

  // 13 Categorical Features (as strings)
  prior_superstructure_condition: string;
  prior_substructure_condition: string;
  prior_culvert_condition: string;
  structure_kind_043a: string;
  structure_type_043b: string;
  deck_structure_type_107: string;
  surface_type_108a: string;
  membrane_type_108b: string;
  deck_protection_108c: string;
  functional_class: string;
  maintenance_responsibility: string;
  owner: string;
  state_code: string;

  // Allow arbitrary additional metadata without error
  [key: string]: any;
}

export interface ModelMetadata {
  classifier_type: string;
  calibrator_type: string;
  target_name: string;
  features_count: number;
  service_phase?: string;
  version?: string;
}

export interface FeatureAttribution {
  feature: string;
  label: string;
  category: string;
  unit: string;
  actual_value: any;
  baseline_value: any;
  delta_score: number;
  delta_prob: number;
  direction: 'INCREASES_RISK' | 'DECREASES_RISK' | 'NEUTRAL';
}

export interface CategoryBreakdown {
  category: string;
  contribution_pct: number;
  risk_contribution: number;
}

export interface ExplainabilityResult {
  bridge_id?: string;
  target_prediction: {
    calibrated_deterioration_probability: number;
    raw_decision_score: number;
  };
  baseline_reference: {
    calibrated_deterioration_probability: number;
    raw_decision_score: number;
  };
  category_breakdown: CategoryBreakdown[];
  top_drivers: FeatureAttribution[];
  all_attributions: FeatureAttribution[];
  methodology: {
    algorithm: string;
    calibrator: string;
    baseline_type: string;
    interpretation: string;
  };
}

export interface BridgeScoringResult {
  bridge_id?: string;
  raw_decision_score: number;
  calibrated_deterioration_probability: number;
  prediction_semantics: string;
  model_metadata: ModelMetadata;
  warnings: string[];
  explanation?: ExplainabilityResult;
}

export interface BatchScoringResponse {
  count: number;
  results: BridgeScoringResult[];
}

export interface HealthCheckResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  service: string;
  phase: string;
  model_ready: boolean;
  classifier_type: string;
  calibrator_type: string;
  features_count: number;
  target_semantics: string;
}

export interface ScientificDisclaimers {
  no_collapse_prediction: string;
  no_engineering_replacement: string;
  validation_scope: string;
  separation_of_concerns: string;
}

export interface FeatureSchema {
  all_features_ordered: string[];
  total_count: number;
  numeric_features: string[];
  categorical_features: string[];
}

export interface ModelMetadataResponse {
  model_type: string;
  target_name: string;
  target_semantics: string;
  scientific_disclaimers: ScientificDisclaimers;
  feature_schema: FeatureSchema;
  service_version: string;
}

export interface SampleBridgeRecord {
  bridge_id: string;
  input_record: BridgeScoringRecord;
  verified_raw_score: number;
  verified_calibrated_probability: number;
}

export interface SampleRecordsResponse {
  count: number;
  samples: SampleBridgeRecord[];
}
