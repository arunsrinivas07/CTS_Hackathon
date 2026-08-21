const grads = [
  'linear-gradient(135deg,#7c2d3e,#9f1239)',
  'linear-gradient(135deg,#78350f,#92400e)',
  'linear-gradient(135deg,#3d6b4a,#4a7c59)',
  'linear-gradient(135deg,#b45309,#d97706)',
  'linear-gradient(135deg,#44403c,#57534e)',
];
export default function Avatar({ initials, size = 'md', colorIndex = 0 }) {
  const bg = grads[colorIndex % grads.length];
  const sz = size === 'sm' ? 'w-7 h-7 text-xs' : size === 'lg' ? 'w-11 h-11 text-sm' : 'w-9 h-9 text-xs';
  return (
    <div className={`${sz} rounded-full flex items-center justify-center font-bold text-white flex-shrink-0`}
      style={{ background: bg }}>
      {initials}
    </div>
  );
}
