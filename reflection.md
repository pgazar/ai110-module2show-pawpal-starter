# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

- Briefly describe your initial UML design.
- What classes did you include, and what responsibilities did you assign to each?
- Classes and responsibilities:
  - `Owner`: represents the person using the app. Stores the owner’s `pets` and their daily `availability_blocks` (time windows like “before work” or “evening”). Provides methods to manage pets and availability.
  - `Pet`: represents each pet the owner cares for (basic identity like name/species). Used to group tasks and generate a plan across multiple pets.
  - `Task`: represents a single care task (walk/feeding/meds/grooming/enrichment) with the minimum scheduling info: `duration_minutes` and `priority`. Each task belongs to a specific pet via `pet_id` and can optionally repeat using a recurrence rule.
  - `RecurrenceRule`: defines when a task repeats (daily/weekly and optional `times_per_day` / `days_of_week`). This lets the system decide whether a task is due “today” without the user re-entering it.
  - `AvailabilityBlock`: represents a time window with a limited capacity of minutes. The scheduler uses these blocks as the “bins” to place tasks into realistic parts of the day.
  - `ScheduledItem`: one scheduled instance in today’s plan (links a `task_id` and `pet_id` to a chosen start/end time and a `block_id`, plus a short `reason` string for explainability).
  - `DailyPlan`: the output object for a specific date. Holds the `scheduled_items` (what fits) and `unscheduled_tasks` (what didn’t fit), plus summary helpers like `total_planned_minutes()`.
  - `Scheduler`: the planning engine. It takes the owner’s availability blocks + the set of tasks due on a date, then produces a `DailyPlan` by prioritizing tasks and fitting them into available time.
- Core user actions (from the scenario):
  - The user can enter basic owner + pet information (so plans can match the pet’s needs and the owner’s routine/preferences).
  - The user can add and edit pet care tasks (at minimum: duration and priority) and optionally set recurrence/cadence (for example: “walk 2x/day” or “groom weekly”) so tasks auto-populate without re-entry.
  - The user can define owner availability blocks (for example: before work, lunch, evening) so the scheduler places tasks into realistic time windows.
  - The user can generate and view today’s care plan/schedule based on constraints (time available, priorities, preferences) and see a short explanation of why tasks were chosen/ordered.

**b. Design changes**

- Did your design change during implementation?
- If yes, describe at least one change and why you made it.
- Changes after reviewing the skeleton (`pawpal_system.py`):
  - Added `Owner.pets` and pet management method stubs so the code matches the real-world relationship “Owner has Pets” (instead of passing pets around separately everywhere).
  - Updated `Scheduler.generate_daily_plan(...)` to rely on the pets stored on the `Owner`, which reduces parameter passing and keeps the main relationship model consistent.
  - Added `AvailabilityBlock.used_minutes` and a planned `allocate_minutes(...)` method stub, because `remaining_minutes()` would otherwise need external context (which can become a logic bottleneck once tasks are being placed into blocks).
  - Kept `RecurrenceRule` as a separate class (instead of baking recurrence fields directly into `Task`) so “is this task due today?” logic stays reusable and testable, especially for weekly schedules and “2x/day” style tasks.
  - Introduced `DailyPlan` + `ScheduledItem` to separate **planning output** from **task definitions**: tasks are templates, while scheduled items represent what actually got placed on a specific day (with time + a short `reason` for explainability). This makes the UI display and tests cleaner.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
