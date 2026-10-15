# HROne Attendance API

A FastAPI-based Employee Attendance and Analytics API using MongoDB.

## Features

- Employee management
- Punch-in and punch-out
- Attendance listing with filters and pagination
- Attendance regularization with history
- Monthly employee attendance analytics
- Department attendance summary
- Late-coming leaderboard
- Department attendance trend
- MongoDB query explain endpoint
- Automated API tests using pytest

## Tech Stack

- Python
- FastAPI
- MongoDB
- PyMongo
- Pydantic
- Pytest
- Uvicorn

## Project Structure

```text
candidate_kit/
├── app/
│   ├── __init__.py
│   └── main.py
├── sample_data/
│   ├── attendance_logs.json
│   └── employees.json
├── tests/
│   └── test_main.py
├── DATA_MODEL.md
├── DECISIONS.md
├── REVIEW.md
├── openapi.yaml
├── requirements.txt
└── sample_seed.py

Setup
Create a virtual environment:
python -m venv .venv

Activate it on Windows:
.venv\Scripts\Activate.ps1

Install the dependencies:
python -m pip install -r requirements.txt

Make sure MongoDB is running and configure the required MongoDB connection settings.
Load the sample data:
python sample_seed.py

Start the API:
uvicorn app.main:app --port 8000

For development with automatic reload:
uvicorn app.main:app --port 8000 --reload

API Documentation
After starting the server, open:
http://127.0.0.1:8000/docs

The OpenAPI contract is available in:
openapi.yaml

Testing
Run the automated tests:
python -m pytest -v

Local test result:
9 passed

Main API Areas
Attendance
- Create employee
- Punch in
- Punch out
- List attendance records
- Regularize attendance
Analytics
- Employee monthly attendance
- Department summary
- Late-coming leaderboard
- Department attendance trend
Admin
- Attendance query explanation using MongoDB explain
Database
The application uses MongoDB to store employee and attendance information.
Attendance records are uniquely identified by:
emp_code + date

Attendance regularization maintains a history of changes for auditability.
Testing Summary
The project was tested using pytest. All 9 implemented API tests passed successfully.
The tests cover:
- Root endpoint
- Employee creation
- Punch-in
- Attendance listing
- Employee monthly analytics
- Department summary
- Late leaderboard
- Department trend
- Admin attendance explain endpoint
Repository
GitHub:
https://github.com/Nasrin-Code/HROne_Attendance_API