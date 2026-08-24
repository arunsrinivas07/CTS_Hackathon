import React, { useState, useEffect } from 'react';
import { claimsAPI } from '../../services/api';
import { Package, Plus, DollarSign, AlertCircle, Clock } from 'lucide-react';

export default function ClaimLineItems({ claimId }) {
  const [lineItems, setLineItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showAddForm, setShowAddForm] = useState(false);

  const [formData, setFormData] = useState({
    line_number: '',
    procedure_code: '',
    procedure_description: '',
    units: '',
    billed_amount: '',
    allowed_amount: '',
    paid_amount: ''
  });

  useEffect(() => {
    if (!claimId) return;
    loadLineItems();
  }, [claimId]);

  const loadLineItems = async () => {
    try {
      setLoading(true);
      const data = await claimsAPI.getLineItems(claimId);
      setLineItems(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await claimsAPI.addLineItem(claimId, {
        ...formData,
        units: parseInt(formData.units) || 1,
        billed_amount: parseFloat(formData.billed_amount) || 0,
        allowed_amount: parseFloat(formData.allowed_amount) || 0,
        paid_amount: parseFloat(formData.paid_amount) || 0
      });
      setShowAddForm(false);
      setFormData({
        line_number: '',
        procedure_code: '',
        procedure_description: '',
        units: '',
        billed_amount: '',
        allowed_amount: '',
        paid_amount: ''
      });
      loadLineItems();
    } catch (err) {
      alert(`Failed to add line item: ${err.message}`);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Clock size={20} className="animate-spin text-blue-500 mr-2" />
        <span className="text-sm text-slate-600">Loading line items...</span>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
      <div className="flex justify-between items-center mb-4 pb-3 border-b">
        <h3 className="text-base font-bold text-slate-800 flex items-center gap-2">
          <Package size={16} className="text-slate-400" />
          Claim Line Items ({lineItems.length})
        </h3>
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className="btn-primary text-sm px-3 py-1.5 rounded-lg flex items-center gap-1"
        >
          <Plus size={14} />
          Add Line Item
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4 flex items-start gap-2">
          <AlertCircle size={16} className="text-red-500 mt-0.5" />
          <span className="text-sm text-red-700">{error}</span>
        </div>
      )}

      {showAddForm && (
        <form onSubmit={handleSubmit} className="bg-slate-50 rounded-lg p-4 mb-4 border border-slate-200">
          <h4 className="font-semibold text-sm text-slate-800 mb-3">Add New Line Item</h4>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Line Number</label>
              <input
                type="number"
                value={formData.line_number}
                onChange={(e) => setFormData({ ...formData, line_number: e.target.value })}
                className="w-full px-3 py-1.5 text-sm border border-slate-300 rounded-lg"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Procedure Code</label>
              <input
                type="text"
                value={formData.procedure_code}
                onChange={(e) => setFormData({ ...formData, procedure_code: e.target.value })}
                className="w-full px-3 py-1.5 text-sm border border-slate-300 rounded-lg"
                placeholder="CPT code"
                required
              />
            </div>
            <div className="col-span-2">
              <label className="block text-xs font-medium text-slate-600 mb-1">Description</label>
              <input
                type="text"
                value={formData.procedure_description}
                onChange={(e) => setFormData({ ...formData, procedure_description: e.target.value })}
                className="w-full px-3 py-1.5 text-sm border border-slate-300 rounded-lg"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Units</label>
              <input
                type="number"
                value={formData.units}
                onChange={(e) => setFormData({ ...formData, units: e.target.value })}
                className="w-full px-3 py-1.5 text-sm border border-slate-300 rounded-lg"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Billed Amount</label>
              <input
                type="number"
                step="0.01"
                value={formData.billed_amount}
                onChange={(e) => setFormData({ ...formData, billed_amount: e.target.value })}
                className="w-full px-3 py-1.5 text-sm border border-slate-300 rounded-lg"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Allowed Amount</label>
              <input
                type="number"
                step="0.01"
                value={formData.allowed_amount}
                onChange={(e) => setFormData({ ...formData, allowed_amount: e.target.value })}
                className="w-full px-3 py-1.5 text-sm border border-slate-300 rounded-lg"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Paid Amount</label>
              <input
                type="number"
                step="0.01"
                value={formData.paid_amount}
                onChange={(e) => setFormData({ ...formData, paid_amount: e.target.value })}
                className="w-full px-3 py-1.5 text-sm border border-slate-300 rounded-lg"
              />
            </div>
          </div>
          <div className="flex gap-2 mt-3">
            <button type="submit" className="btn-primary text-sm px-4 py-1.5 rounded-lg">Save</button>
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

      {lineItems.length === 0 ? (
        <div className="text-center py-8">
          <Package size={32} className="mx-auto text-slate-200 mb-2" />
          <p className="text-sm text-slate-500">No line items recorded yet.</p>
          <p className="text-xs text-slate-400 mt-1">Click "Add Line Item" to add procedure details.</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <th className="px-3 py-2 text-left text-xs font-semibold text-slate-600">Line</th>
                <th className="px-3 py-2 text-left text-xs font-semibold text-slate-600">Procedure Code</th>
                <th className="px-3 py-2 text-left text-xs font-semibold text-slate-600">Description</th>
                <th className="px-3 py-2 text-right text-xs font-semibold text-slate-600">Units</th>
                <th className="px-3 py-2 text-right text-xs font-semibold text-slate-600">Billed</th>
                <th className="px-3 py-2 text-right text-xs font-semibold text-slate-600">Allowed</th>
                <th className="px-3 py-2 text-right text-xs font-semibold text-slate-600">Paid</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {lineItems.map((item) => (
                <tr key={item.id} className="hover:bg-slate-50">
                  <td className="px-3 py-2 font-mono text-xs">{item.line_number}</td>
                  <td className="px-3 py-2 font-mono font-semibold">{item.procedure_code}</td>
                  <td className="px-3 py-2 text-slate-600">{item.procedure_description || '—'}</td>
                  <td className="px-3 py-2 text-right">{item.units}</td>
                  <td className="px-3 py-2 text-right font-semibold">${parseFloat(item.billed_amount || 0).toFixed(2)}</td>
                  <td className="px-3 py-2 text-right">${parseFloat(item.allowed_amount || 0).toFixed(2)}</td>
                  <td className="px-3 py-2 text-right text-emerald-600 font-semibold">${parseFloat(item.paid_amount || 0).toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
            <tfoot className="bg-slate-50 border-t-2 border-slate-300">
              <tr>
                <td colSpan="4" className="px-3 py-2 text-right font-bold text-slate-700">TOTALS:</td>
                <td className="px-3 py-2 text-right font-bold text-slate-900">
                  ${lineItems.reduce((sum, item) => sum + parseFloat(item.billed_amount || 0), 0).toFixed(2)}
                </td>
                <td className="px-3 py-2 text-right font-bold text-slate-900">
                  ${lineItems.reduce((sum, item) => sum + parseFloat(item.allowed_amount || 0), 0).toFixed(2)}
                </td>
                <td className="px-3 py-2 text-right font-bold text-emerald-600">
                  ${lineItems.reduce((sum, item) => sum + parseFloat(item.paid_amount || 0), 0).toFixed(2)}
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      )}
    </div>
  );
}
