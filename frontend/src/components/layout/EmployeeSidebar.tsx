import { CalendarClock, FileText, LayoutDashboard, LogOut, Palmtree, UserCircle } from "lucide-react";
import { useTranslation } from "react-i18next";
import { NavLink } from "react-router-dom";

import { useAuth } from "@/contexts/AuthContext";
import { cn } from "@/utils/cn";

const NAV_ITEMS = [
  { to: "/me/dashboard", labelKey: "nav.dashboard", icon: LayoutDashboard },
  { to: "/me/history", labelKey: "nav.history", icon: CalendarClock },
  { to: "/me/leave", labelKey: "nav.myLeave", icon: Palmtree },
  { to: "/me/explanation-letters", labelKey: "nav.myLetters", icon: FileText },
];

export function EmployeeSidebar() {
  const { t } = useTranslation();
  const { logout } = useAuth();

  return (
    <aside className="flex h-screen w-60 flex-col bg-ink text-white">
      <div className="flex items-center gap-2 px-5 py-5">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand font-display text-sm font-bold">
          QR
        </div>
        <span className="font-display text-base font-semibold">{t("auth.appName")}</span>
      </div>

      <nav className="flex-1 space-y-0.5 px-3">
        {NAV_ITEMS.map(({ to, labelKey, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                isActive ? "bg-brand text-white" : "text-white/70 hover:bg-white/10 hover:text-white",
              )
            }
          >
            <Icon size={18} />
            {t(labelKey)}
          </NavLink>
        ))}
      </nav>

      <div className="space-y-0.5 border-t border-white/10 px-3 py-3">
        <NavLink
          to="/me/profile"
          className={({ isActive }) =>
            cn(
              "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
              isActive ? "bg-brand text-white" : "text-white/70 hover:bg-white/10 hover:text-white",
            )
          }
        >
          <UserCircle size={18} />
          {t("nav.profile")}
        </NavLink>
        <button
          type="button"
          onClick={() => void logout()}
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-white/70 transition-colors hover:bg-white/10 hover:text-white"
        >
          <LogOut size={18} />
          {t("nav.logout")}
        </button>
      </div>
    </aside>
  );
}
