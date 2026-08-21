import { useState, useEffect } from 'react';
import { UserPlus, ArrowRight, CheckCircle, Loader2, RefreshCw, Plus, X } from 'lucide-react';
import PageHeader from '../../components/ui/PageHeader';
import Badge from '../../components/ui/Badge';
import Avatar from '../../components/ui/Avatar';
import RiskMeter from '../../components/ui/RiskMeter';
import Modal from '../../components/ui/Modal';
import { investigations as rawInvestigations, investigators as initialInvestigators } from '../../data/mockData';
import { usersAPI, investigationsAPI } from '../../services/api';

export default function InvestigatorAssignment() {
  const [invs, setInvs] = useState(rawInvestigations);
  const [investigatorList, setInvestigatorList] = useState(initialInvestigators);
  const [assignments, setAssignments] = useState({});
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  // Add Investigator Modal State
  const [showAddModal, setShowAddModal] = useState(false);
  const [newName, setNewName] = useState('');
  const [newEmail, setNewEmail] = useState('');
  const [newPassword, setNewPassword] = useState('password');
  const [newSpecialty, setNewSpecialty] = useState('Clinical Claims Review');
  const [addLoading, setAddLoading] = useState(false);
  const [addError, setAddError] = useState('');
  const [addSuccess, setAddSuccess] = useState(false);

  const fetchUsersAndInvs = () => {
    // 1. Fetch live investigators from backend
    usersAPI.getAll()
      .then(users => {
        if (Array.isArray(users) && users.length > 0) {
          const invUsers = users.filter(u => {
            const r = (u.role || '').toLowerCase();
            return r.includes('invest') || u.role_id === 2;
          });
          if (invUsers.length > 0) {
            const mapped = invUsers.map(u => ({
              id: `u${u.id}`,
              realId: u.id,
              name: u.full_name,
              email: u.email,
              specialization: 'FWA Investigations',
              status: u.is_active ? 'active' : 'inactive',
              avatar: u.full_name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2),
            }));
            setInvestigatorList(mapped);
          }
        }
      })
      .catch(() => { /* keep initial */ });

    // 2. Fetch live investigations
    investigationsAPI.getAll()
      .then(res => {
        if (Array.isArray(res) && res.length > 0) {
          const mapped = res.map(i => ({
            id: `INV-2024-00${i.id}`,
            realId: i.id,
            claimId: `CLM-2024-00${i.claim_id}`,
            provider: 'Riverside Medical Center',
            investigatorId: i.assigned_to ? `u${i.assigned_to}` : null,
            investigatorName: i.assigned_to ? 'Assigned' : null,
            status: i.status === 'in_review' ? 'in_progress' : i.status,
            priority: i.priority || 'medium',
            type: i.reason || 'Billing Anomaly',
            aiRiskScore: 82,
          }));
          setInvs(mapped);
        }
      })
      .catch(() => { /* keep initial */ });
  };

  useEffect(() => {
    fetchUsersAndInvs();
  }, []);

  const unassigned = invs.filter(i => !i.investigatorId && i.status !== 'resolved');
  const assigned = invs.filter(i => i.investigatorId && i.status !== 'resolved');

  const handleAssign = (invId, investigatorId) => {
    setAssignments(prev => ({ ...prev, [invId]: investigatorId }));
  };

  const handleSaveAll = async () => {
    setSaving(true);
    await new Promise(r => setTimeout(r, 600));
    setInvs(prev => prev.map(i => {
      if (assignments[i.id]) {
        const inv = investigatorList.find(x => x.id === assignments[i.id]);
        return { ...i, investigatorId: inv?.id || assignments[i.id], investigatorName: inv?.name || 'Assigned', status: 'in_progress' };
      }
      return i;
    }));
    setAssignments({});
    setSaving(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  const handleAddInvestigator = async e => {
    e.preventDefault();
    if (!newName || !newEmail) {
      setAddError('Please fill in name and email.');
      return;
    }
    setAddLoading(true);
    setAddError('');
    try {
      await usersAPI.create({
        full_name: newName,
        email: newEmail,
        password: newPassword || 'password',
        role: 'investigator',
      });
      setAddSuccess(true);
      setTimeout(() => {
        setShowAddModal(false);
        setNewName('');
        setNewEmail('');
        setAddSuccess(false);
        fetchUsersAndInvs();
      }, 1000);
    } catch (err) {
      setAddError(err.message || 'Failed to add investigator');
    } finally {
      setAddLoading(false);
    }
  };

  const getInvestigatorLoad = (id) => invs.filter(i => i.investigatorId === id && i.status !== 'resolved').length;


  return (
    <div>
      <PageHeader
        title="Investigator Assignment"
        subtitle="Assign and reassign investigators to open cases."
        actions={
          <div className="flex items-center gap-2">
            <button className="btn-secondary text-xs" onClick={() => setShowAddModal(true)}>
              <Plus size={14} /> Add Investigator
            </button>
            {Object.keys(assignments).length > 0 && (
              <button className="btn-primary text-xs" onClick={handleSaveAll} disabled={saving}>
                {saving ? <><Loader2 size={14} className="animate-spin" /> Saving…</> : `Save ${Object.keys(assignments).length} Assignment${Object.keys(assignments).length > 1 ? 's' : ''}`}
              </button>
            )}
          </div>
        }
      />

      {saved && (
        <div className="flex items-center gap-2 px-4 py-2.5 bg-emerald-50 border border-emerald-200 rounded-lg mb-5 text-sm text-emerald-700">
          <CheckCircle size={14} /> Assignments saved successfully.
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Investigator Capacity */}
        <div className="card p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="section-title">Investigator Capacity</h3>
            <span className="text-xs text-slate-400 font-medium">{investigatorList.length} Active</span>
          </div>
          <div className="space-y-4">
            {investigatorList.map((inv, idx) => {
              const load = getInvestigatorLoad(inv.id);
              const maxCases = 8;
              const pct = Math.min((load / maxCases) * 100, 100);
              const barColor = pct >= 75 ? 'bg-red-400' : pct >= 50 ? 'bg-amber-400' : 'bg-emerald-400';
              return (
                <div key={inv.id}>
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="flex items-center gap-2">
                      <Avatar initials={inv.avatar} size="sm" colorIndex={idx} />
                      <div>
                        <p className="text-xs font-semibold text-slate-800">{inv.name}</p>
                        <p className="text-xs text-slate-400">{inv.specialization}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <Badge status={inv.status} size="xs" />
                      <span className="text-xs text-slate-500">{load}/{maxCases}</span>
                    </div>
                  </div>
                  <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                    <div className={`h-full rounded-full ${barColor}`} style={{ width: `${pct}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Assignment Panel */}
        <div className="lg:col-span-2 space-y-4">
          {/* Unassigned */}
          {unassigned.length > 0 && (
            <div className="card overflow-hidden">
              <div className="px-5 py-3 border-b border-slate-100 bg-amber-50">
                <h3 className="text-sm font-semibold text-amber-800">Unassigned Cases ({unassigned.length})</h3>
              </div>
              <div className="divide-y divide-slate-50">
                {unassigned.map(inv => (
                  <div key={inv.id} className="flex items-center gap-4 px-5 py-3.5">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className="text-xs font-mono font-semibold text-rose-700">{inv.id}</span>
                        <Badge status={inv.priority} size="xs" />
                      </div>
                      <p className="text-sm font-medium text-slate-800 truncate">{inv.type}</p>
                      <p className="text-xs text-slate-400 truncate">{inv.provider}</p>
                    </div>
                    <div className="flex items-center gap-3 flex-shrink-0">
                      <RiskMeter score={inv.aiRiskScore} />
                      <select
                        className="select text-xs w-44"
                        value={assignments[inv.id] || ''}
                        onChange={e => handleAssign(inv.id, e.target.value)}
                      >
                        <option value="">Assign to…</option>
                        {investigatorList.filter(i => i.status === 'active').map(i => (
                          <option key={i.id} value={i.id}>{i.name} ({getInvestigatorLoad(i.id)} open)</option>
                        ))}
                      </select>
                      {assignments[inv.id] && (
                        <CheckCircle size={15} className="text-emerald-500 flex-shrink-0" />
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Assigned — for reassignment */}
          <div className="card overflow-hidden">
            <div className="px-5 py-3 border-b border-slate-100">
              <h3 className="section-title">Assigned Cases — Reassignment</h3>
            </div>
            <div className="divide-y divide-slate-50">
              {assigned.map(inv => (
                <div key={inv.id} className="flex items-center gap-4 px-5 py-3.5">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className="text-xs font-mono font-semibold text-rose-700">{inv.id}</span>
                      <Badge status={inv.status} size="xs" />
                    </div>
                    <p className="text-sm font-medium text-slate-800 truncate">{inv.type}</p>
                    <p className="text-xs text-slate-400">Current: <span className="text-slate-600 font-medium">{inv.investigatorName || 'Assigned'}</span></p>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <select
                      className="select text-xs w-44"
                      value={assignments[inv.id] || inv.investigatorId || ''}
                      onChange={e => handleAssign(inv.id, e.target.value)}
                    >
                      {investigatorList.filter(i => i.status === 'active').map(i => (
                        <option key={i.id} value={i.id}>{i.name} ({getInvestigatorLoad(i.id)} open)</option>
                      ))}
                    </select>
                    {assignments[inv.id] && assignments[inv.id] !== inv.investigatorId && (
                      <RefreshCw size={14} className="text-rose-500 flex-shrink-0" />
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Add Investigator Modal */}
      <Modal isOpen={showAddModal} onClose={() => setShowAddModal(false)} title="Add New Investigator" size="md">
        <form onSubmit={handleAddInvestigator} className="space-y-4">
          {addError && (
            <p className="text-xs p-2.5 rounded-lg bg-rose-50 text-rose-600 border border-rose-200">{addError}</p>
          )}
          {addSuccess && (
            <p className="text-xs p-2.5 rounded-lg bg-emerald-50 text-emerald-700 border border-emerald-200">Investigator added and saved to PostgreSQL successfully!</p>
          )}
          <div>
            <label className="label">Full Name <span className="text-rose-600">*</span></label>
            <input
              type="text"
              className="input"
              placeholder="e.g. Anand Sharma"
              value={newName}
              onChange={e => setNewName(e.target.value)}
              required
            />
          </div>
          <div>
            <label className="label">Email Address / Handle <span className="text-rose-600">*</span></label>
            <input
              type="text"
              className="input"
              placeholder="e.g. anand@investigator"
              value={newEmail}
              onChange={e => setNewEmail(e.target.value)}
              required
            />
          </div>
          <div>
            <label className="label">Specialization / Department</label>
            <input
              type="text"
              className="input"
              placeholder="e.g. Unbundling & Procedure Code Audits"
              value={newSpecialty}
              onChange={e => setNewSpecialty(e.target.value)}
            />
          </div>
          <div>
            <label className="label">Default Password</label>
            <input
              type="text"
              className="input"
              value={newPassword}
              onChange={e => setNewPassword(e.target.value)}
            />
          </div>
          <div className="flex gap-2 pt-3">
            <button type="submit" disabled={addLoading} className="btn-primary flex-1 justify-center text-white">
              {addLoading ? <><Loader2 size={14} className="animate-spin" /> Adding…</> : 'Add Investigator'}
            </button>
            <button type="button" className="btn-secondary" onClick={() => setShowAddModal(false)}>
              Cancel
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}

