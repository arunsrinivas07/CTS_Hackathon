import React, { useState } from 'react';
import { useInvestigation } from '../../context/InvestigationContext';
import { claimsAPI } from '../../services/api';
import Select from '../ui/Select';

export default function DecisionPanel() {
  const { activeClaimId, claimData, setClaimData } = useInvestigation();
  const [decision, setDecision] = useState('');
  const [notes, setNotes] = useState('');
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);

  const handleSave = async () => {
    if (!decision) return;
    setSaving(true);
    try {
      let newStatus = 'under_review';
      if (decision === 'clear') newStatus = 'approved';
      else if (decision === 'suspicious') newStatus = 'flagged';

      if (claimData?.id) {
        await claimsAPI.update(claimData.id, { status: newStatus });
        await claimsAPI.addStatusHistory(claimData.id, {
          status: newStatus,
          notes: notes || `Investigator decision: ${decision}`
        });
        setClaimData(prev => ({ ...prev, status: newStatus }));
      }
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (e) {
      console.error(e);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="card p-5 space-y-4">
        <h3 className="section-title border-b pb-2">Final Investigator Decision</h3>

        <div className="space-y-4">
          <div>
            <Select
              label="Decision"
              value={decision}
              onChange={(val) => setDecision(val)}
              placeholder="-- Select Decision --"
              options={[
                { value: 'clear', label: 'Clear / No Issue' },
                { value: 'suspicious', label: 'Confirm Suspicious' },
                { value: 'escalate', label: 'Escalate Case' },
                { value: 'evidence', label: 'Request More Evidence' },
              ]}
            />
          </div>

          <div>
            <label className="block text-sm font-semibold mb-2">Investigator Notes & Rationale</label>
            <textarea
              className="w-full p-2 border rounded h-32"
              placeholder="Document your rationale..."
              value={notes}
              onChange={e => setNotes(e.target.value)}
            />
          </div>

          <button
            className="btn-primary"
            onClick={handleSave}
            disabled={saving || !decision}
          >
            {saving ? 'Saving...' : 'Save Decision'}
          </button>

          {success && <div className="text-emerald-600 text-sm mt-2">Decision saved successfully!</div>}
        </div>
      </div>
    </div>
  );
}
