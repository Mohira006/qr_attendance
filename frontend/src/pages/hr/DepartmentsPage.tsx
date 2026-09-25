import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/Button";
import { Card, CardBody } from "@/components/ui/Card";
import { FieldError, Input, Label } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";
import { getErrorMessage } from "@/services/api";
import { departmentsApi, type DepartmentInput } from "@/services/employeesApi";
import type { DepartmentResponse } from "@/types/models";
import { formatWorkTime } from "@/utils/format";

export function DepartmentsPage() {
  const { t } = useTranslation();
  const departmentsQuery = useQuery({ queryKey: ["departments", "all"], queryFn: () => departmentsApi.list() });
  const [editing, setEditing] = useState<DepartmentResponse | "new" | null>(null);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-semibold text-ink">{t("departments.title")}</h1>
          <p className="text-sm text-ink-muted">
            {departmentsQuery.data ? t("departments.countLabel", { count: departmentsQuery.data.length }) : "-"}
          </p>
        </div>
        <Button onClick={() => setEditing("new")}>
          <Plus size={16} className="mr-1.5" /> {t("departments.addDepartment")}
        </Button>
      </div>

      {departmentsQuery.isLoading && <LoadingState label={t("common.loading")} />}
      {departmentsQuery.isError && <ErrorState message={t("departments.couldNotLoad")} />}

      {departmentsQuery.data &&
        (departmentsQuery.data.length === 0 ? (
          <EmptyState title={t("departments.noDepartments")} description={t("departments.noDepartmentsDescription")} />
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {departmentsQuery.data.map((department) => (
              <Card key={department.id}>
                <CardBody>
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="font-display text-lg font-semibold text-ink">{department.name}</p>
                      <p className="text-sm text-ink-muted">{t("departments.employeeCount", { count: department.employee_count })}</p>
                    </div>
                    <span
                      className={`text-xs font-medium ${department.status === "active" ? "text-status-success" : "text-status-neutral"}`}
                    >
                      {department.status === "active" ? t("common.active") : t("common.inactive")}
                    </span>
                  </div>
                  {department.description && <p className="mt-2 text-sm text-ink-muted">{department.description}</p>}
                  <p className="mt-2 font-mono text-xs text-ink-faint">
                    {department.work_start_time && department.work_end_time
                      ? t("departments.customHours", {
                          start: formatWorkTime(department.work_start_time),
                          end: formatWorkTime(department.work_end_time),
                        })
                      : t("departments.usesDefaultHours")}
                  </p>
                  <button
                    type="button"
                    onClick={() => setEditing(department)}
                    className="mt-3 text-sm font-medium text-brand hover:text-brand-hover"
                  >
                    {t("common.edit")}
                  </button>
                </CardBody>
              </Card>
            ))}
          </div>
        ))}

      {editing && <DepartmentFormModal department={editing === "new" ? null : editing} onClose={() => setEditing(null)} />}
    </div>
  );
}

function DepartmentFormModal({ department, onClose }: { department: DepartmentResponse | null; onClose: () => void }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const isEditing = department !== null;
  const [form, setForm] = useState<DepartmentInput>({
    name: department?.name ?? "",
    description: department?.description ?? "",
    work_start_time: department?.work_start_time?.slice(0, 5) ?? "",
    work_end_time: department?.work_end_time?.slice(0, 5) ?? "",
  });
  const [error, setError] = useState<string | null>(null);

  const saveMutation = useMutation({
    mutationFn: () => {
      const payload = {
        ...form,
        description: form.description || null,
        work_start_time: form.work_start_time || null,
        work_end_time: form.work_end_time || null,
      };
      return isEditing ? departmentsApi.update(department.id, payload) : departmentsApi.create(payload);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["departments"] });
      onClose();
    },
    onError: (err: unknown) => setError(getErrorMessage(err)),
  });

  const deactivateMutation = useMutation({
    mutationFn: () => departmentsApi.deactivate(department?.id ?? 0),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["departments"] });
      onClose();
    },
  });

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    saveMutation.mutate();
  }

  return (
    <Modal title={isEditing ? t("departments.editDepartment") : t("departments.addDepartment")} onClose={onClose}>
      <form onSubmit={onSubmit} className="space-y-4">
        <div>
          <Label htmlFor="name">{t("departments.form.name")}</Label>
          <Input id="name" required value={form.name} onChange={(event) => setForm((f) => ({ ...f, name: event.target.value }))} />
        </div>
        <div>
          <Label htmlFor="description">{t("departments.form.description")}</Label>
          <Input
            id="description"
            value={form.description ?? ""}
            onChange={(event) => setForm((f) => ({ ...f, description: event.target.value }))}
          />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label htmlFor="start">{t("departments.form.workStartOverride")}</Label>
            <Input
              id="start"
              type="time"
              value={form.work_start_time ?? ""}
              onChange={(event) => setForm((f) => ({ ...f, work_start_time: event.target.value }))}
            />
          </div>
          <div>
            <Label htmlFor="end">{t("departments.form.workEndOverride")}</Label>
            <Input
              id="end"
              type="time"
              value={form.work_end_time ?? ""}
              onChange={(event) => setForm((f) => ({ ...f, work_end_time: event.target.value }))}
            />
          </div>
        </div>
        <p className="text-xs text-ink-muted">{t("departments.form.hint")}</p>

        <FieldError>{error}</FieldError>

        <div className="flex items-center justify-between gap-2 border-t border-line pt-4">
          {isEditing && department.status === "active" ? (
            <Button
              type="button"
              variant="danger"
              size="sm"
              onClick={() => deactivateMutation.mutate()}
              disabled={deactivateMutation.isPending}
            >
              {t("common.deactivate")}
            </Button>
          ) : (
            <span />
          )}
          <div className="flex gap-2">
            <Button type="button" variant="secondary" onClick={onClose}>
              {t("common.cancel")}
            </Button>
            <Button type="submit" disabled={saveMutation.isPending}>
              {saveMutation.isPending ? t("common.saving") : t("common.save")}
            </Button>
          </div>
        </div>
      </form>
    </Modal>
  );
}
