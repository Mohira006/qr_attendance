import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { FieldError, Input, Label, Select, Textarea } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";
import { getErrorCode, getErrorDetails, getErrorMessage } from "@/services/api";
import { employeesApi } from "@/services/employeesApi";
import { leaveApi } from "@/services/leaveApi";
import { settingsApi } from "@/services/settingsApi";
import type { LeaveEligibilityResponse } from "@/types/models";
import type { LeaveRequestType } from "@/types/enums";
import { addDays, formatDate, formatDateShort } from "@/utils/format";
import { cn } from "@/utils/cn";
import { leaveRequestStatusTokens } from "@/utils/status";

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

export function EmployeeLeavePage() {
  const { t } = useTranslation();
  const meQuery = useQuery({ queryKey: ["employees", "me"], queryFn: employeesApi.me });
  const employeeId = meQuery.data?.id;

  const eligibilityQuery = useQuery({
    queryKey: ["leave", "eligibility", employeeId],
    queryFn: () => leaveApi.eligibility(employeeId as number),
    enabled: employeeId !== undefined,
  });
  const historyQuery = useQuery({
    queryKey: ["leave", "requests", "me"],
    queryFn: () => leaveApi.list({ page_size: 50 }),
    enabled: employeeId !== undefined,
  });

  const [showRequestModal, setShowRequestModal] = useState(false);

  if (meQuery.isLoading || eligibilityQuery.isLoading) return <LoadingState label={t("common.loading")} />;
  if (meQuery.isError || eligibilityQuery.isError || !eligibilityQuery.data) {
    return <ErrorState message={t("leave.couldNotLoad")} />;
  }

  const eligibility = eligibilityQuery.data;
  const canRequest = eligibility.is_eligible && eligibility.current_request === null;
  const historyItems = historyQuery.data?.items ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-semibold text-ink">{t("leave.myAnnualLeave")}</h1>
      </div>

      <LeaveTimeline eligibility={eligibility} />

      <Card>
        <CardBody className="space-y-2 text-sm">
          <Row label={t("leave.employmentStart")} value={formatDate(eligibility.employment_start_date)} />
          <Row
            label={t("leave.workPeriod")}
            value={`${formatDateShort(eligibility.work_period_start)} - ${formatDateShort(eligibility.work_period_end)}`}
          />
          <Row
            label={t("leave.eligibilityDate")}
            value={eligibility.is_eligible ? t("leave.eligibleFrom", { date: formatDate(eligibility.eligibility_date) }) : t("leave.notYetEligible", { date: formatDate(eligibility.eligibility_date) })}
          />
          <Row label={t("leave.annualLeaveDuration")} value={t("leave.days", { count: eligibility.annual_leave_duration_days })} />
          <div className="flex items-center justify-between border-b border-line py-2 last:border-0">
            <span className="text-ink-muted">{t("leave.currentStatus")}</span>
            {eligibility.current_request ? (
              <StatusBadge tokens={leaveRequestStatusTokens(eligibility.current_request.status)} />
            ) : (
              <span className="text-ink">{t("leave.noRequestYet")}</span>
            )}
          </div>
          {eligibility.current_request && (
            <Row
              label={t("leave.selectedLeave")}
              value={`${formatDateShort(eligibility.current_request.requested_start_date)} - ${formatDateShort(eligibility.current_request.requested_end_date)}`}
            />
          )}
          {eligibility.previous_leave && (
            <Row
              label={t("leave.previousLeave")}
              value={`${formatDateShort(eligibility.previous_leave.requested_start_date)} - ${formatDateShort(eligibility.previous_leave.requested_end_date)}`}
            />
          )}
          {eligibility.next_eligibility_date && <Row label={t("leave.nextEligibility")} value={formatDate(eligibility.next_eligibility_date)} />}
        </CardBody>
      </Card>

      <div className="flex gap-2">
        {canRequest && <Button onClick={() => setShowRequestModal(true)}>{t("leave.requestLeave")}</Button>}
        {eligibility.current_request?.status === "pending" && <CancelButton requestId={eligibility.current_request.id} employeeId={employeeId as number} />}
      </div>

      <Card>
        <CardHeader>
          <h2 className="font-display text-base font-semibold text-ink">{t("leave.history.title")}</h2>
        </CardHeader>
        <CardBody className="p-0">
          {historyItems.length === 0 ? (
            <EmptyState title={t("leave.history.noHistory")} />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-line text-xs uppercase tracking-wide text-ink-muted">
                    <th className="px-4 py-3 font-medium">{t("leave.history.columns.workPeriod")}</th>
                    <th className="px-4 py-3 font-medium">{t("leave.history.columns.startDate")}</th>
                    <th className="px-4 py-3 font-medium">{t("leave.history.columns.endDate")}</th>
                    <th className="px-4 py-3 font-medium">{t("leave.history.columns.duration")}</th>
                    <th className="px-4 py-3 font-medium">{t("leave.history.columns.type")}</th>
                    <th className="px-4 py-3 font-medium">{t("leave.history.columns.status")}</th>
                  </tr>
                </thead>
                <tbody>
                  {historyItems.map((item) => (
                    <tr key={item.id} className="border-b border-line last:border-0">
                      <td className="px-4 py-3 text-ink-muted">
                        {formatDateShort(item.work_period_start)} - {formatDateShort(item.work_period_end)}
                      </td>
                      <td className="px-4 py-3">{formatDateShort(item.requested_start_date)}</td>
                      <td className="px-4 py-3">{formatDateShort(item.requested_end_date)}</td>
                      <td className="px-4 py-3 tabular-nums">{t("leave.days", { count: item.duration_days })}</td>
                      <td className="px-4 py-3 text-ink-muted">{item.request_type === "normal" ? t("leave.form.normal") : t("leave.form.forceMajeure")}</td>
                      <td className="px-4 py-3">
                        <StatusBadge tokens={leaveRequestStatusTokens(item.status)} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardBody>
      </Card>

      {showRequestModal && <RequestLeaveModal eligibility={eligibility} onClose={() => setShowRequestModal(false)} />}
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between border-b border-line py-2 last:border-0">
      <span className="text-ink-muted">{label}</span>
      <span className="text-ink">{value}</span>
    </div>
  );
}

function CancelButton({ requestId, employeeId }: { requestId: number; employeeId: number }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: () => leaveApi.cancel(requestId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["leave", "eligibility", employeeId] });
      void queryClient.invalidateQueries({ queryKey: ["leave", "requests"] });
    },
  });

  return (
    <Button
      variant="danger"
      onClick={() => {
        if (window.confirm(t("leave.cancelConfirm"))) mutation.mutate();
      }}
      disabled={mutation.isPending}
    >
      {mutation.isPending ? t("leave.cancelling") : t("leave.cancelRequest")}
    </Button>
  );
}

