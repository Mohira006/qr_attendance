import type { LoginResponse, Message, UserResponse } from "@/types/models";
import type { Language } from "@/types/enums";

import { api } from "./api";

export const authApi = {
  login: (email: string, password: string) =>
    api.post<LoginResponse>("/auth/login", { email, password }).then((r) => r.data),

  me: () => api.get<UserResponse>("/auth/me").then((r) => r.data),

  logout: (refreshToken: string | null) =>
    api.post<Message>("/auth/logout", { refresh_token: refreshToken }).then((r) => r.data),

  changePassword: (currentPassword: string, newPassword: string) =>
    api
      .post<Message>("/auth/change-password", { current_password: currentPassword, new_password: newPassword })
      .then((r) => r.data),

  updateLanguage: (language: Language) =>
    api.put<UserResponse>("/auth/me/language", { preferred_language: language }).then((r) => r.data),
};
