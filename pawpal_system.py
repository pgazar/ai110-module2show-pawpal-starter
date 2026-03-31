"""
PawPal+ -- Backend system.
All domain models and scheduling logic live here.

Classes:  Owner, Pet, Task, ScheduledTask, DailyPlan, Scheduler
Function: build_plan()  (convenience wrapper around Scheduler)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PRIORITY_RANK: dict[str, int] = {"low": 1, "medium": 2, "high": 3}
FREQUENCY_DAYS: dict[str, int] = {"daily": 1, "weekly": 7}

DAY_START_MINUTE: int = 480  # 8:00 AM


# ---------------------------------------------------------------------------
# Domain models
# ---------------------------------------------------------------------------

@dataclass
class Owner:
    """Represents the pet owner and their available time budget for the day."""

    name: str
    available_minutes: int = 120

    def __post_init__(self) -> None:
        """Validate that name is non-empty and available_minutes is positive."""
        if self.available_minutes <= 0:
            raise ValueError("available_minutes must be positive")
        if not self.name.strip():
            raise ValueError("Owner name must not be empty")


@dataclass
class Pet:
    """Represents a pet, its species, an optional owner, and its task list."""

    name: str
    species: str
    owner: Optional[Owner] = None
    tasks: list[Task] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate that name and species are non-empty strings."""
        if not self.name.strip():
            raise ValueError("Pet name must not be empty")
        if not self.species.strip():
            raise ValueError("Species must not be empty")

    def add_task(self, task: Task) -> None:
        """Append a Task to this pet's personal task list."""
        self.tasks.append(task)

    def task_count(self) -> int:
        """Return the number of tasks currently assigned to this pet."""
        return len(self.tasks)