/** Steps folded to 5 highlighted positions (0-4 as "done/current/upcoming"); reaching
 * a later cycle's eligibility is visually distinguished from the very first one
 * (index 4 vs 2), matching the cyclical loop the spec's own diagram describes -
 * everything else is a straightforward linear progression through one cycle. */
function currentTimelineStep(eligibility: LeaveEligibilityResponse): number {
  if (eligibility.current_request?.status === "approved") return 3;
  if (eligibility.current_request?.status === "pending") return 2;
  if (!eligibility.is_eligible && eligibility.previous_leave) return 4;
  if (!eligibility.is_eligible && !eligibility.previous_leave) return 1;
  return eligibility.cycle_number > 1 ? 5 : 2;
}

function LeaveTimeline({ eligibility }: { eligibility: LeaveEligibilityResponse }) {
  const { t } = useTranslation();
  const current = currentTimelineStep(eligibility);
  const steps = [
    t("leave.timeline.employmentStart"),
    t("leave.timeline.sixMonths"),
    t("leave.timeline.selectionPeriod"),
    t("leave.timeline.annualLeave"),
    t("leave.timeline.workAfterReturn"),
    t("leave.timeline.nextEligibility"),
  ];

  return (
    <Card>
      <CardBody>
        <div className="flex items-center">
          {steps.map((label, index) => {
            const state = index < current ? "done" : index === current ? "current" : "upcoming";
            return (
              <div key={label} className="flex flex-1 items-center last:flex-none">
                <div className="flex flex-col items-center gap-1.5">
                  <div
                    className={cn(
                      "flex h-7 w-7 items-center justify-center rounded-full text-xs font-semibold",
                      state === "done" && "bg-brand text-white",
                      state === "current" && "bg-brand text-white ring-4 ring-brand-light",
                      state === "upcoming" && "bg-canvas text-ink-faint",
                    )}
                  >
                    {index + 1}
                  </div>
                  <span
                    className={cn(
                      "max-w-20 text-center text-[11px] leading-tight",
                      state === "upcoming" ? "text-ink-faint" : "font-medium text-ink",
                    )}
                  >
                    {label}
                  </span>
                </div>
                {index < steps.length - 1 && <div className={cn("mx-1 h-0.5 flex-1", index < current ? "bg-brand" : "bg-line")} />}
              </div>
            );
          })}
        </div>
      </CardBody>
    </Card>
  );
}

