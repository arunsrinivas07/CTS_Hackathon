import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { InvestigationProvider } from './context/InvestigationContext';
import AppLayout from './components/layout/AppLayout';
import ProtectedRoute from './components/layout/ProtectedRoute';

// Auth
import Login from './pages/Login';
import Signup from './pages/Signup';
import Settings from './pages/Settings';

// Provider pages
import ProviderDashboard from './pages/provider/ProviderDashboard';
import SubmitClaim from './pages/provider/SubmitClaim';
import SubmittedClaims from './pages/provider/SubmittedClaims';
import ClaimTimeline from './pages/provider/ClaimTimeline';
import DocumentCenter from './pages/provider/DocumentCenter';
import FacilityProfile from './pages/provider/FacilityProfile';

// Investigator pages
import CommandCenter from './pages/investigator/CommandCenter';
import InvestigationQueue from './pages/investigator/InvestigationQueue';
import ClaimsRepository from './pages/investigator/ClaimsRepository';
import DocumentVerification from './pages/investigator/DocumentVerification';
import ProviderIntelligence from './pages/investigator/ProviderIntelligence';
import CaseDetail from './pages/investigator/CaseDetail';
import AIAnalysis from './pages/investigator/AIAnalysis';
import AICopilot from './pages/investigator/AICopilot';
import DecisionNotes from './pages/investigator/DecisionNotes';
import Reports from './pages/investigator/Reports';

// Admin pages
import ExecutiveDashboard from './pages/admin/ExecutiveDashboard';
import AllInvestigations from './pages/admin/AllInvestigations';
import ProviderRiskMatrix from './pages/admin/ProviderRiskMatrix';
import WorkloadStaffing from './pages/admin/WorkloadStaffing';
import InvestigationManagement from './pages/admin/InvestigationManagement';
import ProviderDetails from './pages/admin/ProviderDetails';
import InvestigatorAssignment from './pages/admin/InvestigatorAssignment';
import SystemAlerts from './pages/admin/SystemAlerts';

function RootRedirect() {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="w-8 h-8 border-4 border-rose-600 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;
  const roleHome = { provider: '/provider', investigator: '/investigator', admin: '/admin' };
  return <Navigate to={roleHome[user.role] || '/login'} replace />;
}


function AppRoutes() {
  return (
    <Routes>
      {/* Public */}
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<Signup />} />

      {/* Root redirect */}
      <Route path="/" element={<RootRedirect />} />

      {/* ── Provider Portal ── */}
      <Route element={<ProtectedRoute allowedRole="provider" />}>
        <Route element={<AppLayout />}>
          <Route path="/provider" element={<ProviderDashboard />} />
          <Route path="/provider/submit" element={<SubmitClaim />} />
          <Route path="/provider/claims" element={<SubmittedClaims />} />
          <Route path="/provider/timeline" element={<ClaimTimeline />} />
          <Route path="/provider/timeline/:claimId" element={<ClaimTimeline />} />
          <Route path="/claims/:claimId" element={<ClaimTimeline />} />
          <Route path="/provider/documents" element={<DocumentCenter />} />
          <Route path="/provider/profile" element={<FacilityProfile />} />
          <Route path="/provider/settings" element={<Settings />} />
        </Route>
      </Route>

      {/* ── Investigator Portal ── */}
      <Route element={<ProtectedRoute allowedRole="investigator" />}>
        <Route element={<AppLayout />}>
          <Route path="/investigator" element={<CommandCenter />} />
          <Route path="/investigator/queue" element={<InvestigationQueue />} />
          <Route path="/investigator/claims" element={<ClaimsRepository />} />
          <Route path="/investigator/documents" element={<DocumentVerification />} />
          <Route path="/investigator/documents/:claimId" element={<DocumentVerification />} />
          <Route path="/investigator/providers" element={<ProviderIntelligence />} />
          <Route path="/investigator/case" element={<CaseDetail />} />
          <Route path="/investigator/case/:id" element={<CaseDetail />} />
          <Route path="/investigations/:id" element={<CaseDetail />} />
          <Route path="/claims/:claimId" element={<ClaimTimeline />} />
          <Route path="/investigator/reports" element={<Reports />} />
          <Route path="/investigator/ai-analysis" element={<AIAnalysis />} />
          <Route path="/investigator/ai-copilot" element={<AICopilot />} />
          <Route path="/investigator/decisions" element={<DecisionNotes />} />
          <Route path="/investigator/settings" element={<Settings />} />
        </Route>
      </Route>

      {/* ── Admin Portal ── */}
      <Route element={<ProtectedRoute allowedRole="admin" />}>
        <Route element={<AppLayout />}>
          <Route path="/admin" element={<ExecutiveDashboard />} />
          <Route path="/admin/investigations" element={<AllInvestigations />} />
          <Route path="/admin/risk-matrix" element={<ProviderRiskMatrix />} />
          <Route path="/admin/workload" element={<WorkloadStaffing />} />
          <Route path="/admin/inv-management" element={<InvestigationManagement />} />
          <Route path="/admin/providers" element={<ProviderDetails />} />
          <Route path="/admin/assignments" element={<InvestigatorAssignment />} />
          <Route path="/admin/alerts" element={<SystemAlerts />} />
          <Route path="/admin/settings" element={<Settings />} />
        </Route>
      </Route>

      {/* Catch-all */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <InvestigationProvider>
          <AppRoutes />
        </InvestigationProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
