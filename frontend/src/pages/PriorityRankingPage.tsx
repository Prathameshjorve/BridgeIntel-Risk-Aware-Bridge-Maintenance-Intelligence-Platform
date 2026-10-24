import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { bridgeService } from '../services/api/bridgeService';
import { BridgeAsset } from '../types/bridge';
import { RiskBadge } from '../components/common/RiskBadge';
import { PriorityBadge } from '../components/common/PriorityBadge';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import { ExplanationPanel } from '../components/common/ExplanationPanel';
import { 
  HelpCircle, 
  ExternalLink
} from 'lucide-react';

export const PriorityRankingPage: React.FC = () => {
  const navigate = useNavigate();
  const [bridges, setBridges] = useState<BridgeAsset[]>([]);
  const [selectedBridge, setSelectedBridge] = useState<BridgeAsset | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await bridgeService.getAllBridges();
      const sorted = [...data].sort((a, b) => b.priorityScore - a.priorityScore);
      setBridges(sorted);
      if (sorted.length > 0) {
        setSelectedBridge(sorted[0]);
      }
    } catch (err: any) {
      setError(err?.message || "Failed to load priority matrix");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  if (loading) return <LoadingState message="Executing multi-criteria priority weighting engine..." />;
  if (error) return <ErrorState message={error} onRetry={loadData} />;

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-sky-950 text-sky-400 border border-sky-800">
              PRIORITY ENGINE
            </span>
            <span className="text-xs font-mono text-slate-500">EXPLAINABLE RANKED MATRIX</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-100">
            Bridge Priority Ranking
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Multi-attribute ranking: Structural Risk (35%) + Public Consequence (25%) + Traffic Exposure (20%) + Deferral Urgency (20%)
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Ranked Bridges Table (Left 2 cols) */}
        <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-lg overflow-hidden shadow-sm">
          <div className="p-4 border-b border-slate-800 flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-slate-200">Global Priority Queue</h3>
              <p className="text-xs text-slate-400 mt-0.5">Select any row to inspect decision attribution breakdown</p>
            </div>
            <span className="text-xs font-mono text-slate-400">{bridges.length} Bridges Analyzed</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950/80 text-slate-400 font-mono border-b border-slate-800">
                <tr>
                  <th className="py-3 px-3 text-center">Rank</th>
                  <th className="py-3 px-3">Bridge / Corridor</th>
                  <th className="py-3 px-3">Risk</th>
                  <th className="py-3 px-3">Impact</th>
                  <th className="py-3 px-3">Urgency</th>
                  <th className="py-3 px-3 text-right">Cost</th>
                  <th className="py-3 px-3 text-center">Priority</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {bridges.map((bridge, index) => {
                  const isSelected = selectedBridge?.id === bridge.id;
                  const rank = index + 1;
                  return (
                    <tr
                      key={bridge.id}
                      onClick={() => setSelectedBridge(bridge)}
                      className={`cursor-pointer transition-colors ${
                        isSelected 
                          ? 'bg-sky-950/40 border-l-4 border-sky-500' 
                          : 'hover:bg-slate-800/50'
                      }`}
                    >
                      <td className="py-3 px-3 text-center font-mono font-bold">
                        <span className={`inline-flex items-center justify-center w-6 h-6 rounded-full text-xs ${
                          rank <= 3 ? 'bg-sky-600/30 text-sky-300 border border-sky-500/50' : 'text-slate-400'
                        }`}>
                          {rank}
                        </span>
                      </td>
                      <td className="py-3 px-3">
                        <div className="font-mono font-semibold text-slate-200">{bridge.id}</div>
                        <div className="text-slate-400 text-[11px] truncate max-w-[180px]">{bridge.name}</div>
                      </td>
                      <td className="py-3 px-3">
                        <RiskBadge level={bridge.riskCategory} score={bridge.modeledRiskScore} size="sm" />
                      </td>
                      <td className="py-3 px-3 font-mono font-medium text-slate-300">
                        {bridge.consequenceScore.toFixed(0)}/100
                      </td>
                      <td className="py-3 px-3 font-mono font-medium text-slate-300">
                        {bridge.urgencyIndex.toFixed(0)}/100
                      </td>
                      <td className="py-3 px-3 text-right font-mono font-medium text-slate-200">
                        ₹{bridge.estimatedInterventionCostCr.toFixed(1)} Cr
                      </td>
                      <td className="py-3 px-3 text-center">
                        <span className="font-mono font-bold text-sm text-sky-400">
                          {bridge.priorityScore.toFixed(1)}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Attribution & Explainability Panel (Right col) */}
        <div className="space-y-4">
          {selectedBridge ? (
            <div className="bg-slate-900 border border-slate-800 rounded-lg p-5 space-y-4">
              <div className="border-b border-slate-800 pb-3">
                <span className="text-[10px] font-mono text-slate-400 uppercase">Decision Attribution Inspector</span>
                <div className="flex items-center justify-between mt-1">
                  <h3 className="font-mono font-bold text-lg text-sky-400">{selectedBridge.id}</h3>
                  <PriorityBadge level={selectedBridge.priorityLevel} score={selectedBridge.priorityScore} />
                </div>
                <p className="text-xs text-slate-300 mt-1 font-medium">{selectedBridge.name}</p>
                <p className="text-[11px] text-slate-400">{selectedBridge.route} • {selectedBridge.county}</p>
              </div>

              {/* Mathematical Formulation Explainer */}
              <div className="p-3 rounded bg-slate-950/80 border border-slate-800 text-xs space-y-2">
                <div className="flex items-center gap-1.5 text-sky-400 font-semibold text-[11px]">
                  <HelpCircle className="w-3.5 h-3.5" />
                  Why is this bridge prioritized?
                </div>
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  Composite score incorporates structural deterioration risk, freight consequence, and life-cycle cost penalties if deferred.
                </p>
                <div className="pt-2 border-t border-slate-800/80 font-mono text-[11px] space-y-1">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Risk Component (35%):</span>
                    <span className="text-slate-200">{(selectedBridge.modeledRiskScore * 0.35).toFixed(1)} pts</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Consequence Component (25%):</span>
                    <span className="text-slate-200">{(selectedBridge.consequenceScore * 0.25).toFixed(1)} pts</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Urgency Component (20%):</span>
                    <span className="text-slate-200">{(selectedBridge.urgencyIndex * 0.20).toFixed(1)} pts</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Deferral Penalty (20%):</span>
                    <span className="text-slate-200">{(selectedBridge.deferralRisk2Year * 0.20).toFixed(1)} pts</span>
                  </div>
                  <div className="flex justify-between pt-1 border-t border-slate-800 text-sky-400 font-bold">
                    <span>Total Priority Score:</span>
                    <span>{selectedBridge.priorityScore.toFixed(1)} / 100</span>
                  </div>
                </div>
              </div>

              <ExplanationPanel 
                factors={selectedBridge.riskFactors} 
                totalScore={selectedBridge.priorityScore}
                title="Dominant Drivers"
                subtitle="Primary empirical conditions influencing ranking"
              />

              <button
                onClick={() => navigate(`/bridges/${selectedBridge.id}`)}
                className="w-full py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded text-xs font-medium transition-colors flex items-center justify-center gap-1.5"
              >
                Open Full Asset Dossier
                <ExternalLink className="w-3.5 h-3.5" />
              </button>
            </div>
          ) : (
            <div className="p-8 text-center text-slate-500 text-xs">
              Select a bridge in the ranking matrix to view detailed explainability.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
