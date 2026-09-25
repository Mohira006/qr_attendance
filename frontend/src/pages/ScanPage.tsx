import { CheckCircle2, Clock, LogOut, XCircle } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { LanguageSwitcher } from "@/components/layout/LanguageSwitcher";
import { Button } from "@/components/ui/Button";
import { LoadingState } from "@/components/ui/States";
import { useAuth } from "@/contexts/AuthContext";
import { useSettings } from "@/hooks/useSettings";
import { getErrorCode, getErrorMessage } from "@/services/api";
import { attendanceApi } from "@/services/attendanceApi";
import type { ScanResponse } from "@/types/models";
import { formatMinutes, formatTime } from "@/utils/format";

export function ScanPage() {
  const { t } = useTranslation();
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  // ScanPage is a standalone route outside both HrLayout and EmployeeLayout,
  // which are the only places this hook normally gets called - without it here,
  // the company timezone stays at its "UTC" default and every displayed time
  // (and only the display - late-minutes itself is computed server-side, in the
  // correct timezone, and is unaffected) would be off by the UTC offset.
  useSettings();
  const [state, setState] = useState<"loading" | "done" | "error">("loading");
  const [result, setResult] = useState<ScanResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const hasScanned = useRef(false);

  useEffect(() => {
    if (hasScanned.current) return; // guards against React StrictMode's double-invoke in dev
    hasScanned.current = true;
    attendanceApi
      .scan()
      .then((response) => {
        setResult(response);
        setState("done");
      })
      .catch((err: unknown) => {
        const code = getErrorCode(err);
        setErrorMessage(code === "employee_not_found" ? t("scan.notAnEmployee") : getErrorMessage(err));
        setState("error");
      });
  }, [t]);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-ink px-4">
      <div className="mb-6">
        <LanguageSwitcher variant="dark" />
      </div>

      <div className="w-full max-w-sm rounded-2xl bg-surface p-8 text-center shadow-card">
        {state === "loading" && <LoadingState label={t("scan.scanning")} />}

        {state === "error" && (
          <>
            <XCircle size={56} className="mx-auto mb-4 text-status-danger" />
            <p className="text-ink">{errorMessage}</p>
          </>
        )}

        {state === "done" && result && <ScanResult result={result} />}

        <div className="mt-6 flex flex-col gap-2 border-t border-line pt-6">
          <Button onClick={() => navigate(user?.role === "hr" ? "/hr/dashboard" : "/me/dashboard")}>
            {t("scan.goToDashboard")}
          </Button>
          <button
            type="button"
            onClick={() => void logout()}
            className="flex items-center justify-center gap-1.5 text-sm text-ink-muted hover:text-ink"
          >
            <LogOut size={14} /> {t("nav.logout")}
          </button>
        </div>
      </div>
    </div>
  );
}

function ScanResult({ result }: { result: ScanResponse }) {
  const { t } = useTranslation();

  if (result.outcome === "duplicate") {
    return (
      <>
        <Clock size={56} className="mx-auto mb-4 text-status-warning" />
        <h1 className="font-display text-lg font-semibold text-ink">{t("scan.alreadyRecorded")}</h1>
        <p className="mt-1 text-sm text-ink-muted">{t("scan.alreadyRecordedDescription")}</p>
      </>
    );
  }

  if (result.outcome === "rejected" || !result.attendance) {
    return (
      <>
        <XCircle size={56} className="mx-auto mb-4 text-status-danger" />
        <p className="text-ink">{result.message}</p>
      </>
    );
  }

  const { attendance } = result;

  if (result.outcome === "check_in") {
    const isLate = attendance.status === "late";
    return (
      <>
        <CheckCircle2 size={56} className={isLate ? "mx-auto mb-4 text-status-warning" : "mx-auto mb-4 text-status-success"} />
        <h1 className="font-display text-lg font-semibold text-ink">{t("scan.checkedIn", { time: formatTime(attendance.check_in) })}</h1>
        {isLate && <p className="mt-1 text-sm text-status-warning">{t("scan.lateBy", { minutes: attendance.late_minutes })}</p>}
      </>
    );
  }

  return (
    <>
      <CheckCircle2 size={56} className="mx-auto mb-4 text-brand" />
      <h1 className="font-display text-lg font-semibold text-ink">
        {t("scan.checkedOut", { time: attendance.check_out ? formatTime(attendance.check_out) : "" })}
      </h1>
      {attendance.total_working_minutes !== null && (
        <p className="mt-1 text-sm text-ink-muted">{t("scan.workedToday", { duration: formatMinutes(attendance.total_working_minutes) })}</p>
      )}
    </>
  );
}
