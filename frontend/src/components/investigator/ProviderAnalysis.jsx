import React from 'react';
import { useInvestigation } from '../../context/InvestigationContext';

export default function ProviderAnalysis() {
  const { claimData } = useInvestigation();

  const provider = claimData?.provider || {};
  const rawFeat = claimData?.raw_extracted_features || {};

  const name = provider.name || provider.facility_name || rawFeat.provider_id || 'Medical Center';
  const npi = provider.npi || rawFeat.provider_id || 'Unknown';
  const totalClaims = provider.total_claims || 142;
  const flaggedClaims = provider.flagged_claims_count || 18;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="card p-5 lg:col-span-1 space-y-4">
          <h3 className="section-title border-b pb-2">Provider Profile</h3>
          <div className="space-y-3 text-xs">
            <div>
              <span className="text-slate-400 block mb-0.5">Provider Name</span>
              <span className="font-semibold text-slate-800">{name}</span>
            </div>
            <div>
              <span className="text-slate-400 block mb-0.5">NPI</span>
              <span className="font-semibold text-slate-800">{npi}</span>
            </div>
            <div>
              <span className="text-slate-400 block mb-0.5">Location</span>
              <span className="font-semibold text-slate-800">{provider.state || rawFeat.state || 'Unknown'}</span>
            </div>
          </div>
        </div>

        <div className="card p-5 lg:col-span-2 space-y-4">
          <h3 className="section-title border-b pb-2">Historical Claims (Simulated)</h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
            <div className="p-3 bg-slate-50 border rounded-xl">
              <span className="text-xl font-bold text-slate-800">{totalClaims}</span>
              <span className="text-[10px] text-slate-400 block uppercase font-bold mt-1">Total Claims</span>
            </div>
            <div className="p-3 bg-emerald-50 border border-emerald-100 rounded-xl">
              <span className="text-xl font-bold text-emerald-700">{totalClaims - flaggedClaims}</span>
              <span className="text-[10px] text-emerald-600 block uppercase font-bold mt-1">Approved</span>
            </div>
            <div className="p-3 bg-amber-50 border border-amber-100 rounded-xl">
              <span className="text-xl font-bold text-amber-700">{flaggedClaims}</span>
              <span className="text-[10px] text-amber-600 block uppercase font-bold mt-1">Flagged</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
