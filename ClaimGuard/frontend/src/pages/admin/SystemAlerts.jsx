import { useState, useEffect } from 'react';
import { Bell, AlertTriangle, Info, CheckCircle, X, Filter } from 'lucide-react';
import PageHeader from '../../components/ui/PageHeader';
import Badge from '../../components/ui/Badge';
import { alerts as rawAlerts } from '../../data/mockData';
import { notificationsAPI } from '../../services/api';

const typeIcon = {
  critical: <AlertTriangle size={15} className="text-red-500 flex-shrink-0 mt-0.5" />,
  warning: <AlertTriangle size={15} className="text-amber-500 flex-shrink-0 mt-0.5" />,
  info: <Info size={15} className="text-rose-500 flex-shrink-0 mt-0.5" />,
};

const typeStyle = {
  critical: 'border-red-100 bg-red-50/60',
  warning: 'border-amber-100 bg-amber-50/60',
  info: 'border-rose-50 bg-rose-50/30',
};

const systemMetrics = [
  { label: 'Claims Processed (24h)', value: '47', status: 'normal' },
  { label: 'Failed Validations (24h)', value: '3', status: 'warning' },
  { label: 'API Response Time (avg)', value: '142ms', status: 'normal' },
  { label: 'System Uptime', value: '99.97%', status: 'normal' },
  { label: 'DB Query Avg', value: '28ms', status: 'normal' },
  { label: 'Pending Reviews', value: '12', status: 'warning' },
];

export default function SystemAlerts() {
  const [alerts, setAlerts] = useState(rawAlerts);
  const [typeFilter, setTypeFilter] = useState('all');

  useEffect(() => {
    notificationsAPI.getAll()
      .then(res => {
        if (Array.isArray(res) && res.length > 0) {
          const mapped = res.map(n => ({
            id: `ALT-00${n.id}`,
            realId: n.id,
            type: n.notification_type || 'info',
            message: n.message,
            date: n.created_at ? n.created_at.split('T')[0] : '2024-07-18',
            read: n.is_read,
          }));
          setAlerts(mapped);
        }
      })
      .catch(() => { /* keep initial */ });
  }, []);

  const filtered = alerts.filter(a => typeFilter === 'all' || a.type === typeFilter);
  const unread = alerts.filter(a => !a.read).length;

  const markRead = (id) => {
    setAlerts(prev => prev.map(a => a.id === id ? { ...a, read: true } : a));
  };
  const dismiss = (id) => setAlerts(prev => prev.filter(a => a.id !== id));
  const markAllRead = () => setAlerts(prev => prev.map(a => ({ ...a, read: true })));


  return (
    <div>
      <PageHeader
        title="System Alerts"
        subtitle="Monitor system-wide notifications, anomalies, and operational metrics."
        actions={
          unread > 0 ? (
            <button className="btn-secondary text-xs" onClick={markAllRead}>
              <CheckCircle size={13} /> Mark all read
            </button>
          ) : null
        }
      />

      {/* System Metrics */}
      <div className="card p-5 mb-5">
        <h3 className="section-title mb-4">System Health Metrics</h3>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
          {systemMetrics.map(m => (
            <div key={m.label} className="text-center">
              <p className={`text-xl font-bold ${m.status === 'warning' ? 'text-amber-600' : 'text-slate-800'}`}>{m.value}</p>
              <p className="text-xs text-slate-400 mt-0.5 leading-tight">{m.label}</p>
              <div className={`w-2 h-2 rounded-full mx-auto mt-1.5 ${m.status === 'warning' ? 'bg-amber-400' : 'bg-emerald-400'}`} />
            </div>
          ))}
        </div>
      </div>

      {/* Alert Stats */}
      <div className="grid grid-cols-3 gap-4 mb-5">
        {[
          { label: 'Critical', count: alerts.filter(a => a.type === 'critical').length, color: 'text-red-600', bg: 'bg-red-50', border: 'border-red-100' },
          { label: 'Warnings', count: alerts.filter(a => a.type === 'warning').length, color: 'text-amber-600', bg: 'bg-amber-50', border: 'border-amber-100' },
          { label: 'Info', count: alerts.filter(a => a.type === 'info').length, color: 'text-rose-600', bg: 'bg-rose-50', border: 'border-rose-100' },
        ].map(({ label, count, color, bg, border }) => (
          <div key={label} className={`card p-4 ${bg} border ${border}`}>
            <p className={`text-2xl font-bold ${color}`}>{count}</p>
            <p className="text-xs text-slate-500 mt-0.5">{label} Alerts</p>
          </div>
        ))}
      </div>

      {/* Filter */}
      <div className="flex items-center gap-3 mb-4">
        <div className="flex items-center gap-1.5 text-sm text-slate-500">
          <Filter size={14} />
          <span>Filter:</span>
        </div>
        {['all', 'critical', 'warning', 'info'].map(t => (
          <button
            key={t}
            onClick={() => setTypeFilter(t)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors capitalize ${
              typeFilter === t ? 'bg-rose-600 text-white' : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
            }`}
          >
            {t === 'all' ? `All (${alerts.length})` : t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
        {unread > 0 && (
          <span className="ml-auto text-xs text-slate-500">{unread} unread</span>
        )}
      </div>

      {/* Alert List */}
      <div className="space-y-2">
        {filtered.length === 0 ? (
          <div className="card p-10 text-center">
            <Bell size={28} className="text-slate-200 mx-auto mb-3" />
            <p className="text-sm text-slate-400">No alerts to display</p>
          </div>
        ) : filtered.map(alert => (
          <div
            key={alert.id}
            className={`flex items-start gap-3 px-4 py-3.5 rounded-xl border transition-colors ${typeStyle[alert.type]} ${!alert.read ? 'ring-1 ring-inset ring-slate-200' : 'opacity-75'}`}
          >
            {typeIcon[alert.type]}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-0.5">
                <Badge status={alert.type} size="xs" />
                {!alert.read && <span className="text-xs font-semibold text-rose-600">New</span>}
              </div>
              <p className="text-sm text-slate-700 leading-relaxed">{alert.message}</p>
              <p className="text-xs text-slate-400 mt-1">{alert.date}</p>
            </div>
            <div className="flex items-center gap-1 flex-shrink-0">
              {!alert.read && (
                <button
                  onClick={() => markRead(alert.id)}
                  className="p-1.5 rounded hover:bg-white/70 text-slate-400 hover:text-emerald-600 transition-colors"
                  title="Mark as read"
                >
                  <CheckCircle size={14} />
                </button>
              )}
              <button
                onClick={() => dismiss(alert.id)}
                className="p-1.5 rounded hover:bg-white/70 text-slate-400 hover:text-red-500 transition-colors"
                title="Dismiss"
              >
                <X size={14} />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
