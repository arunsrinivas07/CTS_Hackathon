import { useState, useEffect } from 'react';
import { Search, Building2, TrendingUp, AlertTriangle, Loader2 } from 'lucide-react';
import PageHeader from '../../components/ui/PageHeader';
import Badge from '../../components/ui/Badge';
import RiskMeter from '../../components/ui/RiskMeter';
import Modal from '../../components/ui/Modal';
import { useNavigate } from 'react-router-dom';
import { providersAPI, claimsAPI } from '../../services/api';

export default function ProviderIntelligence() {
  const navigate = useNavigate();
  const [providers, setProviders] = useState([]);
  const [allClaims, setAllClaims] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [riskFilter, setRiskFilter] = useState('all');
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    Promise.allSettled([providersAPI.getAll(), claimsAPI.getAll()]).then(([pRes, cRes]) => {
      if (pRes.status === 'fulfilled' && Array.isArray(pRes.value)) {
        setProviders(pRes.value.map(p => ({
          id: p.id,
          name: p.name || `Provider #${p.id}`,
          type: p.provider_type || 'Hospital',
          location: p.address || 'N/A',
          riskScore: p.risk_score || 50,
          riskLevel: (p.risk_score || 50) >= 70 ? 'high' : (p.risk_score || 50) >= 40 ? 'medium' : 'low',
          status: p.is_active !== false ? 'active' : 'inactive',
          npi: p.npi || 'N/A',
          phone: p.phone || 'N/A',
          contact: p.email || 'N/A',
          enrolledDate: p.created_at ? p.created_at.slice(0, 10) : 'N/A',
        })));
      }
      if (cRes.status === 'fulfilled' && Array.isArray(cRes.value)) {
        setAllClaims(cRes.value.map(c => ({
          id: c.claim_number || `CLM-${c.id}`,
          realId: c.id,
          providerId: c.provider_id,
          patient: `Patient #${c.patient_id}`,
          amount: parseFloat(c.total_billed_amount || 0),
          status: c.status === 'paid' ? 'approved' : (c.status === 'denied' ? 'rejected' : c.status),
        })));
      }
      setLoading(false);
    });
  }, []);

  const filtered = providers.filter(p => {
    const s = search.toLowerCase();
    const match = p.name.toLowerCase().includes(s) || p.location.toLowerCase().includes(s);
    const matchRisk = riskFilter === 'all' || p.riskLevel === riskFilter;
    return match && matchRisk;
  });

  const provClaims = selected ? allClaims.filter(c => c.providerId === selected.id) : [];

  return (
    <div>
      <PageHeader title="Provider Intelligence" subtitle="Analyze provider risk profiles and claim patterns." />

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3 mb-5">
        <div className="relative flex-1">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input className="input pl-9" placeholder="Search providers…" value={search} onChange={e => setSearch(e.target.value)} />
        </div>
        <select className="select w-full sm:w-40" value={riskFilter} onChange={e => setRiskFilter(e.target.value)}>
          <option value="all">All Risk Levels</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-40 gap-2 text-slate-400">
          <Loader2 size={18} className="animate-spin" /> Loading providers…
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-2 gap-4">
          {filtered.length === 0 ? (
            <p className="text-sm text-slate-400 col-span-2">No providers found.</p>
          ) : filtered.map(p => {
            const pClaims = allClaims.filter(c => c.providerId === p.id);
            const flagged = pClaims.filter(c => c.status === 'flagged' || c.status === 'under_review').length;
            return (
              <div
                key={p.id}
                className="card p-5 hover:shadow-md transition-shadow cursor-pointer"
                onClick={() => setSelected(p)}
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className="p-2.5 bg-rose-50 rounded-lg flex-shrink-0">
                      <Building2 size={18} className="text-rose-600" />
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-slate-800">{p.name}</p>
                      <p className="text-xs text-slate-400">{p.type} · {p.location}</p>
                    </div>
                  </div>
                  <Badge status={p.riskLevel} />
                </div>
                <div className="flex items-center justify-between mb-3">
                  <RiskMeter score={p.riskScore} />
                  <span className="text-xs text-slate-500">Risk: {p.riskScore}/100</span>
                </div>
                <div className="grid grid-cols-3 gap-2">
                  {[
                    { label: 'Total', value: pClaims.length, color: 'text-slate-700' },
                    { label: 'Flagged', value: flagged, color: 'text-amber-600' },
                    { label: 'Approved', value: pClaims.filter(c => c.status === 'approved').length, color: 'text-emerald-600' },
                  ].map(({ label, value, color }) => (
                    <div key={label} className="text-center p-2 bg-slate-50 rounded-lg">
                      <p className={`text-base font-bold ${color}`}>{value}</p>
                      <p className="text-xs text-slate-400">{label}</p>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}

      <Modal isOpen={!!selected} onClose={() => setSelected(null)} title={selected?.name} size="lg">
        {selected && (
          <div className="space-y-4">
            <div className="flex items-center gap-3 flex-wrap">
              <Badge status={selected.riskLevel} />
              <RiskMeter score={selected.riskScore} />
              <Badge status={selected.status} size="xs" />
            </div>
            <div className="grid grid-cols-2 gap-4">
              {[
                ['Type', selected.type],
                ['Location', selected.location],
                ['NPI', selected.npi],
                ['Phone', selected.phone],
                ['Email', selected.contact],
                ['Enrolled', selected.enrolledDate],
              ].map(([k, v]) => (
                <div key={k}>
                  <p className="text-xs text-slate-400 mb-0.5">{k}</p>
                  <p className="text-sm font-medium text-slate-800">{v}</p>
                </div>
              ))}
            </div>
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Recent Claims</p>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr>
                      {['Claim ID', 'Patient', 'Amount', 'Status'].map(h => (
                        <th key={h} className="table-header">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {provClaims.length === 0 ? (
                      <tr>
                        <td colSpan={4} className="text-center py-4 text-slate-400 text-sm">No claims for this provider.</td>
                      </tr>
                    ) : provClaims.slice(0, 4).map(c => (
                      <tr key={c.realId} className="table-row">
                        <td className="table-cell font-mono text-xs text-rose-700">{c.id}</td>
                        <td className="table-cell font-medium">{c.patient}</td>
                        <td className="table-cell font-semibold">${c.amount.toLocaleString()}</td>
                        <td className="table-cell"><Badge status={c.status} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}

