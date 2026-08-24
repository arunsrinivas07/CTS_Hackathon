import React from 'react';
import { useInvestigation } from '../../context/InvestigationContext';
import { CheckCircle, Clock, AlertTriangle, Play, FastForward, SkipForward } from 'lucide-react';
import Badge from '../ui/Badge';

export default function AgenticTraceTimeline() {
  const { 
    traceData, 
    isLoading, 
    investigationData,
    startInvestigation, 
    runInvestigation, 
    activeInvestigationId,
    activeClaimId,
    claimData
  } = useInvestigation();

  const handleStart = async () => {
    if (!activeClaimId) return;
    await startInvestigation({
      claim_id: activeClaimId,
      claim_data: claimData,
      risk_score: 75, // fallback if claimData doesn't have it
      risk_level: "High",
      auto_run: false
    });
  };

  if (!activeInvestigationId && !isLoading) {
    return (
      <div className="card p-6 text-center space-y-4">
        <h3 className="section-title">Agentic Investigation</h3>
        <p className="text-sm text-slate-500">No investigation has been started for this claim.</p>
        <button className="btn-primary mx-auto" onClick={handleStart}>
          <Play size={16} /> Start Investigation
        </button>
      </div>
    );
  }

  const steps = traceData?.steps || [];
  const status = investigationData?.status || 'UNKNOWN';

  return (
    <div className="card p-5 space-y-4">
      <div className="flex justify-between items-center border-b pb-3">
        <h3 className="section-title">AI Investigation Activity</h3>
        <div className="flex gap-2">
           <Badge status={status} />
           {status !== 'COMPLETED' && status !== 'REQUIRES_HUMAN_REVIEW' && (
             <button 
               className="btn-secondary text-xs py-1" 
               onClick={runInvestigation}
               disabled={isLoading}
             >
               <FastForward size={14} /> {isLoading ? 'Running...' : 'Run Investigation'}
             </button>
           )}
        </div>
      </div>

      <div className="space-y-4 relative before:absolute before:inset-0 before:ml-5 before:-translate-x-px md:before:ml-6 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-slate-200 before:to-transparent">
        {steps.length === 0 && (
           <div className="text-sm text-slate-500 text-center py-4">Waiting to run...</div>
        )}
        {steps.map((step, idx) => {
          let Icon = Clock;
          let iconColor = 'text-slate-400 bg-slate-100';
          if (step.status === 'COMPLETED') {
            Icon = CheckCircle;
            iconColor = 'text-emerald-500 bg-emerald-50';
          } else if (step.status === 'FAILED') {
            Icon = AlertTriangle;
            iconColor = 'text-red-500 bg-red-50';
          } else if (step.status === 'REQUIRES_HUMAN_REVIEW') {
            Icon = AlertTriangle;
            iconColor = 'text-amber-500 bg-amber-50';
          } else if (step.status === 'RUNNING') {
            Icon = Clock;
            iconColor = 'text-blue-500 bg-blue-50';
          }

          return (
            <div key={idx} className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active">
              <div className="flex items-center justify-center w-10 h-10 rounded-full border-2 border-white shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 shadow-sm z-10">
                <div className={`flex items-center justify-center w-full h-full rounded-full ${iconColor}`}>
                  <Icon size={16} />
                </div>
              </div>
              <div className="w-[calc(100%-4rem)] md:w-[calc(50%-2.5rem)] p-4 rounded-xl border border-slate-100 bg-white shadow-sm">
                <div className="flex items-center justify-between mb-1">
                  <div className="font-bold text-slate-800 text-sm">{step.name || `Step ${idx + 1}`}</div>
                  <time className="text-xs font-mono text-slate-400">{step.timestamp || new Date().toLocaleTimeString()}</time>
                </div>
                <div className="text-xs text-slate-600">{step.description || step.action}</div>
                {step.findings && (
                  <div className="mt-2 text-xs bg-slate-50 p-2 rounded border border-slate-100 text-slate-700">
                    {step.findings}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
      
      {isLoading && (
        <div className="text-center py-4 text-sm text-slate-500 flex items-center justify-center gap-2">
          <Clock size={16} className="animate-spin text-blue-500" /> AI Investigation Running...
        </div>
      )}
    </div>
  );
}