@dataclass
class Task:
    """
    A single pet care action.

    Attributes
    ----------
    title            : short human-readable name
    duration_minutes : estimated time to complete
    priority         : "low" | "medium" | "high"
    notes            : optional free-text detail
    completed        : True once mark_complete() has been called
    preferred_time   : preferred start in minutes from midnight (None = no preference)
    pet_name         : name of the pet this task belongs to (None = unassigned)
    frequency        : "once" | "daily" | "weekly"
    due_date         : calendar date this task is due (None = no specific date)
    """

    title: str
    duration_minutes: int
    priority: str = "medium"
    notes: str = ""
    completed: bool = False
    preferred_time: Optional[int] = None
    pet_name: Optional[str] = None
    frequency: str = "once"
    due_date: Optional[date] = None

    def __post_init__(self) -> None:
        """Validate priority, duration, title, preferred_time, and frequency."""
        if self.priority not in PRIORITY_RANK:
            raise ValueError(f"priority must be one of {list(PRIORITY_RANK)}")
        if self.duration_minutes <= 0:
            raise ValueError("duration_minutes must be positive")
        if not self.title.strip():
            raise ValueError("Task title must not be empty")
        if self.preferred_time is not None and self.preferred_time < 0:
            raise ValueError("preferred_time must be a non-negative number of minutes")
        if self.frequency not in ("once", "daily", "weekly"):
            raise ValueError("frequency must be 'once', 'daily', or 'weekly'")

    @property
    def priority_rank(self) -> int:
        """Return a numeric rank (1-3) for sorting; higher means more important."""
        return PRIORITY_RANK[self.priority]

    def mark_complete(self) -> Optional[Task]:
        """
        Mark this task as completed.

        For recurring tasks ('daily' or 'weekly') a new Task is returned
        for the next occurrence, computed with timedelta:
          - daily  → due_date + timedelta(days=1)
          - weekly → due_date + timedelta(days=7)

        Returns the next Task if recurring, else None.
        """
        self.completed = True
        if self.frequency in FREQUENCY_DAYS:
            base = self.due_date if self.due_date else date.today()
            next_due = base + timedelta(days=FREQUENCY_DAYS[self.frequency])
            return Task(
                title=self.title,
                duration_minutes=self.duration_minutes,
                priority=self.priority,
                notes=self.notes,
                completed=False,
                preferred_time=self.preferred_time,
                pet_name=self.pet_name,
                frequency=self.frequency,
                due_date=next_due,
            )
        return None

    def to_dict(self) -> dict:
        """Serialize this task to a plain dictionary for session-state storage."""
        return {
            "title": self.title,
            "duration_minutes": self.duration_minutes,
            "priority": self.priority,
            "notes": self.notes,
            "completed": self.completed,
            "preferred_time": self.preferred_time,
            "pet_name": self.pet_name,
            "frequency": self.frequency,
            "due_date": self.due_date.isoformat() if self.due_date else None,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Task":
        """Deserialize a Task from a plain dictionary (e.g. from session state)."""
        raw_date = d.get("due_date")
        return cls(
            title=d["title"],
            duration_minutes=int(d["duration_minutes"]),
            priority=d.get("priority", "medium"),
            notes=d.get("notes", ""),
            completed=d.get("completed", False),
            preferred_time=d.get("preferred_time", None),
            pet_name=d.get("pet_name", None),
            frequency=d.get("frequency", "once"),
            due_date=date.fromisoformat(raw_date) if raw_date else None,
        )


@dataclass
class ScheduledTask:
    """A Task placed at a concrete start time within a DailyPlan."""

    task: Task
    start_minute: int  # minutes from midnight (e.g. 480 = 8:00 AM)

    @property
    def end_minute(self) -> int:
        """Return the minute at which this task finishes."""
        return self.start_minute + self.task.duration_minutes

    def start_time_str(self) -> str:
        """Return the start time as a human-readable string (e.g. '8:00 AM')."""
        h, m = divmod(self.start_minute, 60)
        period = "AM" if h < 12 else "PM"
        h12 = h % 12 or 12
        return f"{h12}:{m:02d} {period}"

    def end_time_str(self) -> str:
        """Return the end time as a human-readable string (e.g. '8:30 AM')."""
        h, m = divmod(self.end_minute, 60)
        period = "AM" if h < 12 else "PM"
        h12 = h % 12 or 12
        return f"{h12}:{m:02d} {period}"


@dataclass
class DailyPlan:
    """Scheduler output: scheduled tasks, skipped tasks, and plain-English reasoning."""

    pet: Pet
    scheduled: list[ScheduledTask] = field(default_factory=list)
    skipped: list[Task] = field(default_factory=list)
    reasoning: list[str] = field(default_factory=list)

    @property
    def total_minutes(self) -> int:
        """Return the total number of minutes consumed by all scheduled tasks."""
        return sum(st.task.duration_minutes for st in self.scheduled)


# ---------------------------------------------------------------------------
# Scheduler class
# ---------------------------------------------------------------------------

class Scheduler:
    """
    Builds a greedy daily care plan for a pet and provides sorting,
    filtering, and conflict-detection helpers.

    Sorting
    -------
    sort_by_priority()   high -> low, shortest duration as tiebreaker
    sort_by_time()       earliest preferred_time first; untimed tasks at end,
                         sorted by priority. Lambda key used on preferred_time
                         integer so tasks with earlier minute values bubble up.

    Filtering
    ---------
    filter_by_completion(completed)  pending (False) or done (True) tasks
    filter_by_pet(pet_name)          tasks assigned to a named pet

    Conflict detection
    ------------------
    detect_conflicts(scheduled_tasks)
        Lightweight O(n²) overlap check. Two ScheduledTask objects conflict
        when one starts before the other ends (i.e. their time windows
        overlap). Returns a list of warning strings — never raises.
    """

    def __init__(
        self,
        pet: Pet,
        tasks: list[Task],
        owner: Owner | None = None,
        day_start_minute: int = DAY_START_MINUTE,
    ) -> None:
        """Store scheduling inputs; resolve the effective owner and time budget."""
        self.pet = pet
        self.tasks = list(tasks)          # defensive copy
        self.day_start_minute = day_start_minute
        self.owner: Owner | None = owner or pet.owner
        self.available: int = self.owner.available_minutes if self.owner else 9999

    # ── Sorting ───────────────────────────────────────────────────────────

    def sort_by_priority(self) -> list[Task]:
        """
        Sort tasks by priority desc then duration asc.

        Uses a lambda key: lambda t: (-t.priority_rank, t.duration_minutes)
        The negative sign flips priority so higher rank sorts first.
        Does not mutate self.tasks.
        """
        return sorted(
            self.tasks,
            key=lambda t: (-t.priority_rank, t.duration_minutes),
        )

    def sort_by_time(self) -> list[Task]:
        """
        Sort tasks by preferred_time asc using a lambda key on the integer
        minute value (e.g. 480 = 8:00 AM, 720 = 12:00 PM).

        Tasks whose preferred_time is None have no stated preference and go
        to the end, ordered among themselves by priority desc then duration
        asc — the same tiebreaker used in sort_by_priority().

        This is equivalent to asking: "sort these HH:MM slots earliest-first,
        putting blanks last" — the lambda key on the integer minute value is
        the most direct Pythonic way to express that comparison.

        Does not mutate self.tasks.
        """
        timed = sorted(
            [t for t in self.tasks if t.preferred_time is not None],
            key=lambda t: t.preferred_time,         # type: ignore[arg-type]
        )
        untimed = sorted(
            [t for t in self.tasks if t.preferred_time is None],
            key=lambda t: (-t.priority_rank, t.duration_minutes),
        )
        return timed + untimed

    # ── Filtering ─────────────────────────────────────────────────────────

    def filter_by_completion(self, completed: bool) -> list[Task]:
        """
        Return tasks whose completed flag matches the given value.

        Pass False for pending tasks, True for finished ones.
        """
        return [t for t in self.tasks if t.completed is completed]

    def filter_by_pet(self, pet_name: str) -> list[Task]:
        """Return tasks assigned to pet_name (case-insensitive match)."""
        return [
            t for t in self.tasks
            if (t.pet_name or "").lower() == pet_name.lower()
        ]

    # ── Conflict detection ────────────────────────────────────────────────

    def detect_conflicts(
        self, scheduled_tasks: list[ScheduledTask]
    ) -> list[str]:
        """
        Detect overlapping time windows in a list of ScheduledTask objects.

        Strategy (lightweight, no crash):
        - Compare every pair (i, j) with i < j.
        - Two tasks overlap when one starts before the other ends:
              A.start < B.end  AND  B.start < A.end
        - Collect a plain-English warning for each conflict found.
        - Return the list of warnings (empty = no conflicts).

        This is O(n²) which is fine for daily care plans (typically < 20
        tasks). It returns warnings rather than raising so callers can
        decide how to surface the information.
        """
        warnings: list[str] = []
        for i in range(len(scheduled_tasks)):
            for j in range(i + 1, len(scheduled_tasks)):
                a = scheduled_tasks[i]
                b = scheduled_tasks[j]
                if a.start_minute < b.end_minute and b.start_minute < a.end_minute:
                    warnings.append(
                        f"CONFLICT: '{a.task.title}' "
                        f"({a.start_time_str()}–{a.end_time_str()}) overlaps "
                        f"'{b.task.title}' "
                        f"({b.start_time_str()}–{b.end_time_str()})"
                    )
        return warnings

    # ── Plan builder ──────────────────────────────────────────────────────

    def build_plan(self, sort_mode: str = "priority") -> DailyPlan:
        """
        Build and return a DailyPlan using the chosen sort mode.

        sort_mode : "priority" (default) | "time"

        After scheduling, automatically runs detect_conflicts() and appends
        any warnings to plan.reasoning so the UI can surface them.
        """
        plan = DailyPlan(pet=self.pet)

        if not self.tasks:
            plan.reasoning.append("No tasks were provided, so the plan is empty.")
            return plan

        if sort_mode == "time":
            sorted_tasks = self.sort_by_time()
            plan.reasoning.append(
                f"Sorting {len(sorted_tasks)} task(s) by preferred time "
                "(earliest first), then by priority for tasks with no time preference."
            )
        else:
            sorted_tasks = self.sort_by_priority()
            plan.reasoning.append(
                f"Sorting {len(sorted_tasks)} task(s) by priority (high -> low), "
                "then by shortest duration first so we fit as many as possible."
            )

        if self.owner:
            plan.reasoning.append(
                f"Time budget for {self.owner.name}: {self.available} minute(s)."
            )

        time_used: int = 0
        current_minute: int = self.day_start_minute

        for task in sorted_tasks:
            if time_used + task.duration_minutes <= self.available:
                st = ScheduledTask(task=task, start_minute=current_minute)
                plan.scheduled.append(st)
                plan.reasoning.append(
                    f"Scheduled '{task.title}' at {st.start_time_str()} "
                    f"({task.duration_minutes} min, priority={task.priority})."
                )
                time_used += task.duration_minutes
                current_minute += task.duration_minutes
            else:
                plan.skipped.append(task)
                remaining = self.available - time_used
                plan.reasoning.append(
                    f"Skipped '{task.title}' -- needs {task.duration_minutes} min "
                    f"but only {remaining} min remain (priority={task.priority})."
                )

        # Run conflict detection on the final scheduled list
        conflicts = self.detect_conflicts(plan.scheduled)
        for warning in conflicts:
            plan.reasoning.append(f"⚠️  {warning}")

        plan.reasoning.append(
            f"Plan complete: {len(plan.scheduled)} task(s) scheduled, "
            f"{len(plan.skipped)} skipped, "
            f"{len(conflicts)} conflict(s) detected. "
            f"Total time used: {plan.total_minutes}/{self.available} min."
        )
        return plan


# ---------------------------------------------------------------------------
# Convenience wrapper (keeps app.py and existing tests unchanged)
# ---------------------------------------------------------------------------

def build_plan(
    pet: Pet,
    tasks: list[Task],
    owner: Owner | None = None,
    day_start_minute: int = DAY_START_MINUTE,
) -> DailyPlan:
    """Convenience wrapper: create a Scheduler and run build_plan('priority')."""
    return Scheduler(pet, tasks, owner, day_start_minute).build_plan("priority")
