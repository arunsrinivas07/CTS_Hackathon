import { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import {
  LayoutDashboard, FileText, ClipboardList, Clock,
  FolderOpen, Building2, Search, ListChecks, Database,
  CheckSquare, Users, Brain, Bot, StickyNote, BarChart3,
  AlertTriangle, UserCheck, Briefcase, LogOut, Settings, Zap
} from 'lucide-react';

const providerNav = [
  { icon: LayoutDashboard, to: '/provider',           label: 'Dashboard' },
  { icon: FileText,        to: '/provider/submit',    label: 'Submit Claim' },
  { icon: ClipboardList,   to: '/provider/claims',    label: 'My Claims' },
  { icon: Clock,           to: '/provider/timeline',  label: 'Timeline' },
  { icon: FolderOpen,      to: '/provider/documents', label: 'Documents' },
  { icon: Building2,       to: '/provider/profile',   label: 'Facility' },
];
const investigatorNav = [
  { icon: LayoutDashboard, to: '/investigator',             label: 'Command Center' },
  { icon: ListChecks,      to: '/investigator/queue',       label: 'Queue' },
  { icon: Database,        to: '/investigator/claims',      label: 'Claims Repository' },
  { icon: CheckSquare,     to: '/investigator/documents',   label: 'Document Verification & Requests' },
  { icon: Users,           to: '/investigator/providers',   label: 'Provider Intelligence' },
  { icon: FileText,        to: '/investigator/reports',     label: 'Investigation Reports' },
];
const adminNav = [
  { icon: BarChart3,     to: '/admin',                 label: 'Dashboard' },
  { icon: Search,        to: '/admin/investigations',  label: 'Investigations' },
  { icon: AlertTriangle, to: '/admin/risk-matrix',     label: 'Risk Matrix' },
  { icon: UserCheck,     to: '/admin/workload',        label: 'Workload' },
  { icon: Briefcase,     to: '/admin/inv-management',  label: 'Management' },
  { icon: Building2,     to: '/admin/providers',       label: 'Providers' },
  { icon: Users,         to: '/admin/assignments',     label: 'Assignments' },
  { icon: AlertTriangle, to: '/admin/alerts',          label: 'Alerts' },
];

const navMap = { provider: providerNav, investigator: investigatorNav, admin: adminNav };
const roots  = { provider: '/provider', investigator: '/investigator', admin: '/admin' };
const settingsPath = { provider: '/provider/settings', investigator: '/investigator/settings', admin: '/admin/settings' };

export default function Sidebar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [isExpanded, setIsExpanded] = useState(false);
  const nav = navMap[user?.role] || [];

  return (
    <aside
      className="w-16 h-screen flex-shrink-0 relative z-50 bg-white transition-all duration-200"
      onMouseEnter={() => setIsExpanded(true)}
      onMouseLeave={() => setIsExpanded(false)}
    >
      <div
        className={`fixed left-0 top-0 h-screen flex flex-col py-5 gap-1 transition-all duration-200 ease-in-out border-r border-slate-200 bg-white z-50 ${
          isExpanded ? 'w-64 shadow-xl px-4 items-stretch' : 'w-16 px-2 items-center'
        }`}
      >
        {/* ── Logo mark ─────────────────────────────── */}
        <div className={`flex items-center gap-3 mb-1 flex-shrink-0 ${isExpanded ? 'px-2' : ''}`}>
          <div
            className="w-10 h-10 rounded-2xl flex items-center justify-center bg-rose-600 text-white flex-shrink-0"
            style={{ boxShadow: '0 4px 12px rgba(37,99,235,0.25)' }}
          >
            <Zap size={20} color="#ffffff" strokeWidth={2} />
          </div>
          {isExpanded && (
            <span className="font-bold text-slate-900 text-sm tracking-tight truncate">ClaimGuard AI</span>
          )}
        </div>

        {/* CG / Brand label */}
        {!isExpanded && (
          <p
            className="text-[9px] font-bold tracking-widest uppercase mb-2 text-slate-400"
          >
            CG
          </p>
        )}

        {/* Thin divider */}
        <div
          className={`mb-3 flex-shrink-0 transition-all ${isExpanded ? 'w-full' : 'w-7'}`}
          style={{ height: 1, background: '#E7E1DC' }}
        />

        {/* ── Nav icons ─────────────────────────────── */}
        <nav className="flex flex-col gap-1.5 flex-1 w-full overflow-y-auto no-scrollbar">
          {nav.map(({ icon: Icon, to, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === roots[user?.role]}
              title={isExpanded ? '' : label}
              className={({ isActive }) => `nav-icon-btn ${isActive ? 'active' : ''}`}
            >
              <Icon size={18} className="flex-shrink-0" />
              {isExpanded && <span className="text-sm font-medium truncate">{label}</span>}
            </NavLink>
          ))}
        </nav>

        {/* ── Bottom controls ────────────────────────── */}
        <div
          className={`flex flex-col gap-1.5 pt-3 w-full flex-shrink-0 border-t border-slate-200`}
        >
          <button
            className="nav-icon-btn"
            title={isExpanded ? '' : 'Settings'}
            onClick={() => navigate(settingsPath[user?.role] || '/settings')}
          >
            <Settings size={18} className="flex-shrink-0" />
            {isExpanded && <span className="text-sm font-medium">Settings</span>}
          </button>

          <button
            className="nav-icon-btn"
            title={isExpanded ? '' : 'Logout'}
            onClick={() => { logout(); navigate('/login'); }}
          >
            <LogOut size={18} className="flex-shrink-0" />
            {isExpanded && <span className="text-sm font-medium">Logout</span>}
          </button>

          {/* User avatar circle */}
          <div className={`flex items-center gap-3 mt-2 ${isExpanded ? 'px-2' : 'justify-center'}`}>
            <div
              className="w-8 h-8 rounded-full flex items-center justify-center text-[10px] font-bold flex-shrink-0"
              style={{
                background: '#F5E6E9',
                border: '1.5px solid #9F1239',
                color: '#9F1239',
              }}
            >
              {user?.avatar}
            </div>
            {isExpanded && (
              <div className="flex flex-col min-w-0">
                <span className="text-xs font-bold text-slate-800 truncate">{user?.name}</span>
                <span className="text-[10px] text-slate-400 capitalize truncate">{user?.role}</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </aside>
  );
}
