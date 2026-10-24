import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { networkService } from '../services/api/networkService';
import { NetworkGraphData, CriticalFacility } from '../types/network';
import { BridgeAsset } from '../types/bridge';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import { 
  Building2, 
  Navigation, 
  ExternalLink
} from 'lucide-react';

export const NetworkImpactPage: React.FC = () => {
  const navigate = useNavigate();
  const [networkData, setNetworkData] = useState<NetworkGraphData | null>(null);
  const [selectedBridge, setSelectedBridge] = useState<BridgeAsset | null>(null);
  const [activeLayer, setActiveLayer] = useState<'all' | 'priority' | 'facilities'>('all');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await networkService.getNetworkData();
      setNetworkData(data);
      if (data.bridges.length > 0) {
        setSelectedBridge(data.bridges[0]);
      }
    } catch (err: any) {
      setError(err?.message || "Failed to load network topology");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  if (loading) return <LoadingState message="Calculating network detour burdens and critical facility dependencies..." />;
  if (error || !networkData) return <ErrorState message={error || "Network data unavailable"} onRetry={loadData} />;

  // Normalize map coordinates to SVG 800x450 viewbox
  // Lat range: 36.70 to 36.96, Lng range: -83.52 to -83.15
  const minLat = 36.70;
  const maxLat = 36.96;
  const minLng = -83.52;
  const maxLng = -83.15;

  const toSvgCoords = (lat: number, lng: number) => {
    const x = ((lng - minLng) / (maxLng - minLng)) * 740 + 30;
    const y = 420 - (((lat - minLat) / (maxLat - minLat)) * 390 + 15);
    return { x, y };
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-sky-950 text-sky-400 border border-sky-800">
              NETWORK TOPOLOGY & GIS
            </span>
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-amber-950/60 border border-amber-800 text-amber-300 font-semibold">
              SIMULATED SPATIAL LAYER
            </span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-100">
            Network Criticality & Detour Analysis
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Evaluating how bridge unavailability impacts regional connectivity, commercial freight detours, and emergency healthcare access
          </p>
        </div>

        {/* Layer Controls */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setActiveLayer('all')}
            className={`px-3 py-1.5 rounded text-xs font-medium border transition-colors ${
              activeLayer === 'all'
                ? 'bg-sky-600 text-white border-sky-500'
                : 'bg-slate-900 text-slate-300 border-slate-800 hover:bg-slate-800'
            }`}
          >
            All Assets
          </button>
          <button
            onClick={() => setActiveLayer('priority')}
            className={`px-3 py-1.5 rounded text-xs font-medium border transition-colors ${
              activeLayer === 'priority'
                ? 'bg-sky-600 text-white border-sky-500'
                : 'bg-slate-900 text-slate-300 border-slate-800 hover:bg-slate-800'
            }`}
          >
            Urgent Priorities
          </button>
          <button
            onClick={() => setActiveLayer('facilities')}
            className={`px-3 py-1.5 rounded text-xs font-medium border transition-colors ${
              activeLayer === 'facilities'
                ? 'bg-sky-600 text-white border-sky-500'
                : 'bg-slate-900 text-slate-300 border-slate-800 hover:bg-slate-800'
            }`}
          >
            Emergency Corridors
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Spatial Map View (2 cols) */}
        <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-lg p-5 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
                <Navigation className="w-4 h-4 text-sky-400" />
                Regional Network Spatial Graph
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">Click any bridge node or corridor route to inspect detour metrics</p>
            </div>
            <div className="flex items-center gap-3 text-xs">
              <span className="flex items-center gap-1.5 text-slate-300">
                <span className="w-2.5 h-2.5 rounded-full bg-rose-500" /> Critical Bridge
              </span>
              <span className="flex items-center gap-1.5 text-slate-300">
                <span className="w-2.5 h-2.5 rounded-full bg-amber-500" /> High Priority
              </span>
              <span className="flex items-center gap-1.5 text-slate-300">
                <span className="w-2.5 h-2.5 rounded-full bg-sky-500" /> Standard Asset
              </span>
            </div>
          </div>

          {/* Interactive SVG Map Canvas */}
          <div className="relative w-full h-[420px] bg-slate-950 rounded-lg border border-slate-800/80 overflow-hidden flex items-center justify-center">
            <svg viewBox="0 0 800 450" className="w-full h-full select-none">
              {/* Arterial Connecting Highway Lines */}
              <path
                d="M 50 150 Q 250 190 450 140 T 750 120"
                fill="none"
                stroke="#334155"
                strokeWidth="4"
                strokeDasharray="4 2"
              />
              <path
                d="M 120 380 Q 300 280 500 220 T 720 180"
                fill="none"
                stroke="#1e293b"
                strokeWidth="3"
              />
              <path
                d="M 280 40 L 320 220 L 380 410"
                fill="none"
                stroke="#334155"
                strokeWidth="3"
              />

              {/* Critical Emergency Facility Markers */}
              {networkData.facilities.map((fac) => {
                const { x, y } = toSvgCoords(fac.latitude, fac.longitude);
                return (
                  <g key={fac.id} className="cursor-pointer">
                    <circle cx={x} cy={y} r="14" fill="#0284c7" fillOpacity="0.15" />
                    <rect x={x - 8} y={y - 8} width="16" height="16" rx="3" fill="#0369a1" stroke="#38bdf8" strokeWidth="1.5" />
                    <text x={x} y={y + 3} textAnchor="middle" fill="#ffffff" fontSize="9" fontWeight="bold">H</text>
                    <text x={x} y={y + 18} textAnchor="middle" fill="#94a3b8" fontSize="8" fontFamily="monospace">{fac.name.split(' ')[0]}</text>
                  </g>
                );
              })}

              {/* Bridge Nodes */}
              {networkData.bridges.map((bridge) => {
                const { x, y } = toSvgCoords(bridge.latitude, bridge.longitude);
                const isSelected = selectedBridge?.id === bridge.id;
                const isUrgent = bridge.priorityLevel === 'Urgent';
                const isHigh = bridge.priorityLevel === 'High';

                let nodeColor = '#0284c7';
                if (bridge.riskCategory === 'Critical' || isUrgent) nodeColor = '#ef4444';
                else if (bridge.riskCategory === 'High' || isHigh) nodeColor = '#f59e0b';
                else if (bridge.riskCategory === 'Moderate') nodeColor = '#38bdf8';
                else nodeColor = '#10b981';

                if (activeLayer === 'priority' && !isUrgent && !isHigh) {
                  return null; // filtered out
                }

                return (
                  <g
                    key={bridge.id}
                    onClick={() => setSelectedBridge(bridge)}
                    className="cursor-pointer group"
                  >
                    {isSelected && (
                      <circle cx={x} cy={y} r="18" fill="none" stroke="#38bdf8" strokeWidth="2" strokeDasharray="3 3" className="animate-spin" />
                    )}
                    <circle 
                      cx={x} 
                      cy={y} 
                      r={isSelected ? "9" : "7"} 
                      fill={nodeColor} 
                      stroke="#0f172a" 
                      strokeWidth="2" 
                    />
                    <text 
                      x={x} 
                      y={y - 11} 
                      textAnchor="middle" 
                      fill="#e2e8f0" 
                      fontSize="9" 
                      fontFamily="monospace"
                      fontWeight="bold"
                    >
                      {bridge.id.replace('BR-NBI-', '')}
                    </text>
                  </g>
                );
              })}
            </svg>

            {/* Scale & Legend Overlay */}
            <div className="absolute bottom-3 left-3 bg-slate-900/90 backdrop-blur border border-slate-800 rounded px-2.5 py-1.5 text-[10px] font-mono text-slate-400">
              <span>LAT: 36.70°N - 36.96°N • LNG: -83.52°W - -83.15°W</span>
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
            <span>Portfolio Max Detour: <strong className="font-mono text-slate-200">{networkData.maxDetourKm} km</strong></span>
            <span>Total Daily Detour Burden: <strong className="font-mono text-amber-400">{networkData.totalDetourVehicleHoursPerDay.toLocaleString()} veh-hrs/day</strong></span>
          </div>
        </div>

        {/* Selected Bridge Detour & Vulnerability Panel (1 col) */}
        <div className="space-y-4">
          {selectedBridge ? (
            <div className="bg-slate-900 border border-slate-800 rounded-lg p-5 space-y-4">
              <div className="border-b border-slate-800 pb-3">
                <span className="text-[10px] font-mono text-slate-400 uppercase">Detour & Criticality Analysis</span>
                <h3 className="font-mono font-bold text-lg text-sky-400 mt-1">{selectedBridge.id}</h3>
                <p className="text-xs text-slate-200 font-semibold">{selectedBridge.name}</p>
                <p className="text-[11px] text-slate-400">{selectedBridge.route} • {selectedBridge.featureIntersected}</p>
              </div>

              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="p-3 bg-slate-950/80 rounded border border-slate-800">
                  <span className="text-slate-400 block mb-1">Detour Distance</span>
                  <span className="text-base font-mono font-bold text-slate-100">{selectedBridge.detourLengthKm} km</span>
                  <span className="text-[10px] text-slate-500 block">Required bypass</span>
                </div>
                <div className="p-3 bg-slate-950/80 rounded border border-slate-800">
                  <span className="text-slate-400 block mb-1">Daily Delay Hours</span>
                  <span className="text-base font-mono font-bold text-amber-400">{selectedBridge.dailyDetourDelayVehicleHours.toLocaleString()}</span>
                  <span className="text-[10px] text-slate-500 block">Veh-hrs per day</span>
                </div>
              </div>

              <div className="space-y-3 text-xs">
                <div>
                  <span className="text-slate-400 block mb-1">Traffic Impact Profile:</span>
                  <div className="p-3 bg-slate-950/60 rounded border border-slate-800 space-y-1.5 font-mono">
                    <div className="flex justify-between">
                      <span className="text-slate-400">Average Daily Traffic:</span>
                      <span className="text-slate-200">{selectedBridge.adt.toLocaleString()} ADT</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Truck Freight Volume:</span>
                      <span className="text-amber-400">{selectedBridge.adttPercent}% ADTT</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Bypass Bottleneck:</span>
                      <span className="text-rose-400 font-semibold">{selectedBridge.bypassViability}</span>
                    </div>
                  </div>
                </div>

                <div>
                  <span className="text-slate-400 block mb-1">Emergency Hospital / Hub Connectivity:</span>
                  {selectedBridge.criticalFacilitiesConnected.length > 0 ? (
                    <div className="space-y-1">
                      {selectedBridge.criticalFacilitiesConnected.map((fac, idx) => (
                        <div key={idx} className="p-2 bg-slate-950/80 rounded border border-slate-800 flex items-center gap-2 text-slate-300">
                          <Building2 className="w-3.5 h-3.5 text-sky-400 shrink-0" />
                          <span className="text-[11px] truncate">{fac}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-[11px] text-slate-500 italic p-2 rounded bg-slate-950/40">
                      Standard secondary connector without direct hospital arterial dependencies.
                    </p>
                  )}
                </div>
              </div>

              <button
                onClick={() => navigate(`/bridges/${selectedBridge.id}`)}
                className="w-full py-2 bg-sky-600 hover:bg-sky-500 text-white rounded text-xs font-medium transition-colors flex items-center justify-center gap-2"
              >
                Inspect Structural & Deferral Dossier
                <ExternalLink className="w-3.5 h-3.5" />
              </button>
            </div>
          ) : (
            <div className="p-6 text-center text-slate-500 text-xs">
              Select a node on the network graph to inspect traffic detour and consequence metrics.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
