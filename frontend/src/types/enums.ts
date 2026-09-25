export type UserRole = "hr" | "employee";
export type Language = "uz" | "ru" | "en";
export type EmploymentStatus = "active" | "inactive";
export type DepartmentStatus = "active" | "inactive";
export type AttendanceStatus = "on_time" | "late";
export type CheckoutStatus = "pending" | "completed" | "missing";
export type LetterStatus = "pending" | "submitted" | "reviewed";
export type LeaveType = "vacation" | "sick" | "unpaid" | "other";
export type LeaveStatus = "pending" | "approved" | "rejected";
export type LeaveRequestType = "normal" | "force_majeure";
export type LeaveRequestStatus = "pending" | "approved" | "rejected" | "cancelled" | "completed";
export type LeaveCycleStatus = "available" | "requested" | "consumed";
export type ScanOutcome = "check_in" | "check_out" | "duplicate" | "rejected";
export type NotificationType =
  | "check_in"
  | "check_out"
  | "late"
  | "explanation_letter"
  | "leave_request_submitted"
  | "leave_request_approved"
  | "leave_request_rejected"
  | "leave_eligibility_reminder"
  | "system";
