import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Search, FileText, Download, Eye } from 'lucide-react';
import PageHeader from '../../components/ui/PageHeader';
import Badge from '../../components/ui/Badge';
import EmptyState from '../../components/ui/EmptyState';
import ReportDetailModal from '../../components/investigator/ReportDetailModal';

// Mock reports list
const mockReports = [
  {
    id: 'REP-2024-001',
    claimId: 'CLM-2024-0081',
    investigationId: 'INV-2024-0041',
    provider: 'Riverside Medical Center',
    patient: 'James Thornton',
    type: 'Clinical Audit Report',
    date: 'Jul 16, 2024',
    status: 'Completed',
    priority: 'high',
    amount: 48200
  },
  {
    id: 'REP-2024-002',
    claimId: 'CLM-2024-0075',
    investigationId: 'INV-2024-0039',
    provider: 'Riverside Medical Center',
    patient: 'Alan Brooks',
    type: 'Upcoding Investigation Summary',
    date: 'Jul 05, 2024',
    status: 'Flagged',
    priority: 'critical',
    amount: 91750
  },
  {
    id: 'REP-2024-003',
    claimId: 'CLM-2024-0064',
    investigationId: 'INV-2024-0036',
    provider: 'Northside Neurological',
    patient: 'Patricia Wells',
    type: 'Outlier Cost Evaluation',
    date: 'Jun 15, 2024',
    status: 'Under Review',
    priority: 'medium',
    amount: 62100
  },
  {
    id: 'REP-2024-004',
    claimId: 'CLM-2024-0068',
    investigationId: 'INV-2024-0031',
    provider: 'Sunrise Health Clinic',
    patient: 'Robert Nguyen',
    type: 'Missing Documentation Review',
    date: 'Jun 22, 2024',
    status: 'Draft',
    priority: 'low',
    amount: 7890
  }
];

