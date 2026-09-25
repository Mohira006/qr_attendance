import type { AuditLogResponse, Page, SettingsResponse } from "@/types/models";

import { api } from "./api";

export const settingsApi = {
  get: () => api.get<SettingsResponse>("/settings").then((r) => r.data),

  update: (data: Partial<{
    company_name: string;
    work_start_time: string;
    work_end_time: string;
    grace_period_minutes: number;
    duplicate_event_window_seconds: number;
    working_days: number[];
    annual_leave_duration_days: number;
    leave_normal_notice_days: number;
    leave_force_majeure_notice_days: number;
    leave_eligibility_after_months: number;
    leave_next_cycle_after_months: number;
    leave_reminder_30_days_enabled: boolean;
    leave_reminder_14_days_enabled: boolean;
    leave_reminder_7_days_enabled: boolean;
  }>) => api.put<SettingsResponse>("/settings", data).then((r) => r.data),
};

export const auditApi = {
  list: (params?: { action?: string; entity_type?: string; user_id?: number; page?: number; page_size?: number }) =>
    api.get<Page<AuditLogResponse>>("/audit-logs", { params }).then((r) => r.data),
};
