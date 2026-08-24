import { Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import Sidebar from './Sidebar';
import Navbar from './Navbar';
import FloatingAIChat from '../investigator/FloatingAIChat';

export default function AppLayout() {
  const { pathname } = useLocation();
  const { user } = useAuth();
  const isInvestigator = user?.role === 'investigator';

  return (
    <div className="app-shell relative">
      <Sidebar />
      <div className="main-area">
        <Navbar currentPath={pathname} />
        <main className="content-area">
          <Outlet />
        </main>
      </div>
      {isInvestigator && <FloatingAIChat />}
    </div>
  );
}