export default function Reports() {
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [dateFilter, setDateFilter] = useState('all');

  const [selectedReport, setSelectedReport] = useState(null);
  const [detailModalOpen, setDetailModalOpen] = useState(false);

  // Filters logic
  const filtered = mockReports.filter(r => {
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

  // Dynamic file downloader
  const handleDownloadReport = (report) => {
    const htmlContent = `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>ClaimGuard AI - Report ${report.id}</title>
  <style>
    body { font-family: Arial, sans-serif; padding: 40px; color: #1e293b; line-height: 1.6; background-color: #FAF9F7; }
    .container { max-width: 800px; margin: 0 auto; background: #ffffff; padding: 40px; border-radius: 16px; border: 1px solid #E7E1DC; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }
    h1 { color: #9F1239; font-size: 24px; border-bottom: 2px solid #9F1239; padding-bottom: 10px; margin-top: 0; }
    h2 { color: #0f172a; font-size: 16px; margin-top: 25px; border-bottom: 1px solid #E7E1DC; padding-bottom: 5px; }
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 20px; }
    .card { background: #f1f5f9; padding: 12px; border-radius: 8px; }
    .field { font-size: 10px; color: #64748b; font-weight: bold; text-transform: uppercase; }
    .val { font-size: 13px; font-weight: 600; color: #0f172a; margin-top: 2px; }
    .alert { background: #fef3c7; border: 1px solid #fde68a; padding: 14px; border-radius: 10px; color: #92400e; font-size: 13px; }
    .footer { margin-top: 50px; font-size: 11px; color: #94a3b8; text-align: center; border-top: 1px solid #E7E1DC; padding-top: 15px; }
  </style>
</head>
<body>
  <div class="container">
    <h1>Investigation Report Log</h1>
    <div class="grid">
      <div class="card"><div class="field">Report ID</div><div class="val">${report.id}</div></div>
      <div class="card"><div class="field">Claim ID</div><div class="val">${report.claimId}</div></div>
      <div class="card"><div class="field">Healthcare Provider</div><div class="val">${report.provider}</div></div>
      <div class="card"><div class="field">Patient Member</div><div class="val">${report.patient}</div></div>
      <div class="card"><div class="field">Report Type</div><div class="val">${report.type}</div></div>
      <div class="card"><div class="field">Date Generated</div><div class="val">${report.date}</div></div>
      <div class="card"><div class="field">Exposure Amount</div><div class="val">$${report.amount.toLocaleString()}</div></div>
      <div class="card"><div class="field">Urgency Level</div><div class="val">${report.priority.toUpperCase()}</div></div>
    </div>

    <h2>1. Executive Summary</h2>
    <div class="alert">
      Clinical audit of claim ${report.claimId} submitted by ${report.provider} for patient ${report.patient} indicates procedure CPT 80307 ($4,000) has an anomalous 11.1x fee scheduled regional benchmark variance ($380). Service date documentation conflicts with facility admission records.
    </div>

    <h2>2. Key Findings</h2>
    <ul>
      <li><strong>High Cost Outlier:</strong> Billed procedure CPT code lists $4,000 vs. peer average of $380.</li>
      <li><strong>Documentation Gap:</strong> Missing laboratory diagnostic logs to support billed complexity.</li>
      <li><strong>Timeline Conflict:</strong> Intake date logs report admission on July 10, whereas invoice states July 12.</li>
    </ul>

    <h2>3. Final Decision & Investigator Notes</h2>
    <p style="font-size: 13px;">
      <strong>Evidences Checked:</strong> Claim forms, medical records, provider history sheets.<br/>
      <strong>Notes:</strong> Based on clinical review, we verified the regional benchmark discrepancy and date timeline inconsistency. Pre-payment hold registered.
    </p>

    <h2>4. Audit Information</h2>
    <p style="font-size: 12px; color: #64748b;">
      Lead Investigator: Sarah Mitchell (Fraud Unit)<br/>
      Audit Signature Status: Signed Digitally
    </p>

    <div class="footer">Generated securely by ClaimGuard AI. Confidential & Proprietary.</div>
  </div>
</body>
</html>
    `;

    const blob = new Blob([htmlContent], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `ClaimGuard_Report_${report.id}.html`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleOpenDetailModal = (report) => {
    setSelectedReport(report);
    setDetailModalOpen(true);
  };

  // Stat summary counters
  const totalCount = mockReports.length;
  const completedCount = mockReports.filter(r => r.status === 'Completed').length;
  const reviewCount = mockReports.filter(r => r.status === 'Under Review').length;

  return (
    <div className="space-y-6">
      {/* 1. Page Header with Compact Summary Stats */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 pb-4 border-b border-slate-200">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Investigation Reports</h1>
          <p className="text-sm text-slate-500 mt-1">Review, search, and retrieve completed investigation reports.</p>
        </div>

        {/* Small Professional Stat Indicators */}
        <div className="flex gap-4 text-xs">
          <div className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 rounded-lg text-slate-700 font-medium">
            <span>Total:</span>
            <strong className="font-bold">{totalCount}</strong>
          </div>
          <div className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-50 rounded-lg text-emerald-800 font-medium border border-emerald-100">
            <span>Completed:</span>
            <strong className="font-bold text-emerald-900">{completedCount}</strong>
          </div>
          <div className="flex items-center gap-1.5 px-3 py-1.5 bg-amber-50 rounded-lg text-amber-800 font-medium border border-amber-100">
            <span>Under Review:</span>
            <strong className="font-bold text-amber-900">{reviewCount}</strong>
          </div>
        </div>
      </div>

      {/* 2. Search + Filter Toolbar */}
      <div className="flex flex-col md:flex-row gap-3">
        <div className="relative flex-1">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            className="input pl-9 text-xs"
            placeholder="Search by report ID, claim ID, provider, patient…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
        <select
          className="select w-full md:w-48 text-xs py-2"
          value={typeFilter}
          onChange={e => setTypeFilter(e.target.value)}
        >
          <option value="all">All Report Types</option>
          <option value="Clinical Audit Report">Clinical Audit Report</option>
          <option value="Upcoding Investigation Summary">Upcoding Investigation Summary</option>
          <option value="Outlier Cost Evaluation">Outlier Cost Evaluation</option>
          <option value="Missing Documentation Review">Missing Documentation Review</option>
        </select>
        <select
          className="select w-full md:w-40 text-xs py-2"
          value={statusFilter}
          onChange={e => setStatusFilter(e.target.value)}
        >
          <option value="all">All Statuses</option>
          <option value="Completed">Completed</option>
          <option value="Under Review">Under Review</option>
          <option value="Flagged">Flagged</option>
          <option value="Draft">Draft</option>
        </select>
        <select
          className="select w-full md:w-40 text-xs py-2"
          value={dateFilter}
          onChange={e => setDateFilter(e.target.value)}
        >
          <option value="all">All Dates</option>
          <option value="Jul">Jul 2024</option>
          <option value="Jun">Jun 2024</option>
        </select>
      </div>

      {/* 3. Main Reports Card */}
      <div className="card p-5 space-y-4">
        <div className="flex justify-between items-center pb-2 border-b border-slate-100">
          <h3 className="text-sm font-bold text-slate-800">Investigation Reports</h3>
          <span className="text-xs text-slate-400 font-semibold">{filtered.length} Reports</span>
        </div>

        {/* 4. Table Structure */}
        {filtered.length === 0 ? (
          <EmptyState
            title="No investigation reports found"
            description="Try adjusting your search or filters."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr>
                  {[
                    'REPORT ID',
                    'CLAIM',
                    'INVESTIGATION',
                    'PROVIDER',
                    'PATIENT',
                    'REPORT TYPE',
                    'GENERATED',
                    'STATUS',
                    'ACTIONS'
                  ].map(h => (
                    <th key={h} className="table-header whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filtered.map(report => (
                  <tr key={report.id} className="table-row">
                    {/* Bold Report ID */}
                    <td className="table-cell font-bold text-slate-850 whitespace-nowrap">{report.id}</td>

                    {/* Burgundy clickable claim link */}
                    <td className="table-cell font-mono text-[11px] font-bold text-rose-600 whitespace-nowrap">
                      <Link to={`/investigations/${report.claimId}`} className="hover:underline">
                        {report.claimId}
                      </Link>
                    </td>

                    {/* Subtle Secondary Investigation ID Link */}
                    <td className="table-cell font-mono text-[11px] text-slate-400 whitespace-nowrap">
                      <Link to={`/investigations/${report.claimId}`} className="hover:text-rose-500 hover:underline">
                        {report.investigationId}
                      </Link>
                    </td>

                    {/* Truncated Provider */}
                    <td className="table-cell font-medium text-slate-700 max-w-[130px] truncate" title={report.provider}>
                      {report.provider}
                    </td>

                    {/* Patient */}
                    <td className="table-cell font-semibold text-slate-800 whitespace-nowrap">{report.patient}</td>

                    {/* Report Type */}
                    <td className="table-cell text-slate-500 whitespace-nowrap">{report.type}</td>

                    {/* Generated Date */}
                    <td className="table-cell text-slate-500 whitespace-nowrap">{report.date}</td>

                    {/* Status Badge */}
                    <td className="table-cell">
                      <Badge
                        status={
                          report.status === 'Completed' ? 'resolved' :
                          report.status === 'Under Review' ? 'warning' :
                          report.status === 'Flagged' ? 'rejected' : 'pending'
                        }
                        label={report.status}
                        size="xs"
                      />
                    </td>

                    {/* Outlined Action Buttons */}
                    <td className="table-cell">
                      <div className="flex items-center gap-2">
                        <button
                          className="btn-secondary text-[11px] py-1 px-2.5 flex items-center gap-1 border-slate-200 text-slate-700 hover:bg-slate-50"
                          onClick={() => handleOpenDetailModal(report)}
                          title="View Details"
                        >
                          <Eye size={12} />
                          View
                        </button>
                        <button
                          className="btn-secondary text-[11px] py-1 px-2.5 flex items-center gap-1 border-slate-200 text-slate-700 hover:bg-slate-50"
                          onClick={() => handleDownloadReport(report)}
                          title="Download Report"
                        >
                          <Download size={12} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Details Modal */}
      {selectedReport && (
        <ReportDetailModal
          isOpen={detailModalOpen}
          onClose={() => {
            setDetailModalOpen(false);
            setSelectedReport(null);
          }}
          report={selectedReport}
        />
      )}
    </div>
  );
}
