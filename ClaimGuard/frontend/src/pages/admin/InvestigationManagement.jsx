import { useState } from 'react';
import { Plus, Search, Edit2, Trash2, CheckCircle, Loader2 } from 'lucide-react';
import PageHeader from '../../components/ui/PageHeader';
import Badge from '../../components/ui/Badge';
import Modal from '../../components/ui/Modal';
import EmptyState from '../../components/ui/EmptyState';
import { investigations as initialInvestigations, investigators } from '../../data/mockData';

export default function InvestigationManagement() {
  const [invs, setInvs] = useState(initialInvestigations);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [editModal, setEditModal] = useState(null);
  const [deleteConfirm, setDeleteConfirm] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const [form, setForm] = useState({});

  const openEdit = (inv) => { setForm({ ...inv }); setEditModal(inv); };

  const handleSave = async () => {
    setSaving(true);
    await new Promise(r => setTimeout(r, 700));
    setInvs(prev => prev.map(i => i.id === form.id ? { ...form } : i));
    setSaving(false);
    setEditModal(null);
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  const handleDelete = () => {
    setInvs(prev => prev.filter(i => i.id !== deleteConfirm.id));
    setDeleteConfirm(null);
  };

  const filtered = invs.filter(i => {
    const s = search.toLowerCase();
    const match = i.id.toLowerCase().includes(s) || i.provider.toLowerCase().includes(s);
    const matchStatus = statusFilter === 'all' || i.status === statusFilter;
    return match && matchStatus;
  });

  return (
    <div>
      <PageHeader title="Investigation Management" subtitle="Create, edit, and manage all investigation records." />

      {saved && (
        <div className="flex items-center gap-2 px-4 py-2.5 bg-emerald-50 border border-emerald-200 rounded-lg mb-4 text-sm text-emerald-700">
          <CheckCircle size={14} /> Investigation updated successfully.
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3 mb-5">
        <div className="relative flex-1">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input className="input pl-9" placeholder="Search investigations…" value={search} onChange={e => setSearch(e.target.value)} />
        </div>
        <select className="select w-full sm:w-40" value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
          <option value="all">All Statuses</option>
          <option value="open">Open</option>
          <option value="in_progress">In Progress</option>
          <option value="resolved">Resolved</option>
        </select>
      </div>

      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr>
                {['ID', 'Provider', 'Type', 'Amount', 'Priority', 'Status', 'Investigator', 'Actions'].map(h => (
                  <th key={h} className="table-header whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr><td colSpan={8}><EmptyState title="No investigations found" /></td></tr>
              ) : filtered.map(inv => (
                <tr key={inv.id} className="table-row">
                  <td className="table-cell font-mono text-xs text-rose-700 font-semibold">{inv.id}</td>
                  <td className="table-cell text-slate-600 max-w-[110px] truncate">{inv.provider}</td>
                  <td className="table-cell text-slate-500 max-w-[120px] truncate">{inv.type}</td>
                  <td className="table-cell font-semibold">${inv.amount.toLocaleString()}</td>
                  <td className="table-cell"><Badge status={inv.priority} size="xs" /></td>
                  <td className="table-cell"><Badge status={inv.status} /></td>
                  <td className="table-cell text-slate-500">{inv.investigatorName || '—'}</td>
                  <td className="table-cell">
                    <div className="flex items-center gap-1">
                      <button className="p-1.5 rounded hover:bg-slate-100 text-slate-400 hover:text-rose-600 transition-colors" onClick={() => openEdit(inv)}>
                        <Edit2 size={13} />
                      </button>
                      <button className="p-1.5 rounded hover:bg-red-50 text-slate-400 hover:text-red-500 transition-colors" onClick={() => setDeleteConfirm(inv)}>
                        <Trash2 size={13} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Edit Modal */}
      <Modal isOpen={!!editModal} onClose={() => setEditModal(null)} title={`Edit — ${editModal?.id}`} size="md">
        {editModal && (
          <div className="space-y-4">
            <div>
              <label className="label">Status</label>
              <select className="select" value={form.status} onChange={e => setForm(f => ({ ...f, status: e.target.value }))}>
                <option value="open">Open</option>
                <option value="in_progress">In Progress</option>
                <option value="resolved">Resolved</option>
              </select>
            </div>
            <div>
              <label className="label">Priority</label>
              <select className="select" value={form.priority} onChange={e => setForm(f => ({ ...f, priority: e.target.value }))}>
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </div>
            <div>
              <label className="label">Assigned Investigator</label>
              <select className="select" value={form.investigatorId || ''} onChange={e => {
                const inv = investigators.find(i => i.id === e.target.value);
                setForm(f => ({ ...f, investigatorId: inv?.id || null, investigatorName: inv?.name || null }));
              }}>
                <option value="">Unassigned</option>
                {investigators.map(i => <option key={i.id} value={i.id}>{i.name}</option>)}
              </select>
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

      {/* Delete Confirm Modal */}
      <Modal isOpen={!!deleteConfirm} onClose={() => setDeleteConfirm(null)} title="Confirm Delete" size="sm">
        {deleteConfirm && (
          <div className="space-y-4">
            <p className="text-sm text-slate-700">
              Are you sure you want to delete investigation <strong>{deleteConfirm.id}</strong>? This action cannot be undone.
            </p>
            <div className="flex gap-2">
              <button className="btn-danger flex-1 justify-center" onClick={handleDelete}>Delete</button>
              <button className="btn-secondary flex-1 justify-center" onClick={() => setDeleteConfirm(null)}>Cancel</button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
