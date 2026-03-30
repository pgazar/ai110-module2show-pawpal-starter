# PawPal+ Key Relationships

## Key relationships (what “has what”)

- **Owner has many Pets**
  - A single owner can manage care for multiple pets.

- **Owner defines many AvailabilityBlocks**
  - Availability blocks represent realistic windows (before work, lunch, evening) where tasks can be scheduled.

- **Pet has many Tasks**
  - Each task belongs to exactly one pet (e.g., “Bella’s morning walk”).
  - If you later add “household-wide” tasks, you can model them as tasks with no pet or a special “household” pet.

- **Task optionally has one RecurrenceRule**
  - Recurrence decides whether a task is due on a given date (daily/weekly, optional times-per-day).

- **Scheduler produces a DailyPlan**
  - The scheduler takes `Owner` (availability), `Pets`, and `Tasks`, then generates one plan for a specific day.

- **DailyPlan contains many ScheduledItems**
  - Each scheduled item references a `Task` (and therefore its `Pet`), plus the selected time and the availability block used.

- **DailyPlan also tracks unscheduled Tasks**
  - Tasks that didn’t fit inside availability blocks (or were deprioritized) are listed as unscheduled.

## Keep-it-simple choices (intentional)

- **No task dependencies** (e.g., “feed before meds”) in the initial design
- **No task splitting** (breaking long tasks into chunks) in the initial design
- **Minimal constraints model** to start (priority + duration + availability blocks + recurrence)

