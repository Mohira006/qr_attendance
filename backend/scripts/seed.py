"""Seed the database with demo data.

Usage (from the backend directory, after `alembic upgrade head`):
    python -m scripts.seed            # refuses to run if data already exists
    python -m scripts.seed --reset    # wipes all tables first

Creates:
- company settings (09:00-18:00, 15 min grace, Mon-Fri)
- 6 departments (Sales has its own 10:00-19:00 hours)
- 22 employees (one inactive, one on approved leave today, one with a personal 08:00-17:00 override)
- one HR administrator account plus one login account per employee
- 30 days of attendance history and a mixed set of records for today

EMP001 (Mohira Sobirjonova), EMP002 (Hasan Karimov), EMP003 and EMP011 have no attendance
record for today so the live Face ID scenario from the specification can be run against them.

Passwords are read from SEED_PASSWORD (default: Password123!) and are for development only.
"""

import argparse
import asyncio
import os
import random
from dataclasses import dataclass
from datetime import date, time, timedelta

from dateutil.relativedelta import relativedelta
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import SessionLocal, engine
from app.core.security import hash_password
from app.core.time import combine_local, today_local
from app.models import (
    Attendance,
    AuditLog,
    CheckoutStatus,
    CompanySettings,
    Department,
    DepartmentStatus,
    Employee,
    EmploymentStatus,
    ExplanationLetter,
    Leave,
    LeaveCycle,
    LeaveCycleStatus,
    LeaveRequest,
    LeaveRequestStatus,
    LeaveRequestType,
    LeaveStatus,
    LeaveType,
    Notification,
    RefreshToken,
    User,
    UserRole,
)
from app.services import leave_service, settings_service
from app.services.working_hours import (
    evaluate_arrival,
    expected_end,
    is_working_day,
    resolve_working_hours,
    working_minutes,
)

HR_ADMIN_EMAIL = "hr@company.com"
EMAIL_DOMAIN = "company.com"
HISTORY_DAYS = 30


@dataclass(frozen=True)
class DepartmentSeed:
    name: str
    description: str
    work_start: time | None = None
    work_end: time | None = None


@dataclass(frozen=True)
class EmployeeSeed:
    code: str
    first_name: str
    last_name: str
    department: str
    position: str
    role: UserRole = UserRole.EMPLOYEE
    status: EmploymentStatus = EmploymentStatus.ACTIVE
    work_start: time | None = None
    work_end: time | None = None
    # How many months ago they were hired. None = randomized (see seed_employees).
    # Specific values below are chosen to demonstrate every leave-eligibility state.
    months_employed: int | None = None


DEPARTMENTS = [
    DepartmentSeed("IT", "Software development, infrastructure and support"),
    DepartmentSeed("HR", "Human resources and recruitment"),
    DepartmentSeed("Finance", "Accounting, payroll and audit"),
    DepartmentSeed("Marketing", "Brand, content and social media"),
    DepartmentSeed("Sales", "Client acquisition and account management", time(10, 0), time(19, 0)),
    DepartmentSeed("Management", "Executive team and operations"),
]

EMPLOYEES = [
    EmployeeSeed("EMP001", "Mohira", "Sobirjonova", "IT", "Backend Developer", months_employed=18),
    EmployeeSeed("EMP002", "Hasan", "Karimov", "Finance", "Accountant", months_employed=18),
    EmployeeSeed("EMP003", "Ali", "Valiyev", "IT", "Frontend Developer"),
    EmployeeSeed("EMP004", "Dilnoza", "Rashidova", "HR", "HR Manager", role=UserRole.HR),
    EmployeeSeed("EMP005", "Jasur", "Tursunov", "Sales", "Sales Manager"),
    EmployeeSeed("EMP006", "Nilufar", "Abdullayeva", "Marketing", "Marketing Specialist"),
    EmployeeSeed("EMP007", "Bobur", "Yusupov", "IT", "DevOps Engineer", work_start=time(8, 0), work_end=time(17, 0)),
    EmployeeSeed("EMP008", "Malika", "Ergasheva", "Finance", "Financial Analyst", months_employed=3),  # not yet eligible
    EmployeeSeed("EMP009", "Sardor", "Mirzayev", "Management", "Operations Director"),
    EmployeeSeed("EMP010", "Zarina", "Nazarova", "Marketing", "Content Manager"),
    EmployeeSeed("EMP011", "Otabek", "Saidov", "Sales", "Sales Representative"),
    EmployeeSeed("EMP012", "Gulnora", "Kamolova", "HR", "Recruiter"),
    EmployeeSeed("EMP013", "Farrukh", "Ismoilov", "IT", "QA Engineer", months_employed=8),  # eligible, no request yet
    EmployeeSeed("EMP014", "Kamola", "Rustamova", "Finance", "Payroll Specialist"),
    EmployeeSeed("EMP015", "Shohruh", "Toshmatov", "Sales", "Account Executive", months_employed=9),  # gets a PENDING request
    EmployeeSeed("EMP016", "Sevara", "Yuldasheva", "Marketing", "SMM Manager"),
    EmployeeSeed("EMP017", "Javohir", "Qodirov", "IT", "Mobile Developer", months_employed=10),  # gets an APPROVED upcoming leave
    EmployeeSeed("EMP018", "Madina", "Xolmatova", "Management", "Executive Assistant"),
    EmployeeSeed("EMP019", "Umid", "Sharipov", "Finance", "Auditor", months_employed=20),  # gets a COMPLETED cycle 1 + cycle 2 in progress
    EmployeeSeed("EMP020", "Lola", "Azimova", "HR", "HR Specialist"),
    EmployeeSeed("EMP021", "Rustam", "Berdiyev", "Sales", "Sales Representative", status=EmploymentStatus.INACTIVE),
    EmployeeSeed("EMP022", "Feruza", "Olimova", "Marketing", "Designer"),
]

