import { useState, useEffect } from 'react';
import { Search, Building2, Eye, Edit2, CheckCircle, Loader2 } from 'lucide-react';
import PageHeader from '../../components/ui/PageHeader';
import Badge from '../../components/ui/Badge';
import Select from '../../components/ui/Select';
import RiskMeter from '../../components/ui/RiskMeter';
import Modal from '../../components/ui/Modal';
import { providersAPI, claimsAPI } from '../../services/api';

export default function ProviderDetails() {
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');
  const [selected, setSelected] = useState(null);
  const [editModal, setEditModal] = useState(null);
  const [form, setForm] = useState({});
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const [providerList, setProviderList] = useState([]);
  const [claimsList, setClaimsList] = useState([]);

  useEffect(() => {
    let isMounted = true;
    providersAPI.getAll()
      .then(res => {
        if (Array.isArray(res) && isMounted) {
          const mapped = res.map(p => ({
            id: p.id,
            name: p.name || p.facility_name || 'Healthcare Provider',
            type: p.facility_type || 'Medical Facility',
            npi: p.npi || '1033472386',
            location: p.state || 'OH',
            phone: p.phone || '(555) 019-2834',
            contact: p.email || 'contact@provider.com',
            enrolledDate: p.created_at ? p.created_at.split('T')[0] : '2026-01-15',
            totalBilled: p.total_billed || 1500000,
            status: p.status || 'active',
            riskLevel: p.risk_tier || 'medium',
            riskScore: Math.round((p.avg_risk_score || 0.45) * 100),
            totalClaims: p.total_claims || 45,
            approvedClaims: p.approved_claims || 38,
            flaggedClaims: p.flagged_claims || 7,
          }));
          setProviderList(mapped);
          if (mapped.length > 0) setSelected(mapped[0]);
        }
      })
      .catch(err => console.warn('Could not load providers in ProviderDetails:', err));

    claimsAPI.getAll()
      .then(res => {
        if (Array.isArray(res) && isMounted) {
          const mapped = res.map(c => ({
            id: c.claim_number || `CLM-${c.id}`,
            providerId: c.provider_id,
            patient: c.patient?.name || `Patient #${c.patient_id || 1}`,
            amount: parseFloat(c.total_billed_amount || 0),
            status: c.status || 'submitted',
          }));
          setClaimsList(mapped);
        }
      })
      .catch(() => { });

    return () => { isMounted = false; };
  }, []);

  const filtered = providerList.filter(p => {
    const s = search.toLowerCase();
    const match = p.name.toLowerCase().includes(s) || p.location.toLowerCase().includes(s) || (p.npi || '').includes(s);
    const matchType = typeFilter === 'all' || p.type === typeFilter;
    return match && matchType;
  });

  const types = [...new Set(providerList.map(p => p.type))];
  const selectedClaims = selected ? claimsList.filter(c => String(c.providerId) === String(selected.id)) : [];

  const openEdit = (p) => { setForm({ ...p }); setEditModal(p); };

  const handleSave = async () => {
    setSaving(true);
    await new Promise(r => setTimeout(r, 700));
    setProviderList(prev => prev.map(p => p.id === form.id ? { ...form } : p));
    setSaving(false);
    setEditModal(null);
    if (selected?.id === form.id) setSelected({ ...form });
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  return (
    <div>
      <PageHeader title="Provider Details" subtitle="View and manage all enrolled healthcare providers." />

      {saved && (
        <div className="flex items-center gap-2 px-4 py-2.5 bg-emerald-50 border border-emerald-200 rounded-lg mb-4 text-sm text-emerald-700">
          <CheckCircle size={14} /> Provider updated successfully.
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3 mb-5">
        <div className="relative flex-1">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input className="input pl-9" placeholder="Search by name, location, or NPI…" value={search} onChange={e => setSearch(e.target.value)} />
        </div>
        <div className="w-full sm:w-48">
          <Select
            value={typeFilter}
            onChange={(val) => setTypeFilter(val)}
            options={[
              { value: 'all', label: 'All Types' },
              ...types.map(t => ({ value: t, label: t }))
            ]}
          />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Provider List */}
        <div className="card overflow-hidden lg:col-span-1">
          <div className="px-4 py-3 border-b border-slate-100 bg-slate-50">
            <p className="text-xs font-semibold text-slate-600 uppercase tracking-wide">{filtered.length} Providers</p>
          </div>
          <div className="divide-y divide-slate-50 max-h-[520px] overflow-y-auto">
            {filtered.map(p => (
              <div
                key={p.id}
                className={`flex items-center gap-3 px-4 py-3.5 cursor-pointer hover:bg-slate-50 transition-colors ${selected?.id === p.id ? 'bg-rose-50' : ''}`}
                onClick={() => setSelected(p)}
              >
                <div className="p-2 bg-rose-50 rounded-lg flex-shrink-0">
                  <Building2 size={15} className="text-rose-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className={`text-sm font-medium truncate ${selected?.id === p.id ? 'text-rose-700' : 'text-slate-800'}`}>{p.name}</p>
                  <p className="text-xs text-slate-400 truncate">{p.type} · {p.location}</p>
                </div>
                <Badge status={p.riskLevel} size="xs" />
              </div>
            ))}
          </div>
        </div>

        {/* Provider Detail */}
        <div className="card p-5 lg:col-span-2">
          {selected ? (
            <>
              <div className="flex items-start justify-between mb-5 pb-4 border-b border-slate-100">
                <div>
                  <h3 className="text-base font-semibold text-slate-900">{selected.name}</h3>
                  <p className="text-sm text-slate-500 mt-0.5">{selected.type} · NPI: {selected.npi}</p>
                  <div className="flex items-center gap-2 mt-1.5">
                    <Badge status={selected.status} />
                    <Badge status={selected.riskLevel} />
                  </div>
                </div>
                <button className="btn-secondary text-xs" onClick={() => openEdit(selected)}>
                  <Edit2 size={13} /> Edit
                </button>
              </div>

              <div className="grid grid-cols-2 gap-4 mb-5">
                {[
                  ['Location', selected.location],
                  ['Phone', selected.phone],
                  ['Email', selected.contact],
                  ['Enrolled', selected.enrolledDate],
                  ['Total Billed', `$${(selected.totalBilled / 1000000).toFixed(2)}M`],
                ].map(([k, v]) => (
                  <div key={k}>
                    <p className="text-xs text-slate-400 mb-0.5">{k}</p>
                    <p className="text-sm font-medium text-slate-800">{v}</p>
                  </div>
                ))}
                <div>
                  <p className="text-xs text-slate-400 mb-1">Risk Score</p>
                  <RiskMeter score={selected.riskScore} />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3 mb-5">
                {[
                  { label: 'Total', value: selected.totalClaims, color: 'text-slate-800' },
                  { label: 'Approved', value: selected.approvedClaims, color: 'text-emerald-600' },
                  { label: 'Flagged', value: selected.flaggedClaims, color: 'text-amber-600' },
                ].map(({ label, value, color }) => (
                  <div key={label} className="text-center p-3 bg-slate-50 rounded-lg">
                    <p className={`text-xl font-bold ${color}`}>{value}</p>
                    <p className="text-xs text-slate-500 mt-0.5">{label} Claims</p>
                  </div>
                ))}
              </div>

              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Recent Claims</p>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr>
                      {['Claim ID', 'Patient', 'Amount', 'Status'].map(h => <th key={h} className="table-header">{h}</th>)}
                    </tr>
                  </thead>
                  <tbody>
                    {selectedClaims.slice(0, 4).map(c => (
                      <tr key={c.id} className="table-row">
                        <td className="table-cell font-mono text-xs text-rose-700">{c.id}</td>
                        <td className="table-cell font-medium">{c.patient}</td>
                        <td className="table-cell font-semibold">${c.amount.toLocaleString()}</td>
                        <td className="table-cell"><Badge status={c.status} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          ) : (
            <div className="flex flex-col items-center justify-center h-64 text-slate-400">
              <Building2 size={32} className="mb-3 text-slate-200" />
              <p className="text-sm">Select a provider to view details</p>
            </div>
          )}
        </div>
      </div>

      {/* Edit Modal */}
      <Modal isOpen={!!editModal} onClose={() => setEditModal(null)} title={`Edit — ${editModal?.name}`} size="md">
        {editModal && (
          <div className="space-y-4">
            {[
              { label: 'Provider Name', field: 'name' },
              { label: 'Phone', field: 'phone' },
              { label: 'Email', field: 'contact' },
              { label: 'Location', field: 'location' },
            ].map(({ label, field }) => (
              <div key={field}>
                <label className="label">{label}</label>
                <input className="input" value={form[field] || ''} onChange={e => setForm(f => ({ ...f, [field]: e.target.value }))} />
              </div>
            ))}
            <div>
              <Select
                label="Status"
                value={form.status}
                onChange={(val) => setForm(f => ({ ...f, status: val }))}
                options={[
                  { value: 'active', label: 'Active' },
                  { value: 'suspended', label: 'Suspended' },
                  { value: 'inactive', label: 'Inactive' },
                ]}
              />
            </div>
            <div className="flex gap-2 pt-2">
              <button className="btn-primary flex-1 justify-center" onClick={handleSave} disabled={saving}>
                {saving ? <><Loader2 size={14} className="animate-spin" /> Saving…</> : 'Save Changes'}
              </button>
              <button className="btn-secondary" onClick={() => setEditModal(null)}>Cancel</button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
