import React, { useEffect, useState } from 'react';
import { useInvestigation } from '../../context/InvestigationContext';
import { mlAPI } from '../../services/api';
import Badge from '../ui/Badge';

export default function Explainability() {
  const { claimData, investigationData } = useInvestigation();
  const [mlPrediction, setMlPrediction] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let isMounted = true;
    async function fetchLivePrediction() {
      if (!claimData) return;
      setLoading(true);
      try {
        const billed = claimData.total_billed_amount || 7500;
        const paid = claimData.total_paid_amount || billed * 0.4;
        
        const payload = {
          transaction_type: "MEDICAL_CLAIM",
          claim_id: claimData.claim_number || "CLM-2024",
          bene_id: String(claimData.patient_id || "PAT-4421"),
          provider_id: String(claimData.provider?.npi || "1578657367"),
          claim_type: (claimData.claim_type || "outpatient").toLowerCase().replace(" ", "_"),
          claim_start_date: claimData.service_date || "2023-03-10",
          clm_pmt_amt: paid,
          clm_tot_chrg_amt: billed,
          line_count: 1,
          diag_count: 1,
          proc_count: 1,
          state: claimData?.provider?.state || "OH"
        };
        const res = await mlAPI.predictHybrid(payload);
        if (isMounted) setMlPrediction(res);
      } catch (e) {
        console.warn('Explainability fetch error:', e);
      } finally {
        if (isMounted) setLoading(false);
      }
    }
    fetchLivePrediction();
    return () => { isMounted = false; };
  }, [claimData]);

  if (loading) {
    return <div className="p-10 text-center text-slate-500">Running Explainable AI Models...</div>;
  }

  if (!mlPrediction) {
    return <div className="p-10 text-center text-slate-500">No ML data available for this claim.</div>;
  }

  const scoreVal = Math.round(mlPrediction.final_risk_score * 100);
  const computedPriority = mlPrediction.final_risk_tier || 'Medium';

  return (
    <div className="space-y-6">
      <div className="card p-5 bg-gradient-to-r from-slate-900 to-rose-950 text-white rounded-2xl shadow-lg border border-rose-900/40">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <span className="text-xs uppercase tracking-wider text-rose-300 font-bold">Hybrid V2 ML Engine</span>
            <h4 className="text-xl font-bold text-white mt-0.5">Live Fraud Risk Assessment</h4>
            <p className="text-xs text-rose-200 mt-1">Adaptive Ensemble (Model B + Model V2 + LEIE Gatekeeper)</p>
          </div>
          <div className="flex items-center gap-4 flex-wrap">
            <div className="text-center px-4 py-2 bg-slate-800/80 rounded-xl border border-rose-900/40">
              <span className="text-[10px] text-slate-400 block uppercase font-bold">Model B (Claim)</span>
              <span className="text-lg font-mono font-bold text-rose-300">
                {Math.round((mlPrediction.claim_score || 0) * 100)}%
              </span>
            </div>
            <div className="text-center px-4 py-2 bg-slate-800/80 rounded-xl border border-rose-900/40">
              <span className="text-[10px] text-slate-400 block uppercase font-bold">Model V2 (Provider)</span>
              <span className="text-lg font-mono font-bold text-amber-300">
                {Math.round((mlPrediction.provider_score || 0) * 100)}%
              </span>
            </div>
            <div className="text-center px-5 py-2.5 bg-rose-600 rounded-xl shadow-md border border-rose-400">
              <span className="text-[10px] text-rose-100 block uppercase font-bold">Hybrid Risk Score</span>
              <span className="text-2xl font-mono font-black text-white">{scoreVal} / 100</span>
            </div>
          </div>
        </div>
      </div>

      <div className="card p-5 space-y-4">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div>
            <h3 className="section-title">SHAP Explainable AI Feature Drivers</h3>
            <p className="text-xs text-slate-500 mt-0.5">Key risk indicators identified by the ML pipeline.</p>
          </div>
          {mlPrediction.leie_override && (
            <span className="text-xs font-bold px-3 py-1 bg-red-600 text-white rounded-full">
              ⚠️ LEIE Exclusion Mandate Triggered
            </span>
          )}
        </div>

        <div className="space-y-4 pt-2">
          {mlPrediction.claim_evidence && mlPrediction.claim_evidence.map((x, idx) => {
             const shapVal = x.shap_contribution ?? x.shap_value ?? 0;
             const isPositiveRisk = shapVal > 0;
             return (
               <div key={idx} className="p-4 rounded-xl border border-slate-100 bg-slate-50/50 space-y-2">
                 <div className="flex justify-between items-center flex-wrap gap-2">
                   <span className="text-xs font-mono font-bold text-slate-800">{x.feature || 'FEATURE'}</span>
                   <span className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full border ${isPositiveRisk ? 'bg-rose-50 text-rose-700 border-rose-200' : 'bg-emerald-50 text-emerald-700 border-emerald-200'}`}>
                     SHAP Impact: {shapVal >= 0 ? `+${shapVal.toFixed(4)}` : shapVal.toFixed(4)}
                   </span>
                 </div>
                 <p className="text-xs text-slate-600">Feature Value: {String(x.value ?? 'N/A')}</p>
               </div>
             );
          })}
        </div>
      </div>
    </div>
  );
}
