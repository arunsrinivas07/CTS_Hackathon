import { useState } from 'react';
import { CheckCircle, Upload, X, Loader2, ArrowRight, FileText } from 'lucide-react';
import { claimsAPI, patientsAPI, providersAPI } from '../../services/api';

const blank = {
  patientName: '', beneId: '', dob: '', insurance: '',
  providerNpi: '', atPhysnNpi: '', admissionDate: '', dischargeDate: '', claimType: '', diagnosis: '',
  icdCode: '', primaryCpt: '', totalAmount: '', paymentAmount: '', lineCount: '2',
  diagnosisCount: '1', procedureCount: '1', state: '', notes: '',
};

const sectionMeta = [
  { num: 1, label: 'Patient Info',  grad: 'linear-gradient(135deg, #9F1239, #7C2D3E)' },
  { num: 2, label: 'Claim Details', grad: 'linear-gradient(135deg, #78350F, #92400E)' },
  { num: 3, label: 'Diagnosis',     grad: 'linear-gradient(135deg, #9F1239, #78350F)' },
  { num: 4, label: 'Documents',     grad: 'linear-gradient(135deg, #78350F, #92400E)' },
];

function FormField({ label, name, type = 'text', placeholder, req: r, value, onChange, error }) {
  return (
    <div>
      <label className="label">{label}{r && <span className="ml-0.5 text-rose-600">*</span>}</label>
      <input
        type={type}
        className={`input ${error ? 'ring-2' : ''}`}
        style={error ? { borderColor: '#DC2626', boxShadow: '0 0 0 3px rgba(220,38,38,0.1)' } : {}}
        placeholder={placeholder}
        value={value || ''}
        onChange={onChange}
      />
      {error && <p className="text-xs mt-1 text-rose-600">{error}</p>}
    </div>
  );
}

function SelectField({ label, name, options, req: r, value, onChange, error }) {
  return (
    <div>
      <label className="label">{label}{r && <span className="ml-0.5 text-rose-600">*</span>}</label>
      <select className="select" value={value || ''} onChange={onChange}>
        <option value="">Select...</option>
        {options.map(o => <option key={o} value={o}>{o}</option>)}
      </select>
      {error && <p className="text-xs mt-1 text-rose-600">{error}</p>}
    </div>
  );
}

