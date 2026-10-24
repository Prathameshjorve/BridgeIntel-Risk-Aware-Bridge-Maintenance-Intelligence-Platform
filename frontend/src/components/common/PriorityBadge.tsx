import React from 'react';
import { PriorityLevel } from '../../types/bridge';
import { Flame, ArrowUpCircle, MinusCircle, CheckCircle2, PauseCircle } from 'lucide-react';

interface PriorityBadgeProps {
  level: PriorityLevel;
  score?: number;
  size?: 'sm' | 'md' | 'lg';
}

export const PriorityBadge: React.FC<PriorityBadgeProps> = ({
  level,
  score,
  size = 'md'
}) => {
  const configs = {
    Urgent: {
      bg: 'bg-red-50 text-red-800 border-red-300 dark:bg-red-950/80 dark:text-red-200 dark:border-red-700/80',
      icon: Flame,
      label: 'Urgent Intervention'
    },
    High: {
      bg: 'bg-orange-50 text-orange-800 border-orange-300 dark:bg-orange-950/70 dark:text-orange-200 dark:border-orange-700/80',
      icon: ArrowUpCircle,
      label: 'High Priority'
    },
    Medium: {
      bg: 'bg-amber-50 text-amber-800 border-amber-300 dark:bg-amber-950/60 dark:text-amber-200 dark:border-amber-700/70',
      icon: MinusCircle,
      label: 'Medium'
    },
    Routine: {
      bg: 'bg-slate-100 text-slate-700 border-slate-300 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700',
      icon: CheckCircle2,
      label: 'Routine Cycle'
    },
    Deferred: {
      bg: 'bg-purple-50 text-purple-800 border-purple-300 dark:bg-purple-950/60 dark:text-purple-300 dark:border-purple-800/80',
      icon: PauseCircle,
      label: 'Planned Deferral'
    }
  };

  const config = configs[level] || configs.Medium;
  const Icon = config.icon;

  const sizeClasses = {
    sm: 'text-xs px-2 py-0.5 gap-1',
    md: 'text-xs px-2.5 py-1 gap-1.5 font-medium',
    lg: 'text-sm px-3 py-1.5 gap-2 font-semibold'
  };

  return (
    <span className={`inline-flex items-center rounded-md border ${config.bg} ${sizeClasses[size]} transition-colors`}>
      <Icon className={size === 'lg' ? 'w-4 h-4' : 'w-3.5 h-3.5'} />
      <span>{config.label}</span>
      {score !== undefined && (
        <span className="font-mono ml-1 font-bold">P-{Math.round(score)}</span>
      )}
    </span>
  );
};
