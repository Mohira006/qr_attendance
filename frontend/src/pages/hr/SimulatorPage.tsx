import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Wand2 } from "lucide-react";
import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Input, Label, Select } from "@/components/ui/Input";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { getErrorMessage } from "@/services/api";
import { simulatorApi } from "@/services/settingsApi";
import type { FaceEventRequestType } from "@/types/enums";
import type { FaceEventResponse } from "@/types/models";
import { formatTime } from "@/utils/format";
import { attendanceStatusTokens } from "@/utils/status";

const OUTCOME_KEYS: Record<FaceEventResponse["outcome"], string> = {
  check_in: "simulator.outcomes.checkIn",
  check_out: "simulator.outcomes.checkOut",
  duplicate: "simulator.outcomes.duplicate",
  unknown_employee: "simulator.outcomes.unknownEmployee",
  rejected: "simulator.outcomes.rejected",
};

interface LogItem {
  id: number;
  result: FaceEventResponse;
}

export function SimulatorPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const employeesQuery = useQuery({ queryKey: ["simulator", "employees"], queryFn: simulatorApi.employees });

  const [identifier, setIdentifier] = useState("");
  const [requestedType, setRequestedType] = useState<FaceEventRequestType>("auto");
  const [useCustomTime, setUseCustomTime] = useState(false);
  const [customTime, setCustomTime] = useState("");
  const [log, setLog] = useState<LogItem[]>([]);

  const triggerMutation = useMutation({
    mutationFn: () => simulatorApi.trigger(identifier, requestedType, useCustomTime && customTime ? customTime : undefined),
    onSuccess: (result) => {
      setLog((previous) => [{ id: Date.now(), result }, ...previous].slice(0, 10));
      void queryClient.invalidateQueries({ queryKey: ["attendance"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!identifier) return;
    triggerMutation.mutate();
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="flex items-center gap-2 font-display text-2xl font-semibold text-ink">
          <Wand2 size={22} className="text-brand" />
          {t("simulator.title")}
        </h1>
        <p className="text-sm text-ink-muted">{t("simulator.subtitle")}</p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <h2 className="font-display text-base font-semibold text-ink">{t("simulator.triggerEvent")}</h2>
          </CardHeader>
          <CardBody>
            <form onSubmit={onSubmit} className="space-y-4">
              <div>
                <Label htmlFor="employee">{t("simulator.employee")}</Label>
                <Select id="employee" value={identifier} onChange={(event) => setIdentifier(event.target.value)} required>
                  <option value="">{t("simulator.selectEmployee")}</option>
                  {employeesQuery.data?.map((employee) => (
                    <option key={employee.id} value={employee.employee_id}>
                      {employee.full_name} ({employee.employee_id}) - {employee.department.name}
                    </option>
                  ))}
                </Select>
              </div>

              <div>
                <Label htmlFor="direction">{t("simulator.direction")}</Label>
                <Select
                  id="direction"
                  value={requestedType}
                  onChange={(event) => setRequestedType(event.target.value as FaceEventRequestType)}
                >
                  <option value="auto">{t("simulator.directionAuto")}</option>
                  <option value="check_in">{t("simulator.directionCheckIn")}</option>
                  <option value="check_out">{t("simulator.directionCheckOut")}</option>
                </Select>
              </div>

              <div>
                <label className="flex items-center gap-2 text-sm text-ink">
                  <input
                    type="checkbox"
                    checked={useCustomTime}
                    onChange={(event) => setUseCustomTime(event.target.checked)}
                    className="rounded border-line"
                  />
                  {t("simulator.useSpecificTime")}
                </label>
                {useCustomTime && (
                  <Input
                    type="datetime-local"
                    value={customTime}
                    onChange={(event) => setCustomTime(event.target.value)}
                    className="mt-2"
                  />
                )}
              </div>

              {triggerMutation.isError && (
                <p role="alert" className="rounded-lg bg-status-danger-bg px-3 py-2 text-sm text-status-danger">
                  {getErrorMessage(triggerMutation.error)}
                </p>
              )}

              <Button type="submit" disabled={!identifier || triggerMutation.isPending} className="w-full">
                {triggerMutation.isPending ? t("simulator.simulating") : t("simulator.simulateButton")}
              </Button>
            </form>
          </CardBody>
        </Card>

        <Card>
          <CardHeader>
            <h2 className="font-display text-base font-semibold text-ink">{t("simulator.recentResults")}</h2>
          </CardHeader>
          <CardBody>
            {log.length === 0 ? (
              <p className="py-8 text-center text-sm text-ink-muted">{t("simulator.triggerToSeeResult")}</p>
            ) : (
              <ul className="space-y-3">
                {log.map(({ id, result }) => (
                  <LogEntry key={id} result={result} />
                ))}
              </ul>
            )}
          </CardBody>
        </Card>
      </div>
    </div>
  );
}

function LogEntry({ result }: { result: FaceEventResponse }) {
  const { t } = useTranslation();
  const time = result.attendance ? formatTime(result.attendance.check_out ?? result.attendance.check_in) : null;
  return (
    <li className="rounded-lg border border-line p-3">
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm font-medium text-ink">{result.employee?.full_name ?? t("simulator.outcomes.unknownEmployee")}</span>
        {result.attendance && <StatusBadge tokens={attendanceStatusTokens(result.attendance.status)} />}
      </div>
      <p className="mt-1 text-sm text-ink-muted">
        {t(OUTCOME_KEYS[result.outcome])}
        {time ? ` at ${time}` : ""}
      </p>
      <p className="mt-1 font-mono text-xs text-ink-faint">{result.message}</p>
    </li>
  );
}
