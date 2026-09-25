import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { useAuth } from "@/contexts/AuthContext";
import { LoadingState } from "@/components/ui/States";
import type { UserRole } from "@/types/enums";

export function homeForRole(role: UserRole | undefined): string {
  return role === "hr" ? "/hr/dashboard" : "/me/dashboard";
}

export function RequireAuth({ children }: { children: ReactNode }) {
  const { user, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-canvas">
        <LoadingState label="Checking your session..." />
      </div>
    );
  }
  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  return <>{children}</>;
}

export function RequireRole({ role, children }: { role: UserRole; children: ReactNode }) {
  const { user } = useAuth();
  if (user && user.role !== role) {
    return <Navigate to={homeForRole(user.role)} replace />;
  }
  return <>{children}</>;
}
