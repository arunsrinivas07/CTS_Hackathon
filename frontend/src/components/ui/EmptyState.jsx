import { Inbox } from 'lucide-react';
export default function EmptyState({ icon: Icon = Inbox, title = 'No data found', description, action }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="w-14 h-14 rounded-2xl flex items-center justify-center mb-4"
        style={{ background: '#fdf5f0' }}>
        <Icon size={24} style={{ color: '#c4a088' }} />
      </div>
      <p className="text-sm font-bold text-stone-700">{title}</p>
      {description && <p className="text-sm text-stone-400 mt-1 max-w-xs">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
