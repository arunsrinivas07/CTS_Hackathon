import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Eye, EyeOff, Loader2, Shield } from 'lucide-react';

import { useAuth } from '../context/AuthContext';

const slides = [
  {
    title: 'Detect Fraud. Protect Claims.',
    sub: 'AI-powered claims intelligence with real-time fraud scoring and automated investigation workflows.',
  },
  {
    title: 'Investigate Smarter.',
    sub: 'Built-in AI Copilot helps investigators resolve cases 3x faster with evidence-driven insights.',
  },
  {
    title: 'Full Visibility. Zero Surprises.',
    sub: 'Executive dashboards, provider risk matrices, and live alerts — everything in one place.',
  },
];

export default function Signup() {
  const { signup } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [org, setOrg] = useState('');
  const [role, setRole] = useState('provider');

  const [showPw, setShowPw] = useState(false);
  const [slide, setSlide] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const handleSubmit = async e => {
    e.preventDefault();
    if (!name || !email || !password || !confirmPassword) {
      setError('Please fill in all required fields.');
      return;
    }
    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }
    setLoading(true);
    setError('');

    const res = await signup({ name, email, password, role });
    setLoading(false);

    if (!res.success) {
      setError(res.error || 'Failed to create account.');
      return;
    }

    setSuccess(true);
    setTimeout(() => {
      navigate('/login');
    }, 1200);
  };


  return (
    <div className="min-h-screen flex items-center justify-center p-4"
      style={{ background: 'linear-gradient(135deg, #FDF1F3 0%, #FAF9F7 40%, #E7E1DC 100%)' }}>

      {/* Card wrapper */}
      <div className="w-full max-w-4xl flex rounded-3xl overflow-hidden shadow-2xl bg-white"
        style={{ minHeight: 620, boxShadow: '0 32px 80px rgba(15,23,42,0.15)' }}>

        {/* ── LEFT: White form panel ─────────────────────────── */}
        <div className="w-full lg:w-[50%] bg-white flex flex-col px-10 py-10 overflow-y-auto max-h-[90vh]">

          {/* Logo */}
          <div className="flex items-center gap-2.5 mb-6">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center text-white bg-rose-600 shadow-md">
              <Shield size={18} />
            </div>
            <span className="font-bold text-slate-900 text-sm tracking-tight">ClaimGuard AI</span>
          </div>

          {/* Heading */}
          <h1 className="text-3xl font-black text-slate-900 leading-tight mb-1">
            Create Account
          </h1>
          <p className="text-sm text-slate-400 mb-6">Join ClaimGuard AI healthcare platform</p>

          {/* Success / Error */}
          {error && (
            <div className="px-4 py-2.5 rounded-xl text-sm font-medium mb-4 bg-red-50 border border-red-200 text-rose-600">
              {error}
            </div>
          )}
          {success && (
            <div className="px-4 py-2.5 rounded-xl text-sm font-medium mb-4 bg-emerald-50 border border-emerald-200 text-emerald-600">
              Account created successfully! Redirecting to login...
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4 flex-1">
            {/* Full Name */}
            <div className="relative">
              <input
                type="text"
                placeholder=" "
                id="name"
                value={name}
                onChange={e => { setName(e.target.value); setError(''); }}
                className="w-full px-4 pt-5 pb-2.5 text-sm text-slate-900 bg-white rounded-xl border border-slate-200 transition-all focus:outline-none focus:border-rose-600 focus:ring-4 focus:ring-rose-100"
              />
              <label htmlFor="name" className="absolute text-xs font-semibold left-4 top-2 text-slate-400 pointer-events-none">
                Full Name
              </label>
            </div>

            {/* Email */}
            <div className="relative">
              <input
                type="email"
                placeholder=" "
                id="email"
                value={email}
                onChange={e => { setEmail(e.target.value); setError(''); }}
                className="w-full px-4 pt-5 pb-2.5 text-sm text-slate-900 bg-white rounded-xl border border-slate-200 transition-all focus:outline-none focus:border-rose-600 focus:ring-4 focus:ring-rose-100"
              />
              <label htmlFor="email" className="absolute text-xs font-semibold left-4 top-2 text-slate-400 pointer-events-none">
                Email Address
              </label>
            </div>

            {/* Password */}
            <div className="relative">
              <input
                type={showPw ? 'text' : 'password'}
                placeholder=" "
                id="password"
                value={password}
                onChange={e => { setPassword(e.target.value); setError(''); }}
                className="w-full px-4 pt-5 pb-2.5 pr-11 text-sm text-slate-900 bg-white rounded-xl border border-slate-200 transition-all focus:outline-none focus:border-rose-600 focus:ring-4 focus:ring-rose-100"
              />
              <label htmlFor="password" className="absolute text-xs font-semibold left-4 top-2 text-slate-400 pointer-events-none">
                Password
              </label>
              <button type="button" onClick={() => setShowPw(v => !v)} className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400">
                {showPw ? <EyeOff size={15} /> : <Eye size={15} />}
              </button>
            </div>

            {/* Confirm Password */}
            <div className="relative">
              <input
                type={showPw ? 'text' : 'password'}
                placeholder=" "
                id="confirmPassword"
                value={confirmPassword}
                onChange={e => { setConfirmPassword(e.target.value); setError(''); }}
                className="w-full px-4 pt-5 pb-2.5 pr-11 text-sm text-slate-900 bg-white rounded-xl border border-slate-200 transition-all focus:outline-none focus:border-rose-600 focus:ring-4 focus:ring-rose-100"
              />
              <label htmlFor="confirmPassword" className="absolute text-xs font-semibold left-4 top-2 text-slate-400 pointer-events-none">
                Confirm Password
              </label>
            </div>

            {/* Organization */}
            <div className="relative">
              <input
                type="text"
                placeholder=" "
                id="org"
                value={org}
                onChange={e => { setOrg(e.target.value); setError(''); }}
                className="w-full px-4 pt-5 pb-2.5 text-sm text-slate-900 bg-white rounded-xl border border-slate-200 transition-all focus:outline-none focus:border-rose-600 focus:ring-4 focus:ring-rose-100"
              />
              <label htmlFor="org" className="absolute text-xs font-semibold left-4 top-2 text-slate-400 pointer-events-none">
                Organization / Hospital
              </label>
            </div>

            {/* Role selection */}
            <div>
              <label className="label">Access Role</label>
              <select
                value={role}
                onChange={e => setRole(e.target.value)}
                className="select"
              >
                <option value="provider">Provider</option>
                <option value="investigator">Investigator</option>
                <option value="admin">Admin</option>
              </select>
            </div>

            {/* Create Account button */}
            <button type="submit" disabled={loading}
              className="w-full py-3.5 rounded-xl text-sm font-bold text-white bg-rose-600 hover:bg-rose-700 transition-all disabled:opacity-60 cursor-pointer shadow-md shadow-rose-200">
              {loading
                ? <span className="flex items-center justify-center gap-2"><Loader2 size={15} className="animate-spin" /> Creating Account…</span>
                : 'Create Account'
              }
            </button>

            <p className="text-center text-xs mt-4 text-slate-400">
              Already have an account?{' '}
              <button type="button" onClick={() => navigate('/login')} className="font-bold text-rose-600 hover:underline">
                Sign in
              </button>
            </p>
          </form>
        </div>

        {/* ── RIGHT: Medical/Healthcare Dark panel ──────────────────────────────── */}
        <div className="hidden lg:flex flex-col flex-1 relative overflow-hidden bg-slate-900"
          style={{ background: 'linear-gradient(135deg, #1e3a8a, #0f172a)' }}>

          {/* Hex grid SVG background */}
          <svg className="absolute inset-0 w-full h-full opacity-10" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <pattern id="hex" x="0" y="0" width="60" height="52" patternUnits="userSpaceOnUse">
                <polygon points="30,2 58,17 58,47 30,62 2,47 2,17"
                  fill="none" stroke="#9F1239" strokeWidth="0.8" />
              </pattern>
            </defs>
            <rect width="100%" height="100%" fill="url(#hex)" />
          </svg>

          {/* Floating accent shapes */}
          <div className="absolute top-8 right-12 w-8 h-8 rotate-45 rounded-sm opacity-20 bg-amber-400" />
          <div className="absolute top-24 left-8 w-5 h-5 opacity-20"
            style={{ borderLeft: '10px solid transparent', borderRight: '10px solid transparent', borderBottom: `18px solid #10b981` }} />
          <div className="absolute bottom-28 right-8 w-6 h-6 rounded-full opacity-20"
            style={{ border: '2px solid #9F1239' }} />

          {/* Center visual — stylised hexagon with 3D feel */}
          <div className="absolute inset-0 flex flex-col items-center justify-center px-8">
            {/* Glowing hex ring */}
            <div className="relative mb-6">
              <div className="absolute inset-0 rounded-full blur-3xl opacity-20 bg-radial from-rose-600 to-green-500" />
              <div className="relative w-52 h-52 flex items-center justify-center rounded-full border border-rose-500/20 bg-rose-500/5">
                {/* Inner hex */}
                <svg viewBox="0 0 120 140" className="absolute inset-0 w-full h-full opacity-30">
                  <polygon points="60,5 115,35 115,105 60,135 5,105 5,35"
                    fill="none" stroke="url(#hgrad)" strokeWidth="1.5" />
                  <defs>
                    <linearGradient id="hgrad" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor="#9F1239" />
                      <stop offset="100%" stopColor="#4A7C59" />
                    </linearGradient>
                  </defs>
                </svg>

                {/* Shield icon */}
                <div className="relative z-10 flex flex-col items-center">
                  <div className="w-20 h-20 rounded-2xl flex items-center justify-center mb-2 bg-gradient-to-br from-rose-600 to-green-500 shadow-lg shadow-rose-500/40">
                    <Shield size={40} className="text-white" />
                  </div>
                  <div className="flex gap-1">
                    {[0, 1, 2].map(i => (
                      <div key={i} className="w-2 h-2 rounded-full" style={{ background: i === 0 ? '#9F1239' : 'rgba(255,255,255,0.2)' }} />
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* Slide text */}
            <div className="text-center max-w-xs">
              <h3 className="text-xl font-bold text-white mb-2 leading-snug">
                {slides[slide].title}
              </h3>
              <p className="text-sm leading-relaxed text-rose-200/60">
                {slides[slide].sub}
              </p>
            </div>

            {/* Slide dots */}
            <div className="flex gap-2 mt-6">
              {slides.map((_, i) => (
                <button key={i} onClick={() => setSlide(i)}
                  className="rounded-full transition-all duration-300"
                  style={{
                    width: i === slide ? 24 : 8,
                    height: 8,
                    background: i === slide ? '#9F1239' : 'rgba(255,255,255,0.2)',
                  }} />
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
