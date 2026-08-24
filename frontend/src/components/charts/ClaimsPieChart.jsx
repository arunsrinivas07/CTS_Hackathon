import { useMemo } from 'react';
import {
  PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer
} from 'recharts';

const COLORS = ['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ec4899', '#6366f1'];

const CustomTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-slate-200 rounded-lg shadow-sm p-3 text-xs">
      <p className="font-semibold text-slate-700">{payload[0].name}</p>
      <p className="text-slate-500">Count: <strong>{payload[0].value}</strong></p>
    </div>
  );
};

export default function ClaimsPieChart({ data, claims }) {
  const chartData = useMemo(() => {
    const rawList = (data && data.length > 0) ? data : (claims || []);

    // Check if data is already pre-aggregated with name/value
    if (rawList.length > 0 && rawList[0].name !== undefined && rawList[0].value !== undefined) {
      return rawList;
    }

    if (rawList.length > 0) {
      const typeCounts = {};
      rawList.forEach(c => {
        let t = c.claim_type || c.type || 'Outpatient';
        t = t.trim().toUpperCase();
        typeCounts[t] = (typeCounts[t] || 0) + 1;
      });

      return Object.entries(typeCounts).map(([name, value]) => ({
        name,
        value,
      }));
    }

    // Default distribution if no database claims exist yet
    return [
      { name: 'OUTPATIENT', value: 45 },
      { name: 'INPATIENT SURGERY', value: 25 },
      { name: 'NEUROLOGY', value: 18 },
      { name: 'PRIMARY CARE', value: 12 },
    ];
  }, [data, claims]);

  return (
    <ResponsiveContainer width="100%" height={220}>
      <PieChart>
        <Pie
          data={chartData}
          cx="50%"
          cy="50%"
          innerRadius={50}
          outerRadius={80}
          paddingAngle={4}
          dataKey="value"
        >
          {chartData.map((_, i) => (
            <Cell key={i} fill={COLORS[i % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip content={<CustomTooltip />} />
        <Legend
          wrapperStyle={{ fontSize: 11 }}
          formatter={v => <span className="text-slate-500 font-medium">{v}</span>}
        />
      </PieChart>
    </ResponsiveContainer>
  );
}
