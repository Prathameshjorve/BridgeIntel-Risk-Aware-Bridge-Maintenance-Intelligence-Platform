import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';

interface KnapsackAllocationChartProps {
  allocatedCr: number;
  remainingCr: number;
}

export const KnapsackAllocationChart: React.FC<KnapsackAllocationChartProps> = ({
  allocatedCr,
  remainingCr
}) => {
  const data = [
    { name: 'Allocated Interventions', value: allocatedCr, color: '#0284c7' },
    { name: 'Remaining Contingency', value: remainingCr, color: '#334155' },
  ];

  return (
    <div className="w-full h-52">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={45}
            outerRadius={70}
            paddingAngle={4}
            dataKey="value"
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip 
            contentStyle={{ 
              backgroundColor: '#0f172a', 
              borderColor: '#334155', 
              borderRadius: '6px',
              fontSize: '12px'
            }}
            formatter={(value: any) => [`₹${Number(value).toFixed(2)} Cr`, 'Amount']}
          />
          <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '4px' }} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
};
