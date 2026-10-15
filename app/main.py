from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from pymongo import ASCENDING, DESCENDING, MongoClient
from pydantic import BaseModel, Field
from pymongo.errors import DuplicateKeyError


# ============================================================
# APP
# ============================================================

app = FastAPI(
    title="Employee Attendance & Analytics API",
    version="2.0.0",
)


# ============================================================
# MONGODB
# ============================================================

MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "hrone_attendance"

client = MongoClient(MONGO_URL)
db = client[DB_NAME]


# Collections
employees = db.employees
attendance_logs = db.attendance_logs


# ============================================================
# CONSTANTS
# ============================================================

ALL_STATUSES = {
    "PRESENT",
    "ABSENT",
    "LEAVE",
    "HALF_DAY",
}


# ============================================================
# PYDANTIC MODELS
# ============================================================

class EmployeeIn(BaseModel):
    emp_code: str
    name: str
    email: str
    department: str
    shift_start: str
    shift_end: str
    joined_on: str


class PunchInIn(BaseModel):
    emp_code: str
    punched_at: int
    status: str = "PRESENT"


class PunchOutIn(BaseModel):
    emp_code: str
    punched_at: int


class RegularizeIn(BaseModel):
    status: str
    punch_in: Optional[int] = None
    punch_out: Optional[int] = None
    reason: str
    regularized_by: str


# ============================================================
# VALIDATION HELPERS
# ============================================================

def valid_date_string(value: str) -> bool:
    try:
        date.fromisoformat(value)
        return True
    except Exception:
        raise ValueError("invalid date")


def valid_month(value: str) -> bool:
    try:
        if len(value) != 7:
            raise ValueError
        datetime.strptime(value, "%Y-%m")
        return True
    except Exception:
        raise ValueError("invalid month")


def validate_status(status: str):
    if status not in ALL_STATUSES:
        raise HTTPException(
            status_code=422,
            detail="invalid status",
        )


def decimal_round(value, places=2):
    if value is None:
        return None

    q = Decimal("1." + ("0" * places))

    return float(
        Decimal(str(value)).quantize(
            q,
            rounding=ROUND_HALF_UP,
        )
    )


def timestamp_to_datetime(timestamp_ms: int) -> datetime:
    return datetime.fromtimestamp(
        timestamp_ms / 1000
    )


def timestamp_to_date(timestamp_ms: int) -> str:
    return timestamp_to_datetime(timestamp_ms).date().isoformat()


def minutes_between(start_ms: int, end_ms: int) -> float:
    return (end_ms - start_ms) / 60000


def time_to_minutes(value: str) -> int:
    try:
        hour, minute = value.split(":")
        return int(hour) * 60 + int(minute)
    except Exception:
        raise HTTPException(
            status_code=422,
            detail="invalid shift time",
        )


def calculate_late_minutes(
    employee: dict,
    punched_at: int,
) -> int:

    punch_dt = timestamp_to_datetime(punched_at)

    punch_minutes = (
        punch_dt.hour * 60
        + punch_dt.minute
    )

    shift_minutes = time_to_minutes(
        employee["shift_start"]
    )

    return max(
        0,
        punch_minutes - shift_minutes,
    )


def calculate_attendance(
    employee: dict,
    record: dict,
) -> dict:

    punch_in = record.get("punch_in")
    punch_out = record.get("punch_out")

    work_hours = None
    overtime_minutes = 0

    if punch_in is not None and punch_out is not None:

        total_minutes = minutes_between(
            punch_in,
            punch_out,
        )

        work_hours = decimal_round(
            total_minutes / 60,
            2,
        )

        shift_start = time_to_minutes(
            employee["shift_start"]
        )

        shift_end = time_to_minutes(
            employee["shift_end"]
        )

        punch_out_dt = timestamp_to_datetime(
            punch_out
        )

        punch_out_minutes = (
            punch_out_dt.hour * 60
            + punch_out_dt.minute
        )

        overtime_minutes = max(
            0,
            punch_out_minutes - shift_end,
        )

    late_minutes = 0

    if punch_in is not None:
        late_minutes = calculate_late_minutes(
            employee,
            punch_in,
        )

    half_day = (
        record.get("status") == "HALF_DAY"
    )

    return {
        "work_hours": work_hours,
        "late_minutes": late_minutes,
        "overtime_minutes": overtime_minutes,
        "half_day": half_day,
    }


