import { useState, useEffect } from 'react';
import { Upload, FileText, CheckCircle, AlertTriangle, Clock, X, Download } from 'lucide-react';
import Badge from '../../components/ui/Badge';
import Select from '../../components/ui/Select';
import { claimsAPI } from '../../services/api';

const statusIcon = {
  verified: <CheckCircle size={13} style={{ color: '#3d6b4a' }} />,
  flagged: <AlertTriangle size={13} style={{ color: '#d97706' }} />,
  under_review: <Clock size={13} style={{ color: '#b45309' }} />,
};

export default function DocumentCenter() {
  const [docList, setDocList] = useState([]);
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [done, setDone] = useState(false);
  const [claimId, setClaimId] = useState('');
  const [docType, setDocType] = useState('');

  useEffect(() => {
    let isMounted = true;
    claimsAPI.getAll()
      .then(res => {
        if (Array.isArray(res) && isMounted) {
          const docs = [];
          res.forEach(c => {
            if (c.raw_extracted_features) {
              docs.push({
                id: `DOC-${c.id}`,
                name: `Claim_Document_${c.claim_number || c.id}.pdf`,
                type: c.claim_type ? c.claim_type.toUpperCase() : 'Claim Form',
                uploadedDate: c.submission_date || c.created_at ? c.created_at.split('T')[0] : '2026-08-21',
                size: '2.4 MB',
                status: c.status === 'approved' ? 'verified' : (c.status === 'flagged' ? 'flagged' : 'under_review'),
                claimId: c.claim_number || `CLM-${c.id}`,
              });
            }
          });
          setDocList(docs);
        }
      })
      .catch(() => { });
    return () => { isMounted = false; };
  }, []);

  const handleUpload = async () => {
    if (!files.length) return;
    setUploading(true);
    await new Promise(r => setTimeout(r, 1000));
    setUploading(false); setDone(true); setFiles([]);
    setTimeout(() => setDone(false), 3000);
  };

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="rounded-2xl p-5 text-white relative overflow-hidden"
        style={{ background: 'linear-gradient(135deg, #9F1239, #7C2D3E, #78350F)' }}>
        <div className="absolute -top-8 -right-8 w-40 h-40 rounded-full opacity-10" style={{ background: '#F5E6E9' }} />
        <div className="relative z-10">
          <h2 className="text-xl font-bold">Document Center</h2>
          <p className="text-sm mt-0.5" style={{ color: 'rgba(219,234,254,0.85)' }}>Upload and manage claim supporting documents.</p>
        </div>
      </div>

      {/* Status summary */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { label: 'Verified', count: docList.filter(d => d.status === 'verified').length, card: 'card-sage' },
          { label: 'Under Review', count: docList.filter(d => d.status === 'under_review').length, card: 'card-amber' },
          { label: 'Flagged', count: docList.filter(d => d.status === 'flagged').length, card: 'card-brown' },
        ].map(({ label, count, card }) => (
          <div key={label} className={card}>
            <p className="text-2xl font-bold text-white">{count}</p>
            <p className="text-sm mt-1 font-medium" style={{ color: 'rgba(255,255,255,0.8)' }}>{label}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Upload panel */}
        <div className="card-p space-y-4">
          <p className="section-title">Upload Document</p>
          <div>
            <label className="label">Claim ID</label>
            <input className="input" placeholder="CLM-2026-0001" value={claimId} onChange={e => setClaimId(e.target.value)} />
          </div>
          <div>
            <Select
              label="Document Type"
              value={docType}
              onChange={(val) => setDocType(val)}
              placeholder="Select type…"
              options={['Claim Form', 'Medical Records', 'Operative Report', 'Lab Report', 'Authorization', 'Other'].map(o => ({ value: o, label: o }))}
            />
          </div>
          <label className="flex flex-col items-center justify-center h-28 rounded-xl cursor-pointer transition-all border border-dashed border-slate-200 hover:border-rose-500 hover:bg-rose-50">
            <Upload size={18} className="mb-1.5 text-slate-400" />
            <span className="text-sm text-slate-600">
              Drop or <span className="font-bold text-rose-600">browse</span>
            </span>
            <span className="text-xs mt-0.5 text-slate-400">PDF, JPG, PNG</span>
            <input type="file" multiple className="hidden" onChange={e => setFiles(Array.from(e.target.files))} />
          </label>
          {files.length > 0 && (
            <ul className="space-y-1.5">
              {files.map(f => (
                <li key={f.name} className="flex items-center justify-between px-3 py-2 rounded-xl text-xs bg-slate-50 border border-slate-200">
                  <span className="text-slate-700 truncate">{f.name}</span>
                  <button onClick={() => setFiles(p => p.filter(x => x.name !== f.name))}>
                    <X size={12} className="text-slate-400 hover:text-red-500" />
                  </button>
                </li>
              ))}
            </ul>
          )}
          <button onClick={handleUpload} disabled={!files.length || uploading}
            className="btn-primary w-full justify-center disabled:opacity-50">
            {uploading ? 'Uploading…' : done ? '✓ Uploaded!' : 'Upload Files'}
          </button>
        </div>

        {/* Document list */}
        <div className="card overflow-hidden lg:col-span-2">
          <div className="px-5 py-4 border-b border-slate-100">
            <p className="section-title">All Documents ({docList.length})</p>
          </div>
          <div className="divide-y divide-slate-100">
            {docList.map(doc => (
              <div key={doc.id} className="flex items-center gap-4 px-5 py-3.5 transition-colors hover:bg-slate-50">
                <div className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 text-white bg-gradient-to-br from-[#9f1239] to-[#92400e]">
                  <FileText size={15} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-slate-900 truncate">{doc.name}</p>
                  <p className="text-xs text-slate-400">{doc.type} · {doc.uploadedDate} · {doc.size}</p>
                </div>
                <div className="flex items-center gap-3 flex-shrink-0">
                  <span className="text-xs font-mono text-slate-400">{doc.claimId}</span>
                  <div className="flex items-center gap-1.5">
                    {statusIcon[doc.status]}
                    <Badge status={doc.status} size="xs" />
                  </div>
                  <button className="w-8 h-8 flex items-center justify-center rounded-xl transition-colors text-slate-400 hover:bg-rose-50 hover:text-rose-600">
                    <Download size={14} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Checklist */}
      <div className="card-p">
        <p className="section-title mb-4">Required Document Checklist</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {[
            { label: 'Claim Form (UB-04 / CMS-1500)', req: true },
            { label: 'Operative Report (if surgery)', req: true },
            { label: 'Medical Records', req: true },
            { label: 'Anesthesia Records', req: false },
            { label: 'Lab / Pathology Report', req: false },
            { label: 'Prior Authorization', req: false },
          ].map(item => (
            <div key={item.label} className="flex items-center gap-2.5 px-3.5 py-3 rounded-xl bg-slate-50 border border-slate-200">
              <CheckCircle size={14} style={{ color: item.req ? '#4A7C59' : '#cbd5e1' }} />
              <span className="text-sm text-slate-700 font-medium flex-1">{item.label}</span>
              {item.req && (
                <span className="text-xs font-bold px-1.5 py-0.5 rounded-full bg-red-50 text-red-600">Req.</span>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
