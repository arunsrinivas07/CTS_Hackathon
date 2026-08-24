import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Eye, EyeOff, Loader2, Zap } from 'lucide-react';

const roleRedirect = { provider: '/provider', investigator: '/investigator', admin: '/admin' };

const slides = [
  {
    title: 'Detect Fraud. Protect Claims.',
    sub: 'AI-powered claims intelligence with real-time fraud scoring and automated investigation workflows.',
  },
  {
    title: 'Investigate Smarter.',
    sub: 'Built-in Copilot helps investigators resolve cases 3x faster with evidence-driven insights.',
  },
  {
    title: 'Full Visibility. Zero Surprises.',
    sub: 'Executive dashboards, provider risk matrices, and live alerts — everything in one place.',
  },
];

const demos = [
  { role: 'Provider',     email: 'user@gmail.com',   color: '#7c2d3e' },
  { role: 'Investigator', email: 'ram@investigator', color: '#78350f' },
  { role: 'Admin',        email: 'ravi@admin',        color: '#3d6b4a' },
];

export default function Login() {
  const { login, loading, error, setError } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail]       = useState('');
  const [password, setPassword] = useState('');
  const [remember, setRemember] = useState(false);
  const [showPw, setShowPw]     = useState(false);
  const [slide, setSlide]       = useState(0);

  const handleSubmit = async e => {
    e.preventDefault();
    if (!email || !password) { setError('Please enter your email and password.'); return; }
    const r = await login(email, password, remember);
    if (r.success) navigate(roleRedirect[r.role] || '/');
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4"
      style={{ background: 'linear-gradient(135deg,#e8d5c8 0%,#f5ede8 40%,#e8e0f0 100%)' }}>

      {/* Card wrapper */}
      <div className="w-full max-w-4xl flex rounded-3xl overflow-hidden shadow-2xl"
        style={{ minHeight: 560, boxShadow: '0 32px 80px rgba(60,20,20,0.25)' }}>

        {/* ── LEFT: White form panel ─────────────────────────── */}
        <div className="w-full lg:w-[45%] bg-white flex flex-col px-10 py-10">

          {/* Logo */}
          <div className="flex items-center gap-2.5 mb-10">
            <span className="font-bold text-stone-900 text-base tracking-tight">ClaimGuard AI</span>
          </div>

          {/* Heading */}
          <h1 className="text-3xl font-black text-stone-900 leading-tight mb-1">
            Welcome Back!
          </h1>
          <p className="text-sm text-stone-400 mb-8">Please enter your login details below</p>

          {/* Error */}
          {error && (
            <div className="px-4 py-2.5 rounded-xl text-sm font-medium mb-4"
              style={{ background: '#fef2f2', border: '1px solid #fecaca', color: '#9f1239' }}>
              {error}
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4 flex-1">
            {/* Email */}
            <div className="relative">
              <input
                type="text"
                placeholder=" "
                id="email"
                value={email}
                onChange={e => { setEmail(e.target.value); setError(''); }}
                autoComplete="email"
                className="w-full px-4 pt-5 pb-2.5 text-sm text-stone-900 bg-white rounded-xl border peer transition-all focus:outline-none"
                style={{ border: '1.5px solid #e7dad4' }}
                onFocus={e => { e.currentTarget.style.border = '1.5px solid #7c2d3e'; e.currentTarget.style.boxShadow = '0 0 0 3px rgba(124,45,62,0.1)'; }}
                onBlur={e => { e.currentTarget.style.border = '1.5px solid #e7dad4'; e.currentTarget.style.boxShadow = ''; }}
              />
              <label htmlFor="email"
                className="absolute text-xs font-semibold left-4 top-2 transition-all pointer-events-none"
                style={{ color: '#a8765a' }}>
                Email
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
                autoComplete="current-password"
                className="w-full px-4 pt-5 pb-2.5 pr-11 text-sm text-stone-900 bg-white rounded-xl border peer transition-all focus:outline-none"
                style={{ border: '1.5px solid #e7dad4' }}
                onFocus={e => { e.currentTarget.style.border = '1.5px solid #7c2d3e'; e.currentTarget.style.boxShadow = '0 0 0 3px rgba(124,45,62,0.1)'; }}
                onBlur={e => { e.currentTarget.style.border = '1.5px solid #e7dad4'; e.currentTarget.style.boxShadow = ''; }}
              />
              <label htmlFor="password"
                className="absolute text-xs font-semibold left-4 top-2 pointer-events-none"
                style={{ color: '#a8765a' }}>
                Password
              </label>
              <button type="button" onClick={() => setShowPw(v => !v)}
                className="absolute right-3.5 top-1/2 -translate-y-1/2"
                style={{ color: '#c4a088' }}>
                {showPw ? <EyeOff size={15} /> : <Eye size={15} />}
              </button>
            </div>

            {/* Forgot */}
            <div className="flex justify-end">
              <button type="button" className="text-sm font-semibold"
                style={{ color: '#a8765a' }}
                onMouseEnter={e => { e.currentTarget.style.color = '#7c2d3e'; }}
                onMouseLeave={e => { e.currentTarget.style.color = '#a8765a'; }}>
                Forget password?
              </button>
            </div>

            {/* Remember */}
            <label className="flex items-center gap-2 cursor-pointer select-none">
              <input type="checkbox" checked={remember} onChange={e => setRemember(e.target.checked)}
                className="w-4 h-4 rounded" style={{ accentColor: '#7c2d3e' }} />
              <span className="text-sm text-stone-500">Remember me</span>
            </label>

            {/* Sign in button */}
            <button type="submit" disabled={loading}
              className="w-full py-3.5 rounded-xl text-sm font-bold text-white transition-all disabled:opacity-60 cursor-pointer"
              style={{ background: '#1c1917', boxShadow: '0 4px 14px rgba(28,25,23,0.3)' }}
              onMouseEnter={e => { e.currentTarget.style.background = '#292524'; }}
              onMouseLeave={e => { e.currentTarget.style.background = '#1c1917'; }}>
              {loading
                ? <span className="flex items-center justify-center gap-2"><Loader2 size={15} className="animate-spin" /> Signing in…</span>
                : 'Sign in'
              }
            </button>

            {/* Create Account link */}
            <p className="text-center text-xs mt-4 text-stone-500">
              Don't have an account?{' '}
              <button type="button" onClick={() => navigate('/signup')} className="font-bold text-[#7c2d3e] hover:underline cursor-pointer">
                Create account
              </button>
            </p>
          </form>
        </div>

        {/* ── RIGHT: Dark panel ──────────────────────────────── */}
        <div className="hidden lg:flex flex-col flex-1 relative overflow-hidden"
          style={{ background: '#0f0a0a' }}>

          {/* Hex grid SVG background */}
          <svg className="absolute inset-0 w-full h-full opacity-20" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <pattern id="hex" x="0" y="0" width="60" height="52" patternUnits="userSpaceOnUse">
                <polygon points="30,2 58,17 58,47 30,62 2,47 2,17"
                  fill="none" stroke="#7c2d3e" strokeWidth="0.8" />
              </pattern>
            </defs>
            <rect width="100%" height="100%" fill="url(#hex)" />
          </svg>

          {/* Floating accent shapes */}
          <div className="absolute top-8 right-12 w-8 h-8 rotate-45 rounded-sm opacity-60"
            style={{ background: '#fcd34d' }} />
          <div className="absolute top-24 left-8 w-5 h-5 opacity-50"
            style={{ borderLeft: '10px solid transparent', borderRight: '10px solid transparent', borderBottom: `18px solid #4ade80` }} />
          <div className="absolute bottom-28 right-8 w-6 h-6 rounded-full opacity-40"
            style={{ border: '2px solid #7c2d3e' }} />

          {/* Center visual — stylised hexagon with 3D feel */}
          <div className="absolute inset-0 flex flex-col items-center justify-center px-8">
            {/* Glowing hex ring */}
            <div className="relative mb-6">
              <div className="absolute inset-0 rounded-full blur-3xl opacity-30"
                style={{ background: 'radial-gradient(circle,#9f1239,#78350f)' }} />
              <div className="relative w-52 h-52 flex items-center justify-center rounded-full"
                style={{ background: 'linear-gradient(135deg,rgba(124,45,62,0.3),rgba(120,53,15,0.2))', border: '1px solid rgba(124,45,62,0.4)' }}>
                {/* Inner hex */}
                <svg viewBox="0 0 120 140" className="absolute inset-0 w-full h-full opacity-30">
                  <polygon points="60,5 115,35 115,105 60,135 5,105 5,35"
                    fill="none" stroke="url(#hgrad)" strokeWidth="1.5" />
                  <defs>
                    <linearGradient id="hgrad" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor="#9f1239" />
                      <stop offset="100%" stopColor="#d97706" />
                    </linearGradient>
                  </defs>
                </svg>

                {/* Centrepiece indicator */}
                <div className="relative z-10 flex flex-col items-center">
                  <div className="flex gap-1 mt-2">
                    {[0, 1, 2].map(i => (
                      <div key={i} className="w-2 h-2 rounded-full" style={{ background: i === 0 ? '#9f1239' : 'rgba(255,255,255,0.2)' }} />
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* Slide text */}
            <div className="text-center max-w-xs transition-all duration-500">
              <h3 className="text-xl font-bold text-white mb-2 leading-snug">
                {slides[slide].title}
              </h3>
              <p className="text-sm leading-relaxed" style={{ color: 'rgba(232,191,189,0.65)' }}>
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
                    background: i === slide ? '#9f1239' : 'rgba(255,255,255,0.2)',
                  }} />
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
