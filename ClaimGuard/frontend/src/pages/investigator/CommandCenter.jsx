import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import StatCard from '../../components/ui/StatCard';
import Badge from '../../components/ui/Badge';
import PageHeader from '../../components/ui/PageHeader';
import ClaimsBarChart from '../../components/charts/ClaimsBarChart';
import RiskBarChart from '../../components/charts/RiskBarChart';
import { investigations as initialInvestigations, claims, alerts as initialAlerts } from '../../data/mockData';
import { investigationsAPI, notificationsAPI } from '../../services/api';
import {
  Search, AlertTriangle, CheckCircle, Clock,
  ArrowRight, Flame
} from 'lucide-react';

export default function CommandCenter() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [invList, setInvList] = useState(initialInvestigations);
  const [alertList, setAlertList] = useState(initialAlerts);

  useEffect(() => {
    investigationsAPI.getAll()
      .then(res => {
        if (Array.isArray(res) && res.length > 0) {
          const mapped = res.map(i => ({
            id: `INV-2024-00${i.id}`,
            realId: i.id,
            claimId: `CLM-2024-00${i.claim_id}`,
            provider: 'Riverside Medical Center',
            investigatorId: i.assigned_to,
            status: i.status === 'in_review' ? 'in_progress' : i.status,
            priority: i.priority || 'medium',
            openedDate: i.created_at ? i.created_at.split('T')[0] : '2024-07-15',
            dueDate: '2024-07-29',
            amount: 48200,
            type: i.reason || 'Billing Anomaly',
            description: i.notes || '',
            aiRiskScore: 82,
          }));
          setInvList(mapped);
        }
      })
      .catch(() => { /* keep initial */ });

    notificationsAPI.getAll()
      .then(res => {
        if (Array.isArray(res) && res.length > 0) {
          const mapped = res.map(n => ({
            id: `ALT-00${n.id}`,
            type: n.notification_type || 'info',
            message: n.message,
            date: n.created_at ? n.created_at.split('T')[0] : '2024-07-18',
            read: n.is_read,
          }));
          setAlertList(mapped);
        }
      })
      .catch(() => { /* keep initial */ });
  }, []);

  const myInvs = invList;
  const openCases = myInvs.filter(i => i.status === 'in_progress' || i.status === 'open').length;
  const criticalCases = myInvs.filter(i => i.priority === 'critical').length;
  const recentAlerts = alertList.filter(a => !a.read);


  return (
    <div className="space-y-6">
      <PageHeader
        title={`Command Center`}
        subtitle={`Welcome back, ${user?.name}. You have ${openCases} active investigations.`}
        actions={
          <button className="btn-primary" onClick={() => navigate('/investigator/queue')}>
            <Search size={15} /> View Queue
          </button>
        }
      />

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="Open Cases" value={openCases} icon={Search} iconBg="bg-rose-50" iconColor="text-rose-600" />
        <StatCard title="Critical" value={criticalCases} icon={Flame} iconBg="bg-red-50" iconColor="text-red-500" />
        <StatCard title="Resolved (30d)" value={8} icon={CheckCircle} iconBg="bg-emerald-50" iconColor="text-emerald-600" />
        <StatCard title="Avg. Resolution" value="9.2d" icon={Clock} iconBg="bg-violet-50" iconColor="text-violet-600" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* My Active Investigations */}
        <div className="card lg:col-span-2">
          <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
            <h3 className="section-title">My Active Investigations</h3>
            <button className="text-sm text-rose-600 hover:text-rose-700 font-medium" onClick={() => navigate('/investigator/queue')}>View all</button>
          </div>
          <div className="divide-y divide-slate-50">
            {myInvs.filter(i => i.status === 'in_progress').map(inv => {
              const relatedClaim = claims.find(c => c.id === inv.claimId);
              return (
                <div key={inv.id} className="flex items-center gap-4 px-5 py-3.5 hover:bg-slate-50 transition-colors cursor-pointer"
                  onClick={() => navigate(`/investigations/${inv.id}`)}>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <span className="text-xs font-mono font-bold text-rose-700">{inv.id}</span>
                      <Badge status={inv.priority} size="xs" />
                      <Badge status={inv.status} size="xs" />
                    </div>
                    <p className="text-sm font-semibold text-slate-800 truncate">{inv.type}</p>
                    <div className="flex items-center gap-3 text-xs text-slate-500 mt-1 flex-wrap">
                      <span>Provider: <strong className="text-slate-700">{inv.provider}</strong></span>
                      <span>Claim: <Link to={`/claims/${inv.claimId}`} className="font-mono text-rose-600 font-semibold hover:underline" onClick={e => e.stopPropagation()}>{inv.claimId}</Link></span>
                      <span>Assigned: {inv.investigatorName || 'Ram Patel'}</span>
                    </div>
                  </div>
                  <div className="flex flex-col items-end gap-1 flex-shrink-0">
                    <span className="text-base font-bold text-slate-800">${inv.amount.toLocaleString()}</span>
                  </div>
                  <ArrowRight size={15} className="text-slate-300 flex-shrink-0" />
                </div>
              );
            })}
          </div>
        </div>

        {/* Alerts */}
        <div className="card">
          <div className="px-5 py-4 border-b border-slate-100">
            <h3 className="section-title">Recent Alerts</h3>
          </div>
          <div className="divide-y divide-slate-50">
            {recentAlerts.slice(0, 4).map(a => (
              <div key={a.id} className="px-4 py-3">
                <div className="flex items-start gap-2">
                  <AlertTriangle size={13} className={a.type === 'critical' ? 'text-red-500 mt-0.5' : 'text-amber-500 mt-0.5'} />
                  <div>
                    <p className="text-xs text-slate-700 leading-relaxed">{a.message}</p>
                    <p className="text-xs text-slate-400 mt-0.5">{a.date}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Critical Priority Investigation Queue Component */}
      <div className="card">
        <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
          <h3 className="section-title">Critical Priority Investigation Queue</h3>
          <span className="text-xs text-slate-500">Sorted by priority level</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr>
                {['CLAIM ID', 'PROVIDER', 'PROCEDURE', 'PRIORITY', 'STATUS', 'ACTION'].map(h => (
                  <th key={h} className="table-header">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {invList.map(inv => {
                const c = claims.find(cl => cl.id === inv.claimId);
                return (
                  <tr key={inv.id} className="table-row">
                    <td className="table-cell font-mono text-xs font-bold text-rose-600">
                      <Link to={`/claims/${inv.claimId}`} className="hover:underline">{inv.claimId}</Link>
                    </td>
                    <td className="table-cell font-medium text-slate-800">{inv.provider}</td>
                    <td className="table-cell text-slate-600">{c?.diagnosis || inv.type}</td>
                    <td className="table-cell"><Badge status={inv.priority} /></td>
                    <td className="table-cell"><Badge status={inv.status} /></td>
                    <td className="table-cell">
                      <button className="btn-primary text-xs py-1 px-3" onClick={() => navigate(`/investigations/${inv.id}`)}>
                        Investigate
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>

          </table>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div className="card p-5">
          <h3 className="section-title mb-4">Monthly Claims Activity</h3>
          <ClaimsBarChart />
        </div>
        <div className="card p-5">
          <h3 className="section-title mb-4">Risk Score Distribution</h3>
          <RiskBarChart />
        </div>
      </div>
    </div>
  );
}
