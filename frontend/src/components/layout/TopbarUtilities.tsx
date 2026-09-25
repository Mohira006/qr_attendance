import { ConnectionIndicator } from "@/components/layout/ConnectionIndicator";
import { LanguageSwitcher } from "@/components/layout/LanguageSwitcher";
import { LiveClock } from "@/components/layout/LiveClock";
import { NotificationBell } from "@/components/layout/NotificationBell";
import { useAuth } from "@/contexts/AuthContext";

export function TopbarUtilities({ notificationsHref, fallbackLabel }: { notificationsHref?: string; fallbackLabel: string }) {
  const { user } = useAuth();

  return (
    <div className="flex items-center gap-5">
      <ConnectionIndicator />
      <LiveClock />
      <LanguageSwitcher />
      <NotificationBell viewAllHref={notificationsHref} />
      <div className="flex items-center gap-2 border-l border-line pl-4">
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-light font-display text-sm font-semibold text-brand">
          {(user?.employee?.full_name ?? user?.email ?? fallbackLabel).charAt(0).toUpperCase()}
        </div>
        <div className="hidden text-sm leading-tight sm:block">
          <p className="font-medium text-ink">{user?.employee?.full_name ?? fallbackLabel}</p>
          <p className="text-xs text-ink-muted">{user?.email}</p>
        </div>
      </div>
    </div>
  );
}
