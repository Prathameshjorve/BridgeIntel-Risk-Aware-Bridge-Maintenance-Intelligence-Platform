import React from 'react';
import { AlertOctagon, RotateCcw } from 'lucide-react';

interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = "Service Connection Error",
  message = "An error occurred while loading decision models or asset records.",
  onRetry
}) => {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4 text-center bg-rose-950/20 border border-rose-900/50 rounded-lg">
      <div className="w-12 h-12 rounded-full bg-rose-950/60 border border-rose-800 flex items-center justify-center text-rose-400 mb-3">
        <AlertOctagon className="w-6 h-6" />
      </div>
      <h3 className="text-sm font-semibold text-rose-200">{title}</h3>
      <p className="text-xs text-rose-300/80 mt-1 max-w-sm font-mono">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-4 inline-flex items-center gap-1.5 px-3 py-1.5 bg-rose-900/40 hover:bg-rose-900/60 text-rose-200 rounded text-xs font-medium border border-rose-700 transition-colors"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          Retry Request
        </button>
      )}
    </div>
  );
};
