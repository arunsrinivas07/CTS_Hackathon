const V = {
  approved:     'bg-emerald-100 text-emerald-800 border border-emerald-200',
  rejected:     'bg-rose-100 text-rose-800 border border-rose-200',
  flagged:      'bg-amber-100 text-amber-800 border border-amber-200',
  under_review: 'bg-amber-100 text-amber-800 border border-amber-200',
  pending:      'bg-slate-100 text-slate-600 border border-slate-200',
  open:         'bg-rose-100 text-rose-800 border border-rose-200',
  in_progress:  'bg-amber-100 text-amber-800 border border-amber-200',
  resolved:     'bg-emerald-100 text-emerald-800 border border-emerald-200',
  closed:       'bg-slate-100 text-slate-500 border border-slate-200',
  active:       'bg-emerald-100 text-emerald-800 border border-emerald-200',
  on_leave:     'bg-amber-100 text-amber-800 border border-amber-200',
  low:          'bg-slate-100 text-slate-600 border border-slate-200',
  medium:       'bg-amber-100 text-amber-800 border border-amber-200',
  high:         'bg-rose-100 text-rose-800 border border-rose-200',
  critical:     'bg-rose-100 text-rose-900 border border-rose-300',
  verified:     'bg-green-100 text-green-800 border border-green-200',
  info:         'bg-rose-100 text-rose-800 border border-rose-200',
  warning:      'bg-amber-100 text-amber-800 border border-amber-200',
  approve:      'bg-emerald-100 text-emerald-800 border border-emerald-200',
  deny:         'bg-rose-100 text-rose-800 border border-rose-200',
  partial:      'bg-amber-100 text-amber-800 border border-amber-200',
  refer:        'bg-amber-100 text-amber-800 border border-amber-200',
};
const L = { under_review: 'Under Review', in_progress: 'In Progress', on_leave: 'On Leave' };

export default function Badge({ status, label, size = 'sm' }) {
  const cls = V[status] || 'bg-slate-100 text-slate-600 border border-slate-200';
  const text = label ?? (L[status] || (status ? status.charAt(0).toUpperCase() + status.slice(1) : ''));
  const sz = size === 'xs' ? 'text-[10px] px-2 py-0.5' : 'text-xs px-2.5 py-1';
  return <span className={`inline-flex items-center rounded-full font-semibold ${sz} ${cls}`}>{text}</span>;
}
