import { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import {
  User,
  Lock,
  Bell,
  Sliders,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  Save,
  Sparkles,
  KeyRound,
  Mail,
  Phone,
  ShieldAlert,
} from 'lucide-react';
import Select from '../components/ui/Select';

// Custom SaaS Toggle Switch Component
function ToggleSwitch({ checked, onChange, labelId }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-labelledby={labelId}
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-rose-500/30 focus:ring-offset-2 ${checked ? 'bg-rose-600' : 'bg-slate-200'
        }`}
    >
      <span
        className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-md ring-0 transition duration-200 ease-in-out ${checked ? 'translate-x-5' : 'translate-x-0'
          }`}
      />
    </button>
  );
}

export default function Settings() {
  const { user, updateProfile } = useAuth();
  const [activeTab, setActiveTab] = useState('profile');
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });

  // Profile form state
  const [profileData, setProfileData] = useState({
    fullName: user?.name || '',
    email: user?.email || '',
    phone: user?.phone || '',
  });

  // Security form state
  const [securityData, setSecurityData] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: '',
    twoFactor: false,
  });

  // Notification preferences
  const [notifications, setNotifications] = useState({
    emailAlerts: true,
    riskAlerts: true,
    caseAssignment: true,
  });

  // System config
  const [systemConfig, setSystemConfig] = useState({
    riskThreshold: 'medium',
    autoRunCopilot: false,
  });

  const tabs = [
    { id: 'profile', label: 'User Profile', icon: User },
    { id: 'security', label: 'Security & Auth', icon: ShieldCheck },
    { id: 'notifications', label: 'Notifications', icon: Bell },
    { id: 'system', label: 'System Config', icon: Sliders },
  ];

  const handleProfileSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setMessage({ type: '', text: '' });

    const result = await updateProfile({
      full_name: profileData.fullName,
      email: profileData.email,
    });

    setSaving(false);
    if (result?.success) {
      setMessage({ type: 'success', text: 'Profile updated successfully!' });
    } else {
      setMessage({ type: 'error', text: result?.error || 'Failed to update profile' });
    }
  };

  const handleSecuritySubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setMessage({ type: '', text: '' });

    if (securityData.newPassword && securityData.newPassword !== securityData.confirmPassword) {
      setMessage({ type: 'error', text: 'New passwords do not match' });
      setSaving(false);
      return;
    }

    setTimeout(() => {
      setSaving(false);
      setMessage({ type: 'success', text: 'Security settings updated successfully!' });
      setSecurityData({
        currentPassword: '',
        newPassword: '',
        confirmPassword: '',
        twoFactor: securityData.twoFactor,
      });
    }, 800);
  };

  const handleNotificationsSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setMessage({ type: '', text: '' });

    setTimeout(() => {
      setSaving(false);
      setMessage({ type: 'success', text: 'Notification preferences saved!' });
    }, 600);
  };

  const handleSystemSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setMessage({ type: '', text: '' });

    setTimeout(() => {
      setSaving(false);
      setMessage({ type: 'success', text: 'System configuration updated successfully!' });
    }, 600);
  };

  return (
    <div className="min-h-screen bg-slate-50/60 p-6 md:p-10">
      <div className="max-w-5xl mx-auto space-y-8">
        {/* Header Hero */}
        <div className="bg-white rounded-2xl p-6 md:p-8 shadow-sm border border-slate-200/80 flex flex-wrap items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="p-2 bg-rose-50 text-rose-600 rounded-xl font-bold">
                <Sliders size={20} />
              </span>
              <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Account Settings</h1>
            </div>
            <p className="text-sm text-slate-500 pl-11">
              Manage your profile preferences, security authentication, and automated AI configurations.
            </p>
          </div>

          {user && (
            <div className="flex items-center gap-3 bg-slate-50 border border-slate-200/80 rounded-2xl p-3 px-4">
              <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-rose-500 to-rose-600 text-white font-bold flex items-center justify-center text-sm shadow-sm">
                {(user.name || user.email || 'U').charAt(0).toUpperCase()}
              </div>
              <div>
                <p className="text-sm font-semibold text-slate-800 leading-tight">{user.name || 'User'}</p>
                <span className="text-[11px] font-bold text-rose-600 uppercase tracking-wider bg-rose-50 px-2 py-0.5 rounded-full inline-block mt-0.5">
                  {user.role || 'Investigator'}
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Tab Navigation Pill Bar */}
        <div className="bg-slate-200/60 p-1.5 rounded-2xl flex flex-wrap gap-1 border border-slate-200/60 shadow-inner">
          {tabs.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => {
                setActiveTab(id);
                setMessage({ type: '', text: '' });
              }}
              className={`flex-1 min-w-[140px] flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold transition-all duration-200 ${activeTab === id
                  ? 'bg-white text-rose-600 shadow-sm shadow-slate-200/80 font-bold'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100/50'
                }`}
            >
              <Icon size={16} className={activeTab === id ? 'text-rose-600' : 'text-slate-400'} />
              <span>{label}</span>
            </button>
          ))}
        </div>

        {/* Dismissible Feedback Message */}
        {message.text && (
          <div
            className={`p-4 rounded-2xl flex items-center gap-3 border transition-all animate-fadeIn ${message.type === 'success'
                ? 'bg-emerald-50 text-emerald-900 border-emerald-200'
                : 'bg-rose-50 text-rose-900 border-rose-200'
              }`}
          >
            {message.type === 'success' ? (
              <CheckCircle2 size={18} className="text-emerald-600 shrink-0" />
            ) : (
              <AlertCircle size={18} className="text-rose-600 shrink-0" />
            )}
            <p className="text-sm font-medium">{message.text}</p>
          </div>
        )}

        {/* Main Form Content Card */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-6 md:p-8">
          {/* TAB 1: User Profile */}
          {activeTab === 'profile' && (
            <form onSubmit={handleProfileSubmit} className="space-y-6">
              <div className="border-b border-slate-100 pb-4">
                <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                  <User size={18} className="text-rose-600" /> Personal Information
                </h2>
                <p className="text-xs text-slate-500 mt-1">Update your display name and contact email address.</p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-2">
                    Full Name
                  </label>
                  <div className="relative">
                    <input
                      type="text"
                      value={profileData.fullName}
                      onChange={(e) => setProfileData({ ...profileData, fullName: e.target.value })}
                      className="w-full px-4 py-2.5 bg-slate-50/50 border border-slate-200 rounded-xl text-slate-800 text-sm focus:bg-white focus:outline-none focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500 transition-all"
                      placeholder="e.g. Dr. Jane Doe"
                      required
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-2">
                    Email Address
                  </label>
                  <div className="relative">
                    <input
                      type="email"
                      value={profileData.email}
                      onChange={(e) => setProfileData({ ...profileData, email: e.target.value })}
                      className="w-full px-4 py-2.5 bg-slate-50/50 border border-slate-200 rounded-xl text-slate-800 text-sm focus:bg-white focus:outline-none focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500 transition-all"
                      placeholder="investigator@claimguard.ai"
                      required
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-2">
                    Phone Number (Optional)
                  </label>
                  <input
                    type="tel"
                    value={profileData.phone}
                    onChange={(e) => setProfileData({ ...profileData, phone: e.target.value })}
                    className="w-full px-4 py-2.5 bg-slate-50/50 border border-slate-200 rounded-xl text-slate-800 text-sm focus:bg-white focus:outline-none focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500 transition-all"
                    placeholder="+1 (555) 000-0000"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-2">
                    Assigned System Role
                  </label>
                  <input
                    type="text"
                    value={user?.role || 'Investigator'}
                    className="w-full px-4 py-2.5 bg-slate-100/70 border border-slate-200 rounded-xl text-slate-500 text-sm font-semibold capitalize cursor-not-allowed"
                    disabled
                  />
                </div>
              </div>

              <div className="pt-4 flex justify-end">
                <button
                  type="submit"
                  disabled={saving}
                  className="px-6 py-2.5 bg-gradient-to-r from-rose-600 to-rose-700 hover:from-rose-700 hover:to-rose-800 text-white font-semibold text-sm rounded-xl shadow-sm shadow-rose-200 active:scale-[0.99] disabled:opacity-50 transition-all flex items-center gap-2"
                >
                  <Save size={16} />
                  <span>{saving ? 'Saving Changes...' : 'Save Profile'}</span>
                </button>
              </div>
            </form>
          )}

          {/* TAB 2: Security & Auth */}
          {activeTab === 'security' && (
            <form onSubmit={handleSecuritySubmit} className="space-y-6">
              <div className="border-b border-slate-100 pb-4">
                <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                  <ShieldCheck size={18} className="text-rose-600" /> Security & Password Settings
                </h2>
                <p className="text-xs text-slate-500 mt-1">Manage password credentials and multi-factor authentication.</p>
              </div>

              <div className="space-y-4 max-w-xl">
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-2">
                    Current Password
                  </label>
                  <input
                    type="password"
                    value={securityData.currentPassword}
                    onChange={(e) => setSecurityData({ ...securityData, currentPassword: e.target.value })}
                    className="w-full px-4 py-2.5 bg-slate-50/50 border border-slate-200 rounded-xl text-slate-800 text-sm focus:bg-white focus:outline-none focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500 transition-all"
                    placeholder="Enter current password to verify"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-2">
                    New Password
                  </label>
                  <input
                    type="password"
                    value={securityData.newPassword}
                    onChange={(e) => setSecurityData({ ...securityData, newPassword: e.target.value })}
                    className="w-full px-4 py-2.5 bg-slate-50/50 border border-slate-200 rounded-xl text-slate-800 text-sm focus:bg-white focus:outline-none focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500 transition-all"
                    placeholder="Leave blank to keep current password"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-2">
                    Confirm New Password
                  </label>
                  <input
                    type="password"
                    value={securityData.confirmPassword}
                    onChange={(e) => setSecurityData({ ...securityData, confirmPassword: e.target.value })}
                    className="w-full px-4 py-2.5 bg-slate-50/50 border border-slate-200 rounded-xl text-slate-800 text-sm focus:bg-white focus:outline-none focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500 transition-all"
                    placeholder="Re-enter new password"
                  />
                </div>

                {/* 2FA Toggle Switch Card */}
                <div className="pt-2">
                  <div className="flex items-center justify-between p-4 bg-slate-50/80 border border-slate-200/80 rounded-2xl">
                    <div className="space-y-0.5">
                      <div className="text-sm font-semibold text-slate-900" id="2fa-label">
                        Two-Factor Authentication (2FA)
                      </div>
                      <div className="text-xs text-slate-500">
                        Require an authentication code when signing into your investigator portal account.
                      </div>
                    </div>
                    <ToggleSwitch
                      checked={securityData.twoFactor}
                      onChange={(val) => setSecurityData({ ...securityData, twoFactor: val })}
                      labelId="2fa-label"
                    />
                  </div>
                </div>
              </div>

              <div className="pt-4 flex justify-end">
                <button
                  type="submit"
                  disabled={saving}
                  className="px-6 py-2.5 bg-gradient-to-r from-rose-600 to-rose-700 hover:from-rose-700 hover:to-rose-800 text-white font-semibold text-sm rounded-xl shadow-sm shadow-rose-200 active:scale-[0.99] disabled:opacity-50 transition-all flex items-center gap-2"
                >
                  <KeyRound size={16} />
                  <span>{saving ? 'Updating...' : 'Update Security Settings'}</span>
                </button>
              </div>
            </form>
          )}

          {/* TAB 3: Notifications */}
          {activeTab === 'notifications' && (
            <form onSubmit={handleNotificationsSubmit} className="space-y-6">
              <div className="border-b border-slate-100 pb-4">
                <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                  <Bell size={18} className="text-rose-600" /> Notification Preferences
                </h2>
                <p className="text-xs text-slate-500 mt-1">Configure alerts for case assignments and high-risk ML triggers.</p>
              </div>

              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 bg-slate-50/80 border border-slate-200/80 rounded-2xl">
                  <div className="space-y-0.5">
                    <div className="text-sm font-semibold text-slate-900" id="email-alerts-label">
                      Email Notification Alerts
                    </div>
                    <div className="text-xs text-slate-500">
                      Send email summaries for critical updates and daily investigation reports.
                    </div>
                  </div>
                  <ToggleSwitch
                    checked={notifications.emailAlerts}
                    onChange={(val) => setNotifications({ ...notifications, emailAlerts: val })}
                    labelId="email-alerts-label"
                  />
                </div>

                <div className="flex items-center justify-between p-4 bg-slate-50/80 border border-slate-200/80 rounded-2xl">
                  <div className="space-y-0.5">
                    <div className="text-sm font-semibold text-slate-900" id="risk-alerts-label">
                      High-Risk ML Anomaly Triggers
                    </div>
                    <div className="text-xs text-slate-500">
                      Receive immediate notifications when claims exceed Critical (75+) hybrid risk score.
                    </div>
                  </div>
                  <ToggleSwitch
                    checked={notifications.riskAlerts}
                    onChange={(val) => setNotifications({ ...notifications, riskAlerts: val })}
                    labelId="risk-alerts-label"
                  />
                </div>

                <div className="flex items-center justify-between p-4 bg-slate-50/80 border border-slate-200/80 rounded-2xl">
                  <div className="space-y-0.5">
                    <div className="text-sm font-semibold text-slate-900" id="case-assignment-label">
                      Case Assignment Alerts
                    </div>
                    <div className="text-xs text-slate-500">
                      Notify me whenever a new claim or investigation workspace task is assigned.
                    </div>
                  </div>
                  <ToggleSwitch
                    checked={notifications.caseAssignment}
                    onChange={(val) => setNotifications({ ...notifications, caseAssignment: val })}
                    labelId="case-assignment-label"
                  />
                </div>
              </div>

              <div className="pt-4 flex justify-end">
                <button
                  type="submit"
                  disabled={saving}
                  className="px-6 py-2.5 bg-gradient-to-r from-rose-600 to-rose-700 hover:from-rose-700 hover:to-rose-800 text-white font-semibold text-sm rounded-xl shadow-sm shadow-rose-200 active:scale-[0.99] disabled:opacity-50 transition-all flex items-center gap-2"
                >
                  <Save size={16} />
                  <span>{saving ? 'Saving...' : 'Save Preferences'}</span>
                </button>
              </div>
            </form>
          )}

          {/* TAB 4: System Config */}
          {activeTab === 'system' && (
            <form onSubmit={handleSystemSubmit} className="space-y-6">
              <div className="border-b border-slate-100 pb-4">
                <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                  <Sliders size={18} className="text-rose-600" /> System & AI Engine Configuration
                </h2>
                <p className="text-xs text-slate-500 mt-1">Configure ML anomaly thresholds and automated Copilot investigation behavior.</p>
              </div>

              <div className="space-y-6 max-w-xl">
                <div>
                  <Select
                    label="ML Anomaly Risk Threshold"
                    value={systemConfig.riskThreshold}
                    onChange={(val) => setSystemConfig({ ...systemConfig, riskThreshold: val })}
                    options={[
                      { value: 'low', label: 'Low Threshold (Sensitive Detection)' },
                      { value: 'medium', label: 'Medium Threshold (Balanced Standard)' },
                      { value: 'high', label: 'High Threshold (Conservative Triggers)' },
                    ]}
                  />
                  <p className="text-xs text-slate-500 mt-1.5 pl-1">
                    Controls algorithmic sensitivity for flagging claims in the Investigation Queue.
                  </p>
                </div>

                <div className="flex items-center justify-between p-4 bg-slate-50/80 border border-slate-200/80 rounded-2xl">
                  <div className="space-y-0.5">
                    <div className="text-sm font-semibold text-slate-900 flex items-center gap-1.5" id="copilot-label">
                      <Sparkles size={16} className="text-rose-600" /> Auto-Run AI Copilot on New Cases
                    </div>
                    <div className="text-xs text-slate-500">
                      Automatically initiate full multi-agent evidence collection when a claim enters investigation queue.
                    </div>
                  </div>
                  <ToggleSwitch
                    checked={systemConfig.autoRunCopilot}
                    onChange={(val) => setSystemConfig({ ...systemConfig, autoRunCopilot: val })}
                    labelId="copilot-label"
                  />
                </div>
              </div>

              <div className="pt-4 flex justify-end">
                <button
                  type="submit"
                  disabled={saving}
                  className="px-6 py-2.5 bg-gradient-to-r from-rose-600 to-rose-700 hover:from-rose-700 hover:to-rose-800 text-white font-semibold text-sm rounded-xl shadow-sm shadow-rose-200 active:scale-[0.99] disabled:opacity-50 transition-all flex items-center gap-2"
                >
                  <Save size={16} />
                  <span>{saving ? 'Saving...' : 'Save Configuration'}</span>
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
