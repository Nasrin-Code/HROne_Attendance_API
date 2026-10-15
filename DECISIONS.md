# DECISIONS.md

1. **Indexes.** I used a unique index on `emp_code + date` to guarantee one attendance record per employee per day. I also used an index on `emp_code + punch_in` to support attendance-list queries. I considered adding more indexes for analytics, but rejected them because the current queries and dataset do not justify the extra index-maintenance cost.

2. **Punch-in race.** If two identical punch-in requests arrive at the same time, both can initially attempt to create the same employee/date record. The unique `emp_code + date` index is the final protection. MongoDB allows only one insert and rejects the duplicate, so two attendance records cannot be created.

3. **Ties.** The leaderboard sorts employees by total late minutes and uses the requested limit. If employees are tied at the cutoff, only the employees that fall within the limit are returned. This keeps the result size deterministic instead of returning extra employees.

4. **Headcount.** The department summary starts from employees rather than only attendance logs. Therefore, employees who have no attendance records are still included in the department employee count.

5. **100x data.** I would add more targeted compound indexes and move expensive analytics to aggregation pipelines optimized for the required reports. I would also consider caching frequently requested monthly analytics.