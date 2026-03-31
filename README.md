# 🐾 PawPal+

A Streamlit app that helps a busy pet owner plan daily care tasks for one or more pets — considering time constraints, task priorities, and preferred schedules.

---

## 📸 Demo

<a href="/course_images/ai110/pawpal_screenshot.png" target="_blank">
  <img src='/course_images/ai110/pawpal_screenshot.png' title='PawPal App' width='' alt='PawPal App' class='center-block' />
</a>

---

## ✨ Features

### Core planning
- **Owner + multi-pet setup** — enter your name, daily time budget, and day start hour; add as many pets as you need, each with a name and species
- **Per-pet task lists** — each task is assigned to a specific pet; switching the pet selector in the Tasks section instantly shows that pet's tasks
- **Quick-add presets** — one-click buttons for the eight most common care tasks (walk, feeding, medication, grooming, enrichment toy, vet appointment, bath, nail trim)
- **Custom task form** — add any task with a title, duration, priority (low / medium / high), and optional notes
- **Edit and delete** — every task can be updated or removed at any time

### Smarter scheduling algorithms
- **Greedy scheduler** — `Scheduler.build_plan()` sorts tasks, fits as many as possible into the owner's time budget, and records a plain-English reason for every include or skip decision
- **Sorting by priority** — `sort_by_priority()` uses `lambda t: (-t.priority_rank, t.duration_minutes)` to place high-priority tasks first, with shortest-duration as the tiebreaker so more tasks fit
- **Sorting by time** — `sort_by_time()` uses `lambda t: t.preferred_time` to place tasks in chronological order by preferred start time; tasks with no time preference fall to the end, ordered by priority
- **Two sort modes in the UI** — a radio button lets the owner choose "By priority" or "By preferred time" both for the task list preview and for plan generation
- **Conflict detection** — `detect_conflicts()` checks every pair of scheduled tasks for overlapping time windows using the condition `A.start < B.end AND B.start < A.end`; conflicts are shown as `st.warning` banners immediately below the build button so the owner sees them before scrolling to the schedule
- **Filtering** — `filter_by_completion()` and `filter_by_pet()` let the scheduler show only pending or done tasks, or only one pet's tasks, without modifying the underlying list

### Recurring tasks
- Each `Task` has a `frequency` field: `"once"`, `"daily"`, or `"weekly"`
- When `mark_complete()` is called on a recurring task, it automatically returns a new `Task` instance for the next occurrence using Python's `timedelta`:
  - Daily → `due_date + timedelta(days=1)`
  - Weekly → `due_date + timedelta(days=7)`
- The follow-up task inherits all attributes (title, priority, preferred time, pet name) but starts with `completed=False`

### Saved plans
- Every plan is auto-saved to session state under the pet's name the moment it is built
- The **Saved Plans** section displays one tab per pet — switch between Mochi's plan and Pepper's plan instantly without rebuilding
- Rebuilding a plan for the same pet overwrites the previous save
- Deleting a pet also removes their saved plan

### Transparency
- Every scheduling decision is logged in plain English in `DailyPlan.reasoning`
- The "Why this plan?" expander in the UI colour-codes each line: ✅ scheduled, ⏭️ skipped, ⚠️ conflict
- Skipped tasks are listed separately so nothing is silently dropped

---

## 🗂 Project structure

```
pawpal_system.py        # All backend logic: models + Scheduler class
app.py                  # Streamlit UI
main.py                 # CLI demo: sorting, filtering, recurrence, conflicts
tests/
  test_pawpal.py        # 61 pytest tests
uml_class_diagram.md    # Mermaid source + change log
uml_final.png           # Rendered UML diagram
reflection.md           # Design decisions and AI collaboration notes
README.md               # This file
```

---

## 🚀 Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Run the app

```bash
streamlit run app.py
```

### Run the CLI demo

```bash
python3 main.py
```

### Run the tests

```bash
python -m pytest tests/test_pawpal.py -v
```

---

## 🧱 Architecture

The backend is a single file — `pawpal_system.py` — with five dataclasses and one class:

| Class | Responsibility |
|---|---|
| `Owner` | Name + daily time budget |
| `Pet` | Name, species, optional owner, personal task list |
| `Task` | Care action with title, duration, priority, recurrence, and preferred time |
| `ScheduledTask` | A `Task` placed at a concrete start time |
| `DailyPlan` | Scheduler output: scheduled tasks, skipped tasks, reasoning |
| `Scheduler` | Sorting, filtering, conflict detection, and greedy plan building |

The module-level `build_plan()` function is a thin wrapper around `Scheduler` kept for backwards compatibility.

---

## 🧪 Tests

61 tests in `tests/test_pawpal.py` across nine test classes:

| Class | What it tests |
|---|---|
| `TestModelValidation` | Invalid inputs raise `ValueError` immediately |
| `TestBuildPlan` | Core greedy scheduling contract |
| `TestScheduledTask` | Time string formatting (AM/PM) |
| `TestSortByTime` | Chronological sort, no mutation |
| `TestFiltering` | Completion status and pet name filters |
| `TestConflictDetection` | Overlap detection edge cases |
| `TestRecurringTasks` | `timedelta` recurrence, attribute inheritance |
| `TestTaskCompletion` | `mark_complete()` flag behaviour |
| `TestPetTaskAddition` | `add_task()` / `task_count()` |
| `TestSortingCorrectness` | ✅ Checkpoint: chronological order verified |
| `TestRecurrenceLogic` | ✅ Checkpoint: daily task → next-day follow-up |
| `TestConflictFlagging` | ✅ Checkpoint: duplicate start times flagged |
