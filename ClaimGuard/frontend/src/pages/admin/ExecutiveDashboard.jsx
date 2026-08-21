import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import StatCard from '../../components/ui/StatCard';
import Badge from '../../components/ui/Badge';
import RiskMeter from '../../components/ui/RiskMeter';
import PageHeader from '../../components/ui/PageHeader';
import ClaimsBarChart from '../../components/charts/ClaimsBarChart';
import SavingsLineChart from '../../components/charts/SavingsLineChart';
import ClaimsPieChart from '../../components/charts/ClaimsPieChart';
import { claimsAPI, investigationsAPI, providersAPI, notificationsAPI, usersAPI } from '../../services/api';
import {
  FileText, Search, AlertTriangle, DollarSign,
  TrendingUp, Users, Loader2
} from 'lucide-react';

export default function ExecutiveDashboard() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [claims, setClaims] = useState([]);
  const [investigations, setInvestigations] = useState([]);
  const [providers, setProviders] = useState([]);
  const [users, setUsers] = useState([]);
  const [alerts, setAlerts] = useState([]);

  useEffect(() => {
    Promise.allSettled([
      claimsAPI.getAll(),
      investigationsAPI.getAll(),
      providersAPI.getAll(),
      usersAPI.getAll(),
      notificationsAPI.getAll(),
    ]).then(([c, i, p, u, a]) => {
      if (c.status === 'fulfilled' && Array.isArray(c.value)) setClaims(c.value);
      if (i.status === 'fulfilled' && Array.isArray(i.value)) setInvestigations(i.value);
      if (p.status === 'fulfilled' && Array.isArray(p.value)) setProviders(p.value);
      if (u.status === 'fulfilled' && Array.isArray(u.value)) setUsers(u.value);
      if (a.status === 'fulfilled' && Array.isArray(a.value)) setAlerts(a.value);
      setLoading(false);
    });
  }, []);

  const totalClaims = claims.length;
  const openInvs = investigations.filter(i => i.status !== 'resolved' && i.status !== 'closed').length;
  const flaggedClaims = claims.filter(c => c.status === 'flagged' || c.status === 'under_review').length;
  const totalBilled = claims.reduce((s, c) => s + parseFloat(c.total_billed_amount || 0), 0);
  const activeInvestigators = users.filter(u => {
    const r = (u.role || '').toLowerCase();
    return r.includes('invest') || u.role_id === 2;
  }).length;
  const unreadAlerts = alerts.filter(a => !a.is_read).length;

  // Map providers to display shape
  const providerDisplay = providers.map(p => ({
    id: p.id,
    name: p.name || `Provider #${p.id}`,
    type: p.provider_type || 'Hospital',
    location: p.address || 'N/A',
    riskScore: p.risk_score || 50,
    riskLevel: (p.risk_score || 50) >= 70 ? 'high' : (p.risk_score || 50) >= 40 ? 'medium' : 'low',
  }));

  // Map investigations to display shape
  const invDisplay = investigations.map(i => ({
    id: i.id,
    provider: `Provider #${i.claim_id}`,
    type: i.reason || i.investigation_type || 'FWA Review',
    amount: parseFloat(i.estimated_fraud_amount || 0),
    priority: i.priority || 'medium',
    status: i.status === 'in_review' ? 'in_progress' : (i.status || 'open'),
    investigatorName: i.assigned_to ? `Agent #${i.assigned_to}` : null,
  }));

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 gap-3 text-slate-400">
        <Loader2 size={22} className="animate-spin" />
        <span className="text-sm">Loading dashboard…</span>
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title="Executive Dashboard"
        subtitle="System-wide overview of claims, investigations, and risk metrics."
      />

      {/* KPI Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <StatCard title="Total Claims" value={totalClaims} icon={FileText} iconBg="bg-rose-50" iconColor="text-rose-600" trend={12} trendLabel="vs last month" />
        <StatCard title="Open Investigations" value={openInvs} icon={Search} iconBg="bg-violet-50" iconColor="text-violet-600" />
        <StatCard title="Flagged Claims" value={flaggedClaims} icon={AlertTriangle} iconBg="bg-amber-50" iconColor="text-amber-600" />
        <StatCard title="Total Billed" value={`$${(totalBilled / 1000).toFixed(0)}k`} icon={DollarSign} iconBg="bg-emerald-50" iconColor="text-emerald-600" />
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <StatCard title="High-Risk Providers" value={providerDisplay.filter(p => p.riskLevel === 'high').length} icon={AlertTriangle} iconBg="bg-red-50" iconColor="text-red-500" />
        <StatCard title="Active Investigators" value={activeInvestigators} icon={Users} iconBg="bg-rose-50" iconColor="text-rose-600" />
        <StatCard title="Savings This Month" value="$139k" icon={TrendingUp} iconBg="bg-emerald-50" iconColor="text-emerald-600" trend={8} trendLabel="vs last month" />
        <StatCard title="Unread Alerts" value={unreadAlerts} icon={AlertTriangle} iconBg="bg-amber-50" iconColor="text-amber-500" />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 mb-5">
        <div className="card p-5 lg:col-span-2">
          <h3 className="section-title mb-4">Monthly Claims Overview</h3>
          <ClaimsBarChart claims={claims} />
        </div>
        <div className="card p-5">
          <h3 className="section-title mb-4">Claims by Type</h3>
          <ClaimsPieChart claims={claims} />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 mb-5">
        <div className="card p-5">
          <h3 className="section-title mb-4">Fraud Savings Trend</h3>
          <SavingsLineChart />
        </div>

        {/* Provider Risk Snapshot */}
        <div className="card">
          <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
            <h3 className="section-title">Provider Risk Snapshot</h3>
            <button className="text-sm text-rose-600 font-medium hover:text-rose-700" onClick={() => navigate('/admin/risk-matrix')}>
              Full matrix
            </button>
          </div>
          <div className="divide-y divide-slate-50">
            {providerDisplay.length === 0 ? (
              <p className="text-sm text-slate-400 px-5 py-4">No providers found.</p>
            ) : providerDisplay.map(p => (
              <div key={p.id} className="flex items-center gap-4 px-5 py-3 hover:bg-slate-50 transition-colors">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-800 truncate">{p.name}</p>
                  <p className="text-xs text-slate-400">{p.type} · {p.location}</p>
                </div>
                <RiskMeter score={p.riskScore} />
                <Badge status={p.riskLevel} size="xs" />
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Recent Investigations */}
      <div className="card">
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
          <h3 className="section-title">Recent Investigations</h3>
          <button className="text-sm text-rose-600 font-medium hover:text-rose-700" onClick={() => navigate('/admin/investigations')}>
            View all
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr>
                {['Investigation ID', 'Provider', 'Type', 'Amount', 'Priority', 'Status', 'Investigator'].map(h => (
                  <th key={h} className="table-header whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {invDisplay.length === 0 ? (
                <tr><td colSpan={7} className="text-center py-8 text-slate-400 text-sm">No investigations yet.</td></tr>
              ) : invDisplay.slice(0, 8).map(inv => (
                <tr key={inv.id} className="table-row">
                  <td className="table-cell font-mono text-xs text-rose-700 font-semibold">INV-{String(inv.id).padStart(4, '0')}</td>
                  <td className="table-cell text-slate-600 max-w-[130px] truncate">{inv.provider}</td>
                  <td className="table-cell text-slate-500 max-w-[130px] truncate">{inv.type}</td>
                  <td className="table-cell font-semibold">${inv.amount.toLocaleString()}</td>
                  <td className="table-cell"><Badge status={inv.priority} size="xs" /></td>
                  <td className="table-cell"><Badge status={inv.status} /></td>
                  <td className="table-cell text-slate-500">{inv.investigatorName || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
