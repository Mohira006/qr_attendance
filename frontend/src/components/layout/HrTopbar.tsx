import { Search } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { TopbarUtilities } from "@/components/layout/TopbarUtilities";

export function HrTopbar() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [search, setSearch] = useState("");

  function onSearchSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (search.trim()) {
      navigate(`/hr/employees?search=${encodeURIComponent(search.trim())}`);
    }
  }

  return (
    <header className="flex h-16 items-center justify-between border-b border-line bg-surface px-6">
      <form onSubmit={onSearchSubmit} className="w-full max-w-sm">
        <div className="relative">
          <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-faint" />
          <input
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder={t("employees.searchPlaceholder")}
            className="w-full rounded-lg border border-line bg-canvas py-2 pl-9 pr-3 text-sm text-ink placeholder:text-ink-faint focus:bg-white"
          />
        </div>
      </form>

      <TopbarUtilities notificationsHref="/hr/notifications" fallbackLabel={t("profile.hrAdmin")} />
    </header>
  );
}