# Today's picture. Offsets are minutes relative to each employee's own work start / end.
# (arrival_offset, departure_offset); departure None = still at work.
TODAY_PLAN: dict[str, tuple[int, int | None]] = {
    "EMP004": (-12, None),
    "EMP005": (-2, None),
    "EMP006": (-5, None),
    "EMP007": (3, None),
    "EMP008": (27, None),
    "EMP009": (-20, None),
    "EMP010": (-8, 5),
    "EMP012": (10, None),
    "EMP013": (19, None),
    "EMP014": (0, 12),
    "EMP015": (33, 2),
    "EMP016": (-15, None),
    "EMP017": (14, None),
    "EMP018": (-3, 0),
    "EMP019": (52, None),
    "EMP020": (41, 25),
}
ON_LEAVE_TODAY = "EMP022"
NO_RECORD_TODAY = {"EMP001", "EMP002", "EMP003", "EMP011"}


def seed_password() -> str:
    return os.environ.get("SEED_PASSWORD", "Password123!")


async def database_has_data(db: AsyncSession) -> bool:
    return (await db.execute(select(Department.id).limit(1))).scalar_one_or_none() is not None


async def reset_database(db: AsyncSession) -> None:
    # Children first; FK ondelete rules are not relied upon so this also works on SQLite.
    for model in (
        Notification,
        ExplanationLetter,
        LeaveRequest,
        LeaveCycle,
        Attendance,
        Leave,
        AuditLog,
        RefreshToken,
        CompanySettings,
        User,
        Employee,
        Department,
    ):
        await db.execute(delete(model))
    await db.commit()


async def seed_departments(db: AsyncSession) -> dict[str, Department]:
    departments: dict[str, Department] = {}
    for item in DEPARTMENTS:
        department = Department(
            name=item.name,
            description=item.description,
            status=DepartmentStatus.ACTIVE,
            work_start_time=item.work_start,
            work_end_time=item.work_end,
        )
        db.add(department)
        departments[item.name] = department
    await db.flush()
    return departments


async def seed_employees(db: AsyncSession, departments: dict[str, Department]) -> dict[str, Employee]:
    today = today_local()
    employees: dict[str, Employee] = {}
    for item in EMPLOYEES:
        months = item.months_employed if item.months_employed is not None else random.randint(12, 48)
        employee = Employee(
            employee_id=item.code,
            first_name=item.first_name,
            last_name=item.last_name,
            department_id=departments[item.department].id,
            position=item.position,
            phone=f"+998 90 {random.randint(100, 999)} {random.randint(10, 99)} {random.randint(10, 99)}",
            email=f"{item.first_name.lower()}.{item.last_name.lower()}@{EMAIL_DOMAIN}",
            work_start_time=item.work_start,
            work_end_time=item.work_end,
            employment_start_date=today - relativedelta(months=months),
            status=item.status,
        )
        db.add(employee)
        employees[item.code] = employee
    await db.flush()
    return employees


async def seed_users(db: AsyncSession, employees: dict[str, Employee]) -> None:
    password_hash = hash_password(seed_password())
    db.add(User(employee_id=None, email=HR_ADMIN_EMAIL, password_hash=password_hash, role=UserRole.HR, is_active=True))
    for item in EMPLOYEES:
        employee = employees[item.code]
        db.add(
            User(
                employee_id=employee.id,
                email=employee.email,
                password_hash=password_hash,
                role=item.role,
                is_active=item.status == EmploymentStatus.ACTIVE,
            )
        )
    await db.flush()


