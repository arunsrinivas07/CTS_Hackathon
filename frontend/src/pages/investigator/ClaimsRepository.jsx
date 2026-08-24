import { useState, useEffect } from 'react';
import { Search, SlidersHorizontal, Eye, AlertCircle } from 'lucide-react';
import PageHeader from '../../components/ui/PageHeader';
import { Link } from 'react-router-dom';
import Badge from '../../components/ui/Badge';
import Modal from '../../components/ui/Modal';
import EmptyState from '../../components/ui/EmptyState';
import { claimsAPI } from '../../services/api';
import Select from '../../components/ui/Select';

export default function ClaimsRepository() {
  const [claimList, setClaimList] = useState([]);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [riskFilter, setRiskFilter] = useState('all');
  const [selected, setSelected] = useState(null);

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

            return {
              id: c.claim_number || `CLM-${c.id}`,
              realId: c.id,
              provider: c.provider ? (c.provider.name || c.provider.facility_name) : (c.raw_extracted_features?.provider_id || 'Medical Provider'),
              providerId: `PRV-${c.provider_id || 1}`,
              patient: c.patient?.name || c.raw_extracted_features?.patient_name || `Patient #${c.patient_id || 1}`,
              patientId: `PAT-${c.patient_id || 1}`,
              amount: parseFloat(c.total_billed_amount || c.raw_extracted_features?.clm_tot_chrg_amt || 0),
              date: c.service_date || '2026-08-21',
              submittedDate: c.submission_date || c.service_date || '2026-08-21',
              type: c.claim_type ? c.claim_type.toUpperCase() : 'OUTPATIENT',
              diagnosis: c.raw_extracted_features?.primary_diagnosis || 'Clinical Procedure',
              icdCode: c.raw_extracted_features?.icd_code || 'K37',
              status: c.status === 'submitted' ? 'under_review' : (c.status || 'under_review'),
              priority: p,
              riskScore: scoreVal,
              flags: scoreVal >= 65 ? ['Billing Anomaly'] : [],
              notes: '',
            };
          });
          setClaimList(mapped);
        }
      })
      .catch(err => console.warn('Could not load claims repository:', err));
    return () => { isMounted = false; };
  }, []);

  const filtered = claimList.filter(c => {
    const s = search.toLowerCase();
    const match = (c.id || '').toLowerCase().includes(s) ||
      (c.patient || '').toLowerCase().includes(s) ||
      (c.provider || '').toLowerCase().includes(s) ||
      (c.diagnosis || '').toLowerCase().includes(s);
    const matchStatus = statusFilter === 'all' || c.status === statusFilter;
    const matchRisk = riskFilter === 'all' || c.priority === riskFilter;
    return match && matchStatus && matchRisk;
  });


  return (
    <div>
      <PageHeader title="Claims Repository" subtitle={`${claimList.length} total claims across all providers`} />

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3 mb-5">
        <div className="relative flex-1">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            className="input pl-9"
            placeholder="Search claims, patients, providers…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
        <div className="w-full sm:w-44">
          <Select
            value={statusFilter}
            onChange={(val) => setStatusFilter(val)}
            options={[
              { value: 'all', label: 'All Statuses' },
              { value: 'approved', label: 'Approved' },
              { value: 'under_review', label: 'Under Review' },
              { value: 'flagged', label: 'Flagged' },
              { value: 'rejected', label: 'Rejected' },
            ]}
          />
        </div>
        <div className="w-full sm:w-40">
          <Select
            value={riskFilter}
            onChange={(val) => setRiskFilter(val)}
            options={[
              { value: 'all', label: 'All Priorities' },
              { value: 'critical', label: 'Critical' },
              { value: 'high', label: 'High' },
              { value: 'medium', label: 'Medium' },
              { value: 'low', label: 'Low' },
            ]}
          />
        </div>
      </div>

      <div className="card overflow-hidden">
        <div className="px-5 py-3 border-b border-slate-100 bg-slate-50 flex items-center justify-between">
          <span className="text-xs text-slate-500">{filtered.length} result{filtered.length !== 1 ? 's' : ''}</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr>
                {['Claim ID', 'Provider', 'Patient', 'Type', 'Diagnosis', 'Amount', 'Date', 'Priority', 'Status', ''].map(h => (
                  <th key={h} className="table-header whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr><td colSpan={10}><EmptyState title="No claims match your filters" /></td></tr>
              ) : filtered.map(c => (
                <tr
                  key={c.id}
                  className="table-row cursor-pointer hover:bg-rose-50/50 transition-colors"
                  onClick={() => window.location.href = `/investigations/${c.id}`}
                >
                  <td className="table-cell font-mono text-xs text-rose-700 font-bold whitespace-nowrap">
                    <Link to={`/investigations/${c.id}`} className="hover:underline">{c.id}</Link>
                  </td>
                  <td className="table-cell text-slate-600 max-w-[120px] truncate">{c.provider}</td>
                  <td className="table-cell font-semibold whitespace-nowrap">{c.patient}</td>
                  <td className="table-cell text-slate-500 whitespace-nowrap">{c.type}</td>
                  <td className="table-cell text-slate-500 max-w-[130px] truncate">{c.diagnosis}</td>
                  <td className="table-cell font-bold text-slate-900 whitespace-nowrap">${c.amount.toLocaleString()}</td>
                  <td className="table-cell text-slate-500 whitespace-nowrap">{c.date}</td>
                  <td className="table-cell"><Badge status={c.priority} /></td>
                  <td className="table-cell"><Badge status={c.status} /></td>
                  <td className="table-cell">
                    <div className="flex items-center gap-2">
                      <button
                        className="p-1.5 rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-700 transition-colors"
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelected(c);
                        }}
                        title="View Details"
                      >
                        <Eye size={15} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Detail Modal */}
      <Modal isOpen={!!selected} onClose={() => setSelected(null)} title={`Claim ${selected?.id}`} size="lg">
        {selected && (
          <div className="space-y-5">
            <div className="flex items-center gap-3 flex-wrap">
              <Badge status={selected.status} />
              <Badge status={selected.priority} />
            </div>
            <div className="grid grid-cols-2 gap-4">
              {[
                ['Provider', selected.provider],
                ['Patient', selected.patient],
                ['Patient ID', selected.patientId],
                ['Claim Type', selected.type],
                ['Diagnosis', selected.diagnosis],
                ['ICD-10', selected.icdCode],
                ['Amount', `$${selected.amount.toLocaleString()}`],
                ['Date of Service', selected.date],
                ['Submitted', selected.submittedDate],
                ['Investigator', selected.investigatorName || 'Unassigned'],
              ].map(([k, v]) => (
                <div key={k}>
                  <p className="text-xs text-slate-500 mb-0.5">{k}</p>
                  <p className="text-sm font-medium text-slate-800">{v}</p>
                </div>
              ))}
            </div>
            {selected.flags?.length > 0 && (
              <div>
                <p className="text-xs text-slate-500 mb-2">Risk Flags</p>
                <div className="flex flex-wrap gap-2">
                  {selected.flags.map(f => (
                    <span key={f} className="text-xs px-2 py-1 bg-amber-50 text-amber-700 border border-amber-200 rounded-full">{f}</span>
                  ))}
                </div>
              </div>
            )}
            {selected.notes && (
              <div>
                <p className="text-xs text-slate-500 mb-1">Notes</p>
                <p className="text-sm text-slate-700 bg-slate-50 rounded-lg px-3 py-2">{selected.notes}</p>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}
