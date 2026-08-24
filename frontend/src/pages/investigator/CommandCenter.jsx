import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import StatCard from '../../components/ui/StatCard';
import Badge from '../../components/ui/Badge';
import PageHeader from '../../components/ui/PageHeader';
import ClaimsBarChart from '../../components/charts/ClaimsBarChart';
import RiskBarChart from '../../components/charts/RiskBarChart';
import { claimsAPI, notificationsAPI } from '../../services/api';
import {
  Search, AlertTriangle, CheckCircle, Clock,
  ArrowRight, Flame
} from 'lucide-react';

export default function CommandCenter() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [invList, setInvList] = useState([]);
  const [alertList, setAlertList] = useState([]);

  useEffect(() => {
    let isMounted = true;
    claimsAPI.getAll()
      .then(res => {
        if (Array.isArray(res) && isMounted) {
          const mapped = res.map(c => {
            const risk = c.risk_scores && c.risk_scores.length > 0 ? c.risk_scores[0] : null;
            const rawScore = risk?.overall_score ?? (c.total_billed_amount > 50000 ? 75 : 27);
            const scoreVal = rawScore <= 1.0 ? Math.round(rawScore * 100) : Math.round(rawScore);

            let p = risk?.risk_level?.toLowerCase();
            if (!p) {
              if (scoreVal >= 85) p = 'critical';
              else if (scoreVal >= 65) p = 'high';
              else if (scoreVal >= 35) p = 'medium';
              else p = 'low';
            }

            const primaryDiag = c.raw_extracted_features?.primary_diagnosis || (c.diag_count ? `Clinical Diagnosis (${c.diag_count} ICDs)` : null);

            return {
              id: `INV-${c.claim_number || c.id}`,
              realId: c.id,
              claimId: c.claim_number || `CLM-${c.id}`,
              provider: c.provider ? (c.provider.name || c.provider.facility_name) : (c.raw_extracted_features?.provider_id || 'Medical Center'),
              investigatorName: user?.name || 'Assigned Investigator',
              status: c.status === 'submitted' ? 'open' : 
                      c.status === 'processing' ? 'in_progress' :
                      c.status === 'under_review' ? 'in_progress' : 
                      c.status === 'flagged' ? 'in_progress' :
                      c.status === 'paid' ? 'resolved' :
                      c.status === 'denied' ? 'resolved' :
                      c.status === 'closed' ? 'resolved' :
                      (c.status || 'open'),
              priority: p,
              openedDate: c.service_date || '2026-08-21',
              dueDate: '2026-09-01',
              amount: parseFloat(c.total_billed_amount || c.raw_extracted_features?.clm_tot_chrg_amt || 0),
              type: c.claim_type ? (c.claim_type.toUpperCase() + ' Claim') : 'Billing Review',
              description: primaryDiag || 'Claim anomaly evaluation',
              aiRiskScore: scoreVal,
              diagnosis: primaryDiag || (c.claim_type ? `${c.claim_type.toUpperCase()} Evaluation` : 'Medical Service')
            };
          });
          setInvList(mapped);
        }
      })
      .catch(err => console.warn('Could not load claims in command center:', err));

    notificationsAPI.getAll()
      .then(res => {
        if (Array.isArray(res) && isMounted) {
          const mapped = res.map(n => ({
            id: `ALT-${n.id}`,
            type: n.notification_type || 'info',
            message: n.message,
            date: n.created_at ? n.created_at.split('T')[0] : '2026-08-21',
            read: n.is_read,
          }));
          setAlertList(mapped);
        }
      })
      .catch(() => { });

    return () => { isMounted = false; };
  }, [user?.name]);

  const myInvs = invList;
  const openCases = myInvs.filter(i => i.status === 'open').length;
  const inProgressCases = myInvs.filter(i => i.status === 'in_progress').length;
  const criticalCases = myInvs.filter(i => i.priority === 'critical' || i.priority === 'high').length;
  const resolvedCases = myInvs.filter(i => i.status === 'resolved').length;
  const recentAlerts = alertList.filter(a => !a.read);
  const activeCases = openCases + inProgressCases;


  return (
    <div className="space-y-6">
      <PageHeader
        title={`Command Center`}
        subtitle={`Welcome back, ${user?.name}. You have ${activeCases} active investigations.`}
        actions={
          <button className="btn-primary" onClick={() => navigate('/investigator/queue')}>
            <Search size={15} /> View Queue
          </button>
        }
      />

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="Open Cases" value={openCases} icon={Search} iconBg="bg-rose-50" iconColor="text-rose-600" />
        <StatCard title="Critical & High" value={criticalCases} icon={Flame} iconBg="bg-red-50" iconColor="text-red-500" />
        <StatCard title="Resolved (30d)" value={resolvedCases} icon={CheckCircle} iconBg="bg-emerald-50" iconColor="text-emerald-600" />
        <StatCard title="Avg. Resolution" value="3.5d" icon={Clock} iconBg="bg-violet-50" iconColor="text-violet-600" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* My Active Investigations */}
        <div className="card lg:col-span-2">
          <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
            <h3 className="section-title">My Active Investigations</h3>
            <button className="text-sm text-rose-600 hover:text-rose-700 font-medium" onClick={() => navigate('/investigator/queue')}>View all</button>
          </div>
          <div className="divide-y divide-slate-50">
            {myInvs.filter(i => i.status === 'in_progress' || i.status === 'open').slice(0, 3).map(inv => {
              return (
                <div key={inv.id} className="flex items-center gap-4 px-5 py-3.5 hover:bg-slate-50 transition-colors cursor-pointer"
                  onClick={() => navigate(`/investigator/case/${inv.claimId}`)}>
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
                      <span>Assigned: {inv.investigatorName || user?.name || 'Assigned Investigator'}</span>
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
          <button className="text-sm text-rose-600 hover:text-rose-700 font-medium" onClick={() => navigate('/investigator/claims')}>View all</button>
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
              {[...invList].sort((a, b) => {
                const priorityOrder = { critical: 0, high: 1, medium: 2, low: 3 };
                return (priorityOrder[a.priority] ?? 4) - (priorityOrder[b.priority] ?? 4);
              }).slice(0, 5).map(inv => {
                return (
                  <tr key={inv.id} className="table-row">
                    <td className="table-cell font-mono text-xs font-bold text-rose-600">
                      <Link to={`/claims/${inv.claimId}`} className="hover:underline">{inv.claimId}</Link>
                    </td>
                    <td className="table-cell font-medium text-slate-800">{inv.provider}</td>
                    <td className="table-cell text-slate-600">{inv.diagnosis || inv.type}</td>
                    <td className="table-cell"><Badge status={inv.priority} /></td>
                    <td className="table-cell"><Badge status={inv.status} /></td>
                    <td className="table-cell">
                      <button className="btn-primary text-xs py-1 px-3" onClick={() => navigate(`/investigator/case/${inv.claimId}`)}>
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
