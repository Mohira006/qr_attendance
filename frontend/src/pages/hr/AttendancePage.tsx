import { useQuery } from "@tanstack/react-query";
import { LayoutGrid, List } from "lucide-react";
import { useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { AttendanceCards } from "@/components/attendance/AttendanceCards";
import { AttendanceTable } from "@/components/attendance/AttendanceTable";
import { Avatar } from "@/components/attendance/Avatar";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Input, Select } from "@/components/ui/Input";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { attendanceApi } from "@/services/attendanceApi";
import { departmentsApi } from "@/services/employeesApi";
import type { EmployeeBrief } from "@/types/models";
import { cn } from "@/utils/cn";

type ViewMode = "table" | "cards";

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

export function AttendancePage() {
  const { t } = useTranslation();
  const [view, setView] = useState<ViewMode>("table");
  const [date, setDate] = useState(todayIso);
  const [departmentId, setDepartmentId] = useState("");

  const departmentsQuery = useQuery({ queryKey: ["departments"], queryFn: () => departmentsApi.list("active") });
  const overviewQuery = useQuery({
    queryKey: ["attendance", "today", date, departmentId],
    queryFn: () => attendanceApi.today({ date, department_id: departmentId ? Number(departmentId) : undefined }),
  });

  const overview = overviewQuery.data;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-semibold text-ink">{t("attendance.title")}</h1>
          <p className="text-sm text-ink-muted">{t("attendance.subtitle")}</p>
        </div>
        <div className="flex items-center gap-1 rounded-lg border border-line bg-white p-1">
          <ViewToggleButton active={view === "table"} onClick={() => setView("table")} icon={<List size={16} />} label={t("attendance.table")} />
          <ViewToggleButton active={view === "cards"} onClick={() => setView("cards")} icon={<LayoutGrid size={16} />} label={t("attendance.cards")} />
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <Input type="date" value={date} onChange={(event) => setDate(event.target.value)} className="w-44" max={todayIso()} />
        <Select value={departmentId} onChange={(event) => setDepartmentId(event.target.value)} className="w-48">
          <option value="">{t("common.allDepartments")}</option>
          {departmentsQuery.data?.map((department) => (
            <option key={department.id} value={department.id}>
              {department.name}
            </option>
          ))}
        </Select>
        {date !== todayIso() && (
          <button type="button" onClick={() => setDate(todayIso())} className="text-sm font-medium text-brand hover:text-brand-hover">
            {t("common.backToToday")}
          </button>
        )}
      </div>

      {overviewQuery.isLoading && <LoadingState label={t("common.loading")} />}
      {overviewQuery.isError && <ErrorState message={t("attendance.couldNotLoad")} />}

      {overview && (
        <>
          <Card>
            <CardBody>
              {view === "table" ? (
                <AttendanceTable onTime={overview.on_time} late={overview.late} />
              ) : (
                <AttendanceCards onTime={overview.on_time} late={overview.late} />
              )}
            </CardBody>
          </Card>

          {(overview.absent.length > 0 || overview.on_leave.length > 0) && (
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              {overview.absent.length > 0 && (
                <EmployeeChipGroup title={t("attendance.absentCount", { count: overview.absent.length })} employees={overview.absent} />
              )}
              {overview.on_leave.length > 0 && (
                <EmployeeChipGroup title={t("attendance.onLeaveCount", { count: overview.on_leave.length })} employees={overview.on_leave} />
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

function ViewToggleButton({ active, onClick, icon, label }: { active: boolean; onClick: () => void; icon: ReactNode; label: string }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={cn(
        "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
        active ? "bg-brand text-white" : "text-ink-muted hover:text-ink",
      )}
    >
      {icon}
      {label}
    </button>
  );
}

function EmployeeChipGroup({ title, employees }: { title: string; employees: EmployeeBrief[] }) {
  return (
    <Card>
      <CardHeader>
        <h2 className="font-display text-base font-semibold text-ink">{title}</h2>
      </CardHeader>
      <CardBody className="flex flex-wrap gap-3">
        {employees.map((employee) => (
          <div key={employee.id} className="flex items-center gap-2 rounded-lg border border-line px-3 py-2">
            <Avatar employee={employee} size={28} />
            <div>
              <p className="text-sm font-medium text-ink">{employee.full_name}</p>
              <p className="font-mono text-xs text-ink-muted">{employee.employee_id}</p>
            </div>
          </div>
        ))}
      </CardBody>
    </Card>
  );
}
