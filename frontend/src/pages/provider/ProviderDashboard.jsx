import { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useNavigate, Link } from 'react-router-dom';
import Badge from '../../components/ui/Badge';
import ClaimsBarChart from '../../components/charts/ClaimsBarChart';
import ClaimsPieChart from '../../components/charts/ClaimsPieChart';
import { claimsAPI } from '../../services/api';
import { Plus, ArrowUpRight, FileText, CheckCircle, Clock, DollarSign, AlertTriangle, TrendingUp, ArrowRight } from 'lucide-react';

export default function ProviderDashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [claimList, setClaimList] = useState([]);

  useEffect(() => {
    let isMounted = true;
    claimsAPI.getAll()
      .then(res => {
        if (Array.isArray(res) && isMounted) {
          const mapped = res.map(c => ({
            id: c.claim_number || `CLM-${c.id}`,
            realId: c.id,
            patient: c.patient?.name || c.raw_extracted_features?.patient_name || `Patient #${c.patient_id || 1}`,
            patientId: `PAT-${c.patient_id || 1}`,
            amount: parseFloat(c.total_billed_amount || 0),
            date: c.service_date || '2026-08-21',
            submittedDate: c.submission_date || c.service_date || '2026-08-21',
            type: c.claim_type ? c.claim_type.toUpperCase() : 'OUTPATIENT',
            diagnosis: c.raw_extracted_features?.primary_diagnosis || 'Clinical Care',
            icdCode: c.raw_extracted_features?.icd_code || 'ICD-10',
            status: c.status === 'submitted' ? 'under_review' : (c.status || 'under_review'),
            priority: c.status === 'flagged' ? 'high' : 'low',
          }));
          setClaimList(mapped);
        }
      })
      .catch(err => console.warn('Could not load claims in ProviderDashboard:', err));
    return () => { isMounted = false; };
  }, []);

  const pc = claimList;
  const stats = {
    total: pc.length,
    approved: pc.filter(c => c.status === 'approved').length,
    review: pc.filter(c => c.status === 'flagged' || c.status === 'under_review').length,
    rejected: pc.filter(c => c.status === 'rejected').length,
    billed: pc.reduce((s, c) => s + (c.amount || 0), 0),
  };

  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour >= 5 && hour < 12) return 'Good Morning';
    if (hour >= 12 && hour < 17) return 'Good Afternoon';
    if (hour >= 17 && hour < 21) return 'Good Evening';
    return 'Good Night';
  };

  return (
    <div className="space-y-5">

      {/* Hero banner */}
      <div className="rounded-2xl p-6 relative overflow-hidden"
        style={{ background: 'linear-gradient(135deg, #9F1239 0%, #7C2D3E 50%, #78350F 100%)' }}>
        <div className="absolute -top-10 -right-10 w-56 h-56 rounded-full opacity-10" style={{ background: '#F5E6E9' }} />
        <div className="absolute -bottom-12 left-1/3 w-48 h-48 rounded-full opacity-10" style={{ background: '#78350F' }} />
        <div className="relative z-10 flex items-center justify-between flex-wrap gap-4">
          <div>
            <p className="text-sm font-medium mb-1" style={{ color: 'rgba(219,234,254,0.9)' }}>{getGreeting()}</p>
            <h2 className="text-2xl font-bold text-white">{user?.name?.split(' ').slice(0, 2).join(' ')}</h2>
            <p className="text-sm mt-1" style={{ color: 'rgba(219,234,254,0.8)' }}>
              {user?.facility || 'Medical Facility'}
            </p>
          </div>
          <button
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl font-semibold text-sm transition-colors shadow-lg"
            style={{ background: '#ffffff', color: '#9F1239' }}
            onMouseEnter={e => { e.currentTarget.style.background = '#FDF1F3'; }}
            onMouseLeave={e => { e.currentTarget.style.background = '#ffffff'; }}
            onClick={() => navigate('/provider/submit')}>
            <Plus size={16} /> New Claim
          </button>
        </div>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="card-burg">
          <div className="w-9 h-9 rounded-xl flex items-center justify-center mb-3" style={{ background: 'rgba(255,255,255,0.2)' }}>
            <FileText size={17} className="text-white" />
          </div>
          <p className="text-3xl font-bold text-white">{stats.total}</p>
          <p className="text-sm mt-1 font-medium" style={{ color: 'rgba(255,255,255,0.75)' }}>Total Claims</p>
        </div>
        <div className="card-sage">
          <div className="w-9 h-9 rounded-xl flex items-center justify-center mb-3" style={{ background: 'rgba(255,255,255,0.2)' }}>
            <CheckCircle size={17} className="text-white" />
          </div>
          <p className="text-3xl font-bold text-white">{stats.approved}</p>
          <p className="text-sm mt-1 font-medium" style={{ color: 'rgba(255,255,255,0.75)' }}>Approved</p>
        </div>
        <div className="card-amber">
          <div className="w-9 h-9 rounded-xl flex items-center justify-center mb-3" style={{ background: 'rgba(255,255,255,0.2)' }}>
            <Clock size={17} className="text-white" />
          </div>
          <p className="text-3xl font-bold text-white">{stats.review}</p>
          <p className="text-sm mt-1 font-medium" style={{ color: 'rgba(255,255,255,0.75)' }}>Under Review</p>
        </div>
        <div className="card-blush">
          <div className="w-9 h-9 rounded-xl flex items-center justify-center mb-3" style={{ background: 'rgba(255,255,255,0.2)' }}>
            <AlertTriangle size={17} className="text-white" />
          </div>
          <p className="text-3xl font-bold text-white">{stats.rejected}</p>
          <p className="text-sm mt-1 font-medium" style={{ color: 'rgba(255,255,255,0.75)' }}>Rejected</p>
        </div>
      </div>

      {/* Total billed strip */}
      <div className="card-p flex items-center justify-between"
        style={{ background: 'linear-gradient(135deg, #FDF1F3, #F5E6E9)', borderColor: '#E8D5D9' }}>
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-2xl flex items-center justify-center text-white"
            style={{ background: 'linear-gradient(135deg, #9F1239, #7C2D3E)' }}>
            <DollarSign size={22} />
          </div>
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-rose-600">Total Billed</p>
            <p className="text-3xl font-bold text-slate-900">${(stats.billed / 1000).toFixed(0)}k</p>
          </div>
        </div>
        <div className="flex items-center gap-2 text-sm font-semibold text-emerald-700">
          <TrendingUp size={16} /> +12% vs last month
        </div>
      </div>

      {/* Quick actions */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="card-p space-y-2">
          <p className="section-title mb-3">Quick Actions</p>
          {[
            { label: 'Submit a New Claim', path: '/provider/submit', color: '#9F1239' },
            { label: 'View All Claims', path: '/provider/claims', color: '#4A7C59' },
            { label: 'Track Claim Status', path: '/provider/timeline', color: '#9F1239' },
            { label: 'Upload Documents', path: '/provider/documents', color: '#4A7C59' },
            { label: 'Facility Profile', path: '/provider/profile', color: '#64748b' },
          ].map(a => (
            <button key={a.path} onClick={() => navigate(a.path)}
              className="w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-sm font-semibold transition-all text-left group"
              style={{ background: '#FAF9F7', border: '1px solid #E7E1DC', color: a.color }}
              onMouseEnter={e => { e.currentTarget.style.background = '#FDF1F3'; }}
              onMouseLeave={e => { e.currentTarget.style.background = '#FAF9F7'; }}>
              {a.label}
              <ArrowRight size={14} className="group-hover:translate-x-0.5 transition-transform" />
            </button>
          ))}
        </div>

        {/* Charts */}
        <div className="card-p lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <p className="section-title">Claims Activity</p>
            <span className="text-xs font-semibold px-3 py-1 rounded-full bg-rose-50 text-rose-600">Last 6 months</span>
          </div>
          <ClaimsBarChart claims={claimList} />
        </div>
      </div>

      {/* Pie + table row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="card-p">
          <p className="section-title mb-1">Claims by Type</p>
          <p className="text-xs mb-3 text-slate-400">Distribution overview</p>
          <ClaimsPieChart claims={claimList} />
        </div>

        <div className="card lg:col-span-2">
          <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
            <div>
              <p className="section-title">Recent Claims</p>
              <p className="text-xs mt-0.5 text-slate-400">Latest {pc.slice(0, 5).length} submissions</p>
            </div>
            <button className="btn-ghost text-xs gap-1" onClick={() => navigate('/provider/claims')}>
              View all <ArrowUpRight size={13} />
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead><tr>
                {['Claim ID', 'Patient', 'Type', 'Amount', 'Priority', 'Status'].map(h => (
                  <th key={h} className="table-header">{h}</th>
                ))}
              </tr></thead>
              <tbody>
                {pc.slice(0, 5).map(c => (
                  <tr key={c.id} className="table-row">
                    <td className="table-cell font-mono text-xs font-bold text-rose-600">
                      <Link to={`/claims/${c.id}`} className="hover:underline">{c.id}</Link>
                    </td>
                    <td className="table-cell font-semibold">{c.patient}</td>
                    <td className="table-cell text-slate-500">{c.type}</td>
                    <td className="table-cell font-bold text-slate-900">${c.amount.toLocaleString()}</td>
                    <td className="table-cell"><Badge status={c.priority} /></td>
                    <td className="table-cell"><Badge status={c.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
