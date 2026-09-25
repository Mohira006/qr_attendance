import { useTranslation } from "react-i18next";

import { TopbarUtilities } from "@/components/layout/TopbarUtilities";

export function EmployeeTopbar() {
  const { t } = useTranslation();

  return (
    <header className="flex h-16 items-center justify-end border-b border-line bg-surface px-6">
      <TopbarUtilities fallbackLabel={t("nav.profile")} />
    </header>
  );
}
