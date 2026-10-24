import React from 'react';
import { Loader2 } from 'lucide-react';

interface LoadingStateProps {
  message?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({ 
  message = "Loading engineering records and modeled predictions..." 
}) => {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4">
      <Loader2 className="w-8 h-8 text-sky-400 animate-spin mb-3" />
      <p className="text-sm text-slate-400 font-mono">{message}</p>
    </div>
  );
};
