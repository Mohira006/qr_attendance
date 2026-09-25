import { Outlet } from "react-router-dom";

import { HrSidebar } from "@/components/layout/HrSidebar";
import { HrTopbar } from "@/components/layout/HrTopbar";
import { useSettings } from "@/hooks/useSettings";

export function HrLayout() {
  useSettings();

  return (
    <div className="flex h-screen overflow-hidden bg-canvas">
      <HrSidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <HrTopbar />
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
