import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";

import type { TokenPair } from "@/types/models";

import { tokenStorage } from "./tokenStorage";

export const api = axios.create({ baseURL: "/api" });

// Requests to these paths must never trigger a refresh-and-retry: retrying a
// failed login makes no sense, and retrying /auth/refresh itself would loop.
const NO_REFRESH_PATHS = ["/auth/login", "/auth/refresh", "/auth/logout"];

interface RetryableConfig extends InternalAxiosRequestConfig {
  _retried?: boolean;
}

api.interceptors.request.use((config) => {
  const token = tokenStorage.getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

let refreshPromise: Promise<string> | null = null;

async function refreshAccessToken(): Promise<string> {
  const refreshToken = tokenStorage.getRefreshToken();
  if (!refreshToken) {
    throw new Error("No refresh token available");
  }
  // A bare axios call, not `api`, so this request never re-enters the interceptor below.
  const response = await axios.post<TokenPair>("/api/auth/refresh", { refresh_token: refreshToken });
  tokenStorage.setTokens(response.data.access_token, response.data.refresh_token);
  return response.data.access_token;
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const config = error.config as RetryableConfig | undefined;
    const isAuthPath = NO_REFRESH_PATHS.some((path) => config?.url?.includes(path));

    if (error.response?.status === 401 && config && !config._retried && !isAuthPath) {
      config._retried = true;
      try {
        if (!refreshPromise) {
          refreshPromise = refreshAccessToken().finally(() => {
            refreshPromise = null;
          });
        }
        const newAccessToken = await refreshPromise;
        config.headers.Authorization = `Bearer ${newAccessToken}`;
        return api(config);
      } catch {
        tokenStorage.clear();
        if (window.location.pathname !== "/login") {
          window.location.href = "/login";
        }
        return Promise.reject(error);
      }
    }
    return Promise.reject(error);
  },
);

/** The `detail`/`code` shape every backend error response shares (see app/core/exceptions.py). */
export interface ApiErrorBody {
  detail: string | { msg: string }[];
  code?: string;
  details?: unknown;
}

export function getErrorMessage(error: unknown, fallback = "Something went wrong. Please try again."): string {
  if (axios.isAxiosError(error)) {
    const body = error.response?.data as ApiErrorBody | undefined;
    if (typeof body?.detail === "string") return body.detail;
    if (Array.isArray(body?.detail) && body.detail[0]?.msg) return body.detail[0].msg;
  }
  return fallback;
}

/** The stable machine-readable code every backend error carries alongside its
 * (English) detail text - use this to look up a translated message instead of
 * displaying the backend's raw text directly. */
export function getErrorCode(error: unknown): string | undefined {
  if (axios.isAxiosError(error)) {
    return (error.response?.data as ApiErrorBody | undefined)?.code;
  }
  return undefined;
}

export function getErrorDetails(error: unknown): Record<string, unknown> | undefined {
  if (axios.isAxiosError(error)) {
    const details = (error.response?.data as ApiErrorBody | undefined)?.details;
    return details && typeof details === "object" ? (details as Record<string, unknown>) : undefined;
  }
  return undefined;
}
