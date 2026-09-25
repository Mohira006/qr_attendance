import { AlertCircle, Inbox, Loader2 } from "lucide-react";
import type { ReactNode } from "react";

export function Spinner({ className = "" }: { className?: string }) {
  return <Loader2 className={`animate-spin text-ink-faint ${className}`} size={20} aria-label="Loading" />;
}

export function LoadingState({ label = "Loading..." }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-ink-muted">
      <Spinner className="h-6 w-6" />
      <p className="text-sm">{label}</p>
    </div>
  );
}

export function EmptyState({ title, description, icon }: { title: string; description?: string; icon?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-16 text-center">
      <div className="mb-1 text-ink-faint">{icon ?? <Inbox size={28} />}</div>
      <p className="font-medium text-ink">{title}</p>
      {description && <p className="max-w-sm text-sm text-ink-muted">{description}</p>}
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-16 text-center">
      <AlertCircle size={28} className="text-status-danger" />
      <p className="font-medium text-ink">Couldn't load this</p>
      <p className="max-w-sm text-sm text-ink-muted">{message}</p>
    </div>
  );
}
