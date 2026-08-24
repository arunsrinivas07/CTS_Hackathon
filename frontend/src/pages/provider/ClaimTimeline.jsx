import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { Search, CheckCircle2, Clock, AlertTriangle, XCircle, Circle } from 'lucide-react';
import Badge from '../../components/ui/Badge';
import { useAuth } from '../../context/AuthContext';
import { claimsAPI } from '../../services/api';

const buildSteps = c => [
  { label: 'Claim Submitted', date: c.submittedDate || c.date, done: true },
  { label: 'Initial Review', date: c.submittedDate || c.date, done: true },
  { label: 'Documentation Check', date: c.submittedDate || c.date, done: c.status !== 'submitted' && c.status !== 'pending', warn: c.flags?.includes('Missing documentation') },
  { label: 'Risk Assessment', date: c.date, done: ['under_review', 'flagged', 'approved', 'rejected', 'paid', 'denied'].includes(c.status) },
  { label: 'Investigator Review', date: c.investigatorName ? c.date : null, done: !!c.investigatorName || c.status === 'flagged', skip: !c.investigatorName && (c.status === 'approved' || c.status === 'paid') },
  { label: 'Final Decision', date: ['approved', 'rejected', 'paid', 'denied'].includes(c.status) ? c.date : null, done: ['approved', 'rejected', 'paid', 'denied'].includes(c.status), finalStatus: c.status },
];

