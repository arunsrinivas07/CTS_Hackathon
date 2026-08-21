import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  CheckCircle, AlertTriangle, Clock, Eye, FileText, Search,
  Download, Send, HelpCircle, ShieldAlert, Sparkles
} from 'lucide-react';
import PageHeader from '../../components/ui/PageHeader';
import Badge from '../../components/ui/Badge';
import Modal from '../../components/ui/Modal';
import {
  documents as mockDocuments,
  claims as mockClaims,
  investigations as mockInvestigations
} from '../../data/mockData';

export default function DocumentVerification() {
  const { claimId } = useParams();

  // Local state synced with localStorage
  const [documents, setDocuments] = useState(() => {
    const saved = localStorage.getItem('cg_documents');
    return saved ? JSON.parse(saved) : mockDocuments;
  });

  const [claims] = useState(() => {
    const saved = localStorage.getItem('cg_claims');
    return saved ? JSON.parse(saved) : mockClaims;
  });

  useEffect(() => {
    localStorage.setItem('cg_documents', JSON.stringify(documents));
  }, [documents]);

  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');

  // Modal state for rejection
  const [rejectModalOpen, setRejectModalOpen] = useState(false);
  const [selectedDocToReject, setSelectedDocToReject] = useState(null);
  const [rejectReason, setRejectReason] = useState('');
  const [rejectionError, setRejectionError] = useState('');
  const [feedbackMessage, setFeedbackMessage] = useState('');

  // Send request form states
  const [targetClaimId, setTargetClaimId] = useState(claimId || claims[0]?.id || '');
  const [requiredDoc, setRequiredDoc] = useState('');
  const [investigativeNotes, setInvestigativeNotes] = useState('');
  const [requestFeedback, setRequestFeedback] = useState('');
  const [formErrors, setFormErrors] = useState({});

  // Filter documents
  const filtered = documents.filter(d => {
    // If claimId parameter is present, filter for that claim's documents primarily
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

  const handleConfirmRejection = () => {
    if (!rejectReason.trim()) {
      setRejectionError('Reason for rejection/dispute is required.');
      return;
    }

    setDocuments(prev => prev.map(d => {
      if (d.id === selectedDocToReject.id) {
        return { ...d, status: 'rejected', rejectionReason: rejectReason };
      }
      return d;
    }));

    setRejectModalOpen(false);
    setFeedbackMessage(`Document "${selectedDocToReject.name}" rejected.`);
    setTimeout(() => setFeedbackMessage(''), 4000);
  };

  const handleVerifyAccept = (docId) => {
    setDocuments(prev => prev.map(d => {
      if (d.id === docId) {
        return { ...d, status: 'verified', rejectionReason: undefined };
      }
      return d;
    }));
    setFeedbackMessage('Document verified and accepted.');
    setTimeout(() => setFeedbackMessage(''), 4000);
  };

  // Submit request to provider
  const handleTransmitRequest = (e) => {
    e.preventDefault();
    const errors = {};
    if (!targetClaimId) errors.targetClaim = 'Target claim is required.';
    if (!requiredDoc.trim()) errors.requiredDoc = 'Required document field is required.';

    if (Object.keys(errors).length > 0) {
      setFormErrors(errors);
      return;
    }

    setFormErrors({});
    setRequestFeedback(`Formal document request for ${requiredDoc} sent to the provider.`);
    setTimeout(() => setRequestFeedback(''), 4000);

    // Clear form
    setRequiredDoc('');
    setInvestigativeNotes('');
  };

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
        <select
          className="select w-full sm:w-40 text-xs"
          value={statusFilter}
          onChange={e => setStatusFilter(e.target.value)}
        >
          <option value="all">All Statuses</option>
          <option value="verified">Verified</option>
          <option value="under_review">Under Review</option>
          <option value="flagged">Flagged</option>
          <option value="rejected">Rejected</option>
        </select>
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
                const docClaim = claims.find(c => c.id === doc.claimId);
                return (
                  <div
                    key={doc.id}
                    className={`card p-5 space-y-4 transition-all hover:shadow-md border-l-4 ${
                      doc.status === 'verified'
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
                          to={`/investigations/${doc.claimId}`}
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
                        Uploaded by <strong className="text-slate-700">{docClaim?.provider || 'Provider'}</strong> for {docClaim?.patient || 'Member'} · {doc.uploadedDate} ({doc.size})
                      </p>
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
              <div className="space-y-1">
                <label className="text-xs font-bold text-slate-600 block">Target Claim *</label>
                <select
                  className="select text-xs py-2"
                  value={targetClaimId}
                  onChange={e => setTargetClaimId(e.target.value)}
                >
                  {claims.map(c => (
                    <option key={c.id} value={c.id}>
                      {c.id} - {c.provider} (${c.amount.toLocaleString()})
                    </option>
                  ))}
                </select>
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
