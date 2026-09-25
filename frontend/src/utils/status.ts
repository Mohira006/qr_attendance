import type { AttendanceStatus, CheckoutStatus, LeaveRequestStatus, LetterStatus } from "@/types/enums";

export interface StatusTokens {
  /** i18next key, e.g. "common.status.onTime" - translated where it's actually
   * rendered (StatusBadge), not here, since this file isn't a React component
   * and can't reactively re-render when the language changes. */
  labelKey: string;
  text: string;
  bg: string;
  border: string;
  dot: string;
}

export function attendanceStatusTokens(status: AttendanceStatus): StatusTokens {
  if (status === "on_time") {
    return {
      labelKey: "common.status.onTime",
      text: "text-status-success",
      bg: "bg-status-success-bg",
      border: "border-status-success",
      dot: "bg-status-success",
    };
  }
  return {
    labelKey: "common.status.late",
    text: "text-status-danger",
    bg: "bg-status-danger-bg",
    border: "border-status-danger",
    dot: "bg-status-danger",
  };
}

export function absentTokens(): StatusTokens {
  return {
    labelKey: "common.status.absent",
    text: "text-status-neutral",
    bg: "bg-status-neutral-bg",
    border: "border-status-neutral",
    dot: "bg-status-neutral",
  };
}

export function onLeaveTokens(): StatusTokens {
  return {
    labelKey: "common.status.onLeave",
    text: "text-status-warning",
    bg: "bg-status-warning-bg",
    border: "border-status-warning",
    dot: "bg-status-warning",
  };
}

export function checkoutStatusLabelKey(status: CheckoutStatus): string {
  switch (status) {
    case "pending":
      return "common.status.currentlyWorking";
    case "completed":
      return "common.status.checkedOut";
    case "missing":
      return "common.status.missingCheckout";
  }
}

export function letterStatusTokens(status: LetterStatus): StatusTokens {
  switch (status) {
    case "pending":
      return {
        labelKey: "common.status.pending",
        text: "text-status-warning",
        bg: "bg-status-warning-bg",
        border: "border-status-warning",
        dot: "bg-status-warning",
      };
    case "submitted":
      return { labelKey: "common.status.submitted", text: "text-brand", bg: "bg-brand-light", border: "border-brand", dot: "bg-brand" };
    case "reviewed":
      return {
        labelKey: "common.status.reviewed",
        text: "text-status-success",
        bg: "bg-status-success-bg",
        border: "border-status-success",
        dot: "bg-status-success",
      };
  }
}

export function leaveRequestStatusTokens(status: LeaveRequestStatus): StatusTokens {
  switch (status) {
    case "pending":
      return {
        labelKey: "common.status.pending",
        text: "text-status-warning",
        bg: "bg-status-warning-bg",
        border: "border-status-warning",
        dot: "bg-status-warning",
      };
    case "approved":
      return {
        labelKey: "common.status.approved",
        text: "text-status-success",
        bg: "bg-status-success-bg",
        border: "border-status-success",
        dot: "bg-status-success",
      };
    case "rejected":
      return {
        labelKey: "common.status.rejected",
        text: "text-status-danger",
        bg: "bg-status-danger-bg",
        border: "border-status-danger",
        dot: "bg-status-danger",
      };
    case "cancelled":
      return {
        labelKey: "common.status.cancelled",
        text: "text-status-neutral",
        bg: "bg-status-neutral-bg",
        border: "border-status-neutral",
        dot: "bg-status-neutral",
      };
    case "completed":
      return { labelKey: "common.status.completed", text: "text-brand", bg: "bg-brand-light", border: "border-brand", dot: "bg-brand" };
  }
}
