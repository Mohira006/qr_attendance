import type { Message, NotificationResponse, Page } from "@/types/models";

import { api } from "./api";

export const notificationsApi = {
  list: (params?: { unread_only?: boolean; page?: number; page_size?: number }) =>
    api.get<Page<NotificationResponse>>("/notifications", { params }).then((r) => r.data),

  unreadCount: () => api.get<{ unread_count: number }>("/notifications/unread-count").then((r) => r.data),

  markRead: (id: number) => api.put<NotificationResponse>(`/notifications/${id}/read`).then((r) => r.data),

  markAllRead: () => api.put<Message>("/notifications/read-all").then((r) => r.data),
};
