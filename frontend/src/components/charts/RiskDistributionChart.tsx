import React from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { BridgeAsset } from '../../types/bridge';

interface RiskDistributionChartProps {
  bridges: BridgeAsset[];
}

export const RiskDistributionChart: React.FC<RiskDistributionChartProps> = ({ bridges }) => {
  const categories = [
    { name: 'Low', count: bridges.filter(b => b.riskCategory === 'Low').length, color: '#10b981' },
    { name: 'Moderate', count: bridges.filter(b => b.riskCategory === 'Moderate').length, color: '#f59e0b' },
    { name: 'High', count: bridges.filter(b => b.riskCategory === 'High').length, color: '#f97316' },
    { name: 'Critical', count: bridges.filter(b => b.riskCategory === 'Critical').length, color: '#ef4444' },
  ];

  return (
    <div className="w-full h-56">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={categories} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
          <XAxis 
            dataKey="name" 
            stroke="#64748b" 
            fontSize={11} 
            tickLine={false}
          />
          <YAxis 
            stroke="#64748b" 
            fontSize={11} 
            tickLine={false}
            allowDecimals={false}
          />
          <Tooltip 
            contentStyle={{ 
              backgroundColor: '#0f172a', 
              borderColor: '#334155', 
              borderRadius: '6px',
              fontSize: '12px'
            }}
            formatter={(value: any) => [`${value} Bridges`, 'Count']}
          />
          <Bar dataKey="count" radius={[4, 4, 0, 0]}>
            {categories.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};