def serialize_attendance(record: dict) -> dict:

    result = {
        "emp_code": record["emp_code"],
        "date": record["date"],
        "status": record["status"],
        "punch_in": record.get("punch_in"),
        "punch_out": record.get("punch_out"),
        "work_hours": record.get("work_hours"),
        "late_minutes": record.get(
            "late_minutes",
            0,
        ),
        "overtime_minutes": record.get(
            "overtime_minutes",
            0,
        ),
        "half_day": record.get(
            "half_day",
            False,
        ),
        "history": record.get(
            "history",
            [],
        ),
    }

    return result


# ============================================================
# INDEXES
# ============================================================

def create_indexes():

    # --------------------------------------------------------
    # Employees
    # --------------------------------------------------------

    employees.create_index(
        [("emp_code", ASCENDING)],
        unique=True,
        name="ux_emp_code",
    )

    employees.create_index(
        [
            ("department", ASCENDING),
            ("joined_on", ASCENDING),
        ],
        name="ix_emp_department_joined",
    )

    # --------------------------------------------------------
    # Attendance
    # --------------------------------------------------------

    attendance_logs.create_index(
        [
            ("emp_code", ASCENDING),
            ("date", ASCENDING),
        ],
        unique=True,
        name="ux_attendance_emp_date",
    )

    attendance_logs.create_index(
        [
            ("emp_code", ASCENDING),
            ("punch_in", ASCENDING),
        ],
        name="ix_attendance_emp_punchin",
    )

    attendance_logs.create_index(
        [
            ("status", ASCENDING),
            ("date", DESCENDING),
            ("emp_code", ASCENDING),
        ],
        name="ix_attendance_status_date_emp",
    )

    attendance_logs.create_index(
        [
            ("date", DESCENDING),
            ("emp_code", ASCENDING),
        ],
        name="ix_attendance_date_emp",
    )

    attendance_logs.create_index(
        [
            ("date", ASCENDING),
            ("emp_code", ASCENDING),
        ],
        name="ix_attendance_date_emp_asc",
    )


@app.on_event("startup")
def startup():

    create_indexes()


# ============================================================
# ROOT / HEALTH
# ============================================================

@app.get("/")
def root():

    return {
        "message": "Employee Attendance & Analytics API"
    }


@app.get("/health")
def health():

    return {
        "status": "ok"
    }


# ============================================================
# EMPLOYEES
# ============================================================

@app.post(
    "/employees",
    status_code=201,
)
def create_employee(
    employee: EmployeeIn,
):

    try:
        valid_date_string(
            employee.joined_on
        )
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail="invalid date",
        )

    document = employee.model_dump()

    document["created_at"] = int(
        datetime.now().timestamp() * 1000
    )

    try:

        employees.insert_one(
            document
        )

    except DuplicateKeyError:

        raise HTTPException(
            status_code=409,
            detail="employee already exists",
        )

    document.pop("_id", None)

    return document


@app.get("/employees")
def list_employees(
    page: int = Query(1, ge=1),
    page_size: int = Query(
        20,
        ge=1,
        le=100,
    ),
):

    skip = (
        page - 1
    ) * page_size

    total = employees.count_documents({})

    items = list(
        employees.find(
            {},
            {"_id": 0},
        )
        .sort(
            "emp_code",
            ASCENDING,
        )
        .skip(skip)
        .limit(page_size)
    )

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


# ============================================================
# ATTENDANCE - PUNCH IN
# ============================================================

