import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  FileText, Clock, CheckCircle, User, DollarSign, Tag,
  AlertTriangle, Check, X, ChevronDown, ChevronUp, Download,
  ExternalLink, BarChart3, TrendingUp, HelpCircle, Briefcase, FilePlus
} from 'lucide-react';
import PageHeader from '../../components/ui/PageHeader';
import Badge from '../../components/ui/Badge';
import Modal from '../../components/ui/Modal';
import {
  investigations as mockInvestigations,
  claims as mockClaims,
  documents as mockDocuments,
  providers as mockProviders
} from '../../data/mockData';

export default function CaseDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('overview');

  // Local state initialized from mock data / localStorage
  const [investigations, setInvestigations] = useState(() => {
    const saved = localStorage.getItem('cg_investigations');
    return saved ? JSON.parse(saved) : mockInvestigations;
  });

  const [claims, setClaims] = useState(() => {
    const saved = localStorage.getItem('cg_claims');
    return saved ? JSON.parse(saved) : mockClaims;
  });

  const [documents, setDocuments] = useState(() => {
    const saved = localStorage.getItem('cg_documents');
    return saved ? JSON.parse(saved) : mockDocuments;
  });

  // Sync state to localStorage whenever it changes
  useEffect(() => {
    localStorage.setItem('cg_investigations', JSON.stringify(investigations));
  }, [investigations]);

  useEffect(() => {
    localStorage.setItem('cg_claims', JSON.stringify(claims));
  }, [claims]);

  useEffect(() => {
    localStorage.setItem('cg_documents', JSON.stringify(documents));
  }, [documents]);

  // Find relevant investigation and claim
  const inv = investigations.find(i => i.id === id || i.claimId === id) || investigations[0];
  const claim = claims.find(c => c.id === inv.claimId);
  const provider = mockProviders.find(p => p.id === inv.providerId) || mockProviders[0];
  const invDocs = documents.filter(d => d.claimId === inv.claimId);

  // Modal states for rejection
  const [rejectModalOpen, setRejectModalOpen] = useState(false);
  const [selectedDocToReject, setSelectedDocToReject] = useState(null);
  const [rejectReason, setRejectReason] = useState('');
  const [rejectionError, setRejectionError] = useState('');
  const [feedbackMessage, setFeedbackMessage] = useState('');

  // Decision tab states
  const [decision, setDecision] = useState(inv.decision || '');
  const [notes, setNotes] = useState(inv.investigatorNotes || '');
  const [reviewedEvidences, setReviewedEvidences] = useState(() => {
    return inv.reviewedEvidences || {
      claimDetails: false,
      supportingDocs: false,
      providerHistory: false,
      billingComparison: false,
      evidenceObtained: false,
      findingsReviewed: false,
    };
  });
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Decision history state simulation
  const [decisionHistory, setDecisionHistory] = useState(() => {
    const saved = localStorage.getItem(`cg_decision_history_${inv.id}`);
    return saved ? JSON.parse(saved) : [
      {
        date: '2024-07-15 10:20',
        investigator: 'System Auditor',
        decision: 'route_review',
        reason: 'Automated screening flagged claim for regional cost outlier deviations.',
        status: 'under_review'
      }
    ];
  });

  useEffect(() => {
    localStorage.setItem(`cg_decision_history_${inv.id}`, JSON.stringify(decisionHistory));
  }, [decisionHistory, inv.id]);

  const tabs = [
    { id: 'overview', label: 'Case Overview' },
    { id: 'findings', label: 'Investigation Findings' },
    { id: 'explainability', label: 'Explainability' },
    { id: 'provider', label: 'Provider Analysis' },
    { id: 'documents', label: 'Documents & Evidence' },
    { id: 'decision', label: 'Investigator Decision & Notes' }
  ];

  // Document Rejection
  const handleOpenRejectModal = (doc) => {
    setSelectedDocToReject(doc);
    setRejectReason('');
    setRejectionError('');
    setRejectModalOpen(true);
  };

  const handleConfirmRejection = () => {
    if (!rejectReason.trim()) {
      setRejectionError('Reason for rejection is required.');
      return;
    }

    setDocuments(prev => prev.map(d => {
      if (d.id === selectedDocToReject.id) {
        return { ...d, status: 'rejected', rejectionReason: rejectReason };
      }
      return d;
    }));

    setRejectModalOpen(false);
    setFeedbackMessage(`Document "${selectedDocToReject.name}" rejected successfully.`);
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

  // Save Decision
  const handleSaveDecision = () => {
    setInvestigations(prev => prev.map(i => {
      if (i.id === inv.id) {
        return {
          ...i,
          status: decision === 'clear' ? 'resolved' : 'in_progress',
          decision: decision,
          investigatorNotes: notes,
          reviewedEvidences: reviewedEvidences,
          decisionSavedAt: new Date().toLocaleString(),
          decisionInvestigator: 'Ram Patel'
        };
      }
      return i;
    }));

    // Update claim status based on decision
    setClaims(prev => prev.map(c => {
      if (c.id === inv.claimId) {
        let newStatus = c.status;
        if (decision === 'clear') newStatus = 'approved';
        else if (decision === 'suspicious') newStatus = 'flagged';
        else if (decision === 'escalate') newStatus = 'under_review';
        return { ...c, status: newStatus };
      }
      return c;
    }));

    // Append to decision history
    const historyItem = {
      date: new Date().toLocaleString(),
      investigator: 'Ram Patel',
      decision: decision,
      reason: notes || 'No comment provided.',
      status: decision === 'clear' ? 'resolved' : 'under_review'
    };
    setDecisionHistory(prev => [historyItem, ...prev]);

    setSaveSuccess(true);
    setTimeout(() => setSaveSuccess(false), 4000);
  };

  // Document Request Action Helper
  const handleRequestEvidenceAction = (docType) => {
    // Navigate to DocumentVerification with current claimId filter, and prefill details where supported
    navigate(`/investigator/documents/${inv.claimId}?requestDoc=${encodeURIComponent(docType)}`);
  };

  // Evidence Request Package Generator
  const handleGenerateEvidencePackage = () => {
    const reportText = `CLAIMGUARD AI EVIDENCE REQUEST PACKAGE
=============================================
CLAIM ID: ${inv.claimId}
HEALTHCARE PROVIDER: ${provider.name}
INVESTIGATION REASON: Outlier procedure cost and clinical timeline conflicts.
REQUESTED DOCUMENTS:
- Detailed Physician Progress Notes (Priority: High)
- Laboratory / Diagnostic Reports (Priority: High)
- Pre-Authorization Documentation (Priority: Medium)

DATE OF REQUEST: ${new Date().toLocaleDateString()}
RECOMMENDED RESPONSE DATE: ${new Date(Date.now() + 14 * 24 * 60 * 60 * 1000).toLocaleDateString()}
---------------------------------------------
Please transmit these documents immediately to prevent payment delays.`;

    const blob = new Blob([reportText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `Evidence_Request_Package_${inv.claimId}.txt`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    setFeedbackMessage('Evidence request package generated and downloaded.');
    setTimeout(() => setFeedbackMessage(''), 4500);
  };

  if (!inv) {
    return <div className="p-5 text-center text-slate-500">Investigation not found.</div>;
  }

  // Count document states
  const docCounts = {
    total: invDocs.length,
    verified: invDocs.filter(d => d.status === 'verified').length,
    flagged: invDocs.filter(d => d.status === 'flagged' || d.status === 'rejected').length,
    under_review: invDocs.filter(d => d.status === 'under_review').length,
    missing: 3, // outstanding required documents
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <PageHeader
        title="Investigation Workspace"
        subtitle={`Workspace for Case ID: ${inv.id} · Claim ID: ${inv.claimId}`}
        actions={
          <div className="flex gap-2">
            <button className="btn-secondary text-xs" onClick={() => navigate('/investigator/queue')}>
              Back to Queue
            </button>
          </div>
        }
      />

      {/* Feedback Banner */}
      {feedbackMessage && (
        <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 px-4 py-3 rounded-xl flex items-center gap-2 text-sm animate-fade-in shadow-sm">
          <CheckCircle size={16} className="text-emerald-600" />
          {feedbackMessage}
        </div>
      )}

      {/* ─── Premium Workspace Header Banner (Jargon-free) ─── */}
      <div className="rounded-2xl p-6 text-white bg-gradient-to-r from-rose-700 to-rose-900 shadow-xl border border-rose-800 relative overflow-hidden">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
          {/* Priority Block */}
          <div className="lg:col-span-3 flex flex-col items-center justify-center border-r border-rose-500/30 pr-0 lg:pr-6">
            <span className="text-[10px] uppercase tracking-wider font-semibold text-rose-300">Priority Level</span>
            <span className={`text-2xl font-black px-5 py-2 rounded-xl mt-2 uppercase tracking-wide border shadow-sm ${
              inv.priority === 'critical' ? 'bg-red-600 border-red-400 text-white' :
              inv.priority === 'high' ? 'bg-orange-600 border-orange-400 text-white' :
              inv.priority === 'medium' ? 'bg-amber-500 border-amber-300 text-white' :
              'bg-slate-500 border-slate-300 text-white'
            }`}>
              {inv.priority}
            </span>
          </div>

          {/* Central Claim & Patient Meta */}
          <div className="lg:col-span-5 space-y-2">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-rose-200 bg-rose-800/60 px-2 py-0.5 rounded">Claim Identifier</span>
              <span className="font-mono text-lg font-bold text-white">#{inv.claimId}</span>
            </div>
            <h2 className="text-2xl font-bold text-white">{provider.name}</h2>
            <div className="space-y-1 text-sm text-rose-100">
              <p><strong className="text-white">Patient Member:</strong> {claim?.patient || 'N/A'} ({claim?.patientId || 'N/A'})</p>
              <p><strong className="text-white">Review Classification:</strong> Potential Overbilling Scheme (Unconfirmed)</p>
            </div>
          </div>

          {/* Right Meta Column */}
          <div className="lg:col-span-4 space-y-3 lg:pl-4">
            <div className="space-y-1.5">
              <div className="flex justify-between items-center text-xs text-rose-200">
                <span>Financial Exposure:</span>
                <span className="font-bold text-white text-sm">${inv.amount?.toLocaleString()}</span>
              </div>
              <div className="flex justify-between items-center text-xs text-rose-200">
                <span>Investigation Status:</span>
                <span className="font-semibold text-amber-200 capitalize">{inv.status.replace('_', ' ')}</span>
              </div>
              <div className="flex justify-between items-center text-xs text-rose-200">
                <span>Assigned Investigator:</span>
                <span className="font-semibold text-white">{inv.investigatorName || 'Ram Patel'}</span>
              </div>
            </div>

            <div className="pt-2 border-t border-rose-500/30 flex justify-end">
              <button onClick={() => setActiveTab('decision')} className="btn-brown record-decision-btn text-xs py-2 px-4 shadow-md">
                Record Decision
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="border-b border-slate-200">
        <div className="flex flex-wrap gap-1">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-3 text-sm font-semibold border-b-2 transition-all ${
                activeTab === tab.id
                  ? 'border-rose-600 text-rose-600 font-bold bg-rose-50/50 rounded-t-lg'
                  : 'border-transparent text-slate-500 hover:text-slate-700 hover:bg-slate-50'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* TAB CONTENT */}

      {/* 1. CASE OVERVIEW */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
            {/* Claim Information */}
            <div className="card p-5 lg:col-span-2 space-y-4">
              <h3 className="section-title border-b pb-2 flex items-center gap-1.5">
                <FileText size={16} className="text-rose-500" />
                Claim Information
              </h3>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                {[
                  ['Claim ID', inv.claimId],
                  ['Investigation ID', inv.id],
                  ['Provider', inv.provider],
                  ['Patient Member', claim?.patient || 'N/A'],
                  ['Claim Type', claim?.type || 'N/A'],
                  ['Diagnosis', claim?.diagnosis || 'N/A'],
                  ['ICD Code', claim?.icdCode || 'N/A'],
                  ['Date of Service', claim?.date || 'N/A'],
                  ['Claim Amount', `$${inv.amount.toLocaleString()}`],
                  ['Assigned Investigator', inv.investigatorName || 'Ram Patel'],
                  ['Current Status', <Badge status={inv.status} key="st" />],
                  ['Priority Level', <Badge status={inv.priority} key="pr" />]
                ].map(([k, v]) => (
                  <div key={typeof k === 'string' ? k : 'meta'}>
                    <span className="text-xs text-slate-400 block mb-0.5">{k}</span>
                    <span className="text-sm font-semibold text-slate-800">{v}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Evidence Inventory Summary */}
            <div className="card p-5 space-y-4">
              <h3 className="section-title border-b pb-2 flex items-center gap-1.5">
                <Briefcase size={16} className="text-rose-500" />
                Evidence Summary
              </h3>
              <div className="grid grid-cols-2 gap-3 text-center">
                <div className="p-3 bg-slate-50 border rounded-xl">
                  <span className="text-2xl font-bold text-slate-800">{docCounts.total}</span>
                  <span className="text-[10px] text-slate-400 block uppercase font-bold mt-1">Total Docs</span>
                </div>
                <div className="p-3 bg-emerald-50 border border-emerald-100 rounded-xl">
                  <span className="text-2xl font-bold text-emerald-700">{docCounts.verified}</span>
                  <span className="text-[10px] text-emerald-600 block uppercase font-bold mt-1">Verified</span>
                </div>
                <div className="p-3 bg-amber-50 border border-amber-100 rounded-xl">
                  <span className="text-2xl font-bold text-amber-700">{docCounts.under_review}</span>
                  <span className="text-[10px] text-amber-600 block uppercase font-bold mt-1">Under Review</span>
                </div>
                <div className="p-3 bg-rose-50 border border-rose-100 rounded-xl">
                  <span className="text-2xl font-bold text-rose-700">{docCounts.flagged}</span>
                  <span className="text-[10px] text-rose-600 block uppercase font-bold mt-1">Flagged/Rejected</span>
                </div>
              </div>
              <div className="pt-2 text-center text-xs text-slate-500">
                Outstanding Evidence Requests: <strong className="text-red-600">{docCounts.missing} Required Documents</strong>
              </div>
            </div>
          </div>

          {/* Investigation Summary & Routed Rationale */}
          <div className="card p-5 space-y-3">
            <h3 className="section-title text-slate-800 flex items-center gap-1.5">
              <AlertTriangle size={16} className="text-amber-500" />
              Investigation Summary
            </h3>
            <p className="text-sm text-slate-600 leading-relaxed bg-slate-50 p-4 border rounded-xl">
              Potential billing irregularities were identified in this claim. The billed amount for the procedure is substantially higher than comparable regional claims, and supporting documentation does not currently provide sufficient clinical justification.
            </p>
          </div>

          {/* Risk Indicators (Translated to investigator terms) */}
          <div className="card p-5">
            <h3 className="section-title mb-4">Risk Indicators</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {[
                {
                  title: 'Unusually High Procedure Charge',
                  observed: 'Billed amount of $4,000 for procedure code CPT 80307.',
                  why: 'Comparable regional claims typically fall within a substantially lower range.',
                  evidence: 'Regional billing reference logs and provider claims catalogs.'
                },
                {
                  title: 'Documentation Gap',
                  observed: 'Operative reports do not contain details supporting specialized procedure tiers.',
                  why: 'Insufficient documentation impairs validation of treatment complexity.',
                  evidence: 'Submitted Operative Report (DOC-003).'
                },
                {
                  title: 'Possible Duplicate Billing',
                  observed: 'Similar procedural profiles billed twice in duplicate windows.',
                  why: 'Double billing claims inflate facility reimbursements.',
                  evidence: 'Provider claims history indexes.'
                },
                {
                  title: 'Inconsistent Clinical Dates',
                  observed: 'Claim reports service date July 12; admission intakes report intake on July 10.',
                  why: 'Service timelines must align to justify billing code validation.',
                  evidence: 'Clinical Admission Records (DOC-002).'
                }
              ].map(ind => (
                <div key={ind.title} className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 space-y-2">
                  <h4 className="text-sm font-bold text-slate-800 flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-red-500" />
                    {ind.title}
                  </h4>
                  <div className="grid grid-cols-1 gap-1.5 text-xs text-slate-600">
                    <p><strong>Observed:</strong> {ind.observed}</p>
                    <p><strong>Why it matters:</strong> {ind.why}</p>
                    <p><strong>Supporting evidence:</strong> {ind.evidence}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* 2. INVESTIGATION FINDINGS */}
      {activeTab === 'findings' && (
        <div className="space-y-6">
          <div className="card p-5 bg-slate-50 border space-y-3">
            <h3 className="text-base font-bold text-slate-800">Investigation Summary</h3>
            <p className="text-xs text-slate-400">Evidence-based findings identified during automated claim review.</p>
            <p className="text-sm text-slate-700 leading-relaxed bg-white p-4 border rounded-xl">
              The claim contains several indicators that require investigator review. The procedure charge is significantly above the observed regional range, supporting documentation is incomplete, and some clinical dates appear inconsistent.
            </p>
          </div>

          {/* Key Findings */}
          <div className="card p-5 space-y-4">
            <h3 className="section-title border-b pb-2">Key Findings</h3>
            <div className="space-y-4">
              {[
                {
                  title: 'Procedure charge is substantially above comparable claims.',
                  observed: 'Claimed amount: $4,000 | Regional median range: approximately $350–$420.',
                  why: 'The charge is significantly outside the observed regional billing pattern.',
                  evidence: 'Regional Fee Schedule & Provider Billing History',
                  status: 'Supported'
                },
                {
                  title: 'Clinical dates appear inconsistent.',
                  observed: 'Claim service date: July 12 | Intake record reports admission on July 10.',
                  why: 'The discrepancy should be verified against the patient\'s clinical records.',
                  evidence: 'Hospital Admission Record (DOC-002)',
                  status: 'Requires Verification'
                },
                {
                  title: 'Supporting documentation is incomplete.',
                  observed: 'Operative documentation does not clearly explain the unusually high billed amount.',
                  why: 'Additional clinical documentation may be required before the claim can be resolved.',
                  evidence: 'Operative Report (DOC-003)',
                  status: 'Evidence Requested'
                }
              ].map((find, idx) => (
                <div key={idx} className="p-4 rounded-xl border border-slate-100 bg-slate-50/50 space-y-2">
                  <div className="flex justify-between items-center flex-wrap gap-2">
                    <h4 className="text-xs font-bold text-slate-800">{find.title}</h4>
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                      find.status === 'Supported' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' :
                      find.status === 'Requires Verification' ? 'bg-amber-50 text-amber-700 border-amber-200' :
                      'bg-rose-50 text-rose-700 border-rose-200'
                    }`}>
                      {find.status}
                    </span>
                  </div>
                  <div className="text-xs text-slate-600 space-y-1">
                    <p><strong>Observed:</strong> {find.observed}</p>
                    <p><strong>Why it matters:</strong> {find.why}</p>
                    <p><strong>Supporting Evidence:</strong> {find.evidence}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Investigator Insight Panel */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            <div className="card p-5 space-y-3">
              <h3 className="section-title text-rose-900">Investigator Insight</h3>
              <p className="text-sm text-slate-600 leading-relaxed bg-rose-50/50 p-4 border border-rose-100 rounded-xl">
                Based on the available claim, provider history, and supporting documentation, this case warrants further review. The strongest concerns are the unusually high procedure charge and insufficient supporting documentation.
              </p>
            </div>

            <div className="card p-5 space-y-3">
              <h3 className="section-title text-slate-800">Recommended Next Steps</h3>
              <ol className="text-xs text-slate-700 space-y-2 list-decimal pl-5">
                <li>Request detailed physician progress notes.</li>
                <li>Request supporting laboratory/diagnostic reports.</li>
                <li>Verify the procedure charge against the applicable regional schedule.</li>
                <li>Confirm the conflicting admission and service dates.</li>
                <li>Review provider billing history for similar claims.</li>
              </ol>
            </div>
          </div>

          {/* Evidence Mapping Table */}
          <div className="card p-5">
            <h3 className="section-title mb-4">Evidence Mapping</h3>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr>
                    {['Finding', 'Supporting Evidence', 'Source Document', 'Status', 'Priority'].map(h => (
                      <th key={h} className="table-header">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {[
                    { find: 'Procedure charge unusually high', evidence: '$4,000 vs regional range $350–$420', source: 'Regional Fee Schedule', status: 'Supported', priority: 'high' },
                    { find: 'Clinical date mismatch', evidence: 'Service date differs from admission record', source: 'Admission Record', status: 'Requires Verification', priority: 'medium' },
                    { find: 'Missing clinical justification', evidence: 'Operative notes do not explain charge', source: 'Operative Report', status: 'Evidence Needed', priority: 'high' }
                  ].map((row, idx) => (
                    <tr key={idx} className="table-row">
                      <td className="table-cell font-medium text-slate-800">{row.find}</td>
                      <td className="table-cell text-slate-600">{row.evidence}</td>
                      <td className="table-cell text-slate-500 font-semibold">{row.source}</td>
                      <td className="table-cell">
                        <Badge status={row.status === 'Supported' ? 'verified' : row.status === 'Evidence Needed' ? 'open' : 'warning'} label={row.status} />
                      </td>
                      <td className="table-cell"><Badge status={row.priority} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* 3. EXPLAINABILITY */}
      {activeTab === 'explainability' && (
        <div className="space-y-6">
          <div className="card p-5 space-y-4">
            <h3 className="section-title">Explainability</h3>
            <p className="text-xs text-slate-500 -mt-2">Why this claim requires additional review.</p>

            <div className="space-y-4 pt-2">
              {[
                {
                  factor: 'HIGH CLAIM AMOUNT',
                  impact: 'high',
                  explanation: 'The billed amount is substantially higher than comparable claims for the same procedure.',
                  evidence: 'Regional billing comparison.'
                },
                {
                  factor: 'UNUSUAL BILLING PATTERN',
                  impact: 'high',
                  explanation: 'The provider\'s billing pattern for this procedure differs materially from comparable claims.',
                  evidence: 'Provider historical billing records.'
                },
                {
                  factor: 'DOCUMENTATION CONFLICT',
                  impact: 'medium',
                  explanation: 'Clinical documentation contains information that does not fully align with the submitted claim.',
                  evidence: 'Admission and claim records.'
                },
                {
                  factor: 'POSSIBLE DUPLICATE BILLING',
                  impact: 'medium',
                  explanation: 'Similar billing codes appear to have been submitted separately within a period where bundled billing may normally apply.',
                  evidence: 'Claim history and billing guidelines.'
                }
              ].map(x => (
                <div key={x.factor} className="p-4 rounded-xl border border-slate-100 bg-slate-50/50 space-y-2">
                  <div className="flex justify-between items-center flex-wrap gap-2">
                    <span className="text-xs font-bold text-slate-800">{x.factor}</span>
                    <Badge status={x.impact} label={`Impact: ${x.impact.toUpperCase()}`} />
                  </div>
                  <p className="text-xs text-slate-600">{x.explanation}</p>
                  <p className="text-xs text-slate-400 bg-white border px-3 py-1.5 rounded-lg">
                    <strong>Supporting Evidence:</strong> {x.evidence}
                  </p>
                </div>
              ))}
            </div>

            <div className="p-3.5 bg-rose-50 border border-rose-100 rounded-xl text-xs text-rose-800">
              This review isolates clinical indicators to justify billing anomalies. It does not independently establish fraud, but highlights items to guide investigator inspection.
            </div>
          </div>
        </div>
      )}

      {/* 4. PROVIDER ANALYSIS */}
      {activeTab === 'provider' && (
        <div className="space-y-6">
          {/* Provider profile */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
            <div className="card p-5 lg:col-span-1 space-y-4">
              <h3 className="section-title border-b pb-2">Provider Profile</h3>
              <div className="space-y-3 text-xs">
                {[
                  ['Provider Name', provider.name],
                  ['Provider ID', provider.id],
                  ['Facility Type', provider.type],
                  ['Location', provider.location],
                  ['Specialty', provider.specialties?.join(', ') || 'N/A'],
                  ['Network Status', 'In-Network'],
                  ['Active Since', provider.enrolledDate]
                ].map(([k, v]) => (
                  <div key={k}>
                    <span className="text-slate-400 block mb-0.5">{k}</span>
                    <span className="font-semibold text-slate-800">{v}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="card p-5 lg:col-span-2 space-y-4">
              <h3 className="section-title border-b pb-2">Historical Claims</h3>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
                <div className="p-3 bg-slate-50 border rounded-xl">
                  <span className="text-xl font-bold text-slate-800">{provider.totalClaims}</span>
                  <span className="text-[10px] text-slate-400 block uppercase font-bold mt-1">Total Claims</span>
                </div>
                <div className="p-3 bg-emerald-50 border border-emerald-100 rounded-xl">
                  <span className="text-xl font-bold text-emerald-700">{provider.approvedClaims}</span>
                  <span className="text-[10px] text-emerald-600 block uppercase font-bold mt-1">Approved</span>
                </div>
                <div className="p-3 bg-amber-50 border border-amber-100 rounded-xl">
                  <span className="text-xl font-bold text-amber-700">{provider.flaggedClaims}</span>
                  <span className="text-[10px] text-amber-600 block uppercase font-bold mt-1">Flagged</span>
                </div>
                <div className="p-3 bg-rose-50 border border-rose-100 rounded-xl">
                  <span className="text-xl font-bold text-rose-700">{provider.rejectedClaims}</span>
                  <span className="text-[10px] text-rose-600 block uppercase font-bold mt-1">Rejected</span>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2 text-xs">
                <div>
                  <span className="text-slate-400 block">Total Billed Amount</span>
                  <span className="text-sm font-semibold text-slate-800">${provider.totalBilled?.toLocaleString()}</span>
                </div>
                <div>
                  <span className="text-slate-400 block">Average Claim Amount</span>
                  <span className="text-sm font-semibold text-slate-800">$32,560</span>
                </div>
                <div>
                  <span className="text-slate-400 block">Average Processing Time</span>
                  <span className="text-sm font-semibold text-slate-800">8.4 Days</span>
                </div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            {/* Historical investigation pattern */}
            <div className="card p-5 space-y-4">
              <h3 className="section-title border-b pb-2">Historical Investigation Pattern</h3>
              <div className="grid grid-cols-2 gap-4 text-xs">
                {[
                  ['Previous Investigations', '24 Cases'],
                  ['Confirmed Issues', '4 Cases'],
                  ['Cleared Investigations', '18 Cases'],
                  ['Open Investigations', '2 Cases'],
                  ['Outstanding Evidence Requests', '6 requests']
                ].map(([k, v]) => (
                  <div key={k} className="flex justify-between items-center py-1.5 border-b border-slate-100">
                    <span className="text-slate-500">{k}</span>
                    <span className="font-semibold text-slate-800">{v}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Financial exposure */}
            <div className="card p-5 space-y-4">
              <h3 className="section-title border-b pb-2">Financial Exposure</h3>
              <div className="grid grid-cols-2 gap-4 text-xs">
                {[
                  ['Current Claim Exposure', `$${inv.amount.toLocaleString()}`],
                  ['Open Claims exposure', '$139,950'],
                  ['Historical Flagged Amount', '$480,000'],
                  ['Potential Recovery Exposure', '$112,000']
                ].map(([k, v]) => (
                  <div key={k} className="flex justify-between items-center py-1.5 border-b border-slate-100">
                    <span className="text-slate-500">{k}</span>
                    <span className="font-semibold text-slate-800">{v}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Billing Behavior & Peer Comparison */}
          <div className="card p-5 space-y-4">
            <h3 className="section-title border-b pb-2">Billing Behavior & Peer Comparison</h3>
            <div className="space-y-3 text-xs text-slate-600">
              <p>Provider\'s average charge for Urine Drug Screen (CPT 80307) is approximately <strong>11.1x</strong> the regional average. Comparable regional claims cluster at $380, while this facility consistently bills $4,000.</p>
              <div className="p-3 bg-slate-50 border rounded-xl flex justify-between items-center">
                <span>Billing Frequency percentile:</span>
                <strong className="text-red-600">99.8th percentile in Region</strong>
              </div>
              <div className="p-3 bg-slate-50 border rounded-xl flex justify-between items-center">
                <span>Duplicate billing occurrences:</span>
                <strong className="text-amber-600">14 potential cluster overlaps (active review)</strong>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 5. DOCUMENTS & EVIDENCE */}
      {activeTab === 'documents' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Left side document table */}
            <div className="lg:col-span-8 space-y-5">
              <div className="flex justify-between items-center flex-wrap gap-2 pb-2 border-b">
                <h3 className="text-lg font-bold text-slate-800">Associated Claim Documents</h3>
                <Link
                  to={`/investigator/documents/${inv.claimId}`}
                  className="btn-primary text-[11px] py-1.5 px-3 flex items-center gap-1.5 bg-green-600 hover:bg-green-700"
                >
                  <ExternalLink size={12} />
                  Open Document Verification
                </Link>
              </div>

              {/* Counts */}
              <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 text-center text-xs">
                {[
                  ['Total Documents', docCounts.total],
                  ['Verified', docCounts.verified],
                  ['Under Review', docCounts.under_review],
                  ['Flagged / Rejected', docCounts.flagged],
                  ['Missing / Requested', docCounts.missing]
                ].map(([k, v]) => (
                  <div key={k.toString()} className="p-2 border rounded-xl bg-slate-50">
                    <span className="text-slate-400 block text-[9px] uppercase font-bold">{k}</span>
                    <span className="text-base font-bold text-slate-700 mt-0.5 block">{v}</span>
                  </div>
                ))}
              </div>

              {/* Table */}
              <div className="card overflow-hidden">
                <table className="w-full">
                  <thead>
                    <tr>
                      {['Document Name', 'Document Type', 'Upload Date', 'Status', 'OCR Result', 'Authenticity', 'Actions'].map(h => (
                        <th key={h} className="table-header">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {invDocs.map(doc => (
                      <tr key={doc.id} className="table-row">
                        <td className="table-cell font-medium text-slate-800">
                          <div className="flex items-center gap-2">
                            <FileText size={14} className="text-rose-500 flex-shrink-0" />
                            <span>{doc.name}</span>
                          </div>
                        </td>
                        <td className="table-cell text-slate-500 text-xs">{doc.type}</td>
                        <td className="table-cell text-slate-500 text-xs">{doc.uploadedDate}</td>
                        <td className="table-cell">
                          <Badge status={doc.status} size="xs" />
                        </td>
                        <td className="table-cell text-xs text-slate-500">Passed (99.4%)</td>
                        <td className="table-cell text-xs text-slate-500">Valid Digital Stamp</td>
                        <td className="table-cell">
                          <div className="flex gap-1">
                            {doc.status === 'under_review' || doc.status === 'flagged' ? (
                              <>
                                <button className="btn-primary text-[10px] py-1 px-2 bg-emerald-600 hover:bg-emerald-700" onClick={() => handleVerifyAccept(doc.id)}>Accept</button>
                                <button className="btn-secondary text-[10px] py-1 px-2 border-red-200 text-red-600 hover:bg-red-50" onClick={() => handleOpenRejectModal(doc)}>Reject</button>
                              </>
                            ) : (
                              <button className="btn-secondary text-[10px] py-1 px-2" onClick={() => alert(`View details: ${doc.name}`)}>View</button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Right side Evidence Needed panel */}
            <div className="lg:col-span-4 space-y-4">
              <div className="card p-5 space-y-3">
                <div>
                  <h3 className="section-title text-slate-800">Evidence Needed</h3>
                  <p className="text-[10px] text-slate-400 mt-0.5 leading-snug">Additional evidence recommended to complete this investigation.</p>
                </div>

                <div className="space-y-3">
                  {[
                    {
                      priority: 'high',
                      title: 'Detailed Physician Progress Notes',
                      reason: 'Current documentation does not provide sufficient clinical justification for the billed procedure.'
                    },
                    {
                      priority: 'high',
                      title: 'Laboratory / Diagnostic Reports',
                      reason: 'Supporting diagnostic evidence is not currently available to validate medical necessity.'
                    },
                    {
                      priority: 'medium',
                      title: 'Pre-Authorization Documentation',
                      reason: 'No prior authorization documentation was found for this high-cost procedure.'
                    }
                  ].map((req, idx) => (
                    <div key={idx} className="p-3 border rounded-xl bg-slate-50 space-y-2 text-xs">
                      <div className="flex justify-between items-center">
                        <span className="font-bold text-slate-800 truncate block max-w-[160px]">{req.title}</span>
                        <Badge status={req.priority} size="xs" />
                      </div>
                      <p className="text-[11px] text-slate-500 leading-snug">{req.reason}</p>
                      <button
                        className="w-full btn-secondary text-[10px] py-1.5 justify-center flex items-center gap-1 border-rose-200 text-rose-700 hover:bg-rose-50"
                        onClick={() => handleRequestEvidenceAction(req.title)}
                      >
                        <FilePlus size={11} />
                        Request Evidence
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Evidence Request Package Generator */}
          <div className="card p-5 flex flex-col sm:flex-row items-center justify-between gap-4 border-t border-slate-100">
            <div className="text-xs space-y-1 max-w-xl text-center sm:text-left">
              <h4 className="font-bold text-slate-800">Investigation Evidence Summary</h4>
              <p className="text-slate-500">This investigation currently has 3 outstanding evidence requirements. Obtaining these documents may materially improve the ability to validate the claim.</p>
            </div>
            <button
              onClick={handleGenerateEvidencePackage}
              className="btn-primary text-xs py-2 px-5 flex items-center gap-1.5 bg-green-600 hover:bg-green-700 shadow-md"
            >
              <Download size={13} />
              Generate Evidence Request Package
            </button>
          </div>

          {/* Rejection modal */}
          <Modal isOpen={rejectModalOpen} onClose={() => setRejectModalOpen(false)} title="Reject / Dispute Document" size="sm">
            <div className="space-y-4">
              <div>
                <span className="text-xs text-slate-400 block">Document Title</span>
                <span className="text-sm font-semibold text-slate-800">{selectedDocToReject?.name}</span>
              </div>
              <div>
                <span className="text-xs text-slate-400 block">Claim ID</span>
                <span className="text-sm font-semibold text-slate-800">{inv.claimId}</span>
              </div>

              <div className="space-y-1">
                <label className="text-xs font-bold text-slate-600 block">Reason for Rejection / Dispute *</label>
                <textarea
                  className="input w-full min-h-[95px] resize-none text-xs"
                  placeholder="Provide clinical or billing discrepancy notes..."
                  value={rejectReason}
                  onChange={e => {
                    setRejectReason(e.target.value);
                    if (e.target.value.trim()) setRejectionError('');
                  }}
                />
                {rejectionError && <p className="text-[10px] text-red-600 font-bold">{rejectionError}</p>}
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t">
                <button className="btn-secondary text-xs" onClick={() => setRejectModalOpen(false)}>Cancel</button>
                <button className="btn-primary text-xs bg-red-600 hover:bg-red-700" onClick={handleConfirmRejection}>Reject Document</button>
              </div>
            </div>
          </Modal>
        </div>
      )}

      {/* 6. INVESTIGATOR DECISION & NOTES */}
      {activeTab === 'decision' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
            {/* Investigator Recommendation */}
            <div className="card p-5 lg:col-span-1 bg-slate-50 border space-y-4">
              <h3 className="section-title">Investigator Recommendation</h3>
              <div className="space-y-2 text-xs text-slate-600 leading-relaxed">
                <div className="flex items-center gap-1 text-red-700 font-bold">
                  <AlertTriangle size={13} />
                  <span>Flagged: Billing Outlier (CPT 80307)</span>
                </div>
                <p>The billed procedure charge ($4,000) exceeds comparable regional averages ($380) by +1005%.</p>
                <p className="font-semibold text-slate-800">Supportive Evidence Summary:</p>
                <ul className="list-disc pl-4 space-y-1">
                  <li>Fee Schedule mismatch</li>
                  <li>Inconsistent admission dates</li>
                  <li>Incomplete physician notes</li>
                </ul>
              </div>
            </div>

            {/* Investigator Form */}
            <div className="card p-5 lg:col-span-2 space-y-5">
              <h3 className="section-title">Final Decision Panel</h3>

              {saveSuccess && (
                <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 p-4 rounded-xl flex items-center gap-2 text-xs">
                  <CheckCircle size={14} className="text-emerald-600" />
                  Decision and notes successfully recorded. Status updated.
                </div>
              )}

              {/* Action selection */}
              <div className="space-y-2">
                <label className="label text-xs">A. Select Investigation Action</label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {[
                    { id: 'suspicious', title: 'Confirm Suspicious', desc: 'Confirm billing anomalies / hold reimbursement.' },
                    { id: 'more_evidence', title: 'Request More Evidence', desc: 'Dispatch formal documentation inquiry.' },
                    { id: 'clear', title: 'Clear / No Issue', desc: 'Approve claim for regular payment processing.' },
                    { id: 'escalate', title: 'Escalate Case', desc: 'Route directly to senior clinical audit board.' }
                  ].map(opt => (
                    <button
                      key={opt.id}
                      type="button"
                      onClick={() => setDecision(opt.id)}
                      className={`text-left p-3 rounded-xl border transition-all ${
                        decision === opt.id
                          ? 'border-rose-600 bg-rose-50/50 shadow-sm'
                          : 'border-slate-200 hover:bg-slate-50'
                      }`}
                    >
                      <span className="text-xs font-bold text-slate-800 block">{opt.title}</span>
                      <span className="text-[11px] text-slate-500 block mt-0.5">{opt.desc}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Evidence Review Checklists */}
              <div className="space-y-2">
                <label className="label text-xs">B. Evidence Review Checklist</label>
                <div className="grid grid-cols-2 gap-2">
                  {[
                    ['claimDetails', 'Claim details reviewed'],
                    ['supportingDocs', 'Supporting documents reviewed'],
                    ['providerHistory', 'Provider history reviewed'],
                    ['billingComparison', 'Billing comparison reviewed'],
                    ['evidenceObtained', 'Required evidence obtained'],
                    ['findingsReviewed', 'Investigation findings reviewed']
                  ].map(([key, label]) => (
                    <label key={key} className="flex items-center gap-2 text-xs text-slate-700 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={reviewedEvidences[key]}
                        onChange={e => setReviewedEvidences(prev => ({ ...prev, [key]: e.target.checked }))}
                        className="rounded border-slate-300 text-rose-600 focus:ring-rose-500"
                      />
                      <span>{label}</span>
                    </label>
                  ))}
                </div>
              </div>

              {/* Textarea */}
              <div className="space-y-1.5">
                <label className="label text-xs">C. Investigator Analysis Notes</label>
                <textarea
                  className="input min-h-[120px] resize-none text-xs leading-relaxed"
                  placeholder="Record your clinical rationale, findings, notes, and final recommendations here..."
                  value={notes}
                  onChange={e => setNotes(e.target.value)}
                />
              </div>

              <div className="flex justify-end pt-3 border-t">
                <button
                  onClick={handleSaveDecision}
                  className="btn-primary text-xs px-6 py-2.5 bg-green-600 hover:bg-green-700 shadow-md"
                >
                  Save Decision
                </button>
              </div>
            </div>
          </div>

          {/* Decision History Log */}
          <div className="card p-5 space-y-4">
            <h3 className="section-title border-b pb-2">Decision History</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr>
                    {['Date', 'Investigator', 'Decision Type', 'Notes / Reasons', 'Status'].map(h => (
                      <th key={h} className="table-header">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {decisionHistory.map((item, index) => (
                    <tr key={index} className="table-row">
                      <td className="table-cell font-mono text-[11px] text-slate-500">{item.date}</td>
                      <td className="table-cell font-semibold text-slate-700">{item.investigator}</td>
                      <td className="table-cell capitalize font-medium text-slate-800">{item.decision?.replace('_', ' ')}</td>
                      <td className="table-cell text-slate-600 max-w-[320px] truncate" title={item.reason}>{item.reason}</td>
                      <td className="table-cell">
                        <Badge status={item.status === 'resolved' ? 'resolved' : 'under_review'} label={item.status} size="xs" />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
