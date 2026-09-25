import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { Avatar } from "@/components/attendance/Avatar";
import { LanguageSwitcher } from "@/components/layout/LanguageSwitcher";
import { ChangePasswordForm } from "@/components/profile/ChangePasswordForm";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { employeesApi } from "@/services/employeesApi";
import { formatWorkTime } from "@/utils/format";

export function EmployeeProfilePage() {
  const { t } = useTranslation();
  const meQuery = useQuery({ queryKey: ["employees", "me"], queryFn: employeesApi.me });

  if (meQuery.isLoading) return <LoadingState label={t("common.loading")} />;
  if (meQuery.isError || !meQuery.data) return <ErrorState message={t("employeeDashboard.notLinked")} />;

  const employee = meQuery.data;

  return (
    <div className="max-w-lg space-y-6">
      <div>
        <h1 className="font-display text-2xl font-semibold text-ink">{t("profile.title")}</h1>
        <p className="text-sm text-ink-muted">{t("profile.employeeSubtitle")}</p>
      </div>

      <Card>
        <CardBody className="flex items-center gap-4">
          <Avatar employee={employee} size={56} />
          <div>
            <p className="font-display text-lg font-semibold text-ink">{employee.full_name}</p>
            <p className="font-mono text-sm text-ink-muted">{employee.employee_id}</p>
          </div>
        </CardBody>
      </Card>

      <Card>
        <CardBody className="space-y-2 text-sm">
          <Row label={t("profile.department")} value={employee.department.name} />
          <Row label={t("profile.position")} value={employee.position ?? "-"} />
          <Row label={t("profile.email")} value={employee.email ?? "-"} />
          <Row label={t("profile.phone")} value={employee.phone ?? "-"} />
          <Row
            label={t("profile.workHours")}
            value={
              employee.work_start_time && employee.work_end_time
                ? `${formatWorkTime(employee.work_start_time)} - ${formatWorkTime(employee.work_end_time)}`
                : t("profile.companyDefault")
            }
          />
        </CardBody>
      </Card>

      <Card>
        <CardHeader>
          <h2 className="font-display text-base font-semibold text-ink">{t("profile.language")}</h2>
        </CardHeader>
        <CardBody>
          <LanguageSwitcher />
        </CardBody>
      </Card>

      <Card>
        <CardHeader>
          <h2 className="font-display text-base font-semibold text-ink">{t("profile.changePassword")}</h2>
        </CardHeader>
        <CardBody>
          <ChangePasswordForm />
        </CardBody>
      </Card>
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
