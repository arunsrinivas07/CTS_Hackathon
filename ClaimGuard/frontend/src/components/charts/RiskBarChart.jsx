import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell
} from 'recharts';
import { riskDistributionData } from '../../data/mockData';

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
      <p className="font-semibold text-slate-700">Risk {label}</p>
      <p className="text-slate-600">Claims: <strong>{payload[0].value}</strong></p>
    </div>
  );
};

export default function RiskBarChart({ data = riskDistributionData }) {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} barSize={32}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
        <XAxis dataKey="range" tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
        <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
        <Tooltip content={<CustomTooltip />} />
        <Bar dataKey="count" radius={[4, 4, 0, 0]}>
          {data.map((entry, i) => (
            <Cell key={i} fill={getColor(entry.range)} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
