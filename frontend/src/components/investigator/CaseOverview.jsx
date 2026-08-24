import React from 'react';
import { useInvestigation } from '../../context/InvestigationContext';
import { FileText, Briefcase, AlertTriangle } from 'lucide-react';
import Badge from '../ui/Badge';

export default function CaseOverview() {
  const { 
    claimData, 
    investigationData, 
    findingsData,
    activeClaimId,
    activeInvestigationId
  } = useInvestigation();

  const providerName = claimData?.provider?.name || claimData?.raw_extracted_features?.provider_id || 'Medical Center';
  const patientName = claimData?.patient?.name || claimData?.raw_extracted_features?.patient_name || `Patient #${claimData?.patient_id || 'Unknown'}`;
  const claimType = claimData?.claim_type ? claimData.claim_type.toUpperCase() : 'OUTPATIENT';
  const amount = claimData?.total_billed_amount || claimData?.raw_extracted_features?.clm_tot_chrg_amt || 0;
  
  const status = investigationData?.status || 'Open';
  const priority = investigationData?.priority || 'High';
  const riskScore = findingsData?.overall_score || 0;
  const leieOverride = findingsData?.leie_override || false;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="card p-5 lg:col-span-2 space-y-4">
          <h3 className="section-title border-b pb-2 flex items-center gap-1.5">
            <FileText size={16} className="text-rose-500" />
            Claim Information
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
            <div>
              <span className="text-xs text-slate-400 block mb-0.5">Claim ID</span>
              <span className="text-sm font-semibold text-slate-800">{activeClaimId}</span>
            </div>
            <div>
              <span className="text-xs text-slate-400 block mb-0.5">Investigation ID</span>
              <span className="text-sm font-semibold text-slate-800">{activeInvestigationId || 'Pending'}</span>
            </div>
            <div>
              <span className="text-xs text-slate-400 block mb-0.5">Provider</span>
              <span className="text-sm font-semibold text-slate-800">{providerName}</span>
            </div>
            <div>
              <span className="text-xs text-slate-400 block mb-0.5">Patient Member</span>
              <span className="text-sm font-semibold text-slate-800">{patientName}</span>
            </div>
            <div>
              <span className="text-xs text-slate-400 block mb-0.5">Claim Type</span>
              <span className="text-sm font-semibold text-slate-800">{claimType}</span>
            </div>
            <div>
              <span className="text-xs text-slate-400 block mb-0.5">Claim Amount</span>
              <span className="text-sm font-semibold text-slate-800">${Number(amount).toLocaleString()}</span>
            </div>
            <div>
              <span className="text-xs text-slate-400 block mb-0.5">Current Status</span>
              <Badge status={status} />
            </div>
            <div>
              <span className="text-xs text-slate-400 block mb-0.5">Priority Level</span>
              <Badge status={priority} />
            </div>
          </div>
        </div>

        <div className="card p-5 space-y-4">
          <h3 className="section-title border-b pb-2 flex items-center gap-1.5">
            <Briefcase size={16} className="text-rose-500" />
            Risk Summary
          </h3>
          
          {leieOverride && (
             <div className="bg-red-50 border border-red-200 text-red-800 p-3 rounded-lg text-sm mb-4">
                <strong>LEIE EXCLUSION DETECTED:</strong> Provider appears on an active exclusion record. Payment should be blocked. Final risk score overridden to Critical.
             </div>
          )}

          <div className="grid grid-cols-2 gap-3 text-center">
            <div className="p-3 bg-slate-50 border rounded-xl">
              <span className="text-2xl font-bold text-slate-800">{riskScore} / 100</span>
              <span className="text-[10px] text-slate-400 block uppercase font-bold mt-1">Hybrid Risk</span>
            </div>
            <div className="p-3 bg-rose-50 border border-rose-100 rounded-xl">
              <span className="text-lg font-bold text-rose-700 capitalize">{priority}</span>
              <span className="text-[10px] text-rose-600 block uppercase font-bold mt-1">Risk Tier</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
