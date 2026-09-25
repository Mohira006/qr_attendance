import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input, Label } from "@/components/ui/Input";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";
import { attendanceApi } from "@/services/attendanceApi";
import { employeesApi } from "@/services/employeesApi";
import { formatDateShort, formatMinutes, formatTime } from "@/utils/format";
import { attendanceStatusTokens, checkoutStatusLabelKey } from "@/utils/status";

export function EmployeeHistoryPage() {
  const { t } = useTranslation();
  const meQuery = useQuery({ queryKey: ["employees", "me"], queryFn: employeesApi.me });
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [page, setPage] = useState(1);

  const employeeId = meQuery.data?.id;
  const historyQuery = useQuery({
    queryKey: ["attendance", "employee", employeeId, "history", dateFrom, dateTo, page],
    queryFn: () =>
      attendanceApi.forEmployee(employeeId as number, {
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        page,
        page_size: 20,
      }),
    enabled: employeeId !== undefined,
  });

  if (meQuery.isError) return <ErrorState message={t("employeeDashboard.notLinked")} />;

  const data = historyQuery.data;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-semibold text-ink">{t("employeeHistory.title")}</h1>
        <p className="text-sm text-ink-muted">{t("employeeHistory.subtitle")}</p>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <div>
          <Label htmlFor="from">{t("reports.from")}</Label>
          <Input
            id="from"
            type="date"
            value={dateFrom}
            onChange={(event) => {
              setDateFrom(event.target.value);
              setPage(1);
            }}
          />
        </div>
        <div>
          <Label htmlFor="to">{t("reports.to")}</Label>
          <Input
            id="to"
            type="date"
            value={dateTo}
            onChange={(event) => {
              setDateTo(event.target.value);
              setPage(1);
            }}
          />
        </div>
      </div>

      {historyQuery.isLoading && <LoadingState label={t("common.loading")} />}
      {historyQuery.isError && <ErrorState message={t("employeeHistory.couldNotLoad")} />}

      {data &&
        (data.items.length === 0 ? (
          <EmptyState title={t("employeeHistory.noRecordsInRange")} description={t("employeeHistory.tryWideningFilter")} />
        ) : (
          <Card>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-line text-xs uppercase tracking-wide text-ink-muted">
                    <th className="px-4 py-3 font-medium">{t("attendance.columns.date")}</th>
                    <th className="px-4 py-3 font-medium">{t("attendance.columns.checkIn")}</th>
                    <th className="px-4 py-3 font-medium">{t("attendance.columns.checkOut")}</th>
                    <th className="px-4 py-3 font-medium">{t("attendance.columns.status")}</th>
                    <th className="px-4 py-3 font-medium">{t("letters.columns.late")}</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((record) => (
                    <tr key={record.id} className="border-b border-line last:border-0">
                      <td className="px-4 py-3 text-ink-muted">{formatDateShort(record.date)}</td>
                      <td className="px-4 py-3 font-mono tabular-nums">{formatTime(record.check_in)}</td>
                      <td className="px-4 py-3 font-mono tabular-nums text-ink-muted">
                        {record.check_out ? formatTime(record.check_out) : t(checkoutStatusLabelKey(record.checkout_status))}
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge tokens={attendanceStatusTokens(record.status)} />
                      </td>
                      <td className="px-4 py-3 tabular-nums">{record.late_minutes > 0 ? formatMinutes(record.late_minutes) : "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {data.pages > 1 && (
              <div className="flex items-center justify-between border-t border-line px-4 py-3">
                <p className="text-sm text-ink-muted">{t("common.page", { page: data.page, pages: data.pages })}</p>
                <div className="flex gap-2">
                  <Button variant="secondary" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                    {t("common.previous")}
                  </Button>
                  <Button variant="secondary" size="sm" disabled={page >= data.pages} onClick={() => setPage((p) => p + 1)}>
                    {t("common.next")}
                  </Button>
                </div>
              </div>
            )}
          </Card>
        ))}
    </div>
  );
}
