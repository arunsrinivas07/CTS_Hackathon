import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Filter, ArrowRight, Clock } from 'lucide-react';
import PageHeader from '../../components/ui/PageHeader';
import Badge from '../../components/ui/Badge';
import RiskMeter from '../../components/ui/RiskMeter';
import EmptyState from '../../components/ui/EmptyState';
import { investigations } from '../../data/mockData';

const priorityOrder = { critical: 0, high: 1, medium: 2, low: 3 };
const priorityBadge = {
  critical: 'bg-red-100 text-red-700 border border-red-200',
  high: 'bg-amber-50 text-amber-700 border border-amber-200',
  medium: 'bg-blue-50 text-blue-700 border border-blue-200',
  low: 'bg-slate-100 text-slate-500 border border-slate-200',
};

export default function InvestigationQueue() {
  const navigate = useNavigate();
  const [search, setSearch] = useState('');
  const [priorityFilter, setPriorityFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');

  const filtered = investigations
    .filter(i => {
      const s = search.toLowerCase();
      const match = i.id.toLowerCase().includes(s) || i.provider.toLowerCase().includes(s) || i.type.toLowerCase().includes(s);
      const matchP = priorityFilter === 'all' || i.priority === priorityFilter;
      const matchS = statusFilter === 'all' || i.status === statusFilter;
      return match && matchP && matchS;
    })
    .sort((a, b) => priorityOrder[a.priority] - priorityOrder[b.priority]);

  return (
    <div>
      <PageHeader
        title="Investigation Queue"
        subtitle={`${investigations.filter(i => i.status !== 'resolved').length} active investigations`}
      />

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3 mb-5">
        <div className="relative flex-1">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            className="input pl-9"
            placeholder="Search by ID, provider, or type…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
        <select className="select w-full sm:w-40" value={priorityFilter} onChange={e => setPriorityFilter(e.target.value)}>
          <option value="all">All Priorities</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
        <select className="select w-full sm:w-40" value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
          <option value="all">All Statuses</option>
          <option value="open">Open</option>
          <option value="in_progress">In Progress</option>
          <option value="resolved">Resolved</option>
        </select>
      </div>

      {/* Queue Cards */}
      {filtered.length === 0 ? (
        <EmptyState title="No investigations found" description="Try adjusting your search or filters." />
      ) : (
        <div className="space-y-3">
          {filtered.map(inv => (
            <div
              key={inv.id}
              className="card p-4 hover:shadow-md transition-shadow cursor-pointer"
              onClick={() => navigate('/investigator/case')}
            >
              <div className="flex items-start gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <span className="text-xs font-mono font-semibold text-blue-700">{inv.id}</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${priorityBadge[inv.priority]}`}>
                      {inv.priority.charAt(0).toUpperCase() + inv.priority.slice(1)}
                    </span>
                    <Badge status={inv.status} size="xs" />
                  </div>
                  <p className="text-sm font-semibold text-slate-800">{inv.type}</p>
                  <p className="text-xs text-slate-500 mt-0.5">{inv.description}</p>
                  <div className="flex items-center gap-4 mt-2 flex-wrap">
                    <span className="text-xs text-slate-400">Provider: <span className="text-slate-600 font-medium">{inv.provider}</span></span>
                    <span className="text-xs text-slate-400">Claim: <span className="font-mono text-blue-600">{inv.claimId}</span></span>
                  </div>
                </div>
                <div className="flex flex-col items-end gap-2 flex-shrink-0">
                  <span className="text-base font-bold text-slate-800">${inv.amount.toLocaleString()}</span>
                  <RiskMeter score={inv.aiRiskScore} />
                  <span className="text-xs text-slate-400">{inv.investigatorName || 'Unassigned'}</span>
                </div>
                <ArrowRight size={16} className="text-slate-300 self-center flex-shrink-0" />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
