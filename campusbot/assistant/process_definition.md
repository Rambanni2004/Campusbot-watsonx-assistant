# Process Definition: Student Leave Request

This document describes the **manual process** that CampusBot automates, written the way a
process definition (PDD) is handed to a developer in an automation project.

## 1. Current (manual) process

1. Student writes a leave application on paper or sends an email to the class coordinator.
2. Coordinator checks the number of days and forwards it to the HOD if needed.
3. HOD approves / rejects, and the coordinator informs the student.
4. The student keeps asking "was my leave approved?" because there is no single place to check.

**Pain points:** slow turnaround, no status visibility, repeated follow-up questions, no audit trail.

## 2. Automated process (CampusBot)

| Step | Actor | Automated by |
|------|-------|--------------|
| 1. Student says they want leave | Student | watsonx Assistant action **Apply for Leave** |
| 2. Collect student ID, number of days, start date, reason | Assistant | Action steps with validation |
| 3. Submit request, apply business rules, store record | Backend | `POST /leave-requests` (Flask + SQLite) |
| 4. Return request ID and status to the student | Assistant | Action response |
| 5. Student checks status any time with the request ID | Student | watsonx Assistant action **Check Leave Status** -> `GET /leave-requests/{id}` |

## 3. Business rules

| Leave duration | Outcome | Status value |
|----------------|---------|--------------|
| 1-2 days | Approved automatically | `APPROVED` |
| 3-5 days | Sent to the HOD | `PENDING_HOD_APPROVAL` |
| 6+ days (max 30) | Escalated, supporting documents required | `ESCALATED` |

## 4. Input validation

- `student_id`: 4-20 letters, digits or hyphens
- `days`: whole number, 1-30
- `from_date`: valid date, `YYYY-MM-DD`
- `reason`: 3-200 characters

## 5. Exceptions

- Invalid input -> API returns HTTP 400 with a clear message; the assistant asks the student to re-enter the value.
- Unknown request ID -> HTTP 404; the assistant tells the student the ID was not found.
- Backend unavailable -> the assistant apologises and suggests contacting the helpdesk.

## 6. Out of scope (possible future work)

HOD approval screen, email/SMS notifications, authentication against a real student database.
