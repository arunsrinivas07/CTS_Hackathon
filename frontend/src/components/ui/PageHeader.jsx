export default function PageHeader({ title, subtitle, actions }) {
  return (
    <div className="flex items-start justify-between mb-6">
      <div>
        <h2 className="text-2xl font-bold text-stone-900 tracking-tight">{title}</h2>
        {subtitle && <p className="text-sm mt-0.5" style={{ color: '#a8765a' }}>{subtitle}</p>}
      </div>
      {actions && <div className="flex items-center gap-2 ml-4 flex-shrink-0">{actions}</div>}
    </div>
  );
}
