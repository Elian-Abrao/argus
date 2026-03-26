import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider } from './lib/auth';
import ProtectedRoute from './components/ProtectedRoute';
import PanelLayout from './layout/PanelLayout';
import AutomationsPage from './pages/AutomationsPage';
import ClientDetailPage from './pages/ClientDetailPage';
import ClientsPage from './pages/ClientsPage';
import DashboardPage from './pages/DashboardPage';
import HostDetailPage from './pages/HostDetailPage';
import HostsPage from './pages/HostsPage';
import LoginPage from './pages/LoginPage';
import NotFoundPage from './pages/NotFoundPage';
import RunDetailPage from './pages/RunDetailPage';
import RunsPage from './pages/RunsPage';
import SchedulesPage from './pages/SchedulesPage';
import AdminUsersPage from './pages/AdminUsersPage';
import ProfilePage from './pages/ProfilePage';

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            element={
              <ProtectedRoute>
                <PanelLayout />
              </ProtectedRoute>
            }
          >
            <Route path="/" element={<DashboardPage />} />
            <Route path="/hosts" element={<HostsPage />} />
            <Route path="/hosts/:hostId" element={<HostDetailPage />} />
            <Route path="/automations" element={<AutomationsPage />} />
            <Route path="/automations/:automationId/runs" element={<RunsPage />} />
            <Route path="/instances/:instanceId/runs" element={<RunsPage />} />
            <Route path="/clients" element={<ClientsPage />} />
            <Route path="/clients/:clientId" element={<ClientDetailPage />} />
            <Route path="/runs" element={<RunsPage />} />
            <Route path="/runs/:runId" element={<RunDetailPage />} />
            <Route path="/schedules" element={<SchedulesPage />} />
            <Route path="/profile" element={<ProfilePage />} />
            <Route path="/admin/users" element={<AdminUsersPage />} />
            <Route path="/404" element={<NotFoundPage />} />
            <Route path="*" element={<Navigate to="/404" replace />} />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
