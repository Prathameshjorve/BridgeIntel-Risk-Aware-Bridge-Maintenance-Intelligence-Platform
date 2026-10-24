import React, { useEffect, useState } from 'react';
import { analyticsService } from '../services/api/analyticsService';
import { AnalyticsReport } from '../types/analytics';
import { KpiCard } from '../components/common/KpiCard';
import { BaselineComparisonChart } from '../components/charts/BaselineComparisonChart';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import { 
  LineChart, 
  BarChart2, 
  CheckCircle2, 
  Sparkles, 
  Layers, 
  TrendingUp, 
  Sliders,
  Award,
  Info
} from 'lucide-react';

export const AnalyticsPage: React.FC = () => {
  const [report, setReport] = useState<AnalyticsReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await analyticsService.getAnalyticsReport();
      setReport(data);
    } catch (err: any) {
      setError(err?.message || "Failed to load research analytics");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  if (loading) return <LoadingState message="Loading empirical validation benchmarks and baseline comparisons..." />;
  if (error || !report) return <ErrorState message={error || "Analytics unavailable"} onRetry={loadData} />;

  const proposed = report.baselineComparisons[0];
  const baseline = report.baselineComparisons[1];
  const riskLift = (((proposed.totalRiskReduction - baseline.totalRiskReduction) / baseline.totalRiskReduction) * 100).toFixed(1);
  const consequenceLift = (((proposed.totalConsequenceAvoided - baseline.totalConsequenceAvoided) / baseline.totalConsequenceAvoided) * 100).toFixed(1);

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-sky-950 text-sky-400 border border-sky-800">
              RESEARCH & BENCHMARKING
            </span>
            <span className="text-xs font-mono text-slate-500">HEAD-TO-HEAD STRATEGY EVALUATION</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-100">
            Strategy Analytics & Baseline Evaluation
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Empirical validation proving why multi-attribute risk-aware optimization outperforms conventional "worst-condition-first" heuristics
          </p>
        </div>
      </div>

      {/* Primary Research Finding Callout */}
      <div className="p-5 bg-sky-950/20 border border-sky-900/60 rounded-lg flex items-start gap-4">
        <Award className="w-6 h-6 text-sky-400 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <h3 className="text-sm font-semibold text-slate-100">
            Core Research Validation Finding
          </h3>
          <p className="text-xs text-slate-300 leading-relaxed">
            Under an identical budget constraint (₹55 Cr), the <strong>Risk-Aware Optimization Engine</strong> achieves a{' '}
            <span className="text-emerald-400 font-semibold font-mono">+{riskLift}% higher aggregate risk reduction</span> and prevents{' '}
            <span className="text-sky-400 font-semibold font-mono">+{consequenceLift}% more public disruption</span> compared to the standard condition-only baseline, 
            while mitigating <span className="font-mono text-amber-300">₹{(baseline.twoYearDeferredRiskLiabilityCr - proposed.twoYearDeferredRiskLiabilityCr).toFixed(1)} Cr</span> in 2-year deferred deterioration liabilities.
          </p>
        </div>
      </div>

      {/* Head-to-Head Comparison Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-sm font-semibold text-slate-200">Comparative Strategy Performance Matrix</h3>
            <p className="text-xs text-slate-400 mt-0.5">Evaluated across portfolio under equal ₹55 Cr capital appropriation</p>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/80 text-slate-400 font-mono border-b border-slate-800">
              <tr>
                <th className="py-3 px-4">Maintenance Strategy</th>
                <th className="py-3 px-4 text-right">Budget Spent</th>
                <th className="py-3 px-4 text-center">Bridges Funded</th>
                <th className="py-3 px-4 text-center">Net Risk Reduction</th>
                <th className="py-3 px-4 text-center">Consequence Avoided</th>
                <th className="py-3 px-4 text-center">Budget Efficiency</th>
                <th className="py-3 px-4 text-right">2-Yr Deferred Liability</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {report.baselineComparisons.map((strat, idx) => {
                const isProposed = idx === 0;
                return (
                  <tr 
                    key={strat.strategyName} 
                    className={isProposed ? 'bg-sky-950/30 font-medium' : 'hover:bg-slate-800/40'}
                  >
                    <td className="py-3.5 px-4">
                      <div className="flex items-center gap-2">
                        {isProposed && <span className="w-2 h-2 rounded-full bg-sky-400" />}
                        <span className={isProposed ? 'text-sky-300 font-semibold text-sm' : 'text-slate-300'}>
                          {strat.strategyName}
                        </span>
                      </div>
                    </td>
                    <td className="py-3.5 px-4 text-right font-mono text-slate-200">
                      ₹{strat.allocatedBudgetCr.toFixed(1)} Cr
                    </td>
                    <td className="py-3.5 px-4 text-center font-mono text-slate-300">
                      {strat.bridgesSelectedCount} Bridges
                    </td>
                    <td className="py-3.5 px-4 text-center font-mono font-bold text-emerald-400">
                      {strat.totalRiskReduction.toFixed(0)} pts
                    </td>
                    <td className="py-3.5 px-4 text-center font-mono font-bold text-sky-400">
                      {strat.totalConsequenceAvoided.toFixed(0)} pts
                    </td>
                    <td className="py-3.5 px-4 text-center font-mono font-bold text-slate-200">
                      {strat.budgetEfficiencyScore.toFixed(2)} pts/₹Cr
                    </td>
                    <td className="py-3.5 px-4 text-right font-mono text-amber-400 font-semibold">
                      ₹{strat.twoYearDeferredRiskLiabilityCr.toFixed(1)} Cr
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Grid: Baseline Chart and Model Validation */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Baseline Bar Chart */}
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-5">
          <div className="flex items-center justify-between mb-2">
            <div>
              <h3 className="text-sm font-semibold text-slate-200">Decision Outcome Comparison</h3>
              <p className="text-xs text-slate-400 mt-0.5">Risk Reduction vs. Consequence Avoidance</p>
            </div>
          </div>
          <BaselineComparisonChart comparisons={report.baselineComparisons} />
        </div>

        {/* Model Accuracy & Validation Specs */}
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-semibold text-slate-200">Model Validation & Accuracy Standards</h3>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400">TEMPORAL SPLIT TEST</span>
            </div>
            <p className="text-xs text-slate-400 mb-4">
              Longitudinal condition deterioration model benchmarked on historical inspection transitions (NBI Items 58–60)
            </p>

            <div className="space-y-3">
              {report.modelPerformance.map((metric) => (
                <div key={metric.metricName} className="p-3 bg-slate-950/70 rounded border border-slate-800 text-xs">
                  <div className="flex justify-between items-center mb-1">
                    <span className="font-semibold text-slate-200">{metric.metricName}</span>
                    <div className="flex items-center gap-2 font-mono">
                      <span className="text-emerald-400 font-bold">{metric.metricValue} {metric.unit}</span>
                      <span className="text-slate-500 text-[10px]">(Baseline: {metric.benchmarkValue})</span>
                    </div>
                  </div>
                  <p className="text-[11px] text-slate-400">{metric.description}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-800 text-[11px] text-slate-500 flex items-center gap-1.5">
            <Info className="w-3.5 h-3.5" />
            Validation strictly tested on held-out temporal cycles to prevent future-data leakage.
          </div>
        </div>
      </div>
    </div>
  );
};
