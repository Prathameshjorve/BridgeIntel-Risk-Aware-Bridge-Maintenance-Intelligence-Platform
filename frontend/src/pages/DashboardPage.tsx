import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { bridgeService } from '../services/api/bridgeService';
import { deferralService } from '../services/api/deferralService';
import { BridgeAsset, PortfolioSummary } from '../types/bridge';
import { DeferralPortfolioReport } from '../types/deferral';
import { KpiCard } from '../components/common/KpiCard';
import { RiskBadge } from '../components/common/RiskBadge';
import { PriorityBadge } from '../components/common/PriorityBadge';
import { ConditionBadge } from '../components/common/ConditionBadge';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import { RiskDistributionChart } from '../components/charts/RiskDistributionChart';
import { 
  Building2, 
  AlertTriangle, 
  Wallet, 
  CheckCheck, 
  TrendingDown, 
  AlertOctagon, 
  ArrowRight,
  Sparkles,
  Info
} from 'lucide-react';

export const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [bridges, setBridges] = useState<BridgeAsset[]>([]);
  const [topPriorityBridges, setTopPriorityBridges] = useState<BridgeAsset[]>([]);
  const [deferralReport, setDeferralReport] = useState<DeferralPortfolioReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [sumData, allBridges, topBridges, defData] = await Promise.all([
        bridgeService.getPortfolioSummary(),
        bridgeService.getAllBridges(),
        bridgeService.getTopPriorityBridges(5),
        deferralService.getDeferralReport()
      ]);
      setSummary(sumData);
      setBridges(allBridges);
      setTopPriorityBridges(topBridges);
      setDeferralReport(defData);
    } catch (err: any) {
      setError(err?.message || "Failed to load dashboard intelligence data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  if (loading) return <LoadingState message="Aggregating bridge portfolio and running prioritization models..." />;
  if (error || !summary) return <ErrorState message={error || "Portfolio data unavailable"} onRetry={loadData} />;

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-sky-950/60 border border-sky-800/80 text-sky-400 font-medium">
              PORTFOLIO DECISION ENGINE
            </span>
            <span className="text-xs font-mono text-slate-500">CYCLE FY 2026-27</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-100">
            Bridge Maintenance Overview
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Risk-aware maintenance planning under budget constraints • Structural deterioration, network criticality & deferral vulnerability
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/optimization')}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-md bg-sky-600 hover:bg-sky-500 text-white text-xs font-medium transition-colors shadow-sm"
          >
            <Sparkles className="w-3.5 h-3.5" />
            Run Budget Optimization
          </button>
          <button
            onClick={() => navigate('/bridges')}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-medium transition-colors"
          >
            Explore All Assets
          </button>
        </div>
      </div>

      {/* Top 5 KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <KpiCard
          title="Total Bridges"
          value={summary.totalBridges}
          subtitle={`Avg. Age: ${summary.averageBridgeAge} years`}
          icon={Building2}
          accentColor="slate"
          tooltip="Total bridge structures under active monitoring in regional inventory"
        />
        <KpiCard
          title="High Priority"
          value={summary.highPriorityCount}
          subtitle={`${summary.criticalRiskCount} in critical structural condition`}
          icon={AlertTriangle}
          accentColor="rose"
          tooltip="Bridges with combined high risk score and network criticality"
        />
        <KpiCard
          title="Available Budget"
          value={`₹${summary.availableBudgetCr.toFixed(1)} Cr`}
          subtitle="Annual capital ceiling"
          icon={Wallet}
          accentColor="brand"
          tooltip="Current municipal/state maintenance appropriation"
        />
        <KpiCard
          title="Recommended Allocation"
          value={`₹${summary.recommendedAllocationCr.toFixed(1)} Cr`}
          subtitle={`₹${summary.remainingBudgetCr.toFixed(1)} Cr reserve remaining`}
          icon={CheckCheck}
          accentColor="emerald"
          tooltip="Optimal expenditure selected by knapsack multi-objective model"
        />
        <KpiCard
          title="Est. Risk Reduction"
          value={`${summary.estimatedPortfolioRiskReductionPercent}%`}
          subtitle="Portfolio vulnerability avoided"
          icon={TrendingDown}
          accentColor="emerald"
          trend={{ value: "+18.4%", isPositive: true, label: "vs condition-only" }}
          tooltip="Net portfolio risk index reduction achieved through proposed intervention plan"
        />
      </div>

      {/* Deferral Alert Banner */}
      {deferralReport && (
        <div className="p-4 bg-rose-950/30 border border-rose-900/60 rounded-lg flex items-center justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className="p-2 rounded bg-rose-950/80 border border-rose-800 text-rose-400 shrink-0 mt-0.5">
              <AlertOctagon className="w-4 h-4" />
            </div>
            <div>
              <h4 className="text-xs font-semibold text-rose-200">
                Maintenance Deferral Alert: {deferralReport.urgentTransitions.length} Bridges Sensitive to Immediate Delay
              </h4>
              <p className="text-[11px] text-rose-300/80 mt-0.5">
                Delaying intervention by 24 months across these structures is projected to escalate intervention costs by ₹{deferralReport.total2YearCostPenaltyCr} Cr due to compounding girder/deck degradation.
              </p>
            </div>
          </div>
          <button
            onClick={() => navigate('/deferral')}
            className="shrink-0 inline-flex items-center gap-1.5 px-3 py-1.5 rounded bg-rose-900/40 hover:bg-rose-900/70 border border-rose-700 text-rose-200 text-xs font-medium transition-colors"
          >
            Review Deferral Analysis
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Analytics & Budget Breakdown Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Risk Distribution Card */}
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold text-slate-200">Portfolio Risk Distribution</h3>
              <p className="text-xs text-slate-400 mt-0.5">Categorized by multi-feature modeled risk score (0-100)</p>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400">N={bridges.length}</span>
          </div>
          <RiskDistributionChart bridges={bridges} />
          <div className="grid grid-cols-2 gap-2 mt-4 pt-3 border-t border-slate-800 text-xs">
            <div className="text-slate-400">Critical & High Risk: <span className="font-mono font-bold text-rose-400">{bridges.filter(b => b.riskCategory === 'Critical' || b.riskCategory === 'High').length}</span></div>
            <div className="text-slate-400">Low & Moderate: <span className="font-mono font-bold text-emerald-400">{bridges.filter(b => b.riskCategory === 'Low' || b.riskCategory === 'Moderate').length}</span></div>
          </div>
        </div>

        {/* Budget Allocation Summary Card */}
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-semibold text-slate-200">Capital Plan Summary</h3>
              <span className="text-xs font-mono text-sky-400">KNAPSACK 0-1</span>
            </div>
            <p className="text-xs text-slate-400 mb-4">Proposed allocation under current ₹{summary.availableBudgetCr} Cr appropriation ceiling</p>

            <div className="space-y-3">
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-slate-300">Funded Interventions</span>
                  <span className="font-mono font-bold text-sky-400">₹{summary.recommendedAllocationCr.toFixed(1)} Cr</span>
                </div>
                <div className="w-full bg-slate-800 rounded-full h-2">
                  <div 
                    className="bg-sky-500 h-2 rounded-full"
                    style={{ width: `${(summary.recommendedAllocationCr / summary.availableBudgetCr) * 100}%` }}
                  />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-slate-300">Contingency Reserve</span>
                  <span className="font-mono font-bold text-slate-400">₹{summary.remainingBudgetCr.toFixed(1)} Cr</span>
                </div>
                <div className="w-full bg-slate-800 rounded-full h-2">
                  <div 
                    className="bg-slate-600 h-2 rounded-full"
                    style={{ width: `${(summary.remainingBudgetCr / summary.availableBudgetCr) * 100}%` }}
                  />
                </div>
              </div>
            </div>

            <div className="mt-5 p-3 rounded bg-slate-950/70 border border-slate-800 text-xs space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-slate-400">Target Bridge Assets:</span>
                <span className="font-mono font-semibold text-slate-200">4 Bridges Funded</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-400">Avoided Public Consequence:</span>
                <span className="font-mono font-semibold text-emerald-400">339.5 Index Pts</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-400">Budget Efficiency Score:</span>
                <span className="font-mono font-semibold text-sky-400">4.47 Risk pts / ₹ Cr</span>
              </div>
            </div>
          </div>

          <button
            onClick={() => navigate('/optimization')}
            className="w-full mt-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded text-xs font-medium transition-colors text-center"
          >
            Adjust Budget Scenarios & Re-solve
          </button>
        </div>

        {/* Methodology & Defensibility Highlights */}
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Info className="w-4 h-4 text-sky-400" />
              <h3 className="text-sm font-semibold text-slate-200">Scientific Framework</h3>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Prioritization integrates physical condition with traffic exposure (ADT), detour burden, and network criticality to prevent catastrophic single-point-of-failure bottlenecks.
            </p>

            <div className="mt-4 space-y-2 text-xs">
              <div className="p-2.5 rounded bg-slate-950/60 border border-slate-800/80">
                <p className="font-medium text-slate-300">1. Condition is Not the Sole Driver</p>
                <p className="text-[11px] text-slate-400 mt-0.5">High-volume Fair bridges can incur higher failure consequence than low-volume Poor bridges.</p>
              </div>
              <div className="p-2.5 rounded bg-slate-950/60 border border-slate-800/80">
                <p className="font-medium text-slate-300">2. Deferral Risk Compounding</p>
                <p className="text-[11px] text-slate-400 mt-0.5">Unaddressed microcracks transition to structural condemnation exponentially.</p>
              </div>
            </div>
          </div>

          <button
            onClick={() => navigate('/methodology')}
            className="w-full mt-4 py-2 bg-slate-800 hover:bg-slate-700 text-sky-300 border border-slate-700 rounded text-xs font-medium transition-colors text-center"
          >
            View System Architecture & Math
          </button>
        </div>
      </div>

      {/* Top Priority Bridges Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden">
        <div className="p-4 border-b border-slate-800 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-slate-200">Top Priority Bridge Candidates</h3>
            <p className="text-xs text-slate-400 mt-0.5">Bridges ranked highest by the multi-criteria risk & consequence engine</p>
          </div>
          <button
            onClick={() => navigate('/priority')}
            className="text-xs text-sky-400 hover:text-sky-300 font-medium inline-flex items-center gap-1"
          >
            View Full Ranked Matrix
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/60 text-slate-400 font-mono border-b border-slate-800">
              <tr>
                <th className="py-3 px-4">Bridge ID / Route</th>
                <th className="py-3 px-4">Structure Type</th>
                <th className="py-3 px-4">Condition</th>
                <th className="py-3 px-4">Modeled Risk</th>
                <th className="py-3 px-4">Consequence</th>
                <th className="py-3 px-4">Priority</th>
                <th className="py-3 px-4">Action</th>
                <th className="py-3 px-4 text-right">Cost (Est.)</th>
                <th className="py-3 px-4 text-center">Inspect</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {topPriorityBridges.map((bridge) => (
                <tr 
                  key={bridge.id} 
                  className="hover:bg-slate-800/50 cursor-pointer transition-colors"
                  onClick={() => navigate(`/bridges/${bridge.id}`)}
                >
                  <td className="py-3 px-4">
                    <div className="font-mono font-semibold text-sky-400">{bridge.id}</div>
                    <div className="text-slate-300 text-[11px] truncate max-w-xs">{bridge.name}</div>
                    <div className="text-slate-400 text-[10px]">{bridge.route}</div>
                  </td>
                  <td className="py-3 px-4 text-slate-300">
                    <div>{bridge.bridgeType}</div>
                    <div className="text-slate-400 text-[10px] font-mono">{bridge.ageYears} yrs ({bridge.yearBuilt})</div>
                  </td>
                  <td className="py-3 px-4">
                    <ConditionBadge category={bridge.conditionCategory} rating={bridge.condition.overallCondition} />
                  </td>
                  <td className="py-3 px-4">
                    <RiskBadge level={bridge.riskCategory} score={bridge.modeledRiskScore} />
                  </td>
                  <td className="py-3 px-4 font-mono font-medium text-slate-200">
                    {bridge.consequenceScore.toFixed(1)}/100
                  </td>
                  <td className="py-3 px-4">
                    <PriorityBadge level={bridge.priorityLevel} score={bridge.priorityScore} />
                  </td>
                  <td className="py-3 px-4 text-slate-300 text-[11px]">
                    {bridge.recommendedAction}
                  </td>
                  <td className="py-3 px-4 text-right font-mono font-semibold text-slate-200">
                    ₹{bridge.estimatedInterventionCostCr.toFixed(1)} Cr
                  </td>
                  <td className="py-3 px-4 text-center">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        navigate(`/bridges/${bridge.id}`);
                      }}
                      className="px-2 py-1 bg-slate-800 hover:bg-sky-600 hover:text-white text-slate-300 rounded border border-slate-700 text-[11px] transition-colors"
                    >
                      View Details
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
