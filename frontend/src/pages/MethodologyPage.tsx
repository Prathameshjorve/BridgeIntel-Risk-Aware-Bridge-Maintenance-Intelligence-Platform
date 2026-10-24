import React from 'react';
import { 
  ArrowDown, 
  Database, 
  Cpu, 
  Network, 
  BarChart3, 
  PieChart, 
  Clock, 
  ShieldCheck, 
  AlertTriangle,
  FileText
} from 'lucide-react';

export const MethodologyPage: React.FC = () => {
  const pipelineSteps = [
    {
      step: "01",
      title: "Bridge Asset Ingestion",
      icon: Database,
      tag: "CORE DATA",
      summary: "Ingestion of Federal Highway Administration (FHWA) National Bridge Inventory (NBI) longitudinal inspection datasets.",
      details: "Extracts discrete ratings for Deck (Item 58), Superstructure (Item 59), Substructure (Item 60), Average Daily Traffic (Item 29), Truck Share (Item 109), and Detour Bypass (Item 19)."
    },
    {
      step: "02",
      title: "Longitudinal Preprocessing & Temporal Alignment",
      icon: Clock,
      tag: "VALIDATION",
      summary: "Cleaning, anomaly filtering, and construction of multi-cycle inspection deterioration trajectories.",
      details: "Removes artificial non-monotonic condition anomalies caused by inspection subjectivity; creates temporal training and validation splits avoiding future data leakage."
    },
    {
      step: "03",
      title: "Deterioration & Risk Prediction Engine",
      icon: Cpu,
      tag: "ML / MARKOV",
      summary: "Probabilistic modeling of structural condition transitions over 24- to 48-month horizons.",
      details: "Gradient boosting and Markov state transition models trained to estimate deterioration velocity given age, structural type, cumulative truck axle loading, and climate freeze-thaw cycles."
    },
    {
      step: "04",
      title: "Public & Network Consequence Modeling",
      icon: Network,
      tag: "EXPOSURE MODEL",
      summary: "Quantification of socio-economic disruption in the event of load-posting or closure.",
      details: "Formulates consequence as a function of Daily Vehicle Delay Hours = (ADT × Detour Km × Cost Factor) + Emergency Access Criticality (trauma centers, hazardous materials routes)."
    },
    {
      step: "05",
      title: "Risk-Aware Priority Synthesis",
      icon: BarChart3,
      tag: "MULTI-CRITERIA",
      summary: "Integrated ranking moving beyond the oversimplified 'worst condition first' heuristic.",
      details: "Calculates Priority Score = w₁·StructuralRisk + w₂·PublicConsequence + w₃·TrafficExposure + w₄·DeferralUrgency."
    },
    {
      step: "06",
      title: "Constrained Knapsack Budget Optimization",
      icon: PieChart,
      tag: "OPTIMIZATION",
      summary: "Maximizes portfolio risk reduction and avoided consequence under strict capital expenditure ceilings.",
      details: "Solves 0-1 Knapsack Dynamic Programming: Maximize Σ(Benefit_i × Selection_i) subject to Σ(InterventionCost_i × Selection_i) ≤ AvailableBudget."
    },
    {
      step: "07",
      title: "Maintenance Deferral Intelligence",
      icon: AlertTriangle,
      tag: "LIFE-CYCLE",
      summary: "Quantifies the compounding cost penalty of delaying intervention by 12 to 24 months.",
      details: "Identifies non-linear fatigue and spalling thresholds where minor preventative maintenance escalates into full structural condemnation."
    },
    {
      step: "08",
      title: "Explainability & Engineering Decision Support",
      icon: ShieldCheck,
      tag: "AUDITABLE AI",
      summary: "Transparent feature attribution (SHAP-approximated) presented to licensed professional engineers.",
      details: "Provides transparent reasoning for every priority rank and selection, keeping human engineers as the ultimate certified authority."
    }
  ];

  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      {/* Header */}
      <div className="border-b border-slate-800 pb-4">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs font-mono px-2 py-0.5 rounded bg-sky-950 text-sky-400 border border-sky-800">
            SYSTEM ARCHITECTURE & THEORY
          </span>
          <span className="text-xs font-mono text-slate-500">DEFENSIBLE AI FRAMEWORK</span>
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-100">
          Methodology & System Architecture
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Scientific formulation, algorithmic pipeline, and empirical data standards governing the decision engine
        </p>
      </div>

      {/* Scientific Integrity Box */}
      <div className="p-5 bg-slate-900 border border-slate-800 rounded-lg space-y-3">
        <div className="flex items-center gap-2 text-sky-400 font-semibold text-sm">
          <ShieldCheck className="w-4 h-4" />
          Core Research Stance & Engineering Guardrails
        </div>
        <div className="text-xs text-slate-300 leading-relaxed space-y-2">
          <p>
            This system is designed as a <strong>decision-support tool</strong> to assist infrastructure planners and transportation authorities managing large portfolios. It does not replace licensed structural engineers or physical field inspection certified under NBIS standards.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2">
            <div className="p-3 bg-slate-950/70 rounded border border-slate-800">
              <strong className="text-slate-200 block mb-1">1. Non-Fabrication Principle</strong>
              <p className="text-slate-400 text-[11px]">
                The platform will never synthesize fake collapse probabilities or fabricate bridge measurements. Empirical models predict deterioration rates and relative risk indices.
              </p>
            </div>
            <div className="p-3 bg-slate-950/70 rounded border border-slate-800">
              <strong className="text-slate-200 block mb-1">2. Multi-Objective Decision Superiority</strong>
              <p className="text-slate-400 text-[11px]">
                Selecting interventions purely based on the lowest condition rating ignores traffic volume and network isolation. Our risk-aware model balances condition with real-world consequence.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Visual Pipeline Flow */}
      <div className="space-y-4">
        <h3 className="text-sm font-semibold text-slate-200">End-to-End Decision Pipeline</h3>

        <div className="space-y-3">
          {pipelineSteps.map((step, idx) => {
            const Icon = step.icon;
            return (
              <div key={step.step} className="relative">
                <div className="p-4 bg-slate-900 border border-slate-800 rounded-lg flex flex-col md:flex-row md:items-center justify-between gap-4 hover:border-slate-700 transition-colors">
                  <div className="flex items-start gap-3.5">
                    <div className="w-10 h-10 rounded-lg bg-sky-950/60 border border-sky-800 text-sky-400 flex items-center justify-center shrink-0 font-mono font-bold text-sm">
                      {step.step}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h4 className="text-sm font-semibold text-slate-100">{step.title}</h4>
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                          {step.tag}
                        </span>
                      </div>
                      <p className="text-xs text-slate-300 mt-1">{step.summary}</p>
                      <p className="text-[11px] text-slate-400 mt-0.5">{step.details}</p>
                    </div>
                  </div>
                  <div className="hidden md:flex p-2 rounded bg-slate-950 text-slate-400 shrink-0">
                    <Icon className="w-5 h-5" />
                  </div>
                </div>

                {idx < pipelineSteps.length - 1 && (
                  <div className="flex justify-center my-1">
                    <ArrowDown className="w-4 h-4 text-slate-600" />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Mathematical Formulations Section */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-6 space-y-4">
        <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
          <FileText className="w-4 h-4 text-sky-400" />
          Core Mathematical Formulations
        </h3>

        <div className="space-y-4 text-xs">
          {/* Formulation 1 */}
          <div className="p-4 bg-slate-950 rounded border border-slate-800 space-y-2">
            <span className="font-mono text-sky-400 font-semibold block">1. Integrated Priority Score Formulation</span>
            <div className="p-3 bg-slate-900 rounded font-mono text-slate-200 text-xs overflow-x-auto">
              Priority_i = w₁ · R_i + w₂ · C_i + w₃ · E_i + w₄ · D_i
            </div>
            <p className="text-slate-400 text-[11px] leading-relaxed">
              Where <code className="text-slate-300 font-mono">R_i</code> is Modeled Structural Deterioration Risk, <code className="text-slate-300 font-mono">C_i</code> is Consequence / Detour Burden Score, <code className="text-slate-300 font-mono">E_i</code> is Traffic Exposure (ADT & Truck %), and <code className="text-slate-300 font-mono">D_i</code> is 2-Year Deferral Sensitivity Index. Weights satisfy Σ w_k = 1.0.
            </p>
          </div>

          {/* Formulation 2 */}
          <div className="p-4 bg-slate-950 rounded border border-slate-800 space-y-2">
            <span className="font-mono text-sky-400 font-semibold block">2. Knapsack Constrained Multi-Objective Optimization</span>
            <div className="p-3 bg-slate-900 rounded font-mono text-slate-200 text-xs overflow-x-auto">
              Maximize: Σ [ x_i · ( ΔR_i · C_i ) ] <br />
              Subject to: Σ [ x_i · Cost_i ] ≤ Budget_Appropriation, &nbsp; x_i ∈ {'{0, 1}'}
            </div>
            <p className="text-slate-400 text-[11px] leading-relaxed">
              Where binary decision variable <code className="text-slate-300 font-mono">x_i = 1</code> indicates funding asset intervention in current fiscal cycle, <code className="text-slate-300 font-mono">ΔR_i</code> is expected risk reduction, and <code className="text-slate-300 font-mono">Cost_i</code> is parametric estimated cost.
            </p>
          </div>
        </div>
      </div>

      {/* Dataset Architecture References */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-5">
        <h3 className="text-sm font-semibold text-slate-200 mb-3">Data Source Taxonomy & Boundaries</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
          <div className="p-3 bg-slate-950 rounded border border-slate-800">
            <div className="flex items-center justify-between mb-1">
              <span className="font-semibold text-slate-200">FHWA NBI Core</span>
              <span className="text-[10px] font-mono text-emerald-400">CORE PIPELINE</span>
            </div>
            <p className="text-[11px] text-slate-400">
              National Bridge Inventory longitudinal dataset covering structural items 58, 59, 60, traffic exposure, and detour lengths.
            </p>
          </div>
          <div className="p-3 bg-slate-950 rounded border border-slate-800">
            <div className="flex items-center justify-between mb-1">
              <span className="font-semibold text-slate-200">OpenStreetMap / GIS</span>
              <span className="text-[10px] font-mono text-amber-400">OPTIONAL / SIMULATED</span>
            </div>
            <p className="text-[11px] text-slate-400">
              Corridor detour bypass topology and critical trauma center routing distances. Currently simulated via verified contract.
            </p>
          </div>
          <div className="p-3 bg-slate-950 rounded border border-slate-800">
            <div className="flex items-center justify-between mb-1">
              <span className="font-semibold text-slate-200">SDNET2018 (CV)</span>
              <span className="text-[10px] font-mono text-slate-400">FUTURE EXTENSION</span>
            </div>
            <p className="text-[11px] text-slate-400">
              Concrete crack and spalling image classification. Architecturally optional; core engine functions deterministically without image inputs.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
