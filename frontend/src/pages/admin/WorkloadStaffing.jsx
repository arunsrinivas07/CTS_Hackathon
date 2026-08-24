import { useState, useEffect } from 'react';
import PageHeader from '../../components/ui/PageHeader';
import Badge from '../../components/ui/Badge';
import Avatar from '../../components/ui/Avatar';
import WorkloadChart from '../../components/charts/WorkloadChart';
import { usersAPI, investigationsAPI } from '../../services/api';
import { Loader2 } from 'lucide-react';

export default function WorkloadStaffing() {
  const [investigators, setInvestigators] = useState([]);
  const [investigations, setInvestigations] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.allSettled([usersAPI.getAll(), investigationsAPI.getAll()]).then(([uRes, iRes]) => {
      let invUsers = [];
      if (uRes.status === 'fulfilled' && Array.isArray(uRes.value)) {
        invUsers = uRes.value
          .filter(u => (u.role || '').toLowerCase().includes('invest') || u.role_id === 2)
          .map((u, idx) => ({
            id: u.id,
            name: u.full_name,
            email: u.email || '',
            status: u.is_active !== false ? 'active' : 'inactive',
            specialization: 'FWA Investigations',
            avatar: (u.full_name || 'U').split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2),
            joinedDate: u.created_at ? u.created_at.slice(0, 10) : 'N/A',
          }));
        setInvestigators(invUsers);
      }
      if (iRes.status === 'fulfilled' && Array.isArray(iRes.value)) {
        setInvestigations(iRes.value);
      }
      setLoading(false);
    });
  }, []);

  const getOpenCases = (invId) => investigations.filter(i => i.assigned_to === invId && i.status !== 'resolved' && i.status !== 'closed').length;
  const getResolvedCases = (invId) => investigations.filter(i => i.assigned_to === invId && (i.status === 'resolved' || i.status === 'closed')).length;

  const totalOpen = investigators.reduce((s, i) => s + getOpenCases(i.id), 0);
  const totalResolved = investigators.reduce((s, i) => s + getResolvedCases(i.id), 0);

  return (
    <div>
      <PageHeader title="Workload & Staffing" subtitle="Monitor investigator capacity, case distribution, and performance." />

      {loading ? (
        <div className="flex items-center justify-center h-40 gap-2 text-slate-400">
          <Loader2 size={18} className="animate-spin" /> Loading staffing data...
        </div>
      ) : (
        <>
          {/* Stats */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
            {[
              { label: 'Active Investigators', value: investigators.filter(i => i.status === 'active').length, color: 'text-rose-700' },
              { label: 'Total Open Cases', value: totalOpen, color: 'text-amber-600' },
              { label: 'Resolved (All Time)', value: totalResolved, color: 'text-emerald-600' },
              { label: 'Total Investigators', value: investigators.length, color: 'text-violet-600' },
            ].map(({ label, value, color }) => (
              <div key={label} className="card p-4">
                <p className={`text-2xl font-bold ${color}`}>{value}</p>
                <p className="text-xs text-slate-500 mt-1">{label}</p>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 mb-5">
            <div className="card p-5">
              <h3 className="section-title mb-4">Case Distribution by Investigator</h3>
              <WorkloadChart investigators={investigators} getOpenCases={getOpenCases} />
            </div>
            <div className="card p-5">
              <h3 className="section-title mb-4">Capacity Overview</h3>
              <div className="space-y-4">
                {investigators.length === 0 ? (
                  <p className="text-sm text-slate-400">No investigators found.</p>
                ) : investigators.map((inv, idx) => {
                  const openCases = getOpenCases(inv.id);
                  const maxCases = 8;
                  const pct = Math.min((openCases / maxCases) * 100, 100);
                  const color = pct >= 75 ? 'bg-red-500' : pct >= 50 ? 'bg-amber-400' : 'bg-emerald-500';
                  return (
                    <div key={inv.id}>
                      <div className="flex items-center justify-between mb-1">
                        <div className="flex items-center gap-2">
                          <Avatar initials={inv.avatar} size="sm" colorIndex={idx} />
                          <span className="text-sm font-medium text-slate-800">{inv.name}</span>
                          <Badge status={inv.status} size="xs" />
                        </div>
                        <span className="text-xs text-slate-500">{openCases}/{maxCases} cases</span>
                      </div>
                      <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                        <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${pct}%` }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Investigator Table */}
          <div className="card overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-100">
              <h3 className="section-title">Investigator Performance</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr>
                    {['Investigator', 'Specialization', 'Status', 'Open Cases', 'Resolved', 'Joined'].map(h => (
                      <th key={h} className="table-header whitespace-nowrap">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {investigators.map((inv, idx) => (
                    <tr key={inv.id} className="table-row">
                      <td className="table-cell">
                        <div className="flex items-center gap-2">
                          <Avatar initials={inv.avatar} size="sm" colorIndex={idx} />
                          <div>
                            <p className="text-sm font-medium text-slate-800">{inv.name}</p>
                            <p className="text-xs text-slate-400">{inv.email}</p>
                          </div>
                        </div>
                      </td>
                      <td className="table-cell text-slate-500">{inv.specialization}</td>
                      <td className="table-cell"><Badge status={inv.status} /></td>
                      <td className="table-cell">
                        <span className={`text-sm font-semibold ${getOpenCases(inv.id) >= 6 ? 'text-red-600' : getOpenCases(inv.id) >= 4 ? 'text-amber-600' : 'text-slate-800'}`}>
                          {getOpenCases(inv.id)}
                        </span>
                      </td>
                      <td className="table-cell font-semibold text-emerald-600">{getResolvedCases(inv.id)}</td>
                      <td className="table-cell text-slate-500">{inv.joinedDate}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
