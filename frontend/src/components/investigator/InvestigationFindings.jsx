import React from 'react';
import { useInvestigation } from '../../context/InvestigationContext';
import Badge from '../ui/Badge';

export default function InvestigationFindings() {
  const { investigationData, findingsData } = useInvestigation();

  if (!findingsData && !investigationData?.findings) {
    return (
      <div className="card p-8 text-center text-slate-500">
        <h3 className="section-title mb-2">No Findings Available</h3>
        <p>The AI Agent has not yet generated findings for this investigation. Run the investigation to see findings.</p>
      </div>
    );
  }

  const findings = findingsData || investigationData?.findings || {};
  const evidenceGaps = findings.evidence_gaps || [];

  return (
    <div className="space-y-6">
      <div className="card p-5 space-y-4">
        <h3 className="section-title border-b pb-2">Investigation Findings</h3>
        <div className="bg-slate-50 p-4 rounded-xl border text-sm text-slate-700 whitespace-pre-wrap">
          {findings.summary || findings.explanation || 'No summary available.'}
        </div>
      </div>

      <div className="card p-5 space-y-4">
        <h3 className="section-title border-b pb-2">Evidence Gaps</h3>
        {evidenceGaps.length === 0 ? (
          <p className="text-sm text-emerald-600">No evidence gaps identified.</p>
        ) : (
          <ul className="space-y-3">
            {evidenceGaps.map((gap, idx) => (
              <li key={idx} className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-800">
                <strong>Missing:</strong> {typeof gap === 'string' ? gap : gap.description || JSON.stringify(gap)}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
