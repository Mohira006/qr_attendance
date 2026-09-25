import { useQuery } from "@tanstack/react-query";
import { Download, FileSpreadsheet } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Input, Label, Select } from "@/components/ui/Input";
import { attendanceApi } from "@/services/attendanceApi";
import { departmentsApi } from "@/services/employeesApi";
import type { AttendanceStatus } from "@/types/enums";

export function ReportsPage() {
  const { t } = useTranslation();
  const departmentsQuery = useQuery({ queryKey: ["departments"], queryFn: () => departmentsApi.list("active") });

  const [departmentId, setDepartmentId] = useState("");
  const [status, setStatus] = useState<AttendanceStatus | "">("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [isDownloading, setIsDownloading] = useState<"csv" | "xlsx" | null>(null);

  async function onDownload(format: "csv" | "xlsx") {
    setIsDownloading(format);
    try {
      await attendanceApi.downloadExport(format, {
        department_id: departmentId ? Number(departmentId) : undefined,
        status: status || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
      });
    } finally {
      setIsDownloading(null);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-semibold text-ink">{t("reports.title")}</h1>
        <p className="text-sm text-ink-muted">{t("reports.subtitle")}</p>
      </div>

      <Card>
        <CardHeader>
          <h2 className="flex items-center gap-2 font-display text-base font-semibold text-ink">
            <FileSpreadsheet size={18} className="text-brand" />
            {t("reports.attendanceExport")}
          </h2>
        </CardHeader>
        <CardBody className="space-y-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <Label htmlFor="date_from">{t("reports.from")}</Label>
              <Input id="date_from" type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} />
            </div>
            <div>
              <Label htmlFor="date_to">{t("reports.to")}</Label>
              <Input id="date_to" type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} />
            </div>
            <div>
              <Label htmlFor="department">{t("reports.department")}</Label>
              <Select id="department" value={departmentId} onChange={(event) => setDepartmentId(event.target.value)}>
                <option value="">{t("common.allDepartments")}</option>
                {departmentsQuery.data?.map((department) => (
                  <option key={department.id} value={department.id}>
                    {department.name}
                  </option>
                ))}
              </Select>
            </div>
            <div>
              <Label htmlFor="status">{t("reports.status")}</Label>
              <Select id="status" value={status} onChange={(event) => setStatus(event.target.value as AttendanceStatus | "")}>
                <option value="">{t("reports.onTimeAndLate")}</option>
                <option value="on_time">{t("reports.onTimeOnly")}</option>
                <option value="late">{t("reports.lateOnly")}</option>
              </Select>
            </div>
          </div>

          <div className="flex gap-3 border-t border-line pt-4">
            <Button onClick={() => void onDownload("csv")} disabled={isDownloading !== null}>
              <Download size={16} className="mr-1.5" />
              {isDownloading === "csv" ? t("reports.preparing") : t("reports.downloadCsv")}
            </Button>
            <Button variant="secondary" onClick={() => void onDownload("xlsx")} disabled={isDownloading !== null}>
              <Download size={16} className="mr-1.5" />
              {isDownloading === "xlsx" ? t("reports.preparing") : t("reports.downloadExcel")}
            </Button>
          </div>
        </CardBody>
      </Card>
    </div>
  );
}
