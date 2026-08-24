import React, { useState, useEffect } from 'react';
import { investigationsAPI } from '../../services/api';
import { Search, Plus, AlertTriangle, Clock, FileText } from 'lucide-react';
import Select from '../ui/Select';

export default function FindingsManager({ investigationId, claimId }) {
  const [findings, setFindings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showAddForm, setShowAddForm] = useState(false);

  const [formData, setFormData] = useState({
    finding_type: 'discrepancy',
    severity: 'medium',
    description: '',
    supporting_evidence: '',
    recommendation: ''
  });

  useEffect(() => {
    if (!investigationId) return;
    loadFindings();
  }, [investigationId]);

  const loadFindings = async () => {
    try {
      setLoading(true);
      const data = await investigationsAPI.getFindings(investigationId);
      setFindings(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await investigationsAPI.addFinding(investigationId, formData);
      setShowAddForm(false);
      setFormData({
        finding_type: 'discrepancy',
        severity: 'medium',
        description: '',
        supporting_evidence: '',
        recommendation: ''
      });
      loadFindings();
    } catch (err) {
      alert(`Failed to add finding: ${err.message}`);
    }
  };

  const getSeverityBadge = (severity) => {
    const s = String(severity || '').toLowerCase();
    if (s === 'critical' || s === 'high') return 'bg-red-100 text-red-700 border-red-200';
    if (s === 'medium') return 'bg-amber-100 text-amber-700 border-amber-200';
    return 'bg-slate-100 text-slate-600 border-slate-200';
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
        <span className="text-sm text-slate-600">Loading findings...</span>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
      <div className="flex justify-between items-center mb-4 pb-3 border-b">
        <h3 className="text-base font-bold text-slate-800 flex items-center gap-2">
          <Search size={16} className="text-slate-400" />
          Investigation Findings ({findings.length})
        </h3>
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className="btn-primary text-sm px-3 py-1.5 rounded-lg flex items-center gap-1"
        >
          <Plus size={14} />
          Add Finding
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4 flex items-start gap-2">
          <AlertTriangle size={16} className="text-red-500 mt-0.5" />
          <span className="text-sm text-red-700">{error}</span>
        </div>
      )}

      {showAddForm && (
        <form onSubmit={handleSubmit} className="bg-slate-50 rounded-lg p-4 mb-4 border border-slate-200">
          <h4 className="font-semibold text-sm text-slate-800 mb-3">Add New Finding</h4>

          <div className="grid grid-cols-2 gap-3 mb-3">
            <div>
              <Select
                label="Finding Type"
                value={formData.finding_type}
                onChange={(val) => setFormData({ ...formData, finding_type: val })}
                options={[
                  { value: 'discrepancy', label: 'Discrepancy' },
                  { value: 'policy_violation', label: 'Policy Violation' },
                  { value: 'billing_error', label: 'Billing Error' },
                  { value: 'documentation_issue', label: 'Documentation Issue' },
                  { value: 'fraud_indicator', label: 'Fraud Indicator' },
                  { value: 'other', label: 'Other' },
                ]}
              />
            </div>
            <div>
              <Select
                label="Severity"
                value={formData.severity}
                onChange={(val) => setFormData({ ...formData, severity: val })}
                options={[
                  { value: 'critical', label: 'Critical' },
                  { value: 'high', label: 'High' },
                  { value: 'medium', label: 'Medium' },
                  { value: 'low', label: 'Low' },
                ]}
              />
            </div>
          </div>

          <div className="mb-3">
            <label className="block text-xs font-medium text-slate-600 mb-1">Description *</label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg"
              rows="3"
              required
              placeholder="Describe the finding in detail..."
            />
          </div>

          <div className="mb-3">
            <label className="block text-xs font-medium text-slate-600 mb-1">Supporting Evidence</label>
            <textarea
              value={formData.supporting_evidence}
              onChange={(e) => setFormData({ ...formData, supporting_evidence: e.target.value })}
              className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg"
              rows="2"
              placeholder="Reference evidence, documents, or data supporting this finding..."
            />
          </div>

          <div className="mb-3">
            <label className="block text-xs font-medium text-slate-600 mb-1">Recommendation</label>
            <textarea
              value={formData.recommendation}
              onChange={(e) => setFormData({ ...formData, recommendation: e.target.value })}
              className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg"
              rows="2"
              placeholder="Recommended action or next steps..."
            />
          </div>

          <div className="flex gap-2">
            <button type="submit" className="btn-primary text-sm px-4 py-1.5 rounded-lg">Save Finding</button>
            <button
              type="button"
              onClick={() => setShowAddForm(false)}
              className="text-sm px-4 py-1.5 rounded-lg border border-slate-300 hover:bg-slate-50"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {findings.length === 0 ? (
        <div className="text-center py-8">
          <FileText size={32} className="mx-auto text-slate-200 mb-2" />
          <p className="text-sm text-slate-500">No findings recorded yet.</p>
          <p className="text-xs text-slate-400 mt-1">Click "Add Finding" to document investigation results.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {findings.map((finding) => (
            <div key={finding.id} className="bg-slate-50 border border-slate-200 rounded-lg p-4">
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className={`px-2.5 py-1 rounded-full text-xs font-bold uppercase border ${getSeverityBadge(finding.severity)}`}>
                    {finding.severity}
                  </span>
                  <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 capitalize">
                    {finding.finding_type?.replace(/_/g, ' ')}
                  </span>
                </div>
                <span className="text-xs text-slate-400">{formatDate(finding.identified_at || finding.created_at)}</span>
              </div>

              <h4 className="font-semibold text-slate-800 text-sm mb-2">Finding #{finding.id}</h4>
              <p className="text-sm text-slate-700 mb-3">{finding.description}</p>

              {finding.supporting_evidence && (
                <div className="bg-white border border-slate-200 rounded p-2 mb-2">
                  <p className="text-xs font-medium text-slate-600 mb-1">Supporting Evidence:</p>
                  <p className="text-xs text-slate-600">{finding.supporting_evidence}</p>
                </div>
              )}

              {finding.recommendation && (
                <div className="bg-emerald-50 border border-emerald-100 rounded p-2">
                  <p className="text-xs font-medium text-emerald-700 mb-1">Recommendation:</p>
                  <p className="text-xs text-emerald-700">{finding.recommendation}</p>
                </div>
              )}

              {finding.identified_by_user_id && (
                <p className="text-xs text-slate-400 mt-2">Identified by User #{finding.identified_by_user_id}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