export default function ClaimTimeline() {
  const { claimId } = useParams();
  const { user } = useAuth();
  const [claimList, setClaimList] = useState([]);
  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState(null);
  const [statusHistory, setStatusHistory] = useState([]);

  useEffect(() => {
    let isMounted = true;
    claimsAPI.getAll()
      .then(res => {
        if (Array.isArray(res) && isMounted) {
          const mapped = res.map(c => ({
            id: c.claim_number || `CLM-${c.id}`,
            realId: c.id,
            provider: c.provider ? (c.provider.name || c.provider.facility_name) : 'Medical Center',
            providerId: `PRV-${c.provider_id || 1}`,
            patient: c.patient?.name || c.raw_extracted_features?.patient_name || `Patient #${c.patient_id || 1}`,
            patientId: `PAT-${c.patient_id || 1}`,
            amount: parseFloat(c.total_billed_amount || 0),
            date: c.service_date || '2026-08-21',
            submittedDate: c.submission_date || c.service_date || '2026-08-21',
            type: c.claim_type ? c.claim_type.toUpperCase() : 'OUTPATIENT',
            diagnosis: c.raw_extracted_features?.primary_diagnosis || 'Clinical Diagnosis',
            icdCode: c.raw_extracted_features?.icd_code || 'ICD-10',
            status: c.status === 'submitted' ? 'under_review' : (c.status || 'under_review'),
            flags: c.status === 'flagged' ? ['High risk anomaly'] : [],
            investigatorName: c.assigned_investigator ? (c.assigned_investigator.full_name || c.assigned_investigator.email) : null,
            notes: c.status === 'flagged' ? 'Flagged for SIU review due to rule match.' : 'Standard adjudication workflow.',
          }));
          setClaimList(mapped);

          // Find target claim if claimId param is passed
          if (claimId) {
            const found = mapped.find(c => c.id === claimId || String(c.realId) === claimId);
            if (found) setSelected(found);
            else setSelected(mapped[0] || null);
          } else {
            setSelected(mapped[0] || null);
          }
        }
      })
      .catch(err => console.warn('Could not load claims in ClaimTimeline:', err));

    return () => { isMounted = false; };
  }, [claimId]);

  useEffect(() => {
    if (selected && selected.realId) {
      claimsAPI.getStatusHistory(selected.realId)
        .then(history => {
          if (Array.isArray(history) && history.length > 0) {
            setStatusHistory(history);
          } else {
            setStatusHistory([]);
          }
        })
        .catch(() => setStatusHistory([]));
    }
  }, [selected]);

  const pc = user?.role === 'investigator' || user?.role === 'admin'
    ? claimList
    : claimList;

  const filtered = pc.filter(c =>
    (c.id || '').toLowerCase().includes(search.toLowerCase()) ||
    (c.patient || '').toLowerCase().includes(search.toLowerCase())
  );

  const steps = selected ? buildSteps(selected) : [];


  return (
    <div className="w-full max-w-6xl mx-auto space-y-6">
      <div className="rounded-2xl p-5 text-white relative overflow-hidden"
        style={{ background: 'linear-gradient(135deg, #9F1239, #7C2D3E, #78350F)' }}>
        <div className="absolute -top-8 -right-8 w-40 h-40 rounded-full opacity-10" style={{ background: '#F5E6E9' }} />
        <div className="relative z-10">
          <h2 className="text-xl font-bold">Claim Timeline</h2>
          <p className="text-sm mt-0.5" style={{ color: 'rgba(219,234,254,0.85)' }}>Track each claim through the review process.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* List */}
        <div className="card overflow-hidden">
          <div className="px-4 py-3 border-b border-slate-100">
            <div className="relative">
              <Search size={13} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
              <input className="input pl-9 text-xs" placeholder="Search claims…"
                value={search} onChange={e => setSearch(e.target.value)} />
            </div>
          </div>
          <div className="divide-y max-h-[520px] overflow-y-auto border-slate-100">
            {filtered.map(c => (
              <button key={c.id} onClick={() => setSelected(c)}
                className="w-full text-left px-4 py-3.5 transition-colors cursor-pointer"
                style={{ background: selected?.id === c.id ? '#F5E6E9' : '' }}
                onMouseEnter={e => { if (selected?.id !== c.id) e.currentTarget.style.background = '#FAF9F7'; }}
                onMouseLeave={e => { if (selected?.id !== c.id) e.currentTarget.style.background = ''; }}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-mono font-bold"
                    style={{ color: selected?.id === c.id ? '#9F1239' : '#64748B' }}>{c.id}</span>
                  <Badge status={c.status} size="xs" />
                </div>
                <p className="text-sm font-semibold text-slate-800">{c.patient}</p>
                <p className="text-xs text-slate-500">{c.diagnosis}</p>
              </button>
            ))}
          </div>
        </div>

        {/* Timeline detail */}
        <div className="card-p lg:col-span-2">
          {selected ? (
            <>
              <div className="flex items-start justify-between mb-5">
                <div>
                  <p className="text-lg font-bold text-slate-900">{selected.id}</p>
                  <p className="text-sm mt-0.5 text-slate-500">{selected.patient} · {selected.diagnosis}</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-lg font-bold text-slate-900">${selected.amount.toLocaleString()}</span>
                  <Badge status={selected.status} />
                </div>
              </div>

              {/* Steps */}
              <div className="relative pl-2">
                <div className="absolute left-[17px] top-2 bottom-2 w-px bg-slate-200" />
                <div className="space-y-6">
                  {steps.map((step, i) => {
                    const Icon = step.done
                      ? step.warn ? AlertTriangle
                        : step.finalStatus === 'rejected' ? XCircle
                          : CheckCircle2
                      : step.skip ? Circle : Clock;
                    const col = step.done
                      ? step.warn ? '#F59E0B'
                        : step.finalStatus === 'rejected' ? '#DC2626'
                          : '#4A7C59'
                      : '#94A3B8';
                    return (
                      <div key={i} className="relative flex items-start gap-4">
                        <div className="relative z-10 flex-shrink-0"><Icon size={18} style={{ color: col }} /></div>
                        <div className="pt-0.5">
                          <p className="text-sm font-semibold" style={{ color: step.done ? '#0F172A' : '#94A3B8' }}>{step.label}</p>
                          {step.date && <p className="text-xs mt-0.5 text-slate-500">{step.date}</p>}
                          {step.skip && <p className="text-xs italic mt-0.5 text-slate-400">Skipped — direct approval</p>}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {selected.notes && (
                <div className="mt-6 pt-5 border-t border-slate-100">
                  <p className="text-xs font-bold uppercase tracking-wider mb-2 text-slate-400">Reviewer Notes</p>
                  <p className="text-sm text-slate-700 rounded-xl px-4 py-3 bg-slate-50 border border-slate-200">{selected.notes}</p>
                </div>
              )}
            </>
          ) : (
            <p className="text-sm text-center py-10 text-slate-400">Select a claim to view its timeline.</p>
          )}
        </div>

        {/* Current Claim Stage */}
        <div className="card-p lg:col-span-1 h-fit">
          {selected ? (
            <>
              <div className="flex items-center gap-2 mb-4">
                <span className="text-lg">📌</span>
                <h3 className="font-bold text-slate-900">Current Claim Stage</h3>
              </div>

              <div className="bg-[#FFFBEB] border border-[#FDE68A] rounded-xl p-4 mb-5">
                <p className="font-bold text-[#92400e] mb-1.5 font-mono text-xs uppercase tracking-wide">
                  Status: {selected.status.replace('_', ' ')}
                </p>
                <p className="text-sm text-slate-600 leading-relaxed">
                  {selected.status === 'flagged' || selected.status === 'under_review'
                    ? 'Your claim is currently under active clinical & SIU review by the carrier.'
                    : selected.status === 'approved'
                      ? 'Claim has been approved and queued for disbursement.'
                      : selected.status === 'rejected'
                        ? 'Claim review completed. Decision notification issued.'
                        : 'Claim received and entered standard processing.'}
                </p>
              </div>

              <div className="space-y-2.5 text-sm">
                <p><span className="font-bold text-slate-700">Expected Adjudication:</span> <span className="text-slate-500">1–3 Business Days</span></p>
                <p><span className="font-bold text-slate-700">Assigned Investigator:</span> <span className="text-slate-500">{selected.investigatorName || 'Unassigned (Auto-Processing)'}</span></p>
                <p><span className="font-bold text-slate-700">Inquiry Tracking:</span> <span className="text-slate-500">#{selected.id}</span></p>
              </div>
            </>
          ) : (
            <p className="text-sm text-center py-10 text-slate-400">No claim selected.</p>
          )}
        </div>
      </div>
    </div>
  );
}
