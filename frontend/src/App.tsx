import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppShell } from './components/layout/AppShell';
import { DashboardPage } from './pages/DashboardPage';
import { BridgePortfolioPage } from './pages/BridgePortfolioPage';
import { BridgeDetailPage } from './pages/BridgeDetailPage';
import { PriorityRankingPage } from './pages/PriorityRankingPage';
import { BudgetOptimizationPage } from './pages/BudgetOptimizationPage';
import { DeferralIntelligencePage } from './pages/DeferralIntelligencePage';
import { NetworkImpactPage } from './pages/NetworkImpactPage';
import { AnalyticsPage } from './pages/AnalyticsPage';
import { MethodologyPage } from './pages/MethodologyPage';
import { SettingsPage } from './pages/SettingsPage';

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<AppShell />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="bridges" element={<BridgePortfolioPage />} />
          <Route path="bridges/:id" element={<BridgeDetailPage />} />
          <Route path="priority" element={<PriorityRankingPage />} />
          <Route path="optimization" element={<BudgetOptimizationPage />} />
          <Route path="deferral" element={<DeferralIntelligencePage />} />
          <Route path="network" element={<NetworkImpactPage />} />
          <Route path="analytics" element={<AnalyticsPage />} />
          <Route path="methodology" element={<MethodologyPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
};

export default App;
