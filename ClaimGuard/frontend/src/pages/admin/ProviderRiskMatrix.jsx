import { useState } from 'react';
import { Search, AlertTriangle } from 'lucide-react';
import PageHeader from '../../components/ui/PageHeader';
import Badge from '../../components/ui/Badge';
import RiskMeter from '../../components/ui/RiskMeter';
import Modal from '../../components/ui/Modal';
import RiskBarChart from '../../components/charts/RiskBarChart';
import { providers, claims } from '../../data/mockData';

const riskFactors = {
  'PRV-001': [
    { factor: 'Unbundling detected', weight: 'High', score: 28 },
    { factor: 'High-cost outliers', weight: 'High', score: 22 },
    { factor: 'Duplicate billing history', weight: 'Medium', score: 14 },
    { factor: 'Documentation gaps', weight: 'Low', score: 8 },
  ],
  'PRV-002': [
    { factor: 'Missing documentation', weight: 'Medium', score: 18 },
    { factor: 'Moderate claim volume', weight: 'Low', score: 12 },
    { factor: 'One rejected claim', weight: 'Low', score: 8 },
  ],
  'PRV-003': [
    { factor: 'Low claim volume', weight: 'Low', score: 12 },
    { factor: 'High approval rate', weight: 'Low', score: 6 },
    { factor: 'No active investigations', weight: 'Low', score: 4 },
  ],
  'PRV-004': [
    { factor: 'High-cost specialty billing', weight: 'High', score: 32 },
    { factor: 'Multiple open investigations', weight: 'Medium', score: 20 },
    { factor: 'Cost outlier pattern', weight: 'Medium', score: 13 },
  ],
};

const riskWeightColor = { High: 'text-red-600 bg-red-50', Medium: 'text-amber-600 bg-amber-50', Low: 'text-slate-500 bg-slate-100' };

export default function ProviderRiskMatrix() {
  const [search, setSearch] = useState('');
  const [riskFilter, setRiskFilter] = useState('all');
  const [selected, setSelected] = useState(null);
  const [sortBy, setSortBy] = useState('risk');

  const filtered = providers
    .filter(p => {
      const s = search.toLowerCase();
      const match = p.name.toLowerCase().includes(s) || p.location.toLowerCase().includes(s);
      const matchRisk = riskFilter === 'all' || p.riskLevel === riskFilter;
      return match && matchRisk;
    })
    .sort((a, b) => sortBy === 'risk' ? b.riskScore - a.riskScore : b.totalClaims - a.totalClaims);

  const selectedClaims = selected ? claims.filter(c => c.providerId === selected.id) : [];
  const factors = selected ? (riskFactors[selected.id] || []) : [];

  return (
    <div>
      <PageHeader title="Provider Risk Matrix" subtitle="Assess and monitor provider-level fraud risk scores." />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 mb-5">
        {/* Risk Distribution */}
        <div className="card p-5 lg:col-span-2">
          <h3 className="section-title mb-4">Risk Score Distribution</h3>
          <RiskBarChart />
        </div>

        {/* Summary */}
        <div className="card p-5">
          <h3 className="section-title mb-4">Risk Summary</h3>
          <div className="space-y-3">
            {[
              { label: 'High Risk Providers', value: providers.filter(p => p.riskLevel === 'high').length, color: 'text-red-600' },
              { label: 'Medium Risk Providers', value: providers.filter(p => p.riskLevel === 'medium').length, color: 'text-amber-600' },
              { label: 'Low Risk Providers', value: providers.filter(p => p.riskLevel === 'low').length, color: 'text-emerald-600' },
              { label: 'Total Providers', value: providers.length, color: 'text-slate-800' },
            ].map(({ label, value, color }) => (
              <div key={label} className="flex items-center justify-between py-1 border-b border-slate-50">
                <span className="text-sm text-slate-600">{label}</span>
                <span className={`text-sm font-bold ${color}`}>{value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3 mb-4">
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
        <select className="select w-full sm:w-40" value={sortBy} onChange={e => setSortBy(e.target.value)}>
          <option value="risk">Sort by Risk Score</option>
          <option value="claims">Sort by Claims</option>
        </select>
      </div>

      {/* Matrix Table */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr>
                {['Provider', 'Type', 'Location', 'Total Claims', 'Flagged', 'Rejected', 'Total Billed', 'Risk Score', 'Risk Level', ''].map(h => (
                  <th key={h} className="table-header whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map(p => (
                <tr key={p.id} className="table-row cursor-pointer" onClick={() => setSelected(p)}>
                  <td className="table-cell font-medium">{p.name}</td>
                  <td className="table-cell text-slate-500">{p.type}</td>
                  <td className="table-cell text-slate-500 whitespace-nowrap">{p.location}</td>
                  <td className="table-cell text-center font-semibold">{p.totalClaims}</td>
                  <td className="table-cell text-center font-semibold text-amber-600">{p.flaggedClaims}</td>
                  <td className="table-cell text-center font-semibold text-red-500">{p.rejectedClaims}</td>
                  <td className="table-cell font-semibold whitespace-nowrap">${(p.totalBilled / 1000).toFixed(0)}k</td>
                  <td className="table-cell"><RiskMeter score={p.riskScore} /></td>
                  <td className="table-cell"><Badge status={p.riskLevel} /></td>
                  <td className="table-cell text-rose-600 text-xs font-medium cursor-pointer hover:underline">Details</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Provider Risk Detail Modal */}
      <Modal isOpen={!!selected} onClose={() => setSelected(null)} title={`Risk Profile — ${selected?.name}`} size="xl">
        {selected && (
          <div className="space-y-5">
            <div className="flex items-center gap-3 flex-wrap">
              <Badge status={selected.riskLevel} />
              <RiskMeter score={selected.riskScore} />
              <span className="text-sm text-slate-500">Score: <strong className="text-slate-800">{selected.riskScore}/100</strong></span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {[
                { label: 'Total Claims', value: selected.totalClaims },
                { label: 'Approved', value: selected.approvedClaims, color: 'text-emerald-600' },
                { label: 'Flagged', value: selected.flaggedClaims, color: 'text-amber-600' },
                { label: 'Rejected', value: selected.rejectedClaims, color: 'text-red-500' },
              ].map(({ label, value, color }) => (
                <div key={label} className="text-center p-3 bg-slate-50 rounded-lg">
                  <p className={`text-xl font-bold ${color || 'text-slate-800'}`}>{value}</p>
                  <p className="text-xs text-slate-500 mt-0.5">{label}</p>
                </div>
              ))}
            </div>

            {factors.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Risk Factors</p>
                <div className="space-y-2">
                  {factors.map((f, i) => (
                    <div key={i} className="flex items-center justify-between px-3 py-2 bg-slate-50 rounded-lg">
                      <div className="flex items-center gap-2">
                        <AlertTriangle size={13} className="text-amber-500" />
                        <span className="text-sm text-slate-700">{f.factor}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${riskWeightColor[f.weight]}`}>{f.weight}</span>
                        <span className="text-xs font-semibold text-slate-600">+{f.score}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div>
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
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
