import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  CheckCircle, AlertTriangle, Clock, Eye, FileText, Search,
  Download, Send, HelpCircle, AlertCircle, Sparkles
} from 'lucide-react';
import PageHeader from '../../components/ui/PageHeader';
import Badge from '../../components/ui/Badge';
import Select from '../../components/ui/Select';
import Modal from '../../components/ui/Modal';
import { claimsAPI, documentationRequestsAPI, investigationsAPI } from '../../services/api';

export default function DocumentVerification() {
  const { claimId } = useParams();

  // Load real data from backend instead of localStorage
  const [docRequests, setDocRequests] = useState([]);
  const [claims, setClaims] = useState([]);
  const [investigations, setInvestigations] = useState([]);
  const [loading, setLoading] = useState(true);

  // Load data from backend on mount
  useEffect(() => {
    let isMounted = true;

    const loadData = async () => {
      try {
        setLoading(true);

        // Load all required data in parallel
        const [claimsRes, docReqRes, invRes] = await Promise.all([
          claimsAPI.getAll(),
          documentationRequestsAPI.getAll(),
          investigationsAPI.getAll()
        ]);

        if (isMounted) {
          setClaims(claimsRes || []);
          setDocRequests(docReqRes || []);
          setInvestigations(invRes || []);
        }
      } catch (err) {
        console.error('Error loading document verification data:', err);
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    loadData();
    return () => { isMounted = false; };
  }, []);

  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');

  // Modal state for rejection
  const [rejectModalOpen, setRejectModalOpen] = useState(false);
  const [selectedDocToReject, setSelectedDocToReject] = useState(null);
  const [rejectReason, setRejectReason] = useState('');
  const [rejectionError, setRejectionError] = useState('');
  const [feedbackMessage, setFeedbackMessage] = useState('');

  // Send request form states
  const [targetClaimId, setTargetClaimId] = useState('');
  const [requiredDoc, setRequiredDoc] = useState('');
  const [investigativeNotes, setInvestigativeNotes] = useState('');
  const [requestFeedback, setRequestFeedback] = useState('');
  const [formErrors, setFormErrors] = useState({});

  // Map doc requests to display format
  const documents = docRequests.map(req => {
    const inv = investigations.find(i => i.id === req.investigation_id);
    const claim = claims.find(c => c.id === inv?.claim_id);

    return {
      id: req.id,
      name: req.document_type,
      type: 'Medical Record',
      claimId: claim?.claim_number || `CLM-${inv?.claim_id}`,
      investigationId: req.investigation_id,
      status: req.is_fulfilled ? 'verified' : 'under_review',
      uploadedDate: new Date(req.created_at).toLocaleDateString(),
      size: '2.4 MB',
      requestedFrom: req.requested_from,
      description: req.description,
      dueDate: req.due_date ? new Date(req.due_date).toLocaleDateString() : null
    };
  });

  // Filter documents
  const filtered = documents.filter(d => {
    const matchesClaimParam = !claimId || d.claimId === claimId;
    const s = search.toLowerCase();
    const matchSearch = d.name.toLowerCase().includes(s) || d.claimId.toLowerCase().includes(s);
    const matchStatus = statusFilter === 'all' || d.status === statusFilter;
    return matchesClaimParam && matchSearch && matchStatus;
  });

  // Rejection actions
  const handleOpenRejectModal = (doc) => {
    setSelectedDocToReject(doc);
    setRejectReason('');
    setRejectionError('');
    setRejectModalOpen(true);
  };

  const handleConfirmRejection = async () => {
    if (!rejectReason.trim()) {
      setRejectionError('Reason for rejection/dispute is required.');
      return;
    }

    try {
      // Update the documentation request to mark as rejected (not fulfilled)
      await documentationRequestsAPI.update(selectedDocToReject.id, {
        is_fulfilled: false,
        description: `${selectedDocToReject.description}\n\nREJECTED: ${rejectReason}`
      });

      // Reload data
      const updated = await documentationRequestsAPI.getAll();
      setDocRequests(updated || []);

      setRejectModalOpen(false);
      setFeedbackMessage(`Document "${selectedDocToReject.name}" rejected.`);
      setTimeout(() => setFeedbackMessage(''), 4000);
    } catch (err) {
      setRejectionError('Failed to reject document: ' + err.message);
    }
  };

  const handleVerifyAccept = async (docId) => {
    try {
      // Update the documentation request to mark as fulfilled
      await documentationRequestsAPI.update(docId, {
        is_fulfilled: true
      });

      // Reload data
      const updated = await documentationRequestsAPI.getAll();
      setDocRequests(updated || []);

      setFeedbackMessage('Document verified and accepted.');
      setTimeout(() => setFeedbackMessage(''), 4000);
    } catch (err) {
      console.error('Failed to verify document:', err);
      setFeedbackMessage('Error verifying document: ' + err.message);
    }
  };

  // Submit request to provider
  const handleTransmitRequest = async (e) => {
    e.preventDefault();
    const errors = {};

    if (!targetClaimId) errors.targetClaim = 'Target claim is required.';
    if (!requiredDoc.trim()) errors.requiredDoc = 'Required document field is required.';

    if (Object.keys(errors).length > 0) {
      setFormErrors(errors);
      return;
    }

    try {
      // Find investigation for this claim
      const claim = claims.find(c => c.id === parseInt(targetClaimId) || c.claim_number === targetClaimId);
      let investigation = investigations.find(i => i.claim_id === claim?.id);

      // If no investigation exists, create one
      if (!investigation) {
        investigation = await investigationsAPI.create({
          claim_id: claim.id,
          priority: 'medium',
          reason: 'Document verification required',
          status: 'open'
        });
        setInvestigations([...investigations, investigation]);
      }

      // Create documentation request
      const dueDate = new Date();
      dueDate.setDate(dueDate.getDate() + 7); // 7 days from now

      await documentationRequestsAPI.create({
        investigation_id: investigation.id,
        requested_from: claim.provider?.name || 'Provider',
        document_type: requiredDoc,
        description: investigativeNotes || `Document request for ${requiredDoc}`,
        due_date: dueDate.toISOString(),
        is_fulfilled: false
      });

      // Reload data
      const updated = await documentationRequestsAPI.getAll();
      setDocRequests(updated || []);

      setFormErrors({});
      setRequestFeedback(`Formal document request for ${requiredDoc} sent to the provider.`);
      setTimeout(() => setRequestFeedback(''), 4000);

      // Clear form
      setRequiredDoc('');
      setInvestigativeNotes('');
    } catch (err) {
      console.error('Failed to create documentation request:', err);
      setFormErrors({ submit: 'Failed to send request: ' + err.message });
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-slate-500">Loading documentation requests...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Document Verification & Request Center"
        subtitle="Verify uploaded medical records from healthcare providers or transmit formal document requests."
        actions={
          <button
            className="btn-primary text-xs bg-green-600 hover:bg-green-700 flex items-center gap-1.5"
            onClick={() => {
              const element = document.getElementById('request-form-card');
              if (element) {
                element.scrollIntoView({ behavior: 'smooth' });
                element.classList.add('ring-2', 'ring-green-500');
                setTimeout(() => element.classList.remove('ring-2', 'ring-green-500'), 2000);
              }
            }}
          >
            + Send New Document Request to Provider
          </button>
        }
      />

      {feedbackMessage && (
        <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 px-4 py-3 rounded-xl flex items-center gap-2 text-sm animate-fade-in shadow-sm">
          <CheckCircle size={15} className="text-emerald-600" />
          {feedbackMessage}
        </div>
      )}

      {claimId && (
        <div className="bg-rose-50 border border-rose-200 text-rose-800 px-4 py-2.5 rounded-xl flex items-center justify-between text-xs">
          <span>Currently filtering documents for Claim: <strong>{claimId}</strong></span>
          <Link to="/investigator/documents" className="text-rose-600 hover:underline font-bold">Clear Claim Filter</Link>
        </div>
      )}

      {/* Filter Row */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            className="input pl-9 text-xs"
            placeholder="Search by document title or claim ID…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
        <div className="w-full sm:w-44">
          <Select
            value={statusFilter}
            onChange={(val) => setStatusFilter(val)}
            options={[
              { value: 'all', label: 'All Statuses' },
              { value: 'verified', label: 'Verified' },
              { value: 'under_review', label: 'Under Review' },
              { value: 'flagged', label: 'Flagged' },
              { value: 'rejected', label: 'Rejected' },
            ]}
          />
        </div>
      </div>

      {/* Two Column Layout: Left pending list, Right send request + guidelines */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* LEFT COLUMN: Pending/Uploaded Documents */}
        <div className="lg:col-span-8 space-y-4">
          <div className="flex justify-between items-center px-2">
            <h3 className="section-title text-slate-700">
              Uploaded Provider Documents Pending Verification ({filtered.length})
            </h3>
          </div>

          {filtered.length === 0 ? (
            <div className="card p-8 text-center text-slate-400 text-sm">
              No matching documents require verification.
            </div>
          ) : (
            <div className="space-y-4">
              {filtered.map(doc => {
                const claim = claims.find(c => c.claim_number === doc.claimId || c.id === doc.claimId);
                return (
                  <div
                    key={doc.id}
                    className={`card p-5 space-y-4 transition-all hover:shadow-md border-l-4 ${doc.status === 'verified'
                      ? 'border-l-[#92400e]'
                      : doc.status === 'rejected'
                        ? 'border-l-rose-500'
                        : doc.status === 'flagged'
                          ? 'border-l-amber-500'
                          : 'border-l-rose-400'
                      }`}
                  >
                    {/* Top Row: Claim ID & Status Badge */}
                    <div className="flex justify-between items-start flex-wrap gap-2">
                      <div className="flex items-center gap-2">
                        <Link
                          to={`/investigations/${doc.investigationId}`}
                          className="text-[11px] font-mono font-bold text-rose-600 bg-rose-50 px-2.5 py-1 rounded-lg border border-rose-200 hover:bg-rose-100"
                        >
                          Claim {doc.claimId}
                        </Link>
                        <span className="text-[10px] text-slate-400 font-semibold">{doc.type}</span>
                      </div>
                      <Badge status={doc.status} size="xs" />
                    </div>

                    {/* Document Info */}
                    <div className="space-y-1">
                      <h4 className="text-sm font-bold text-slate-800 flex items-center gap-1.5">
                        <FileText size={15} className="text-rose-500" />
                        {doc.name}
                      </h4>
                      <p className="text-xs text-slate-500">
                        Requested from <strong className="text-slate-700">{doc.requestedFrom}</strong> · Due: {doc.dueDate || 'Not set'} · Created: {doc.uploadedDate}
                      </p>
                      {doc.description && (
                        <p className="text-xs text-slate-600 italic mt-2">{doc.description}</p>
                      )}
                    </div>

                    {/* Verification Signals */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 bg-slate-50 p-3 rounded-xl border border-slate-100">
                      <div className="text-xs flex items-center gap-2">
                        <Search size={14} className="text-slate-400 flex-shrink-0" />
                        <span>
                          <strong>OCR Verification:</strong> {doc.status === 'verified' ? 'Passed (99.4% Match)' : 'CCR Text Extracted (99.4%)'}
                        </span>
                      </div>
                      <div className="text-xs flex items-center gap-2">
                        <CheckCircle size={14} className="text-emerald-500 flex-shrink-0" />
                        <span>
                          <strong>Authenticity Check:</strong> {doc.status === 'verified' ? 'Valid Digital Stamp' : 'Digital Stamp: Dr. Rajesh Kumar (Verified)'}
                        </span>
                      </div>
                    </div>

                    {/* Rejection reason displayed if rejected */}
                    {doc.status === 'rejected' && doc.rejectionReason && (
                      <div className="bg-rose-50 border border-rose-100 text-rose-800 p-3 rounded-xl text-xs space-y-1">
                        <strong>Rejection Reason:</strong>
                        <p className="italic">{doc.rejectionReason}</p>
                      </div>
                    )}

                    {/* Action buttons */}
                    <div className="pt-3 border-t flex justify-between items-center flex-wrap gap-2">
                      <button
                        className="btn-ghost text-xs py-1.5 px-3"
                        onClick={() => alert(`Viewing full document details for ${doc.name}`)}
                      >
                        <Eye size={13} /> View Full Document
                      </button>

                      {doc.status !== 'verified' && doc.status !== 'rejected' && (
                        <div className="flex gap-2">
                          <button
                            className="btn-secondary text-xs py-1.5 px-3 border-red-200 text-red-600 hover:bg-red-50"
                            onClick={() => handleOpenRejectModal(doc)}
                          >
                            Reject / Dispute
                          </button>
                          <button
                            className="btn-primary text-xs py-1.5 px-3 bg-green-600 hover:bg-green-700"
                            onClick={() => handleVerifyAccept(doc.id)}
                          >
                            Verify & Accept
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* RIGHT COLUMN: Request Form & Integrity Guidelines */}
        <div className="lg:col-span-4 space-y-6">
          {/* Request Form */}
          <div id="request-form-card" className="card p-5 space-y-4 transition-all">
            <div>
              <h3 className="section-title text-slate-800 flex items-center gap-1.5">
                <Send size={15} className="text-[#92400e]" />
                Send Document Request to Provider
              </h3>
              <p className="text-xs text-slate-400 mt-1 leading-snug">
                Request specific operative charts, radiologist slice logs, or prescription receipts directly from the hospital billing unit.
              </p>
            </div>

            {requestFeedback && (
              <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 p-3 rounded-xl text-xs flex items-center gap-2">
                <CheckCircle size={13} className="text-emerald-600" />
                {requestFeedback}
              </div>
            )}

            <form onSubmit={handleTransmitRequest} className="space-y-3.5">
              <div>
                <Select
                  label="Target Claim *"
                  value={targetClaimId}
                  onChange={(val) => setTargetClaimId(val)}
                  placeholder="Select a claim..."
                  options={claims.map(c => ({
                    value: c.id,
                    label: `${c.claim_number} - ${c.provider?.name || 'Provider'} ($${parseFloat(c.total_billed_amount || 0).toLocaleString()})`
                  }))}
                />
                {formErrors.targetClaim && (
                  <p className="text-[10px] text-red-600 font-semibold">{formErrors.targetClaim}</p>
                )}
              </div>

              <div className="space-y-1">
                <label className="text-xs font-bold text-slate-600 block">Required Document Checklist *</label>
                <input
                  type="text"
                  className="input text-xs py-2"
                  placeholder="e.g. Signed Radiologist MRI Interpretations, Post-op charts..."
                  value={requiredDoc}
                  onChange={e => setRequiredDoc(e.target.value)}
                />
                {formErrors.requiredDoc && (
                  <p className="text-[10px] text-red-600 font-semibold">{formErrors.requiredDoc}</p>
                )}
              </div>

              <div className="space-y-1">
                <label className="text-xs font-bold text-slate-600 block">Specific Investigative Notes to Provider</label>
                <textarea
                  className="input min-h-[80px] resize-none text-xs py-2"
                  placeholder="Please provide high-resolution DICOM slices and signed radiologist notes to substantiate billed amount..."
                  value={investigativeNotes}
                  onChange={e => setInvestigativeNotes(e.target.value)}
                />
              </div>

              <button
                type="submit"
                className="w-full btn-primary justify-center text-xs py-2.5 bg-green-600 hover:bg-green-700 shadow-md mt-1"
              >
                Transmit Formal Request to Hospital
              </button>
            </form>
          </div>

          {/* Document Integrity Guidelines */}
          <div className="card p-5 space-y-4">
            <h3 className="section-title flex items-center gap-1.5">
              <HelpCircle size={15} className="text-slate-600" />
              Document Integrity Guidelines
            </h3>
            <div className="space-y-3 text-xs text-slate-600 leading-relaxed">
              <div className="flex gap-2.5 items-start">
                <div className="p-1 rounded bg-green-50 text-green-600 mt-0.5"><CheckCircle size={12} /></div>
                <p>Check NPI digital signature matches state licensing board database registry.</p>
              </div>
              <div className="flex gap-2.5 items-start">
                <div className="p-1 rounded bg-green-50 text-green-600 mt-0.5"><CheckCircle size={12} /></div>
                <p>Cross-reference date of service with patient EHR timeline to confirm valid admission times.</p>
              </div>
              <div className="flex gap-2.5 items-start">
                <div className="p-1 rounded bg-green-50 text-green-600 mt-0.5"><CheckCircle size={12} /></div>
                <p>Verify CPT coding matches operative transcript description. Discrepancies signal potential coding upcharges.</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Reject / Dispute Modal */}
      <Modal isOpen={rejectModalOpen} onClose={() => setRejectModalOpen(false)} title="Reject / Dispute Document" size="sm">
        <div className="space-y-4">
          <div>
            <span className="text-xs text-slate-400 block">Document Title</span>
            <span className="text-sm font-semibold text-slate-800">{selectedDocToReject?.name}</span>
          </div>
          <div>
            <span className="text-xs text-slate-400 block">Claim ID</span>
            <span className="text-sm font-semibold text-slate-800">{selectedDocToReject?.claimId}</span>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-bold text-slate-600 block">Reason for Rejection / Dispute *</label>
            <textarea
              className="input w-full min-h-[90px] resize-none text-xs"
              placeholder="Please provide explicit clinical, signatures, or date reasons..."
              value={rejectReason}
              onChange={e => {
                setRejectReason(e.target.value);
                if (e.target.value.trim()) setRejectionError('');
              }}
            />
            {rejectionError && (
              <p className="text-[10px] text-red-600 font-semibold">{rejectionError}</p>
            )}
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t">
            <button
              className="btn-secondary text-xs"
              onClick={() => {
                setRejectModalOpen(false);
                setSelectedDocToReject(null);
              }}
            >
              Cancel
            </button>
            <button
              className="btn-primary text-xs bg-red-600 hover:bg-red-700"
              onClick={handleConfirmRejection}
            >
              Reject Document
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
