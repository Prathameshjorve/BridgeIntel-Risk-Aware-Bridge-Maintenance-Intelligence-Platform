import React from 'react';
import { LucideIcon } from 'lucide-react';

interface KpiCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  trend?: {
    value: string;
    isPositive?: boolean;
    label?: string;
  };
  accentColor?: 'brand' | 'amber' | 'emerald' | 'rose' | 'slate';
  tooltip?: string;
}

export const KpiCard: React.FC<KpiCardProps> = ({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
  accentColor = 'brand',
  tooltip
}) => {
  const accentClasses = {
    brand: 'text-sky-400 bg-sky-950/40 border-sky-800/40',
    amber: 'text-amber-400 bg-amber-950/40 border-amber-800/40',
    emerald: 'text-emerald-400 bg-emerald-950/40 border-emerald-800/40',
    rose: 'text-rose-400 bg-rose-950/40 border-rose-800/40',
    slate: 'text-slate-400 bg-slate-900 border-slate-800',
  };

  return (
    <div 
      className="bg-slate-900 border border-slate-800 rounded-lg p-5 shadow-sm hover:border-slate-700 transition-all flex flex-col justify-between"
      title={tooltip}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">{title}</p>
          <h3 className="text-2xl font-bold font-mono text-slate-50 mt-1.5">{value}</h3>
        </div>
        <div className={`p-2.5 rounded-lg border ${accentClasses[accentColor]}`}>
          <Icon className="w-5 h-5" />
        </div>
      </div>

      {(subtitle || trend) && (
        <div className="mt-3 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs">
          {subtitle && <span className="text-slate-400 truncate">{subtitle}</span>}
          {trend && (
            <span className={`font-mono font-medium ${trend.isPositive ? 'text-emerald-400' : 'text-rose-400'}`}>
              {trend.value} <span className="text-slate-500 font-sans">{trend.label}</span>
            </span>
          )}
        </div>
      )}
    </div>
  );
};
