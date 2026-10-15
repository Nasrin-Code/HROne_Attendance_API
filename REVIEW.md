# REVIEW.md

| # | Where (function / line) | What is wrong | How you'd notice it (test, input, or symptom) | How you fixed it |
|---|---|---|---|---|
| 1 | Attendance calculation | Work hours, late minutes, overtime minutes, and half-day status were not handled correctly for all attendance cases. | Test punch-in and punch-out with different timestamps and compare the calculated values with the business rules. | Implemented the required attendance calculations according to the API rules. |
| 2 | Punch-in endpoint | Duplicate punch-in requests for the same employee and date need to be prevented safely. | Send two identical punch-in requests for the same employee and date. | Added the employee/date uniqueness guarantee and handled duplicate attendance records. |
| 3 | Attendance regularization | Updating an attendance record must preserve the previous values for audit purposes. | Regularize an existing record and inspect its history. | Added history entries containing the old value, new value, reason, and user making the change. |
| 4 | Analytics | Analytics must use attendance records together with employee information so department-level results are correct. | Query monthly and department analytics with employees having different attendance records. | Implemented the required aggregation and employee/headcount handling. |
| 5 | Department trend | Trend results must cover the requested date range, including dates without attendance records. | Request a trend for a month where only some dates have attendance data. | Generate the complete date range and return zero values for dates without records. |

## Not defects

I also reviewed the existing API structure, data model, OpenAPI contract, sample data, and MongoDB query behavior. The existing API responses, pagination structure, attendance history format, and MongoDB indexes were retained where they already satisfied the requirements.