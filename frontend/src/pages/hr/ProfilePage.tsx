import { useTranslation } from "react-i18next";

import { LanguageSwitcher } from "@/components/layout/LanguageSwitcher";
import { ChangePasswordForm } from "@/components/profile/ChangePasswordForm";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { useAuth } from "@/contexts/AuthContext";

export function HrProfilePage() {
  const { t } = useTranslation();
  const { user } = useAuth();

  return (
    <div className="max-w-lg space-y-6">
      <div>
        <h1 className="font-display text-2xl font-semibold text-ink">{t("profile.title")}</h1>
        <p className="text-sm text-ink-muted">{t("profile.subtitle")}</p>
      </div>

      <Card>
        <CardBody className="space-y-2 text-sm">
          <Row label={t("profile.email")} value={user?.email ?? "-"} />
          <Row label={t("profile.role")} value={t("profile.hrAdmin")} />
          {user?.employee && (
            <Row label={t("profile.linkedEmployee")} value={`${user.employee.full_name} (${user.employee.employee_id})`} />
          )}
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
