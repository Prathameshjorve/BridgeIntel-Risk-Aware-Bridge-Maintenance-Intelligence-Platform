import React, { useState } from 'react';
import { DEFAULT_SYSTEM_SETTINGS } from '../mock/settings';
import { SystemSettings } from '../types/settings';
import { 
  Sliders, 
  Database, 
  Check, 
  RotateCcw, 
  AlertCircle
} from 'lucide-react';

export const SettingsPage: React.FC = () => {
  const [settings, setSettings] = useState<SystemSettings>({ ...DEFAULT_SYSTEM_SETTINGS });
  const [notice, setNotice] = useState<string | null>(null);

  const totalWeights = (
    settings.weights.structuralRisk +
    settings.weights.trafficExposure +
    settings.weights.networkCriticality +
    settings.weights.deferralUrgency
  );

  const isNormalized = Math.abs(totalWeights - 1.0) < 0.001;

  const handleWeightChange = (key: keyof SystemSettings['weights'], val: number) => {
    setSettings(prev => ({
      ...prev,
      weights: {
        ...prev.weights,
        [key]: parseFloat(val.toFixed(2))
      }
    }));
  };

  const handleNormalize = () => {
    const sum = totalWeights;
    if (sum === 0) return;
    setSettings(prev => ({
      ...prev,
      weights: {
        structuralRisk: parseFloat((prev.weights.structuralRisk / sum).toFixed(2)),
        trafficExposure: parseFloat((prev.weights.trafficExposure / sum).toFixed(2)),
        networkCriticality: parseFloat((prev.weights.networkCriticality / sum).toFixed(2)),
        deferralUrgency: parseFloat((prev.weights.deferralUrgency / sum).toFixed(2)),
      }
    }));
    setNotice("Weights automatically normalized to sum to 1.00");
    setTimeout(() => setNotice(null), 3000);
  };

  const handleReset = () => {
    setSettings({ ...DEFAULT_SYSTEM_SETTINGS });
    setNotice("Decision weights successfully restored to default baseline: Risk 0.35, Exposure 0.20, Network 0.25, Deferral 0.20");
    setTimeout(() => setNotice(null), 4000);
  };

  const handleSave = () => {
    setNotice("Settings successfully saved and decision engine weights calibrated.");
    setTimeout(() => setNotice(null), 3500);
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-sky-950 text-sky-400 border border-sky-800">
              CALIBRATION & PREFERENCES
            </span>
            <span className="text-xs font-mono text-slate-500">GOVERNANCE CONTROLS</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-100">
            System & Decision Weights Settings
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Calibrate multi-criteria decision trade-offs, default fiscal appropriations, and backend pipeline data sources
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleReset}
            aria-label="Reset weights to default values"
            title="Reset to default baseline weights"
            className="px-3 py-1.5 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 transition-colors flex items-center gap-1.5"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Reset to Default
          </button>
          <button
            onClick={handleSave}
            disabled={!isNormalized}
            aria-label="Save and apply configuration settings"
            title={!isNormalized ? "Please normalize weights to sum to 1.00" : "Save settings"}
            className="px-4 py-1.5 rounded-md bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white text-xs font-medium transition-colors flex items-center gap-1.5 shadow-sm"
          >
            <Check className="w-3.5 h-3.5" />
            Apply Settings
          </button>
        </div>
      </div>

      {notice && (
        <div className="p-3 bg-emerald-950/60 border border-emerald-800 rounded-lg text-xs text-emerald-300 flex items-center gap-2 transition-all">
          <Check className="w-4 h-4 shrink-0" />
          <span>{notice}</span>
        </div>
      )}

      {/* Decision Weights Calibration */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
              <Sliders className="w-4 h-4 text-sky-400" />
              Multi-Attribute Decision Weights (Σ = 1.00)
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Control the relative influence of physical condition vs socio-economic disruption in global ranking
            </p>
          </div>
          <div className="text-right">
            <span className={`text-xs font-mono font-bold px-2.5 py-1 rounded border ${
              isNormalized ? 'bg-emerald-950 text-emerald-300 border-emerald-800' : 'bg-rose-950 text-rose-300 border-rose-800'
            }`}>
              Weight Sum: {totalWeights.toFixed(2)} / 1.00
            </span>
          </div>
        </div>

        {!isNormalized && (
          <div className="p-3 bg-rose-950/30 border border-rose-900/60 rounded flex items-center justify-between text-xs text-rose-300">
            <span className="flex items-center gap-1.5">
              <AlertCircle className="w-4 h-4" />
              Weights do not sum to 1.00. Automatic normalization recommended.
            </span>
            <button
              onClick={handleNormalize}
              aria-label="Automatically normalize weights to sum to 1.00"
              className="px-2.5 py-1 rounded bg-rose-900/60 hover:bg-rose-900 text-rose-100 font-medium"
            >
              Auto-Normalize
            </button>
          </div>
        )}

        <div className="space-y-4 pt-2">
          {/* Structural Risk Weight */}
          <div className="p-3 bg-slate-950/80 rounded border border-slate-800 space-y-2">
            <div className="flex justify-between text-xs">
              <label htmlFor="weight-risk" className="font-semibold text-slate-200">1. Structural Deterioration Risk (w₁)</label>
              <span className="font-mono text-sky-400 font-bold">{settings.weights.structuralRisk.toFixed(2)}</span>
            </div>
            <input
              id="weight-risk"
              type="range"
              aria-label="Structural Deterioration Risk Weight"
              min="0.1"
              max="0.6"
              step="0.05"
              value={settings.weights.structuralRisk}
              onChange={(e) => handleWeightChange('structuralRisk', parseFloat(e.target.value))}
              className="w-full h-1.5 bg-slate-800 rounded appearance-none cursor-pointer accent-sky-500"
            />
            <p className="text-[11px] text-slate-400">Emphasizes fatigue cracking, deck delamination, and pier scour urgency.</p>
          </div>

          {/* Public Consequence / Detour */}
          <div className="p-3 bg-slate-950/80 rounded border border-slate-800 space-y-2">
            <div className="flex justify-between text-xs">
              <label htmlFor="weight-criticality" className="font-semibold text-slate-200">2. Public Consequence & Detour Burden (w₂)</label>
              <span className="font-mono text-amber-400 font-bold">{settings.weights.networkCriticality.toFixed(2)}</span>
            </div>
            <input
              id="weight-criticality"
              type="range"
              aria-label="Public Consequence Weight"
              min="0.1"
              max="0.5"
              step="0.05"
              value={settings.weights.networkCriticality}
              onChange={(e) => handleWeightChange('networkCriticality', parseFloat(e.target.value))}
              className="w-full h-1.5 bg-slate-800 rounded appearance-none cursor-pointer accent-amber-500"
            />
            <p className="text-[11px] text-slate-400">Emphasizes bypass detour mileage, emergency trauma access, and commuter disruption.</p>
          </div>

          {/* Traffic Exposure */}
          <div className="p-3 bg-slate-950/80 rounded border border-slate-800 space-y-2">
            <div className="flex justify-between text-xs">
              <label htmlFor="weight-exposure" className="font-semibold text-slate-200">3. Traffic Volume & Truck Exposure (w₃)</label>
              <span className="font-mono text-emerald-400 font-bold">{settings.weights.trafficExposure.toFixed(2)}</span>
            </div>
            <input
              id="weight-exposure"
              type="range"
              aria-label="Traffic Exposure Weight"
              min="0.1"
              max="0.4"
              step="0.05"
              value={settings.weights.trafficExposure}
              onChange={(e) => handleWeightChange('trafficExposure', parseFloat(e.target.value))}
              className="w-full h-1.5 bg-slate-800 rounded appearance-none cursor-pointer accent-emerald-500"
            />
            <p className="text-[11px] text-slate-400">Emphasizes ADT density and heavy commercial truck freight stress.</p>
          </div>

          {/* Deferral Urgency */}
          <div className="p-3 bg-slate-950/80 rounded border border-slate-800 space-y-2">
            <div className="flex justify-between text-xs">
              <label htmlFor="weight-deferral" className="font-semibold text-slate-200">4. Life-Cycle Deferral Urgency (w₄)</label>
              <span className="font-mono text-rose-400 font-bold">{settings.weights.deferralUrgency.toFixed(2)}</span>
            </div>
            <input
              id="weight-deferral"
              type="range"
              aria-label="Deferral Urgency Weight"
              min="0.1"
              max="0.4"
              step="0.05"
              value={settings.weights.deferralUrgency}
              onChange={(e) => handleWeightChange('deferralUrgency', parseFloat(e.target.value))}
              className="w-full h-1.5 bg-slate-800 rounded appearance-none cursor-pointer accent-rose-500"
            />
            <p className="text-[11px] text-slate-400">Penalizes assets exhibiting rapid compounding degradation if delayed 24 months.</p>
          </div>
        </div>
      </div>

      {/* Fiscal & Planning Horizon Settings */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-5 space-y-4">
        <h3 className="text-sm font-semibold text-slate-200">Fiscal Planning & Threshold Constraints</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div className="p-3 bg-slate-950/80 rounded border border-slate-800">
            <label htmlFor="currency-select" className="text-slate-400 block mb-1">Currency & Unit System</label>
            <select
              id="currency-select"
              aria-label="Currency and Unit System"
              value={settings.currencyUnit}
              onChange={(e) => setSettings(prev => ({ ...prev, currencyUnit: e.target.value as any }))}
              className="w-full bg-slate-900 border border-slate-800 rounded px-2.5 py-1.5 text-xs text-slate-200 mt-1 focus:outline-none focus:border-sky-500"
            >
              <option value="INR (Crores)">INR (Crores ₹ Cr)</option>
              <option value="USD (Millions)">USD (Millions $ M)</option>
            </select>
          </div>

          <div className="p-3 bg-slate-950/80 rounded border border-slate-800">
            <label htmlFor="horizon-select" className="text-slate-400 block mb-1">Default Planning Horizon</label>
            <select
              id="horizon-select"
              aria-label="Planning Horizon"
              value={settings.planningHorizonYears}
              onChange={(e) => setSettings(prev => ({ ...prev, planningHorizonYears: parseInt(e.target.value) }))}
              className="w-full bg-slate-900 border border-slate-800 rounded px-2.5 py-1.5 text-xs text-slate-200 mt-1 focus:outline-none focus:border-sky-500"
            >
              <option value="1">1 Year Fiscal Horizon</option>
              <option value="2">2 Years (Multi-Cycle Life-Cycle)</option>
              <option value="5">5 Years (Strategic Master Plan)</option>
            </select>
          </div>
        </div>
      </div>

      {/* Backend & Data Pipeline Mode */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-5 space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
            <Database className="w-4 h-4 text-sky-400" />
            Data Source Adapter & Pipeline Mode
          </h3>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-950/60 border border-amber-800 text-amber-300 font-semibold">
            SIMULATION ISOLATION ACTIVE
          </span>
        </div>
        <p className="text-xs text-slate-400">
          The application frontend currently interacts with the verified simulation service layer. In Phase 15+, this will bridge to the FastAPI ingestion service without modifying the UI architecture.
        </p>

        <div className="p-3 bg-slate-950/80 rounded border border-slate-800 text-xs flex items-center justify-between">
          <div>
            <span className="font-semibold text-slate-200 block">Current Service Endpoint Adapter</span>
            <span className="font-mono text-slate-400 text-[11px]">frontend/src/services/api/* (Mock Service Protocol)</span>
          </div>
          <span className="px-2 py-1 rounded bg-slate-800 text-slate-300 font-mono text-[11px]">
            Ready for Backend Swap
          </span>
        </div>
      </div>
    </div>
  );
};