function RequestLeaveModal({ eligibility, onClose }: { eligibility: LeaveEligibilityResponse; onClose: () => void }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const settingsQuery = useQuery({ queryKey: ["settings"], queryFn: settingsApi.get });

  const [startDate, setStartDate] = useState("");
  const [requestType, setRequestType] = useState<LeaveRequestType>("normal");
  const [comment, setComment] = useState("");
  const [error, setError] = useState<string | null>(null);

  const duration = eligibility.annual_leave_duration_days;
  const previewEndDate = startDate ? addDays(startDate, duration - 1) : null;
  const requiredNotice = requestType === "normal" ? settingsQuery.data?.leave_normal_notice_days : settingsQuery.data?.leave_force_majeure_notice_days;

  const mutation = useMutation({
    mutationFn: () =>
      leaveApi.create({ requested_start_date: startDate, request_type: requestType, employee_comment: comment.trim() || null }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["leave"] });
      onClose();
    },
    onError: (err: unknown) => {
      const code = getErrorCode(err);
      if (code === "notice_period_too_short") {
        const details = getErrorDetails(err);
        const required = typeof details?.required_days === "number" ? details.required_days : requiredNotice;
        setError(
          `${t("leave.form.error.noticePeriodTooShort")} ${
            requestType === "normal" ? t("leave.form.noticeNormal", { days: required }) : t("leave.form.noticeForceMajeure", { days: required })
          }`,
        );
      } else if (code === "leave_already_pending") {
        setError(t("leave.form.error.alreadyPending"));
      } else if (code === "not_yet_eligible") {
        setError(t("leave.form.error.notEligible"));
      } else if (code === "invalid_start_date") {
        setError(t("leave.form.error.invalidStartDate"));
      } else {
        setError(getErrorMessage(err));
      }
    },
  });

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    mutation.mutate();
  }

  return (
    <Modal title={t("leave.form.title")} onClose={onClose}>
      <form onSubmit={onSubmit} className="space-y-4">
        <div>
          <Label htmlFor="start_date">{t("leave.form.startDate")}</Label>
          <Input id="start_date" type="date" required min={todayIso()} value={startDate} onChange={(event) => setStartDate(event.target.value)} />
        </div>

        <div>
          <Label>{t("leave.form.duration")}</Label>
          <Input disabled value={t("leave.days", { count: duration })} />
          <p className="mt-1 text-xs text-ink-muted">{t("leave.form.durationNote")}</p>
        </div>

        {previewEndDate && (
          <div className="rounded-lg bg-canvas px-3 py-2 text-sm text-ink">
            {t("leave.form.endDate")}: <span className="font-medium">{formatDate(previewEndDate)}</span>
          </div>
        )}

        <div>
          <Label htmlFor="request_type">{t("leave.form.requestType")}</Label>
          <Select id="request_type" value={requestType} onChange={(event) => setRequestType(event.target.value as LeaveRequestType)}>
            <option value="normal">{t("leave.form.normal")}</option>
            <option value="force_majeure">{t("leave.form.forceMajeure")}</option>
          </Select>
          {requiredNotice !== undefined && (
            <p className="mt-1 text-xs text-ink-muted">
              {requestType === "normal" ? t("leave.form.noticeNormal", { days: requiredNotice }) : t("leave.form.noticeForceMajeure", { days: requiredNotice })}
            </p>
          )}
        </div>

        <div>
          <Label htmlFor="comment">{t("leave.form.comment")}</Label>
          <Textarea id="comment" rows={3} value={comment} onChange={(event) => setComment(event.target.value)} placeholder={t("leave.form.commentPlaceholder") ?? undefined} />
        </div>

        <FieldError>{error}</FieldError>

        <div className="flex justify-end gap-2 border-t border-line pt-4">
          <Button type="button" variant="secondary" onClick={onClose}>
            {t("common.cancel")}
          </Button>
          <Button type="submit" disabled={!startDate || mutation.isPending}>
            {mutation.isPending ? t("leave.form.submitting") : t("leave.form.submit")}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