@app.post(
    "/attendance/punch-in",
    status_code=201,
)
def punch_in(
    request: PunchInIn,
):

    employee = employees.find_one(
        {
            "emp_code": request.emp_code
        }
    )

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="employee not found",
        )

    validate_status(
        request.status
    )

    attendance_date = timestamp_to_date(
        request.punched_at
    )

    existing = attendance_logs.find_one(
        {
            "emp_code": request.emp_code,
            "date": attendance_date,
        }
    )

    if existing and existing.get("punch_in") is not None:
        raise HTTPException(
            status_code=409,
            detail="employee already punched in",
        )

    calculations = calculate_attendance(
        employee,
        {
            "status": request.status,
            "punch_in": request.punched_at,
            "punch_out": None,
        },
    )

    document = {
        "emp_code": request.emp_code,
        "date": attendance_date,
        "status": request.status,
        "punch_in": request.punched_at,
        "punch_out": None,
        "work_hours": None,
        "late_minutes": calculations[
            "late_minutes"
        ],
        "overtime_minutes": 0,
        "half_day": calculations[
            "half_day"
        ],
        "history": [],
    }

    if existing:

        attendance_logs.update_one(
            {
                "emp_code": request.emp_code,
                "date": attendance_date,
            },
            {
                "$set": document
            },
        )

    else:

        attendance_logs.insert_one(
            document
        )

    return serialize_attendance(
        document
    )


# ============================================================
# ATTENDANCE - PUNCH OUT
# ============================================================

@app.post(
    "/attendance/punch-out"
)
def punch_out(
    request: PunchOutIn,
):

    employee = employees.find_one(
        {
            "emp_code": request.emp_code
        }
    )

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="employee not found",
        )

    attendance_date = timestamp_to_date(
        request.punched_at
    )

    record = attendance_logs.find_one(
        {
            "emp_code": request.emp_code,
            "date": attendance_date,
        }
    )

    if not record:
        raise HTTPException(
            status_code=404,
            detail="attendance record not found",
        )

    if record.get("punch_in") is None:
        raise HTTPException(
            status_code=422,
            detail="punch-in is required",
        )

    if record.get("punch_out") is not None:
        raise HTTPException(
            status_code=409,
            detail="employee already punched out",
        )

    if request.punched_at < record["punch_in"]:
        raise HTTPException(
            status_code=422,
            detail="punch-out must be after punch-in",
        )

    calculations = calculate_attendance(
        employee,
        {
            **record,
            "punch_out": request.punched_at,
        },
    )

    update = {
        "punch_out": request.punched_at,
        "work_hours": calculations[
            "work_hours"
        ],
        "late_minutes": calculations[
            "late_minutes"
        ],
        "overtime_minutes": calculations[
            "overtime_minutes"
        ],
        "half_day": calculations[
            "half_day"
        ],
    }

    attendance_logs.update_one(
        {
            "_id": record["_id"]
        },
        {
            "$set": update
        },
    )

    record.update(update)

    return serialize_attendance(
        record
    )


# ============================================================
# ATTENDANCE LIST
# ============================================================

