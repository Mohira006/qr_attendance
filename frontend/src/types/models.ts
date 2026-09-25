import type {
  AttendanceStatus,
  CheckoutStatus,
  DepartmentStatus,
  EmploymentStatus,
  Language,
  LeaveCycleStatus,
  LeaveRequestStatus,
  LeaveRequestType,
  LetterStatus,
  NotificationType,
  ScanOutcome,
  UserRole,
} from "./enums";

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface Message {
  message: string;
}

export interface DepartmentBrief {
  id: number;
  name: string;
}

export interface DepartmentResponse {
  id: number;
  name: string;
  description: string | null;
  status: DepartmentStatus;
  work_start_time: string | null; // "HH:MM:SS"
  work_end_time: string | null;
  employee_count: number;
  created_at: string;
  updated_at: string;
}

export interface EmployeeAccountResponse {
  id: number;
  email: string;
  role: UserRole;
  is_active: boolean;
  last_login_at: string | null;
}

export interface EmployeeBrief {
  id: number;
  employee_id: string;
  first_name: string;
  last_name: string;
  full_name: string;
  department: DepartmentBrief;
  position: string | null;
  profile_photo_url: string | null;
}

export interface EmployeeResponse extends EmployeeBrief {
  phone: string | null;
  email: string | null;
  work_start_time: string | null;
  work_end_time: string | null;
  employment_start_date: string;
  annual_leave_duration_days: number | null;
  status: EmploymentStatus;
  account: EmployeeAccountResponse | null;
  created_at: string;
  updated_at: string;
}

export interface UserResponse {
  id: number;
  email: string;
  role: UserRole;
  is_active: boolean;
  last_login_at: string | null;
  preferred_language: Language;
  employee: EmployeeBrief | null;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: UserResponse;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface AttendanceResponse {
  id: number;
  employee: EmployeeBrief;
  date: string; // "YYYY-MM-DD"
  check_in: string; // ISO datetime, UTC
  check_out: string | null;
  status: AttendanceStatus;
  checkout_status: CheckoutStatus;
  late_minutes: number;
  total_working_minutes: number | null;
  expected_check_in: string; // "HH:MM:SS"
  expected_check_out: string;
  explanation_letter_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface DayOverviewResponse {
  date: string;
  total_employees: number;
  present_count: number;
  currently_working_count: number;
  on_time: AttendanceResponse[];
  late: AttendanceResponse[];
  absent: EmployeeBrief[];
  on_leave: EmployeeBrief[];
}

export interface EmployeeAttendanceSummaryResponse {
  employee: EmployeeBrief;
  period_start: string;
  period_end: string;
  on_time_count: number;
  late_count: number;
  absent_count: number;
  on_leave_count: number;
  total_working_minutes: number;
  attendance_percentage: number;
}

export interface ScanResponse {
  outcome: ScanOutcome;
  message: string;
  attendance: AttendanceResponse | null;
}

export interface NotificationResponse {
  id: number;
  type: NotificationType;
  title: string;
  message: string;
  employee: EmployeeBrief | null;
  attendance_id: number | null;
  explanation_letter_id: number | null;
  is_read: boolean;
  read_at: string | null;
  created_at: string;
}

export interface ExplanationLetterResponse {
  id: number;
  employee: EmployeeBrief;
  attendance_id: number;
  date: string;
  late_minutes: number;
  employee_explanation: string | null;
  hr_comment: string | null;
  status: LetterStatus;
  reviewed_by_user_id: number | null;
  attachment_url: string | null;
  created_at: string;
  updated_at: string;
}

export interface SettingsResponse {
  company_name: string;
  timezone: string;
  work_start_time: string;
  work_end_time: string;
  grace_period_minutes: number;
  duplicate_event_window_seconds: number;
  working_days: number[]; // ISO weekday numbers, 1=Monday..7=Sunday
  annual_leave_duration_days: number;
  leave_normal_notice_days: number;
  leave_force_majeure_notice_days: number;
  leave_eligibility_after_months: number;
  leave_next_cycle_after_months: number;
  leave_reminder_30_days_enabled: boolean;
  leave_reminder_14_days_enabled: boolean;
  leave_reminder_7_days_enabled: boolean;
  updated_at: string;
}

export interface LeaveRequestResponse {
  id: number;
  employee: EmployeeBrief;
  cycle_number: number;
  work_period_start: string;
  work_period_end: string;
  eligibility_date: string;
  requested_start_date: string;
  requested_end_date: string;
  duration_days: number;
  request_type: LeaveRequestType;
  status: LeaveRequestStatus;
  employee_comment: string | null;
  hr_comment: string | null;
  submitted_at: string;
  approved_at: string | null;
  rejected_at: string | null;
  cancelled_at: string | null;
  reviewed_by_user_id: number | null;
  is_hr_override: boolean;
  override_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface LeaveEligibilityResponse {
  employee: EmployeeBrief;
  employment_start_date: string;
  annual_leave_duration_days: number;
  cycle_number: number;
  work_period_start: string;
  work_period_end: string;
  eligibility_date: string;
  is_eligible: boolean;
  cycle_status: LeaveCycleStatus;
  current_request: LeaveRequestResponse | null;
  previous_leave: LeaveRequestResponse | null;
  next_eligibility_date: string | null;
}

export interface DashboardStatisticsResponse {
  date: string;
  total_employees: number;
  present_today: number;
  on_time_count: number;
  late_count: number;
  absent_count: number;
  on_leave_count: number;
  currently_working_count: number;
  attendance_percentage: number;
  average_arrival_time: string | null; // "HH:MM"
}

export interface TrendDay {
  date: string;
  on_time_count: number;
  late_count: number;
  present_count: number;
  attendance_percentage: number;
  is_working_day: boolean;
}

export interface DepartmentBreakdown {
  department: DepartmentBrief;
  total_employees: number;
  on_time_count: number;
  late_count: number;
  absent_count: number;
}

export interface AuditLogResponse {
  id: number;
  user_id: number | null;
  action: string;
  entity_type: string | null;
  entity_id: string | null;
  details: Record<string, unknown> | null;
  ip_address: string | null;
  created_at: string;
}
