import React, { useEffect, useState, useMemo } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { bridgeService } from '../services/api/bridgeService';
import { BridgeAsset } from '../types/bridge';
import { RiskBadge } from '../components/common/RiskBadge';
import { PriorityBadge } from '../components/common/PriorityBadge';
import { ConditionBadge } from '../components/common/ConditionBadge';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import { EmptyState } from '../components/common/EmptyState';
import { Search, ArrowUpDown, ArrowUp, ArrowDown, X, ExternalLink, RotateCcw, Cpu, AlertTriangle, RefreshCw } from 'lucide-react';
import { scoringService, mapBridgeAssetToScoringRecord } from '../services/api/scoringService';
import { BridgeScoringResult } from '../types/scoring';

export const BridgePortfolioPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const [bridges, setBridges] = useState<BridgeAsset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters State
  const [searchQuery, setSearchQuery] = useState(searchParams.get('search') || '');
  const [selectedRisk, setSelectedRisk] = useState<string>('All');
  const [selectedCondition, setSelectedCondition] = useState<string>('All');
  const [selectedPriority, setSelectedPriority] = useState<string>('All');
  const [selectedAction, setSelectedAction] = useState<string>('All');
  const [sortField, setSortField] = useState<keyof BridgeAsset>('priorityScore');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');

  // Quick Inspection Drawer
  const [inspectedBridge, setInspectedBridge] = useState<BridgeAsset | null>(null);
  const [drawerScoringResult, setDrawerScoringResult] = useState<BridgeScoringResult | null>(null);
  const [drawerScoringLoading, setDrawerScoringLoading] = useState(false);
  const [drawerScoringError, setDrawerScoringError] = useState<string | null>(null);

  useEffect(() => {
    setDrawerScoringResult(null);
    setDrawerScoringError(null);
  }, [inspectedBridge]);

  const handleScoreInspectedBridge = async () => {
    if (!inspectedBridge) return;
    setDrawerScoringLoading(true);
    setDrawerScoringError(null);
    try {
      const rec = mapBridgeAssetToScoringRecord(inspectedBridge);
      const res = await scoringService.scoreBridge(rec);
      setDrawerScoringResult(res);
    } catch (err: any) {
      setDrawerScoringError(err?.message || "Failed to score bridge risk via API");
    } finally {
      setDrawerScoringLoading(false);
    }
  };

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await bridgeService.getAllBridges();
      setBridges(data);
    } catch (err: any) {
      setError(err?.message || "Failed to load bridge inventory records");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Sync url param if search changes externally
  useEffect(() => {
    const q = searchParams.get('search');
    if (q !== null && q !== searchQuery) {
      setSearchQuery(q);
    }
  }, [searchParams]);

  // Usability: Escape key closes inspection drawer
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && inspectedBridge) {
        setInspectedBridge(null);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [inspectedBridge]);

  const handleSort = (field: keyof BridgeAsset) => {
    if (sortField === field) {
      setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const renderSortIndicator = (field: keyof BridgeAsset) => {
    if (sortField === field) {
      return sortDirection === 'asc' ? (
        <ArrowUp className="w-3.5 h-3.5 text-sky-400 font-bold ml-1" />
      ) : (
        <ArrowDown className="w-3.5 h-3.5 text-sky-400 font-bold ml-1" />
      );
    }
    return <ArrowUpDown className="w-3 h-3 text-slate-500 opacity-60 ml-1" />;
  };

  const filteredBridges = useMemo(() => {
    return bridges.filter(b => {
      const matchesSearch = 
        searchQuery === '' ||
        b.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        b.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        b.route.toLowerCase().includes(searchQuery.toLowerCase()) ||
        b.featureIntersected.toLowerCase().includes(searchQuery.toLowerCase()) ||
        b.county.toLowerCase().includes(searchQuery.toLowerCase());

      const matchesRisk = selectedRisk === 'All' || b.riskCategory === selectedRisk;
      const matchesCondition = selectedCondition === 'All' || b.conditionCategory === selectedCondition;
      const matchesPriority = selectedPriority === 'All' || b.priorityLevel === selectedPriority;
      const matchesAction = selectedAction === 'All' || b.recommendedAction === selectedAction;

      return matchesSearch && matchesRisk && matchesCondition && matchesPriority && matchesAction;
    }).sort((a, b) => {
      let valA: any = a[sortField];
      let valB: any = b[sortField];

      if (typeof valA === 'string') {
        return sortDirection === 'asc' 
          ? valA.localeCompare(valB) 
          : valB.localeCompare(valA);
      }
      return sortDirection === 'asc' ? valA - valB : valB - valA;
    });
  }, [bridges, searchQuery, selectedRisk, selectedCondition, selectedPriority, selectedAction, sortField, sortDirection]);

  const hasActiveFilters = searchQuery !== '' || selectedRisk !== 'All' || selectedCondition !== 'All' || selectedPriority !== 'All' || selectedAction !== 'All';

  const resetFilters = () => {
    setSearchQuery('');
    setSelectedRisk('All');
    setSelectedCondition('All');
    setSelectedPriority('All');
    setSelectedAction('All');
    setSearchParams({});
  };

  if (loading) return <LoadingState message="Loading bridge registry inventory..." />;
  if (error) return <ErrorState message={error} onRetry={loadData} />;

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
              ASSET REGISTRY
            </span>
            <span className="text-xs font-mono text-slate-500">
              Showing {filteredBridges.length} of {bridges.length} structures
            </span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-100">
            Bridge Asset Portfolio
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Comprehensive inventory with NBI structural ratings, modeled risk probabilities, consequence burdens, and deferral status
          </p>
        </div>

        {hasActiveFilters && (
          <div className="flex items-center gap-2">
            <button
              onClick={resetFilters}
              aria-label="Reset all search and filter parameters"
              className="px-3 py-1.5 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 transition-colors flex items-center gap-1.5"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              Reset Filters
            </button>
          </div>
        )}
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 space-y-3">
        <div className="flex flex-col md:flex-row gap-3">
          {/* Search Box */}
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              type="text"
              aria-label="Filter bridges by ID, name, or route"
              placeholder="Search by ID, name, route, or river..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-md pl-9 pr-3 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-sky-500"
            />
          </div>

          {/* Risk Level Filter */}
          <div className="flex items-center gap-2">
            <label htmlFor="filter-risk" className="text-xs text-slate-400 font-mono">Risk:</label>
            <select
              id="filter-risk"
              aria-label="Filter by Risk Category"
              value={selectedRisk}
              onChange={(e) => setSelectedRisk(e.target.value)}
              className="bg-slate-950 border border-slate-800 rounded-md px-2.5 py-2 text-xs text-slate-200 focus:outline-none focus:border-sky-500"
            >
              <option value="All">All Risk Levels</option>
              <option value="Critical">Critical Risk</option>
              <option value="High">High Risk</option>
              <option value="Moderate">Moderate</option>
              <option value="Low">Low Risk</option>
            </select>
          </div>

          {/* Condition Filter */}
          <div className="flex items-center gap-2">
            <label htmlFor="filter-condition" className="text-xs text-slate-400 font-mono">Condition:</label>
            <select
              id="filter-condition"
              aria-label="Filter by Structural Condition Category"
              value={selectedCondition}
              onChange={(e) => setSelectedCondition(e.target.value)}
              className="bg-slate-950 border border-slate-800 rounded-md px-2.5 py-2 text-xs text-slate-200 focus:outline-none focus:border-sky-500"
            >
              <option value="All">All Conditions</option>
              <option value="Good">Good (7-9)</option>
              <option value="Fair">Fair (5-6)</option>
              <option value="Poor">Poor (4)</option>
              <option value="Critical">Critical (0-3)</option>
            </select>
          </div>

          {/* Priority Level */}
          <div className="flex items-center gap-2">
            <label htmlFor="filter-priority" className="text-xs text-slate-400 font-mono">Priority:</label>
            <select
              id="filter-priority"
              aria-label="Filter by Priority Level"
              value={selectedPriority}
              onChange={(e) => setSelectedPriority(e.target.value)}
              className="bg-slate-950 border border-slate-800 rounded-md px-2.5 py-2 text-xs text-slate-200 focus:outline-none focus:border-sky-500"
            >
              <option value="All">All Priorities</option>
              <option value="Urgent">Urgent Intervention</option>
              <option value="High">High Priority</option>
              <option value="Medium">Medium</option>
              <option value="Routine">Routine Cycle</option>
            </select>
          </div>
        </div>
      </div>

      {/* Main Table */}
      {filteredBridges.length === 0 ? (
        <EmptyState onReset={resetFilters} />
      ) : (
        <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950/80 text-slate-400 font-mono border-b border-slate-800 select-none">
                <tr>
                  <th 
                    className="py-3 px-4 cursor-pointer hover:text-slate-100 transition-colors"
                    onClick={() => handleSort('id')}
                    title="Sort by Bridge ID"
                  >
                    <div className="flex items-center">
                      Bridge ID / Name
                      {renderSortIndicator('id')}
                    </div>
                  </th>
                  <th 
                    className="py-3 px-4 cursor-pointer hover:text-slate-100 transition-colors"
                    onClick={() => handleSort('yearBuilt')}
                    title="Sort by Age / Built Year"
                  >
                    <div className="flex items-center">
                      Age / Built
                      {renderSortIndicator('yearBuilt')}
                    </div>
                  </th>
                  <th className="py-3 px-4">Condition</th>
                  <th 
                    className="py-3 px-4 cursor-pointer hover:text-slate-100 transition-colors"
                    onClick={() => handleSort('adt')}
                    title="Sort by Traffic Volume (ADT)"
                  >
                    <div className="flex items-center">
                      Traffic (ADT)
                      {renderSortIndicator('adt')}
                    </div>
                  </th>
                  <th 
                    className="py-3 px-4 cursor-pointer hover:text-slate-100 transition-colors"
                    onClick={() => handleSort('modeledRiskScore')}
                    title="Sort by Modeled Risk Score"
                  >
                    <div className="flex items-center">
                      Modeled Risk
                      {renderSortIndicator('modeledRiskScore')}
                    </div>
                  </th>
                  <th 
                    className="py-3 px-4 cursor-pointer hover:text-slate-100 transition-colors"
                    onClick={() => handleSort('consequenceScore')}
                    title="Sort by Consequence Score"
                  >
                    <div className="flex items-center">
                      Consequence
                      {renderSortIndicator('consequenceScore')}
                    </div>
                  </th>
                  <th 
                    className="py-3 px-4 cursor-pointer hover:text-slate-100 transition-colors"
                    onClick={() => handleSort('priorityScore')}
                    title="Sort by Priority Score"
                  >
                    <div className="flex items-center">
                      Priority Score
                      {renderSortIndicator('priorityScore')}
                    </div>
                  </th>
                  <th 
                    className="py-3 px-4 text-right cursor-pointer hover:text-slate-100 transition-colors"
                    onClick={() => handleSort('estimatedInterventionCostCr')}
                    title="Sort by Estimated Intervention Cost"
                  >
                    <div className="flex items-center justify-end">
                      Cost (Est.)
                      {renderSortIndicator('estimatedInterventionCostCr')}
                    </div>
                  </th>
                  <th className="py-3 px-4">Deferral Sensitivity</th>
                  <th className="py-3 px-4 text-center">Inspect</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {filteredBridges.map((bridge) => (
                  <tr 
                    key={bridge.id} 
                    className="hover:bg-sky-500/5 dark:hover:bg-slate-800/60 cursor-pointer transition-colors"
                    onClick={() => setInspectedBridge(bridge)}
                  >
                    <td className="py-3.5 px-4">
                      <div className="font-mono font-semibold text-sky-400">{bridge.id}</div>
                      <div className="text-slate-200 font-medium truncate max-w-xs">{bridge.name}</div>
                      <div className="text-slate-400 text-[10px]">{bridge.route} • {bridge.county}</div>
                    </td>
                    <td className="py-3.5 px-4 font-mono">
                      <div className="text-slate-200">{bridge.ageYears} yrs</div>
                      <div className="text-slate-400 text-[10px]">Built {bridge.yearBuilt}</div>
                    </td>
                    <td className="py-3.5 px-4">
                      <ConditionBadge category={bridge.conditionCategory} rating={bridge.condition.overallCondition} />
                    </td>
                    <td className="py-3.5 px-4 font-mono">
                      <div className="text-slate-200">{bridge.adt.toLocaleString()} ADT</div>
                      <div className="text-slate-400 text-[10px]">{bridge.adttPercent}% Trucks</div>
                    </td>
                    <td className="py-3.5 px-4">
                      <RiskBadge level={bridge.riskCategory} score={bridge.modeledRiskScore} />
                    </td>
                    <td className="py-3.5 px-4 font-mono font-medium text-slate-200">
                      {bridge.consequenceScore.toFixed(1)}/100
                    </td>
                    <td className="py-3.5 px-4">
                      <PriorityBadge level={bridge.priorityLevel} score={bridge.priorityScore} />
                    </td>
                    <td className="py-3.5 px-4 text-right font-mono font-bold text-slate-100">
                      ₹{bridge.estimatedInterventionCostCr.toFixed(1)} Cr
                    </td>
                    <td className="py-3.5 px-4">
                      <span className={`text-[11px] px-2 py-0.5 rounded font-medium border ${
                        bridge.deferralSensitivity === 'High deferral sensitivity'
                          ? 'bg-rose-50 text-rose-800 border-rose-300 dark:bg-rose-950/60 dark:text-rose-300 dark:border-rose-800'
                          : bridge.deferralSensitivity === 'Prioritize before deferral'
                          ? 'bg-amber-50 text-amber-800 border-amber-300 dark:bg-amber-950/60 dark:text-amber-300 dark:border-amber-800'
                          : 'bg-slate-100 text-slate-600 border-slate-300 dark:bg-slate-800 dark:text-slate-400 dark:border-slate-700'
                      }`}>
                        {bridge.deferralSensitivity}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-center">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate(`/bridges/${bridge.id}`);
                        }}
                        aria-label={`View complete engineering dossier for ${bridge.id}`}
                        title="View Complete Engineering Dossier"
                        className="p-1.5 rounded-md bg-slate-800 hover:bg-sky-600 hover:text-white text-slate-300 border border-slate-700 transition-colors"
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Quick Inspection Drawer with Backdrop */}
      {inspectedBridge && (
        <div className="fixed inset-0 z-40 overflow-hidden">
          {/* Backdrop (click to close) */}
          <div 
            onClick={() => setInspectedBridge(null)}
            className="fixed inset-0 bg-slate-950/60 backdrop-blur-xs transition-opacity"
            aria-hidden="true"
          />

          {/* Drawer Panel */}
          <div 
            role="dialog"
            aria-modal="true"
            aria-label={`Asset preview for ${inspectedBridge.id}`}
            className="fixed inset-y-0 right-0 w-full sm:w-96 bg-slate-900 border-l border-slate-800 p-6 shadow-2xl z-50 flex flex-col justify-between overflow-y-auto"
          >
            <div>
              <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
                <div>
                  <span className="text-[10px] font-mono text-slate-400">QUICK ASSET PREVIEW (ESC TO CLOSE)</span>
                  <h3 className="text-base font-bold font-mono text-sky-400">{inspectedBridge.id}</h3>
                </div>
                <button 
                  onClick={() => setInspectedBridge(null)}
                  aria-label="Close preview drawer"
                  title="Close preview (Esc)"
                  className="p-1.5 rounded-md text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="space-y-4 text-xs">
                <div>
                  <h4 className="font-semibold text-slate-100 text-sm">{inspectedBridge.name}</h4>
                  <p className="text-slate-400 text-[11px] mt-0.5">{inspectedBridge.route} • {inspectedBridge.featureIntersected}</p>
                </div>

                <div className="grid grid-cols-2 gap-2 p-3 rounded-lg bg-slate-950/80 border border-slate-800">
                  <div>
                    <span className="text-slate-400 text-[10px]">Condition</span>
                    <div className="mt-1">
                      <ConditionBadge category={inspectedBridge.conditionCategory} rating={inspectedBridge.condition.overallCondition} />
                    </div>
                  </div>
                  <div>
                    <span className="text-slate-400 text-[10px]">Priority</span>
                    <div className="mt-1">
                      <PriorityBadge level={inspectedBridge.priorityLevel} score={inspectedBridge.priorityScore} />
                    </div>
                  </div>
                </div>

                <div>
                  <span className="text-slate-400 block mb-1">NBI Component Breakdown (0-9):</span>
                  <div className="grid grid-cols-3 gap-2 text-center font-mono">
                    <div className="p-2 bg-slate-950 rounded border border-slate-800">
                      <div className="text-[10px] text-slate-400">Deck</div>
                      <div className="text-sm font-bold text-slate-200">{inspectedBridge.condition.deck}/9</div>
                    </div>
                    <div className="p-2 bg-slate-950 rounded border border-slate-800">
                      <div className="text-[10px] text-slate-400">Super</div>
                      <div className="text-sm font-bold text-slate-200">{inspectedBridge.condition.superstructure}/9</div>
                    </div>
                    <div className="p-2 bg-slate-950 rounded border border-slate-800">
                      <div className="text-[10px] text-slate-400">Sub</div>
                      <div className="text-sm font-bold text-slate-200">{inspectedBridge.condition.substructure}/9</div>
                    </div>
                  </div>
                </div>

                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Traffic Exposure:</span>
                    <span className="font-mono text-slate-200">{inspectedBridge.adt.toLocaleString()} ADT ({inspectedBridge.adttPercent}% Trucks)</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Bypass Detour Length:</span>
                    <span className="font-mono text-slate-200">{inspectedBridge.detourLengthKm} km</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Intervention Cost Est:</span>
                    <span className="font-mono font-bold text-sky-400">₹{inspectedBridge.estimatedInterventionCostCr} Cr</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">2-Year Deferral Cost Multiplier:</span>
                    <span className="font-mono font-bold text-rose-400">{inspectedBridge.costOfDelayMultiplier2Year}x</span>
                  </div>
                </div>

                <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800">
                  <span className="text-[10px] text-slate-400 uppercase font-mono block mb-1">Recommended Action</span>
                  <p className="font-medium text-slate-200">{inspectedBridge.recommendedAction}</p>
                  <p className="text-[11px] text-slate-400 mt-1">{inspectedBridge.deferralNarrative}</p>
                </div>
              </div>
            </div>

            <div className="mt-6 pt-4 border-t border-slate-800 space-y-3">
              {/* Real-time ML Deterioration Scoring Section */}
              <div className="p-3 bg-slate-950 rounded-lg border border-sky-800/80 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-mono text-sky-400 font-bold uppercase flex items-center gap-1.5">
                    <Cpu className="w-3.5 h-3.5" />
                    Live ML Deterioration Scorer
                  </span>
                  <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-sky-950 text-sky-300 border border-sky-800">
                    Phase 19 API
                  </span>
                </div>

                {!drawerScoringResult && !drawerScoringLoading && !drawerScoringError && (
                  <button
                    onClick={handleScoreInspectedBridge}
                    className="w-full py-2 px-3 rounded bg-sky-950/80 hover:bg-sky-900 border border-sky-700/80 text-sky-200 text-xs font-mono font-medium flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
                  >
                    <Cpu className="w-3.5 h-3.5" />
                    Evaluate via Real REST API
                  </button>
                )}

                {drawerScoringLoading && (
                  <div className="py-2 flex items-center justify-center gap-2 text-xs font-mono text-sky-300">
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    Calling /api/score...
                  </div>
                )}

                {drawerScoringError && (
                  <div className="p-2 rounded bg-rose-950/60 border border-rose-800 text-rose-200 text-[11px] space-y-1">
                    <div className="flex items-center gap-1 text-rose-300 font-bold">
                      <AlertTriangle className="w-3 h-3" />
                      <span>API Call Failed</span>
                    </div>
                    <p className="text-[10px]">{drawerScoringError}</p>
                    <button
                      onClick={handleScoreInspectedBridge}
                      className="text-[10px] text-sky-300 underline font-mono cursor-pointer"
                    >
                      Retry
                    </button>
                  </div>
                )}

                {drawerScoringResult && (
                  <div className="space-y-1.5 pt-1 text-xs font-mono">
                    <div className="flex items-center justify-between">
                      <span className="text-slate-400 text-[11px]">Calibrated 2-Yr Prob:</span>
                      <span className="text-base font-bold text-amber-400">
                        {(drawerScoringResult.calibrated_deterioration_probability * 100).toFixed(2)}%
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="text-slate-500">Raw Margin (z):</span>
                      <span className="text-slate-300 font-bold">{drawerScoringResult.raw_decision_score.toFixed(4)}</span>
                    </div>
                    <p className="text-[10px] text-slate-500 font-sans leading-tight pt-1">
                      Predicts routine decline (DECK₂₀₂₅ &lt; DECK₂₀₂₃). Does not predict collapse.
                    </p>
                  </div>
                )}
              </div>

              <button
                onClick={() => navigate(`/bridges/${inspectedBridge.id}`)}
                className="w-full py-2.5 rounded-md bg-sky-600 hover:bg-sky-500 text-white font-medium text-xs transition-colors flex items-center justify-center gap-2 shadow-xs cursor-pointer"
              >
                Open Full Engineering Dossier & ML Scoring
                <ExternalLink className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
