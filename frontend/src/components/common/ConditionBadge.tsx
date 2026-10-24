import React from 'react';
import { ConditionCategory } from '../../types/bridge';

interface ConditionBadgeProps {
  category: ConditionCategory;
  rating?: number; // 0 to 9 NBI scale
}

export const ConditionBadge: React.FC<ConditionBadgeProps> = ({
  category,
  rating
}) => {
  const styles = {
    Good: 'bg-emerald-50 text-emerald-800 border-emerald-300 dark:bg-emerald-950/50 dark:text-emerald-300 dark:border-emerald-800/80',
    Fair: 'bg-sky-50 text-sky-800 border-sky-300 dark:bg-sky-950/50 dark:text-sky-300 dark:border-sky-800/80',
    Poor: 'bg-amber-50 text-amber-800 border-amber-300 dark:bg-amber-950/60 dark:text-amber-300 dark:border-amber-800/80',
    Critical: 'bg-rose-50 text-rose-800 border-rose-300 dark:bg-rose-950/70 dark:text-rose-300 dark:border-rose-800',
  };

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${styles[category] || styles.Fair} transition-colors`}>
      {rating !== undefined && (
        <span className="font-mono font-bold mr-1.5">{rating}/9</span>
      )}
      <span>{category}</span>
    </span>
  );
};
