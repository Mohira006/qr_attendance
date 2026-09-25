import { useTranslation } from "react-i18next";

import { Avatar } from "@/components/attendance/Avatar";
import { RequestExplanationAction } from "@/components/attendance/AttendanceTable";
import { Card, CardBody } from "@/components/ui/Card";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { EmptyState } from "@/components/ui/States";
import { useFlashOnUpdate } from "@/hooks/useFlashOnUpdate";
import type { AttendanceResponse } from "@/types/models";
import { cn } from "@/utils/cn";
import { formatMinutes, formatTime } from "@/utils/format";
import { attendanceStatusTokens, checkoutStatusLabelKey } from "@/utils/status";

export function AttendanceCards({ onTime, late }: { onTime: AttendanceResponse[]; late: AttendanceResponse[] }) {
  const { t } = useTranslation();
  const rows = [...onTime, ...late];
  if (rows.length === 0) {
    return <EmptyState title={t("attendance.noAttendanceYet")} description={t("attendance.noAttendanceYetDescription")} />;
  }

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {rows.map((attendance) => (
        <AttendanceCard key={attendance.id} attendance={attendance} />
      ))}
    </div>
  );
}

function AttendanceCard({ attendance }: { attendance: AttendanceResponse }) {
  const { t } = useTranslation();
  const tokens = attendanceStatusTokens(attendance.status);
  const flashing = useFlashOnUpdate(attendance.id);

  return (
    <Card
      className={cn(
        "overflow-hidden border-t-4",
        tokens.border,
        flashing && (attendance.status === "on_time" ? "animate-flash-success" : "animate-flash-danger"),
      )}
    >
      <CardBody>
        <div className="flex items-start gap-3">
          <Avatar employee={attendance.employee} size={44} />
          <div className="min-w-0 flex-1">
            <p className="truncate font-medium text-ink">{attendance.employee.full_name}</p>
            <p className="truncate font-mono text-xs text-ink-muted">
              {attendance.employee.employee_id} · {attendance.employee.department.name}
            </p>
          </div>
        </div>
        <div className="mt-3">
          <StatusBadge tokens={tokens} />
        </div>
        <dl className="mt-4 grid grid-cols-2 gap-3 border-t border-line pt-4 text-sm">
          <div>
            <dt className="text-xs text-ink-muted">{t("attendance.columns.arrival")}</dt>
            <dd className="font-mono tabular-nums text-ink">{formatTime(attendance.check_in)}</dd>
          </div>
          <div>
            <dt className="text-xs text-ink-muted">{t("attendance.columns.departure")}</dt>
            <dd className="font-mono tabular-nums text-ink">
              {attendance.check_out ? formatTime(attendance.check_out) : t(checkoutStatusLabelKey(attendance.checkout_status))}
            </dd>
          </div>
          {attendance.late_minutes > 0 && (
            <div className="col-span-2">
              <dt className="text-xs text-ink-muted">{t("attendance.columns.lateBy")}</dt>
              <dd className="font-medium text-status-danger">{formatMinutes(attendance.late_minutes)}</dd>
            </div>
          )}
        </dl>
        {attendance.status === "late" && (
          <div className="mt-3 border-t border-line pt-3">
            <RequestExplanationAction attendance={attendance} />
          </div>
        )}
      </CardBody>
    </Card>
  );
}
