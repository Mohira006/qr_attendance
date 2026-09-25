from enum import StrEnum


class UserRole(StrEnum):
    HR = "hr"
    EMPLOYEE = "employee"


class EmploymentStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class DepartmentStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class AttendanceStatus(StrEnum):
    """Arrival status. Absent and on-leave are derived at read time, never stored."""

    ON_TIME = "on_time"
    LATE = "late"


class CheckoutStatus(StrEnum):
    PENDING = "pending"  # checked in, still at work
    COMPLETED = "completed"  # checked out
    MISSING = "missing"  # never checked out; flagged by the end-of-day job


class ScanOutcome(StrEnum):
    """How the backend resolved an employee's QR-code scan."""

    CHECK_IN = "check_in"
    CHECK_OUT = "check_out"
    DUPLICATE = "duplicate"
    REJECTED = "rejected"


class LetterStatus(StrEnum):
    PENDING = "pending"  # generated, waiting for the employee's explanation
    SUBMITTED = "submitted"  # employee provided an explanation
    REVIEWED = "reviewed"  # HR commented / closed it


class LeaveType(StrEnum):
    VACATION = "vacation"
    SICK = "sick"
    UNPAID = "unpaid"
    OTHER = "other"


class LeaveStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class LeaveRequestType(StrEnum):
    """Which notice-period rule applies to a leave request."""

    NORMAL = "normal"
    FORCE_MAJEURE = "force_majeure"


class LeaveRequestStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    COMPLETED = "completed"  # approved and the leave period has fully passed


class LeaveCycleStatus(StrEnum):
    AVAILABLE = "available"  # eligible (or not yet), no request submitted against this cycle
    REQUESTED = "requested"  # a request is pending against this cycle
    CONSUMED = "consumed"  # a request against this cycle was approved


class Language(StrEnum):
    UZ = "uz"
    RU = "ru"
    EN = "en"


class NotificationType(StrEnum):
    CHECK_IN = "check_in"
    CHECK_OUT = "check_out"
    LATE = "late"
    EXPLANATION_LETTER = "explanation_letter"
    LEAVE_REQUEST_SUBMITTED = "leave_request_submitted"
    LEAVE_REQUEST_APPROVED = "leave_request_approved"
    LEAVE_REQUEST_REJECTED = "leave_request_rejected"
    LEAVE_ELIGIBILITY_REMINDER = "leave_eligibility_reminder"
    SYSTEM = "system"
