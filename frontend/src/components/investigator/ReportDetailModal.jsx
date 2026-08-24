import Modal from '../ui/Modal';
import { FileText, AlertTriangle, Award, CheckCircle, ListChecks } from 'lucide-react';

const DECISION_STYLES = {
  Completed: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  Flagged: 'bg-red-50 text-red-700 border-red-200',
  'Under Review': 'bg-amber-50 text-amber-700 border-amber-200',
};

const DECISION_LABELS = {
  Completed: 'Claim Cleared (Payment Released)',
  Flagged: 'Confirmed Suspicious (Reimbursement Hold)',
  'Under Review': 'Pending Investigator Decision',
};

export default function ReportDetailModal({ isOpen, onClose, report }) {
  if (!report) return null;

  const factors = report.contributingFactors || [];
  const recommendations = report.recommendations || [];
  const riskPct = report.riskScore != null ? (report.riskScore * 100).toFixed(1) : null;
  const amount = Number(report.amount || 0);

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={`Investigation Report - ${report.id}`} size="lg">
      <div className="space-y-6 max-h-[75vh] overflow-y-auto pr-2 text-slate-800 text-xs leading-relaxed">

        {/* Identifiers */}
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
            <span className="font-semibold text-slate-800 block truncate" title={report.provider}>{report.provider}</span>
            <span className="text-[10px] text-slate-400">NPI: {report.providerNpi || '—'}</span>
          </div>
          <div>
            <span className="text-[10px] text-slate-400 block font-bold uppercase">Patient</span>
            <span className="font-semibold text-slate-800">{report.patient}</span>
          </div>
        </div>

        {/* Status strip */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-rose-50/50 p-3.5 border border-rose-100 rounded-xl">
          <div>
            <span className="text-[9px] uppercase font-bold text-slate-400 block">Priority</span>
            <span className="font-bold text-rose-900">{report.priority?.toUpperCase() || '—'}</span>
          </div>
          <div>
            <span className="text-[9px] uppercase font-bold text-slate-400 block">Status</span>
            <span className="font-bold text-rose-900">{report.status}</span>
          </div>
          <div>
            <span className="text-[9px] uppercase font-bold text-slate-400 block">Claim Amount</span>
            <span className="font-bold text-rose-900">${amount.toLocaleString()}</span>
          </div>
          <div>
            <span className="text-[9px] uppercase font-bold text-slate-400 block">Investigator</span>
            <span className="font-bold text-rose-900">{report.investigator || 'Unassigned'}</span>
          </div>
        </div>

        {/* Summary derived from the claim record */}
        <div className="space-y-2">
          <h4 className="font-bold text-slate-700 border-b pb-1 flex items-center gap-1.5">
            <FileText size={13} className="text-rose-500" aria-hidden="true" />
            Investigation Summary
          </h4>
          <p className="text-slate-600 bg-slate-50 p-3 border rounded-xl leading-relaxed">
            Claim <strong>{report.claimId}</strong> from <strong>{report.provider}</strong> for{' '}
            <strong>{report.patient}</strong> carries a billed exposure of{' '}
            <strong>${amount.toLocaleString()}</strong> under CPT <strong>{report.cptCode || '—'}</strong> and
            diagnosis <strong>{report.diagnosisCode || '—'}</strong>.{' '}
            {report.hasRiskRecord && riskPct
              ? <>The ML model scored this claim at <strong>{riskPct}%</strong> anomaly probability, placing it in the{' '}
                <strong>{report.priority?.toUpperCase()}</strong> tier.</>
              : <>No stored ML risk record exists for this claim, so the{' '}
                <strong>{report.priority?.toUpperCase()}</strong> tier shown is a provisional baseline pending scoring.</>}
          </p>
        </div>

        {/* Risk factors from risk_scores.contributing_factors */}
        <div className="space-y-2.5">
          <h4 className="font-bold text-slate-700 flex items-center gap-1.5">
            <AlertTriangle size={13} className="text-amber-500" aria-hidden="true" />
            Key Risk Factors
          </h4>
          {factors.length === 0 ? (
            <p className="text-slate-500 italic bg-slate-50 p-3 border rounded-xl">
              No risk factors recorded for this claim.
            </p>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {factors.map((factor, i) => {
                const isObj = factor && typeof factor === 'object';
                const title = isObj ? (factor.name || factor.feature || factor.title || `Factor ${i + 1}`) : `Factor ${i + 1}`;
                const detail = isObj ? (factor.description || factor.detail || factor.explanation || '') : String(factor);
                const weight = isObj ? (factor.contribution ?? factor.weight ?? factor.impact) : undefined;
                return (
                  <div key={`${title}-${i}`} className="p-3 bg-slate-50 border rounded-xl space-y-1">
                    <span className="font-bold text-slate-800 block">{title}</span>
                    {detail && <p className="text-slate-600 text-[11px] leading-snug">{detail}</p>}
                    {weight !== undefined && weight !== null && (
                      <p className="text-[10px] text-slate-400 mt-1"><strong>Contribution:</strong> {String(weight)}</p>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Coding evidence + provider context */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="card p-4 space-y-2">
            <h4 className="font-bold text-slate-700 flex items-center gap-1.5">
              <CheckCircle size={13} className="text-green-600" aria-hidden="true" />
              Coding &amp; Billing Evidence
            </h4>
            <dl className="space-y-1 text-slate-600">
              <div className="flex justify-between gap-2"><dt>Procedure (CPT)</dt><dd className="font-semibold font-mono">{report.cptCode || '—'}</dd></div>
              <div className="flex justify-between gap-2"><dt>Diagnosis (ICD-10)</dt><dd className="font-semibold font-mono">{report.diagnosisCode || '—'}</dd></div>
              <div className="flex justify-between gap-2"><dt>Billed amount</dt><dd className="font-semibold">${amount.toLocaleString()}</dd></div>
              <div className="flex justify-between gap-2"><dt>Report type</dt><dd className="font-semibold">{report.type}</dd></div>
            </dl>
          </div>
          <div className="card p-4 space-y-2">
            <h4 className="font-bold text-slate-700 flex items-center gap-1.5">
              <Award size={13} className="text-rose-600" aria-hidden="true" />
              Provider Profile
            </h4>
            <dl className="space-y-1 text-slate-600">
              <div className="flex justify-between gap-2"><dt>Facility</dt><dd className="font-semibold truncate max-w-[55%]" title={report.provider}>{report.provider}</dd></div>
              <div className="flex justify-between gap-2"><dt>NPI</dt><dd className="font-semibold font-mono">{report.providerNpi || '—'}</dd></div>
              <div className="flex justify-between gap-2"><dt>Risk tier</dt><dd className="font-semibold">{report.priority?.toUpperCase() || '—'}</dd></div>
              {riskPct && <div className="flex justify-between gap-2"><dt>Anomaly score</dt><dd className="font-semibold">{riskPct}%</dd></div>}
            </dl>
          </div>
        </div>

        {/* Recommendations from risk_scores.recommendations */}
        <div className="space-y-2">
          <h4 className="font-bold text-slate-700 flex items-center gap-1.5">
            <ListChecks size={13} className="text-slate-500" aria-hidden="true" />
            Investigator Recommendations
          </h4>
          {recommendations.length === 0 ? (
            <p className="text-slate-500 italic">No recommendations recorded.</p>
          ) : (
            <ul className="list-disc pl-4 space-y-1 text-slate-600">
              {recommendations.map((rec, i) => (
                <li key={i}>{typeof rec === 'object' ? (rec.description || rec.action || JSON.stringify(rec)) : rec}</li>
              ))}
            </ul>
          )}
        </div>

        {/* Current disposition, driven by claim status */}
        <div className="space-y-3 pt-2 border-t">
          <div>
            <span className="font-bold text-slate-700 block">Current Disposition</span>
            <span className={`text-xs font-semibold px-2 py-0.5 rounded-full inline-block mt-1 border ${DECISION_STYLES[report.status] || 'bg-slate-50 text-slate-700 border-slate-200'}`}>
              {DECISION_LABELS[report.status] || report.status}
            </span>
          </div>

          <div className="pt-2 flex justify-between items-center text-[10px] text-slate-400">
            <span>Generated from live claim records</span>
            <span>Record date: {report.date || '—'}</span>
          </div>
        </div>
      </div>
    </Modal>
  );
}
