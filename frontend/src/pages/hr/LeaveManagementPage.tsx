import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, LayoutGrid, List, Plus } from "lucide-react";
import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { Avatar } from "@/components/attendance/Avatar";
import { Button } from "@/components/ui/Button";
import { Card, CardBody } from "@/components/ui/Card";
import { FieldError, Input, Label, Select, Textarea } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";
import { getErrorMessage } from "@/services/api";
import { departmentsApi } from "@/services/employeesApi";
import { leaveApi } from "@/services/leaveApi";
import { employeesApi } from "@/services/employeesApi";
import type { LeaveRequestStatus, LeaveRequestType } from "@/types/enums";
import type { LeaveRequestResponse } from "@/types/models";
import { addDays, formatDate, formatDateTime } from "@/utils/format";
import { cn } from "@/utils/cn";
import { leaveRequestStatusTokens } from "@/utils/status";

type ViewMode = "table" | "calendar";

export function LeaveManagementPage() {
  const { t } = useTranslation();
  const [view, setView] = useState<ViewMode>("table");
  const [status, setStatus] = useState<LeaveRequestStatus | "">("");
  const [departmentId, setDepartmentId] = useState("");
  const [page, setPage] = useState(1);
  const [viewingRequest, setViewingRequest] = useState<LeaveRequestResponse | null>(null);
  const [showOverride, setShowOverride] = useState(false);

  const departmentsQuery = useQuery({ queryKey: ["departments"], queryFn: () => departmentsApi.list("active") });
  const requestsQuery = useQuery({
    queryKey: ["leave-requests", "hr", status, departmentId, page],
    queryFn: () =>
      leaveApi.list({
        status: status || undefined,
        department_id: departmentId ? Number(departmentId) : undefined,
        page,
        page_size: 20,
      }),
    enabled: view === "table",
  });

  const data = requestsQuery.data;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-semibold text-ink">{t("leaveManagement.title")}</h1>
          <p className="text-sm text-ink-muted">{t("leaveManagement.subtitle")}</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1 rounded-lg border border-line bg-white p-1">
            <ViewToggleButton active={view === "table"} onClick={() => setView("table")} icon={<List size={16} />} label={t("leaveManagement.tableView")} />
            <ViewToggleButton active={view === "calendar"} onClick={() => setView("calendar")} icon={<LayoutGrid size={16} />} label={t("leaveManagement.calendarView")} />
          </div>
          <Button onClick={() => setShowOverride(true)}>
            <Plus size={16} className="mr-1.5" /> {t("leaveManagement.override.button")}
          </Button>
        </div>
      </div>

      {view === "table" ? (
        <>
          <div className="flex flex-wrap items-center gap-3">
            <Select
              value={status}
              onChange={(event) => {
                setStatus(event.target.value as LeaveRequestStatus | "");
                setPage(1);
              }}
              className="w-48"
            >
              <option value="">{t("common.allStatuses")}</option>
              <option value="pending">{t("common.status.pending")}</option>
              <option value="approved">{t("common.status.approved")}</option>
              <option value="rejected">{t("common.status.rejected")}</option>
              <option value="cancelled">{t("common.status.cancelled")}</option>
              <option value="completed">{t("common.status.completed")}</option>
            </Select>
            <Select
              value={departmentId}
              onChange={(event) => {
                setDepartmentId(event.target.value);
                setPage(1);
              }}
              className="w-48"
            >
              <option value="">{t("common.allDepartments")}</option>
              {departmentsQuery.data?.map((department) => (
                <option key={department.id} value={department.id}>
                  {department.name}
                </option>
              ))}
            </Select>
          </div>

          {requestsQuery.isLoading && <LoadingState label={t("common.loading")} />}
          {requestsQuery.isError && <ErrorState message={t("leaveManagement.couldNotLoad")} />}

          {data &&
            (data.items.length === 0 ? (
              <EmptyState title={t("leaveManagement.noRequests")} description={t("leaveManagement.noRequestsDescription")} />
            ) : (
              <Card>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead>
                      <tr className="border-b border-line text-xs uppercase tracking-wide text-ink-muted">
                        <th className="px-4 py-3 font-medium">{t("leaveManagement.columns.employee")}</th>
                        <th className="px-4 py-3 font-medium">{t("leaveManagement.columns.workPeriod")}</th>
                        <th className="px-4 py-3 font-medium">{t("leaveManagement.columns.leaveStart")}</th>
                        <th className="px-4 py-3 font-medium">{t("leaveManagement.columns.leaveEnd")}</th>
                        <th className="px-4 py-3 font-medium">{t("leaveManagement.columns.days")}</th>
                        <th className="px-4 py-3 font-medium">{t("leaveManagement.columns.requestType")}</th>
                        <th className="px-4 py-3 font-medium">{t("leaveManagement.columns.status")}</th>
                        <th className="px-4 py-3 font-medium">{t("leaveManagement.columns.actions")}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.items.map((request) => (
                        <tr key={request.id} className="border-b border-line last:border-0 hover:bg-canvas">
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-2">
                              <Avatar employee={request.employee} size={28} />
                              <div>
                                <p className="font-medium text-ink">{request.employee.full_name}</p>
                                <p className="text-xs text-ink-muted">
                                  {request.employee.position ?? request.employee.employee_id}
                                </p>
                              </div>
                            </div>
                          </td>
                          <td className="px-4 py-3 text-ink-muted">
                            {formatDate(request.work_period_start)} - {formatDate(request.work_period_end)}
                          </td>
                          <td className="px-4 py-3">{formatDate(request.requested_start_date)}</td>
                          <td className="px-4 py-3">{formatDate(request.requested_end_date)}</td>
                          <td className="px-4 py-3 tabular-nums">{request.duration_days}</td>
                          <td className="px-4 py-3 text-ink-muted">
                            {request.request_type === "normal" ? t("leave.form.normal") : t("leave.form.forceMajeure")}
                          </td>
                          <td className="px-4 py-3">
                            <StatusBadge tokens={leaveRequestStatusTokens(request.status)} />
                          </td>
                          <td className="px-4 py-3 text-right">
                            <button type="button" onClick={() => setViewingRequest(request)} className="text-sm font-medium text-brand hover:text-brand-hover">
                              {t("leaveManagement.view")}
                            </button>
                          </td>
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
        </>
      ) : (
        <LeaveCalendar />
      )}

      {viewingRequest && <RequestDetailModal request={viewingRequest} onClose={() => setViewingRequest(null)} />}
      {showOverride && <HrOverrideModal onClose={() => setShowOverride(false)} />}
    </div>
  );
}

function ViewToggleButton({ active, onClick, icon, label }: { active: boolean; onClick: () => void; icon: React.ReactNode; label: string }) {
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

function RequestDetailModal({ request: initial, onClose }: { request: LeaveRequestResponse; onClose: () => void }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [request, setRequest] = useState(initial);
  const [hrComment, setHrComment] = useState(request.hr_comment ?? "");
  const [error, setError] = useState<string | null>(null);

  function refresh() {
    void queryClient.invalidateQueries({ queryKey: ["leave-requests"] });
  }

  const approveMutation = useMutation({
    mutationFn: () => leaveApi.approve(request.id, hrComment.trim() || null),
    onSuccess: (updated) => {
      setRequest(updated);
      refresh();
    },
    onError: (err: unknown) => setError(getErrorMessage(err)),
  });

  const rejectMutation = useMutation({
    mutationFn: () => leaveApi.reject(request.id, hrComment.trim() || null),
    onSuccess: (updated) => {
      setRequest(updated);
      refresh();
    },
    onError: (err: unknown) => setError(getErrorMessage(err)),
  });

  const commentMutation = useMutation({
    mutationFn: () => leaveApi.updateComment(request.id, hrComment.trim()),
    onSuccess: (updated) => {
      setRequest(updated);
      refresh();
    },
    onError: (err: unknown) => setError(getErrorMessage(err)),
  });

  const isPending = request.status === "pending";

  return (
    <Modal title={t("leaveManagement.reviewRequest", { name: request.employee.full_name })} onClose={onClose} width="max-w-lg">
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-3 rounded-lg bg-canvas p-3 text-sm">
          <InfoRow label={t("leaveManagement.columns.workPeriod")} value={`${formatDate(request.work_period_start)} - ${formatDate(request.work_period_end)}`} />
          <InfoRow label={t("leaveManagement.columns.eligibilityDate")} value={formatDate(request.eligibility_date)} />
          <InfoRow label={t("leaveManagement.columns.leaveStart")} value={formatDate(request.requested_start_date)} />
          <InfoRow label={t("leaveManagement.columns.leaveEnd")} value={formatDate(request.requested_end_date)} />
          <DurationField request={request} onUpdated={(updated) => { setRequest(updated); refresh(); }} />
          <InfoRow label={t("leaveManagement.columns.requestType")} value={request.request_type === "normal" ? t("leave.form.normal") : t("leave.form.forceMajeure")} />
          <InfoRow label={t("leaveManagement.requestedOn", { date: formatDateTime(request.submitted_at) })} value="" />
        </div>

        <div className="flex items-center justify-between">
          <span className="text-sm text-ink-muted">{t("leaveManagement.columns.status")}</span>
          <StatusBadge tokens={leaveRequestStatusTokens(request.status)} />
        </div>

        {request.is_hr_override && request.override_reason && (
          <div className="rounded-lg bg-status-warning-bg px-3 py-2 text-sm text-status-warning">
            {t("leaveManagement.override.title")}: {request.override_reason}
          </div>
        )}

        <div>
          <Label>{t("leaveManagement.employeeComment")}</Label>
          <p className="rounded-lg border border-line bg-canvas px-3 py-2 text-sm text-ink">
            {request.employee_comment || t("leaveManagement.notSelected")}
          </p>
        </div>

        <div>
          <Label htmlFor="hr_comment">{t("leaveManagement.hrComment")}</Label>
          <Textarea
            id="hr_comment"
            rows={3}
            value={hrComment}
            onChange={(event) => setHrComment(event.target.value)}
            placeholder={t("leaveManagement.hrCommentPlaceholder") ?? undefined}
          />
        </div>

        <FieldError>{error}</FieldError>

        <div className="flex flex-wrap justify-end gap-2 border-t border-line pt-4">
          <Button type="button" variant="secondary" onClick={onClose}>
            {t("common.close")}
          </Button>
          {isPending ? (
            <>
              <Button
                type="button"
                variant="danger"
                onClick={() => {
                  setError(null);
                  rejectMutation.mutate();
                }}
                disabled={rejectMutation.isPending || approveMutation.isPending}
              >
                {t("leaveManagement.reject")}
              </Button>
              <Button
                type="button"
                onClick={() => {
                  setError(null);
                  approveMutation.mutate();
                }}
                disabled={rejectMutation.isPending || approveMutation.isPending}
              >
                {t("leaveManagement.approve")}
              </Button>
            </>
          ) : (
            <Button
              type="button"
              onClick={() => {
                setError(null);
                commentMutation.mutate();
              }}
              disabled={commentMutation.isPending || !hrComment.trim()}
            >
              {commentMutation.isPending ? t("common.saving") : t("leaveManagement.addComment")}
            </Button>
          )}
        </div>
      </div>
    </Modal>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-ink-muted">{label}</p>
      {value && <p className="font-medium text-ink">{value}</p>}
    </div>
  );
}

function DurationField({ request, onUpdated }: { request: LeaveRequestResponse; onUpdated: (updated: LeaveRequestResponse) => void }) {
  const { t } = useTranslation();
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(request.duration_days);
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () => leaveApi.updateDuration(request.id, value),
    onSuccess: (updated) => {
      onUpdated(updated);
      setEditing(false);
    },
    onError: (err: unknown) => setError(getErrorMessage(err)),
  });

  const canEdit = request.status === "pending";

  if (!editing) {
    return (
      <div>
        <p className="text-xs text-ink-muted">{t("leaveManagement.columns.days")}</p>
        <div className="flex items-center gap-2">
          <p className="font-medium text-ink">{request.duration_days}</p>
          {canEdit && (
            <button
              type="button"
              onClick={() => {
                setValue(request.duration_days);
                setError(null);
                setEditing(true);
              }}
              className="text-xs font-medium text-brand hover:text-brand-hover"
            >
              {t("leaveManagement.editDuration")}
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div>
      <p className="text-xs text-ink-muted">{t("leaveManagement.columns.days")}</p>
      <div className="flex items-center gap-1.5">
        <Input
          type="number"
          min={1}
          max={365}
          value={value}
          onChange={(event) => setValue(Number(event.target.value))}
          className="h-8 w-20 px-2 py-1 text-sm"
        />
        <button type="button" onClick={() => mutation.mutate()} disabled={mutation.isPending} className="text-xs font-medium text-brand hover:text-brand-hover">
          {t("common.save")}
        </button>
        <button type="button" onClick={() => setEditing(false)} className="text-xs text-ink-muted hover:text-ink">
          {t("common.cancel")}
        </button>
      </div>
      {error && <p className="mt-1 text-xs text-status-danger">{error}</p>}
    </div>
  );
}

function HrOverrideModal({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const employeesQuery = useQuery({
    queryKey: ["employees", "active-for-dropdown"],
    queryFn: () => employeesApi.list({ status: "active", page: 1, page_size: 500 }),
  });

  const [employeeId, setEmployeeId] = useState("");
  const [startDate, setStartDate] = useState("");
  const [requestType, setRequestType] = useState<LeaveRequestType>("normal");
  const [comment, setComment] = useState("");
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);

  // Reads the selected employee's actual resolved entitlement (employee override,
  // if any, otherwise the company default) - the same precedence the backend
  // applies on submission - rather than assuming everyone uses the company-wide
  // setting, which would show a wrong preview for anyone with a personal override.
  const eligibilityQuery = useQuery({
    queryKey: ["leave", "eligibility", employeeId],
    queryFn: () => leaveApi.eligibility(Number(employeeId)),
    enabled: employeeId !== "",
  });
  const duration = eligibilityQuery.data?.annual_leave_duration_days;
  const previewEndDate = startDate && duration ? addDays(startDate, duration - 1) : null;

  const mutation = useMutation({
    mutationFn: () =>
      leaveApi.hrCreate({
        employee_id: Number(employeeId),
        requested_start_date: startDate,
        request_type: requestType,
        employee_comment: comment.trim() || null,
        override_reason: reason.trim(),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["leave-requests"] });
      onClose();
    },
    onError: (err: unknown) => setError(getErrorMessage(err)),
  });

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    mutation.mutate();
  }

  return (
    <Modal title={t("leaveManagement.override.title")} onClose={onClose}>
      <form onSubmit={onSubmit} className="space-y-4">
        <p className="text-sm text-ink-muted">{t("leaveManagement.override.description")}</p>

        <div>
          <Label htmlFor="employee">{t("simulator.employee")}</Label>
          <Select id="employee" required value={employeeId} onChange={(event) => setEmployeeId(event.target.value)}>
            <option value="">{t("simulator.selectEmployee")}</option>
            {employeesQuery.data?.items.map((employee) => (
              <option key={employee.id} value={employee.id}>
                {employee.full_name} ({employee.employee_id}) - {employee.department.name}
              </option>
            ))}
          </Select>
        </div>

        <div>
          <Label htmlFor="start_date">{t("leave.form.startDate")}</Label>
          <Input id="start_date" type="date" required value={startDate} onChange={(event) => setStartDate(event.target.value)} />
        </div>

        {previewEndDate && (
          <div className="rounded-lg bg-canvas px-3 py-2 text-sm text-ink">
            {t("leave.form.endDate")}: <span className="font-medium">{formatDate(previewEndDate)}</span> ({t("leave.days", { count: duration })})
          </div>
        )}

        <div>
          <Label htmlFor="request_type">{t("leave.form.requestType")}</Label>
          <Select id="request_type" value={requestType} onChange={(event) => setRequestType(event.target.value as LeaveRequestType)}>
            <option value="normal">{t("leave.form.normal")}</option>
            <option value="force_majeure">{t("leave.form.forceMajeure")}</option>
          </Select>
        </div>

        <div>
          <Label htmlFor="comment">{t("leave.form.comment")}</Label>
          <Textarea id="comment" rows={2} value={comment} onChange={(event) => setComment(event.target.value)} />
        </div>

        <div>
          <Label htmlFor="reason">{t("leaveManagement.override.reason")}</Label>
          <Textarea
            id="reason"
            rows={2}
            required
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            placeholder={t("leaveManagement.override.reasonPlaceholder") ?? undefined}
          />
        </div>

        <FieldError>{error}</FieldError>

        <div className="flex justify-end gap-2 border-t border-line pt-4">
          <Button type="button" variant="secondary" onClick={onClose}>
            {t("common.cancel")}
          </Button>
          <Button type="submit" disabled={!employeeId || !startDate || !reason.trim() || mutation.isPending}>
            {mutation.isPending ? t("leave.form.submitting") : t("leave.form.submit")}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function monthBounds(year: number, month: number): { start: string; end: string; gridStart: Date; daysInMonth: number } {
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const firstWeekday = new Date(year, month, 1).getDay(); // 0=Sunday
  const mondayOffset = firstWeekday === 0 ? 6 : firstWeekday - 1;
  const gridStart = new Date(year, month, 1 - mondayOffset);
  const pad = (n: number) => String(n).padStart(2, "0");
  return {
    start: `${year}-${pad(month + 1)}-01`,
    end: `${year}-${pad(month + 1)}-${pad(daysInMonth)}`,
    gridStart,
    daysInMonth,
  };
}

function LeaveCalendar() {
  const { t } = useTranslation();
  const [cursor, setCursor] = useState(() => {
    const now = new Date();
    return { year: now.getFullYear(), month: now.getMonth() };
  });

  const { start, end, gridStart } = monthBounds(cursor.year, cursor.month);
  const calendarQuery = useQuery({
    queryKey: ["leave-requests", "calendar", start, end],
    queryFn: () => leaveApi.calendar(start, end),
  });

  const monthLabel = new Date(cursor.year, cursor.month, 1).toLocaleDateString(undefined, { month: "long", year: "numeric" });

  const gridDays: Date[] = Array.from({ length: 42 }, (_, i) => {
    const d = new Date(gridStart);
    d.setDate(d.getDate() + i);
    return d;
  });

  function toIso(d: Date): string {
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  }

  const entriesForDay = (iso: string) =>
    (calendarQuery.data ?? []).filter((entry) => entry.requested_start_date <= iso && entry.requested_end_date >= iso);

  const hasAnyThisMonth = (calendarQuery.data ?? []).length > 0;

  return (
    <Card>
      <CardBody>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="font-display text-base font-semibold text-ink">{t("leaveManagement.calendar.title")}</h2>
          <div className="flex items-center gap-2">
            <button
              type="button"
              aria-label={t("leaveManagement.calendar.previousMonth")}
              onClick={() => setCursor((c) => (c.month === 0 ? { year: c.year - 1, month: 11 } : { year: c.year, month: c.month - 1 }))}
              className="rounded-lg p-1.5 text-ink-muted hover:bg-canvas hover:text-ink"
            >
              <ChevronLeft size={18} />
            </button>
            <span className="min-w-32 text-center text-sm font-medium text-ink">{monthLabel}</span>
            <button
              type="button"
              aria-label={t("leaveManagement.calendar.nextMonth")}
              onClick={() => setCursor((c) => (c.month === 11 ? { year: c.year + 1, month: 0 } : { year: c.year, month: c.month + 1 }))}
              className="rounded-lg p-1.5 text-ink-muted hover:bg-canvas hover:text-ink"
            >
              <ChevronRight size={18} />
            </button>
          </div>
        </div>

        {calendarQuery.isLoading && <LoadingState label={t("common.loading")} />}

        {calendarQuery.data && !hasAnyThisMonth && <p className="py-6 text-center text-sm text-ink-muted">{t("leaveManagement.calendar.noLeaveThisMonth")}</p>}

        {calendarQuery.data && (
          <div className="grid grid-cols-7 gap-1">
            {gridDays.map((day) => {
              const iso = toIso(day);
              const inMonth = day.getMonth() === cursor.month;
              const entries = entriesForDay(iso);
              const isToday = iso === toIso(new Date());
              return (
                <div
                  key={iso}
                  className={cn(
                    "min-h-20 rounded-lg border border-line p-1.5",
                    !inMonth && "bg-canvas/50 opacity-50",
                    isToday && "ring-2 ring-brand",
                  )}
                >
                  <p className="text-xs text-ink-muted">{day.getDate()}</p>
                  <div className="mt-1 space-y-0.5">
                    {entries.slice(0, 2).map((entry) => (
                      <div
                        key={entry.id}
                        title={`${entry.employee.full_name} - ${entry.employee.department.name}`}
                        className={cn(
                          "truncate rounded px-1 py-0.5 text-[10px] font-medium",
                          entry.status === "completed" ? "bg-brand-light text-brand" : "bg-status-success-bg text-status-success",
                        )}
                      >
                        {entry.employee.full_name}
                      </div>
                    ))}
                    {entries.length > 2 && <p className="text-[10px] text-ink-faint">+{entries.length - 2}</p>}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </CardBody>
    </Card>
  );
}
