import { Menu } from "lucide-react";
import { useTranslation } from "react-i18next";

import { TopbarUtilities } from "@/components/layout/TopbarUtilities";

export function EmployeeTopbar({ onMenuClick }: { onMenuClick: () => void }) {
  const { t } = useTranslation();

  return (
    <header className="flex h-16 items-center justify-end gap-3 border-b border-line bg-surface px-4 md:px-6">
      <button
        type="button"
        onClick={onMenuClick}
        className="mr-auto rounded-lg p-2 text-ink-muted hover:bg-canvas hover:text-ink md:hidden"
        aria-label="Menu"
      >
        <Menu size={20} />
      </button>
      <TopbarUtilities fallbackLabel={t("nav.profile")} />
    </header>
  );
}