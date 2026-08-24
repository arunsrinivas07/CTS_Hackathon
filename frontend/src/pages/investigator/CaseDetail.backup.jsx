import React, { useState, useEffect, useContext, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { claimsAPI, mlAPI, investigationsAPI, providersAPI } from '../../services/api';
import { InvestigationContext } from '../../context/InvestigationContext';
import CopilotPanel from '../../components/investigator/CopilotPanel';
import {
  FileText, Briefcase, AlertTriangle, Play, CheckCircle, Clock,
  Search, ChevronRight, FileX, ShieldAlert, Activity, Database,
  BarChart2, BookOpen, Edit3, Save, User, Building2, Calendar,
  DollarSign, Stethoscope, Info, RefreshCw, ExternalLink
} from 'lucide-react';

// ─── Helpers ──────────────────────────────────────────────────────────────────
const fmt$ = (v) => {
  const n = parseFloat(v);
  if (isNaN(n)) return '—';
  return '$' + n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
};
const fmtDate = (v) => {
  if (!v) return '—';
  try { return new Date(v).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' }); }
  catch { return String(v); }
};
const riskColor = (score) => {
  if (score >= 75) return 'text-red-500';
  if (score >= 50) return 'text-amber-500';
  return 'text-emerald-500';
};
const riskBg = (level) => {
  const l = String(level).toUpperCase();
  if (l === 'CRITICAL') return 'bg-red-100 text-red-700';
  if (l === 'HIGH') return 'bg-orange-100 text-orange-700';
  if (l === 'MEDIUM') return 'bg-amber-100 text-amber-700';
  return 'bg-emerald-100 text-emerald-700';
};
const statusColor = (s) => {
  const upper = String(s || '').toUpperCase();
  if (upper === 'COMPLETED') return 'bg-emerald-100 text-emerald-700';
  if (upper === 'FAILED') return 'bg-red-100 text-red-700';
  if (upper === 'REQUIRES_HUMAN_REVIEW') return 'bg-amber-100 text-amber-800';
  if (upper === 'MAX_ITERATIONS_REACHED') return 'bg-orange-100 text-orange-700';
  if (['IN_PROGRESS', 'COUNTER_ANALYSIS', 'CRITIC_REVIEW'].includes(upper)) return 'bg-blue-100 text-blue-700';
  return 'bg-slate-100 text-slate-600';
};

const TABS = [
  { id: 'overview', label: 'Case Overview', icon: FileText },
  { id: 'trace', label: 'Agentic Trace', icon: Activity },
  { id: 'findings', label: 'Investigation Findings', icon: Search },
  { id: 'explainability', label: 'Explainability', icon: BarChart2 },
  { id: 'provider', label: 'Provider Analysis', icon: Building2 },
  { id: 'documents', label: 'Documents & Evidence', icon: BookOpen },
  { id: 'decision', label: 'Decision & Notes', icon: Edit3 },
];

// ─── Component ────────────────────────────────────────────────────────────────
export default function CaseDetail() {
  const { id } = useParams();           // claim_number from URL
  const navigate = useNavigate();
  const { user } = useAuth();
  const invCtx = useContext(InvestigationContext);

  const [activeTab, setActiveTab] = useState('overview');

  // Claim + ML state
  const [claimData, setClaimData]     = useState(null);
  const [mlPrediction, setMlPrediction] = useState(null);
  const [claimLoading, setClaimLoading] = useState(true);
  const [claimError, setClaimError]   = useState('');
  const [mlLoading, setMlLoading]     = useState(false);
  const [mlError, setMlError]         = useState('');

  // Agent investigation state
  const [invState, setInvState]       = useState(null);
  const [traceData, setTraceData]     = useState(null);
  const [invLoading, setInvLoading]   = useState(false);
  const [isPolling, setIsPolling]     = useState(false);
  const [dbClaimId, setDbClaimId]     = useState(null);

  // Decision tab state
  const [decisionNote, setDecisionNote] = useState('');
  const [decisionStatus, setDecisionStatus] = useState('pending_review');
  const [savingDecision, setSavingDecision] = useState(false);
  const [decisionSaved, setDecisionSaved] = useState(false);

  // ── Load claim by number, then ML score ───────────────────────────────────
  useEffect(() => {
    if (!id) return;
    let mounted = true;
    setClaimLoading(true);
    setClaimError('');
    setMlError('');
    setClaimData(null);
    setMlPrediction(null);

    // Fetch all claims and find by claim_number
    claimsAPI.getAll({ limit: 200 })
      .then(claims => {
        const list = Array.isArray(claims) ? claims : (claims?.items || []);
        const found = list.find(c => String(c.claim_number) === String(id));
        if (!found) throw new Error(`Claim "${id}" not found in database.`);
        if (!mounted) return;
        setClaimData(found);
        setDbClaimId(found.id);
        // Push into context only if context is available
        if (invCtx?.setActiveClaim) invCtx.setActiveClaim(id, found);

        // Score claim via ML
        setMlLoading(true);
        mlAPI.scoreClaim(found.id)
          .then(res => { if (mounted) setMlPrediction(res); })
          .catch(err => {
            console.warn('ML scoring error:', err);
            if (mounted) setMlError('ML risk scoring unavailable. Showing any cached scores from database.');
          })
          .finally(() => { if (mounted) setMlLoading(false); });
      })
      .catch(err => {
        if (mounted) {
          setClaimError(err.message || 'Failed to load claim data.');
          setClaimLoading(false);
        }
      })
      .finally(() => { if (mounted) setClaimLoading(false); });

    return () => { mounted = false; };
  }, [id]);

  // ── Polling for investigation updates ────────────────────────────────────
  useEffect(() => {
    if (!isPolling || !invState?.investigation_id) return;
    const interval = setInterval(async () => {
      try {
        const res = await investigationsAPI.getAgenticState(invState.investigation_id);
        setInvState(res);
        if (invCtx?.setActiveInvestigation) invCtx.setActiveInvestigation(res.investigation_id, res);
        const upper = String(res.status || '').toUpperCase();
        if (['COMPLETED', 'FAILED', 'REQUIRES_HUMAN_REVIEW', 'MAX_ITERATIONS_REACHED'].includes(upper)) {
          setIsPolling(false);
        }
      } catch (err) {
        console.error('Polling error:', err);
      }
      try {
        const trace = await investigationsAPI.getTrace(invState.investigation_id);
        setTraceData(trace);
      } catch { /* ignore */ }
    }, 3000);
    return () => clearInterval(interval);
  }, [isPolling, invState?.investigation_id]);

  // ── Start Investigation ───────────────────────────────────────────────────
  const startInvestigation = async () => {
    if (!dbClaimId || !claimData) return;
    setInvLoading(true);
    try {
      const hybridResult = mlPrediction?.hybrid_result || mlPrediction || {};
      const riskScore = hybridResult.final_risk_score !== undefined
        ? hybridResult.final_risk_score
        : (claimData?.risk_scores?.[0]
          ? (parseFloat(claimData.risk_scores[0].overall_score) / 100)
          : 0.0);
      const riskLevel = hybridResult.final_risk_tier
        || String(claimData?.risk_scores?.[0]?.risk_level || 'LOW').toUpperCase();

      const rawFeatures = claimData?.raw_extracted_features || {};
      const providerNpi = claimData?.provider?.npi || String(claimData.provider_id);
      const providerName = claimData?.provider?.name || `Provider #${claimData.provider_id}`;
      const patientName = claimData?.patient
        ? `${claimData.patient.first_name} ${claimData.patient.last_name}`
        : `Patient #${claimData.patient_id}`;
      const diagnosis = rawFeatures.primary_diagnosis || rawFeatures.diagnosis || 'Unspecified';
      const procedure = rawFeatures.primary_procedure || rawFeatures.procedure || 'Unspecified';

      const shap = hybridResult.provider_evidence
        || hybridResult.claim_evidence
        || hybridResult.factors
        || [];

      const payload = {
        claim_id: id,
        claim_data: {
          claim_number: claimData.claim_number,
          claim_type: claimData.claim_type || 'Medical',
          claim_amount: parseFloat(claimData.total_billed_amount || 0),
          total_paid_amount: parseFloat(claimData.total_paid_amount || 0),
          service_date: String(claimData.service_date || ''),
          submission_date: String(claimData.submission_date || ''),
          status: claimData.status,
          provider_id: providerNpi,
          provider_name: providerName,
          patient_id: String(claimData.patient_id),
          patient_name: patientName,
          diagnosis,
          procedure,
          bene_id: claimData?.patient?.member_id || `PAT-${claimData.patient_id}`,
          state: claimData.state || '',
          diag_count: claimData.diag_count || 1,
          proc_count: claimData.proc_count || 1,
          line_count: claimData.line_count || 1,
          ...rawFeatures,
        },
        risk_score: riskScore,
        risk_level: riskLevel,
        shap_contributors: shap,
        detected_patterns: [],
        auto_run: false,
      };

      const res = await investigationsAPI.start(payload);
      setInvState(res);
      if (invCtx?.setActiveInvestigation) invCtx.setActiveInvestigation(res.investigation_id, res);
      setIsPolling(true);

      // Fire & forget run-to-completion
      investigationsAPI.run(res.investigation_id).catch(console.error);
    } catch (err) {
      console.error('Start investigation error:', err);
      alert(`Failed to start investigation: ${err.message}`);
    } finally {
      setInvLoading(false);
    }
  };

  // ── Derived display values ────────────────────────────────────────────────
  const hybridResult = mlPrediction?.hybrid_result || mlPrediction || {};
  const riskScoreRaw = hybridResult.final_risk_score !== undefined
    ? hybridResult.final_risk_score
    : (claimData?.risk_scores?.[0] ? parseFloat(claimData.risk_scores[0].overall_score) / 100 : null);
  const riskScore100 = riskScoreRaw !== null ? Math.round(riskScoreRaw * 100) : null;
  const riskLevel = hybridResult.final_risk_tier
    || String(claimData?.risk_scores?.[0]?.risk_level || '').toUpperCase()
    || null;

  const claimAmount = parseFloat(claimData?.total_billed_amount || 0);
  const paidAmount  = parseFloat(claimData?.total_paid_amount || 0);
  const serviceDate = claimData?.service_date;
  const providerName = claimData?.provider?.name
    || claimData?.provider?.facility_name
    || (claimData?.provider_id ? `Provider #${claimData.provider_id}` : 'Unknown Provider');
  const patientName = claimData?.patient
    ? `${claimData.patient.first_name} ${claimData.patient.last_name}`
    : `Patient #${claimData?.patient_id || '—'}`;
  const rawFeatures = claimData?.raw_extracted_features || {};
  const diagnosis = rawFeatures.primary_diagnosis || rawFeatures.diagnosis || claimData?.diagnosis || '—';
  const procedure = rawFeatures.primary_procedure || rawFeatures.procedure || claimData?.procedure || '—';

  const normalizedStatus = String(invState?.status || '').toUpperCase();
  const isTerminal = ['COMPLETED', 'FAILED', 'REQUIRES_HUMAN_REVIEW', 'MAX_ITERATIONS_REACHED'].includes(normalizedStatus);

  let stage = 0;
  if (['INITIALIZED', 'IN_PROGRESS'].includes(normalizedStatus)) stage = 3;
  else if (normalizedStatus === 'COUNTER_ANALYSIS') stage = 4;
  else if (normalizedStatus === 'CRITIC_REVIEW') stage = 5;
  else if (isTerminal) stage = 6;

  // ── Save Decision ─────────────────────────────────────────────────────────
  const handleSaveDecision = async () => {
    if (!dbClaimId) return;
    setSavingDecision(true);
    try {
      await claimsAPI.update(dbClaimId, { status: decisionStatus });
      setDecisionSaved(true);
      setTimeout(() => setDecisionSaved(false), 3000);
      setClaimData(prev => prev ? { ...prev, status: decisionStatus } : prev);
    } catch (err) {
      alert(`Failed to save decision: ${err.message}`);
    } finally {
      setSavingDecision(false);
    }
  };

  // ─── RENDER ───────────────────────────────────────────────────────────────
  if (claimLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <Clock size={32} className="mx-auto text-blue-400 animate-spin mb-3" />
          <p className="text-slate-600 font-medium">Loading case data...</p>
        </div>
      </div>
    );
  }

  if (claimError) {
    return (
      <div className="max-w-2xl mx-auto mt-16 p-8 bg-red-50 border border-red-200 rounded-xl text-center">
        <AlertTriangle size={32} className="mx-auto text-red-400 mb-3" />
        <h2 className="text-red-800 font-bold text-lg mb-2">Claim Not Found</h2>
        <p className="text-red-700 text-sm mb-4">{claimError}</p>
        <button className="btn-primary px-4 py-2 text-sm rounded-lg" onClick={() => navigate('/investigator/queue')}>
          Back to Queue
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6 relative pb-32 max-w-7xl mx-auto">

      {/* ── CASE HEADER ──────────────────────────────────────────────────── */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="bg-slate-50 px-6 py-3 border-b border-slate-200 flex justify-between items-center">
          <button
            className="text-sm text-slate-500 font-medium hover:text-slate-800 flex items-center transition"
            onClick={() => navigate('/investigator/queue')}
          >
            <ChevronRight size={14} className="mr-1 rotate-180" /> Back to Investigations
          </button>
          <div className="flex items-center gap-2">
            {normalizedStatus && (
              <span className={`px-2.5 py-1 text-xs font-bold rounded-full ${statusColor(normalizedStatus)}`}>
                {normalizedStatus}
              </span>
            )}
            <span className={`px-2.5 py-1 text-xs font-medium rounded-full bg-slate-100 text-slate-600`}>
              {claimData?.status?.toUpperCase() || 'UNKNOWN'}
            </span>
          </div>
        </div>

        <div className="p-6">
          <div className="flex flex-col md:flex-row justify-between gap-6">
            <div className="space-y-4">
              <div>
                <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-3 flex-wrap">
                  CASE {id}
                  {!invState && (
                    <button
                      className="btn-primary text-sm px-4 py-1.5 rounded-lg shadow-sm font-semibold flex items-center gap-2"
                      onClick={startInvestigation}
                      disabled={invLoading || mlLoading || claimLoading}
                    >
                      {invLoading
                        ? <><Clock size={14} className="animate-spin" /> Starting...</>
                        : <><Play size={14} /> Start Investigation</>}
                    </button>
                  )}
                  {invState && !isTerminal && (
                    <span className="flex items-center gap-1 text-sm text-blue-600 font-medium">
                      <Clock size={14} className="animate-spin" /> Investigation running...
                    </span>
                  )}
                </h1>
                <p className="text-sm text-slate-500 mt-1">
                  Provider: <strong className="text-slate-700">{providerName}</strong>
                  {claimData?.provider?.specialty && (
                    <span className="text-slate-400 ml-2">({claimData.provider.specialty})</span>
                  )}
                </p>
              </div>

              <div className="flex flex-wrap gap-8 pt-2">
                <div>
                  <p className="text-xs text-slate-500 font-semibold uppercase tracking-wider mb-1">Billed Amount</p>
                  <p className="text-lg font-bold text-slate-900">{fmt$(claimAmount)}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500 font-semibold uppercase tracking-wider mb-1">Paid Amount</p>
                  <p className="text-lg font-bold text-slate-900">{paidAmount > 0 ? fmt$(paidAmount) : '—'}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500 font-semibold uppercase tracking-wider mb-1">Service Date</p>
                  <p className="text-lg font-bold text-slate-900">{fmtDate(serviceDate)}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500 font-semibold uppercase tracking-wider mb-1">Claim Type</p>
                  <p className="text-lg font-bold text-slate-900">{claimData?.claim_type || 'Medical'}</p>
                </div>
              </div>
            </div>

            {/* Risk Score Card */}
            <div className="bg-slate-900 text-white p-5 rounded-xl min-w-[240px] flex flex-col justify-between shadow-lg">
              <div>
                <p className="text-xs text-slate-400 font-bold uppercase tracking-wider mb-1">ML Risk Score</p>
                {mlLoading ? (
                  <p className="text-slate-400 text-sm flex items-center gap-1 mt-2">
                    <Clock size={12} className="animate-spin" /> Calculating...
                  </p>
                ) : riskScore100 !== null ? (
                  <>
                    <p className="text-4xl font-black">{riskScore100}<span className="text-slate-400 text-xl">/100</span></p>
                    <div className="inline-flex items-center gap-2 mt-2 px-3 py-1.5 rounded-full bg-white/10 border border-white/20 backdrop-blur-sm">
                      <div className={`w-2 h-2 rounded-full ${
                        riskLevel === 'CRITICAL' ? 'bg-rose-300' :
                        riskLevel === 'HIGH' ? 'bg-amber-300' :
                        riskLevel === 'MEDIUM' ? 'bg-yellow-300' :
                        'bg-emerald-300'
                      }`} />
                      <span className="text-xs font-semibold uppercase text-white">
                        {riskLevel || 'UNKNOWN'} RISK
                      </span>
                    </div>
                  </>
                ) : (
                  <p className="text-slate-400 text-sm mt-2 italic">ML assessment not available</p>
                )}
              </div>
              {mlError && (
                <p className="text-xs text-amber-400 mt-3 flex items-start gap-1">
                  <Info size={11} className="shrink-0 mt-0.5" />{mlError}
                </p>
              )}
              {riskScore100 !== null && (
                <div className="mt-3">
                  <p className="text-xs text-slate-500 mb-1">Hybrid Model</p>
                  <div className="w-full h-2 bg-slate-700 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${riskScore100 >= 75 ? 'bg-red-500' : riskScore100 >= 50 ? 'bg-amber-500' : 'bg-emerald-500'}`}
                      style={{ width: `${riskScore100}%` }}
                    />
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Progress bar */}
          <div className="mt-8 border-t border-slate-100 pt-6">
            <div className="flex items-center text-xs font-semibold overflow-x-auto pb-2 gap-2">
              {[
                { label: 'Claim Intake', s: 1 },
                { label: 'Risk Analysis', s: 2 },
                { label: 'Agent Investigation', s: 3 },
                { label: 'Counter Analysis', s: 4 },
                { label: 'Critic Review', s: 5 },
                { label: 'Final Report', s: 6 },
              ].map((item, i) => (
                <React.Fragment key={item.s}>
                  {i > 0 && <div className="w-8 h-px bg-slate-200 shrink-0" />}
                  <span className={`flex items-center whitespace-nowrap ${
                    stage > item.s ? 'text-emerald-600'
                    : stage === item.s ? 'text-blue-600 font-bold'
                    : item.s <= 2 ? 'text-emerald-600'
                    : 'text-slate-400'
                  }`}>
                    {stage > item.s || item.s <= 2
                      ? <CheckCircle size={14} className="mr-1.5" />
                      : stage === item.s
                        ? <Play size={14} className="mr-1.5 animate-pulse" />
                        : <div className="w-3 h-3 rounded-full border-2 border-slate-300 mr-1.5" />}
                    {item.label}
                  </span>
                </React.Fragment>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Alert banners */}
      {normalizedStatus === 'REQUIRES_HUMAN_REVIEW' && (
        <div className="bg-amber-50 border-l-4 border-amber-500 p-5 rounded-r-xl flex items-start">
          <AlertTriangle className="text-amber-500 mr-4 shrink-0 mt-0.5" size={24} />
          <div>
            <h3 className="text-amber-800 font-bold text-sm mb-1">Human Review Required</h3>
            <p className="text-amber-700 text-sm">The automated investigation reached a point requiring investigator validation.</p>
          </div>
        </div>
      )}
      {normalizedStatus === 'FAILED' && (
        <div className="bg-red-50 border-l-4 border-red-500 p-5 rounded-r-xl flex items-start">
          <AlertTriangle className="text-red-500 mr-4 shrink-0 mt-0.5" size={24} />
          <div className="flex-1">
            <h3 className="text-red-800 font-bold text-sm mb-1">Investigation Encountered an Error</h3>
            <p className="text-red-700 text-sm mb-3">{invState?.current_reasoning || 'A transient failure occurred.'}</p>
            <button
              className="btn-primary text-xs px-4 py-2 rounded-lg font-semibold flex items-center gap-2"
              onClick={() => { setInvState(null); setTraceData(null); setIsPolling(false); }}
            >
              <Play size={14} /> Retry Investigation
            </button>
          </div>
        </div>
      )}

      {/* ── TABS ─────────────────────────────────────────────────────────── */}
      <div className="border-b border-slate-200 overflow-x-auto scrollbar-hide">
        <div className="flex w-max min-w-full">
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-5 py-3 text-sm font-semibold border-b-2 transition-all whitespace-nowrap flex items-center gap-1.5 ${
                activeTab === tab.id
                  ? 'border-blue-600 text-blue-700 bg-blue-50/30'
                  : 'border-transparent text-slate-500 hover:text-slate-800 hover:bg-slate-50'
              }`}
            >
              <tab.icon size={14} />
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      <div className="min-h-[400px]">
        {/* ── TAB: CASE OVERVIEW ─────────────────────────────────────────── */}
        {activeTab === 'overview' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Claim Summary */}
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
              <h3 className="text-base font-bold text-slate-800 mb-4 pb-2 border-b flex items-center gap-2">
                <FileText size={16} className="text-slate-400" /> Claim Information
              </h3>
              <dl className="grid grid-cols-2 gap-y-4 gap-x-6 text-sm">
                <div><dt className="text-slate-500 mb-0.5">Claim ID</dt><dd className="font-semibold text-slate-900">{id}</dd></div>
                <div><dt className="text-slate-500 mb-0.5">Status</dt><dd className="font-semibold text-slate-900">{claimData?.status || '—'}</dd></div>
                <div><dt className="text-slate-500 mb-0.5">Service Date</dt><dd className="font-semibold text-slate-900">{fmtDate(serviceDate)}</dd></div>
                <div><dt className="text-slate-500 mb-0.5">Submission Date</dt><dd className="font-semibold text-slate-900">{fmtDate(claimData?.submission_date)}</dd></div>
                <div><dt className="text-slate-500 mb-0.5">Billed Amount</dt><dd className="font-bold text-slate-900">{fmt$(claimAmount)}</dd></div>
                <div><dt className="text-slate-500 mb-0.5">Paid Amount</dt><dd className="font-bold text-slate-900">{paidAmount > 0 ? fmt$(paidAmount) : '—'}</dd></div>
                <div><dt className="text-slate-500 mb-0.5">Claim Type</dt><dd className="font-semibold text-slate-900">{claimData?.claim_type || 'Medical'}</dd></div>
                <div><dt className="text-slate-500 mb-0.5">State</dt><dd className="font-semibold text-slate-900">{claimData?.state || '—'}</dd></div>
                <div><dt className="text-slate-500 mb-0.5">Diagnosis</dt><dd className="font-semibold text-slate-900">{diagnosis}</dd></div>
                <div><dt className="text-slate-500 mb-0.5">Procedure</dt><dd className="font-semibold text-slate-900">{procedure}</dd></div>
                <div><dt className="text-slate-500 mb-0.5">Diag Lines</dt><dd className="font-semibold text-slate-900">{claimData?.diag_count || '—'}</dd></div>
                <div><dt className="text-slate-500 mb-0.5">Proc Lines</dt><dd className="font-semibold text-slate-900">{claimData?.proc_count || '—'}</dd></div>
              </dl>
            </div>

            {/* Provider + Patient */}
            <div className="space-y-4">
              <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
                <h3 className="text-base font-bold text-slate-800 mb-4 pb-2 border-b flex items-center gap-2">
                  <Building2 size={16} className="text-slate-400" /> Provider
                </h3>
                {claimData?.provider ? (
                  <dl className="grid grid-cols-2 gap-y-3 text-sm">
                    <div><dt className="text-slate-500 mb-0.5">Name</dt><dd className="font-semibold">{claimData.provider.name}</dd></div>
                    <div><dt className="text-slate-500 mb-0.5">NPI</dt><dd className="font-semibold font-mono">{claimData.provider.npi}</dd></div>
                    <div><dt className="text-slate-500 mb-0.5">Type</dt><dd className="font-semibold">{claimData.provider.provider_type || '—'}</dd></div>
                    <div><dt className="text-slate-500 mb-0.5">Specialty</dt><dd className="font-semibold">{claimData.provider.specialty || '—'}</dd></div>
                    <div className="col-span-2"><dt className="text-slate-500 mb-0.5">Address</dt><dd className="font-semibold">{claimData.provider.address || '—'}</dd></div>
                    <div><dt className="text-slate-500 mb-0.5">Active</dt><dd className={`font-bold ${claimData.provider.is_active ? 'text-emerald-600' : 'text-red-600'}`}>{claimData.provider.is_active ? 'Yes' : 'No'}</dd></div>
                  </dl>
                ) : (
                  <p className="text-sm text-slate-500">Provider #{claimData?.provider_id}</p>
                )}
              </div>

              <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
                <h3 className="text-base font-bold text-slate-800 mb-4 pb-2 border-b flex items-center gap-2">
                  <User size={16} className="text-slate-400" /> Beneficiary / Patient
                </h3>
                {claimData?.patient ? (
                  <dl className="grid grid-cols-2 gap-y-3 text-sm">
                    <div><dt className="text-slate-500 mb-0.5">Name</dt><dd className="font-semibold">{claimData.patient.first_name} {claimData.patient.last_name}</dd></div>
                    <div><dt className="text-slate-500 mb-0.5">Member ID</dt><dd className="font-semibold font-mono">{claimData.patient.member_id || '—'}</dd></div>
                    <div><dt className="text-slate-500 mb-0.5">Date of Birth</dt><dd className="font-semibold">{fmtDate(claimData.patient.date_of_birth)}</dd></div>
                    <div><dt className="text-slate-500 mb-0.5">Gender</dt><dd className="font-semibold capitalize">{claimData.patient.gender || '—'}</dd></div>
                    <div><dt className="text-slate-500 mb-0.5">Ext. ID</dt><dd className="font-semibold font-mono text-xs">{claimData.patient.patient_external_id || '—'}</dd></div>
                  </dl>
                ) : (
                  <p className="text-sm text-slate-500">Patient #{claimData?.patient_id}</p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* ── TAB: AGENTIC TRACE ─────────────────────────────────────────── */}
        {activeTab === 'trace' && (
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
            <div className="flex justify-between items-end border-b pb-4 mb-6">
              <div>
                <h3 className="text-base font-bold text-slate-800">Agentic Investigation Trace</h3>
                <p className="text-sm text-slate-500 mt-1">Real-time timeline of agent reasoning, tool calls, and observations.</p>
              </div>
              {invState && (
                <div className="text-right">
                  <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-1">Iteration</p>
                  <p className="text-lg font-bold text-slate-800">{invState.iteration_count} / {invState.max_iterations}</p>
                </div>
              )}
            </div>

            {!invState ? (
              <div className="text-center py-12">
                <Search size={32} className="mx-auto text-slate-300 mb-3" />
                <p className="text-sm font-medium text-slate-600">No investigation started yet.</p>
                <p className="text-xs text-slate-400 mt-1">Click "Start Investigation" to begin the agentic workflow.</p>
              </div>
            ) : (
              <div className="space-y-6 relative before:absolute before:inset-0 before:ml-[1.4rem] before:-translate-x-px before:h-full before:w-0.5 before:bg-slate-200 pl-2">
                {(!traceData?.iterations || traceData.iterations.length === 0) ? (
                  <p className="text-sm text-slate-500 ml-12 py-4">
                    {['IN_PROGRESS', 'INITIALIZED'].includes(normalizedStatus)
                      ? 'Agent is initializing the investigation...'
                      : 'No iteration trace available.'}
                  </p>
                ) : traceData.iterations.map((step, idx) => {
                  const toolLower = (step.selected_tool || '').toLowerCase();
                  const isRag = toolLower.includes('rag');
                  const isMl = toolLower.includes('ml');
                  const isDb = toolLower.includes('provider') || toolLower.includes('claim');
                  const isEnd = step.decision === 'counter_analysis' || step.decision === 'escalate';
                  const isFail = step.tool_status === 'TOOL_FAILURE' || step.tool_status === 'INVALID_TOOL';

                  return (
                    <div key={idx} className="relative flex items-start group">
                      <div className={`flex items-center justify-center w-10 h-10 rounded-full border-[3px] border-white shrink-0 shadow-sm z-10 ${
                        isFail ? 'bg-red-100 text-red-600'
                        : isEnd ? 'bg-emerald-100 text-emerald-600'
                        : isRag ? 'bg-teal-100 text-teal-600'
                        : isMl ? 'bg-purple-100 text-purple-600'
                        : isDb ? 'bg-indigo-100 text-indigo-600'
                        : 'bg-blue-100 text-blue-600'
                      }`}>
                        {isFail ? <AlertTriangle size={16} />
                          : isEnd ? <CheckCircle size={16} />
                          : <Clock size={16} />}
                      </div>
                      <div className="ml-6 w-full">
                        <div className="flex items-center gap-2 mb-1 mt-1 flex-wrap">
                          <h4 className="font-bold text-slate-800 text-sm">
                            Iteration {step.iteration}: {step.selected_tool || 'unknown'}
                          </h4>
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                            step.tool_status === 'SUCCESS' ? 'bg-emerald-100 text-emerald-700'
                            : step.tool_status === 'NO_EVIDENCE_FOUND' ? 'bg-amber-100 text-amber-700'
                            : 'bg-red-100 text-red-700'
                          }`}>{step.tool_status || 'UNKNOWN'}</span>
                          <span className="text-xs text-slate-400">{step.decision && `→ ${step.decision}`}</span>
                        </div>
                        <div className="bg-slate-50 border border-slate-100 rounded-lg p-4 text-sm text-slate-700 shadow-sm">
                          <p className="font-medium text-slate-900 mb-2">Q: {step.question}</p>
                          <p className="text-slate-600">{step.observation || 'No observation recorded.'}</p>
                          <div className="mt-3 flex flex-wrap gap-2">
                            {step.evidence_count > 0 && (
                              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-700">{step.evidence_count} evidence items</span>
                            )}
                            {isRag && <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-teal-100 text-teal-700 uppercase">RAG Policy</span>}
                            {isMl && <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-100 text-purple-700 uppercase">ML</span>}
                            {isDb && <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-100 text-indigo-700 uppercase">Database</span>}
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}

                {/* Counter Analysis */}
                {traceData?.counter_analysis && (
                  <div className="relative flex items-start">
                    <div className="flex items-center justify-center w-10 h-10 rounded-full border-[3px] border-white shrink-0 shadow-sm z-10 bg-orange-100 text-orange-600">
                      <ShieldAlert size={16} />
                    </div>
                    <div className="ml-6 w-full">
                      <h4 className="font-bold text-slate-800 text-sm mt-1 mb-2">Counter Analysis</h4>
                      <div className="bg-orange-50 border border-orange-100 rounded-lg p-4 text-sm">
                        <p className="text-slate-700">{traceData.counter_analysis.counter_evidence_count} counter-evidence items found.</p>
                        {traceData.counter_analysis.alternative_explanations?.length > 0 && (
                          <ul className="mt-2 space-y-1">
                            {traceData.counter_analysis.alternative_explanations.map((e, i) => (
                              <li key={i} className="text-slate-600 text-xs">• {e}</li>
                            ))}
                          </ul>
                        )}
                      </div>
                    </div>
                  </div>
                )}

                {/* Critic */}
                {traceData?.critic && (
                  <div className="relative flex items-start">
                    <div className={`flex items-center justify-center w-10 h-10 rounded-full border-[3px] border-white shrink-0 shadow-sm z-10 ${traceData.critic.status === 'PASS' ? 'bg-emerald-100 text-emerald-600' : 'bg-amber-100 text-amber-600'}`}>
                      <CheckCircle size={16} />
                    </div>
                    <div className="ml-6 w-full">
                      <h4 className="font-bold text-slate-800 text-sm mt-1 mb-2">Critic Review — {traceData.critic.status}</h4>
                      <div className="bg-slate-50 border border-slate-100 rounded-lg p-4 text-sm">
                        {traceData.critic.issues?.length > 0 ? (
                          <ul className="space-y-1">{traceData.critic.issues.map((i, x) => <li key={x} className="text-slate-600">• {i}</li>)}</ul>
                        ) : (
                          <p className="text-emerald-700">No critical issues found.</p>
                        )}
                      </div>
                    </div>
                  </div>
                )}

                {/* Spinning indicator */}
                {['IN_PROGRESS', 'INITIALIZED', 'COUNTER_ANALYSIS', 'CRITIC_REVIEW'].includes(normalizedStatus) && (
                  <div className="relative flex items-start">
                    <div className="flex items-center justify-center w-10 h-10 rounded-full border-[3px] border-white shrink-0 shadow-sm z-10 bg-slate-100 text-slate-400">
                      <Clock size={16} className="animate-spin" />
                    </div>
                    <div className="ml-6 mt-2">
                      <h4 className="font-bold text-slate-400 text-sm italic">
                        {normalizedStatus === 'COUNTER_ANALYSIS' ? 'Running counter-analysis...'
                          : normalizedStatus === 'CRITIC_REVIEW' ? 'Critic reviewing conclusion...'
                          : 'Agent is reasoning...'}
                      </h4>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* ── TAB: INVESTIGATION FINDINGS ───────────────────────────────── */}
        {activeTab === 'findings' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Findings */}
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
              <h3 className="text-base font-bold text-slate-800 border-b pb-3 mb-4 flex justify-between items-center">
                Key Findings
                {invState?.final_report?.findings?.length > 0 && (
                  <span className="text-xs bg-slate-100 text-slate-600 px-2 py-1 rounded-full">{invState.final_report.findings.length}</span>
                )}
              </h3>
              {!invState ? (
                <p className="text-sm text-slate-400 italic">No investigation started.</p>
              ) : !invState.final_report?.findings?.length ? (
                isTerminal ? (
                  <div className="text-center py-8"><FileX size={28} className="mx-auto text-slate-200 mb-2" /><p className="text-sm text-slate-500">Investigation completed but no structured findings were generated. Check the Evidence tab.</p></div>
                ) : (
                  <div className="text-center py-8"><Clock size={28} className="mx-auto text-blue-200 animate-spin mb-2" /><p className="text-sm text-slate-500">Investigation in progress. Findings will appear when evidence collection completes.</p></div>
                )
              ) : (
                <ul className="space-y-3">
                  {invState.final_report.findings.map((f, i) => (
                    <li key={i} className="bg-slate-50 border border-slate-100 rounded-lg p-4 text-sm text-slate-800">{f}</li>
                  ))}
                </ul>
              )}
            </div>

            {/* Questions asked */}
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
              <h3 className="text-base font-bold text-slate-800 border-b pb-3 mb-4 flex justify-between items-center">
                Investigation Questions
                {invState?.questions?.length > 0 && (
                  <span className="text-xs bg-slate-100 text-slate-600 px-2 py-1 rounded-full">{invState.questions.length}</span>
                )}
              </h3>
              {!invState?.questions?.length ? (
                <p className="text-sm text-slate-400 italic">No questions generated yet.</p>
              ) : (
                <ul className="space-y-2">
                  {invState.questions.map((q, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm">
                      <span className="text-slate-400 font-mono text-xs mt-0.5 shrink-0">{i + 1}.</span>
                      <div>
                        <p className="text-slate-800 font-medium">{q.question}</p>
                        {q.preferred_tool && (
                          <p className="text-xs text-slate-400 mt-0.5">Tool: {q.preferred_tool} · Priority: {q.priority}</p>
                        )}
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {/* Evidence Gaps */}
            {invState?.evidence_gaps?.length > 0 && (
              <div className="bg-amber-50 rounded-xl border border-amber-100 p-6 lg:col-span-2">
                <h3 className="text-base font-bold text-amber-800 mb-3">Unresolved Evidence Gaps ({invState.evidence_gaps.length})</h3>
                <ul className="space-y-2">
                  {invState.evidence_gaps.map((g, i) => (
                    <li key={i} className="text-sm text-amber-700 flex items-start gap-2">
                      <AlertTriangle size={14} className="shrink-0 mt-0.5" />
                      <span>{g.description}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Final Conclusion */}
            {invState?.final_report?.conclusion && (
              <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 lg:col-span-2">
                <h3 className="text-base font-bold text-slate-800 mb-3">Conclusion</h3>
                <p className="text-sm text-slate-700 leading-relaxed">{invState.final_report.conclusion}</p>
                <div className="mt-3 flex items-center gap-3">
                  <span className="text-xs text-slate-500">Confidence:</span>
                  <div className="flex-1 h-2 bg-slate-100 rounded-full max-w-xs">
                    <div className="h-full bg-blue-500 rounded-full" style={{ width: `${Math.round((invState.final_report.confidence || 0) * 100)}%` }} />
                  </div>
                  <span className="text-xs font-bold text-slate-700">{Math.round((invState.final_report.confidence || 0) * 100)}%</span>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── TAB: EXPLAINABILITY ───────────────────────────────────────── */}
        {activeTab === 'explainability' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* ML Components */}
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
              <h3 className="text-base font-bold text-slate-800 border-b pb-3 mb-4 flex items-center gap-2">
                <BarChart2 size={16} className="text-slate-400" /> ML Score Breakdown
              </h3>
              {!mlPrediction && !mlLoading ? (
                <p className="text-sm text-slate-400 italic">{mlError || 'ML assessment not available.'}</p>
              ) : mlLoading ? (
                <p className="text-sm text-slate-400 flex items-center gap-1"><Clock size={12} className="animate-spin" /> Computing...</p>
              ) : (
                <div className="space-y-4">
                  {hybridResult.final_risk_score !== undefined && (
                    <div className="bg-slate-50 rounded-lg p-4 border">
                      <div className="flex justify-between text-sm font-medium mb-1">
                        <span>Hybrid Risk Score</span>
                        <span className="font-bold">{Math.round(hybridResult.final_risk_score * 100)}/100</span>
                      </div>
                      <div className="h-2 bg-slate-200 rounded-full">
                        <div className={`h-full rounded-full ${riskScore100 >= 75 ? 'bg-red-500' : riskScore100 >= 50 ? 'bg-amber-500' : 'bg-emerald-500'}`} style={{ width: `${Math.round(hybridResult.final_risk_score * 100)}%` }} />
                      </div>
                      <p className={`text-xs font-bold mt-1 uppercase ${riskColor(Math.round(hybridResult.final_risk_score * 100))}`}>{hybridResult.final_risk_tier}</p>
                    </div>
                  )}
                  {hybridResult.claim_score !== undefined && (
                    <div>
                      <div className="flex justify-between text-xs font-medium text-slate-500 mb-1">
                        <span>Claim Anomaly Score</span>
                        <span>{Math.round(hybridResult.claim_score * 100)}%</span>
                      </div>
                      <div className="h-1.5 bg-slate-100 rounded-full">
                        <div className="h-full bg-indigo-400 rounded-full" style={{ width: `${Math.round(hybridResult.claim_score * 100)}%` }} />
                      </div>
                    </div>
                  )}
                  {hybridResult.provider_score !== undefined && (
                    <div>
                      <div className="flex justify-between text-xs font-medium text-slate-500 mb-1">
                        <span>Provider Fraud Score</span>
                        <span>{Math.round(hybridResult.provider_score * 100)}%</span>
                      </div>
                      <div className="h-1.5 bg-slate-100 rounded-full">
                        <div className="h-full bg-purple-400 rounded-full" style={{ width: `${Math.round(hybridResult.provider_score * 100)}%` }} />
                      </div>
                    </div>
                  )}
                  {hybridResult.model_weights && (
                    <div className="text-xs text-slate-500 pt-2 border-t">
                      <span className="font-medium">Model Weights: </span>
                      Claim {Math.round((hybridResult.model_weights.claim_weight || 0) * 100)}% /
                      Provider {Math.round((hybridResult.model_weights.provider_weight || 0) * 100)}%
                      {hybridResult.model_weights.mode && ` · ${hybridResult.model_weights.mode}`}
                    </div>
                  )}
                  {hybridResult.leie_override && (
                    <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-xs text-red-700 font-medium">
                      ⚠️ LEIE Override Active: Provider has active OIG exclusion.
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* SHAP / Risk Factors */}
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
              <h3 className="text-base font-bold text-slate-800 border-b pb-3 mb-4">Risk Factors & SHAP Drivers</h3>
              {invState?.risk_factors?.length > 0 ? (
                <ul className="space-y-3">
                  {invState.risk_factors.map((rf, i) => (
                    <li key={i} className="flex items-start justify-between gap-3 py-2 border-b border-slate-50 last:border-0">
                      <div className="flex-1">
                        <p className="text-sm font-semibold text-slate-800">{rf.name}</p>
                        {rf.description && <p className="text-xs text-slate-500 mt-0.5">{rf.description}</p>}
                      </div>
                      <div className="text-right shrink-0">
                        {rf.shap_value !== null && rf.shap_value !== undefined && (
                          <p className="text-xs font-mono font-bold text-slate-600">{rf.shap_value > 0 ? '+' : ''}{rf.shap_value.toFixed(3)}</p>
                        )}
                        {rf.magnitude && (
                          <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded uppercase ${rf.magnitude === 'HIGH' ? 'bg-red-100 text-red-700' : rf.magnitude === 'MEDIUM' ? 'bg-amber-100 text-amber-700' : 'bg-slate-100 text-slate-600'}`}>{rf.magnitude}</span>
                        )}
                      </div>
                    </li>
                  ))}
                </ul>
              ) : mlPrediction ? (
                <p className="text-sm text-slate-400 italic">No SHAP factors isolated. Start an investigation to extract risk drivers.</p>
              ) : (
                <p className="text-sm text-slate-400 italic">ML assessment not available.</p>
              )}
            </div>

            {/* Detected Patterns */}
            {invState?.detected_patterns?.length > 0 && (
              <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 lg:col-span-2">
                <h3 className="text-base font-bold text-slate-800 border-b pb-3 mb-4">Detected Patterns</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {invState.detected_patterns.map((p, i) => (
                    <div key={i} className="bg-blue-50 border border-blue-100 rounded-lg p-3">
                      <p className="text-xs font-bold text-blue-700 uppercase mb-1">Pattern {i + 1}</p>
                      <p className="text-sm font-semibold text-blue-900">{p.name}</p>
                      {p.description && <p className="text-xs text-blue-700 mt-0.5">{p.description}</p>}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── TAB: PROVIDER ANALYSIS ────────────────────────────────────── */}
        {activeTab === 'provider' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
              <h3 className="text-base font-bold text-slate-800 border-b pb-3 mb-4 flex items-center gap-2">
                <Building2 size={16} className="text-slate-400" /> Provider Profile
              </h3>
              {claimData?.provider ? (
                <dl className="space-y-3 text-sm">
                  <div className="flex justify-between"><dt className="text-slate-500">Name</dt><dd className="font-semibold">{claimData.provider.name}</dd></div>
                  <div className="flex justify-between"><dt className="text-slate-500">NPI</dt><dd className="font-mono font-semibold">{claimData.provider.npi}</dd></div>
                  <div className="flex justify-between"><dt className="text-slate-500">Type</dt><dd className="font-semibold">{claimData.provider.provider_type || '—'}</dd></div>
                  <div className="flex justify-between"><dt className="text-slate-500">Specialty</dt><dd className="font-semibold">{claimData.provider.specialty || '—'}</dd></div>
                  <div className="flex justify-between"><dt className="text-slate-500">Active</dt><dd className={`font-bold ${claimData.provider.is_active ? 'text-emerald-600' : 'text-red-600'}`}>{claimData.provider.is_active ? 'Active' : 'Inactive'}</dd></div>
                </dl>
              ) : (
                <p className="text-sm text-slate-400">Provider #{claimData?.provider_id}</p>
              )}
            </div>

            {/* Provider evidence from agent */}
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
              <h3 className="text-base font-bold text-slate-800 border-b pb-3 mb-4">Provider Evidence from Investigation</h3>
              {!invState ? (
                <p className="text-sm text-slate-400 italic">Start an investigation to collect provider history evidence.</p>
              ) : (() => {
                const provEv = invState.evidence?.filter(e =>
                  ['provider_statistic', 'provider_history', 'peer_comparison'].includes(e.type)
                ) || [];
                return provEv.length === 0
                  ? <p className="text-sm text-slate-400 italic">No provider-specific evidence collected yet.</p>
                  : <ul className="space-y-3">{provEv.map((e, i) => (
                    <li key={i} className="bg-slate-50 border border-slate-100 rounded-lg p-3 text-sm">
                      <p className="font-medium text-slate-800 mb-1">{e.type.replace(/_/g, ' ').toUpperCase()}</p>
                      <p className="text-slate-600">{e.description}</p>
                      <p className="text-xs text-slate-400 mt-1">Source: {e.source} · Confidence: {Math.round((e.confidence || 0) * 100)}%</p>
                    </li>
                  ))}</ul>;
              })()}
            </div>

            {/* Counter Evidence */}
            {invState?.counter_evidence?.length > 0 && (
              <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 lg:col-span-2">
                <h3 className="text-base font-bold text-slate-800 border-b pb-3 mb-4">Counter Evidence ({invState.counter_evidence.length})</h3>
                <ul className="space-y-3">
                  {invState.counter_evidence.map((e, i) => (
                    <li key={i} className="bg-amber-50 border border-amber-100 rounded-lg p-4 text-sm">
                      <p className="font-medium text-amber-800 mb-1">{e.type.replace(/_/g, ' ')}</p>
                      <p className="text-amber-700">{e.description}</p>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* ── TAB: DOCUMENTS & EVIDENCE ─────────────────────────────────── */}
        {activeTab === 'documents' && (
          <div className="space-y-6">
            {!invState ? (
              <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-12 text-center">
                <BookOpen size={32} className="mx-auto text-slate-300 mb-3" />
                <p className="text-sm text-slate-500">No evidence collected yet. Start an investigation to gather evidence.</p>
              </div>
            ) : (
              <>
                {/* Evidence Items */}
                <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
                  <h3 className="text-base font-bold text-slate-800 border-b pb-3 mb-4 flex justify-between items-center">
                    Collected Evidence
                    <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded-full">{invState.evidence?.length || 0} items</span>
                  </h3>
                  {!invState.evidence?.length ? (
                    <p className="text-sm text-slate-400 italic">No evidence collected yet.</p>
                  ) : (
                    <div className="space-y-3">
                      {invState.evidence.map((e, i) => (
                        <div key={i} className="border border-slate-100 rounded-lg p-4 hover:bg-slate-50 transition">
                          <div className="flex items-start justify-between gap-3 mb-2">
                            <span className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase ${
                              e.type === 'policy' ? 'bg-teal-100 text-teal-700'
                              : e.type === 'ml_score' ? 'bg-purple-100 text-purple-700'
                              : e.type?.includes('provider') ? 'bg-indigo-100 text-indigo-700'
                              : 'bg-slate-100 text-slate-600'
                            }`}>{e.type?.replace(/_/g, ' ')}</span>
                            <span className="text-xs text-slate-400">Confidence: {Math.round((e.confidence || 0) * 100)}%</span>
                          </div>
                          <p className="text-sm text-slate-800 font-medium mb-1">{e.description}</p>
                          <p className="text-xs text-slate-500">Source: {e.source} · Tool: {e.tool_used || '—'}</p>
                          {e.related_question && (
                            <p className="text-xs text-slate-400 italic mt-1">Q: {e.related_question}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Citations */}
                {invState.citations?.length > 0 && (
                  <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
                    <h3 className="text-base font-bold text-slate-800 border-b pb-3 mb-4 flex justify-between items-center">
                      Policy Citations
                      <span className="text-xs bg-teal-100 text-teal-700 px-2 py-1 rounded-full">{invState.citations.length}</span>
                    </h3>
                    <div className="space-y-3">
                      {invState.citations.map((c, i) => {
                        const source = c.source || c.document || 'CMS';
                        const section = c.section || c.reference || '';
                        const text = c.text || c.excerpt || '';
                        const url = c.url || c.official_cms_url || '';
                        return (
                          <div key={i} className="bg-teal-50 border border-teal-100 rounded-lg p-4 text-sm">
                            <p className="font-semibold text-teal-800">{source}{section ? ` — ${section}` : ''}</p>
                            {text && <p className="text-teal-700 mt-1 text-xs leading-relaxed">{text.slice(0, 300)}{text.length > 300 ? '...' : ''}</p>}
                            {url && (
                              <a href={url} target="_blank" rel="noreferrer" className="text-xs text-teal-600 flex items-center gap-1 mt-1 hover:underline">
                                <ExternalLink size={11} /> View Source
                              </a>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* ── TAB: DECISION & NOTES ─────────────────────────────────────── */}
        {activeTab === 'decision' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
              <h3 className="text-base font-bold text-slate-800 border-b pb-3 mb-4 flex items-center gap-2">
                <Edit3 size={16} className="text-slate-400" /> Investigator Decision
              </h3>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-2">Decision</label>
                  <select
                    value={decisionStatus}
                    onChange={e => setDecisionStatus(e.target.value)}
                    className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="pending_review">Pending Review</option>
                    <option value="flagged">Flag for Further Investigation</option>
                    <option value="denied">Deny — Fraud/Waste Confirmed</option>
                    <option value="paid">Approve — Claim Legitimate</option>
                    <option value="closed">Close — No Action Required</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-2">Investigator Notes</label>
                  <textarea
                    value={decisionNote}
                    onChange={e => setDecisionNote(e.target.value)}
                    rows={6}
                    placeholder="Enter your investigation notes, rationale, and recommended actions..."
                    className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                  />
                </div>
                <button
                  onClick={handleSaveDecision}
                  disabled={savingDecision || !dbClaimId}
                  className="btn-primary w-full py-2.5 text-sm font-semibold rounded-lg flex items-center justify-center gap-2 disabled:opacity-50"
                >
                  {savingDecision ? <><Clock size={14} className="animate-spin" /> Saving...</> : decisionSaved ? <><CheckCircle size={14} /> Saved!</> : <><Save size={14} /> Save Decision</>}
                </button>
              </div>
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
              <h3 className="text-base font-bold text-slate-800 border-b pb-3 mb-4">Final Report Summary</h3>
              {invState?.final_report ? (
                <div className="space-y-4 text-sm">
                  <div>
                    <p className="text-xs font-bold text-slate-500 uppercase mb-1">Claim Summary</p>
                    <p className="text-slate-700">{invState.final_report.claim_summary || '—'}</p>
                  </div>
                  <div>
                    <p className="text-xs font-bold text-slate-500 uppercase mb-1">Risk Summary</p>
                    <p className="text-slate-700">{invState.final_report.risk_summary || '—'}</p>
                  </div>
                  <div>
                    <p className="text-xs font-bold text-slate-500 uppercase mb-1">Recommendation</p>
                    <p className="text-slate-700">{invState.final_report.recommendation || invState.final_report.conclusion || '—'}</p>
                  </div>
                  <div className="pt-2 border-t flex gap-4 text-xs text-slate-500">
                    <span>Confidence: <strong className="text-slate-700">{Math.round((invState.final_report.confidence || 0) * 100)}%</strong></span>
                    <span>Evidence: <strong className="text-slate-700">{invState.final_report.evidence_collected?.length || invState.evidence?.length || 0}</strong></span>
                    <span>Gaps: <strong className="text-slate-700">{invState.evidence_gaps?.length || 0}</strong></span>
                  </div>
                </div>
              ) : (
                <p className="text-sm text-slate-400 italic">Final report will appear when investigation completes.</p>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Copilot */}
      <CopilotPanel />
    </div>
  );
}
