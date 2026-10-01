# Conversation Design

All college details below are **sample data** for a fictional "Demo Campus". Replace them with
your own values when building the assistant.

## Assistant persona

CampusBot is friendly, short and clear. It answers in 1-3 sentences and always tells the
student what it can help with when it does not understand.

## Actions

| # | Action name | Type | Example phrases | Response |
|---|-------------|------|-----------------|----------|
| 1 | Greeting | FAQ | 12 | "Hi! I'm CampusBot, the student helpdesk assistant. I can help with fees, timings, exams, hostel, placements, contacts and leave requests. What do you need?" |
| 2 | Fees Information | FAQ | 12 | "B.Tech tuition is Rs. 1,20,000 per year, payable in two installments (July and January)." |
| 3 | College Timings | FAQ | 12 | "College runs 9:00 AM to 4:30 PM, Monday to Saturday. The library is open 8:30 AM to 6:00 PM." |
| 4 | Contact Details | FAQ | 12 | "Helpdesk: helpdesk@democampus.edu | +91-00000-00000 | Admin Block, Ground Floor." |
| 5 | Exam Schedule | FAQ | 12 | "Mid exams are in week 9 and end-semester exams begin in the 2nd week of December. The official timetable is on the student portal." |
| 6 | Hostel Information | FAQ | 12 | "We have separate hostels for boys and girls with Wi-Fi and a mess. In-time is 9:00 PM. Apply at the hostel office with your admission number." |
| 7 | Placement Information | FAQ | 12 | "Training starts in the 5th semester and recruiters visit from the 6th semester. Contact the placement cell for company lists and statistics." |
| 8 | Apply for Leave | Process (API) | 12 | See flow below |
| 9 | Check Leave Status | Process (API) | 12 | See flow below |
| 10 | Goodbye | FAQ | 12 | "Thanks for chatting. Have a great day!" |
| - | Fallback (No action matches) | Built-in | - | "Sorry, I didn't get that. I can help with fees, timings, exams, hostel, placements, contact details and leave requests." After two misses, offer the helpdesk contact details. |

Training data: `assistant/intents.csv` (all phrases) and `assistant/example_phrases/*.csv` (one file per action).
Held-out test data: `scripts/test_utterances.csv` (30 phrases the assistant is **not** trained on).

## Flow: Apply for Leave

1. Ask: "What is your student ID?"
2. Ask: "How many days of leave do you need?" (whole number, 1-30)
3. Ask: "From which date? (YYYY-MM-DD)"
4. Ask: "What is the reason?"
5. Confirm: "Submit a {days}-day leave from {date} for {reason}?" (Yes / No)
6. If Yes -> call `createLeaveRequest` (custom extension).
7. Respond by status:
   - `APPROVED`: "Your leave is approved. Request ID: {request_id}."
   - `PENDING_HOD_APPROVAL`: "Your request {request_id} has been sent to the HOD for approval."
   - `ESCALATED`: "Request {request_id} needs HOD approval and supporting documents. Please contact the helpdesk."
8. If the call fails -> apologise and show the helpdesk contact.

## Flow: Check Leave Status

1. Ask: "Please share your leave request ID (for example LR-0001)."
2. Call `getLeaveRequest`.
3. Respond: "Request {request_id}: {status}. {remarks}"
4. 404 -> "I couldn't find that request ID. Please check it and try again."

## Design decisions

- Phrases are written the way students actually type: short, informal, sometimes incomplete.
- Similar actions (Fees vs Hostel, Apply vs Check leave) use clearly different vocabulary in
  their examples to reduce confusion between them.
- Business rules live in the backend, not in the chatbot, so they can change without retraining.
