import type { DashboardStatisticsResponse, DepartmentBreakdown, TrendDay } from "@/types/models";

import { api } from "./api";

export const dashboardApi = {
  statistics: (date?: string) =>
    api.get<DashboardStatisticsResponse>("/dashboard/statistics", { params: { date } }).then((r) => r.data),

  trend: (days = 14) => api.get<TrendDay[]>("/dashboard/trend", { params: { days } }).then((r) => r.data),

  departments: (date?: string) =>
    api.get<DepartmentBreakdown[]>("/dashboard/departments", { params: { date } }).then((r) => r.data),
};
