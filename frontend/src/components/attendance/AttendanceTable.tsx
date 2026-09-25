import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { Avatar } from "@/components/attendance/Avatar";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { EmptyState } from "@/components/ui/States";
import { useFlashOnUpdate } from "@/hooks/useFlashOnUpdate";
import { explanationLettersApi } from "@/services/explanationLettersApi";
import type { AttendanceResponse } from "@/types/models";
import { cn } from "@/utils/cn";
import { formatDateShort, formatMinutes, formatTime } from "@/utils/format";
import { attendanceStatusTokens, checkoutStatusLabelKey } from "@/utils/status";

const COLUMN_COUNT = 9;

export function AttendanceTable({ onTime, late }: { onTime: AttendanceResponse[]; late: AttendanceResponse[] }) {
  const { t } = useTranslation();

  if (onTime.length === 0 && late.length === 0) {
    return <EmptyState title={t("attendance.noAttendanceYet")} description={t("attendance.noAttendanceYetDescription")} />;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-line text-xs uppercase tracking-wide text-ink-muted">
            <th className="px-4 py-3 font-medium">{t("attendance.columns.status")}</th>
            <th className="px-4 py-3 font-medium">{t("attendance.columns.employee")}</th>
            <th className="px-4 py-3 font-medium">{t("attendance.columns.employeeId")}</th>
            <th className="px-4 py-3 font-medium">{t("attendance.columns.department")}</th>
            <th className="px-4 py-3 font-medium">{t("attendance.columns.date")}</th>
            <th className="px-4 py-3 font-medium">{t("attendance.columns.checkIn")}</th>
            <th className="px-4 py-3 font-medium">{t("attendance.columns.checkOut")}</th>
            <th className="px-4 py-3 font-medium">{t("attendance.columns.lateDuration")}</th>
            <th className="px-4 py-3 font-medium" />
          </tr>
        </thead>
        {onTime.length > 0 && (
          <tbody>
            <SectionHeader label={`${t("common.status.onTime")} (${onTime.length})`} colorClass="bg-status-success-bg text-status-success" />
            {onTime.map((attendance) => (
              <AttendanceRow key={attendance.id} attendance={attendance} />
            ))}
          </tbody>
        )}
        {late.length > 0 && (
          <tbody>
            <SectionHeader label={`${t("common.status.late")} (${late.length})`} colorClass="bg-status-danger-bg text-status-danger" />
            {late.map((attendance) => (
              <AttendanceRow key={attendance.id} attendance={attendance} />
            ))}
          </tbody>
        )}
      </table>
    </div>
  );
}

function SectionHeader({ label, colorClass }: { label: string; colorClass: string }) {
  return (
    <tr>
      <td colSpan={COLUMN_COUNT} className={cn("px-4 py-1.5 text-xs font-semibold uppercase tracking-wide", colorClass)}>
        {label}
      </td>
    </tr>
  );
}

function AttendanceRow({ attendance }: { attendance: AttendanceResponse }) {
  const { t } = useTranslation();
  const tokens = attendanceStatusTokens(attendance.status);
  const flashing = useFlashOnUpdate(attendance.id);

  return (
    <tr
      className={cn(
        "border-b border-l-2 border-line last:border-b-0 hover:bg-canvas",
        tokens.border,
        flashing && (attendance.status === "on_time" ? "animate-flash-success" : "animate-flash-danger"),
      )}
    >
      <td className="px-4 py-3">
        <StatusBadge tokens={tokens} />
      </td>
      <td className="px-4 py-3">
        <Link to={`/hr/employees?search=${encodeURIComponent(attendance.employee.employee_id)}`} className="flex items-center gap-2">
          <Avatar employee={attendance.employee} />
          <span className="font-medium text-ink hover:text-brand">{attendance.employee.full_name}</span>
        </Link>
      </td>
      <td className="px-4 py-3 font-mono text-ink-muted">{attendance.employee.employee_id}</td>
      <td className="px-4 py-3 text-ink-muted">{attendance.employee.department.name}</td>
      <td className="px-4 py-3 text-ink-muted">{formatDateShort(attendance.date)}</td>
      <td className="px-4 py-3 font-mono tabular-nums text-ink">{formatTime(attendance.check_in)}</td>
      <td className="px-4 py-3 font-mono tabular-nums text-ink-muted">
        {attendance.check_out ? formatTime(attendance.check_out) : t(checkoutStatusLabelKey(attendance.checkout_status))}
      </td>
      <td className={cn("px-4 py-3 tabular-nums", attendance.late_minutes > 0 ? "font-medium text-status-danger" : "text-ink-faint")}>
        {attendance.late_minutes > 0 ? formatMinutes(attendance.late_minutes) : "-"}
      </td>
      <td className="px-4 py-3 text-right">{attendance.status === "late" && <RequestExplanationAction attendance={attendance} />}</td>
    </tr>
  );
}

export function RequestExplanationAction({ attendance }: { attendance: AttendanceResponse }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: () => explanationLettersApi.request(attendance.id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["attendance"] });
      void queryClient.invalidateQueries({ queryKey: ["explanation-letters"] });
    },
  });

  if (attendance.explanation_letter_id !== null) {
    return <span className="text-xs text-ink-faint">{t("letters.requested")}</span>;
  }

  return (
    <button
      type="button"
      onClick={() => {
        if (window.confirm(t("letters.requestExplanationConfirm", { name: attendance.employee.full_name }))) {
          mutation.mutate();
        }
      }}
      disabled={mutation.isPending}
      className="text-sm font-medium text-brand hover:text-brand-hover disabled:opacity-50"
    >
      {t("letters.requestExplanation")}
    </button>
  );
}
