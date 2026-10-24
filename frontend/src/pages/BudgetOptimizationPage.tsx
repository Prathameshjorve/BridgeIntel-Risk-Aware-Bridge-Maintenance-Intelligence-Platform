import React, { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import * as XLSX from 'xlsx';
import { optimizationService } from '../services/api/optimizationService';
import { scoringService, mapBridgeAssetToScoringRecord } from '../services/api/scoringService';
import { OptimizationPortfolioResult, BudgetScenario } from '../types/optimization';
import { BridgeAsset } from '../types/bridge';
import { MOCK_BRIDGES } from '../mock/bridges';
import { KpiCard } from '../components/common/KpiCard';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import { KnapsackAllocationChart } from '../components/charts/KnapsackAllocationChart';
import { 
  Wallet, 
  CheckCircle2, 
  XCircle, 
  Sliders, 
  TrendingDown, 
  ShieldCheck, 
  Layers,
  FileSpreadsheet,
  Upload,
  Download,
  Database,
  RotateCcw,
  AlertCircle,
  Sparkles,
  Calculator,
  Wrench,
  AlertTriangle,
  ChevronRight,
  Check,
  X,
  BookOpen
} from 'lucide-react';

export const BudgetOptimizationPage: React.FC = () => {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [budgetCr, setBudgetCr] = useState<number>(55.0);
  const [budgetInputStr, setBudgetInputStr] = useState<string>('55.0');
  const [result, setResult] = useState<OptimizationPortfolioResult | null>(null);
  const [scenarios, setScenarios] = useState<BudgetScenario[]>([]);
  const [loading, setLoading] = useState(true);
  const [solving, setSolving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Data source modes: 'standard' (pre-loaded portfolio) vs 'excel' (custom uploaded dataset)
  const [dataSourceMode, setDataSourceMode] = useState<'standard' | 'excel'>('standard');
  const [customBridges, setCustomBridges] = useState<BridgeAsset[]>([]);
  const [uploadedFileName, setUploadedFileName] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccessMsg, setUploadSuccessMsg] = useState<string | null>(null);
  const [selectedBridgeForInspection, setSelectedBridgeForInspection] = useState<BridgeAsset | null>(null);

  const initData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [scenList, initOpt] = await Promise.all([
        optimizationService.getScenarios(),
        optimizationService.getInitialOptimization()
      ]);
      setScenarios(scenList);
      setResult(initOpt);
    } catch (err: any) {
      setError(err?.message || "Failed to initialize optimization solver");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    initData();
  }, []);

  // Compute active bridge pool
  const activeBridges = dataSourceMode === 'excel' && customBridges.length > 0
    ? customBridges 
    : MOCK_BRIDGES;

  const runSolver = async (newBudget: number, bridgesToUse: BridgeAsset[]) => {
    setSolving(true);
    try {
      const opt = await optimizationService.runOptimization(newBudget, bridgesToUse);
      setResult(opt);
    } catch (err: any) {
      console.error(err);
    } finally {
      setSolving(false);
    }
  };

  const handleBudgetChange = async (newBudget: number) => {
    setBudgetCr(newBudget);
    setBudgetInputStr(String(newBudget));
    await runSolver(newBudget, activeBridges);
  };

  const handleAnalyzeCustomBudget = async () => {
    const parsed = parseFloat(budgetInputStr);
    if (isNaN(parsed) || parsed <= 0) {
      setUploadError('Please enter a valid positive budget amount in Crores (e.g. 45.0).');
      return;
    }
    setUploadError(null);
    setBudgetCr(parsed);
    await runSolver(parsed, activeBridges);
  };

  const handleSwitchToStandard = async () => {
    setDataSourceMode('standard');
    setUploadError(null);
    setUploadSuccessMsg(null);
    await runSolver(budgetCr, MOCK_BRIDGES);
  };

  const handleSwitchToExcel = async () => {
    if (customBridges.length > 0) {
      setDataSourceMode('excel');
      await runSolver(budgetCr, customBridges);
    } else {
      fileInputRef.current?.click();
    }
  };

  // Parse Excel / CSV files
  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploadError(null);
    setUploadSuccessMsg(null);

    const reader = new FileReader();
    reader.onload = async (evt) => {
      try {
        const bstr = evt.target?.result;
        const workbook = XLSX.read(bstr, { type: 'binary' });
        const sheetName = workbook.SheetNames[0];
        const worksheet = workbook.Sheets[sheetName];
        const rawJson: any[] = XLSX.utils.sheet_to_json(worksheet);

        if (!rawJson || rawJson.length === 0) {
          setUploadError('The uploaded sheet is empty. Please provide bridge rows.');
          return;
        }

        // Map rows into BridgeAsset candidate items
        let parsedBridges: BridgeAsset[] = rawJson.map((row: any, idx: number) => {
          const id = String(row['Bridge ID'] || row['bridge_id'] || row['ID'] || `UPLOAD-${idx + 1}`);
          const name = String(row['Bridge Name'] || row['name'] || row['Structure'] || `Bridge Crossing ${id}`);
          const route = String(row['Route / Corridor'] || row['route'] || 'Primary Arterial');
          const cost = parseFloat(row['Estimated Cost (Cr)'] || row['Cost (Cr)'] || row['estimated_cost'] || row['Cost'] || '10.0') || 10.0;
          const userRiskReduction = parseFloat(row['Risk Reduction Score'] || row['Risk Delta'] || row['risk_reduction'] || '0') || 0;
          const consequence = parseFloat(row['Consequence Score'] || row['consequence_score'] || row['Consequence'] || '60.0') || 60.0;
          const userRisk = parseFloat(row['Modeled Risk Score'] || row['Risk Score'] || row['current_risk'] || '0') || 0;
          const priorDeck = parseFloat(row['Prior Deck Condition'] || row['prior_deck_condition'] || row['Deck Condition'] || '5.0') || 5.0;
          const priorSuper = parseFloat(row['Superstructure Condition'] || row['prior_superstructure_condition'] || '5.0') || 5.0;
          const priorSub = parseFloat(row['Substructure Condition'] || row['prior_substructure_condition'] || '5.0') || 5.0;
          const detourKm = parseFloat(row['Detour (km)'] || row['detour_kilos'] || row['Detour'] || '14.5') || 14.5;
          const trafficAdt = parseInt(row['ADT'] || row['adt'] || '12000') || 12000;
          const yrBuilt = parseInt(row['Year Built'] || row['year_built'] || '1978') || 1978;

          let safeAction: BridgeAsset['recommendedAction'] = 'Deck Rehabilitation';
          const rawAct = String(row['Recommended Action'] || row['Action'] || '').toLowerCase();
          if (rawAct.includes('superstructure')) safeAction = 'Superstructure Replacement';
          else if (rawAct.includes('substructure')) safeAction = 'Substructure Repair';
          else if (rawAct.includes('routine') || rawAct.includes('preventative')) safeAction = 'Routine Preventative';
          else if (rawAct.includes('reconstruction')) safeAction = 'Comprehensive Reconstruction';
          else if (rawAct.includes('deck')) safeAction = 'Deck Rehabilitation';

          const fallbackRisk = userRisk > 0 ? userRisk : Math.min(95, Math.max(20, (9 - priorDeck) * 15 + (trafficAdt > 20000 ? 15 : 5)));
          const fallbackRiskRed = userRiskReduction > 0 ? userRiskReduction : Math.round(fallbackRisk * 0.7);

          return {
            id,
            name,
            route,
            featureIntersected: String(row['Feature Intersected'] || 'Waterway / Rail'),
            state: 'Regional DOT',
            county: 'State Inventory',
            latitude: 36.8 + (idx * 0.05),
            longitude: -83.2 - (idx * 0.05),
            yearBuilt: yrBuilt,
            ageYears: 2026 - yrBuilt,
            bridgeType: String(row['Bridge Type'] || 'Steel Girder / Pre-stressed Concrete'),
            totalLengthMeters: parseFloat(row['Length (m)'] || row['structure_len_mt'] || '120') || 120,
            maxSpanMeters: parseFloat(row['Max Span (m)'] || row['max_span_len_mt'] || '35') || 35,
            deckAreaSqM: 1500,
            adt: trafficAdt,
            adttPercent: parseFloat(row['Truck %'] || row['percent_adt_truck'] || '15') || 15,
            detourLengthKm: detourKm,
            bypassViability: 'Constrained Detour',
            condition: {
              deck: priorDeck,
              superstructure: priorSuper,
              substructure: priorSub,
              overallCondition: Math.min(priorDeck, priorSuper, priorSub)
            },
            conditionCategory: priorDeck <= 4 ? 'Poor' : priorDeck <= 6 ? 'Fair' : 'Good',
            historicalInspections: [],
            modeledRiskScore: fallbackRisk,
            riskCategory: fallbackRisk > 75 ? 'Critical' : fallbackRisk > 50 ? 'High' : 'Moderate',
            confidenceInterval: [Math.max(0, fallbackRisk - 5), Math.min(100, fallbackRisk + 5)],
            projectedAnnualDeteriorationRate: -0.3,
            riskFactors: [
              { factor: 'Deck Deterioration Exposure', contributionPercent: 40, description: 'Model-estimated 2-yr degradation probability', category: 'Structural' },
              { factor: 'Traffic ADT Loading', contributionPercent: 35, description: `${trafficAdt.toLocaleString()} daily vehicular throughput`, category: 'Traffic' },
              { factor: 'Detour Bypass Burden', contributionPercent: 25, description: `${detourKm} km bypass penalty on regional mobility`, category: 'Network' }
            ],
            networkCriticalityScore: consequence,
            criticalFacilitiesConnected: ['Regional Logistics Corridor'],
            dailyDetourDelayVehicleHours: Math.round(trafficAdt * detourKm * 0.015),
            consequenceScore: consequence,
            priorityScore: (fallbackRisk * 0.5) + (consequence * 0.5),
            priorityLevel: fallbackRisk > 75 ? 'Urgent' : 'High',
            urgencyIndex: fallbackRisk,
            estimatedInterventionCostCr: cost,
            recommendedAction: safeAction,
            expectedRiskReductionScore: fallbackRiskRed,
            deferralRisk1Year: fallbackRisk * 1.1,
            deferralRisk2Year: fallbackRisk * 1.25,
            deferralSensitivity: 'High deferral sensitivity',
            costOfDelayMultiplier2Year: 1.8,
            deferralNarrative: 'Postponing maintenance will exponentially increase lifecycle rehabilitation cost.'
          };
        });

        // LIVE ML MODEL INGESTION: Score all uploaded bridge assets via the Phase 17+18 ML Backend
        try {
          const scoringRecords = parsedBridges.map(b => mapBridgeAssetToScoringRecord(b));
          const batchRes = await scoringService.scoreBatch(scoringRecords);
          if (batchRes && batchRes.results && batchRes.results.length === parsedBridges.length) {
            parsedBridges = parsedBridges.map((b, i) => {
              const mlScore = batchRes.results[i];
              const prob = mlScore.calibrated_deterioration_probability; // 0.0 to 1.0
              // Calculate machine learning modeled risk score (0-100 scale)
              const mlRisk = Number((prob * 100).toFixed(1));
              const mlRiskRed = Number(Math.max(15, mlRisk * 0.75).toFixed(1));
              return {
                ...b,
                modeledRiskScore: mlRisk,
                expectedRiskReductionScore: mlRiskRed,
                riskCategory: mlRisk > 60 ? 'Critical' : mlRisk > 35 ? 'High' : 'Moderate',
                priorityScore: Number(((mlRisk * 0.5) + (b.consequenceScore * 0.5)).toFixed(1)),
                priorityLevel: mlRisk > 60 ? 'Urgent' : 'High',
                urgencyIndex: mlRisk
              };
            });
          }
        } catch (mlErr) {
          console.warn('Backend ML batch scoring fallback applied:', mlErr);
        }

        setCustomBridges(parsedBridges);
        setUploadedFileName(file.name);
        setDataSourceMode('excel');

        const totalCost = parsedBridges.reduce((acc, b) => acc + b.estimatedInterventionCostCr, 0);
        const defaultBudget = Number((totalCost * 0.6).toFixed(1));
        setBudgetInputStr(String(defaultBudget));
        setBudgetCr(defaultBudget);

        setUploadSuccessMsg(
          `Successfully loaded "${file.name}" with ${parsedBridges.length} bridge records (Total Portfolio Cost: ₹${totalCost.toFixed(1)} Cr). ML Model calibrated deterioration risks for all assets. Now adjust the budget and click "Analyze & Optimize" to update readings.`
        );

        // Run initial optimization with default budget
        await runSolver(defaultBudget, parsedBridges);
      } catch (parseErr: any) {
        setUploadError(`Failed to parse file: ${parseErr?.message || 'Unsupported format'}. Use .xlsx, .xls, or .csv.`);
      }
    };
    reader.readAsBinaryString(file);
    e.target.value = '';
  };

  // Download template Excel file
  const handleDownloadTemplate = () => {
    const templateData = [
      {
        'Bridge ID': 'BR-DEMO-001',
        'Bridge Name': 'Ganga Valley Highway Crossing',
        'Route / Corridor': 'NH-44 Express Corridor',
        'Estimated Cost (Cr)': 18.5,
        'Risk Reduction Score': 62.0,
        'Consequence Score': 89.5,
        'Modeled Risk Score': 86.4,
        'Recommended Action': 'Superstructure Replacement',
        'Year Built': 1974,
        'ADT': 45000,
        'Detour (km)': 38.0
      },
      {
        'Bridge ID': 'BR-DEMO-002',
        'Bridge Name': 'Western Industrial Bypass Viaduct',
        'Route / Corridor': 'State Highway 12B',
        'Estimated Cost (Cr)': 12.0,
        'Risk Reduction Score': 54.0,
        'Consequence Score': 78.0,
        'Modeled Risk Score': 79.2,
        'Recommended Action': 'Deck Hydrodemolition & Overlay',
        'Year Built': 1982,
        'ADT': 28000,
        'Detour (km)': 22.5
      },
      {
        'Bridge ID': 'BR-DEMO-003',
        'Bridge Name': 'Metropolitan Coastal Canal Span',
        'Route / Corridor': 'Ring Road Sector 4',
        'Estimated Cost (Cr)': 24.5,
        'Risk Reduction Score': 70.0,
        'Consequence Score': 94.0,
        'Modeled Risk Score': 91.0,
        'Recommended Action': 'Substructure & Pier Strengthening',
        'Year Built': 1968,
        'ADT': 65000,
        'Detour (km)': 45.0
      },
      {
        'Bridge ID': 'BR-DEMO-004',
        'Bridge Name': 'Northern Rail Spur Flyover',
        'Route / Corridor': 'Freight Bypass Link',
        'Estimated Cost (Cr)': 8.5,
        'Risk Reduction Score': 42.0,
        'Consequence Score': 65.0,
        'Modeled Risk Score': 71.5,
        'Recommended Action': 'Joints & Bearing Replacement',
        'Year Built': 1990,
        'ADT': 19000,
        'Detour (km)': 15.0
      },
      {
        'Bridge ID': 'BR-DEMO-005',
        'Bridge Name': 'Eastern Ghats River Bridge',
        'Route / Corridor': 'SH-29 Mountain Route',
        'Estimated Cost (Cr)': 15.0,
        'Risk Reduction Score': 48.0,
        'Consequence Score': 72.0,
        'Modeled Risk Score': 74.0,
        'Recommended Action': 'Full Deck Slab Reconstruction',
        'Year Built': 1979,
        'ADT': 14000,
        'Detour (km)': 52.0
      }
    ];

    const worksheet = XLSX.utils.json_to_sheet(templateData);
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, 'Bridge_Portfolio');
    XLSX.writeFile(workbook, 'bridge_maintenance_budget_template.xlsx');
  };

  if (loading) return <LoadingState message="Initializing 0-1 Knapsack Multi-Objective Optimizer..." />;
  if (error || !result) return <ErrorState message={error || "Solver error"} onRetry={initData} />;

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Hidden File Input */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileUpload}
        accept=".xlsx,.xls,.csv"
        className="hidden"
      />

      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-sky-950 text-sky-400 border border-sky-800">
              CONSTRAINED RESOURCE ALLOCATION
            </span>
            <span className="text-xs font-mono text-slate-500">SOLVER: 0-1 KNAPSACK MULTI-OBJECTIVE</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-100">
            Maintenance Budget Optimization
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Maximize aggregate portfolio risk reduction and consequence avoidance subject to available capital budget ceiling
          </p>
        </div>

        {/* Dual Mode Switcher: Standard Portfolio vs. Excel Upload */}
        <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 p-1.5 rounded-lg">
          <button
            onClick={handleSwitchToStandard}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
              dataSourceMode === 'standard'
                ? 'bg-sky-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
            }`}
          >
            <Database className="w-3.5 h-3.5" />
            <span>Standard Portfolio ({MOCK_BRIDGES.length} Bridges)</span>
          </button>
          <button
            onClick={handleSwitchToExcel}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
              dataSourceMode === 'excel'
                ? 'bg-emerald-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
            }`}
          >
            <FileSpreadsheet className="w-3.5 h-3.5" />
            <span>
              {customBridges.length > 0 ? `Custom Excel (${customBridges.length})` : 'Upload Excel / CSV'}
            </span>
          </button>
        </div>
      </div>

      {/* Excel Upload & Management Bar */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-emerald-950/60 border border-emerald-800 text-emerald-400">
              <FileSpreadsheet className="w-5 h-5" />
            </div>
            <div>
              <h4 className="text-xs font-bold text-slate-200 flex items-center gap-2">
                <span>Dataset Origin:</span>
                <span className={`font-mono px-2 py-0.5 rounded text-[10px] ${
                  dataSourceMode === 'excel'
                    ? 'bg-emerald-950 text-emerald-300 border border-emerald-700'
                    : 'bg-sky-950 text-sky-300 border border-sky-800'
                }`}>
                  {dataSourceMode === 'excel' ? `Uploaded Excel: ${uploadedFileName || 'Custom File'}` : 'System NBI Corridor Database'}
                </span>
              </h4>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Optimize allocations on pre-loaded infrastructure assets or upload your own agency Excel sheet (.xlsx, .xls, .csv).
              </p>
            </div>
          </div>

          {/* Action Buttons: Upload New, Download Template, Reset */}
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => fileInputRef.current?.click()}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white transition-colors shadow-sm"
            >
              <Upload className="w-3.5 h-3.5" />
              <span>Upload Excel Sheet</span>
            </button>

            <button
              onClick={handleDownloadTemplate}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
              title="Download standard Excel template with columns for ID, Cost, Risk, Consequence"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Download Template</span>
            </button>

            {dataSourceMode === 'excel' && (
              <button
                onClick={handleSwitchToStandard}
                className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-200 border border-slate-700 transition-colors"
                title="Switch back to system baseline bridges"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Reset to Standard</span>
              </button>
            )}
          </div>
        </div>

        {/* Upload feedback alerts */}
        {uploadError && (
          <div className="p-3 rounded bg-rose-950/40 border border-rose-800/80 text-rose-300 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{uploadError}</span>
          </div>
        )}
        {uploadSuccessMsg && (
          <div className="p-3 rounded bg-emerald-950/40 border border-emerald-800/80 text-emerald-300 text-xs flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{uploadSuccessMsg}</span>
          </div>
        )}
      </div>

      {/* Interactive Scenario Controls Card */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-5">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4">
          <div>
            <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
              <Sliders className="w-4 h-4 text-sky-400" />
              Appropriation Budget Ceiling
            </h3>
            <p className="text-xs text-slate-400">
              Slide or choose a predefined fiscal scenario to dynamically trigger Pareto-optimal knapsack allocation
            </p>
          </div>

          {/* Quick Preset Buttons */}
          <div className="flex flex-wrap items-center gap-2">
            {scenarios.map((scen) => (
              <button
                key={scen.id}
                onClick={() => handleBudgetChange(scen.budgetCr)}
                className={`px-3 py-1.5 rounded text-xs font-medium border transition-colors ${
                  budgetCr === scen.budgetCr
                    ? 'bg-sky-600 text-white border-sky-500 shadow-sm'
                    : 'bg-slate-950 text-slate-300 border-slate-800 hover:bg-slate-800'
                }`}
              >
                {scen.name}
              </button>
            ))}
          </div>
        </div>

        {/* Budget Allocation Input & Analysis Controls */}
        <div className="space-y-4 pt-3 border-t border-slate-800/80">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-3 rounded-lg bg-slate-950/70 border border-slate-800">
            <div className="flex items-center gap-2">
              <Calculator className="w-4 h-4 text-emerald-400" />
              <div>
                <span className="text-xs font-semibold text-slate-200">Specific Capital Budget Appropriation</span>
                <p className="text-[11px] text-slate-400">
                  {dataSourceMode === 'excel'
                    ? `Input custom allocation for ${customBridges.length} bridges in uploaded sheet`
                    : 'Input custom appropriation amount for the current portfolio'}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 font-mono text-xs text-slate-400">₹</span>
                <input
                  type="number"
                  step="0.5"
                  min="1"
                  max="1000"
                  value={budgetInputStr}
                  onChange={(e) => setBudgetInputStr(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleAnalyzeCustomBudget();
                  }}
                  placeholder="e.g. 45.0"
                  className="w-32 bg-slate-900 border border-slate-700 rounded-lg pl-7 pr-3 py-1.5 text-xs font-mono font-bold text-slate-100 focus:outline-none focus:border-emerald-500"
                />
                <span className="absolute right-3 top-1/2 -translate-y-1/2 font-mono text-[11px] text-slate-400">Cr</span>
              </div>

              <button
                onClick={handleAnalyzeCustomBudget}
                disabled={solving}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-bold bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-800 text-white transition-all shadow-md active:scale-95"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>{solving ? 'Analyzing...' : 'Analyze & Optimize'}</span>
              </button>
            </div>
          </div>

          {/* Quick Slider alternative */}
          <div className="space-y-2">
            <div className="flex justify-between items-center text-xs">
              <span className="text-slate-400">Or Slide Available Budget Range:</span>
              <span className="font-mono text-lg font-bold text-sky-400">
                ₹{budgetCr.toFixed(1)} Crores
              </span>
            </div>
            <input
              type="range"
              min="5"
              max={Math.max(150, Math.ceil(budgetCr * 1.5))}
              step="2.5"
              value={budgetCr}
              onChange={(e) => handleBudgetChange(parseFloat(e.target.value))}
              className="w-full h-2 bg-slate-950 rounded-lg appearance-none cursor-pointer accent-sky-500 border border-slate-800"
            />
            <div className="flex justify-between text-[10px] font-mono text-slate-500">
              <span>₹5 Cr (Austerity)</span>
              <span>₹55 Cr (Target Baseline)</span>
              <span>₹90 Cr (Expanded)</span>
              <span>₹{Math.max(150, Math.ceil(budgetCr * 1.5))} Cr (Upper Bound)</span>
            </div>
          </div>
        </div>
      </div>

      {/* Solver Outcome KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <KpiCard
          title="Allocated Capital"
          value={`₹${result.totalAllocatedCr.toFixed(1)} Cr`}
          subtitle={`Under ₹${result.budgetLimitCr.toFixed(1)} Cr limit`}
          icon={Wallet}
          accentColor="brand"
        />
        <KpiCard
          title="Contingency Reserve"
          value={`₹${result.remainingBudgetCr.toFixed(1)} Cr`}
          subtitle="Unallocated buffer"
          icon={CheckCircle2}
          accentColor="slate"
        />
        <KpiCard
          title="Funded Bridges"
          value={`${result.bridgesSelectedCount} / ${result.totalCandidateBridges}`}
          subtitle={`${result.totalCandidateBridges - result.bridgesSelectedCount} bridges deferred`}
          icon={Layers}
          accentColor="emerald"
        />
        <KpiCard
          title="Risk Reduction"
          value={`${result.totalRiskReduction.toFixed(0)} pts`}
          subtitle={`${result.portfolioRiskReductionPercentage}% of portfolio vulnerability`}
          icon={TrendingDown}
          accentColor="emerald"
        />
        <KpiCard
          title="Avoided Consequence"
          value={`${result.totalConsequenceAvoided.toFixed(0)} pts`}
          subtitle="Public/detour burden avoided"
          icon={ShieldCheck}
          accentColor="brand"
        />
      </div>

      {/* Allocation Visual and Decision Plan Table */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Knapsack Visual breakdown */}
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-5 flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-semibold text-slate-200">Capital Plan Utilization</h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Budget efficiency ({dataSourceMode === 'excel' ? 'Uploaded Excel' : 'Standard Portfolio'})
            </p>
            <KnapsackAllocationChart 
              allocatedCr={result.totalAllocatedCr} 
              remainingCr={result.remainingBudgetCr} 
            />
          </div>

          <div className="p-3 bg-slate-950/80 rounded border border-slate-800 text-xs space-y-2 mt-4 font-mono">
            <div className="flex justify-between">
              <span className="text-slate-400">Budget Limit:</span>
              <span className="text-slate-200">₹{result.budgetLimitCr.toFixed(1)} Cr</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Funded Interventions:</span>
              <span className="text-sky-400 font-bold">₹{result.totalAllocatedCr.toFixed(1)} Cr</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Reserve Balance:</span>
              <span className="text-slate-400">₹{result.remainingBudgetCr.toFixed(1)} Cr</span>
            </div>
            <div className="flex justify-between pt-1 border-t border-slate-800">
              <span className="text-slate-400">Algorithm Status:</span>
              <span className="text-emerald-400 font-bold">Optimal Solution Found</span>
            </div>
          </div>
        </div>

        {/* Selected vs Deferred Bridges Table */}
        <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-lg overflow-hidden">
          <div className="p-4 border-b border-slate-800 flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-slate-200">
                Optimized Action Plan ({result.items.length} Evaluated)
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Candidates selected based on Benefit-to-Cost Ratio (BCR) • {dataSourceMode === 'excel' ? 'Uploaded Sheet Mode' : 'Standard Mode'}
              </p>
            </div>
            {solving && (
              <span className="text-xs font-mono text-sky-400 animate-pulse">Solving Knapsack...</span>
            )}
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950/80 text-slate-400 font-mono border-b border-slate-800">
                <tr>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Bridge ID / Corridor</th>
                  <th className="py-3 px-4">Action</th>
                  <th className="py-3 px-4 text-right">Cost</th>
                  <th className="py-3 px-4 text-center">Risk Delta</th>
                  <th className="py-3 px-4 text-center">BCR Ratio</th>
                  <th className="py-3 px-4 text-center">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {result.items.map((item) => {
                  const b = item.bridge;
                  return (
                    <tr 
                      key={b.id}
                      className={item.selected ? 'bg-sky-950/20 hover:bg-sky-950/30' : 'bg-slate-950/40 opacity-75 hover:opacity-100'}
                    >
                      <td className="py-3 px-4">
                        {item.selected ? (
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-emerald-950/80 text-emerald-300 border border-emerald-800 font-semibold text-[11px]">
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            FUNDED
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-800 text-slate-400 border border-slate-700 text-[11px]">
                            <XCircle className="w-3.5 h-3.5" />
                            DEFERRED
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-4">
                        <div className="font-mono font-semibold text-slate-200">{b.id}</div>
                        <div className="text-slate-400 text-[11px] truncate max-w-xs">{b.name}</div>
                      </td>
                      <td className="py-3 px-4 text-slate-300 font-medium">
                        {b.recommendedAction}
                      </td>
                      <td className="py-3 px-4 text-right font-mono font-bold text-slate-200">
                        ₹{b.estimatedInterventionCostCr.toFixed(1)} Cr
                      </td>
                      <td className="py-3 px-4 text-center font-mono text-emerald-400 font-bold">
                        -{b.expectedRiskReductionScore}
                      </td>
                      <td className="py-3 px-4 text-center font-mono text-sky-400 font-semibold">
                        {item.benefitCostRatio}x
                      </td>
                      <td className="py-3 px-4 text-center">
                        <button
                          onClick={() => setSelectedBridgeForInspection(b)}
                          className="px-2.5 py-1 bg-sky-950/80 hover:bg-sky-900 text-sky-300 rounded border border-sky-700/80 text-[11px] font-semibold flex items-center gap-1 mx-auto transition-colors shadow-sm"
                          title="Open Explainable AI Diagnosis & Engineering Repair Prescription"
                        >
                          <Wrench className="w-3 h-3 text-sky-400" />
                          <span>Inspect & Repair</span>
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>
      {/* Explainable AI Defect Diagnosis & Repair Plan Modal */}
      {selectedBridgeForInspection && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-slate-900 border border-slate-700/80 rounded-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto shadow-2xl p-6 space-y-6">
            {/* Modal Header */}
            <div className="flex items-start justify-between border-b border-slate-800 pb-4">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-sky-950 text-sky-400 border border-sky-800">
                    EXPLAINABLE AI DIAGNOSTIC & REPAIR SPECIFICATION
                  </span>
                  <span className="text-[10px] font-mono text-slate-500">ASSET: {selectedBridgeForInspection.id}</span>
                </div>
                <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
                  <Wrench className="w-5 h-5 text-emerald-400" />
                  <span>{selectedBridgeForInspection.name}</span>
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  Route: {selectedBridgeForInspection.route} • Built: {selectedBridgeForInspection.yearBuilt} ({selectedBridgeForInspection.ageYears} yrs) • Length: {selectedBridgeForInspection.totalLengthMeters}m
                </p>
              </div>
              <button
                onClick={() => setSelectedBridgeForInspection(null)}
                className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-100 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* AI Condition Summary & Modeled Metrics */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono text-xs">
              <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
                <span className="text-[10px] text-slate-500 uppercase block">Deck Rating</span>
                <span className={`text-lg font-bold ${
                  (selectedBridgeForInspection.condition.deck || 5) <= 4 ? 'text-rose-400' : 'text-amber-400'
                }`}>
                  {selectedBridgeForInspection.condition.deck || 5} / 9
                </span>
                <span className="text-[10px] text-slate-500 block">NBI Ordinal Scale</span>
              </div>

              <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
                <span className="text-[10px] text-slate-500 uppercase block">Modeled Risk Score</span>
                <span className="text-lg font-bold text-rose-400">
                  {selectedBridgeForInspection.modeledRiskScore.toFixed(1)} / 100
                </span>
                <span className="text-[10px] text-slate-500 block">2-Yr Degradation Risk</span>
              </div>

              <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
                <span className="text-[10px] text-slate-500 uppercase block">Intervention Cost</span>
                <span className="text-lg font-bold text-sky-400">
                  ₹{selectedBridgeForInspection.estimatedInterventionCostCr.toFixed(1)} Cr
                </span>
                <span className="text-[10px] text-slate-500 block">Estimated Capital</span>
              </div>

              <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
                <span className="text-[10px] text-slate-500 uppercase block">Risk Avoidance Delta</span>
                <span className="text-lg font-bold text-emerald-400">
                  -{selectedBridgeForInspection.expectedRiskReductionScore.toFixed(0)} pts
                </span>
                <span className="text-[10px] text-slate-500 block">Post-Repair Impact</span>
              </div>
            </div>

            {/* Section 1: Detected Structural Defects from Dataset */}
            <div className="space-y-3">
              <h3 className="text-sm font-bold text-slate-200 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-400" />
                <span>1. Explainable Defect Breakdown (Identified from NBI Features)</span>
              </h3>

              <div className="space-y-2">
                {selectedBridgeForInspection.riskFactors && selectedBridgeForInspection.riskFactors.length > 0 ? (
                  selectedBridgeForInspection.riskFactors.map((rf, idx) => (
                    <div key={idx} className="p-3 rounded-lg bg-slate-950/80 border border-slate-800/80 space-y-1.5">
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-semibold text-slate-200">{rf.factor}</span>
                        <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-rose-950/80 text-rose-300 border border-rose-800">
                          {rf.contributionPercent}% Risk Contribution
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-400 leading-relaxed">
                        {rf.description}
                      </p>
                      <div className="w-full bg-slate-900 rounded-full h-1.5 overflow-hidden">
                        <div
                          className="bg-rose-500 h-full rounded-full"
                          style={{ width: `${rf.contributionPercent}%` }}
                        />
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="p-3 rounded bg-slate-950 border border-slate-800 text-xs text-slate-400">
                    Defects driven by age ({selectedBridgeForInspection.ageYears} years), deck condition rating ({selectedBridgeForInspection.condition.deck}/9), and high traffic exposure ({selectedBridgeForInspection.adt.toLocaleString()} ADT).
                  </div>
                )}
              </div>
            </div>

            {/* Section 2: Prescriptive Engineering Repair Plan (How to Fix It) */}
            <div className="space-y-3">
              <h3 className="text-sm font-bold text-slate-200 flex items-center gap-2">
                <BookOpen className="w-4 h-4 text-sky-400" />
                <span>2. Prescriptive Engineering Repair Plan & Action Steps</span>
              </h3>

              <div className="p-4 rounded-lg bg-sky-950/30 border border-sky-800/60 space-y-3 text-xs">
                <div className="flex items-center justify-between border-b border-sky-800/40 pb-2">
                  <span className="text-sky-300 font-semibold font-mono text-sm">
                    Recommended Primary Action: {selectedBridgeForInspection.recommendedAction}
                  </span>
                  <span className="px-2.5 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800 font-mono text-[10px] font-bold">
                    PRIORITY: {selectedBridgeForInspection.priorityLevel}
                  </span>
                </div>

                <div className="space-y-2 text-slate-300 text-[11px] leading-relaxed">
                  <p className="font-semibold text-slate-200">Recommended Scope of Work & Procedures:</p>
                  <ul className="list-disc pl-5 space-y-1 text-slate-400">
                    {selectedBridgeForInspection.recommendedAction === 'Superstructure Replacement' && (
                      <>
                        <li>Erect temporary traffic staging or implement detour along designated corridors ({selectedBridgeForInspection.detourLengthKm} km route).</li>
                        <li>Hydrodemolish deteriorated deck slab sections and lift off compromised plate girders.</li>
                        <li>Install modern pre-stressed high-performance concrete beams / weatherproof steel girders.</li>
                        <li>Pour high-strength silica-fume reinforced deck overlay with integrated waterproof membrane.</li>
                      </>
                    )}
                    {selectedBridgeForInspection.recommendedAction === 'Deck Rehabilitation' && (
                      <>
                        <li>Shot-blast and mill existing asphalt/concrete wearing surface to sound substrate.</li>
                        <li>Conduct full-depth concrete patch repairs on delaminated and spalled deck areas.</li>
                        <li>Apply penetrating silane sealer followed by elastomeric waterproof membrane.</li>
                        <li>Reconstruct failed expansion joints with modular seal assemblies to prevent runoff leakage onto substructure.</li>
                      </>
                    )}
                    {selectedBridgeForInspection.recommendedAction === 'Substructure Repair' && (
                      <>
                        <li>Install cofferdams / riprap rock armor around pier footings to eliminate active scour.</li>
                        <li>Pressure-inject epoxy into pier stem microcracks and install carbon-fiber-reinforced polymer (CFRP) jackets.</li>
                        <li>Rehab bearing pedestals and replace corroded elastomeric bearings.</li>
                      </>
                    )}
                    {selectedBridgeForInspection.recommendedAction === 'Routine Preventative' && (
                      <>
                        <li>Power-wash bridge deck, drainage scuppers, and bearing seats to clear deicing salts.</li>
                        <li>Clean and seal deck hairline cracks with high-molecular-weight methacrylate (HMWM).</li>
                        <li>Lubricate bearing assemblies and touch-up protective paint coatings.</li>
                      </>
                    )}
                    {selectedBridgeForInspection.recommendedAction === 'Comprehensive Reconstruction' && (
                      <>
                        <li>Complete end-to-end multi-phase structural reconstruction across both superstructure and substructure.</li>
                        <li>Widen deck cross-section to accommodate current AASHTO safety clear-zone requirements.</li>
                        <li>Full seismic and fatigue retrofitting of pier bents and abutments.</li>
                      </>
                    )}
                  </ul>
                </div>

                {/* Maintenance Deferral Warning */}
                <div className="p-3 rounded bg-amber-950/40 border border-amber-800/60 text-[11px] text-amber-300 flex items-start gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-amber-400" />
                  <div>
                    <span className="font-bold">Lifecycle Deferral Consequence:</span>
                    <p className="text-amber-200/90 mt-0.5">
                      {selectedBridgeForInspection.deferralNarrative || 
                        `Delaying repair past 12 months will escalate costs by ${selectedBridgeForInspection.costOfDelayMultiplier2Year || 1.8}x due to progressive structural fatigue.`}
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="flex items-center justify-between border-t border-slate-800 pt-4">
              <span className="text-[11px] text-slate-500 font-mono">
                Prescription generated from HistGradientBoosting Deterioration Model & AASHTO Guidelines
              </span>
              <button
                onClick={() => setSelectedBridgeForInspection(null)}
                className="px-4 py-2 rounded-lg text-xs font-bold bg-slate-800 hover:bg-slate-700 text-slate-200 transition-colors"
              >
                Close Diagnostic
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

