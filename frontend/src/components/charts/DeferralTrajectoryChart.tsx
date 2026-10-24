import React from 'react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from 'recharts';
import { DeferralTrajectoryPoint } from '../../types/deferral';

interface DeferralTrajectoryChartProps {
  trajectories: DeferralTrajectoryPoint[];
}

export const DeferralTrajectoryChart: React.FC<DeferralTrajectoryChartProps> = ({ trajectories }) => {
  return (
    <div className="w-full h-64">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={trajectories} margin={{ top: 10, right: 20, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id="riskGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.4}/>
              <stop offset="95%" stopColor="#f43f5e" stopOpacity={0.0}/>
            </linearGradient>
            <linearGradient id="costGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#eab308" stopOpacity={0.3}/>
              <stop offset="95%" stopColor="#eab308" stopOpacity={0.0}/>
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis 
            dataKey="horizonLabel" 
            stroke="#64748b" 
            fontSize={11} 
            tickLine={false}
          />
          <YAxis 
            yAxisId="risk"
            domain={[0, 100]} 
            stroke="#f43f5e" 
            fontSize={11} 
            tickLine={false}
          />
          <YAxis 
            yAxisId="cost"
            orientation="right"
            stroke="#eab308" 
            fontSize={11} 
            tickLine={false}
          />
          <Tooltip 
            contentStyle={{ 
              backgroundColor: '#0f172a', 
              borderColor: '#334155', 
              borderRadius: '6px',
              fontSize: '12px'
            }}
          />
          <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
          <Area 
            yAxisId="risk"
            type="monotone" 
            dataKey="averageRiskScore" 
            name="Avg Portfolio Risk Score" 
            stroke="#f43f5e" 
            strokeWidth={2}
            fillOpacity={1} 
            fill="url(#riskGrad)" 
          />
          <Area 
            yAxisId="cost"
            type="monotone" 
            dataKey="projectedPortfolioDegradationCostCr" 
            name="Cost Penalty of Deferral (₹ Cr)" 
            stroke="#eab308" 
            strokeWidth={2}
            fillOpacity={1} 
            fill="url(#costGrad)" 
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};
