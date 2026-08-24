import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-slate-200 rounded-lg shadow-sm p-3 text-xs">
      <p className="font-semibold text-slate-700 mb-2">{label}</p>
      {payload.map(p => (
        <p key={p.name} style={{ color: p.color }}>
          {p.name}: <strong>{p.value}</strong>
        </p>
      ))}
    </div>
  );
};

export default function WorkloadChart({ data = [] }) {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} barSize={16} barGap={4}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
        <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
        <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
        <Tooltip content={<CustomTooltip />} />
        <Legend wrapperStyle={{ fontSize: 11 }} formatter={v => <span className="text-slate-500 capitalize">{v}</span>} />
        <Bar dataKey="open" fill="#3b82f6" radius={[3, 3, 0, 0]} name="Open" />
        <Bar dataKey="resolved" fill="#10b981" radius={[3, 3, 0, 0]} name="Resolved" />
      </BarChart>
    </ResponsiveContainer>
  );
}
