import React, { useState, useEffect } from 'react';
import { scoringService } from '../../services/api/scoringService';
import { BridgeScoringRecord, BridgeScoringResult, SampleBridgeRecord } from '../../types/scoring';
import { BridgeAsset } from '../../types/bridge';
import { 
  Cpu, 
  CheckCircle2, 
  AlertTriangle, 
  RefreshCw, 
  Sliders, 
  ShieldAlert, 
  Info,
  ChevronDown,
  ChevronUp,
  TrendingUp,
  TrendingDown,
  HelpCircle,
  BarChart2,
  Layers
} from 'lucide-react';

interface LiveDeteriorationScorerProps {
  bridge?: BridgeAsset;
}

export const LiveDeteriorationScorer: React.FC<LiveDeteriorationScorerProps> = ({ bridge }) => {
  const [apiConnected, setApiConnected] = useState<boolean | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<BridgeScoringResult | null>(null);
  const [samples, setSamples] = useState<SampleBridgeRecord[]>([]);
  const [showParameters, setShowParameters] = useState<boolean>(false);

  // Default record mapped from bridge or baseline values
  const [activeRecord, setActiveRecord] = useState<BridgeScoringRecord>(() => {
    return {
      bridge_id: bridge?.id || '01_000043660-00015',
      prior_deck_condition: bridge?.condition?.deck ?? 6.0,
      structure_len_mt: bridge?.totalLengthMeters ?? 45.0,
      max_span_len_mt: bridge?.maxSpanMeters ?? 15.0,
      deck_width_mt: bridge?.deckAreaSqM ? Number((bridge.deckAreaSqM / (bridge.totalLengthMeters || 45)).toFixed(1)) : 9.5,
      traffic_lanes_on: 2,
      adt: bridge?.adt ?? 4500,
      percent_adt_truck: bridge?.adttPercent ?? 12.0,
      detour_kilos: bridge?.detourLengthKm ?? 8.0,
      year_built: bridge?.yearBuilt ?? 1974,
      structure_age_at_inspection: bridge?.ageYears ?? 50.0,
      prior_inspect_month: 6,
      prior_inspect_year: 2023,
      inspect_freq_months: 24,
      prior_superstructure_condition: bridge?.condition?.superstructure ? String(bridge.condition.superstructure) : '6',
      prior_substructure_condition: bridge?.condition?.substructure ? String(bridge.condition.substructure) : '6',
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
  });

  // Check health on mount and fetch sample records
  useEffect(() => {
    let isMounted = true;

    async function init() {
      try {
        const health = await scoringService.checkHealth();
        if (isMounted) setApiConnected(health.status === 'healthy');
      } catch {
        if (isMounted) setApiConnected(false);
      }

      try {
        const sampleData = await scoringService.getSampleRecords();
        if (isMounted && sampleData.samples) {
          setSamples(sampleData.samples);
        }
      } catch {
        // Samples endpoint optional if backend offline
      }
    }

    init();
    return () => { isMounted = false; };
  }, []);

  const handleScore = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await scoringService.scoreBridge(activeRecord);
      setResult(res);
      setApiConnected(true);
    } catch (err: any) {
      setError(err?.message || 'Failed to score bridge risk');
      if (err?.errorType === 'connection_error') {
        setApiConnected(false);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSelectSample = (sample: SampleBridgeRecord) => {
    setActiveRecord({ ...sample.input_record, bridge_id: sample.bridge_id });
    setResult(null);
    setError(null);
  };

  const handleNumericChange = (field: keyof BridgeScoringRecord, val: string) => {
    const num = parseFloat(val);
    setActiveRecord(prev => ({
      ...prev,
      [field]: isNaN(num) ? 0 : num
    }));
  };

  const handleCategoricalChange = (field: keyof BridgeScoringRecord, val: string) => {
    setActiveRecord(prev => ({
      ...prev,
      [field]: val
    }));
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-5 shadow-sm space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <Cpu className="w-4 h-4 text-sky-400" />
            <h3 className="text-sm font-bold text-slate-100">Live ML Deterioration Scoring Service</h3>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-sky-950 text-sky-300 border border-sky-800">
              Phase 19 Integration
            </span>
          </div>
          <p className="text-[11px] text-slate-400 mt-0.5">
            Real-time inference using pre-trained HistGradientBoosting + Platt Scaled Calibrator (26 features)
          </p>
        </div>

        {/* API Status Badge */}
        <div className="flex items-center gap-2 self-start sm:self-auto">
          {apiConnected === true && (
            <span className="inline-flex items-center gap-1.5 text-[11px] font-mono px-2.5 py-1 rounded bg-emerald-950/80 text-emerald-400 border border-emerald-800">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              API Connected (:5000)
            </span>
          )}
          {apiConnected === false && (
            <span className="inline-flex items-center gap-1.5 text-[11px] font-mono px-2.5 py-1 rounded bg-amber-950/80 text-amber-400 border border-amber-800" title="Backend Flask server is offline. Run 'python backend/app.py'">
              <span className="w-2 h-2 rounded-full bg-amber-400" />
              API Offline
            </span>
          )}
          <button
            onClick={() => scoringService.checkHealth().then(h => setApiConnected(h.status === 'healthy')).catch(() => setApiConnected(false))}
            title="Refresh API Connection"
            className="p-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-200 transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Target Definition Notice */}
      <div className="p-3 rounded bg-slate-950/80 border border-slate-800/80 text-[11px] flex items-start gap-2.5">
        <Info className="w-4 h-4 text-sky-400 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <p className="text-slate-200 font-medium">
            Verified Target Semantics: <span className="font-mono text-sky-300">DECK_2025 &lt; DECK_2023</span> (Routine Biennial Decline)
          </p>
          <p className="text-slate-400 leading-normal text-[11px]">
            The model outputs the calibrated 2-year probability that the bridge deck condition rating declines by 1 or more points on the FHWA 0–9 ordinal scale.
          </p>
        </div>
      </div>

      {/* Quick Verified Sample Records Selector */}
      {samples.length > 0 && (
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="text-[11px] text-slate-400 font-mono">Load Verified FHWA Record:</span>
          {samples.map((s, idx) => (
            <button
              key={s.bridge_id}
              onClick={() => handleSelectSample(s)}
              className={`px-2 py-1 rounded text-[11px] font-mono transition-colors border ${
                activeRecord.bridge_id === s.bridge_id
                  ? 'bg-sky-900/60 text-sky-200 border-sky-600 font-bold'
                  : 'bg-slate-800 hover:bg-slate-700 text-slate-300 border-slate-700'
              }`}
            >
              Bridge {idx + 1} ({s.bridge_id.slice(-6)})
            </button>
          ))}
        </div>
      )}

      {/* Parameters Inspector Toggle */}
      <div className="pt-1">
        <button
          onClick={() => setShowParameters(!showParameters)}
          className="inline-flex items-center gap-1.5 text-xs font-mono text-slate-400 hover:text-slate-200 transition-colors"
        >
          <Sliders className="w-3.5 h-3.5" />
          <span>{showParameters ? 'Hide 26 Feature Parameters' : 'Inspect / Edit 26 Feature Parameters'}</span>
          {showParameters ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        </button>

        {showParameters && (
          <div className="mt-3 p-3 rounded-lg bg-slate-950/80 border border-slate-800 space-y-3 text-xs font-mono">
            <div>
              <span className="text-[10px] text-sky-400 font-bold uppercase block mb-1.5">13 Numeric Features</span>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
                <div>
                  <label className="text-[10px] text-slate-500 block truncate">prior_deck_condition (0-9)</label>
                  <input
                    type="number"
                    min="0"
                    max="9"
                    step="1"
                    value={activeRecord.prior_deck_condition}
                    onChange={e => handleNumericChange('prior_deck_condition', e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-200 text-xs"
                  />
                </div>
                <div>
                  <label className="text-[10px] text-slate-500 block truncate">structure_len_mt</label>
                  <input
                    type="number"
                    step="0.1"
                    value={activeRecord.structure_len_mt}
                    onChange={e => handleNumericChange('structure_len_mt', e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-200 text-xs"
                  />
                </div>
                <div>
                  <label className="text-[10px] text-slate-500 block truncate">max_span_len_mt</label>
                  <input
                    type="number"
                    step="0.1"
                    value={activeRecord.max_span_len_mt}
                    onChange={e => handleNumericChange('max_span_len_mt', e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-200 text-xs"
                  />
                </div>
                <div>
                  <label className="text-[10px] text-slate-500 block truncate">deck_width_mt</label>
                  <input
                    type="number"
                    step="0.1"
                    value={activeRecord.deck_width_mt}
                    onChange={e => handleNumericChange('deck_width_mt', e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-200 text-xs"
                  />
                </div>
                <div>
                  <label className="text-[10px] text-slate-500 block truncate">adt (vehicles/day)</label>
                  <input
                    type="number"
                    value={activeRecord.adt}
                    onChange={e => handleNumericChange('adt', e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-200 text-xs"
                  />
                </div>
                <div>
                  <label className="text-[10px] text-slate-500 block truncate">percent_adt_truck (%)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={activeRecord.percent_adt_truck}
                    onChange={e => handleNumericChange('percent_adt_truck', e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-200 text-xs"
                  />
                </div>
                <div>
                  <label className="text-[10px] text-slate-500 block truncate">detour_kilos (km)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={activeRecord.detour_kilos}
                    onChange={e => handleNumericChange('detour_kilos', e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-200 text-xs"
                  />
                </div>
                <div>
                  <label className="text-[10px] text-slate-500 block truncate">year_built</label>
                  <input
                    type="number"
                    value={activeRecord.year_built}
                    onChange={e => handleNumericChange('year_built', e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-200 text-xs"
                  />
                </div>
              </div>
            </div>

            <div>
              <span className="text-[10px] text-emerald-400 font-bold uppercase block mb-1.5">Selected Categorical Codes (13 Total)</span>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                <div>
                  <label className="text-[10px] text-slate-500 block truncate">superstructure (0-9, N)</label>
                  <input
                    type="text"
                    value={activeRecord.prior_superstructure_condition}
                    onChange={e => handleCategoricalChange('prior_superstructure_condition', e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-200 text-xs"
                  />
                </div>
                <div>
                  <label className="text-[10px] text-slate-500 block truncate">substructure (0-9, N)</label>
                  <input
                    type="text"
                    value={activeRecord.prior_substructure_condition}
                    onChange={e => handleCategoricalChange('prior_substructure_condition', e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-200 text-xs"
                  />
                </div>
                <div>
                  <label className="text-[10px] text-slate-500 block truncate">structure_type_043b</label>
                  <input
                    type="text"
                    value={activeRecord.structure_type_043b}
                    onChange={e => handleCategoricalChange('structure_type_043b', e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-200 text-xs"
                  />
                </div>
                <div>
                  <label className="text-[10px] text-slate-500 block truncate">state_code</label>
                  <input
                    type="text"
                    value={activeRecord.state_code}
                    onChange={e => handleCategoricalChange('state_code', e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-200 text-xs"
                  />
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Action Button */}
      <div>
        <button
          onClick={handleScore}
          disabled={loading}
          className="w-full sm:w-auto px-5 py-2.5 rounded-md bg-sky-600 hover:bg-sky-500 disabled:bg-slate-800 disabled:text-slate-500 text-white font-medium text-xs transition-colors flex items-center justify-center gap-2 shadow-xs cursor-pointer"
        >
          {loading ? (
            <>
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
              Evaluating Model Inference via REST API...
            </>
          ) : (
            <>
              <Cpu className="w-3.5 h-3.5" />
              Run Live ML Deterioration Inference
            </>
          )}
        </button>
      </div>

      {/* Error State */}
      {error && (
        <div className="p-3.5 rounded-lg bg-rose-950/80 border border-rose-800 text-rose-200 text-xs space-y-1">
          <div className="flex items-center gap-2 font-bold text-rose-300">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>Scoring Request Failed</span>
          </div>
          <p className="leading-relaxed pl-6">{error}</p>
          {apiConnected === false && (
            <div className="mt-2 pl-6 pt-2 border-t border-rose-900 text-[11px] text-rose-300/80 font-mono">
              Tip: Start the backend scoring server with: <code className="bg-rose-900/60 px-1 py-0.5 rounded text-white">python backend/app.py</code>
            </div>
          )}
        </div>
      )}

      {/* Result Display */}
      {result && (
        <div className="p-4 rounded-lg bg-slate-950 border border-sky-800/80 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
            <div className="flex items-center gap-2 text-xs font-semibold text-sky-300">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span>Inference Results ({result.bridge_id || 'Active Record'})</span>
            </div>
            <span className="text-[10px] font-mono text-slate-500">
              {result.model_metadata.classifier_type} • {result.model_metadata.calibrator_type}
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
            <div className="p-3 rounded bg-slate-900 border border-slate-800">
              <span className="text-[10px] font-mono text-slate-400 uppercase block">Calibrated 2-Yr Deterioration Prob</span>
              <div className="text-2xl font-bold font-mono text-amber-400 mt-1">
                {(result.calibrated_deterioration_probability * 100).toFixed(2)}%
              </div>
              <span className="text-[10px] text-slate-500 mt-1 block">
                Platt-calibrated probability of rating drop
              </span>
            </div>

            <div className="p-3 rounded bg-slate-900 border border-slate-800">
              <span className="text-[10px] font-mono text-slate-400 uppercase block">Raw Decision Margin (z)</span>
              <div className="text-2xl font-bold font-mono text-slate-200 mt-1">
                {result.raw_decision_score.toFixed(4)}
              </div>
              <span className="text-[10px] text-slate-500 mt-1 block">
                Classifier uncalibrated logit score
              </span>
            </div>

            <div className="p-3 rounded bg-slate-900 border border-slate-800">
              <span className="text-[10px] font-mono text-slate-400 uppercase block">Features Evaluated</span>
              <div className="text-2xl font-bold font-mono text-sky-400 mt-1">
                {result.model_metadata.features_count} / 26
              </div>
              <span className="text-[10px] text-slate-500 mt-1 block">
                13 numeric + 13 categorical inputs
              </span>
            </div>
          </div>

          {/* Explainable AI Attribution & Risk Driver Breakdown */}
          {result.explanation && (
            <div className="pt-3 border-t border-slate-800 space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <BarChart2 className="w-4 h-4 text-sky-400" />
                  <h4 className="text-xs font-bold text-slate-200">
                    Explainable AI: Counterfactual Factor Decomposition
                  </h4>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-sky-950 text-sky-300 border border-sky-800">
                    Live Marginal Attributions
                  </span>
                </div>
                <div className="text-[11px] font-mono text-slate-400">
                  National Cohort Baseline: {(result.explanation.baseline_reference.calibrated_deterioration_probability * 100).toFixed(2)}%
                </div>
              </div>

              {/* Category Contributions Bar */}
              {result.explanation.category_breakdown && (
                <div className="p-3 rounded bg-slate-900 border border-slate-800 space-y-2">
                  <span className="text-[10px] font-mono text-slate-400 uppercase block">
                    Domain Risk Attribution by Category
                  </span>
                  <div className="w-full bg-slate-950 h-3 rounded-full flex overflow-hidden border border-slate-800">
                    {result.explanation.category_breakdown.map((cat, idx) => {
                      const colors = [
                        'bg-rose-500',
                        'bg-amber-500',
                        'bg-sky-500',
                        'bg-purple-500',
                        'bg-emerald-500',
                      ];
                      return (
                        <div
                          key={cat.category}
                          style={{ width: `${Math.max(2, cat.contribution_pct)}%` }}
                          className={`${colors[idx % colors.length]} transition-all duration-500`}
                          title={`${cat.category}: ${cat.contribution_pct}%`}
                        />
                      );
                    })}
                  </div>
                  <div className="flex flex-wrap items-center gap-3 text-[11px] text-slate-300">
                    {result.explanation.category_breakdown.map((cat, idx) => {
                      const dotColors = [
                        'bg-rose-500',
                        'bg-amber-500',
                        'bg-sky-500',
                        'bg-purple-500',
                        'bg-emerald-500',
                      ];
                      return (
                        <div key={cat.category} className="flex items-center gap-1.5">
                          <span className={`w-2 h-2 rounded-full ${dotColors[idx % dotColors.length]}`} />
                          <span className="text-slate-400">{cat.category}:</span>
                          <span className="font-mono font-bold text-slate-200">{cat.contribution_pct}%</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Top Feature Attributions Table */}
              {result.explanation.top_drivers && (
                <div className="space-y-2">
                  <span className="text-[10px] font-mono text-slate-400 uppercase block">
                    Top Feature Risk Influencers vs. Empirical National Baselines
                  </span>
                  <div className="overflow-x-auto rounded border border-slate-800">
                    <table className="w-full text-left text-[11px] font-mono">
                      <thead className="bg-slate-900/90 text-slate-400 text-[10px] uppercase border-b border-slate-800">
                        <tr>
                          <th className="py-2 px-3">Feature Name</th>
                          <th className="py-2 px-3">Domain</th>
                          <th className="py-2 px-3">Actual Value</th>
                          <th className="py-2 px-3">Cohort Baseline</th>
                          <th className="py-2 px-3">Impact (Δ Prob)</th>
                          <th className="py-2 px-3">Influence</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60 bg-slate-950/60">
                        {result.explanation.top_drivers.map((driver) => (
                          <tr key={driver.feature} className="hover:bg-slate-900/40">
                            <td className="py-2 px-3 text-slate-200 font-sans font-medium">
                              <div>{driver.label}</div>
                              <span className="text-[10px] text-slate-500 font-mono">{driver.feature}</span>
                            </td>
                            <td className="py-2 px-3">
                              <span className="px-1.5 py-0.5 rounded text-[10px] bg-slate-800 text-slate-300">
                                {driver.category}
                              </span>
                            </td>
                            <td className="py-2 px-3 text-slate-200 font-bold">
                              {String(driver.actual_value)} <span className="text-[10px] font-normal text-slate-500">{driver.unit}</span>
                            </td>
                            <td className="py-2 px-3 text-slate-400">
                              {String(driver.baseline_value)}
                            </td>
                            <td className="py-2 px-3 font-bold">
                              <span className={driver.delta_prob > 0 ? 'text-rose-400' : (driver.delta_prob < 0 ? 'text-emerald-400' : 'text-slate-400')}>
                                {driver.delta_prob > 0 ? `+${(driver.delta_prob * 100).toFixed(2)}%` : `${(driver.delta_prob * 100).toFixed(2)}%`}
                              </span>
                            </td>
                            <td className="py-2 px-3">
                              {driver.direction === 'INCREASES_RISK' ? (
                                <span className="inline-flex items-center gap-1 text-[10px] text-rose-400 font-sans">
                                  <TrendingUp className="w-3 h-3 text-rose-400" />
                                  Amplifies Risk
                                </span>
                              ) : driver.direction === 'DECREASES_RISK' ? (
                                <span className="inline-flex items-center gap-1 text-[10px] text-emerald-400 font-sans">
                                  <TrendingDown className="w-3 h-3 text-emerald-400" />
                                  Protective
                                </span>
                              ) : (
                                <span className="text-slate-500 text-[10px] font-sans">Neutral</span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}

          {result.warnings && result.warnings.length > 0 && (
            <div className="p-2.5 rounded bg-amber-950/40 border border-amber-800/60 text-[11px] text-amber-300 space-y-1">
              <span className="font-semibold block">Inference Warnings:</span>
              <ul className="list-disc pl-4 space-y-0.5">
                {result.warnings.map((w, idx) => (
                  <li key={idx}>{w}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Mandatory Scientific Disclaimers */}
      <div className="p-3 rounded bg-slate-950/60 border border-slate-800/60 space-y-2 text-[11px] text-slate-400">
        <div className="flex items-center gap-1.5 font-bold text-amber-400 text-xs">
          <ShieldAlert className="w-3.5 h-3.5" />
          <span>Scientific Boundaries & Governance Disclaimers</span>
        </div>
        <ul className="list-disc pl-4 space-y-1 text-[11px] leading-relaxed">
          <li>
            <strong className="text-slate-300">Target Semantics:</strong> Predicts routine biennial NBI deck condition rating decrease (0–9 scale). Does <em>not</em> predict bridge collapse, catastrophic structural failure, or human safety risk.
          </li>
          <li>
            <strong className="text-slate-300">Decision-Support Role:</strong> This tool is an AI-assisted planning aid. It does <em>not</em> certify structural safety or replace qualified bridge inspection engineers.
          </li>
          <li>
            <strong className="text-slate-300">Separation of Concerns:</strong> Deterioration probabilities are kept strictly isolated from public consequence, detour cost, maintenance cost, and budget knapsack optimization.
          </li>
          <li>
            <strong className="text-slate-300">Validation Scope:</strong> Calibrated on an internal held-out 50% partition of historical FHWA NBI validation records. External geographical and temporal validation has not yet been established.
          </li>
        </ul>
      </div>
    </div>
  );
};
