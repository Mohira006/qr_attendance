import { useQuery } from "@tanstack/react-query";
import { Activity, AlertTriangle, Clock, Palmtree, UserCheck, Users, UserX } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { StatCard } from "@/components/attendance/StatCard";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { getErrorMessage } from "@/services/api";
import { dashboardApi } from "@/services/dashboardApi";
import { formatDateShort } from "@/utils/format";

export function DashboardPage() {
  const { t } = useTranslation();
  const statsQuery = useQuery({ queryKey: ["dashboard", "statistics"], queryFn: () => dashboardApi.statistics() });
  const trendQuery = useQuery({ queryKey: ["dashboard", "trend"], queryFn: () => dashboardApi.trend(14) });
  const departmentsQuery = useQuery({ queryKey: ["dashboard", "departments"], queryFn: () => dashboardApi.departments() });

  const stats = statsQuery.data;

  if (statsQuery.isLoading) return <LoadingState label={t("common.loading")} />;
  if (statsQuery.isError || !stats) return <ErrorState message={getErrorMessage(statsQuery.error)} />;

  const departmentChartData = (departmentsQuery.data ?? []).map((row) => ({
    name: row.department.name,
    onTime: row.on_time_count,
    late: row.late_count,
    absent: row.absent_count,
  }));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-semibold text-ink">{t("dashboard.title")}</h1>
        <p className="text-sm text-ink-muted">{t("dashboard.subtitle", { date: formatDateShort(stats.date) })}</p>
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        <StatCard label={t("dashboard.totalEmployees")} value={stats.total_employees} icon={<Users size={20} />} />
        <StatCard
          label={t("dashboard.presentToday")}
          value={stats.present_today}
          icon={<UserCheck size={20} />}
          accentClass="bg-brand-light text-brand"
        />
        <StatCard
          label={t("dashboard.onTime")}
          value={stats.on_time_count}
          icon={<Clock size={20} />}
          accentClass="bg-status-success-bg text-status-success"
        />
        <StatCard
          label={t("dashboard.late")}
          value={stats.late_count}
          icon={<AlertTriangle size={20} />}
          accentClass="bg-status-danger-bg text-status-danger"
        />
        <StatCard
          label={t("dashboard.absent")}
          value={stats.absent_count}
          icon={<UserX size={20} />}
          accentClass="bg-status-neutral-bg text-status-neutral"
        />
        <StatCard
          label={t("dashboard.currentlyWorking")}
          value={stats.currently_working_count}
          icon={<Activity size={20} />}
          accentClass="bg-status-warning-bg text-status-warning"
        />
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card>
          <CardBody>
            <p className="text-sm text-ink-muted">{t("dashboard.attendanceRate")}</p>
            <p className="mt-1 font-display text-3xl font-semibold tabular-nums text-ink">{stats.attendance_percentage}%</p>
          </CardBody>
        </Card>
        <Card>
          <CardBody>
            <p className="text-sm text-ink-muted">{t("dashboard.averageArrivalTime")}</p>
            <p className="mt-1 font-mono text-3xl font-semibold tabular-nums text-ink">{stats.average_arrival_time ?? "-"}</p>
          </CardBody>
        </Card>
        <Card>
          <CardBody className="flex items-center gap-3">
            <Palmtree size={20} className="text-status-warning" />
            <div>
              <p className="text-sm text-ink-muted">{t("dashboard.onApprovedLeave")}</p>
              <p className="font-display text-2xl font-semibold tabular-nums text-ink">{stats.on_leave_count}</p>
            </div>
          </CardBody>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <h2 className="font-display text-base font-semibold text-ink">{t("dashboard.attendanceTrend")}</h2>
          </CardHeader>
          <CardBody>
            {trendQuery.data ? (
              <ResponsiveContainer width="100%" height={260}>
                <LineChart data={trendQuery.data}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E4E7EC" vertical={false} />
                  <XAxis
                    dataKey="date"
                    tickFormatter={(value: string) => formatDateShort(value)}
                    tick={{ fontSize: 12, fill: "#5B6472" }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis
                    domain={[0, 100]}
                    unit="%"
                    tick={{ fontSize: 12, fill: "#5B6472" }}
                    axisLine={false}
                    tickLine={false}
                    width={44}
                  />
                  <Tooltip
                    labelFormatter={(value) => formatDateShort(value as string)}
                    formatter={(value: number) => [`${value}%`, t("dashboard.attendanceRate")]}
                    contentStyle={{ borderRadius: 8, borderColor: "#E4E7EC", fontSize: 13 }}
                  />
                  <Line type="monotone" dataKey="attendance_percentage" stroke="#3452E1" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <LoadingState label={t("dashboard.loadingTrend")} />
            )}
          </CardBody>
        </Card>

        <Card>
          <CardHeader>
            <h2 className="font-display text-base font-semibold text-ink">{t("dashboard.byDepartment")}</h2>
          </CardHeader>
          <CardBody>
            {departmentsQuery.data ? (
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={departmentChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E4E7EC" vertical={false} />
                  <XAxis dataKey="name" tick={{ fontSize: 12, fill: "#5B6472" }} axisLine={false} tickLine={false} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 12, fill: "#5B6472" }} axisLine={false} tickLine={false} width={28} />
                  <Tooltip contentStyle={{ borderRadius: 8, borderColor: "#E4E7EC", fontSize: 13 }} />
                  <Bar dataKey="onTime" name={t("dashboard.onTime")} stackId="a" fill="#1A8754" />
                  <Bar dataKey="late" name={t("dashboard.late")} stackId="a" fill="#D64545" />
                  <Bar dataKey="absent" name={t("dashboard.absent")} stackId="a" fill="#8B93A1" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <LoadingState label={t("dashboard.loadingBreakdown")} />
            )}
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
