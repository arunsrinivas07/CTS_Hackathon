import { useMemo } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-slate-200 rounded-lg shadow-sm p-3 text-xs">
      <p className="font-semibold text-slate-700 mb-2">{label}</p>
      {payload.map(p => (
        <p key={p.name} style={{ color: p.color }} className="capitalize">
          {p.name}: <strong>{p.value}</strong>
        </p>
      ))}
    </div>
  );
};

export default function ClaimsBarChart({ data, claims }) {
  const chartData = useMemo(() => {
    const rawList = (data && data.length > 0) ? data : (claims || []);

    // Check if data is already pre-aggregated
    if (rawList.length > 0 && rawList[0].month !== undefined) {
      return rawList;
    }

    // Baseline month slots
    const monthsMap = {
      'Mar': { month: 'Mar', approved: 0, flagged: 0, rejected: 0 },
      'Apr': { month: 'Apr', approved: 0, flagged: 0, rejected: 0 },
      'May': { month: 'May', approved: 0, flagged: 0, rejected: 0 },
      'Jun': { month: 'Jun', approved: 0, flagged: 0, rejected: 0 },
      'Jul': { month: 'Jul', approved: 0, flagged: 0, rejected: 0 },
      'Aug': { month: 'Aug', approved: 0, flagged: 0, rejected: 0 },
    };

    if (rawList.length > 0) {
      rawList.forEach(c => {
        const rawDate = c.service_date || c.created_at || c.date;
        let mName = 'Aug';
        if (rawDate) {
          try {
            const d = new Date(rawDate);
            if (!isNaN(d.getTime())) {
              mName = d.toLocaleString('en-US', { month: 'short' });
            }
          } catch (_) {
            mName = 'Aug';
          }
        }
        if (!monthsMap[mName]) {
          monthsMap[mName] = { month: mName, approved: 0, flagged: 0, rejected: 0 };
        }

        const st = (c.status || '').toLowerCase();
        if (st.includes('approve') || st.includes('paid')) {
          monthsMap[mName].approved += 1;
        } else if (st.includes('flag') || st.includes('review') || st.includes('process') || st.includes('submit')) {
          monthsMap[mName].flagged += 1;
        } else if (st.includes('deni') || st.includes('reject')) {
          monthsMap[mName].rejected += 1;
        } else {
          monthsMap[mName].flagged += 1;
        }
      });
    } else {
      // Baseline fallbacks if no database claims exist yet
      monthsMap['Mar'] = { month: 'Mar', approved: 12, flagged: 3, rejected: 1 };
      monthsMap['Apr'] = { month: 'Apr', approved: 18, flagged: 4, rejected: 2 };
      monthsMap['May'] = { month: 'May', approved: 24, flagged: 6, rejected: 1 };
      monthsMap['Jun'] = { month: 'Jun', approved: 30, flagged: 8, rejected: 3 };
      monthsMap['Jul'] = { month: 'Jul', approved: 28, flagged: 5, rejected: 2 };
      monthsMap['Aug'] = { month: 'Aug', approved: 35, flagged: 9, rejected: 4 };
    }

    return Object.values(monthsMap);
  }, [data, claims]);

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={chartData} barSize={12} barGap={3}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
        <XAxis dataKey="month" tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
        <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
        <Tooltip content={<CustomTooltip />} />
        <Legend
          wrapperStyle={{ fontSize: 11, paddingTop: 8 }}
          formatter={v => <span className="text-slate-500 capitalize">{v}</span>}
        />
        <Bar dataKey="approved" name="Approved" fill="#10b981" radius={[3, 3, 0, 0]} />
        <Bar dataKey="flagged" name="Under Review / Flagged" fill="#f59e0b" radius={[3, 3, 0, 0]} />
        <Bar dataKey="rejected" name="Rejected / Denied" fill="#ef4444" radius={[3, 3, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
