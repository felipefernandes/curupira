## MODIFIED Requirements
### Requirement: Reminder Management
The system MUST allow value listing and deletion of scheduled reminders, presenting the pending reminders ordered ascendingly by their ID.

#### Scenario: List Reminders
1.  User asks: "Quais são meus lembretes?".
2.  System responds with a formatted, user-friendly list of PENDING reminders.
3.  The list MUST be strictly ordered by the reminder `ID` in ascending order.
4.  Each item in the list clearly separates its visual elements (ID, message, next trigger time, recurrence, and task indicators).

#### Scenario: Delete Reminder
1.  User asks: "Cancele o lembrete 1".
2.  System confirms deletion.
3.  The specific reminder does NOT fire at the scheduled time.
