// gradient = CSS gradient string e.g. 'linear-gradient(135deg,#9F1239,#4A7C59)'
// OR use iconBg / iconColor for white card style
export default function StatCard({ title, value, subtitle, icon: Icon, gradient, iconBg, iconColor, trend, trendLabel }) {
  const isPos = trend > 0;

  if (gradient) {
    return (
      <div className="rounded-2xl p-5 text-white" style={{ background: gradient, boxShadow: '0 4px 18px rgba(15,23,42,0.1)' }}>
        {Icon && (
          <div className="w-10 h-10 rounded-xl flex items-center justify-center mb-3" style={{ background: 'rgba(255,255,255,0.2)' }}>
            <Icon size={18} className="text-white" />
          </div>
        )}
        <p className="text-3xl font-bold leading-none">{value}</p>
        <p className="text-sm mt-1.5 font-medium" style={{ color: 'rgba(255,255,255,0.8)' }}>{title}</p>
        {subtitle && <p className="text-xs mt-0.5" style={{ color: 'rgba(255,255,255,0.6)' }}>{subtitle}</p>}
        {trend !== undefined && (
          <p className="text-xs font-semibold mt-2" style={{ color: 'rgba(255,255,255,0.85)' }}>
            {isPos ? '↑' : '↓'} {Math.abs(trend)}% {trendLabel}
          </p>
        )}
      </div>
    );
  }

  return (
    <div className="card-p">
      {Icon && (
        <div className={`w-10 h-10 ${iconBg || 'bg-rose-50'} rounded-xl flex items-center justify-center mb-3`}>
          <Icon size={18} className={iconColor || 'text-rose-600'} />
        </div>
      )}
      <p className="text-3xl font-bold text-slate-900 leading-none">{value}</p>
      <p className="text-sm text-slate-500 mt-1.5 font-medium">{title}</p>
      {subtitle && <p className="text-xs text-slate-400 mt-0.5">{subtitle}</p>}
      {trend !== undefined && (
        <p className={`text-xs font-semibold mt-2 ${isPos ? 'text-emerald-600' : 'text-rose-600'}`}>
          {isPos ? '↑' : '↓'} {Math.abs(trend)}% {trendLabel}
        </p>
      )}
    </div>
  );
}
