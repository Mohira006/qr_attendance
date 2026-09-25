import type { LeaveEligibilityResponse, LeaveRequestResponse, Page } from "@/types/models";
import type { LeaveRequestStatus, LeaveRequestType } from "@/types/enums";

import { api } from "./api";

export interface LeaveRequestCreateInput {
  requested_start_date: string;
  request_type: LeaveRequestType;
  employee_comment?: string | null;
}

export interface HrLeaveRequestCreateInput extends LeaveRequestCreateInput {
  employee_id: number;
  override_reason: string;
}

export const leaveApi = {
  list: (params?: {
    employee_id?: number;
    department_id?: number;
    status?: LeaveRequestStatus;
    date_from?: string;
    date_to?: string;
    page?: number;
    page_size?: number;
  }) => api.get<Page<LeaveRequestResponse>>("/leave-requests", { params }).then((r) => r.data),

  get: (id: number) => api.get<LeaveRequestResponse>(`/leave-requests/${id}`).then((r) => r.data),

  create: (payload: LeaveRequestCreateInput) =>
    api.post<LeaveRequestResponse>("/leave-requests", payload).then((r) => r.data),

  hrCreate: (payload: HrLeaveRequestCreateInput) =>
    api.post<LeaveRequestResponse>("/leave-requests/hr", payload).then((r) => r.data),

  approve: (id: number, hrComment?: string | null) =>
    api.put<LeaveRequestResponse>(`/leave-requests/${id}/approve`, { hr_comment: hrComment ?? null }).then((r) => r.data),

  reject: (id: number, hrComment?: string | null) =>
    api.put<LeaveRequestResponse>(`/leave-requests/${id}/reject`, { hr_comment: hrComment ?? null }).then((r) => r.data),

  cancel: (id: number) => api.put<LeaveRequestResponse>(`/leave-requests/${id}/cancel`).then((r) => r.data),

  updateComment: (id: number, hrComment: string) =>
    api.put<LeaveRequestResponse>(`/leave-requests/${id}/comment`, { hr_comment: hrComment }).then((r) => r.data),

  updateDuration: (id: number, durationDays: number) =>
    api.put<LeaveRequestResponse>(`/leave-requests/${id}/duration`, { duration_days: durationDays }).then((r) => r.data),

  calendar: (dateFrom: string, dateTo: string) =>
    api
      .get<LeaveRequestResponse[]>("/leave-requests/calendar", { params: { date_from: dateFrom, date_to: dateTo } })
      .then((r) => r.data),

  eligibility: (employeeId: number) =>
    api.get<LeaveEligibilityResponse>(`/employees/${employeeId}/leave-eligibility`).then((r) => r.data),
};
