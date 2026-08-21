import { useState, useEffect } from 'react';
import { Building2, Phone, Mail, MapPin, Edit2, Save, X, CheckCircle } from 'lucide-react';
import PageHeader from '../../components/ui/PageHeader';
import Badge from '../../components/ui/Badge';
import { Link } from 'react-router-dom';
import { providers as initialProviders, claims as initialClaims } from '../../data/mockData';
import { useAuth } from '../../context/AuthContext';
import { claimsAPI, providersAPI } from '../../services/api';

export default function FacilityProfile() {
  const { user } = useAuth();
  const [editing, setEditing] = useState(false);
  const [saved, setSaved] = useState(false);
  const [claimList, setClaimList] = useState(initialClaims.filter(c => c.providerId === 'PRV-001' || !c.providerId));

  const defaultFacilityName = user?.name ? (user.name.includes('Dr.') ? `${user.name}'s Practice` : `${user.name} Medical Center`) : 'Riverside Medical Center';

  const [form, setForm] = useState(() => {
    const savedProfile = localStorage.getItem(`cg_facility_${user?.id}`);
    if (savedProfile) {
      try { return JSON.parse(savedProfile); } catch { /* fallback */ }
    }
    return {
      name: defaultFacilityName,
      phone: '+1 (555) 234-5678',
      contact: user?.email || 'provider@claimguard.ai',
      location: 'Los Angeles, CA',
      type: 'General & Surgical Hospital',
      npi: '1093847291',
      specialties: ['General Surgery', 'Internal Medicine', 'Cardiology', 'Radiology'],
      status: 'active',
      enrolledDate: 'Jan 2023',
    };
  });

  useEffect(() => {
    claimsAPI.getAll()
      .then(res => {
        if (Array.isArray(res) && res.length > 0) {
          const mapped = res.map(c => ({
            id: c.claim_number || `CLM-${c.id}`,
            realId: c.id,
            patient: `Patient #${c.patient_id}`,
            amount: parseFloat(c.total_billed_amount || 0),
            status: c.status === 'paid' ? 'approved' : (c.status === 'denied' ? 'rejected' : (c.status === 'processing' ? 'under_review' : c.status)),
            priority: c.status === 'flagged' ? 'high' : 'low',
          }));
          setClaimList(mapped);
        }
      })
      .catch(() => { /* keep initial */ });
  }, []);

  const facilityClaims = claimList;

  const handleSave = async () => {
    localStorage.setItem(`cg_facility_${user?.id}`, JSON.stringify(form));
    setEditing(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };


  return (
    <div className="w-full max-w-[1600px] mx-auto space-y-6">
      <PageHeader
        title="Facility Profile"
        subtitle="View and manage your facility information."
        actions={
          editing ? (
            <div className="flex gap-2">
              <button className="btn-primary" onClick={handleSave}><Save size={15} /> Save Changes</button>
              <button className="btn-secondary" onClick={() => setEditing(false)}><X size={15} /> Cancel</button>
            </div>
          ) : (
            <button className="btn-secondary" onClick={() => setEditing(true)}><Edit2 size={15} /> Edit Profile</button>
          )
        }
      />

      {saved && (
        <div className="flex items-center gap-2 px-4 py-2.5 bg-emerald-50 border border-emerald-200 rounded-lg mb-5 text-sm text-emerald-700">
          <CheckCircle size={15} /> Profile updated successfully.
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Info */}
        <div className="card p-5 lg:col-span-2">
          <div className="flex items-center gap-4 mb-5 pb-5 border-b border-slate-100">
            <div className="p-4 bg-rose-50 rounded-xl">
              <Building2 size={28} className="text-rose-600" />
            </div>
            <div>
              {editing ? (
                <input className="input text-lg font-semibold" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />
              ) : (
                <h2 className="text-lg font-semibold text-slate-900">{form.name}</h2>
              )}
              <p className="text-sm text-slate-500">{form.type} · NPI: {form.npi}</p>
              <div className="flex items-center gap-2 mt-1">
                <Badge status={form.status} />
                <span className="text-xs text-slate-400">Enrolled {form.enrolledDate}</span>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="label"><Phone size={12} className="inline mr-1" />Phone</label>
              {editing ? (
                <input className="input" value={form.phone} onChange={e => setForm(f => ({ ...f, phone: e.target.value }))} />
              ) : (
                <p className="text-sm text-slate-800">{form.phone}</p>
              )}
            </div>
            <div>
              <label className="label"><Mail size={12} className="inline mr-1" />Email</label>
              {editing ? (
                <input className="input" value={form.contact} onChange={e => setForm(f => ({ ...f, contact: e.target.value }))} />
              ) : (
                <p className="text-sm text-slate-800">{form.contact}</p>
              )}
            </div>
            <div className="sm:col-span-2">
              <label className="label"><MapPin size={12} className="inline mr-1" />Location</label>
              {editing ? (
                <input className="input" value={form.location} onChange={e => setForm(f => ({ ...f, location: e.target.value }))} />
              ) : (
                <p className="text-sm text-slate-800">{form.location}</p>
              )}
            </div>
            <div className="sm:col-span-2">
              <label className="label">Specialties</label>
              <div className="flex flex-wrap gap-2">
                {(form.specialties || ['General Medicine', 'Surgery']).map(s => (
                  <span key={s} className="text-xs px-2.5 py-1 bg-rose-50 text-rose-700 border border-rose-100 rounded-full font-medium">{s}</span>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Stats */}
        <div className="card p-5 flex flex-col justify-between">
          <div>
            <p className="text-xs text-slate-500 mb-4 font-semibold uppercase tracking-wide">Claims Overview</p>
            <div className="space-y-4">
              {[
                { label: 'Total Claims', value: facilityClaims.length },
                { label: 'Approved', value: facilityClaims.filter(c => c.status === 'approved' || c.status === 'paid').length, color: 'text-emerald-600' },
                { label: 'Flagged', value: facilityClaims.filter(c => c.status === 'flagged' || c.status === 'under_review').length, color: 'text-amber-600' },
                { label: 'Rejected', value: facilityClaims.filter(c => c.status === 'rejected' || c.status === 'denied').length, color: 'text-red-500' },
                { label: 'Total Billed', value: `$${(facilityClaims.reduce((s, c) => s + (c.amount || 0), 0) / 1000).toFixed(0)}k` },
              ].map(({ label, value, color }) => (
                <div key={label} className="flex items-center justify-between pb-2 border-b border-slate-50 last:border-0">
                  <span className="text-sm text-slate-600 font-medium">{label}</span>
                  <span className={`text-sm font-bold ${color || 'text-slate-800'}`}>{value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>


      {/* Recent Activity */}
      <div className="card">
        <div className="px-5 py-4 border-b border-slate-100">
          <h3 className="section-title">Recent Claim Activity</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr>
                {['Claim ID', 'Patient', 'Amount', 'Status', 'Priority'].map(h => (
                  <th key={h} className="table-header">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {facilityClaims.slice(0, 5).map(c => (
                <tr key={c.id} className="table-row">
                  <td className="table-cell font-mono text-xs text-rose-700 font-semibold">
                    <Link to={`/claims/${c.id}`} className="hover:underline">{c.id}</Link>
                  </td>
                  <td className="table-cell font-medium">{c.patient}</td>
                  <td className="table-cell font-semibold">${c.amount.toLocaleString()}</td>
                  <td className="table-cell"><Badge status={c.status} /></td>
                  <td className="table-cell"><Badge status={c.priority} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
