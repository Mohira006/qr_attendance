import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Input, Label } from "@/components/ui/Input";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { getErrorMessage } from "@/services/api";
import { settingsApi } from "@/services/settingsApi";
import { cn } from "@/utils/cn";

const WEEKDAYS = [1, 2, 3, 4, 5, 6, 7];

export function HrSettingsPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const settingsQuery = useQuery({ queryKey: ["settings"], queryFn: settingsApi.get });

  const [companyName, setCompanyName] = useState("");
  const [workStart, setWorkStart] = useState("");
  const [workEnd, setWorkEnd] = useState("");
  const [gracePeriod, setGracePeriod] = useState(15);
  const [duplicateWindow, setDuplicateWindow] = useState(60);
  const [workingDays, setWorkingDays] = useState<number[]>([1, 2, 3, 4, 5]);

  const [annualLeaveDuration, setAnnualLeaveDuration] = useState(24);
  const [normalNotice, setNormalNotice] = useState(14);
  const [forceMajeureNotice, setForceMajeureNotice] = useState(3);
  const [initialEligibility, setInitialEligibility] = useState(6);
  const [nextCycle, setNextCycle] = useState(11);
  const [reminder30, setReminder30] = useState(true);
  const [reminder14, setReminder14] = useState(true);
  const [reminder7, setReminder7] = useState(true);

  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const data = settingsQuery.data;
    if (!data) return;
    setCompanyName(data.company_name);
    setWorkStart(data.work_start_time.slice(0, 5));
    setWorkEnd(data.work_end_time.slice(0, 5));
    setGracePeriod(data.grace_period_minutes);
    setDuplicateWindow(data.duplicate_event_window_seconds);
    setWorkingDays(data.working_days);
    setAnnualLeaveDuration(data.annual_leave_duration_days);
    setNormalNotice(data.leave_normal_notice_days);
    setForceMajeureNotice(data.leave_force_majeure_notice_days);
    setInitialEligibility(data.leave_eligibility_after_months);
    setNextCycle(data.leave_next_cycle_after_months);
    setReminder30(data.leave_reminder_30_days_enabled);
    setReminder14(data.leave_reminder_14_days_enabled);
    setReminder7(data.leave_reminder_7_days_enabled);
  }, [settingsQuery.data]);

  const saveMutation = useMutation({
    mutationFn: () =>
      settingsApi.update({
        company_name: companyName,
        work_start_time: workStart,
        work_end_time: workEnd,
        grace_period_minutes: gracePeriod,
        duplicate_event_window_seconds: duplicateWindow,
        working_days: workingDays,
        annual_leave_duration_days: annualLeaveDuration,
        leave_normal_notice_days: normalNotice,
        leave_force_majeure_notice_days: forceMajeureNotice,
        leave_eligibility_after_months: initialEligibility,
        leave_next_cycle_after_months: nextCycle,
        leave_reminder_30_days_enabled: reminder30,
        leave_reminder_14_days_enabled: reminder14,
        leave_reminder_7_days_enabled: reminder7,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["settings"] });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    },
    onError: (err: unknown) => setError(getErrorMessage(err)),
  });

  function toggleDay(day: number) {
    setWorkingDays((previous) => (previous.includes(day) ? previous.filter((d) => d !== day) : [...previous, day].sort((a, b) => a - b)));
  }

  if (settingsQuery.isLoading) return <LoadingState label={t("common.loading")} />;
  if (settingsQuery.isError) return <ErrorState message={t("settings.couldNotLoad")} />;

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1 className="font-display text-2xl font-semibold text-ink">{t("settings.title")}</h1>
        <p className="text-sm text-ink-muted">{t("settings.subtitle")}</p>
      </div>

      <Card>
        <CardHeader>
          <h2 className="font-display text-base font-semibold text-ink">{t("settings.company")}</h2>
        </CardHeader>
        <CardBody>
          <Label htmlFor="company_name">{t("settings.companyName")}</Label>
          <Input id="company_name" value={companyName} onChange={(event) => setCompanyName(event.target.value)} />
        </CardBody>
      </Card>

      <Card>
        <CardHeader>
          <h2 className="font-display text-base font-semibold text-ink">{t("settings.workingHours")}</h2>
        </CardHeader>
        <CardBody className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="work_start">{t("settings.workStart")}</Label>
              <Input id="work_start" type="time" value={workStart} onChange={(event) => setWorkStart(event.target.value)} />
            </div>
            <div>
              <Label htmlFor="work_end">{t("settings.workEnd")}</Label>
              <Input id="work_end" type="time" value={workEnd} onChange={(event) => setWorkEnd(event.target.value)} />
            </div>
          </div>
          <div>
            <Label htmlFor="grace">{t("settings.gracePeriod")}</Label>
            <Input
              id="grace"
              type="number"
              min={0}
              max={240}
              value={gracePeriod}
              onChange={(event) => setGracePeriod(Number(event.target.value))}
            />
            <p className="mt-1 text-xs text-ink-muted">{t("settings.gracePeriodHint")}</p>
          </div>
          <div>
            <p className="mb-2 text-sm font-medium text-ink">{t("settings.workingDays")}</p>
            <div className="flex gap-2">
              {WEEKDAYS.map((day) => (
                <button
                  key={day}
                  type="button"
                  onClick={() => toggleDay(day)}
                  aria-pressed={workingDays.includes(day)}
                  className={cn(
                    "h-9 w-9 rounded-lg text-sm font-medium transition-colors",
                    workingDays.includes(day) ? "bg-brand text-white" : "bg-canvas text-ink-muted hover:text-ink",
                  )}
                >
                  {t(`settings.weekdays.${day}`)}
                </button>
              ))}
            </div>
            {workingDays.length === 0 && <p className="mt-1 text-xs text-status-danger">{t("settings.selectAtLeastOneDay")}</p>}
          </div>
        </CardBody>
      </Card>

      <Card>
        <CardHeader>
          <h2 className="font-display text-base font-semibold text-ink">{t("settings.duplicateScanning")}</h2>
        </CardHeader>
        <CardBody className="space-y-4">
          <div>
            <Label htmlFor="duplicate">{t("settings.duplicateWindow")}</Label>
            <Input
              id="duplicate"
              type="number"
              min={0}
              max={3600}
              value={duplicateWindow}
              onChange={(event) => setDuplicateWindow(Number(event.target.value))}
            />
            <p className="mt-1 text-xs text-ink-muted">{t("settings.duplicateWindowHint")}</p>
          </div>
        </CardBody>
      </Card>

      <Card>
        <CardHeader>
          <h2 className="font-display text-base font-semibold text-ink">{t("leaveSettings.title")}</h2>
        </CardHeader>
        <CardBody className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="annual_duration">{t("leaveSettings.annualDuration")}</Label>
              <Input
                id="annual_duration"
                type="number"
                min={1}
                max={90}
                value={annualLeaveDuration}
                onChange={(event) => setAnnualLeaveDuration(Number(event.target.value))}
              />
            </div>
            <div>
              <Label htmlFor="initial_eligibility">{t("leaveSettings.initialEligibility")}</Label>
              <Input
                id="initial_eligibility"
                type="number"
                min={0}
                max={36}
                value={initialEligibility}
                onChange={(event) => setInitialEligibility(Number(event.target.value))}
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="normal_notice">{t("leaveSettings.normalNotice")}</Label>
              <Input
                id="normal_notice"
                type="number"
                min={0}
                max={180}
                value={normalNotice}
                onChange={(event) => setNormalNotice(Number(event.target.value))}
              />
            </div>
            <div>
              <Label htmlFor="force_majeure_notice">{t("leaveSettings.forceMajeureNotice")}</Label>
              <Input
                id="force_majeure_notice"
                type="number"
                min={0}
                max={90}
                value={forceMajeureNotice}
                onChange={(event) => setForceMajeureNotice(Number(event.target.value))}
              />
            </div>
          </div>
          <div>
            <Label htmlFor="next_cycle">{t("leaveSettings.nextCycle")}</Label>
            <Input
              id="next_cycle"
              type="number"
              min={0}
              max={36}
              value={nextCycle}
              onChange={(event) => setNextCycle(Number(event.target.value))}
              className="max-w-xs"
            />
          </div>
          <div className="border-t border-line pt-4">
            <p className="mb-2 text-sm font-medium text-ink">{t("leaveSettings.reminders")}</p>
            <div className="space-y-2">
              <label className="flex items-center gap-2 text-sm text-ink">
                <input type="checkbox" checked={reminder30} onChange={(event) => setReminder30(event.target.checked)} className="rounded border-line" />
                {t("leaveSettings.reminder30")}
              </label>
              <label className="flex items-center gap-2 text-sm text-ink">
                <input type="checkbox" checked={reminder14} onChange={(event) => setReminder14(event.target.checked)} className="rounded border-line" />
                {t("leaveSettings.reminder14")}
              </label>
              <label className="flex items-center gap-2 text-sm text-ink">
                <input type="checkbox" checked={reminder7} onChange={(event) => setReminder7(event.target.checked)} className="rounded border-line" />
                {t("leaveSettings.reminder7")}
              </label>
            </div>
          </div>
        </CardBody>
      </Card>

      {error && (
        <p role="alert" className="rounded-lg bg-status-danger-bg px-3 py-2 text-sm text-status-danger">
          {error}
        </p>
      )}
      <div className="flex items-center gap-3">
        <Button
          onClick={() => {
            setError(null);
            saveMutation.mutate();
          }}
          disabled={saveMutation.isPending || workingDays.length === 0}
        >
          {saveMutation.isPending ? t("common.saving") : t("settings.saveSettings")}
        </Button>
        {saved && <span className="text-sm text-status-success">{t("settings.saved")}</span>}
      </div>
    </div>
  );
}
