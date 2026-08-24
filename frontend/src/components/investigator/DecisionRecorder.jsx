import React, { useState, useEffect } from 'react';
import { investigationsAPI, decisionsAPI } from '../../services/api';
import { CheckCircle, XCircle, Clock, AlertCircle, FileText } from 'lucide-react';
import Select from '../ui/Select';

export default function DecisionRecorder({ investigationId }) {
  const [decisions, setDecisions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showAddForm, setShowAddForm] = useState(false);

  const [formData, setFormData] = useState({
    decision_type: 'approve',
    decision_rationale: '',
    recommended_action: '',
    confidence_level: '0.8'
  });

  useEffect(() => {
    if (!investigationId) return;
    loadDecisions();
  }, [investigationId]);

  const loadDecisions = async () => {
    try {
      setLoading(true);
      const data = await investigationsAPI.getDecisions(investigationId);
      setDecisions(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await investigationsAPI.addDecision(investigationId, {
        ...formData,
        confidence_level: parseFloat(formData.confidence_level) || 0.8
      });
      setShowAddForm(false);
      setFormData({
        decision_type: 'approve',
        decision_rationale: '',
        recommended_action: '',
        confidence_level: '0.8'
      });
      loadDecisions();
    } catch (err) {
      alert(`Failed to record decision: ${err.message}`);
    }
  };

  const getDecisionIcon = (type) => {
    const t = String(type || '').toLowerCase();
    if (t === 'approve' || t === 'approved') return CheckCircle;
    if (t === 'deny' || t === 'denied' || t === 'reject') return XCircle;
    if (t === 'review' || t === 'pending') return AlertCircle;
    return Clock;
  };

  const getDecisionColor = (type) => {
    const t = String(type || '').toLowerCase();
    if (t === 'approve' || t === 'approved') return 'bg-emerald-100 text-emerald-700 border-emerald-200';
    if (t === 'deny' || t === 'denied' || t === 'reject') return 'bg-red-100 text-red-700 border-red-200';
    if (t === 'review' || t === 'pending') return 'bg-amber-100 text-amber-700 border-amber-200';
    return 'bg-blue-100 text-blue-700 border-blue-200';
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
        <span className="text-sm text-slate-600">Loading decisions...</span>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
      <div className="flex justify-between items-center mb-4 pb-3 border-b">
        <h3 className="text-base font-bold text-slate-800 flex items-center gap-2">
          <FileText size={16} className="text-slate-400" />
          Investigation Decisions ({decisions.length})
        </h3>
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className="btn-primary text-sm px-3 py-1.5 rounded-lg flex items-center gap-1"
        >
          <CheckCircle size={14} />
          Record Decision
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
          <span className="text-sm text-red-700">{error}</span>
        </div>
      )}

      {showAddForm && (
        <form onSubmit={handleSubmit} className="bg-slate-50 rounded-lg p-4 mb-4 border border-slate-200">
          <h4 className="font-semibold text-sm text-slate-800 mb-3">Record New Decision</h4>

          <div className="mb-3">
            <Select
              label="Decision Type"
              value={formData.decision_type}
              onChange={(val) => setFormData({ ...formData, decision_type: val })}
              options={[
                { value: 'approve', label: 'Approve' },
                { value: 'deny', label: 'Deny' },
                { value: 'pending_review', label: 'Pending Review' },
                { value: 'request_more_info', label: 'Request More Info' },
                { value: 'escalate', label: 'Escalate' },
              ]}
            />
          </div>

          <div className="mb-3">
            <label className="block text-xs font-medium text-slate-600 mb-1">Decision Rationale *</label>
            <textarea
              value={formData.decision_rationale}
              onChange={(e) => setFormData({ ...formData, decision_rationale: e.target.value })}
              className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg"
              rows="4"
              required
              placeholder="Explain the reasoning behind this decision..."
            />
          </div>

          <div className="mb-3">
            <label className="block text-xs font-medium text-slate-600 mb-1">Recommended Action</label>
            <textarea
              value={formData.recommended_action}
              onChange={(e) => setFormData({ ...formData, recommended_action: e.target.value })}
              className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg"
              rows="2"
              placeholder="Next steps or actions to take..."
            />
          </div>

          <div className="mb-3">
            <label className="block text-xs font-medium text-slate-600 mb-1">Confidence Level (0-1)</label>
            <input
              type="number"
              step="0.1"
              min="0"
              max="1"
              value={formData.confidence_level}
              onChange={(e) => setFormData({ ...formData, confidence_level: e.target.value })}
              className="w-full px-3 py-1.5 text-sm border border-slate-300 rounded-lg"
            />
          </div>

          <div className="flex gap-2">
            <button type="submit" className="btn-primary text-sm px-4 py-1.5 rounded-lg">Save Decision</button>
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

      {decisions.length === 0 ? (
        <div className="text-center py-8">
          <CheckCircle size={32} className="mx-auto text-slate-200 mb-2" />
          <p className="text-sm text-slate-500">No decisions recorded yet.</p>
          <p className="text-xs text-slate-400 mt-1">Record investigation outcome and final decision.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {decisions.map((decision) => {
            const Icon = getDecisionIcon(decision.decision_type);
            return (
              <div key={decision.id} className={`border-2 rounded-lg p-5 ${getDecisionColor(decision.decision_type)}`}>
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <Icon size={24} />
                    <div>
                      <h4 className="font-bold text-sm capitalize">
                        {decision.decision_type?.replace(/_/g, ' ')}
                      </h4>
                      <p className="text-xs opacity-75 mt-0.5">{formatDate(decision.decision_date || decision.created_at)}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-xs font-medium mb-1">Confidence</p>
                    <p className="text-lg font-bold">{Math.round((decision.confidence_level || 0) * 100)}%</p>
                  </div>
                </div>

                <div className="bg-white/50 rounded-lg p-3 mb-3">
                  <p className="text-xs font-semibold mb-1">Rationale:</p>
                  <p className="text-sm">{decision.decision_rationale}</p>
                </div>

                {decision.recommended_action && (
                  <div className="bg-white/50 rounded-lg p-3 mb-3">
                    <p className="text-xs font-semibold mb-1">Recommended Action:</p>
                    <p className="text-sm">{decision.recommended_action}</p>
                  </div>
                )}

                {decision.made_by_user_id && (
                  <p className="text-xs opacity-75">Decision by User #{decision.made_by_user_id}</p>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
