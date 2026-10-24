import React from 'react';
import { RiskFactorAttribution } from '../../types/bridge';
import { HelpCircle, Info } from 'lucide-react';

interface ExplanationPanelProps {
  title?: string;
  subtitle?: string;
  factors: RiskFactorAttribution[];
  totalScore?: number;
}

export const ExplanationPanel: React.FC<ExplanationPanelProps> = ({
  title = "Modeled Attribution Breakdown",
  subtitle = "Relative factor contributions derived from structural, exposure, and network features",
  factors,
  totalScore
}) => {
  const categoryColors = {
    Structural: 'bg-rose-500',
    Traffic: 'bg-amber-500',
    Network: 'bg-sky-500',
    Aging: 'bg-purple-500'
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-5">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h4 className="text-sm font-semibold text-slate-200 flex items-center gap-1.5">
            <Info className="w-4 h-4 text-sky-400" />
            {title}
          </h4>
          <p className="text-xs text-slate-400 mt-0.5">{subtitle}</p>
        </div>
        {totalScore !== undefined && (
          <div className="text-right">
            <span className="text-xs text-slate-400">Composite Score</span>
            <div className="text-lg font-mono font-bold text-sky-400">{totalScore.toFixed(1)}/100</div>
          </div>
        )}
      </div>

      <div className="space-y-4">
        {factors.map((factor, idx) => (
          <div key={idx} className="space-y-1.5">
            <div className="flex items-center justify-between text-xs">
              <span className="font-medium text-slate-200">{factor.factor}</span>
              <span className="font-mono text-slate-300 font-semibold">{factor.contributionPercent}%</span>
            </div>
            
            {/* Visual Bar */}
            <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
              <div 
                className={`h-full rounded-full ${categoryColors[factor.category] || 'bg-sky-500'}`}
                style={{ width: `${Math.min(100, factor.contributionPercent * 2)}%` }} // normalized for visibility
              />
            </div>

            <p className="text-[11px] text-slate-400 leading-tight">
              {factor.description}
            </p>
          </div>
        ))}
      </div>

      <div className="mt-4 pt-3 border-t border-slate-800 flex items-center justify-between text-[11px] text-slate-500">
        <span className="flex items-center gap-1">
          <HelpCircle className="w-3 h-3 text-slate-400" />
          Additive feature contribution (SHAP-approximated)
        </span>
        <div className="flex items-center gap-2">
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-rose-500 inline-block"/> Structural</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-amber-500 inline-block"/> Traffic</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-sky-500 inline-block"/> Network</span>
        </div>
      </div>
    </div>
  );
};
