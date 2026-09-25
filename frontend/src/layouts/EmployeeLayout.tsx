import { Outlet } from "react-router-dom";

import { EmployeeSidebar } from "@/components/layout/EmployeeSidebar";
import { EmployeeTopbar } from "@/components/layout/EmployeeTopbar";
import { useSettings } from "@/hooks/useSettings";

export function EmployeeLayout() {
  useSettings();

  return (
    <div className="flex h-screen overflow-hidden bg-canvas">
      <EmployeeSidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <EmployeeTopbar />
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
