import type {
  DepartmentResponse,
  EmployeeAccountResponse,
  EmployeeResponse,
  Page,
} from "@/types/models";
import type { EmploymentStatus, UserRole } from "@/types/enums";

import { api } from "./api";

export interface EmployeeListParams {
  search?: string;
  department_id?: number;
  status?: EmploymentStatus;
  page?: number;
  page_size?: number;
}

export interface EmployeeCreateInput {
  employee_id: string;
  first_name: string;
  last_name: string;
  department_id: number;
  position?: string | null;
  phone?: string | null;
  email?: string | null;
  work_start_time?: string | null;
  work_end_time?: string | null;
  annual_leave_duration_days?: number | null;
  status?: EmploymentStatus;
}

export type EmployeeUpdateInput = Partial<EmployeeCreateInput>;

export const employeesApi = {
  list: (params: EmployeeListParams) => api.get<Page<EmployeeResponse>>("/employees", { params }).then((r) => r.data),

  me: () => api.get<EmployeeResponse>("/employees/me").then((r) => r.data),

  get: (id: number) => api.get<EmployeeResponse>(`/employees/${id}`).then((r) => r.data),

  create: (data: EmployeeCreateInput) => api.post<EmployeeResponse>("/employees", data).then((r) => r.data),

  update: (id: number, data: EmployeeUpdateInput) =>
    api.put<EmployeeResponse>(`/employees/${id}`, data).then((r) => r.data),

  deactivate: (id: number) => api.delete(`/employees/${id}`),

  uploadPhoto: (id: number, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return api.post<EmployeeResponse>(`/employees/${id}/photo`, form).then((r) => r.data);
  },

  createAccount: (id: number, email: string, password: string, role: UserRole) =>
    api.post<EmployeeAccountResponse>(`/employees/${id}/account`, { email, password, role }).then((r) => r.data),

  updateAccount: (id: number, data: { password?: string; role?: UserRole; is_active?: boolean }) =>
    api.put<EmployeeAccountResponse>(`/employees/${id}/account`, data).then((r) => r.data),
};

export interface DepartmentInput {
  name: string;
  description?: string | null;
  work_start_time?: string | null;
  work_end_time?: string | null;
  status?: "active" | "inactive";
}

export const departmentsApi = {
  list: (status?: "active" | "inactive") =>
    api.get<DepartmentResponse[]>("/departments", { params: { status } }).then((r) => r.data),

  get: (id: number) => api.get<DepartmentResponse>(`/departments/${id}`).then((r) => r.data),

  create: (data: DepartmentInput) => api.post<DepartmentResponse>("/departments", data).then((r) => r.data),

  update: (id: number, data: Partial<DepartmentInput>) =>
    api.put<DepartmentResponse>(`/departments/${id}`, data).then((r) => r.data),

  deactivate: (id: number) => api.delete(`/departments/${id}`),
};
