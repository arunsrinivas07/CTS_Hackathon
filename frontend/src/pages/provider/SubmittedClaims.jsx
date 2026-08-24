import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Search, Eye } from 'lucide-react';
import Badge from '../../components/ui/Badge';
import Modal from '../../components/ui/Modal';
import EmptyState from '../../components/ui/EmptyState';
import { claimsAPI } from '../../services/api';
import { useAuth } from '../../context/AuthContext';

const filterTabs = [
  { v: 'all', l: 'All', grad: 'linear-gradient(135deg, #9F1239, #7C2D3E)' },
  { v: 'approved', l: 'Approved', grad: 'linear-gradient(135deg, #4A7C59, #166534)' },
  { v: 'under_review', l: 'Under Review', grad: 'linear-gradient(135deg, #F59E0B, #d97706)' },
  { v: 'flagged', l: 'Flagged', grad: 'linear-gradient(135deg, #F59E0B, #d97706)' },
  { v: 'rejected', l: 'Rejected', grad: 'linear-gradient(135deg, #DC2626, #EF4444)' },
];

export default function SubmittedClaims() {
  const { user } = useAuth();
  const [claimList, setClaimList] = useState([]);
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('all');
  const [selected, setSelected] = useState(null);

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
            diagnosis: c.raw_extracted_features?.primary_diagnosis || 'Clinical Consultation',
            icdCode: c.raw_extracted_features?.icd_code || 'ICD-10',
            status: c.status === 'submitted' ? 'under_review' : (c.status || 'under_review'),
            riskScore: c.risk_scores && c.risk_scores.length > 0 ? Math.round((c.risk_scores[0].final_risk_score || 0.35) * 100) : 35,
            flags: c.status === 'flagged' ? ['Risk Alert'] : [],
            notes: '',
          }));
          setClaimList(mapped);
        }
      })
      .catch(err => console.warn('Could not load claims in SubmittedClaims:', err));
    return () => { isMounted = false; };
  }, []);

  const pc = claimList;

  const filtered = pc.filter(c => {
    const s = search.toLowerCase();
    const pName = (c.patient || '').toLowerCase();
    const diag = (c.diagnosis || '').toLowerCase();
    const cid = (c.id || '').toLowerCase();
    return (cid.includes(s) || pName.includes(s) || diag.includes(s))
      && (status === 'all' || c.status === status);
  });


  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="rounded-2xl p-5 text-white relative overflow-hidden"
        style={{ background: 'linear-gradient(135deg, #9F1239, #7C2D3E, #78350F)' }}>
        <div className="absolute -top-8 -right-8 w-40 h-40 rounded-full opacity-10" style={{ background: '#F5E6E9' }} />
        <div className="relative z-10">
          <h2 className="text-xl font-bold">My Claims</h2>
          <p className="text-sm mt-0.5" style={{ color: 'rgba(219,234,254,0.85)' }}>
            {pc.length} submissions · {user?.name ? `${user.name}'s Facility` : 'Medical Facility'}
          </p>
        </div>
      </div>

      {/* Stat strip */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: 'Total', val: pc.length, card: 'card-burg' },
          { label: 'Approved', val: pc.filter(c => c.status === 'approved').length, card: 'card-sage' },
          { label: 'In Review', val: pc.filter(c => c.status === 'under_review' || c.status === 'flagged').length, card: 'card-amber' },
          { label: 'Rejected', val: pc.filter(c => c.status === 'rejected').length, card: 'card-blush' },
        ].map(({ label, val, card }) => (
          <div key={label} className={card}>
            <p className="text-3xl font-bold text-white">{val}</p>
            <p className="text-sm mt-1 font-medium" style={{ color: 'rgba(255,255,255,0.8)' }}>{label}</p>
          </div>
        ))}
      </div>

      {/* Filter tabs */}
      <div className="flex flex-wrap gap-2">
        {filterTabs.map(t => (
          <button key={t.v} onClick={() => setStatus(t.v)}
            className="px-4 py-2 rounded-xl text-sm font-semibold transition-all cursor-pointer"
            style={status === t.v
              ? { background: t.grad, color: '#fff', boxShadow: '0 2px 8px rgba(37,99,235,0.2)' }
              : { background: '#ffffff', color: '#64748B', border: '1px solid #E7E1DC' }}
            onMouseEnter={e => { if (status !== t.v) e.currentTarget.style.background = '#FAF9F7'; }}
            onMouseLeave={e => { if (status !== t.v) e.currentTarget.style.background = '#ffffff'; }}>
            {t.l} <span style={{ opacity: 0.65 }}>{pc.filter(c => t.v === 'all' ? true : c.status === t.v).length}</span>
          </button>
        ))}
      </div>

      {/* Search */}
      <div className="relative max-w-sm">
        <Search size={15} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
        <input className="input pl-10" placeholder="Search claims…" value={search} onChange={e => setSearch(e.target.value)} />
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead><tr>
              {['Claim ID', 'Patient', 'Type', 'Diagnosis', 'Amount', 'Submitted', 'Priority', 'Status', ''].map(h => (
                <th key={h} className="table-header">{h}</th>
              ))}
            </tr></thead>
            <tbody>
              {filtered.length === 0
                ? <tr><td colSpan={9}><EmptyState title="No claims match" /></td></tr>
                : filtered.map(c => (
                  <tr key={c.id} className="table-row">
                    <td className="table-cell font-mono text-xs font-bold text-rose-600">
                      <Link to={`/claims/${c.id}`} className="hover:underline">{c.id}</Link>
                    </td>
                    <td className="table-cell font-semibold">{c.patient}</td>
                    <td className="table-cell text-slate-500">{c.type}</td>
                    <td className="table-cell max-w-[120px] truncate text-slate-500">{c.diagnosis}</td>
                    <td className="table-cell font-bold text-slate-900">${c.amount.toLocaleString()}</td>
                    <td className="table-cell text-slate-500">{c.submittedDate}</td>
                    <td className="table-cell"><Badge status={c.priority} /></td>
                    <td className="table-cell"><Badge status={c.status} /></td>
                    <td className="table-cell">
                      <button className="w-8 h-8 flex items-center justify-center rounded-xl transition-colors text-slate-400 hover:bg-rose-50 hover:text-rose-600"
                        onClick={() => setSelected(c)}>
                        <Eye size={14} />
                      </button>
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Detail modal */}
      <Modal isOpen={!!selected} onClose={() => setSelected(null)} title={`Claim ${selected?.id}`} size="lg">
        {selected && (
          <div className="space-y-5">
            <div className="flex gap-2 flex-wrap"><Badge status={selected.status} /><Badge status={selected.priority} /></div>
            <div className="grid grid-cols-2 gap-3">
              {[['Patient', selected.patient], ['Patient ID', selected.patientId], ['Type', selected.type],
              ['Diagnosis', selected.diagnosis], ['ICD-10', selected.icdCode],
              ['Amount', `$${selected.amount.toLocaleString()}`], ['Date', selected.date], ['Submitted', selected.submittedDate]]
                .map(([k, v]) => (
                  <div key={k} className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                    <p className="text-xs font-bold mb-0.5 text-slate-400">{k}</p>
                    <p className="text-sm font-bold text-slate-900">{v}</p>
                  </div>
                ))}
            </div>
            {selected.flags?.length > 0 && (
              <div>
                <p className="text-xs font-bold mb-2 text-slate-400">Risk Flags</p>
                <div className="flex flex-wrap gap-2">
                  {selected.flags.map(f => (
                    <span key={f} className="text-xs px-3 py-1 rounded-full font-semibold bg-red-50 text-red-600 border border-red-200">{f}</span>
                  ))}
                </div>
              </div>
            )}
            {selected.notes && (
              <div>
                <p className="text-xs font-bold mb-1.5 text-slate-400">Reviewer Notes</p>
                <p className="text-sm text-slate-700 rounded-xl px-4 py-3 bg-slate-50 border border-slate-200">{selected.notes}</p>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}
