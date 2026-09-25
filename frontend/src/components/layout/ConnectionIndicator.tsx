import { useLiveUpdates } from "@/contexts/WebSocketContext";
import { cn } from "@/utils/cn";

export function ConnectionIndicator() {
  const { connectionState } = useLiveUpdates();

  const label =
    connectionState === "open" ? "Live" : connectionState === "connecting" ? "Connecting" : "Reconnecting";
  const dotClass =
    connectionState === "open"
      ? "bg-status-success animate-pulse"
      : connectionState === "connecting"
        ? "bg-status-warning"
        : "bg-status-danger";

  return (
    <div className="hidden items-center gap-1.5 text-xs text-ink-muted lg:flex" title={`Real-time connection: ${label}`}>
      <span className={cn("h-1.5 w-1.5 rounded-full", dotClass)} />
      {label}
    </div>
  );
}
