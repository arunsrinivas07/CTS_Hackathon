import { useMemo } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell
} from 'recharts';

const getColor = (range) => {
  const [min] = range.split('-').map(Number);
  if (min >= 80) return '#ef4444';
  if (min >= 60) return '#f59e0b';
  if (min >= 40) return '#eab308';
  if (min >= 20) return '#22c55e';
  return '#10b981';
};

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-slate-200 rounded-lg shadow-sm p-3 text-xs">
      <p className="font-semibold text-slate-700">Risk Range: {label}</p>
      <p className="text-slate-600">Claims Count: <strong>{payload[0].value}</strong></p>
    </div>
  );
};

export default function RiskBarChart({ data, claims }) {
  const chartData = useMemo(() => {
    const rawList = (data && data.length > 0) ? data : (claims || []);

    if (rawList.length > 0 && rawList[0].range !== undefined && rawList[0].count !== undefined) {
      return rawList;
    }

    const ranges = {
      '0-20': 0,
      '21-40': 0,
      '41-60': 0,
      '61-80': 0,
      '81-100': 0,
    };

    if (rawList.length > 0) {
      rawList.forEach(c => {
        const score = c.aiRiskScore || (c.risk_scores && c.risk_scores[0] ? c.risk_scores[0].overall_score : 50);
        if (score <= 20) ranges['0-20'] += 1;
        else if (score <= 40) ranges['21-40'] += 1;
        else if (score <= 60) ranges['41-60'] += 1;
        else if (score <= 80) ranges['61-80'] += 1;
        else ranges['81-100'] += 1;
      });
      return Object.entries(ranges).map(([range, count]) => ({ range, count }));
    }

    return [
      { range: '0-20', count: 14 },
      { range: '21-40', count: 28 },
      { range: '41-60', count: 42 },
      { range: '61-80', count: 19 },
      { range: '81-100', count: 8 },
    ];
  }, [data, claims]);

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={chartData} barSize={32}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
        <XAxis dataKey="range" tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
        <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
        <Tooltip content={<CustomTooltip />} />
        <Bar dataKey="count" radius={[4, 4, 0, 0]}>
          {chartData.map((entry, i) => (
            <Cell key={i} fill={getColor(entry.range)} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
