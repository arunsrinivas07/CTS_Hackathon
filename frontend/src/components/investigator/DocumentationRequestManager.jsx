import React, { useState, useEffect } from 'react';
import { documentationRequestsAPI } from '../../services/api';
import { FileText, Plus, Clock, CheckCircle, AlertCircle } from 'lucide-react';
import Select from '../ui/Select';

export default function DocumentationRequestManager({ investigationId }) {
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showAddForm, setShowAddForm] = useState(false);

  const [formData, setFormData] = useState({
    request_type: 'medical_records',
    description: '',
    requested_from: '',
    urgency: 'normal',
    due_date: ''
  });

  useEffect(() => {
    if (!investigationId) return;
    loadRequests();
  }, [investigationId]);

  const loadRequests = async () => {
    try {
      setLoading(true);
      const data = await documentationRequestsAPI.getByInvestigation(investigationId);
      setRequests(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await documentationRequestsAPI.create({
        ...formData,
        investigation_id: investigationId,
        status: 'pending'
      });
      setShowAddForm(false);
      setFormData({
        request_type: 'medical_records',
        description: '',
        requested_from: '',
        urgency: 'normal',
        due_date: ''
      });
      loadRequests();
    } catch (err) {
      alert(`Failed to create request: ${err.message}`);
    }
  };

  const handleMarkFulfilled = async (requestId) => {
    try {
      await documentationRequestsAPI.update(requestId, {
        status: 'fulfilled',
        fulfilled_date: new Date().toISOString()
      });
      loadRequests();
    } catch (err) {
      alert(`Failed to update status: ${err.message}`);
    }
  };

  const getStatusBadge = (status) => {
    const s = String(status || '').toLowerCase();
    if (s === 'fulfilled') return 'bg-emerald-100 text-emerald-700 border-emerald-200';
    if (s === 'pending') return 'bg-amber-100 text-amber-700 border-amber-200';
    if (s === 'overdue') return 'bg-red-100 text-red-700 border-red-200';
    return 'bg-slate-100 text-slate-600 border-slate-200';
  };

  const getUrgencyBadge = (urgency) => {
    const u = String(urgency || '').toLowerCase();
    if (u === 'urgent' || u === 'high') return 'bg-red-50 text-red-600 border-red-200';
    if (u === 'normal' || u === 'medium') return 'bg-blue-50 text-blue-600 border-blue-200';
    return 'bg-slate-50 text-slate-500 border-slate-200';
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '—';
    try {
      return new Date(dateStr).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
      });
    } catch {
      return String(dateStr);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Clock size={20} className="animate-spin text-blue-500 mr-2" />
        <span className="text-sm text-slate-600">Loading documentation requests...</span>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
      <div className="flex justify-between items-center mb-4 pb-3 border-b">
        <h3 className="text-base font-bold text-slate-800 flex items-center gap-2">
          <FileText size={16} className="text-slate-400" />
          Documentation Requests ({requests.length})
        </h3>
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className="btn-primary text-sm px-3 py-1.5 rounded-lg flex items-center gap-1"
        >
          <Plus size={14} />
          Request Documents
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
          <span className="text-sm text-red-700">{error}</span>
        </div>
      )}

      {showAddForm && (
        <form onSubmit={handleSubmit} className="bg-slate-50 rounded-lg p-4 mb-4 border border-slate-200">
          <h4 className="font-semibold text-sm text-slate-800 mb-3">New Documentation Request</h4>

          <div className="grid grid-cols-2 gap-3 mb-3">
            <div>
              <Select
                label="Request Type"
                value={formData.request_type}
                onChange={(val) => setFormData({ ...formData, request_type: val })}
                options={[
                  { value: 'medical_records', label: 'Medical Records' },
                  { value: 'billing_statement', label: 'Billing Statement' },
                  { value: 'prior_authorization', label: 'Prior Authorization' },
                  { value: 'lab_results', label: 'Lab Results' },
                  { value: 'imaging', label: 'Imaging/Radiology' },
                  { value: 'provider_notes', label: 'Provider Notes' },
                  { value: 'other', label: 'Other' },
                ]}
              />
            </div>
            <div>
              <Select
                label="Urgency"
                value={formData.urgency}
                onChange={(val) => setFormData({ ...formData, urgency: val })}
                options={[
                  { value: 'urgent', label: 'Urgent' },
                  { value: 'normal', label: 'Normal' },
                  { value: 'low', label: 'Low Priority' },
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
              placeholder="Specify what documents are needed and why..."
            />
          </div>

          <div className="grid grid-cols-2 gap-3 mb-3">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Requested From</label>
              <input
                type="text"
                value={formData.requested_from}
                onChange={(e) => setFormData({ ...formData, requested_from: e.target.value })}
                className="w-full px-3 py-1.5 text-sm border border-slate-300 rounded-lg"
                placeholder="Provider, facility, etc."
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Due Date</label>
              <input
                type="date"
                value={formData.due_date}
                onChange={(e) => setFormData({ ...formData, due_date: e.target.value })}
                className="w-full px-3 py-1.5 text-sm border border-slate-300 rounded-lg"
              />
            </div>
          </div>

          <div className="flex gap-2">
            <button type="submit" className="btn-primary text-sm px-4 py-1.5 rounded-lg">Create Request</button>
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

      {requests.length === 0 ? (
        <div className="text-center py-8">
          <FileText size={32} className="mx-auto text-slate-200 mb-2" />
          <p className="text-sm text-slate-500">No documentation requests yet.</p>
          <p className="text-xs text-slate-400 mt-1">Request additional documents to support the investigation.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {requests.map((request) => (
            <div key={request.id} className="bg-slate-50 border border-slate-200 rounded-lg p-4">
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className={`px-2.5 py-1 rounded-full text-xs font-bold uppercase border ${getStatusBadge(request.status)}`}>
                    {request.status}
                  </span>
                  <span className={`px-2.5 py-1 rounded text-xs font-semibold border ${getUrgencyBadge(request.urgency)}`}>
                    {request.urgency || 'normal'} priority
                  </span>
                  <span className="px-2.5 py-1 rounded text-xs font-semibold bg-blue-50 text-blue-700 capitalize">
                    {request.request_type?.replace(/_/g, ' ')}
                  </span>
                </div>
                {request.status !== 'fulfilled' && (
                  <button
                    onClick={() => handleMarkFulfilled(request.id)}
                    className="text-xs px-3 py-1 rounded bg-emerald-100 text-emerald-700 hover:bg-emerald-200 font-semibold"
                  >
                    Mark Fulfilled
                  </button>
                )}
              </div>

              <h4 className="font-semibold text-slate-800 text-sm mb-2">Request #{request.id}</h4>
              <p className="text-sm text-slate-700 mb-3">{request.description}</p>

              <div className="grid grid-cols-2 gap-3 text-xs">
                {request.requested_from && (
                  <div>
                    <span className="text-slate-500">Requested from:</span>
                    <span className="ml-1 font-semibold text-slate-700">{request.requested_from}</span>
                  </div>
                )}
                {request.due_date && (
                  <div>
                    <span className="text-slate-500">Due:</span>
                    <span className="ml-1 font-semibold text-slate-700">{formatDate(request.due_date)}</span>
                  </div>
                )}
                <div>
                  <span className="text-slate-500">Requested:</span>
                  <span className="ml-1 font-semibold text-slate-700">{formatDate(request.request_date || request.created_at)}</span>
                </div>
                {request.fulfilled_date && (
                  <div>
                    <span className="text-slate-500">Fulfilled:</span>
                    <span className="ml-1 font-semibold text-emerald-600">{formatDate(request.fulfilled_date)}</span>
                  </div>
                )}
              </div>

              {request.requested_by_user_id && (
                <p className="text-xs text-slate-400 mt-2">Requested by User #{request.requested_by_user_id}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
