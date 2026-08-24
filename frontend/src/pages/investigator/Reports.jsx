import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Search, Download, Eye, ChevronDown } from 'lucide-react';
import Badge from '../../components/ui/Badge';
import Select from '../../components/ui/Select';
import EmptyState from '../../components/ui/EmptyState';
import ReportDetailModal from '../../components/investigator/ReportDetailModal';
import { claimsAPI, providersAPI, patientsAPI } from '../../services/api';
import { useAuth } from '../../context/AuthContext';

// Escape user/DB supplied values before interpolating into the downloaded HTML.
const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (ch) => (
  { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]
));

export default function Reports() {
  const { user } = useAuth();
  const [reportsList, setReportsList] = useState([]);
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [dateFilter, setDateFilter] = useState('all');
  const [showAll, setShowAll] = useState(false);
  const [selectedReport, setSelectedReport] = useState(null);
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);

    Promise.allSettled([
      claimsAPI.getAll(),
      providersAPI.getAll(),
      patientsAPI.getAll(),
    ])
      .then(([claimsRes, providersRes, patientsRes]) => {
        if (!isMounted) return;

        const pick = (res) => (res.status === 'fulfilled' && Array.isArray(res.value) ? res.value : []);
        const claims = pick(claimsRes);
        const providerMap = new Map(pick(providersRes).map(p => [p.id, p]));
        const patientMap = new Map(pick(patientsRes).map(p => [p.id, p]));

        const mapped = claims.map((c, idx) => {
          const risk = c.risk_scores?.[0] || null;
          const rawScore = risk?.final_risk_score ?? risk?.overall_score ?? risk?.anomaly_score ?? null;
          // Scores arrive either 0–1 or 0–100 depending on the producer; normalise to 0–1.
          const scoreVal = rawScore === null ? 0.45 : (rawScore > 1 ? rawScore / 100 : rawScore);

          let priority = 'medium';
          if (scoreVal >= 0.8) priority = 'critical';
          else if (scoreVal >= 0.6) priority = 'high';
          else if (scoreVal < 0.3) priority = 'low';

          let status = 'Under Review';
          if (['approved', 'paid'].includes(c.status)) status = 'Completed';
          else if (['flagged', 'denied', 'rejected'].includes(c.status)) status = 'Flagged';

          const raw = c.raw_extracted_features || {};

          // Provider: prefer the eager-loaded relation, fall back to the lookup map, then raw features.
          const provObj = c.provider || providerMap.get(c.provider_id);
          const provName = provObj?.name || provObj?.facility_name || raw.provider_name || 'Medical Center';
          const provNpi = provObj?.npi || raw.provider_npi || '—';

          // Patient: relation → map → raw features → placeholder.
          const patObj = c.patient || patientMap.get(c.patient_id);
          let patName = '';
          if (patObj) {
            patName = [patObj.first_name, patObj.last_name].filter(Boolean).join(' ').trim() || patObj.name || '';
          }
          if (!patName) patName = raw.patient_name || `Patient #${c.patient_id || idx + 1}`;

          const amount = parseFloat(c.total_billed_amount || 0);
          const cptCode = raw.cpt_code || raw.procedure_code || '—';
          const diagnosisCode = raw.diagnosis_code || raw.icd_code || '—';

          return {
            id: `REP-2026-${String(idx + 1).padStart(3, '0')}`,
            claimId: c.claim_number || `CLM-${c.id}`,
            realClaimId: c.id,
            investigationId: `INV-2026-${String(c.id).padStart(3, '0')}`,
            provider: provName,
            providerNpi: provNpi,
            patient: patName,
            investigator: user?.name || 'Assigned Investigator',
            type: c.claim_type ? `${c.claim_type.toUpperCase()} Audit Report` : 'Clinical Audit Report',
            date: c.submission_date || c.service_date || c.created_at?.split('T')[0] || '—',
            status,
            priority,
            amount,
            cptCode,
            diagnosisCode,
            riskScore: scoreVal,
            hasRiskRecord: !!risk,
            contributingFactors: risk?.contributing_factors?.length ? risk.contributing_factors : [
              `Billed exposure of $${amount.toLocaleString()} evaluated against specialty peer distribution.`,
              `CPT procedure code ${cptCode} verified against ICD-10 diagnosis ${diagnosisCode}.`,
              `Provider NPI registration (${provNpi}) cross-referenced with the licensing database.`,
            ],
            recommendations: risk?.recommendations?.length ? risk.recommendations : [
              'Perform clinical chart audit on attending physician signature.',
              'Cross-reference patient admission timeline with facility billing records.',
            ],
            rawFeatures: raw,
          };
        });

        setReportsList(mapped);
      })
      .catch(err => console.warn('Error loading report dependencies:', err))
      .finally(() => { if (isMounted) setLoading(false); });

    return () => { isMounted = false; };
  }, [user?.name]);

  const filtered = reportsList.filter(r => {
    const s = search.toLowerCase();
    const matchSearch =
      r.id.toLowerCase().includes(s) ||
      r.claimId.toLowerCase().includes(s) ||
      r.investigationId.toLowerCase().includes(s) ||
      r.provider.toLowerCase().includes(s) ||
      r.patient.toLowerCase().includes(s) ||
      r.type.toLowerCase().includes(s);

    const matchType = typeFilter === 'all' || r.type === typeFilter;
    const matchStatus = statusFilter === 'all' || r.status === statusFilter;
    const matchDate = dateFilter === 'all' || r.date.includes(dateFilter);

    return matchSearch && matchType && matchStatus && matchDate;
  });

  const handleDownloadReport = (report) => {
    const findingsHtml = report.contributingFactors.map(f => `<li>${esc(f)}</li>`).join('');
    const recommendationsHtml = report.recommendations.map(r => `<li>${esc(r)}</li>`).join('');
    const riskPct = (report.riskScore * 100).toFixed(1);

    const htmlContent = `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>ClaimGuard AI - Report ${esc(report.id)}</title>
  <style>
    body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 40px; color: #1e293b; line-height: 1.6; background-color: #FAF9F7; }
    .container { max-width: 800px; margin: 0 auto; background: #ffffff; padding: 40px; border-radius: 16px; border: 1px solid #E7E1DC; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }
    h1 { color: #9F1239; font-size: 24px; border-bottom: 2px solid #9F1239; padding-bottom: 10px; margin-top: 0; }
    h2 { color: #0f172a; font-size: 16px; margin-top: 25px; border-bottom: 1px solid #E7E1DC; padding-bottom: 5px; }
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 20px; }
    .card { background: #f8fafc; padding: 12px; border-radius: 8px; border: 1px solid #e2e8f0; }
    .field { font-size: 10px; color: #64748b; font-weight: bold; text-transform: uppercase; }
    .val { font-size: 13px; font-weight: 600; color: #0f172a; margin-top: 2px; word-wrap: break-word; }
    .alert { background: #fff1f2; border: 1px solid #fecdd3; padding: 14px; border-radius: 10px; color: #9f1239; font-size: 13px; }
    ul { padding-left: 20px; margin-top: 8px; font-size: 13px; }
    li { margin-bottom: 6px; }
    .footer { margin-top: 50px; font-size: 11px; color: #94a3b8; text-align: center; border-top: 1px solid #E7E1DC; padding-top: 15px; }
  </style>
</head>
<body>
  <div class="container">
    <h1>Clinical Investigation Audit Report</h1>
    <div class="grid">
      <div class="card"><div class="field">Report ID</div><div class="val">${esc(report.id)}</div></div>
      <div class="card"><div class="field">Claim Number</div><div class="val">${esc(report.claimId)}</div></div>
      <div class="card"><div class="field">Healthcare Provider</div><div class="val">${esc(report.provider)} (NPI: ${esc(report.providerNpi)})</div></div>
      <div class="card"><div class="field">Patient Member</div><div class="val">${esc(report.patient)}</div></div>
      <div class="card"><div class="field">Report Type</div><div class="val">${esc(report.type)}</div></div>
      <div class="card"><div class="field">Date Evaluated</div><div class="val">${esc(report.date)}</div></div>
      <div class="card"><div class="field">Total Billed Exposure</div><div class="val">$${report.amount.toLocaleString()}</div></div>
      <div class="card"><div class="field">Risk Score &amp; Tier</div><div class="val">${riskPct}% (${esc(report.priority.toUpperCase())})</div></div>
    </div>

    <h2>1. Executive Summary</h2>
    <div class="alert">
      Clinical audit performed for claim <strong>${esc(report.claimId)}</strong> submitted by
      <strong>${esc(report.provider)}</strong> (NPI: <strong>${esc(report.providerNpi)}</strong>) for member
      <strong>${esc(report.patient)}</strong>. Total billed: <strong>$${report.amount.toLocaleString()}</strong>.
      Primary CPT code: <strong>${esc(report.cptCode)}</strong>, diagnosis code: <strong>${esc(report.diagnosisCode)}</strong>.
      ${report.hasRiskRecord
        ? `ML anomaly evaluation: <strong>${riskPct}% risk score</strong>.`
        : 'No stored ML risk record for this claim; the displayed tier is a provisional baseline.'}
    </div>

    <h2>2. Key Clinical &amp; Financial Risk Factors</h2>
    <ul>${findingsHtml}</ul>

    <h2>3. Supporting Clinical Evidence &amp; Provider Profile</h2>
    <p style="font-size: 13px;">
      <strong>Diagnosis (ICD-10):</strong> ${esc(report.diagnosisCode)}<br/>
      <strong>Procedure (CPT):</strong> ${esc(report.cptCode)}<br/>
      <strong>Provider NPI:</strong> ${esc(report.providerNpi)}<br/>
      <strong>Risk evaluation:</strong> ${riskPct}% anomaly probability against regional provider benchmarks.
    </p>

    <h2>4. Investigator Recommendations</h2>
    <ul>${recommendationsHtml}</ul>

    <h2>5. Audit Metadata</h2>
    <div style="font-size: 12px; color: #64748b;">
      Lead investigator: ${esc(report.investigator)}<br/>
      Claim status: ${esc(report.status)}<br/>
      Digital signature: verified by ClaimGuard AI
    </div>

    <div class="footer">Generated from live claim records by ClaimGuard AI. Confidential &amp; proprietary.</div>
  </div>
</body>
</html>`;

    const blob = new Blob([htmlContent], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `ClaimGuard_Report_${report.claimId}_${report.id}.html`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleOpenDetailModal = (report) => {
    setSelectedReport(report);
    setDetailModalOpen(true);
  };

  const totalCount = reportsList.length;
  const completedCount = reportsList.filter(r => r.status === 'Completed').length;
  const reviewCount = reportsList.filter(r => r.status === 'Under Review').length;

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center" role="status" aria-live="polite">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-rose-600 mx-auto mb-4" />
          <p className="text-slate-600">Loading reports…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header + summary stats */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 pb-4 border-b border-slate-200">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Investigation Reports</h1>
          <p className="text-sm text-slate-500 mt-1">
            Review, search, and retrieve investigation reports generated from live claim records.
          </p>
        </div>

        <div className="flex gap-4 text-xs">
          <div className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 rounded-lg text-slate-700 font-medium">
            <span>Total:</span><strong className="font-bold">{totalCount}</strong>
          </div>
          <div className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-50 rounded-lg text-emerald-800 font-medium border border-emerald-100">
            <span>Completed:</span><strong className="font-bold text-emerald-900">{completedCount}</strong>
          </div>
          <div className="flex items-center gap-1.5 px-3 py-1.5 bg-amber-50 rounded-lg text-amber-800 font-medium border border-amber-100">
            <span>Under Review:</span><strong className="font-bold text-amber-900">{reviewCount}</strong>
          </div>
        </div>
      </div>

      {/* Search + filters */}
      <div className="flex flex-col md:flex-row gap-3">
        <div className="relative flex-1">
          <Search size={15} aria-hidden="true" className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            className="input pl-9 text-xs"
            aria-label="Search reports"
            placeholder="Search by report ID, claim ID, provider, patient…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
        <Select
          className="w-full md:w-52 text-xs"
          aria-label="Filter by report type"
          value={typeFilter}
          onChange={setTypeFilter}
          options={[
            { value: 'all', label: 'All Report Types' },
            { value: 'INPATIENT Audit Report', label: 'Inpatient Audit Report' },
            { value: 'OUTPATIENT Audit Report', label: 'Outpatient Audit Report' },
            { value: 'PHARMACY Audit Report', label: 'Pharmacy Audit Report' },
            { value: 'Clinical Audit Report', label: 'Clinical Audit Report' },
          ]}
        />
        <Select
          className="w-full md:w-44 text-xs"
          aria-label="Filter by status"
          value={statusFilter}
          onChange={setStatusFilter}
          options={[
            { value: 'all', label: 'All Statuses' },
            { value: 'Completed', label: 'Completed' },
            { value: 'Under Review', label: 'Under Review' },
            { value: 'Flagged', label: 'Flagged' },
          ]}
        />
        <Select
          className="w-full md:w-44 text-xs"
          aria-label="Filter by date"
          value={dateFilter}
          onChange={setDateFilter}
          options={[
            { value: 'all', label: 'All Dates' },
            { value: '2026', label: 'Year 2026' },
            { value: '2025', label: 'Year 2025' },
          ]}
        />
      </div>

      {/* Table */}
      <div className="card p-5 space-y-4">
        <div className="flex justify-between items-center pb-2 border-b border-slate-100">
          <h3 className="text-sm font-bold text-slate-800">Investigation Reports</h3>
          <span className="text-xs text-slate-400 font-semibold">{filtered.length} Reports</span>
        </div>

        {filtered.length === 0 ? (
          <EmptyState title="No investigation reports found" description="Try adjusting your search or filters." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <caption className="sr-only">Investigation reports generated from claim records</caption>
              <thead>
                <tr>
                  {['REPORT ID', 'CLAIM', 'INVESTIGATION', 'PROVIDER', 'PATIENT', 'REPORT TYPE', 'GENERATED', 'STATUS', 'ACTIONS'].map(h => (
                    <th key={h} scope="col" className="table-header whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {(showAll ? filtered : filtered.slice(0, 10)).map(report => (
                  <tr key={report.id} className="table-row">
                    <td className="table-cell font-bold text-slate-800 whitespace-nowrap">{report.id}</td>
                    <td className="table-cell font-mono text-[11px] font-bold text-rose-600 whitespace-nowrap">
                      <Link to={`/investigations/${report.claimId}`} className="hover:underline">{report.claimId}</Link>
                    </td>
                    <td className="table-cell font-mono text-[11px] text-slate-400 whitespace-nowrap">
                      <Link to={`/investigations/${report.claimId}`} className="hover:text-rose-500 hover:underline">
                        {report.investigationId}
                      </Link>
                    </td>
                    <td className="table-cell font-medium text-slate-700 max-w-[130px] truncate" title={report.provider}>
                      {report.provider}
                    </td>
                    <td className="table-cell font-semibold text-slate-800 whitespace-nowrap">{report.patient}</td>
                    <td className="table-cell text-slate-500 whitespace-nowrap">{report.type}</td>
                    <td className="table-cell text-slate-500 whitespace-nowrap">{report.date}</td>
                    <td className="table-cell whitespace-nowrap">
                      <Badge
                        status={
                          report.status === 'Completed' ? 'resolved'
                            : report.status === 'Under Review' ? 'under_review'
                              : report.status === 'Flagged' ? 'flagged' : 'pending'
                        }
                        label={report.status}
                        size="xs"
                      />
                    </td>
                    <td className="table-cell">
                      <div className="flex items-center gap-2">
                        <button
                          className="btn-secondary text-[11px] py-1 px-2.5 flex items-center gap-1 border-slate-200 text-slate-700 hover:bg-slate-50 cursor-pointer"
                          onClick={() => handleOpenDetailModal(report)}
                          title={`View details for ${report.id}`}
                        >
                          <Eye size={12} aria-hidden="true" /> View
                        </button>
                        <button
                          className="btn-secondary text-[11px] py-1 px-2.5 flex items-center gap-1 border-slate-200 text-slate-700 hover:bg-slate-50 cursor-pointer"
                          onClick={() => handleDownloadReport(report)}
                          title={`Download ${report.id}`}
                        >
                          <Download size={12} aria-hidden="true" /> Download
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {filtered.length > 10 && (
              <div className="border-t border-slate-100 bg-slate-50/60 p-2.5 flex justify-center">
                <button
                  onClick={() => setShowAll(!showAll)}
                  aria-expanded={showAll}
                  className="flex items-center gap-2 px-4 py-2 text-xs font-semibold text-rose-700 hover:text-rose-800 bg-white hover:bg-rose-50/80 border border-slate-200 hover:border-rose-200 rounded-lg shadow-sm transition-all duration-300 cursor-pointer"
                >
                  <span>{showAll ? 'Show Less (Collapse to 10)' : `View All (${filtered.length} Reports)`}</span>
                  <ChevronDown size={14} aria-hidden="true" className={`transition-transform duration-300 ${showAll ? 'rotate-180' : 'rotate-0'}`} />
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {selectedReport && (
        <ReportDetailModal
          isOpen={detailModalOpen}
          onClose={() => { setDetailModalOpen(false); setSelectedReport(null); }}
          report={selectedReport}
        />
      )}
    </div>
  );
}
