import { useState } from 'react';
import { Search, Eye, UserPlus } from 'lucide-react';
import PageHeader from '../../components/ui/PageHeader';
import Badge from '../../components/ui/Badge';
import RiskMeter from '../../components/ui/RiskMeter';
import Modal from '../../components/ui/Modal';
import EmptyState from '../../components/ui/EmptyState';
import { investigations, investigators } from '../../data/mockData';

const priorityBadge = {
  critical: 'bg-red-100 text-red-700 border border-red-200',
  high: 'bg-amber-50 text-amber-700 border border-amber-200',
  medium: 'bg-rose-50 text-rose-700 border border-rose-200',
  low: 'bg-slate-100 text-slate-500 border border-slate-200',
};

export default function AllInvestigations() {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [priorityFilter, setPriorityFilter] = useState('all');
  const [selected, setSelected] = useState(null);
  const [assignModal, setAssignModal] = useState(null);
  const [assignTo, setAssignTo] = useState('');
  const [assignSuccess, setAssignSuccess] = useState(false);

  const filtered = investigations.filter(i => {
    const s = search.toLowerCase();
    const match = i.id.toLowerCase().includes(s) || i.provider.toLowerCase().includes(s) || i.type.toLowerCase().includes(s);
    const matchStatus = statusFilter === 'all' || i.status === statusFilter;
    const matchPriority = priorityFilter === 'all' || i.priority === priorityFilter;
    return match && matchStatus && matchPriority;
  });

  const handleAssign = async () => {
    await new Promise(r => setTimeout(r, 700));
    setAssignModal(null);
    setAssignSuccess(true);
    setTimeout(() => setAssignSuccess(false), 3000);
  };

  return (
    <div>
      <PageHeader title="All Investigations" subtitle={`${investigations.length} total investigations`} />

      {assignSuccess && (
        <div className="flex items-center gap-2 px-4 py-2.5 bg-emerald-50 border border-emerald-200 rounded-lg mb-4 text-sm text-emerald-700">
          Investigator assigned successfully.
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3 mb-5">
        <div className="relative flex-1">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input className="input pl-9" placeholder="Search by ID, provider, type…" value={search} onChange={e => setSearch(e.target.value)} />
        </div>
        <select className="select w-full sm:w-40" value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
          <option value="all">All Statuses</option>
          <option value="open">Open</option>
          <option value="in_progress">In Progress</option>
          <option value="resolved">Resolved</option>
        </select>
        <select className="select w-full sm:w-40" value={priorityFilter} onChange={e => setPriorityFilter(e.target.value)}>
          <option value="all">All Priorities</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
      </div>

      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr>
                {['Inv. ID', 'Claim ID', 'Provider', 'Type', 'Amount', 'Priority', 'Status', 'Investigator', ''].map(h => (
                  <th key={h} className="table-header whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr><td colSpan={9}><EmptyState title="No investigations found" /></td></tr>
              ) : filtered.map(inv => (
                <tr key={inv.id} className="table-row">
                  <td className="table-cell font-mono text-xs text-rose-700 font-semibold">{inv.id}</td>
                  <td className="table-cell font-mono text-xs text-slate-500">{inv.claimId}</td>
                  <td className="table-cell text-slate-600 max-w-[120px] truncate">{inv.provider}</td>
                  <td className="table-cell text-slate-500 max-w-[120px] truncate">{inv.type}</td>
                  <td className="table-cell font-semibold whitespace-nowrap">${inv.amount.toLocaleString()}</td>
                  <td className="table-cell">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${priorityBadge[inv.priority]}`}>
                      {inv.priority.charAt(0).toUpperCase() + inv.priority.slice(1)}
                    </span>
                  </td>
                  <td className="table-cell"><Badge status={inv.status} /></td>
                  <td className="table-cell text-slate-500 whitespace-nowrap">{inv.investigatorName || <span className="text-slate-300">Unassigned</span>}</td>
                  <td className="table-cell">
                    <div className="flex items-center gap-1">
                      <button className="p-1.5 rounded hover:bg-slate-100 text-slate-400 hover:text-slate-700 transition-colors" onClick={() => setSelected(inv)}>
                        <Eye size={14} />
                      </button>
                      <button className="p-1.5 rounded hover:bg-rose-50 text-slate-400 hover:text-rose-600 transition-colors" onClick={() => { setAssignModal(inv); setAssignTo(''); }}>
                        <UserPlus size={14} />
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
      <Modal isOpen={!!selected} onClose={() => setSelected(null)} title={selected?.id} size="lg">
        {selected && (
          <div className="space-y-4">
            <div className="flex gap-2 flex-wrap">
              <Badge status={selected.status} />
              <Badge status={selected.priority} />
            </div>
            <div className="grid grid-cols-2 gap-4">
              {[
                ['Type', selected.type],
                ['Provider', selected.provider],
                ['Claim ID', selected.claimId],
                ['Amount', `$${selected.amount.toLocaleString()}`],
                ['Opened', selected.openedDate],
                ['Investigator', selected.investigatorName || 'Unassigned'],
                ['AI Risk Score', selected.aiRiskScore],
              ].map(([k, v]) => (
                <div key={k}>
                  <p className="text-xs text-slate-400 mb-0.5">{k}</p>
                  <p className="text-sm font-medium text-slate-800">{v}</p>
                </div>
              ))}
            </div>
            <div>
              <p className="text-xs text-slate-400 mb-1">Description</p>
              <p className="text-sm text-slate-700 bg-slate-50 rounded-lg px-3 py-2">{selected.description}</p>
            </div>
            {selected.findings && (
              <div>
                <p className="text-xs text-slate-400 mb-1">Findings</p>
                <p className="text-sm text-slate-700 bg-slate-50 rounded-lg px-3 py-2">{selected.findings}</p>
              </div>
            )}
          </div>
        )}
      </Modal>

      {/* Assign Modal */}
      <Modal isOpen={!!assignModal} onClose={() => setAssignModal(null)} title={`Assign Investigator — ${assignModal?.id}`} size="sm">
        {assignModal && (
          <div className="space-y-4">
            <div>
              <label className="label">Select Investigator</label>
              <select className="select" value={assignTo} onChange={e => setAssignTo(e.target.value)}>
                <option value="">Choose investigator…</option>
                {investigators.filter(i => i.status === 'active').map(i => (
                  <option key={i.id} value={i.id}>{i.name} ({i.openCases} open cases)</option>
                ))}
              </select>
            </div>
            <div className="flex gap-2">
              <button className="btn-primary flex-1 justify-center" onClick={handleAssign} disabled={!assignTo}>Assign</button>
              <button className="btn-secondary" onClick={() => setAssignModal(null)}>Cancel</button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
