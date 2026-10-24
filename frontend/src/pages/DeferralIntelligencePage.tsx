import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { deferralService } from '../services/api/deferralService';
import { DeferralPortfolioReport } from '../types/deferral';
import { KpiCard } from '../components/common/KpiCard';
import { DeferralTrajectoryChart } from '../components/charts/DeferralTrajectoryChart';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import { 
  AlertTriangle, 
  ShieldAlert, 
  TrendingUp, 
  Layers, 
  Info
} from 'lucide-react';

export const DeferralIntelligencePage: React.FC = () => {
  const navigate = useNavigate();
  const [report, setReport] = useState<DeferralPortfolioReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await deferralService.getDeferralReport();
      setReport(data);
    } catch (err: any) {
      setError(err?.message || "Failed to load deferral intelligence models");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  if (loading) return <LoadingState message="Simulating longitudinal multi-year deferral degradation curves..." />;
  if (error || !report) return <ErrorState message={error || "Deferral data unavailable"} onRetry={loadData} />;

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-sky-950 text-sky-400 border border-sky-800">
              LIFE-CYCLE DEFERRAL MODEL
            </span>
            <span className="text-xs font-mono text-slate-500">HORIZON: +12 & +24 MONTHS</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-100">
            Maintenance Deferral Intelligence
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Estimate how modeled bridge risk escalates and identify non-linear cost penalty thresholds if capital intervention is delayed
          </p>
        </div>
      </div>

      {/* Safety & Language Disclaimer Alert */}
      <div className="p-4 bg-slate-900 border border-slate-800 rounded-lg flex items-start gap-3">
        <Info className="w-5 h-5 text-sky-400 shrink-0 mt-0.5" />
        <div className="text-xs text-slate-400 leading-relaxed">
          <strong className="text-slate-200">Scientific Interpretation Standard: </strong>
          Models project rate of structural condition deterioration under ongoing cyclic load. "Stable under modeled assumptions" denotes a gradual degradation trajectory, 
          <strong> not an engineering certification of safety</strong>. Bridges flagged with "High deferral sensitivity" exhibit compounding distress where postponing intervention by 12–24 months triggers expensive structural replacement.
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          title="High Deferral Sensitivity"
          value={report.highSensitivityCount}
          subtitle="Non-linear deterioration if delayed"
          icon={AlertTriangle}
          accentColor="rose"
        />
        <KpiCard
          title="Prioritize Before Deferral"
          value={report.prioritizeCount}
          subtitle="Imminent transition to load-posting"
          icon={ShieldAlert}
          accentColor="amber"
        />
        <KpiCard
          title="2-Yr Portfolio Cost Penalty"
          value={`₹${report.total2YearCostPenaltyCr} Cr`}
          subtitle="Avoidable escalation if delayed"
          icon={TrendingUp}
          accentColor="rose"
        />
        <KpiCard
          title="Stable / Monitor Cohort"
          value={`${report.stableCount + report.monitorCount} Bridges`}
          subtitle="Linear degradation trajectory"
          icon={Layers}
          accentColor="emerald"
        />
      </div>

      {/* Trajectory Visualizer */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-5">
        <div className="flex items-center justify-between mb-2">
          <div>
            <h3 className="text-sm font-semibold text-slate-200">Multi-Horizon Portfolio Trajectory</h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Projected portfolio average risk score and cumulative cost penalties across Current, +1 Year, and +2 Year deferral windows
            </p>
          </div>
          <span className="text-xs font-mono text-slate-400">Longitudinal Degradation Model</span>
        </div>
        <DeferralTrajectoryChart trajectories={report.trajectories} />
      </div>

      {/* Deferral Sensitivity Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden shadow-sm">
        <div className="p-4 border-b border-slate-800 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-slate-200">Asset Deferral Sensitivity Matrix</h3>
            <p className="text-xs text-slate-400 mt-0.5">Ranked by 2-year modeled risk escalation magnitude</p>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/80 text-slate-400 font-mono border-b border-slate-800">
              <tr>
                <th className="py-3 px-4">Bridge ID / Corridor</th>
                <th className="py-3 px-4 text-center">Current Risk</th>
                <th className="py-3 px-4 text-center">+1 Year Projected</th>
                <th className="py-3 px-4 text-center">+2 Years Projected</th>
                <th className="py-3 px-4 text-center">2-Year Risk Δ</th>
                <th className="py-3 px-4">Deferral Sensitivity Status</th>
                <th className="py-3 px-4 text-right">Cost Penalty (Delay)</th>
                <th className="py-3 px-4 text-center">Inspect</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {report.urgentTransitions.map((item) => {
                const b = item.bridge;
                return (
                  <tr key={b.id} className="hover:bg-slate-800/50 transition-colors">
                    <td className="py-3.5 px-4">
                      <div className="font-mono font-semibold text-sky-400">{b.id}</div>
                      <div className="text-slate-200 font-medium truncate max-w-xs">{b.name}</div>
                      <div className="text-slate-400 text-[10px]">{b.route}</div>
                    </td>
                    <td className="py-3.5 px-4 text-center font-mono text-slate-300 font-semibold">
                      {item.currentRisk.toFixed(1)}
                    </td>
                    <td className="py-3.5 px-4 text-center font-mono text-amber-400 font-semibold">
                      {item.risk1Year.toFixed(1)}
                    </td>
                    <td className="py-3.5 px-4 text-center font-mono text-rose-400 font-bold">
                      {item.risk2Year.toFixed(1)}
                    </td>
                    <td className="py-3.5 px-4 text-center font-mono font-bold text-rose-300">
                      +{item.riskDelta2Year.toFixed(1)} ({item.riskIncreasePercentage}%)
                    </td>
                    <td className="py-3.5 px-4">
                      <span className={`text-[11px] px-2.5 py-1 rounded font-medium border ${
                        item.status === 'High deferral sensitivity'
                          ? 'bg-rose-950/80 text-rose-200 border-rose-800'
                          : item.status === 'Prioritize before deferral'
                          ? 'bg-amber-950/80 text-amber-200 border-amber-800'
                          : 'bg-slate-800 text-slate-300 border-slate-700'
                      }`}>
                        {item.status}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-right font-mono font-bold text-rose-400">
                      +₹{item.costEscalationCr.toFixed(2)} Cr
                    </td>
                    <td className="py-3.5 px-4 text-center">
                      <button
                        onClick={() => navigate(`/bridges/${b.id}`)}
                        className="px-2 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded border border-slate-700 text-[11px]"
                      >
                        Inspect
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
