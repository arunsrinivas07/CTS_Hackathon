import { useState } from 'react';
import { Save, CheckCircle, XCircle, Clock, StickyNote, Plus, Loader2 } from 'lucide-react';
import PageHeader from '../../components/ui/PageHeader';
import Badge from '../../components/ui/Badge';
import { investigations } from '../../data/mockData';

const decisionOptions = [
  { value: 'approve', label: 'Approve Claim', icon: CheckCircle, color: 'border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-100' },
  { value: 'deny', label: 'Deny Claim', icon: XCircle, color: 'border-red-200 bg-red-50 text-red-700 hover:bg-red-100' },
  { value: 'partial', label: 'Partial Approval', icon: Clock, color: 'border-amber-200 bg-amber-50 text-amber-700 hover:bg-amber-100' },
  { value: 'refer', label: 'Refer for Further Review', icon: StickyNote, color: 'border-rose-200 bg-rose-50 text-rose-700 hover:bg-rose-100' },
];

const initialNotes = investigations.map(inv => ({
  invId: inv.id,
  claimId: inv.claimId,
  provider: inv.provider,
  type: inv.type,
  amount: inv.amount,
  decision: inv.status === 'resolved' ? 'deny' : '',
  note: inv.findings || '',
  savedAt: inv.status === 'resolved' ? '2024-07-05 14:32' : '',
}));

export default function DecisionNotes() {
  const [notes, setNotes] = useState(initialNotes);
  const [active, setActive] = useState(initialNotes[0]);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const current = notes.find(n => n.invId === active?.invId);

  const update = (field, value) => {
    setNotes(prev => prev.map(n => n.invId === active.invId ? { ...n, [field]: value } : n));
    setSaved(false);
  };

  const handleSave = async () => {
    setSaving(true);
    await new Promise(r => setTimeout(r, 800));
    const now = new Date().toISOString().slice(0, 16).replace('T', ' ');
    setNotes(prev => prev.map(n => n.invId === active.invId ? { ...n, savedAt: now } : n));
    setSaving(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  return (
    <div>
      <PageHeader title="Decision & Notes" subtitle="Record investigation decisions and supporting notes." />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Case List */}
        <div className="card overflow-hidden">
          <div className="px-4 py-3 border-b border-slate-100 bg-slate-50">
            <p className="text-xs font-semibold text-slate-600 uppercase tracking-wide">Investigations</p>
          </div>
          <div className="divide-y divide-slate-50">
            {notes.map(n => (
              <button
                key={n.invId}
                onClick={() => { setActive(n); setSaved(false); }}
                className={`w-full text-left px-4 py-3.5 hover:bg-slate-50 transition-colors ${active?.invId === n.invId ? 'bg-rose-50' : ''}`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className={`text-xs font-mono font-semibold ${active?.invId === n.invId ? 'text-rose-700' : 'text-slate-700'}`}>{n.invId}</span>
                  {n.decision && <Badge status={n.decision === 'approve' ? 'approved' : n.decision === 'deny' ? 'rejected' : 'pending'} size="xs" />}
                </div>
                <p className="text-xs text-slate-600 truncate">{n.type}</p>
                <p className="text-xs text-slate-400 truncate">{n.provider}</p>
                {n.savedAt && <p className="text-xs text-slate-300 mt-0.5">Saved {n.savedAt}</p>}
              </button>
            ))}
          </div>
        </div>

        {/* Decision Form */}
        {current && (
          <div className="card p-5 lg:col-span-2">
            <div className="flex items-start justify-between mb-5 pb-4 border-b border-slate-100">
              <div>
                <div className="flex items-center gap-2 mb-0.5">
                  <span className="text-sm font-mono font-semibold text-rose-700">{current.invId}</span>
                  <span className="text-xs font-mono text-slate-400">{current.claimId}</span>
                </div>
                <p className="text-base font-semibold text-slate-800">{current.type}</p>
                <p className="text-xs text-slate-500">{current.provider} · <span className="font-semibold">${current.amount.toLocaleString()}</span></p>
              </div>
              {saved && (
                <div className="flex items-center gap-1.5 text-emerald-600 text-sm">
                  <CheckCircle size={14} /> Saved
                </div>
              )}
            </div>

            {/* Decision Selector */}
            <div className="mb-5">
              <label className="label">Decision</label>
              <div className="grid grid-cols-2 gap-2">
                {decisionOptions.map(opt => {
                  const Icon = opt.icon;
                  const isSelected = current.decision === opt.value;
                  return (
                    <button
                      key={opt.value}
                      onClick={() => update('decision', opt.value)}
                      className={`flex items-center gap-2 px-3 py-2.5 rounded-lg border text-sm font-medium transition-colors ${
                        isSelected ? opt.color + ' ring-2 ring-offset-1 ring-current/30' : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50'
                      }`}
                    >
                      <Icon size={14} />
                      {opt.label}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Notes */}
            <div className="mb-5">
              <label className="label">Investigation Notes</label>
              <textarea
                className="input min-h-[140px] resize-none"
                placeholder="Document your investigation findings, evidence reviewed, and rationale for the decision…"
                value={current.note}
                onChange={e => update('note', e.target.value)}
              />
            </div>

            {/* Action Buttons */}
            <div className="flex items-center gap-3">
              <button onClick={handleSave} disabled={saving || !current.decision} className="btn-primary disabled:opacity-60">
                {saving ? <><Loader2 size={14} className="animate-spin" /> Saving…</> : <><Save size={14} /> Save Decision</>}
              </button>
              <button className="btn-secondary" onClick={() => update('note', '')}>
                Clear Notes
              </button>
            </div>

            {/* Saved History */}
            {current.savedAt && (
              <p className="text-xs text-slate-400 mt-3">Last saved: {current.savedAt}</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
