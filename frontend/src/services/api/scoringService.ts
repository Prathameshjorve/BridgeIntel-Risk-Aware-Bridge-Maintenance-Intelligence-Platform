/**
 * Phase 19: Inference-Only Bridge Risk Scoring Client Service
 * Risk-Aware Bridge Maintenance Intelligence Platform
 *
 * Connects frontend workflows to the backend Flask API (/api/score, /api/health, etc.).
 * Configurable via VITE_API_BASE_URL environment variable with fallback to '/api'.
 */

import {
  BridgeScoringRecord,
  BridgeScoringResult,
  BatchScoringResponse,
  HealthCheckResponse,
  ModelMetadataResponse,
  SampleRecordsResponse,
} from '../../types/scoring';
import { BridgeAsset } from '../../types/bridge';

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/+$/, '');

/**
 * Maps a BridgeAsset entity to a valid 26-feature BridgeScoringRecord.
 */
export function mapBridgeAssetToScoringRecord(b: BridgeAsset): BridgeScoringRecord {
  const len = b.totalLengthMeters || 45.0;
  return {
    bridge_id: b.id,
    prior_deck_condition: b.condition?.deck ?? 6.0,
    structure_len_mt: len,
    max_span_len_mt: b.maxSpanMeters || 15.0,
    deck_width_mt: b.deckAreaSqM ? Number((b.deckAreaSqM / len).toFixed(1)) : 9.5,
    traffic_lanes_on: 2,
    adt: b.adt || 4500,
    percent_adt_truck: b.adttPercent || 12.0,
    detour_kilos: b.detourLengthKm || 8.0,
    year_built: b.yearBuilt || 1974,
    structure_age_at_inspection: b.ageYears || 50.0,
    prior_inspect_month: 6,
    prior_inspect_year: 2023,
    inspect_freq_months: 24,
    prior_superstructure_condition: b.condition?.superstructure ? String(b.condition.superstructure) : '6',
    prior_substructure_condition: b.condition?.substructure ? String(b.condition.substructure) : '6',
    prior_culvert_condition: 'N',
    structure_kind_043a: '1',
    structure_type_043b: '02',
    deck_structure_type_107: '1',
    surface_type_108a: '1',
    membrane_type_108b: '0',
    deck_protection_108c: '0',
    functional_class: '06',
    maintenance_responsibility: '01',
    owner: '01',
    state_code: '01',
  };
}

class ScoringServiceError extends Error {
  statusCode?: number;
  errorType?: string;
  details?: any;

  constructor(message: string, statusCode?: number, errorType?: string, details?: any) {
    super(message);
    this.name = 'ScoringServiceError';
    this.statusCode = statusCode;
    this.errorType = errorType;
    this.details = details;
  }
}

async function handleResponse<T>(res: Response): Promise<T> {
  const contentType = res.headers.get('content-type') || '';
  const isJson = contentType.includes('application/json');

  if (!res.ok) {
    if (isJson) {
      const errData = await res.json().catch(() => ({}));
      const message = errData.message || `Request failed with status ${res.status}`;
      throw new ScoringServiceError(message, res.status, errData.error, errData);
    }
    const text = await res.text().catch(() => '');
    throw new ScoringServiceError(
      text || `Server returned error status ${res.status}`,
      res.status,
      'http_error'
    );
  }

  if (isJson) {
    return (await res.json()) as T;
  }
  return {} as T;
}

export const scoringService = {
  /**
   * Health check verifying API connectivity and model artifact loading.
   */
  async checkHealth(): Promise<HealthCheckResponse> {
    try {
      const res = await fetch(`${API_BASE_URL}/health`, {
        method: 'GET',
        headers: { 'Accept': 'application/json' },
      });
      return await handleResponse<HealthCheckResponse>(res);
    } catch (err: any) {
      if (err instanceof ScoringServiceError) throw err;
      throw new ScoringServiceError(
        `Unable to connect to scoring service at ${API_BASE_URL}. Ensure backend Flask server is running.`,
        0,
        'connection_error'
      );
    }
  },

  /**
   * Fetches model metadata, schema, and scientific disclaimers.
   */
  async getModelMetadata(): Promise<ModelMetadataResponse> {
    const res = await fetch(`${API_BASE_URL}/model/metadata`, {
      method: 'GET',
      headers: { 'Accept': 'application/json' },
    });
    return await handleResponse<ModelMetadataResponse>(res);
  },

  /**
   * Retrieves authentic verified sample records from regression fixtures.
   */
  async getSampleRecords(): Promise<SampleRecordsResponse> {
    const res = await fetch(`${API_BASE_URL}/sample-records`, {
      method: 'GET',
      headers: { 'Accept': 'application/json' },
    });
    return await handleResponse<SampleRecordsResponse>(res);
  },

  /**
   * Scores a single bridge record containing the 26 required NBI features.
   * Returns calibrated 2-year deterioration probability and raw decision score.
   */
  async scoreBridge(record: BridgeScoringRecord, explain: boolean = true): Promise<BridgeScoringResult> {
    try {
      const url = explain ? `${API_BASE_URL}/score?explain=true` : `${API_BASE_URL}/score`;
      const res = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify({ record, explain }),
      });
      return await handleResponse<BridgeScoringResult>(res);
    } catch (err: any) {
      if (err instanceof ScoringServiceError) throw err;
      throw new ScoringServiceError(
        `Failed to reach scoring endpoint. Ensure backend server is running on ${API_BASE_URL}.`,
        0,
        'network_error'
      );
    }
  },

  /**
   * Dedicated explainability endpoint providing local counterfactual feature attributions.
   */
  async explainBridge(record: BridgeScoringRecord): Promise<any> {
    try {
      const res = await fetch(`${API_BASE_URL}/explain`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify({ record }),
      });
      return await handleResponse<any>(res);
    } catch (err: any) {
      if (err instanceof ScoringServiceError) throw err;
      throw new ScoringServiceError(
        `Failed to reach explain endpoint. ${err?.message || ''}`,
        0,
        'network_error'
      );
    }
  },

  /**
   * Global feature importance rankings from Phase 17 Permutation Importance.
   */
  async getFeatureImportances(): Promise<any> {
    try {
      const res = await fetch(`${API_BASE_URL}/model/feature-importance`, {
        method: 'GET',
        headers: { 'Accept': 'application/json' },
      });
      return await handleResponse<any>(res);
    } catch (err: any) {
      if (err instanceof ScoringServiceError) throw err;
      throw new ScoringServiceError(
        `Failed to reach feature-importance endpoint. ${err?.message || ''}`,
        0,
        'network_error'
      );
    }
  },

  /**
   * Scores a batch of bridge records.
   */
  async scoreBatch(records: BridgeScoringRecord[]): Promise<BatchScoringResponse> {
    try {
      const res = await fetch(`${API_BASE_URL}/score/batch`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify({ records }),
      });
      return await handleResponse<BatchScoringResponse>(res);
    } catch (err: any) {
      if (err instanceof ScoringServiceError) throw err;
      throw new ScoringServiceError(
        `Failed to execute batch scoring. ${err?.message || ''}`,
        0,
        'network_error'
      );
    }
  },
};
