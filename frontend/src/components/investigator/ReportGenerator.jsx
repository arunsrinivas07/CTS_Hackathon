import React, { useState, useEffect } from 'react';
import { reportsAPI } from '../../services/api';
import { FileText, Download, Plus, Clock, Eye } from 'lucide-react';
import Select from '../ui/Select';

export default function ReportGenerator({ investigationId, claimId }) {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showGenerateForm, setShowGenerateForm] = useState(false);
  const [generating, setGenerating] = useState(false);

  const [formData, setFormData] = useState({
    report_type: 'investigation_summary',
    title: '',
    format: 'pdf'
  });

  useEffect(() => {
    loadReports();
  }, []);

  const loadReports = async () => {
    try {
      setLoading(true);
      const data = await reportsAPI.getAll();
      // Filter by investigation or claim if provided
      let filtered = Array.isArray(data) ? data : [];
      if (investigationId) {
        filtered = filtered.filter(r => r.investigation_id === investigationId);
      } else if (claimId) {
        filtered = filtered.filter(r => r.claim_id === claimId);
      }
      setReports(filtered);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async (e) => {
    e.preventDefault();
    setGenerating(true);
    try {
      // For now, we'll create a placeholder report
      // In production, this would trigger backend report generation
      const reportData = {
        ...formData,
        investigation_id: investigationId,
        claim_id: claimId,
        status: 'generated',
        generated_at: new Date().toISOString()
      };

      // This would call the backend to generate the actual report
      alert('Report generation initiated. This would trigger backend PDF generation.');

      setShowGenerateForm(false);
      setFormData({
        report_type: 'investigation_summary',
        title: '',
        format: 'pdf'
      });
      // loadReports(); // Reload after generation
    } catch (err) {
      alert(`Failed to generate report: ${err.message}`);
    } finally {
      setGenerating(false);
    }
  };

  const handleDownload = (report) => {
    if (report.file_path) {
      window.open(report.file_path, '_blank');
    } else {
      alert('Report file not available. Generation may still be in progress.');
    }
  };

  const getReportTypeBadge = (type) => {
    const t = String(type || '').toLowerCase();
    if (t.includes('summary')) return 'bg-blue-100 text-blue-700';
    if (t.includes('finding')) return 'bg-purple-100 text-purple-700';
    if (t.includes('audit')) return 'bg-amber-100 text-amber-700';
    return 'bg-slate-100 text-slate-600';
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '—';
    try {
      return new Date(dateStr).toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return String(dateStr);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Clock size={20} className="animate-spin text-blue-500 mr-2" />
        <span className="text-sm text-slate-600">Loading reports...</span>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
      <div className="flex justify-between items-center mb-4 pb-3 border-b">
        <h3 className="text-base font-bold text-slate-800 flex items-center gap-2">
          <FileText size={16} className="text-slate-400" />
          Reports ({reports.length})
        </h3>
        <button
          onClick={() => setShowGenerateForm(!showGenerateForm)}
          className="btn-primary text-sm px-3 py-1.5 rounded-lg flex items-center gap-1"
        >
          <Plus size={14} />
          Generate Report
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
          <span className="text-sm text-red-700">{error}</span>
        </div>
      )}

      {showGenerateForm && (
        <form onSubmit={handleGenerate} className="bg-slate-50 rounded-lg p-4 mb-4 border border-slate-200">
          <h4 className="font-semibold text-sm text-slate-800 mb-3">Generate New Report</h4>

          <div className="grid grid-cols-2 gap-3 mb-3">
            <div>
              <Select
                label="Report Type"
                value={formData.report_type}
                onChange={(val) => setFormData({ ...formData, report_type: val })}
                options={[
                  { value: 'investigation_summary', label: 'Investigation Summary' },
                  { value: 'findings_report', label: 'Findings Report' },
                  { value: 'audit_trail', label: 'Audit Trail' },
                  { value: 'risk_assessment', label: 'Risk Assessment' },
                  { value: 'compliance_report', label: 'Compliance Report' },
                  { value: 'custom', label: 'Custom Report' },
                ]}
              />
            </div>
            <div>
              <Select
                label="Format"
                value={formData.format}
                onChange={(val) => setFormData({ ...formData, format: val })}
                options={[
                  { value: 'pdf', label: 'PDF' },
                  { value: 'docx', label: 'Word Document' },
                  { value: 'html', label: 'HTML' },
                ]}
              />
            </div>
          </div>

          <div className="mb-3">
            <label className="block text-xs font-medium text-slate-600 mb-1">Report Title</label>
            <input
              type="text"
              value={formData.title}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              className="w-full px-3 py-1.5 text-sm border border-slate-300 rounded-lg"
              placeholder="Optional custom title"
            />
          </div>

          <div className="flex gap-2">
            <button
              type="submit"
              className="btn-primary text-sm px-4 py-1.5 rounded-lg flex items-center gap-2"
              disabled={generating}
            >
              {generating ? (
                <><Clock size={14} className="animate-spin" /> Generating...</>
              ) : (
                <><FileText size={14} /> Generate Report</>
              )}
            </button>
            <button
              type="button"
              onClick={() => setShowGenerateForm(false)}
              className="text-sm px-4 py-1.5 rounded-lg border border-slate-300 hover:bg-slate-50"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {reports.length === 0 ? (
        <div className="text-center py-8">
          <FileText size={32} className="mx-auto text-slate-200 mb-2" />
          <p className="text-sm text-slate-500">No reports generated yet.</p>
          <p className="text-xs text-slate-400 mt-1">Generate reports to document investigation results.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {reports.map((report) => (
            <div key={report.id} className="bg-slate-50 border border-slate-200 rounded-lg p-4 hover:bg-slate-100 transition">
              <div className="flex items-start justify-between mb-2">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <span className={`px-2.5 py-1 rounded text-xs font-bold capitalize ${getReportTypeBadge(report.report_type)}`}>
                      {report.report_type?.replace(/_/g, ' ')}
                    </span>
                    <span className="text-xs text-slate-500">#{report.id}</span>
                  </div>
                  <h4 className="font-semibold text-slate-800 text-sm">
                    {report.title || `${report.report_type?.replace(/_/g, ' ')} Report`}
                  </h4>
                  <p className="text-xs text-slate-500 mt-1">
                    Generated {formatDate(report.generated_at || report.created_at)}
                  </p>
                </div>
                <div className="flex gap-2">
                  {report.file_path && (
                    <>
                      <button
                        onClick={() => handleDownload(report)}
                        className="px-3 py-1.5 text-xs rounded bg-blue-100 text-blue-700 hover:bg-blue-200 font-semibold flex items-center gap-1"
                      >
                        <Download size={12} />
                        Download
                      </button>
                      <button
                        onClick={() => handleDownload(report)}
                        className="px-3 py-1.5 text-xs rounded bg-slate-200 text-slate-700 hover:bg-slate-300 font-semibold flex items-center gap-1"
                      >
                        <Eye size={12} />
                        View
                      </button>
                    </>
                  )}
                </div>
              </div>

              {report.summary && (
                <div className="bg-white border border-slate-200 rounded p-3 text-sm text-slate-700 mt-2">
                  <p className="text-xs font-medium text-slate-600 mb-1">Summary:</p>
                  <p>{report.summary}</p>
                </div>
              )}

              <div className="flex items-center justify-between mt-3 pt-2 border-t border-slate-200 text-xs">
                <div className="flex gap-4">
                  {report.format && (
                    <span className="text-slate-500">Format: <span className="font-semibold text-slate-700 uppercase">{report.format}</span></span>
                  )}
                  {report.file_size && (
                    <span className="text-slate-500">Size: <span className="font-semibold text-slate-700">{(report.file_size / 1024).toFixed(1)} KB</span></span>
                  )}
                </div>
                {report.generated_by_user_id && (
                  <span className="text-slate-400">Generated by User #{report.generated_by_user_id}</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
