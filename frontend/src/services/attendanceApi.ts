import type { AttendanceResponse, DayOverviewResponse, EmployeeAttendanceSummaryResponse, Page, ScanResponse } from "@/types/models";
import type { AttendanceStatus } from "@/types/enums";

import { api } from "./api";

export const attendanceApi = {
  today: (params?: { date?: string; department_id?: number }) =>
    api.get<DayOverviewResponse>("/attendance/today", { params }).then((r) => r.data),

  history: (params: {
    employee_id?: number;
    department_id?: number;
    status?: AttendanceStatus;
    date_from?: string;
    date_to?: string;
    page?: number;
    page_size?: number;
  }) => api.get<Page<AttendanceResponse>>("/attendance/history", { params }).then((r) => r.data),

  forEmployee: (
    employeeId: number,
    params?: { date_from?: string; date_to?: string; page?: number; page_size?: number },
  ) => api.get<Page<AttendanceResponse>>(`/attendance/employee/${employeeId}`, { params }).then((r) => r.data),

  summary: (employeeId: number, month?: string) =>
    api
      .get<EmployeeAttendanceSummaryResponse>(`/attendance/employee/${employeeId}/summary`, { params: { month } })
      .then((r) => r.data),

  /** The endpoint requires the same Bearer auth as every other call, which a plain
   * <a href> cannot send - so this fetches the file through the authenticated
   * client and triggers the browser's save dialog from the response in memory. */
  downloadExport: async (
    format: "csv" | "xlsx",
    params: {
      employee_id?: number;
      department_id?: number;
      status?: AttendanceStatus;
      date_from?: string;
      date_to?: string;
    },
  ) => {
    const response = await api.get("/attendance/history/export", {
      params: { format, ...params },
      responseType: "blob",
    });
    const blobUrl = URL.createObjectURL(response.data as Blob);
    const link = document.createElement("a");
    link.href = blobUrl;
    link.download = `attendance-export.${format}`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(blobUrl);
  },

  scan: () => api.post<ScanResponse>("/attendance/scan").then((r) => r.data),
};
