import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/Button";
import { FieldError, Input, Label, Select } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { getErrorMessage } from "@/services/api";
import { employeesApi, type EmployeeCreateInput } from "@/services/employeesApi";
import type { DepartmentResponse, EmployeeResponse } from "@/types/models";

export function EmployeeFormModal({
  employee,
  departments,
  onClose,
}: {
  employee: EmployeeResponse | null;
  departments: DepartmentResponse[];
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const isEditing = employee !== null;

  const [form, setForm] = useState<EmployeeCreateInput>({
    employee_id: employee?.employee_id ?? "",
    first_name: employee?.first_name ?? "",
    last_name: employee?.last_name ?? "",
    department_id: employee?.department.id ?? departments[0]?.id ?? 0,
    position: employee?.position ?? "",
    phone: employee?.phone ?? "",
    email: employee?.email ?? "",
    work_start_time: employee?.work_start_time?.slice(0, 5) ?? "",
    work_end_time: employee?.work_end_time?.slice(0, 5) ?? "",
  });
  // Kept separate from `form` (and as a string) since it's a nullable number:
  // "" means "no override, use the company default", matching how the other
  // optional text fields represent "not set" - converted at payload time below.
  const [leaveDurationOverride, setLeaveDurationOverride] = useState(employee?.annual_leave_duration_days?.toString() ?? "");
  const [error, setError] = useState<string | null>(null);
  const [photoFile, setPhotoFile] = useState<File | null>(null);
  const [accountEmail, setAccountEmail] = useState("");
  const [accountPassword, setAccountPassword] = useState("");

  const saveMutation = useMutation({
    mutationFn: async () => {
      const payload = {
        ...form,
        position: form.position || null,
        phone: form.phone || null,
        email: form.email || null,
        work_start_time: form.work_start_time || null,
        work_end_time: form.work_end_time || null,
        annual_leave_duration_days: leaveDurationOverride ? Number(leaveDurationOverride) : null,
      };
      const saved = isEditing ? await employeesApi.update(employee.id, payload) : await employeesApi.create(payload);
      if (photoFile) {
        await employeesApi.uploadPhoto(saved.id, photoFile);
      }
      return saved;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["employees"] });
      void queryClient.invalidateQueries({ queryKey: ["departments"] });
      onClose();
    },
    onError: (err: unknown) => setError(getErrorMessage(err)),
  });

  const deactivateMutation = useMutation({
    mutationFn: () => employeesApi.deactivate(employee?.id ?? 0),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["employees"] });
      onClose();
    },
  });

  const createAccountMutation = useMutation({
    mutationFn: () => employeesApi.createAccount(employee?.id ?? 0, accountEmail, accountPassword, "employee"),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["employees"] });
      setAccountEmail("");
      setAccountPassword("");
    },
    onError: (err: unknown) => setError(getErrorMessage(err)),
  });

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    saveMutation.mutate();
  }

  return (
    <Modal title={isEditing ? t("employees.editEmployee") : t("employees.addEmployee")} onClose={onClose} width="max-w-lg">
      <form onSubmit={onSubmit} className="space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label htmlFor="employee_id">{t("employees.form.employeeId")}</Label>
            <Input
              id="employee_id"
              required
              value={form.employee_id}
              onChange={(event) => setForm((f) => ({ ...f, employee_id: event.target.value }))}
              placeholder="EMP023"
            />
          </div>
          <div>
            <Label htmlFor="department">{t("employees.form.department")}</Label>
            <Select
              id="department"
              required
              value={form.department_id}
              onChange={(event) => setForm((f) => ({ ...f, department_id: Number(event.target.value) }))}
            >
              {departments.map((department) => (
                <option key={department.id} value={department.id}>
                  {department.name}
                </option>
              ))}
            </Select>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label htmlFor="first_name">{t("employees.form.firstName")}</Label>
            <Input
              id="first_name"
              required
              value={form.first_name}
              onChange={(event) => setForm((f) => ({ ...f, first_name: event.target.value }))}
            />
          </div>
          <div>
            <Label htmlFor="last_name">{t("employees.form.lastName")}</Label>
            <Input
              id="last_name"
              required
              value={form.last_name}
              onChange={(event) => setForm((f) => ({ ...f, last_name: event.target.value }))}
            />
          </div>
        </div>

        <div>
          <Label htmlFor="position">{t("employees.form.position")}</Label>
          <Input id="position" value={form.position ?? ""} onChange={(event) => setForm((f) => ({ ...f, position: event.target.value }))} />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label htmlFor="phone">{t("employees.form.phone")}</Label>
            <Input
              id="phone"
              value={form.phone ?? ""}
              onChange={(event) => setForm((f) => ({ ...f, phone: event.target.value }))}
              placeholder="+998 90 123 45 67"
            />
          </div>
          <div>
            <Label htmlFor="email">{t("employees.form.email")}</Label>
            <Input
              id="email"
              type="email"
              value={form.email ?? ""}
              onChange={(event) => setForm((f) => ({ ...f, email: event.target.value }))}
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label htmlFor="work_start">{t("employees.form.workStart")}</Label>
            <Input
              id="work_start"
              type="time"
              value={form.work_start_time ?? ""}
              onChange={(event) => setForm((f) => ({ ...f, work_start_time: event.target.value }))}
            />
          </div>
          <div>
            <Label htmlFor="work_end">{t("employees.form.workEnd")}</Label>
            <Input
              id="work_end"
              type="time"
              value={form.work_end_time ?? ""}
              onChange={(event) => setForm((f) => ({ ...f, work_end_time: event.target.value }))}
            />
          </div>
        </div>

        <div>
          <Label htmlFor="leave_duration_override">{t("employees.form.leaveDurationOverride")}</Label>
          <Input
            id="leave_duration_override"
            type="number"
            min={1}
            max={365}
            value={leaveDurationOverride}
            onChange={(event) => setLeaveDurationOverride(event.target.value)}
          />
          <p className="mt-1 text-xs text-ink-muted">{t("employees.form.leaveDurationOverrideHint")}</p>
        </div>

        <div>
          <Label htmlFor="photo">{t("employees.form.photo")}</Label>
          <input
            id="photo"
            type="file"
            accept="image/png,image/jpeg,image/webp"
            onChange={(event) => setPhotoFile(event.target.files?.[0] ?? null)}
            className="block text-sm text-ink-muted"
          />
        </div>

        <FieldError>{error}</FieldError>

        <div className="flex items-center justify-between gap-2 border-t border-line pt-4">
          {isEditing && employee.status === "active" ? (
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

      {isEditing && !employee.account && (
        <div className="mt-6 border-t border-line pt-4">
          <p className="mb-2 text-sm font-medium text-ink">{t("employees.form.createLoginAccount")}</p>
          <div className="flex flex-wrap gap-2">
            <Input
              type="email"
              placeholder={t("employees.form.loginEmail") ?? undefined}
              value={accountEmail}
              onChange={(event) => setAccountEmail(event.target.value)}
              className="min-w-40 flex-1"
            />
            <Input
              type="password"
              placeholder={t("employees.form.passwordHint") ?? undefined}
              value={accountPassword}
              onChange={(event) => setAccountPassword(event.target.value)}
              className="min-w-40 flex-1"
            />
            <Button
              type="button"
              size="sm"
              onClick={() => createAccountMutation.mutate()}
              disabled={!accountEmail || accountPassword.length < 8 || createAccountMutation.isPending}
            >
              {t("employees.form.createButton")}
            </Button>
          </div>
        </div>
      )}
    </Modal>
  );
}
