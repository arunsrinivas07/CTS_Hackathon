import { Bell, Search, ChevronDown } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { notificationsAPI } from '../../services/api';
import { useState, useEffect } from 'react';

const PT = {
  '/provider': 'Dashboard', '/provider/submit': 'Submit Claim', '/provider/claims': 'My Claims',
  '/provider/timeline': 'Claim Timeline', '/provider/documents': 'Document Center', '/provider/profile': 'Facility Profile',
  '/investigator': 'Command Center', '/investigator/queue': 'Investigation Queue',
  '/investigator/claims': 'Claims Repository', '/investigator/documents': 'Document Verification',
  '/investigator/providers': 'Provider Intelligence', '/investigator/case': 'Case Detail',
  '/investigator/ai-analysis': 'AI Business Analysis', '/investigator/ai-copilot': 'AI Case Copilot',
  '/investigator/decisions': 'Decision & Notes',
  '/admin': 'Executive Dashboard', '/admin/investigations': 'All Investigations',
  '/admin/risk-matrix': 'Provider Risk Matrix', '/admin/workload': 'Workload & Staffing',
  '/admin/inv-management': 'Investigation Management', '/admin/providers': 'Provider Details',
  '/admin/assignments': 'Investigator Assignment', '/admin/alerts': 'System Alerts',
};

const roleMeta = {
  provider: { label: 'Provider Portal', dot: '#9F1239' },
  investigator: { label: 'Investigator Portal', dot: '#4A7C59' },
  admin: { label: 'Admin Portal', dot: '#9F1239' },
};

export default function Navbar({ currentPath }) {
  const { user } = useAuth();
  const [showAlerts, setShowAlerts] = useState(false);
  const [alerts, setAlerts] = useState([]);

  useEffect(() => {
    if (user && user.role !== 'provider') {
      let isMounted = true;
      notificationsAPI.getAll()
        .then(res => {
          if (Array.isArray(res) && isMounted) {
            const mapped = res.map(n => ({
              id: n.id,
              type: n.notification_type || 'info',
              message: n.message,
              date: n.created_at ? n.created_at.split('T')[0] : '2026-08-21',
              read: n.is_read,
            }));
            setAlerts(mapped);
          }
        })
        .catch(() => { });
      return () => { isMounted = false; };
    }
  }, [user]);

  const unread = alerts.filter(a => !a.read).length;
  let title = PT[currentPath];
  if (!title) {
    if (currentPath?.startsWith('/investigations/') || currentPath?.startsWith('/investigator/case/')) {
      title = 'Case Detail';
    } else {
      title = 'ClaimGuard AI';
    }
  }
  const meta = roleMeta[user?.role] || roleMeta.provider;

  const dotColor = { critical: '#DC2626', warning: '#F59E0B', info: '#9F1239' };

  return (
    <header className="topbar">
      {/* Left: accent bar + title */}
      <div className="flex items-center gap-3 flex-1 min-w-0">
        <div className="w-1 h-7 rounded-full flex-shrink-0"
          style={{ background: `linear-gradient(180deg, ${meta.dot}, #4A7C59)` }} />
        <div className="min-w-0">
          <h1 className="text-base font-bold text-slate-900 leading-tight truncate">{title}</h1>
          <p className="text-xs font-semibold leading-tight text-slate-400">{meta.label}</p>
        </div>
      </div>

      {/* Search */}
      <div className="search-pill w-52 flex-shrink-0 hidden sm:flex">
        <Search size={14} className="flex-shrink-0 text-slate-400" />
        <span className="text-sm">Search anything...</span>
      </div>

      {/* Right actions */}
      <div className="flex items-center gap-2 flex-shrink-0">
        {/* Bell — not for provider */}
        {user?.role !== 'provider' && (
          <div className="relative">
            <button
              onClick={() => setShowAlerts(v => !v)}
              className="relative w-9 h-9 flex items-center justify-center rounded-xl transition-colors"
              style={{ background: '#F1F5F9', color: '#64748B' }}
              onMouseEnter={e => { e.currentTarget.style.background = '#E7E1DC'; e.currentTarget.style.color = '#0F172A'; }}
              onMouseLeave={e => { e.currentTarget.style.background = '#F1F5F9'; e.currentTarget.style.color = '#64748B'; }}
            >
              <Bell size={16} />
              {unread > 0 && (
                <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full ring-2 ring-white"
                  style={{ background: '#DC2626' }} />
              )}
            </button>

            {showAlerts && (
              <>
                <div className="fixed inset-0 z-30" onClick={() => setShowAlerts(false)} />
                <div className="absolute right-0 top-full mt-2 w-80 bg-white rounded-2xl shadow-xl z-40 overflow-hidden"
                  style={{ border: '1px solid #E7E1DC', boxShadow: '0 8px 32px rgba(15,23,42,0.08)' }}>
                  <div className="px-5 py-3.5 flex items-center justify-between border-b border-slate-100">
                    <p className="text-sm font-bold text-slate-900">Notifications</p>
                    {unread > 0 && (
                      <span className="text-xs font-bold px-2 py-0.5 rounded-full text-white"
                        style={{ background: '#DC2626' }}>{unread} new</span>
                    )}
                  </div>
                  <div className="max-h-72 overflow-y-auto divide-y divide-slate-100">
                    {alerts.map(a => (
                      <div key={a.id}
                        className="px-5 py-3 transition-colors"
                        style={{ background: !a.read ? '#FAF9F7' : '#FFFFFF' }}
                        onMouseEnter={e => { e.currentTarget.style.background = '#F1F5F9'; }}
                        onMouseLeave={e => { e.currentTarget.style.background = !a.read ? '#FAF9F7' : '#FFFFFF'; }}
                      >
                        <div className="flex items-start gap-2.5">
                          <div className="w-2 h-2 rounded-full mt-1.5 flex-shrink-0"
                            style={{ background: dotColor[a.type] || '#64748B' }} />
                          <div>
                            <p className="text-xs text-slate-700 leading-relaxed">{a.message}</p>
                            <p className="text-[10px] mt-0.5 text-slate-400">{a.date}</p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            )}
          </div>
        )}

        {/* User avatar */}
        {user && (
          <button className="flex items-center gap-2.5 pl-2 border-l border-slate-200">
            <div className="w-8 h-8 rounded-xl flex items-center justify-center text-xs font-bold text-white flex-shrink-0"
              style={{ background: 'linear-gradient(135deg, #9F1239, #4A7C59)' }}>
              {user.avatar}
            </div>
            <div className="hidden sm:block text-left">
              <p className="text-xs font-bold text-slate-800 leading-tight">{user.name.split(' ')[0]}</p>
              <p className="text-[10px] leading-tight capitalize text-slate-400">{user.role}</p>
            </div>
            <ChevronDown size={13} className="hidden sm:block text-slate-400" />
          </button>
        )}
      </div>
    </header>
  );
}
