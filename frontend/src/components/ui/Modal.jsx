import { useEffect } from 'react';
import { X } from 'lucide-react';

export default function Modal({ isOpen, onClose, title, children, size = 'md' }) {
  useEffect(() => {
    document.body.style.overflow = isOpen ? 'hidden' : '';
    return () => { document.body.style.overflow = ''; };
  }, [isOpen]);

  if (!isOpen) return null;
  const sizes = { sm: 'max-w-md', md: 'max-w-lg', lg: 'max-w-2xl', xl: 'max-w-4xl' };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 backdrop-blur-sm" style={{ background: 'rgba(28,25,23,0.4)' }} onClick={onClose} />
      <div className={`relative bg-white rounded-2xl w-full ${sizes[size]} max-h-[90vh] flex flex-col`}
        style={{ boxShadow: '0 20px 60px rgba(120,53,15,0.2)', border: '1px solid #f0e6e0' }}>
        <div className="flex items-center justify-between px-6 py-4" style={{ borderBottom: '1px solid #faf5f2' }}>
          <h2 className="text-base font-bold text-stone-900">{title}</h2>
          <button onClick={onClose}
            className="w-8 h-8 flex items-center justify-center rounded-xl transition-colors"
            style={{ color: '#a8765a' }}
            onMouseEnter={e => { e.currentTarget.style.background = '#fdf5f0'; }}
            onMouseLeave={e => { e.currentTarget.style.background = ''; }}>
            <X size={15} />
          </button>
        </div>
        <div className="overflow-y-auto flex-1 px-6 py-5">{children}</div>
      </div>
    </div>
  );
}
