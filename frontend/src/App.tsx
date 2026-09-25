import { Navigate, Route, Routes } from "react-router-dom";

import { RequireAuth, RequireRole, homeForRole } from "@/components/RouteGuards";
import { useAuth } from "@/contexts/AuthContext";
import { EmployeeLayout } from "@/layouts/EmployeeLayout";
import { HrLayout } from "@/layouts/HrLayout";
import { LoginPage } from "@/pages/auth/LoginPage";
import { ScanPage } from "@/pages/ScanPage";
import { EmployeeDashboardPage } from "@/pages/employee/DashboardPage";
import { EmployeeExplanationLettersPage } from "@/pages/employee/ExplanationLettersPage";
import { EmployeeHistoryPage } from "@/pages/employee/HistoryPage";
import { EmployeeLeavePage } from "@/pages/employee/LeavePage";
import { EmployeeProfilePage } from "@/pages/employee/ProfilePage";
import { AttendancePage } from "@/pages/hr/AttendancePage";
import { DashboardPage } from "@/pages/hr/DashboardPage";
import { DepartmentsPage } from "@/pages/hr/DepartmentsPage";
import { EmployeesPage } from "@/pages/hr/EmployeesPage";
import { ExplanationLettersPage } from "@/pages/hr/ExplanationLettersPage";
import { LeaveManagementPage } from "@/pages/hr/LeaveManagementPage";
import { HrNotificationsPage } from "@/pages/hr/NotificationsPage";
import { HrProfilePage } from "@/pages/hr/ProfilePage";
import { QrCodePage } from "@/pages/hr/QrCodePage";
import { ReportsPage } from "@/pages/hr/ReportsPage";
import { HrSettingsPage } from "@/pages/hr/SettingsPage";

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/scan"
        element={
          <RequireAuth>
            <ScanPage />
          </RequireAuth>
        }
      />

      <Route
        path="/hr"
        element={
          <RequireAuth>
            <RequireRole role="hr">
              <HrLayout />
            </RequireRole>
          </RequireAuth>
        }
      >
        <Route index element={<Navigate to="dashboard" replace />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="attendance" element={<AttendancePage />} />
        <Route path="employees" element={<EmployeesPage />} />
        <Route path="departments" element={<DepartmentsPage />} />
        <Route path="leave-management" element={<LeaveManagementPage />} />
        <Route path="explanation-letters" element={<ExplanationLettersPage />} />
        <Route path="notifications" element={<HrNotificationsPage />} />
        <Route path="reports" element={<ReportsPage />} />
        <Route path="qr-code" element={<QrCodePage />} />
        <Route path="settings" element={<HrSettingsPage />} />
        <Route path="profile" element={<HrProfilePage />} />
      </Route>

      <Route
        path="/me"
        element={
          <RequireAuth>
            <RequireRole role="employee">
              <EmployeeLayout />
            </RequireRole>
          </RequireAuth>
        }
      >
        <Route index element={<Navigate to="dashboard" replace />} />
        <Route path="dashboard" element={<EmployeeDashboardPage />} />
        <Route path="history" element={<EmployeeHistoryPage />} />
        <Route path="leave" element={<EmployeeLeavePage />} />
        <Route path="explanation-letters" element={<EmployeeExplanationLettersPage />} />
        <Route path="profile" element={<EmployeeProfilePage />} />
      </Route>

      <Route path="/" element={<RootRedirect />} />
      <Route path="*" element={<RootRedirect />} />
    </Routes>
  );
}

function RootRedirect() {
  const { user, isLoading } = useAuth();
  if (isLoading) return null;
  if (!user) return <Navigate to="/login" replace />;
  return <Navigate to={homeForRole(user.role)} replace />;
}
