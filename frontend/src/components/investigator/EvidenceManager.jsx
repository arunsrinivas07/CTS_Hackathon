import React, { useState, useEffect } from 'react';
import { investigationsAPI } from '../../services/api';
import { FileText, Plus, Upload, Clock, ExternalLink } from 'lucide-react';
import Select from '../ui/Select';

export default function EvidenceManager({ investigationId }) {
  const [evidence, setEvidence] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showAddForm, setShowAddForm] = useState(false);

  const [formData, setFormData] = useState({
    evidence_type: 'document',
    source: '',
    description: '',
    content: '',
    confidence_score: '0.8'
  });

  useEffect(() => {
    if (!investigationId) return;
    loadEvidence();
  }, [investigationId]);

  const loadEvidence = async () => {
    try {
      setLoading(true);
      const data = await investigationsAPI.getEvidence(investigationId);
      setEvidence(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await investigationsAPI.addEvidence(investigationId, {
        ...formData,
        confidence_score: parseFloat(formData.confidence_score) || 0.8
      });
      setShowAddForm(false);
      setFormData({
        evidence_type: 'document',
        source: '',
        description: '',
        content: '',
        confidence_score: '0.8'
      });
      loadEvidence();
    } catch (err) {
      alert(`Failed to add evidence: ${err.message}`);
    }
  };

  const getEvidenceTypeColor = (type) => {
    const t = String(type || '').toLowerCase();
    if (t === 'document') return 'bg-blue-100 text-blue-700';
    if (t === 'screenshot') return 'bg-purple-100 text-purple-700';
    if (t === 'medical_record') return 'bg-teal-100 text-teal-700';
    if (t === 'policy_reference') return 'bg-amber-100 text-amber-700';
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
        <span className="text-sm text-slate-600">Loading evidence...</span>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
      <div className="flex justify-between items-center mb-4 pb-3 border-b">
        <h3 className="text-base font-bold text-slate-800 flex items-center gap-2">
          <FileText size={16} className="text-slate-400" />
          Evidence Items ({evidence.length})
        </h3>
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className="btn-primary text-sm px-3 py-1.5 rounded-lg flex items-center gap-1"
        >
          <Plus size={14} />
          Add Evidence
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
          <span className="text-sm text-red-700">{error}</span>
        </div>
      )}

      {showAddForm && (
        <form onSubmit={handleSubmit} className="bg-slate-50 rounded-lg p-4 mb-4 border border-slate-200">
          <h4 className="font-semibold text-sm text-slate-800 mb-3">Add New Evidence</h4>

          <div className="grid grid-cols-2 gap-3 mb-3">
            <div>
              <Select
                label="Evidence Type"
                value={formData.evidence_type}
                onChange={(val) => setFormData({ ...formData, evidence_type: val })}
                options={[
                  { value: 'document', label: 'Document' },
                  { value: 'screenshot', label: 'Screenshot' },
                  { value: 'medical_record', label: 'Medical Record' },
                  { value: 'policy_reference', label: 'Policy Reference' },
                  { value: 'testimony', label: 'Testimony' },
                  { value: 'data_analysis', label: 'Data Analysis' },
                  { value: 'other', label: 'Other' },
                ]}
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Source</label>
              <input
                type="text"
                value={formData.source}
                onChange={(e) => setFormData({ ...formData, source: e.target.value })}
                className="w-full px-3 py-1.5 text-sm border border-slate-300 rounded-lg"
                placeholder="Source or origin"
                required
              />
            </div>
          </div>

          <div className="mb-3">
            <label className="block text-xs font-medium text-slate-600 mb-1">Description *</label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg"
              rows="2"
              required
              placeholder="Brief description of the evidence..."
            />
          </div>

          <div className="mb-3">
            <label className="block text-xs font-medium text-slate-600 mb-1">Content/Details</label>
            <textarea
              value={formData.content}
              onChange={(e) => setFormData({ ...formData, content: e.target.value })}
              className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg"
              rows="3"
              placeholder="Detailed content, findings, or notes..."
            />
          </div>

          <div className="mb-3">
            <label className="block text-xs font-medium text-slate-600 mb-1">Confidence Score (0-1)</label>
            <input
              type="number"
              step="0.1"
              min="0"
              max="1"
              value={formData.confidence_score}
              onChange={(e) => setFormData({ ...formData, confidence_score: e.target.value })}
              className="w-full px-3 py-1.5 text-sm border border-slate-300 rounded-lg"
            />
          </div>

          <div className="flex gap-2">
            <button type="submit" className="btn-primary text-sm px-4 py-1.5 rounded-lg">Save Evidence</button>
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

      {evidence.length === 0 ? (
        <div className="text-center py-8">
          <Upload size={32} className="mx-auto text-slate-200 mb-2" />
          <p className="text-sm text-slate-500">No evidence items yet.</p>
          <p className="text-xs text-slate-400 mt-1">Upload or document evidence to support the investigation.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {evidence.map((item) => (
            <div key={item.id} className="bg-slate-50 border border-slate-200 rounded-lg p-4">
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className={`px-2.5 py-1 rounded-full text-xs font-bold capitalize ${getEvidenceTypeColor(item.evidence_type)}`}>
                    {item.evidence_type?.replace(/_/g, ' ')}
                  </span>
                  <span className="text-xs text-slate-500">#{item.id}</span>
                </div>
                <span className="text-xs text-slate-400">{formatDate(item.collected_at || item.created_at)}</span>
              </div>

              <h4 className="font-semibold text-slate-800 text-sm mb-1">{item.description}</h4>

              {item.source && (
                <p className="text-xs text-slate-500 mb-2">
                  <span className="font-medium">Source:</span> {item.source}
                </p>
              )}

              {item.content && (
                <div className="bg-white border border-slate-200 rounded p-3 text-sm text-slate-700 mb-2">
                  {item.content}
                </div>
              )}

              {item.file_path && (
                <div className="flex items-center gap-2 text-xs text-blue-600 hover:text-blue-700 cursor-pointer">
                  <ExternalLink size={12} />
                  <span>View attachment</span>
                </div>
              )}

              <div className="flex items-center justify-between mt-3 pt-2 border-t border-slate-200">
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-500">Confidence:</span>
                  <div className="w-24 h-1.5 bg-slate-200 rounded-full">
                    <div
                      className="h-full bg-emerald-500 rounded-full"
                      style={{ width: `${(item.confidence_score || 0) * 100}%` }}
                    />
                  </div>
                  <span className="text-xs font-bold text-slate-700">
                    {Math.round((item.confidence_score || 0) * 100)}%
                  </span>
                </div>
                {item.collected_by_user_id && (
                  <span className="text-xs text-slate-400">Collected by User #{item.collected_by_user_id}</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
