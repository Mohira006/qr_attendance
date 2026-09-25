import type { ExplanationLetterResponse, Page } from "@/types/models";
import type { LetterStatus } from "@/types/enums";

import { api } from "./api";

export const explanationLettersApi = {
  request: (attendanceId: number) =>
    api.post<ExplanationLetterResponse>("/explanation-letters", { attendance_id: attendanceId }).then((r) => r.data),

  list: (params?: {
    status?: LetterStatus;
    employee_id?: number;
    department_id?: number;
    date_from?: string;
    date_to?: string;
    page?: number;
    page_size?: number;
  }) => api.get<Page<ExplanationLetterResponse>>("/explanation-letters", { params }).then((r) => r.data),

  get: (id: number) => api.get<ExplanationLetterResponse>(`/explanation-letters/${id}`).then((r) => r.data),

  submitExplanation: (id: number, text: string) =>
    api
      .put<ExplanationLetterResponse>(`/explanation-letters/${id}/explanation`, { employee_explanation: text })
      .then((r) => r.data),

  review: (id: number, comment: string) =>
    api.put<ExplanationLetterResponse>(`/explanation-letters/${id}/review`, { hr_comment: comment }).then((r) => r.data),

  downloadPdf: async (id: number, employeeCode: string, date: string) => {
    const response = await api.get(`/explanation-letters/${id}/pdf`, { responseType: "blob" });
    const blobUrl = URL.createObjectURL(response.data as Blob);
    const link = document.createElement("a");
    link.href = blobUrl;
    link.download = `explanation-letter-${employeeCode}-${date}.pdf`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(blobUrl);
  },

  uploadAttachment: (id: number, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return api.post<ExplanationLetterResponse>(`/explanation-letters/${id}/attachment`, form).then((r) => r.data);
  },

  downloadAttachment: async (id: number, filename: string) => {
    const response = await api.get(`/explanation-letters/${id}/attachment`, { responseType: "blob" });
    const blobUrl = URL.createObjectURL(response.data as Blob);
    const link = document.createElement("a");
    link.href = blobUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(blobUrl);
  },
};
