import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell, CheckCheck } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";
import { notificationsApi } from "@/services/notificationsApi";
import { cn } from "@/utils/cn";
import { formatDateTime } from "@/utils/format";

export function HrNotificationsPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [page, setPage] = useState(1);

  const notificationsQuery = useQuery({
    queryKey: ["notifications", "all", unreadOnly, page],
    queryFn: () => notificationsApi.list({ unread_only: unreadOnly, page, page_size: 25 }),
  });

  const markReadMutation = useMutation({
    mutationFn: (id: number) => notificationsApi.markRead(id),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["notifications"] }),
  });

  const markAllReadMutation = useMutation({
    mutationFn: () => notificationsApi.markAllRead(),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["notifications"] }),
  });

  const data = notificationsQuery.data;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-semibold text-ink">{t("notifications.title")}</h1>
          <p className="text-sm text-ink-muted">{t("notifications.subtitle")}</p>
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-ink-muted">
            <input
              type="checkbox"
              checked={unreadOnly}
              onChange={(event) => {
                setUnreadOnly(event.target.checked);
                setPage(1);
              }}
              className="rounded border-line"
            />
            {t("notifications.unreadOnly")}
          </label>
          <Button variant="secondary" size="sm" onClick={() => markAllReadMutation.mutate()} disabled={markAllReadMutation.isPending}>
            <CheckCheck size={14} className="mr-1.5" /> {t("notifications.markAllRead")}
          </Button>
        </div>
      </div>

      {notificationsQuery.isLoading && <LoadingState label={t("common.loading")} />}
      {notificationsQuery.isError && <ErrorState message={t("notifications.couldNotLoad")} />}

      {data &&
        (data.items.length === 0 ? (
          <EmptyState title={t("notifications.noNotifications")} icon={<Bell size={28} />} description={t("notifications.allCaughtUp")} />
        ) : (
          <Card>
            <ul>
              {data.items.map((notification) => (
                <li
                  key={notification.id}
                  className={cn(
                    "flex items-start justify-between gap-4 border-b border-line px-5 py-4 last:border-0",
                    !notification.is_read && "bg-brand-light/30",
                  )}
                >
                  <div>
                    {/* Backend-generated content stays in English for now - see the
                        NotificationBell.tsx comment and the Stage 7 summary for why. */}
                    <p className="font-medium text-ink">{notification.title}</p>
                    <p className="mt-0.5 text-sm text-ink-muted">{notification.message}</p>
                    <p className="mt-1 font-mono text-xs text-ink-faint">{formatDateTime(notification.created_at)}</p>
                  </div>
                  {!notification.is_read && (
                    <button
                      type="button"
                      onClick={() => markReadMutation.mutate(notification.id)}
                      className="shrink-0 text-sm font-medium text-brand hover:text-brand-hover"
                    >
                      {t("notifications.markRead")}
                    </button>
                  )}
                </li>
              ))}
            </ul>
            {data.pages > 1 && (
              <div className="flex items-center justify-between border-t border-line px-4 py-3">
                <p className="text-sm text-ink-muted">{t("common.page", { page: data.page, pages: data.pages })}</p>
                <div className="flex gap-2">
                  <Button variant="secondary" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                    {t("common.previous")}
                  </Button>
                  <Button variant="secondary" size="sm" disabled={page >= data.pages} onClick={() => setPage((p) => p + 1)}>
                    {t("common.next")}
                  </Button>
                </div>
              </div>
            )}
          </Card>
        ))}
    </div>
  );
}
