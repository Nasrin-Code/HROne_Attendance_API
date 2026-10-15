from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_root():
    response = client.get("/")
    assert response.status_code == 200


def test_create_employee():
    employee = {
        "emp_code": "TEST001",
        "name": "Test User",
        "email": "test@example.com",
        "department": "Engineering",
        "shift_start": "09:00",
        "shift_end": "18:00",
        "joined_on": "2025-10-01",
    }

    response = client.post("/employees", json=employee)

    assert response.status_code in [201, 409]


def test_punch_in():
    employee = {
        "emp_code": "TEST002",
        "name": "Test User 2",
        "email": "test2@example.com",
        "department": "Engineering",
        "shift_start": "09:00",
        "shift_end": "18:00",
        "joined_on": "2025-10-01",
    }

    create_response = client.post("/employees", json=employee)
    assert create_response.status_code in [201, 409]

    punch_in = {
        "emp_code": "TEST002",
        "punched_at": 1760515200000,
        "status": "PRESENT",
    }

    response = client.post("/attendance/punch-in", json=punch_in)

    assert response.status_code in [201, 409]


def test_attendance_list():
    response = client.get("/attendance?page=1&page_size=20")

    assert response.status_code == 200

    data = response.json()

    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data


def test_employee_monthly_analytics():
    response = client.get(
        "/analytics/employees/EMP98611/monthly?month=2025-10"
    )

    assert response.status_code in [200, 404]


def test_department_summary():
    response = client.get(
        "/analytics/departments/summary"
        "?month=2025-10&department=Engineering"
    )

    assert response.status_code == 200

    data = response.json()

    assert "month" in data
    assert "items" in data


def test_late_leaderboard():
    response = client.get(
        "/analytics/leaderboard/late?month=2025-10&limit=10"
    )

    assert response.status_code == 200

    data = response.json()

    assert "month" in data
    assert "items" in data


def test_department_trend():
    response = client.get(
        "/analytics/departments/Engineering/trend"
        "?from=2025-10-01&to=2025-10-31"
    )

    assert response.status_code == 200

    data = response.json()

    assert "department" in data
    assert "items" in data


def test_admin_explain_attendance():
    response = client.get(
        "/admin/explain/attendance_list"
        "?emp_code=EMP98611"
        "&limit=10"
        "&date_from=2025-10-15"
        "&date_to=2025-10-15"
        "&status=PRESENT"
    )

    assert response.status_code == 200

    data = response.json()

    assert "endpoint" in data
    assert "collection" in data
    assert "explain" in data