def build_attendance(
    employee: Employee,
    department: Department,
    settings: CompanySettings,
    day: date,
    arrival_offset: int,
    departure_offset: int | None,
) -> Attendance:
    hours = resolve_working_hours(employee, department, settings)
    check_in = combine_local(day, hours.start) + timedelta(minutes=arrival_offset, seconds=random.randint(0, 59))
    evaluation = evaluate_arrival(check_in, hours, day)

    check_out = None
    checkout_status = CheckoutStatus.PENDING
    total = None
    if departure_offset is not None:
        check_out = expected_end(day, hours) + timedelta(minutes=departure_offset, seconds=random.randint(0, 59))
        checkout_status = CheckoutStatus.COMPLETED
        total = working_minutes(check_in, check_out)

    return Attendance(
        employee_id=employee.id,
        date=day,
        check_in=check_in,
        check_out=check_out,
        status=evaluation.status,
        checkout_status=checkout_status,
        late_minutes=evaluation.late_minutes,
        total_working_minutes=total,
        expected_check_in=hours.start,
        expected_check_out=hours.end,
    )


def random_history_offsets() -> tuple[int, int | None] | None:
    """Returns (arrival_offset, departure_offset) for a past working day, or None for an absence."""
    roll = random.random()
    if roll < 0.07:
        return None  # absent
    if roll < 0.80:
        arrival = random.randint(-25, 12)  # on time (grace period is 15 min)
    elif roll < 0.97:
        arrival = random.randint(16, 55)  # late, letter generated in production flow
    else:
        arrival = random.randint(60, 120)  # very late
    if random.random() < 0.04:
        return arrival, None  # forgot to check out (ends up MISSING after the end-of-day job)
    return arrival, random.randint(-10, 45)


async def seed_attendance(
    db: AsyncSession,
    employees: dict[str, Employee],
    departments: dict[str, Department],
    settings: CompanySettings,
) -> tuple[int, int]:
    today = today_local()
    department_by_id = {department.id: department for department in departments.values()}
    history_count = 0

    for offset in range(HISTORY_DAYS, 0, -1):
        day = today - timedelta(days=offset)
        if not is_working_day(day, settings):
            continue
        for item in EMPLOYEES:
            if item.status == EmploymentStatus.INACTIVE and offset < 10:
                continue  # deactivated ten days ago
            employee = employees[item.code]
            offsets = random_history_offsets()
            if offsets is None:
                continue
            arrival, departure = offsets
            record = build_attendance(employee, department_by_id[employee.department_id], settings, day, arrival, departure)
            if departure is None:
                record.checkout_status = CheckoutStatus.MISSING
            db.add(record)
            history_count += 1

    today_count = 0
    for code, (arrival, departure) in TODAY_PLAN.items():
        employee = employees[code]
        db.add(build_attendance(employee, department_by_id[employee.department_id], settings, today, arrival, departure))
        today_count += 1

    await db.flush()
    return history_count, today_count


async def seed_leave(db: AsyncSession, employees: dict[str, Employee]) -> None:
    today = today_local()
    db.add(
        Leave(
            employee_id=employees[ON_LEAVE_TODAY].id,
            start_date=today - timedelta(days=2),
            end_date=today + timedelta(days=3),
            leave_type=LeaveType.VACATION,
            status=LeaveStatus.APPROVED,
            reason="Annual leave",
        )
    )
    await db.flush()


