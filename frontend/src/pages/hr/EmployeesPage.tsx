import { useQuery } from "@tanstack/react-query";
import { Plus, Search } from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";

import { Avatar } from "@/components/attendance/Avatar";
import { EmployeeFormModal } from "@/components/employees/EmployeeFormModal";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input, Select } from "@/components/ui/Input";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";
import { departmentsApi, employeesApi } from "@/services/employeesApi";
import type { EmploymentStatus } from "@/types/enums";
import type { EmployeeResponse } from "@/types/models";

export function EmployeesPage() {
  const { t } = useTranslation();
  const [searchParams, setSearchParams] = useSearchParams();
  const [search, setSearch] = useState(searchParams.get("search") ?? "");
  const [departmentId, setDepartmentId] = useState("");
  const [status, setStatus] = useState<EmploymentStatus | "">("active");
  const [page, setPage] = useState(1);
  const [editing, setEditing] = useState<EmployeeResponse | "new" | null>(null);

  useEffect(() => {
    const fromUrl = searchParams.get("search");
    if (fromUrl && fromUrl !== search) {
      setSearch(fromUrl);
    }
    // Only react to external URL changes (e.g. the topbar search or a table row
    // link); typing in this page's own search box updates the URL, not the reverse.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  const departmentsQuery = useQuery({ queryKey: ["departments"], queryFn: () => departmentsApi.list("active") });
  const employeesQuery = useQuery({
    queryKey: ["employees", search, departmentId, status, page],
    queryFn: () =>
      employeesApi.list({
        search: search || undefined,
        department_id: departmentId ? Number(departmentId) : undefined,
        status: status || undefined,
        page,
        page_size: 20,
      }),
  });

  function onSearchChange(value: string) {
    setSearch(value);
    setPage(1);
    setSearchParams(value ? { search: value } : {});
  }

  const data = employeesQuery.data;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-semibold text-ink">{t("employees.title")}</h1>
          <p className="text-sm text-ink-muted">{data ? t("employees.countLabel", { count: data.total }) : "-"}</p>
        </div>
        <Button onClick={() => setEditing("new")}>
          <Plus size={16} className="mr-1.5" /> {t("employees.addEmployee")}
        </Button>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <div className="relative w-64">
          <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-faint" />
          <Input
            value={search}
            onChange={(event) => onSearchChange(event.target.value)}
            placeholder={t("employees.searchPlaceholder")}
            className="pl-9"
          />
        </div>
        <Select
          value={departmentId}
          onChange={(event) => {
            setDepartmentId(event.target.value);
            setPage(1);
          }}
          className="w-48"
        >
          <option value="">{t("common.allDepartments")}</option>
          {departmentsQuery.data?.map((department) => (
            <option key={department.id} value={department.id}>
              {department.name}
            </option>
          ))}
        </Select>
        <Select
          value={status}
          onChange={(event) => {
            setStatus(event.target.value as EmploymentStatus | "");
            setPage(1);
          }}
          className="w-40"
        >
          <option value="active">{t("common.active")}</option>
          <option value="inactive">{t("common.inactive")}</option>
          <option value="">{t("common.allStatuses")}</option>
        </Select>
      </div>

      {employeesQuery.isLoading && <LoadingState label={t("common.loading")} />}
      {employeesQuery.isError && <ErrorState message={t("employees.couldNotLoad")} />}

      {data &&
        (data.items.length === 0 ? (
          <EmptyState title={t("employees.noEmployeesFound")} description={t("employees.noEmployeesFoundDescription")} />
        ) : (
          <Card>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-line text-xs uppercase tracking-wide text-ink-muted">
                    <th className="px-4 py-3 font-medium">{t("employees.columns.employee")}</th>
                    <th className="px-4 py-3 font-medium">{t("employees.columns.employeeId")}</th>
                    <th className="px-4 py-3 font-medium">{t("employees.columns.department")}</th>
                    <th className="px-4 py-3 font-medium">{t("employees.columns.position")}</th>
                    <th className="px-4 py-3 font-medium">{t("employees.columns.status")}</th>
                    <th className="px-4 py-3 font-medium">{t("employees.columns.account")}</th>
                    <th className="px-4 py-3 font-medium" />
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((employee) => (
                    <tr key={employee.id} className="border-b border-line last:border-0 hover:bg-canvas">
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <Avatar employee={employee} />
                          <span className="font-medium text-ink">{employee.full_name}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 font-mono text-ink-muted">{employee.employee_id}</td>
                      <td className="px-4 py-3 text-ink-muted">{employee.department.name}</td>
                      <td className="px-4 py-3 text-ink-muted">{employee.position ?? "-"}</td>
                      <td className="px-4 py-3">
                        <span className={employee.status === "active" ? "text-status-success" : "text-status-neutral"}>
                          {employee.status === "active" ? t("common.active") : t("common.inactive")}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-ink-muted">{employee.account ? employee.account.email : t("employees.columns.noLogin")}</td>
                      <td className="px-4 py-3 text-right">
                        <button
                          type="button"
                          onClick={() => setEditing(employee)}
                          className="text-sm font-medium text-brand hover:text-brand-hover"
                        >
                          {t("common.edit")}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
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

      {editing && (
        <EmployeeFormModal
          employee={editing === "new" ? null : editing}
          departments={departmentsQuery.data ?? []}
          onClose={() => setEditing(null)}
        />
      )}
    </div>
  );
}
