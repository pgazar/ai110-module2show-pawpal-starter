# PawPal+ — UML Class Diagram (Final)

```mermaid
classDiagram
  class Owner {
    +String name
    +int available_minutes
    +__post_init__() None
  }

  class Pet {
    +String name
    +String species
    +Owner owner
    +List~Task~ tasks
    +add_task(task) None
    +task_count() int
    +__post_init__() None
  }

  class Task {
    +String title
    +int duration_minutes
    +String priority
    +String notes
    +bool completed
    +int preferred_time
    +String pet_name
    +String frequency
    +date due_date
    +priority_rank() int
    +mark_complete() Task
    +to_dict() dict
    +from_dict(d) Task
    +__post_init__() None
  }

  class ScheduledTask {
    +Task task
    +int start_minute
    +end_minute() int
    +start_time_str() str
    +end_time_str() str
  }

  class DailyPlan {
    +Pet pet
    +List~ScheduledTask~ scheduled
    +List~Task~ skipped
    +List~str~ reasoning
    +total_minutes() int
  }

  class Scheduler {
    +Pet pet
    +List~Task~ tasks
    +Owner owner
    +int available
    +int day_start_minute
    +sort_by_priority() List~Task~
    +sort_by_time() List~Task~
    +filter_by_completion(completed) List~Task~
    +filter_by_pet(pet_name) List~Task~
    +detect_conflicts(scheduled_tasks) List~str~
    +build_plan(sort_mode) DailyPlan
  }

  Owner "1" --o "0..*" Pet : owns
  Task "1" --* "1" ScheduledTask : wrapped by
  ScheduledTask "0..*" --* "1" DailyPlan : scheduled in
  Task "0..*" --o "1" DailyPlan : skipped in
  DailyPlan "1" --o "1" Pet : plans for
  Scheduler "1" --> "1" DailyPlan : produces
  Scheduler "1" --> "0..*" Task : sorts and filters
  Scheduler "1" --> "0..*" ScheduledTask : detects conflicts
  Task "0..*" --o "1" Pet : assigned to
```

## Relationship key

| Notation | Meaning |
|---|---|
| `--*` | Composition — the child cannot exist without the parent |
| `--o` | Aggregation — the child exists independently and is referenced |
| `-->` | Association — one class uses another directly |

## What changed from Phase 1 to final

| Change | Reason |
|---|---|
| `scheduler` module → `Scheduler` class | Sorting, filtering, and conflict detection required state and multiple methods |
| `Task` gained `completed`, `frequency`, `due_date`, `preferred_time`, `pet_name` | Recurrence, multi-pet support, and time-based sorting required new fields |
| `Task.mark_complete()` returns `Optional[Task]` | Recurring tasks spawn a new instance via `timedelta` |
| `Pet` gained `tasks`, `add_task()`, `task_count()` | Pets now own their personal task lists directly |
| `Scheduler.sort_by_time()` added | Second sort mode using lambda key on `preferred_time` integer |
| `Scheduler.filter_by_completion()` + `filter_by_pet()` added | Non-mutating filter methods for UI task list display |
| `Scheduler.detect_conflicts()` added | Lightweight O(n²) overlap check returning plain-English warning strings |
| Module-level `build_plan()` kept as thin wrapper | Backwards compatibility — `app.py` and tests import it unchanged |
