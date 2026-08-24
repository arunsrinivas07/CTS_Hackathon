export default function RiskMeter({ score }) {
  const bar =
    score >= 80 ? 'linear-gradient(90deg,#DC2626,#EF4444)' :
    score >= 60 ? 'linear-gradient(90deg,#F59E0B,#fbbf24)' :
    score >= 40 ? 'linear-gradient(90deg,#F59E0B,#fbbf24)' :
                  'linear-gradient(90deg,#4A7C59,#166534)';
  const txt =
    score >= 80 ? '#DC2626' :
    score >= 60 ? '#D97706' :
    score >= 40 ? '#D97706' :
                  '#4A7C59';
  return (
    <div className="flex items-center gap-2">
      <div className="w-20 h-2 rounded-full overflow-hidden" style={{ background: '#E7E1DC' }}>
        <div className="h-full rounded-full" style={{ width: `${score}%`, background: bar }} />
      </div>
      <span className="text-xs font-bold tabular-nums" style={{ color: txt }}>{score}</span>
    </div>
  );
}
