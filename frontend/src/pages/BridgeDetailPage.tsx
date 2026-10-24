import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { bridgeService } from '../services/api/bridgeService';
import { BridgeAsset } from '../types/bridge';
import { RiskBadge } from '../components/common/RiskBadge';
import { PriorityBadge } from '../components/common/PriorityBadge';
import { ConditionBadge } from '../components/common/ConditionBadge';
import { ExplanationPanel } from '../components/common/ExplanationPanel';
import { ConditionTrendChart } from '../components/charts/ConditionTrendChart';
import { LiveDeteriorationScorer } from '../components/common/LiveDeteriorationScorer';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import { 
  ArrowLeft, 
  MapPin, 
  Calendar, 
  Truck, 
  Compass, 
  AlertTriangle, 
  TrendingDown, 
  Clock, 
  ShieldAlert, 
  CheckCircle2, 
  CornerDownRight
} from 'lucide-react';

export const BridgeDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [bridge, setBridge] = useState<BridgeAsset | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadBridge = async () => {
    if (!id) return;
    try {
      setLoading(true);
      setError(null);
      const data = await bridgeService.getBridgeById(id);
      if (!data) {
        setError(`Bridge record "${id}" was not found in the inventory registry.`);
      } else {
        setBridge(data);
      }
    } catch (err: any) {
      setError(err?.message || "Failed to load bridge structural dossier");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadBridge();
  }, [id]);

  if (loading) return <LoadingState message={`Fetching structural inspection and telemetry dossier for ${id}...`} />;
  if (error || !bridge) return <ErrorState message={error || "Bridge not found"} onRetry={loadBridge} />;

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Back button & Breadcrumb */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => navigate(-1)}
          className="inline-flex items-center gap-1.5 text-xs font-mono text-slate-400 hover:text-slate-200 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Back to Asset Registry
        </button>
        <span className="text-[11px] font-mono text-slate-500">NBI DATA STANDARD COMPLIANT</span>
      </div>

      {/* Main Dossier Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
        <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="font-mono text-base font-bold text-sky-400">{bridge.id}</span>
              <ConditionBadge category={bridge.conditionCategory} rating={bridge.condition.overallCondition} />
              <RiskBadge level={bridge.riskCategory} score={bridge.modeledRiskScore} />
              <PriorityBadge level={bridge.priorityLevel} score={bridge.priorityScore} />
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-100">{bridge.name}</h1>
            <div className="flex flex-wrap items-center gap-4 text-xs text-slate-400 mt-2">
              <span className="flex items-center gap-1">
                <MapPin className="w-3.5 h-3.5 text-slate-500" />
                {bridge.route} • {bridge.county}, {bridge.state}
              </span>
              <span className="flex items-center gap-1 font-mono">
                <Compass className="w-3.5 h-3.5 text-slate-500" />
                {bridge.latitude.toFixed(4)}°N, {Math.abs(bridge.longitude).toFixed(4)}°W
              </span>
              <span className="flex items-center gap-1">
                <Calendar className="w-3.5 h-3.5 text-slate-500" />
                Built {bridge.yearBuilt} ({bridge.ageYears} years in service)
              </span>
            </div>
          </div>

          <div className="flex flex-col md:items-end gap-2 shrink-0">
            <span className="text-xs font-mono text-slate-400">Recommended Intervention</span>
            <div className="px-3 py-1.5 rounded-md bg-sky-950/60 border border-sky-800 text-sky-300 font-semibold text-xs">
              {bridge.recommendedAction}
            </div>
            <span className="text-xs font-mono text-slate-400">
              Parametric Cost: <strong className="text-slate-100">₹{bridge.estimatedInterventionCostCr.toFixed(1)} Cr</strong>
            </span>
          </div>
        </div>
      </div>

      {/* Grid: Profile and Condition */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Section A: Bridge Physical Profile */}
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-5">
          <h3 className="text-sm font-semibold text-slate-200 mb-3 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-sky-400" />
            Section A: Physical Specifications & Exposure
          </h3>
          <div className="grid grid-cols-2 gap-4 text-xs">
            <div className="p-3 bg-slate-950/60 rounded border border-slate-800/80">
              <span className="text-slate-400 block mb-1">Superstructure Type</span>
              <span className="font-medium text-slate-200">{bridge.bridgeType}</span>
            </div>
            <div className="p-3 bg-slate-950/60 rounded border border-slate-800/80">
              <span className="text-slate-400 block mb-1">Feature Intersected</span>
              <span className="font-medium text-slate-200">{bridge.featureIntersected}</span>
            </div>
            <div className="p-3 bg-slate-950/60 rounded border border-slate-800/80">
              <span className="text-slate-400 block mb-1">Total Length / Max Span</span>
              <span className="font-mono text-slate-200">{bridge.totalLengthMeters}m total / {bridge.maxSpanMeters}m max span</span>
            </div>
            <div className="p-3 bg-slate-950/60 rounded border border-slate-800/80">
              <span className="text-slate-400 block mb-1">Deck Area</span>
              <span className="font-mono text-slate-200">{bridge.deckAreaSqM.toLocaleString()} m²</span>
            </div>
            <div className="p-3 bg-slate-950/60 rounded border border-slate-800/80">
              <span className="text-slate-400 block mb-1">Average Daily Traffic (ADT)</span>
              <span className="font-mono font-bold text-slate-100">{bridge.adt.toLocaleString()} vehicles/day</span>
            </div>
            <div className="p-3 bg-slate-950/60 rounded border border-slate-800/80">
              <span className="text-slate-400 block mb-1">Heavy Freight Truck Share</span>
              <span className="font-mono font-bold text-amber-400">{bridge.adttPercent}% ADTT</span>
            </div>
          </div>
        </div>

        {/* Section B: Current Condition & NBI Rating */}
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
              Section B: NBI Component Condition Ratings (0-9 Scale)
            </h3>
            <span className="text-xs font-mono text-slate-400">Min Rating: {bridge.condition.overallCondition}/9</span>
          </div>

          <div className="grid grid-cols-3 gap-3 mb-4 font-mono text-center">
            <div className="p-3 bg-slate-950/80 rounded border border-slate-800">
              <span className="text-[10px] text-slate-400 uppercase">Deck Item 58</span>
              <div className="text-xl font-bold text-sky-400 mt-1">{bridge.condition.deck}/9</div>
              <span className="text-[10px] text-slate-400 mt-1 block">Wearing & Slab</span>
            </div>
            <div className="p-3 bg-slate-950/80 rounded border border-slate-800">
              <span className="text-[10px] text-slate-400 uppercase">Super Item 59</span>
              <div className="text-xl font-bold text-sky-400 mt-1">{bridge.condition.superstructure}/9</div>
              <span className="text-[10px] text-slate-400 mt-1 block">Girders & Bearings</span>
            </div>
            <div className="p-3 bg-slate-950/80 rounded border border-slate-800">
              <span className="text-[10px] text-slate-400 uppercase">Sub Item 60</span>
              <div className="text-xl font-bold text-sky-400 mt-1">{bridge.condition.substructure}/9</div>
              <span className="text-[10px] text-slate-400 mt-1 block">Piers & Abutments</span>
            </div>
          </div>

          <div className="text-xs">
            <span className="text-slate-400 font-mono text-[11px] block mb-2">Historical Longitudinal Condition & Modeled Risk Trend:</span>
            <ConditionTrendChart inspections={bridge.historicalInspections} />
          </div>
        </div>
      </div>

      {/* Grid: Risk Assessment and Network Impact */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Section C: Risk Assessment & Explainability */}
        <div className="space-y-4">
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-5">
            <h3 className="text-sm font-semibold text-slate-200 mb-2 flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-rose-400" />
              Section C: Modeled Deterioration & Risk Profile
            </h3>
            <p className="text-xs text-slate-400 mb-4">
              Risk score combines multi-year degradation trajectory with stress cycle accumulation.
            </p>

            <div className="grid grid-cols-3 gap-3 p-3 rounded bg-slate-950/80 border border-slate-800 mb-4 font-mono text-xs">
              <div>
                <span className="text-[10px] text-slate-500 uppercase block">Modeled Risk</span>
                <span className="text-lg font-bold text-rose-400">{bridge.modeledRiskScore.toFixed(1)}/100</span>
              </div>
              <div>
                <span className="text-[10px] text-slate-500 uppercase block">95% Conf. Interval</span>
                <span className="text-xs text-slate-300 font-semibold mt-1 block">
                  [{bridge.confidenceInterval[0]}, {bridge.confidenceInterval[1]}]
                </span>
              </div>
              <div>
                <span className="text-[10px] text-slate-500 uppercase block">Annual Decline</span>
                <span className="text-xs text-amber-400 font-semibold mt-1 block">
                  {bridge.projectedAnnualDeteriorationRate} pts/yr
                </span>
              </div>
            </div>

            <ExplanationPanel 
              factors={bridge.riskFactors} 
              totalScore={bridge.modeledRiskScore}
            />
          </div>

          {/* Live REST API Deterioration Risk Scorer */}
          <LiveDeteriorationScorer bridge={bridge} />
        </div>

        {/* Section D: Public & Network Consequence */}
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-5 flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-semibold text-slate-200 mb-2 flex items-center gap-2">
              <Truck className="w-4 h-4 text-amber-400" />
              Section D: Public & Network Consequence Burden
            </h3>
            <p className="text-xs text-slate-400 mb-4">
              Evaluates regional disruption in the event of load-posting or closure.
            </p>

            <div className="space-y-3 text-xs">
              <div className="p-3 bg-slate-950/60 rounded border border-slate-800/80 flex items-center justify-between">
                <div>
                  <span className="text-slate-400">Detour Bypass Distance</span>
                  <p className="text-[11px] text-slate-500">Additional mileage required if bridge is closed</p>
                </div>
                <span className="font-mono font-bold text-slate-200 text-sm">{bridge.detourLengthKm} km</span>
              </div>

              <div className="p-3 bg-slate-950/60 rounded border border-slate-800/80 flex items-center justify-between">
                <div>
                  <span className="text-slate-400">Daily Detour Delay Burden</span>
                  <p className="text-[11px] text-slate-500">Aggregate daily vehicular delay across rerouted traffic</p>
                </div>
                <span className="font-mono font-bold text-amber-400 text-sm">
                  {bridge.dailyDetourDelayVehicleHours.toLocaleString()} veh-hrs/day
                </span>
              </div>

              <div className="p-3 bg-slate-950/60 rounded border border-slate-800/80 flex items-center justify-between">
                <div>
                  <span className="text-slate-400">Bypass Corridor Viability</span>
                  <p className="text-[11px] text-slate-500">Capacity of alternate local roads to handle diverted freight</p>
                </div>
                <span className={`font-semibold px-2 py-0.5 rounded text-[11px] ${
                  bridge.bypassViability === 'Severe Bottleneck' 
                    ? 'bg-rose-950 text-rose-300 border border-rose-800' 
                    : 'bg-slate-800 text-slate-300'
                }`}>
                  {bridge.bypassViability}
                </span>
              </div>

              <div className="p-3 bg-slate-950/60 rounded border border-slate-800/80">
                <span className="text-slate-400 block mb-1">Directly Dependent Critical Infrastructure</span>
                {bridge.criticalFacilitiesConnected.length > 0 ? (
                  <ul className="space-y-1">
                    {bridge.criticalFacilitiesConnected.map((fac, idx) => (
                      <li key={idx} className="flex items-center gap-2 text-slate-300 font-medium">
                        <CornerDownRight className="w-3 h-3 text-sky-400" />
                        {fac}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <span className="text-slate-500 italic">No primary trauma or hazardous materials corridors directly dependent.</span>
                )}
              </div>
            </div>
          </div>

          <div className="mt-4 p-3 bg-slate-950/80 rounded border border-slate-800 flex items-center justify-between text-xs font-mono">
            <span className="text-slate-400">Net Consequence Score:</span>
            <span className="text-base font-bold text-amber-400">{bridge.consequenceScore.toFixed(1)} / 100</span>
          </div>
        </div>
      </div>

      {/* Section E: Maintenance Deferral & Recommendation */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-5">
        <h3 className="text-sm font-semibold text-slate-200 mb-2 flex items-center gap-2">
          <Clock className="w-4 h-4 text-sky-400" />
          Section E: Maintenance Recommendation & 2-Year Deferral Cost-of-Delay
        </h3>
        <p className="text-xs text-slate-400 mb-4">
          Decision engine synthesis integrating urgency, expected intervention risk reduction, and future cost penalties under deferred capital allocation.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-xs mb-4">
          <div className="p-3 bg-slate-950/80 rounded border border-slate-800">
            <span className="text-slate-400 block">Current Modeled Risk</span>
            <span className="text-base font-mono font-bold text-slate-200 mt-1 block">{bridge.modeledRiskScore.toFixed(1)}</span>
          </div>
          <div className="p-3 bg-slate-950/80 rounded border border-slate-800">
            <span className="text-slate-400 block">Projected 1-Year Risk</span>
            <span className="text-base font-mono font-bold text-amber-400 mt-1 block">{bridge.deferralRisk1Year.toFixed(1)}</span>
          </div>
          <div className="p-3 bg-slate-950/80 rounded border border-slate-800">
            <span className="text-slate-400 block">Projected 2-Year Risk</span>
            <span className="text-base font-mono font-bold text-rose-400 mt-1 block">{bridge.deferralRisk2Year.toFixed(1)}</span>
          </div>
          <div className="p-3 bg-slate-950/80 rounded border border-slate-800">
            <span className="text-slate-400 block">Cost-of-Delay Escalator</span>
            <span className="text-base font-mono font-bold text-rose-400 mt-1 block">{bridge.costOfDelayMultiplier2Year}x (₹{(bridge.estimatedInterventionCostCr * bridge.costOfDelayMultiplier2Year).toFixed(1)} Cr)</span>
          </div>
        </div>

        <div className="p-4 rounded bg-slate-950/80 border border-slate-800 text-xs space-y-2">
          <div className="flex items-center gap-2 text-sky-400 font-semibold">
            <CheckCircle2 className="w-4 h-4" />
            Decision Engine Rationale:
          </div>
          <p className="text-slate-300 leading-relaxed">
            {bridge.deferralNarrative}
          </p>
          <div className="pt-2 text-[11px] text-slate-500 flex items-center gap-1">
            <span>Intervention Category:</span>
            <strong className="text-slate-300">{bridge.recommendedAction}</strong>
            <span className="mx-2">•</span>
            <span>Expected Immediate Risk Reduction:</span>
            <strong className="text-emerald-400">-{bridge.expectedRiskReductionScore} pts</strong>
          </div>
        </div>
      </div>
    </div>
  );
};
