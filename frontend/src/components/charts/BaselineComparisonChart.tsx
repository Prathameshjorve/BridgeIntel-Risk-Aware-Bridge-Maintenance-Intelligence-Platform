import React from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend, CartesianGrid } from 'recharts';
import { StrategyComparisonMetrics } from '../../types/analytics';

interface BaselineComparisonChartProps {
  comparisons: StrategyComparisonMetrics[];
}

export const BaselineComparisonChart: React.FC<BaselineComparisonChartProps> = ({ comparisons }) => {
  const chartData = comparisons.map(c => ({
    name: c.strategyName.replace(/ \(.*\)/, ''),
    riskReduction: c.totalRiskReduction,
    consequenceAvoided: c.totalConsequenceAvoided,
    efficiency: Number(c.budgetEfficiencyScore.toFixed(2)),
  }));

  return (
    <div className="w-full h-72">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} margin={{ top: 15, right: 20, left: -10, bottom: 25 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis 
            dataKey="name" 
            stroke="#94a3b8" 
            fontSize={11} 
            tickLine={false}
            interval={0}
            angle={-10}
            textAnchor="end"
          />
          <YAxis 
            stroke="#94a3b8" 
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
          <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '16px' }} />
          <Bar dataKey="riskReduction" name="Total Risk Reduction" fill="#0284c7" radius={[4, 4, 0, 0]} />
          <Bar dataKey="consequenceAvoided" name="Consequence Avoided" fill="#10b981" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};