@app.get("/attendance")
def list_attendance(
    emp_code: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(
        20,
        ge=1,
        le=100,
    ),
):

    if date_from:

        try:
            valid_date_string(
                date_from
            )
        except ValueError:

            raise HTTPException(
                status_code=422,
                detail="invalid date_from",
            )

    if date_to:

        try:
            valid_date_string(
                date_to
            )
        except ValueError:

            raise HTTPException(
                status_code=422,
                detail="invalid date_to",
            )

    if (
        date_from
        and date_to
        and date_from > date_to
    ):

        raise HTTPException(
            status_code=422,
            detail="date_from must not be after date_to",
        )

    if status:
        validate_status(status)

    query = {}

    if emp_code:
        query["emp_code"] = emp_code

    if date_from or date_to:

        query["date"] = {}

        if date_from:
            query["date"]["$gte"] = date_from

        if date_to:
            query["date"]["$lte"] = date_to

    if status:
        query["status"] = status

    total = attendance_logs.count_documents(
        query
    )

    skip = (
        page - 1
    ) * page_size

    items = list(
        attendance_logs.find(
            query,
            {"_id": 0},
        )
        .sort(
            [
                ("date", DESCENDING),
                ("emp_code", ASCENDING),
            ]
        )
        .skip(skip)
        .limit(page_size)
    )

    return {
        "items": [
            serialize_attendance(item)
            for item in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


# ============================================================
# REGULARIZE ATTENDANCE
# ============================================================

@app.patch(
    "/attendance/{emp_code}/{date}"
)
def regularize_attendance(
    emp_code: str,
    date: str,
    request: RegularizeIn,
):

    try:
        valid_date_string(date)
    except ValueError:

        raise HTTPException(
            status_code=422,
            detail="invalid date",
        )

    validate_status(
        request.status
    )

    employee = employees.find_one(
        {
            "emp_code": emp_code
        }
    )

    if not employee:

        raise HTTPException(
            status_code=404,
            detail="employee not found",
        )

    record = attendance_logs.find_one(
        {
            "emp_code": emp_code,
            "date": date,
        }
    )

    if not record:

        raise HTTPException(
            status_code=404,
            detail="attendance record not found",
        )

    new_values = {}

    if request.status != record.get(
        "status"
    ):
        new_values["status"] = request.status

    if (
        request.punch_in is not None
        and request.punch_in
        != record.get("punch_in")
    ):
        new_values["punch_in"] = (
            request.punch_in
        )

    if (
        request.punch_out is not None
        and request.punch_out
        != record.get("punch_out")
    ):
        new_values["punch_out"] = (
            request.punch_out
        )

    if not new_values:

        raise HTTPException(
            status_code=422,
            detail="request does not change the record",
        )

    updated_record = {
        **record,
        **new_values,
    }

    calculations = calculate_attendance(
        employee,
        updated_record,
    )

    new_values.update(
        {
            "work_hours": calculations[
                "work_hours"
            ],
            "late_minutes": calculations[
                "late_minutes"
            ],
            "overtime_minutes": calculations[
                "overtime_minutes"
            ],
            "half_day": calculations[
                "half_day"
            ],
        }
    )

    changes = {}

    for key, new_value in new_values.items():

        old_value = record.get(key)

        if old_value != new_value:

            changes[key] = {
                "from": old_value,
                "to": new_value,
            }

    history_entry = {
        "at": int(
            datetime.now().timestamp()
            * 1000
        ),
        "by": request.regularized_by,
        "reason": request.reason,
        "changes": changes,
    }

    new_values["history"] = (
        record.get("history", [])
        + [history_entry]
    )

    attendance_logs.update_one(
        {
            "_id": record["_id"]
        },
        {
            "$set": new_values
        },
    )

    record.update(new_values)

    return serialize_attendance(
        record
    )


# ============================================================
# EMPLOYEE MONTHLY ANALYTICS
# ============================================================

@app.get(
    "/analytics/employees/{emp_code}/monthly"
)
def employee_monthly(
    emp_code: str,
    month: str = Query(...),
):

    try:
        valid_month(month)
    except ValueError:

        raise HTTPException(
            status_code=422,
            detail="month must be YYYY-MM",
        )

    employee = employees.find_one(
        {
            "emp_code": emp_code
        }
    )

    if not employee:

        raise HTTPException(
            status_code=404,
            detail="employee not found",
        )

    records = list(
        attendance_logs.find(
            {
                "emp_code": emp_code,
                "date": {
                    "$regex": f"^{month}-"
                },
            },
            {"_id": 0},
        )
    )

    present_days = sum(
        1
        for r in records
        if r.get("status") == "PRESENT"
    )

    leave_days = sum(
        1
        for r in records
        if r.get("status") == "LEAVE"
    )

    half_days = sum(
        1
        for r in records
        if r.get("status") == "HALF_DAY"
    )

    late_records = [
        r
        for r in records
        if r.get("late_minutes", 0) > 0
    ]

    total_late_minutes = sum(
        r.get("late_minutes", 0)
        for r in records
    )

    total_overtime_minutes = sum(
        r.get("overtime_minutes", 0)
        for r in records
    )

    # Weekdays in the month after employee joined
    year, month_number = map(
        int,
        month.split("-")
    )

    month_start = date(
        year,
        month_number,
        1,
    )

    if month_number == 12:

        next_month = date(
            year + 1,
            1,
            1,
        )

    else:

        next_month = date(
            year,
            month_number + 1,
            1,
        )

    month_end = (
        next_month
        - timedelta(days=1)
    )

    joined_on = date.fromisoformat(
        employee["joined_on"]
    )

    working_start = max(
        month_start,
        joined_on,
    )

    working_days = 0

    if working_start <= month_end:

        current = working_start

        while current <= month_end:

            if current.weekday() < 5:
                working_days += 1

            current += timedelta(days=1)

    attendance_pct = None

    if working_days > 0:

        attendance_pct = decimal_round(
            (
                (
                    present_days
                    + (half_days * 0.5)
                )
                / working_days
            )
            * 100,
            2,
        )

    return {
        "month": month,
        "working_days": working_days,
        "present_days": present_days,
        "leave_days": leave_days,
        "late_count": len(late_records),
        "total_late_minutes": total_late_minutes,
        "total_overtime_minutes": total_overtime_minutes,
        "emp_code": emp_code,
        "attendance_pct": attendance_pct,
    }


# ============================================================
# DEPARTMENT SUMMARY
# ============================================================

@app.get(
    "/analytics/departments/summary"
)
def department_summary(
    month: str = Query(...),
    department: Optional[str] = None,
):

    try:
        valid_month(month)
    except ValueError:

        raise HTTPException(
            status_code=422,
            detail="month must be YYYY-MM",
        )

    employee_query = {}

    if department:
        employee_query["department"] = (
            department
        )

    employee_list = list(
        employees.find(
            employee_query,
            {"_id": 0},
        )
    )

    if not employee_list:
        return {
            "month": month,
            "items": [],
        }

    items = []

    for employee in employee_list:

        emp_code = employee[
            "emp_code"
        ]

        records = list(
            attendance_logs.find(
                {
                    "emp_code": emp_code,
                    "date": {
                        "$regex": f"^{month}-"
                    },
                },
                {"_id": 0},
            )
        )

        present_days = sum(
            1
            for r in records
            if r.get("status")
            == "PRESENT"
        )

        leave_days = sum(
            1
            for r in records
            if r.get("status")
            == "LEAVE"
        )

        half_days = sum(
            1
            for r in records
            if r.get("status")
            == "HALF_DAY"
        )

        late_count = sum(
            1
            for r in records
            if r.get(
                "late_minutes",
                0,
            ) > 0
        )

        total_late_minutes = sum(
            r.get(
                "late_minutes",
                0,
            )
            for r in records
        )

        total_overtime_minutes = sum(
            r.get(
                "overtime_minutes",
                0,
            )
            for r in records
        )

        items.append(
            {
                "department": employee[
                    "department"
                ],
                "employee_count": 1,
                "present_days": present_days,
                "leave_days": leave_days,
                "half_days": half_days,
                "late_count": late_count,
                "total_late_minutes":
                    total_late_minutes,
                "total_overtime_minutes":
                    total_overtime_minutes,
            }
        )

    # Group employees by department
    grouped = {}

    for item in items:

        dept = item[
            "department"
        ]

        if dept not in grouped:

            grouped[dept] = {
                "department": dept,
                "employee_count": 0,
                "present_days": 0,
                "leave_days": 0,
                "half_days": 0,
                "late_count": 0,
                "total_late_minutes": 0,
                "total_overtime_minutes": 0,
            }

        grouped[dept][
            "employee_count"
        ] += 1

        grouped[dept][
            "present_days"
        ] += item["present_days"]

        grouped[dept][
            "leave_days"
        ] += item["leave_days"]

        grouped[dept][
            "half_days"
        ] += item["half_days"]

        grouped[dept][
            "late_count"
        ] += item["late_count"]

        grouped[dept][
            "total_late_minutes"
        ] += item[
            "total_late_minutes"
        ]

        grouped[dept][
            "total_overtime_minutes"
        ] += item[
            "total_overtime_minutes"
        ]

    return {
        "month": month,
        "items": list(
            grouped.values()
        ),
    }


# ============================================================
# LATE LEADERBOARD
# ============================================================

@app.get(
    "/analytics/leaderboard/late"
)
def late_leaderboard(
    month: str = Query(...),
    limit: int = Query(
        10,
        ge=1,
        le=50,
    ),
    department: Optional[str] = None,
):

    try:
        valid_month(month)
    except ValueError:

        raise HTTPException(
            status_code=422,
            detail="month must be YYYY-MM",
        )

    query = {
        "date": {
            "$regex": f"^{month}-"
        },
        "late_minutes": {
            "$gt": 0
        },
    }

    if department:
        query[
            "department"
        ] = department

    records = list(
        attendance_logs.find(
            query,
            {"_id": 0},
        )
    )

    employee_codes = {
        r["emp_code"]
        for r in records
    }

    employee_map = {}

    for code in employee_codes:

        employee = employees.find_one(
            {
                "emp_code": code
            },
            {"_id": 0},
        )

        if employee:

            employee_map[code] = employee

    grouped = {}

    for record in records:

        code = record[
            "emp_code"
        ]

        employee = employee_map.get(
            code
        )

        if not employee:
            continue

        if (
            department
            and employee["department"]
            != department
        ):
            continue

        if code not in grouped:

            grouped[code] = {
                "name": employee["name"],
                "department": employee[
                    "department"
                ],
                "total_late_minutes": 0,
                "late_count": 0,
                "emp_code": code,
            }

        grouped[code][
            "total_late_minutes"
        ] += record.get(
            "late_minutes",
            0,
        )

        grouped[code][
            "late_count"
        ] += 1

    sorted_items = sorted(
        grouped.values(),
        key=lambda x: (
            -x["total_late_minutes"],
            -x["late_count"],
            x["emp_code"],
        ),
    )

    result = []

    for rank, item in enumerate(
        sorted_items[:limit],
        start=1,
    ):

        item["rank"] = rank

        # Keep requested output order
        result.append(
            {
                "name": item["name"],
                "department": item[
                    "department"
                ],
                "total_late_minutes":
                    item[
                        "total_late_minutes"
                    ],
                "late_count":
                    item["late_count"],
                "rank": item["rank"],
                "emp_code": item[
                    "emp_code"
                ],
            }
        )

    return {
        "month": month,
        "items": result,
    }


# ============================================================
# DEPARTMENT TREND
# ============================================================

@app.get(
    "/analytics/departments/{department}/trend"
)
def department_trend(
    department: str,
    from_: str = Query(
        ...,
        alias="from",
    ),
    to: str = Query(...),
):

    try:

        valid_date_string(
            from_
        )

        valid_date_string(
            to
        )

    except ValueError:

        raise HTTPException(
            status_code=422,
            detail="invalid date",
        )

    start = date.fromisoformat(
        from_
    )

    end = date.fromisoformat(
        to
    )

    if end < start:

        raise HTTPException(
            status_code=422,
            detail="to must not be before from",
        )

    if (
        end - start
    ).days + 1 > 92:

        raise HTTPException(
            status_code=422,
            detail="date range must not exceed 92 days",
        )

    employee_count = employees.count_documents(
        {
            "department": department
        }
    )

    if employee_count == 0:

        raise HTTPException(
            status_code=404,
            detail="department not found",
        )

    # --------------------------------------------------------
    # IMPORTANT:
    # Do NOT use MongoDB $documents here.
    # We calculate the trend directly from attendance records.
    # --------------------------------------------------------

    records = list(
        attendance_logs.find(
            {},
            {"_id": 0},
        )
    )

    # Keep only dates in requested range
    # and employees from requested department.
    department_codes = {
        employee["emp_code"]
        for employee in employees.find(
            {
                "department": department
            },
            {
                "_id": 0,
                "emp_code": 1,
            },
        )
    }

    filtered = []

    for record in records:

        if record["emp_code"] not in department_codes:
            continue

        if (
            record["date"] < from_
            or record["date"] > to
        ):
            continue

        filtered.append(record)

    # Group by date
    by_date = {}

    for record in filtered:

        day = record["date"]

        if day not in by_date:
            by_date[day] = []

        by_date[day].append(record)

    items = []

    current = start

    while current <= end:

        day_string = current.isoformat()

        day_records = by_date.get(
            day_string,
            [],
        )

        present = sum(
            1
            for r in day_records
            if r.get("status")
            == "PRESENT"
        )

        half_day = sum(
            1
            for r in day_records
            if r.get("status")
            == "HALF_DAY"
        )

        leave = sum(
            1
            for r in day_records
            if r.get("status")
            == "LEAVE"
        )

        absent = sum(
            1
            for r in day_records
            if r.get("status")
            == "ABSENT"
        )

        late_minutes = sum(
            r.get(
                "late_minutes",
                0,
            )
            for r in day_records
        )

        overtime_minutes = sum(
            r.get(
                "overtime_minutes",
                0,
            )
            for r in day_records
        )

        attendance_rate = None

        if employee_count > 0:

            attendance_rate = (
                (
                    present
                    + half_day * 0.5
                )
                / employee_count
            ) * 100

        items.append(
            {
                "date": day_string,
                "present": present,
                "half_day": half_day,
                "leave": leave,
                "absent": absent,
                "late_minutes":
                    late_minutes,
                "overtime_minutes":
                    overtime_minutes,
                "attendance_rate":
                    decimal_round(
                        attendance_rate,
                        4,
                    )
                    if attendance_rate
                    is not None
                    else None,
            }
        )

        current += timedelta(
            days=1
        )

    # --------------------------------------------------------
    # 7-day moving average
    # --------------------------------------------------------

    for index, item in enumerate(
        items
    ):

        start_index = max(
            0,
            index - 6,
        )

        window = items[
            start_index:index + 1
        ]

        rates = [
            x["attendance_rate"]
            for x in window
            if x[
                "attendance_rate"
            ] is not None
        ]

        if rates:

            item[
                "moving_avg_7d"
            ] = decimal_round(
                sum(rates)
                / len(rates),
                4,
            )

        else:

            item[
                "moving_avg_7d"
            ] = None

    return {
        "department": department,
        "items": items,
    }


# ============================================================
# ADMIN EXPLAIN
# ============================================================

def explain_find(
    collection,
    filter_query,
    sort_query,
    projection=None,
    skip=0,
    limit=20,
    hint=None,
):
    find_command = {
        "find": collection.name,
        "filter": filter_query,
        "sort": dict(sort_query),
        "skip": skip,
        "limit": limit,
    }

    if projection:
        find_command["projection"] = projection

    if hint:
        find_command["hint"] = hint

    command = {
        "explain": find_command,
        "verbosity": "executionStats",
    }

    return collection.database.command(command)


def explain_aggregate(
    collection_name: str,
    pipeline: list,
    hint=None,
):

    # Use MongoDB's explain command correctly.
    command = {
        "explain": {
            "aggregate": collection_name,
            "pipeline": pipeline,
            "cursor": {},
        },
        "verbosity": "executionStats",
    }

    if hint:
        command[
            "explain"
        ]["hint"] = hint

    return db.command(
        command
    )


# ============================================================
# ADMIN EXPLAIN
# ============================================================

@app.get(
    "/admin/explain/{endpoint}"
)
def admin_explain(
    endpoint: str,
    emp_code: Optional[str] = None,
    month: Optional[str] = None,
    department: Optional[str] = None,
    limit: int = Query(
        10,
        ge=1,
        le=50,
    ),
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    status: Optional[str] = None,
    from_: Optional[str] = Query(
        None,
        alias="from",
    ),
    to: Optional[str] = None,
):

    allowed = {
        "attendance_list",
        "employee_monthly",
        "department_summary",
        "late_leaderboard",
        "department_trend",
    }

    if endpoint not in allowed:

        raise HTTPException(
            status_code=422,
            detail="invalid endpoint",
        )

    # --------------------------------------------------------
    # attendance_list
    # --------------------------------------------------------

    if endpoint == "attendance_list":

        if date_from:

            try:
                valid_date_string(
                    date_from
                )
            except ValueError:

                raise HTTPException(
                    status_code=422,
                    detail="invalid date_from",
                )

        if date_to:

            try:
                valid_date_string(
                    date_to
                )
            except ValueError:

                raise HTTPException(
                    status_code=422,
                    detail="invalid date_to",
                )

        if (
            date_from
            and date_to
            and date_from > date_to
        ):

            raise HTTPException(
                status_code=422,
                detail="date_from must not be after date_to",
            )

        if status:
            validate_status(status)

        query = {}

        if emp_code:
            query["emp_code"] = emp_code

        if date_from or date_to:

            query["date"] = {}

            if date_from:
                query["date"][
                    "$gte"
                ] = date_from

            if date_to:
                query["date"][
                    "$lte"
                ] = date_to

        if status:
            query["status"] = status

        if emp_code:

            hint = (
                "ix_attendance_emp_punchin"
            )

        elif status:

            hint = (
                "ix_attendance_status_date_emp"
            )

        else:

            hint = (
                "ix_attendance_date_emp"
            )

        explain = explain_find(
            attendance_logs,
            query,
            [
                (
                    "date",
                    DESCENDING,
                ),
                (
                    "emp_code",
                    ASCENDING,
                ),
            ],
            {
                "_id": 0
            },
            0,
            20,
            hint,
        )

        return {
            "endpoint": endpoint,
            "collection": "attendance_logs",
            "explain": explain,
        }

    # --------------------------------------------------------
    # employee_monthly
    # --------------------------------------------------------

    if endpoint == "employee_monthly":

        if not emp_code or not month:

            raise HTTPException(
                status_code=422,
                detail="emp_code and month are required",
            )

        try:
            valid_month(month)
        except ValueError:

            raise HTTPException(
                status_code=422,
                detail="month must be YYYY-MM",
            )

        # Explain a normal MongoDB find.
        query = {
            "emp_code": emp_code,
            "date": {
                "$regex": f"^{month}-"
            },
        }

        explain = explain_find(
            attendance_logs,
            query,
            [
                (
                    "date",
                    ASCENDING,
                )
            ],
            {
                "_id": 0
            },
            0,
            20,
            "ux_attendance_emp_date",
        )

        return {
            "endpoint": endpoint,
            "collection": "attendance_logs",
            "explain": explain,
        }

    # --------------------------------------------------------
    # department_summary
    # --------------------------------------------------------

    if endpoint == "department_summary":

        if not month:

            raise HTTPException(
                status_code=422,
                detail="month is required",
            )

        try:
            valid_month(month)
        except ValueError:

            raise HTTPException(
                status_code=422,
                detail="month must be YYYY-MM",
            )

        query = {}

        if department:

            query[
                "department"
            ] = department

        explain = explain_find(
            employees,
            query,
            [
                (
                    "department",
                    ASCENDING,
                ),
                (
                    "joined_on",
                    ASCENDING,
                ),
            ],
            {
                "_id": 0
            },
            0,
            20,
            "ix_emp_department_joined",
        )

        return {
            "endpoint": endpoint,
            "collection": "employees",
            "explain": explain,
        }

    # --------------------------------------------------------
    # late_leaderboard
    # --------------------------------------------------------

    if endpoint == "late_leaderboard":

        if not month:

            raise HTTPException(
                status_code=422,
                detail="month is required",
            )

        try:
            valid_month(month)
        except ValueError:

            raise HTTPException(
                status_code=422,
                detail="month must be YYYY-MM",
            )

        query = {
            "date": {
                "$regex": f"^{month}-"
            },
            "late_minutes": {
                "$gt": 0
            },
        }

        explain = explain_find(
            attendance_logs,
            query,
            [
                (
                    "late_minutes",
                    DESCENDING,
                )
            ],
            {
                "_id": 0
            },
            0,
            limit,
            "ix_attendance_status_date_emp",
        )

        return {
            "endpoint": endpoint,
            "collection": "attendance_logs",
            "explain": explain,
        }

    # --------------------------------------------------------
    # department_trend
    # --------------------------------------------------------

    if (
        not department
        or not from_
        or not to
    ):

        raise HTTPException(
            status_code=422,
            detail="department, from and to are required",
        )

    try:

        valid_date_string(
            from_
        )

        valid_date_string(
            to
        )

    except ValueError:

        raise HTTPException(
            status_code=422,
            detail="invalid date",
        )

    start = date.fromisoformat(
        from_
    )

    end = date.fromisoformat(
        to
    )

    if end < start:

        raise HTTPException(
            status_code=422,
            detail="invalid trend range",
        )

    if (
        end - start
    ).days + 1 > 92:

        raise HTTPException(
            status_code=422,
            detail="invalid trend range",
        )

    # Safe explain using a normal find.
    explain = explain_find(
        attendance_logs,
        {
            "date": {
                "$gte": from_,
                "$lte": to,
            }
        },
        [
            (
                "date",
                ASCENDING,
            )
        ],
        {
            "_id": 0
        },
        0,
        20,
        "ix_attendance_date_emp",
    )

    return {
        "endpoint": endpoint,
        "collection": "attendance_logs",
        "explain": explain,
    }