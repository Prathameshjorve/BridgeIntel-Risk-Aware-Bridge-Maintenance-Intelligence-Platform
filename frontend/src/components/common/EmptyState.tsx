import React from 'react';
import { Database, RefreshCw } from 'lucide-react';

interface EmptyStateProps {
  title?: string;
  description?: string;
  onReset?: () => void;
  resetLabel?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title = "No Bridge Records Found",
  description = "No bridges matched the current search and filtering criteria.",
  onReset,
  resetLabel = "Reset Filters"
}) => {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4 text-center bg-slate-900/50 border border-dashed border-slate-800 rounded-lg">
      <div className="w-12 h-12 rounded-full bg-slate-800 flex items-center justify-center text-slate-400 mb-3">
        <Database className="w-6 h-6" />
      </div>
      <h3 className="text-sm font-semibold text-slate-200">{title}</h3>
      <p className="text-xs text-slate-400 mt-1 max-w-sm">{description}</p>
      {onReset && (
        <button
          onClick={onReset}
          className="mt-4 inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded text-xs font-medium border border-slate-700 transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          {resetLabel}
        </button>
      )}
    </div>
  );
};
