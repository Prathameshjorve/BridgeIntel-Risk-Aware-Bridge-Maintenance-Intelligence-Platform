import React from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend, CartesianGrid } from 'recharts';
import { HistoricalInspection } from '../../types/bridge';

interface ConditionTrendChartProps {
  inspections: HistoricalInspection[];
}

export const ConditionTrendChart: React.FC<ConditionTrendChartProps> = ({ inspections }) => {
  return (
    <div className="w-full h-64">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={inspections} margin={{ top: 10, right: 20, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis 
            dataKey="year" 
            stroke="#64748b" 
            fontSize={11} 
            tickLine={false}
          />
          {/* Dual Y-Axes: Left for NBI Condition (0-9), Right for Modeled Risk (0-100) */}
          <YAxis 
            yAxisId="left"
            domain={[0, 9]} 
            stroke="#38bdf8" 
            fontSize={11} 
            tickLine={false}
          />
          <YAxis 
            yAxisId="right"
            orientation="right"
            domain={[0, 100]} 
            stroke="#f43f5e" 
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
          <Line 
            yAxisId="left"
            type="monotone" 
            dataKey="conditionRating" 
            name="NBI Condition Rating (0-9)" 
            stroke="#38bdf8" 
            strokeWidth={2}
            dot={{ r: 4, fill: '#38bdf8' }} 
          />
          <Line 
            yAxisId="right"
            type="monotone" 
            dataKey="modeledRiskScore" 
            name="Modeled Risk Score (0-100)" 
            stroke="#f43f5e" 
            strokeWidth={2}
            strokeDasharray="4 4"
            dot={{ r: 4, fill: '#f43f5e' }} 
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};