async def seed_leave_requests(db: AsyncSession, employees: dict[str, Employee], hr_actor: User, settings: CompanySettings) -> None:
    """A few employees get real leave_cycles/leave_requests in interesting states.
    Two go through the actual leave_service, so this data obeys the exact same
    rules the live app enforces - not hand-rolled duplicate logic. The third
    (EMP019's already-completed first cycle) is necessarily historical, and
    create_leave_request correctly refuses to backdate a request even for HR -
    that guard is a data-integrity rule, not something seed data should route
    around - so that one is constructed directly, mirroring exactly what
    approve_leave_request does internally.
    """
    today = today_local()

    # EMP015: submitted with three weeks' notice, still awaiting a decision.
    await leave_service.create_leave_request(
        db,
        employee=employees["EMP015"],
        requested_start_date=today + timedelta(days=21),
        request_type=LeaveRequestType.NORMAL,
        employee_comment="Oilaviy sabablar tufayli ta'tilga chiqmoqchiman.",
        settings=settings,
        actor=hr_actor,
        ip=None,
    )

    # EMP017: already approved, upcoming.
    request_17 = await leave_service.create_leave_request(
        db,
        employee=employees["EMP017"],
        requested_start_date=today + timedelta(days=16),
        request_type=LeaveRequestType.NORMAL,
        employee_comment="Planning a family trip.",
        settings=settings,
        actor=hr_actor,
        ip=None,
    )
    await leave_service.approve_leave_request(db, request_17, settings, actor=hr_actor, ip=None, hr_comment="Approved.")

    # EMP019: a full first cycle already taken and finished, now partway through
    # the wait for cycle 2's eligibility (still in the future - demonstrates the
    # 11-months-after-return rule with a concrete, already-elapsed example).
    emp19 = employees["EMP019"]
    cycle1_start = emp19.employment_start_date
    cycle1_end, cycle1_eligibility = leave_service.compute_cycle_window(cycle1_start, settings.leave_eligibility_after_months)
    cycle1 = LeaveCycle(
        employee_id=emp19.id,
        cycle_number=1,
        cycle_start_date=cycle1_start,
        cycle_end_date=cycle1_end,
        eligibility_date=cycle1_eligibility,
        status=LeaveCycleStatus.CONSUMED,
    )
    db.add(cycle1)
    await db.flush()

    leave_start = cycle1_eligibility + timedelta(days=10)
    leave_end = leave_start + timedelta(days=settings.annual_leave_duration_days - 1)
    submitted_at = combine_local(leave_start - timedelta(days=20), time(9, 0))
    approved_at = combine_local(leave_start - timedelta(days=18), time(11, 0))

    request_19 = LeaveRequest(
        employee_id=emp19.id,
        leave_cycle_id=cycle1.id,
        requested_start_date=leave_start,
        requested_end_date=leave_end,
        duration_days=settings.annual_leave_duration_days,
        request_type=LeaveRequestType.NORMAL,
        status=LeaveRequestStatus.COMPLETED,
        employee_comment="Annual vacation.",
        hr_comment="Approved. Enjoy the break.",
        submitted_at=submitted_at,
        approved_at=approved_at,
        reviewed_by_user_id=hr_actor.id,
    )
    db.add(request_19)
    await db.flush()

    leave_row = Leave(
        employee_id=emp19.id,
        start_date=leave_start,
        end_date=leave_end,
        leave_type=LeaveType.VACATION,
        status=LeaveStatus.APPROVED,
        reason="Annual vacation.",
        created_by_user_id=hr_actor.id,
    )
    db.add(leave_row)
    await db.flush()
    request_19.leave_id = leave_row.id

    cycle2_end, cycle2_eligibility = leave_service.compute_cycle_window(leave_end, settings.leave_next_cycle_after_months)
    cycle2 = LeaveCycle(
        employee_id=emp19.id,
        cycle_number=2,
        cycle_start_date=leave_end,
        cycle_end_date=cycle2_end,
        eligibility_date=cycle2_eligibility,
        status=LeaveCycleStatus.AVAILABLE,
    )
    db.add(cycle2)
    await db.flush()


async def run(reset: bool) -> None:
    random.seed(42)
    async with SessionLocal() as db:
        if await database_has_data(db):
            if not reset:
                raise SystemExit("Database already contains data. Re-run with --reset to wipe it first.")
            await reset_database(db)

        settings = await settings_service.get_or_create(db)
        departments = await seed_departments(db)
        employees = await seed_employees(db, departments)
        await seed_users(db, employees)
        await seed_leave(db, employees)
        hr_admin = (await db.execute(select(User).where(User.email == HR_ADMIN_EMAIL))).scalar_one()
        await seed_leave_requests(db, employees, hr_admin, settings)
        history_count, today_count = await seed_attendance(db, employees, departments, settings)
        await db.commit()

    await engine.dispose()

    print("Seed complete.")
    print(f"  departments: {len(departments)}")
    print(f"  employees:   {len(employees)} (1 inactive, 1 on leave today)")
    print(f"  attendance:  {history_count} historical records, {today_count} for today")
    print(f"  today without a record (for the live demo): {', '.join(sorted(NO_RECORD_TODAY))}")
    print("  leave demo: EMP008/EMP013 not-yet/eligible-untouched, EMP015 pending,")
    print("              EMP017 approved-upcoming, EMP019 completed cycle 1 + cycle 2 in progress")
    print("Accounts (password from SEED_PASSWORD, default Password123!):")
    print(f"  HR admin:  {HR_ADMIN_EMAIL}")
    print(f"  HR (employee-linked): dilnoza.rashidova@{EMAIL_DOMAIN}")
    print(f"  Employees: mohira.sobirjonova@{EMAIL_DOMAIN}, hasan.karimov@{EMAIL_DOMAIN}, ... (firstname.lastname)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed demo data")
    parser.add_argument("--reset", action="store_true", help="delete existing data before seeding")
    args = parser.parse_args()
    asyncio.run(run(reset=args.reset))


if __name__ == "__main__":
    main()
