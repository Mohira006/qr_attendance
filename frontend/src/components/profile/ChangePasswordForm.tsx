import { useMutation } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/Button";
import { Input, Label } from "@/components/ui/Input";
import { useAuth } from "@/contexts/AuthContext";
import { getErrorMessage } from "@/services/api";
import { authApi } from "@/services/authApi";

export function ChangePasswordForm() {
  const { t } = useTranslation();
  const { logout } = useAuth();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const mutation = useMutation({
    mutationFn: () => authApi.changePassword(currentPassword, newPassword),
    onSuccess: () => {
      setSuccess(true);
      setCurrentPassword("");
      setNewPassword("");
      // The backend revokes every session on a password change, so keeping the
      // current tab logged in would be misleading - sign out after a moment.
      setTimeout(() => void logout(), 2000);
    },
    onError: (err: unknown) => setError(getErrorMessage(err)),
  });

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSuccess(false);
    mutation.mutate();
  }

  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <div>
        <Label htmlFor="current_password">{t("profile.currentPassword")}</Label>
        <Input
          id="current_password"
          type="password"
          required
          autoComplete="current-password"
          value={currentPassword}
          onChange={(event) => setCurrentPassword(event.target.value)}
        />
      </div>
      <div>
        <Label htmlFor="new_password">{t("profile.newPassword")}</Label>
        <Input
          id="new_password"
          type="password"
          required
          minLength={8}
          autoComplete="new-password"
          value={newPassword}
          onChange={(event) => setNewPassword(event.target.value)}
        />
      </div>
      {error && <p className="text-sm text-status-danger">{error}</p>}
      {success && <p className="text-sm text-status-success">{t("profile.passwordChanged")}</p>}
      <Button type="submit" disabled={mutation.isPending}>
        {mutation.isPending ? t("profile.updating") : t("profile.changePasswordButton")}
      </Button>
    </form>
  );
}