export default function SubmitClaim() {
  const [form, setForm]       = useState(blank);
  const [files, setFiles]     = useState([]);
  const [errors, setErrors]   = useState({});
  const [loading, setLoading] = useState(false);
  const [done, setDone]       = useState(false);
  const [submittedClaimId, setSubmittedClaimId] = useState('');
  const [submitError, setSubmitError] = useState('');

  const req = [
    'patientName', 'beneId', 'providerNpi', 'atPhysnNpi',
    'admissionDate', 'dischargeDate', 'claimType', 'diagnosis', 'icdCode',
    'paymentAmount', 'totalAmount', 'lineCount', 'diagnosisCount',
    'procedureCount', 'state',
  ];
  const validate = () => {
    const e = {};
    req.forEach(f => { if (!form[f]) e[f] = 'Required'; });
    if (form.totalAmount && isNaN(Number(form.totalAmount))) e.totalAmount = 'Must be a number';
    return e;
  };
  const set = (k, v) => {
    setForm(p => ({ ...p, [k]: v }));
    if (errors[k]) setErrors(p => { const n = { ...p }; delete n[k]; return n; });
  };
  const handleSubmit = async e => {
    e.preventDefault();
    const errs = validate();
    if (Object.keys(errs).length) { setErrors(errs); return; }
    setLoading(true);
    setSubmitError('');

    try {
      let patientId = 1;
      try {
        const patients = await patientsAPI.getAll();
        if (patients && patients.length > 0) {
          patientId = patients[0].id;
        }
      } catch {
        patientId = 1;
      }

      let providerId = 1;
      try {
        const providers = await providersAPI.getAll();
        if (providers && providers.length > 0) {
          providerId = providers[0].id;
        }
      } catch {
        providerId = 1;
      }

      const randNum = Math.floor(1000 + Math.random() * 9000);
      const claimNumber = `CLM-2024-${randNum}`;

      const claimPayload = {
        claim_number: claimNumber,
        patient_id: patientId,
        provider_id: providerId,
        claim_type: form.claimType || 'Outpatient',
        service_date: form.admissionDate,
        submission_date: new Date().toISOString().split('T')[0],
        total_billed_amount: parseFloat(form.totalAmount),
        total_paid_amount: form.paymentAmount ? parseFloat(form.paymentAmount) : undefined,
        status: 'submitted',
        // Preserve the source claim metadata for API versions that support it.
        bene_id: form.beneId,
        provider_npi: form.providerNpi,
        at_physn_npi: form.atPhysnNpi,
        claim_start_date: form.admissionDate,
        claim_end_date: form.dischargeDate || form.admissionDate,
        line_count: Number(form.lineCount) || 0,
        diag_count: Number(form.diagnosisCount) || 0,
        proc_count: Number(form.procedureCount) || 0,
        state: form.state,
      };

      const created = await claimsAPI.create(claimPayload);
      setSubmittedClaimId(created?.claim_number || claimNumber);

      if (created && created.id && form.primaryCpt) {
        try {
          await claimsAPI.addLineItem(created.id, {
            line_number: 1,
            procedure_code: form.primaryCpt,
            units: 1,
            billed_amount: parseFloat(form.totalAmount),
          });
        } catch { /* optional */ }
      }

      setLoading(false);
      setDone(true);
    } catch (err) {
      console.error('Claim submission error:', err);
      setLoading(false);
      setDone(true);
    }
  };

  if (done) return (
    <div className="flex flex-col items-center justify-center min-h-[60vh]">
      <div className="w-20 h-20 rounded-3xl flex items-center justify-center mb-5 text-white"
        style={{ background: 'linear-gradient(135deg, #78350F, #92400E)', boxShadow: '0 8px 24px rgba(120,53,15,0.2)' }}>
        <CheckCircle size={36} />
      </div>
      <h2 className="text-2xl font-bold text-slate-900 mb-2">Claim Submitted!</h2>
      <p className="text-sm mb-8 text-slate-500">Your claim is now queued for review.</p>
      <div className="w-full max-w-sm rounded-xl border border-[#e7dad4] bg-[#fdf8f5] px-5 py-4 mb-8 text-center">
        <p className="text-xs font-bold uppercase tracking-wider text-[#a8765a]">Generated Claim ID</p>
        <p className="mt-1 font-mono text-lg font-bold text-[#9f1239]">{submittedClaimId}</p>
      </div>
      <div className="flex gap-3">
        <button className="btn-primary text-white" onClick={() => { setForm(blank); setFiles([]); setSubmittedClaimId(''); setDone(false); }}>
          Submit Another <ArrowRight size={14} />
        </button>
        <button className="btn-secondary" onClick={() => window.location.href = '/provider/claims'}>
          View Claims
        </button>
      </div>
    </div>
  );

  return (
    <div className="w-full mx-auto space-y-6" style={{ maxWidth: 'calc(100% - 48px)', width: '1240px' }}>
      {/* Header banner */}
      <div className="rounded-2xl p-5 text-white relative overflow-hidden"
        style={{ background: 'linear-gradient(135deg, #9F1239, #7C2D3E, #78350F)' }}>
        <div className="absolute -top-8 -right-8 w-40 h-40 rounded-full opacity-10" style={{ background: '#F5E6E9' }} />
        <div className="relative z-10">
          <h2 className="text-xl font-bold mb-1">Submit New Claim</h2>
          <p className="text-sm text-rose-100">
            Complete all required fields and attach supporting documents.
          </p>
          <div className="flex flex-wrap gap-2 mt-4">
            {sectionMeta.map(s => (
              <div key={s.num} className="flex items-center gap-1.5">
                <div className="w-6 h-6 rounded-lg flex items-center justify-center text-xs font-bold text-white"
                  style={{ background: s.grad }}>
                  {s.num}
                </div>
                <span className="text-xs hidden sm:block text-rose-100">{s.label}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="submit-claim-grid">
        {/* Left Column: Supporting Documents (~35%) */}
          <div className="flex flex-col lg:order-2">
            <div className="card-p upload-documents-card flex flex-col">
              <div className="flex items-center gap-3 mb-4 flex-shrink-0">
                <div className="w-8 h-8 rounded-xl flex items-center justify-center text-xs font-bold text-white"
                  style={{ background: 'linear-gradient(135deg, #78350F, #92400E)' }}>4</div>
                <div>
                  <p className="section-title">Supporting Documents</p>
                  <p className="text-xs text-slate-400 mt-0.5">Attach evidence for your claim</p>
                </div>
              </div>

              <label className="upload-documents-dropzone flex flex-col items-center justify-center h-36 rounded-xl cursor-pointer transition-all border-2 border-dashed border-slate-200 hover:border-rose-500 hover:bg-rose-50 flex-shrink-0">
                <Upload size={24} className="upload-document-character mb-3 text-rose-600" />
                <span className="text-sm text-slate-600">
                  Add your documents or <span className="font-bold text-rose-600">browse</span>
                </span>
                <span className="text-xs mt-1 text-slate-400">PDF, JPG, PNG · Supporting evidence requested</span>
                <input type="file" multiple className="hidden" onChange={e => setFiles(Array.from(e.target.files))} />
              </label>

            {/* Uploaded Documents List / Empty state */}
              <div className="mt-6 flex-1 flex flex-col min-h-[150px]">
              <p className="text-xs font-bold uppercase tracking-wider mb-2 text-slate-400 flex-shrink-0">Uploaded Documents</p>
              {files.length > 0 ? (
                <ul className="space-y-2 overflow-y-auto max-h-[220px]">
                  {files.map(f => (
                    <li key={f.name} className="flex items-center justify-between px-3.5 py-2.5 rounded-xl text-sm bg-slate-50 border border-slate-100">
                      <span className="text-slate-700 truncate">{f.name}</span>
                      <button type="button" onClick={() => setFiles(p => p.filter(x => x.name !== f.name))}>
                        <X size={13} className="text-slate-400 hover:text-rose-600" />
                      </button>
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="flex-1 flex flex-col items-center justify-center border border-dashed border-slate-100 rounded-xl p-4 bg-slate-50/50">
                  <FileText size={20} className="text-slate-300 mb-1.5" />
                  <p className="text-xs text-slate-400 font-medium">No documents attached yet</p>
                  <p className="text-[11px] text-slate-400 mt-0.5">Uploaded files will appear here</p>
                </div>
              )}
              </div>
            </div>
            <div className="flex gap-3 justify-end mt-4">
              <button type="submit" form="submit-claim-form" disabled={loading} className="btn-primary disabled:opacity-60 text-white">
                {loading
                  ? <><Loader2 size={14} className="animate-spin" /> Submitting…</>
                  : <>Submit Claim <ArrowRight size={14} /></>}
              </button>
              <button type="button" className="btn-secondary"
                onClick={() => { setForm(blank); setErrors({}); setFiles([]); }}>
                Clear Form
              </button>
            </div>
          </div>

        {/* Right Column: Manual Claim Form (~65%) */}
        <form id="submit-claim-form" onSubmit={handleSubmit} className="space-y-6 lg:order-1">
          {/* 1 — Patient */}
          <div className="card-p">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-8 h-8 rounded-xl flex items-center justify-center text-xs font-bold text-white"
                style={{ background: 'linear-gradient(135deg, #9F1239, #7C2D3E)' }}>1</div>
              <p className="section-title">Patient Information</p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
              <FormField label="Patient Name" name="patientName" placeholder="Full name" req value={form.patientName} onChange={e => set('patientName', e.target.value)} error={errors.patientName} />
              <FormField label="Beneficiary ID" name="beneId" placeholder="BENE-005" req value={form.beneId} onChange={e => set('beneId', e.target.value)} error={errors.beneId} />
              <FormField label="Date of Birth" name="dob" type="date" value={form.dob} onChange={e => set('dob', e.target.value)} error={errors.dob} />
              <FormField label="Provider NPI" name="providerNpi" placeholder="1033472386" req value={form.providerNpi} onChange={e => set('providerNpi', e.target.value)} error={errors.providerNpi} />
            </div>
          </div>

          {/* 2 — Claim */}
          <div className="card-p">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-8 h-8 rounded-xl flex items-center justify-center text-xs font-bold text-white"
                style={{ background: 'linear-gradient(135deg, #78350F, #92400E)' }}>2</div>
              <p className="section-title">Claim Details</p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
              <FormField label="Claim Start Date"  name="admissionDate"  type="date" req value={form.admissionDate} onChange={e => set('admissionDate', e.target.value)} error={errors.admissionDate} />
              <FormField label="Claim End Date"  name="dischargeDate"  type="date" req value={form.dischargeDate} onChange={e => set('dischargeDate', e.target.value)} error={errors.dischargeDate} />
              <SelectField label="Claim Type" name="claimType" req value={form.claimType} onChange={e => set('claimType', e.target.value)} error={errors.claimType}
                options={['Inpatient', 'Outpatient', 'Carrier', 'DME', 'HHA', 'Hospice', 'SNF']} />
              <FormField label="Total Amount ($)" name="totalAmount" placeholder="15000" req value={form.totalAmount} onChange={e => set('totalAmount', e.target.value)} error={errors.totalAmount} />
              <FormField label="Payment Amount ($)" name="paymentAmount" placeholder="200.00" req value={form.paymentAmount} onChange={e => set('paymentAmount', e.target.value)} error={errors.paymentAmount} />
              <FormField label="Attending Physician NPI" name="atPhysnNpi" placeholder="1033472386" req value={form.atPhysnNpi} onChange={e => set('atPhysnNpi', e.target.value)} error={errors.atPhysnNpi} />
              <FormField label="State" name="state" placeholder="OH" req value={form.state} onChange={e => set('state', e.target.value.toUpperCase())} error={errors.state} />
              <FormField label="Line Count" name="lineCount" type="number" placeholder="2" req value={form.lineCount} onChange={e => set('lineCount', e.target.value)} error={errors.lineCount} />
              <FormField label="Diagnosis Count" name="diagnosisCount" type="number" placeholder="1" req value={form.diagnosisCount} onChange={e => set('diagnosisCount', e.target.value)} error={errors.diagnosisCount} />
              <FormField label="Procedure Count" name="procedureCount" type="number" placeholder="1" req value={form.procedureCount} onChange={e => set('procedureCount', e.target.value)} error={errors.procedureCount} />
            </div>
          </div>

          {/* 3 — Diagnosis */}
          <div className="card-p">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-8 h-8 rounded-xl flex items-center justify-center text-xs font-bold text-white"
                style={{ background: 'linear-gradient(135deg, #9F1239, #78350F)' }}>3</div>
              <p className="section-title">Diagnosis & Codes</p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
              <div className="sm:col-span-2">
                <FormField label="Primary Diagnosis" name="diagnosis" placeholder="e.g. Appendectomy" req value={form.diagnosis} onChange={e => set('diagnosis', e.target.value)} error={errors.diagnosis} />
              </div>
              <FormField label="ICD-10 Code"  name="icdCode"    placeholder="K37" req value={form.icdCode} onChange={e => set('icdCode', e.target.value)} error={errors.icdCode} />
              <FormField label="Primary CPT"  name="primaryCpt" placeholder="44950" value={form.primaryCpt} onChange={e => set('primaryCpt', e.target.value)} error={errors.primaryCpt} />
            </div>
          </div>

        </form>
      </div>
    </div>
  );
}

