import React from 'react';
import Modal from '../ui/Modal';
import Badge from '../ui/Badge';
import { FileText, ShieldAlert, AlertTriangle, User, Calendar, DollarSign, Award, CheckCircle } from 'lucide-react';

export default function ReportDetailModal({ isOpen, onClose, report }) {
  if (!report) return null;

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={`Investigation Report - ${report.id}`} size="lg">
      <div className="space-y-6 max-h-[75vh] overflow-y-auto pr-2 text-slate-800 text-xs leading-relaxed">
        {/* Header Metadata block */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 bg-slate-50 p-4 border rounded-2xl">
          <div>
            <span className="text-[10px] text-slate-400 block font-bold uppercase">Report ID</span>
            <span className="font-semibold text-slate-800">{report.id}</span>
          </div>
          <div>
            <span className="text-[10px] text-slate-400 block font-bold uppercase">Claim ID</span>
            <span className="font-mono font-semibold text-rose-600">{report.claimId}</span>
          </div>
          <div>
            <span className="text-[10px] text-slate-400 block font-bold uppercase">Provider</span>
            <span className="font-semibold text-slate-800 truncate block">{report.provider}</span>
          </div>
          <div>
            <span className="text-[10px] text-slate-400 block font-bold uppercase">Patient</span>
            <span className="font-semibold text-slate-800">{report.patient}</span>
          </div>
        </div>

        {/* Compact Status Banner inside modal */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-rose-50/50 p-3.5 border border-rose-100 rounded-xl">
          <div>
            <span className="text-[9px] uppercase font-bold text-slate-400 block">Priority</span>
            <span className="font-bold text-rose-900 capitalize">{report.priority?.toUpperCase() || 'HIGH'}</span>
          </div>
          <div>
            <span className="text-[9px] uppercase font-bold text-slate-400 block">Status</span>
            <span className="font-bold text-rose-900">{report.status}</span>
          </div>
          <div>
            <span className="text-[9px] uppercase font-bold text-slate-400 block">Claim Amount</span>
            <span className="font-bold text-rose-900">${(report.amount || 48200).toLocaleString()}</span>
          </div>
          <div>
            <span className="text-[9px] uppercase font-bold text-slate-400 block">Investigator</span>
            <span className="font-bold text-rose-900">Sarah Mitchell</span>
          </div>
        </div>

        {/* 1. Investigation Summary */}
        <div className="space-y-2">
          <h4 className="font-bold text-slate-700 border-b pb-1 flex items-center gap-1.5">
            <FileText size={13} className="text-rose-500" />
            Investigation Summary
          </h4>
          <p className="text-slate-600 bg-slate-50 p-3 border rounded-xl leading-relaxed">
            This claim was reviewed because the submitted procedure charge was substantially higher than comparable claims and supporting documentation did not fully explain the billed amount. Conflicting admission timeline details were also identified during initial reviews.
          </p>
        </div>

        {/* 2. Key Findings (Compact Cards) */}
        <div className="space-y-2.5">
          <h4 className="font-bold text-slate-700 flex items-center gap-1.5">
            <AlertTriangle size={13} className="text-amber-500" />
            Key Findings
          </h4>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {[
              {
                title: 'High Procedure Charge',
                why: 'The submitted amount is substantially above the observed regional range.',
                evidence: 'Regional Billing Datasets (median benchmark: $380).'
              },
              {
                title: 'Documentation Gap',
                why: 'Required clinical documentation was not available to fully support the billed procedure.',
                evidence: 'Submitted Operative Report (DOC-003) missing surgeon credential logs.'
              },
              {
                title: 'Billing Pattern Concern',
                why: 'Similar billing activity was identified in the provider\'s historical claims.',
                evidence: '14 related claims in the historical database cluster.'
              }
            ].map(find => (
              <div key={find.title} className="p-3 bg-slate-50 border rounded-xl space-y-1">
                <span className="font-bold text-slate-800 block">{find.title}</span>
                <p className="text-slate-600 text-[11px] leading-snug">{find.why}</p>
                <p className="text-[10px] text-slate-400 mt-1"><strong>Evidence:</strong> {find.evidence}</p>
              </div>
            ))}
          </div>
        </div>

        {/* 3. Supporting Evidence & Provider Analysis */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="card p-4 space-y-2">
            <h4 className="font-bold text-slate-700 flex items-center gap-1.5">
              <CheckCircle size={13} className="text-green-600" />
              Supporting Evidence
            </h4>
            <p className="text-slate-600">Billed CPT code 80307 at $4,000 against regional median schedule benchmarks ($380). Admission logs verify clinical intake date inconsistencies.</p>
          </div>
          <div className="card p-4 space-y-2">
            <h4 className="font-bold text-slate-700 flex items-center gap-1.5">
              <Award size={13} className="text-rose-600" />
              Provider Analysis
            </h4>
            <p className="text-slate-600">Riverside Medical Center risk rating is flagged as High (risk index 72/100). The facility bills Urine Drug Screen codes at the 99.8th percentile regional volume.</p>
          </div>
        </div>

        {/* 4. Documents Reviewed */}
        <div className="space-y-2">
          <h4 className="font-bold text-slate-700 flex items-center gap-1.5">
            <FileText size={13} className="text-slate-500" />
            Documents Reviewed
          </h4>
          <ul className="list-disc pl-4 space-y-1 text-slate-600">
            <li>Claim Form UB-04 (Verified)</li>
            <li>Clinical Admission Log (Verified)</li>
            <li>Operative Notes Report (Flagged - incomplete credentials)</li>
          </ul>
        </div>

        {/* 5. Investigator Notes, Final Decision & Audit Information */}
        <div className="space-y-3 pt-2 border-t">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <span className="font-bold text-slate-700 block">Final Decision</span>
              <span className="text-xs bg-red-50 text-red-700 font-semibold px-2 py-0.5 rounded-full inline-block mt-1 border border-red-200">
                Confirm Suspicious (Reimbursement Hold)
              </span>
            </div>
            <div>
              <span className="font-bold text-slate-700 block">Investigator Notes</span>
              <p className="text-slate-600 italic mt-1">
                "Verified regional fee schedule outlier rates. Supplemental documents requested from provider to support procedure complexity."
              </p>
            </div>
          </div>

          <div className="pt-2 flex justify-between items-center text-[10px] text-slate-400">
            <span>Audit Information: Signed Digitally</span>
            <span>Completed on: {report.date} 15:42</span>
          </div>
        </div>
      </div>
    </Modal>
  );
}
