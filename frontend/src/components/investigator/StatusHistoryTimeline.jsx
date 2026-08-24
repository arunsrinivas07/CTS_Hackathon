import React, { useState, useEffect } from 'react';
import { claimsAPI } from '../../services/api';
import { Clock, CheckCircle, XCircle, AlertCircle, Activity } from 'lucide-react';

export default function StatusHistoryTimeline({ claimId }) {
  const [statusHistory, setStatusHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!claimId) return;
    loadStatusHistory();
  }, [claimId]);

  const loadStatusHistory = async () => {
    try {
      setLoading(true);
      const data = await claimsAPI.getStatusHistory(claimId);
      setStatusHistory(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const getStatusIcon = (status) => {
    const s = String(status || '').toLowerCase();
    if (s === 'approved' || s === 'completed' || s === 'paid') return CheckCircle;
    if (s === 'denied' || s === 'rejected' || s === 'failed') return XCircle;
    if (s.includes('review') || s.includes('pending')) return AlertCircle;
    return Activity;
  };

  const getStatusColor = (status) => {
    const s = String(status || '').toLowerCase();
    if (s === 'approved' || s === 'completed' || s === 'paid') return 'bg-emerald-100 text-emerald-600';
    if (s === 'denied' || s === 'rejected' || s === 'failed') return 'bg-red-100 text-red-600';
    if (s.includes('review') || s.includes('pending')) return 'bg-amber-100 text-amber-600';
    return 'bg-blue-100 text-blue-600';
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
        <span className="text-sm text-slate-600">Loading status history...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-sm text-red-700">{error}</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
      <h3 className="text-base font-bold text-slate-800 mb-4 pb-3 border-b flex items-center gap-2">
        <Activity size={16} className="text-slate-400" />
        Status History ({statusHistory.length})
      </h3>

      {statusHistory.length === 0 ? (
        <div className="text-center py-8">
          <Activity size={32} className="mx-auto text-slate-200 mb-2" />
          <p className="text-sm text-slate-500">No status changes recorded.</p>
        </div>
      ) : (
        <div className="space-y-6 relative before:absolute before:inset-0 before:ml-[1.4rem] before:-translate-x-px before:h-full before:w-0.5 before:bg-slate-200 pl-2">
          {statusHistory.map((status, idx) => {
            // Use new_status from the status history record
            const statusValue = status.new_status || status.status || 'unknown';
            const Icon = getStatusIcon(statusValue);
            const colorClass = getStatusColor(statusValue);

            return (
              <div key={status.id || idx} className="relative flex items-start group">
                <div className={`flex items-center justify-center w-10 h-10 rounded-full border-[3px] border-white shrink-0 shadow-sm z-10 ${colorClass}`}>
                  <Icon size={16} />
                </div>
                <div className="ml-6 w-full">
                  <div className="flex items-start justify-between gap-4 mb-1 mt-1">
                    <div>
                      <h4 className="font-bold text-slate-800 text-sm capitalize">
                        {statusValue.replace(/_/g, ' ')}
                        {status.old_status && (
                          <span className="text-xs text-slate-400 font-normal ml-2">
                            (from {status.old_status.replace(/_/g, ' ')})
                          </span>
                        )}
                      </h4>
                      <p className="text-xs text-slate-500 mt-0.5">{formatDate(status.changed_at || status.created_at)}</p>
                    </div>
                    {status.changed_by && (
                      <span className="text-xs text-slate-400">User #{status.changed_by}</span>
                    )}
                  </div>
                  {status.reason && (
                    <div className="bg-slate-50 border border-slate-100 rounded-lg p-3 text-sm text-slate-700 shadow-sm mt-2">
                      <p className="font-medium text-slate-600 text-xs mb-1">Reason:</p>
                      <p>{status.reason}</p>
                    </div>
                  )}
                  {status.notes && (
                    <div className="mt-2 text-xs text-slate-600">
                      <span className="font-medium">Notes:</span> {status.notes}
                    </div>
                  )}
                </div>
              </div>
            );
          })}

          {/* Current status indicator */}
          {statusHistory.length > 0 && (
            <div className="relative flex items-start">
              <div className="flex items-center justify-center w-10 h-10 rounded-full border-[3px] border-white shrink-0 shadow-sm z-10 bg-blue-100 text-blue-600">
                <Clock size={16} />
              </div>
              <div className="ml-6 mt-2">
                <h4 className="font-bold text-blue-600 text-sm">Current Status</h4>
                <p className="text-xs text-slate-500">Last updated {formatDate(statusHistory[0].changed_at || statusHistory[0].created_at)}</p>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
