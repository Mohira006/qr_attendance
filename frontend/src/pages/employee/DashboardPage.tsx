import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, CalendarCheck, Clock, QrCode, TrendingUp } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { QrScannerModal } from "@/components/attendance/QrScannerModal";
import { StatCard } from "@/components/attendance/StatCard";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";
import { attendanceApi } from "@/services/attendanceApi";
import { employeesApi } from "@/services/employeesApi";
import { formatDateShort, formatMinutes, formatTime } from "@/utils/format";
import { attendanceStatusTokens, checkoutStatusLabelKey } from "@/utils/status";

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

export function EmployeeDashboardPage() {
  const { t } = useTranslation();
  const [showScanner, setShowScanner] = useState(false);
  const meQuery = useQuery({ queryKey: ["employees", "me"], queryFn: employeesApi.me });
  const employeeId = meQuery.data?.id;

  const historyQuery = useQuery({
    queryKey: ["attendance", "employee", employeeId, "recent"],
    queryFn: () => attendanceApi.forEmployee(employeeId as number, { page_size: 5 }),
    enabled: employeeId !== undefined,
  });
  const summaryQuery = useQuery({
    queryKey: ["attendance", "employee", employeeId, "summary"],
    queryFn: () => attendanceApi.summary(employeeId as number),
    enabled: employeeId !== undefined,
  });

  if (meQuery.isLoading) return <LoadingState label={t("common.loading")} />;
  if (meQuery.isError || !meQuery.data) {
    return <ErrorState message={t("employeeDashboard.notLinked")} />;
  }

  const employee = meQuery.data;
  const today = historyQuery.data?.items.find((record) => record.date === todayIso());

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-semibold text-ink">{t("employeeDashboard.welcomeBack", { name: employee.first_name })}</h1>
        <p className="text-sm text-ink-muted">
          {employee.department.name} · {employee.position ?? employee.employee_id}
        </p>
      </div>

      <Card>
        <CardHeader>
          <h2 className="font-display text-base font-semibold text-ink">{t("employeeDashboard.today")}</h2>
          <Button size="sm" onClick={() => setShowScanner(true)}>
            <QrCode size={16} className="mr-1.5" /> {t("employeeDashboard.scanButton")}
          </Button>
        </CardHeader>
        <CardBody>
          {today ? (
            <div className="flex flex-wrap items-center gap-8">
              <div>
                <p className="text-xs text-ink-muted">{t("attendance.columns.arrival")}</p>
                <p className="font-mono text-2xl font-semibold tabular-nums text-ink">{formatTime(today.check_in)}</p>
              </div>
              <div>
                <p className="text-xs text-ink-muted">{t("attendance.columns.departure")}</p>
                <p className="font-mono text-2xl font-semibold tabular-nums text-ink">
                  {today.check_out ? formatTime(today.check_out) : t(checkoutStatusLabelKey(today.checkout_status))}
                </p>
              </div>
              <div>
                <p className="text-xs text-ink-muted">{t("attendance.columns.status")}</p>
                <div className="mt-1">
                  <StatusBadge tokens={attendanceStatusTokens(today.status)} />
                </div>
              </div>
              {today.late_minutes > 0 && (
                <div>
                  <p className="text-xs text-ink-muted">{t("attendance.columns.lateBy")}</p>
                  <p className="font-medium text-status-danger">{formatMinutes(today.late_minutes)}</p>
                </div>
              )}
            </div>
          ) : (
            <p className="text-sm text-ink-muted">{t("employeeDashboard.notCheckedInYet")}</p>
          )}
        </CardBody>
      </Card>

      {summaryQuery.data && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <StatCard
            label={t("employeeDashboard.onTimeMonth")}
            value={summaryQuery.data.on_time_count}
            icon={<Clock size={20} />}
            accentClass="bg-status-success-bg text-status-success"
          />
          <StatCard
            label={t("employeeDashboard.lateMonth")}
            value={summaryQuery.data.late_count}
            icon={<AlertTriangle size={20} />}
            accentClass="bg-status-danger-bg text-status-danger"
          />
          <StatCard label={t("employeeDashboard.attendanceRate")} value={`${summaryQuery.data.attendance_percentage}%`} icon={<TrendingUp size={20} />} />
          <StatCard
            label={t("employeeDashboard.hoursWorkedMonth")}
            value={formatMinutes(summaryQuery.data.total_working_minutes)}
            icon={<CalendarCheck size={20} />}
          />
        </div>
      )}

      <Card>
        <CardHeader>
          <h2 className="font-display text-base font-semibold text-ink">{t("employeeDashboard.recentAttendance")}</h2>
        </CardHeader>
        <CardBody className="p-0">
          {historyQuery.data && historyQuery.data.items.length > 0 ? (
            <table className="w-full text-left text-sm">
              <tbody>
                {historyQuery.data.items.map((record) => (
                  <tr key={record.id} className="border-b border-line last:border-0">
                    <td className="px-5 py-3 text-ink-muted">{formatDateShort(record.date)}</td>
                    <td className="px-5 py-3 font-mono tabular-nums">{formatTime(record.check_in)}</td>
                    <td className="px-5 py-3 font-mono tabular-nums text-ink-muted">
                      {record.check_out ? formatTime(record.check_out) : "-"}
                    </td>
                    <td className="px-5 py-3">
                      <StatusBadge tokens={attendanceStatusTokens(record.status)} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <EmptyState title={t("employeeDashboard.noHistoryYet")} />
          )}
        </CardBody>
      </Card>

      {showScanner && <QrScannerModal onClose={() => setShowScanner(false)} />}
    </div>
  );
}
