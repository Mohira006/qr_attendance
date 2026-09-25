import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useLocation } from "react-router-dom";

import { Button } from "@/components/ui/Button";
import { Input, Label } from "@/components/ui/Input";
import { LanguageSwitcher } from "@/components/layout/LanguageSwitcher";
import { useAuth } from "@/contexts/AuthContext";
import { homeForRole } from "@/components/RouteGuards";

export function LoginPage() {
  const { t } = useTranslation();
  const { login, user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (user) {
    const from = (location.state as { from?: { pathname: string } } | null)?.from?.pathname;
    navigate(from ?? homeForRole(user.role), { replace: true });
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await login(email, password);
    } catch {
      // Same generic message regardless of the specific reason (wrong password
      // vs. a deactivated account) - deliberately not leaking which one to
      // whoever is attempting the login.
      setError(t("auth.invalidCredentials"));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-ink px-4">
      <div className="w-full max-w-sm">
        <div className="mb-4 flex justify-center">
          <LanguageSwitcher variant="dark" />
        </div>
        <div className="mb-8 flex flex-col items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand font-display text-lg font-bold text-white">
            QR
          </div>
          <div className="text-center">
            <h1 className="font-display text-xl font-semibold text-white">{t("auth.appName")}</h1>
            <p className="mt-1 text-sm text-white/50">{t("auth.signInSubtitle")}</p>
          </div>
        </div>

        <form onSubmit={onSubmit} className="rounded-2xl bg-surface p-6 shadow-card">
          <div className="mb-4">
            <Label htmlFor="email">{t("auth.email")}</Label>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@company.com"
            />
          </div>
          <div className="mb-5">
            <Label htmlFor="password">{t("auth.password")}</Label>
            <Input
              id="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="••••••••"
            />
          </div>

          {error && (
            <p role="alert" className="mb-4 rounded-lg bg-status-danger-bg px-3 py-2 text-sm text-status-danger">
              {error}
            </p>
          )}

          <Button type="submit" className="w-full" disabled={isSubmitting}>
            {isSubmitting ? t("auth.signingIn") : t("auth.signIn")}
          </Button>
        </form>
      </div>
    </div>
  );
}
