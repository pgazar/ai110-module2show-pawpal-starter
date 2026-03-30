from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Optional
from uuid import uuid4


def _add_minutes(t: time, minutes: int) -> time:
    """Return a time offset by N minutes."""
    dt = datetime.combine(date.today(), t) + timedelta(minutes=minutes)
    return dt.time().replace(microsecond=0)


def _format_time(t: time) -> str:
    """Format a time for display."""
    return t.strftime("%-I:%M %p") if hasattr(t, "strftime") else str(t)


def format_time_range(start: time, end: time) -> str:
    """Format a start/end time range for display."""
    return f"{_format_time(start)}–{_format_time(end)}"


def _intervals_overlap(plan_date: date, a_start: time, a_end: time, b_start: time, b_end: time) -> bool:
    """
    Return whether two same-day time intervals overlap.

    Uses ``datetime`` endpoints on ``plan_date`` so comparisons are reliable.
    Two intervals overlap if each starts strictly before the other ends
    (standard overlap test for scheduling).

    Args:
        plan_date: Calendar day for both intervals.
        a_start, a_end: First interval (wall-clock times on that day).
        b_start, b_end: Second interval (wall-clock times on that day).

    Returns:
        True if the intervals overlap, False otherwise.
    """
    a0 = datetime.combine(plan_date, a_start)
    a1 = datetime.combine(plan_date, a_end)
    b0 = datetime.combine(plan_date, b_start)
    b1 = datetime.combine(plan_date, b_end)
    return a0 < b1 and b0 < a1


def _parse_hhmm(value: Optional[str]) -> time:
    """
    Parse an ``'HH:MM'`` string into ``datetime.time`` for sorting and display prep.

    Lexicographic sort on strings does not match chronological order (e.g. ``"9:00"``
    vs ``"10:00"``), so callers should parse to ``time`` (or minutes) before sorting.

    Args:
        value: A 24-hour ``'HH:MM'`` string, or None/empty.

    Returns:
        Parsed time, or ``23:59`` if missing or invalid (sorts late as a fallback).
    """
    if not value:
        return time(23, 59)
    try:
        return datetime.strptime(value.strip(), "%H:%M").time()
    except ValueError:
        return time(23, 59)


@dataclass
class Pet:
    id: str
    name: str
    species: str
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Add a task to this pet."""
        if task.pet_id != self.id:
            raise ValueError("Task.pet_id must match Pet.id")
        self.tasks.append(task)

    def remove_task(self, task_id: str) -> None:
        """Remove a task from this pet by id."""
        self.tasks = [t for t in self.tasks if t.id != task_id]

    def get_tasks(self) -> list[Task]:
        """Return a copy of this pet's tasks."""
        return list(self.tasks)


@dataclass
class AvailabilityBlock:
    id: str
    label: str
    start_time: time
    end_time: time
    capacity_minutes: int
    used_minutes: int = 0

    def remaining_minutes(self) -> int:
        """Return how many minutes remain available in this block."""
        return max(0, self.capacity_minutes - self.used_minutes)

    def allocate_minutes(self, minutes: int) -> None:
        """Consume minutes from this block's remaining capacity."""
        if minutes < 0:
            raise ValueError("minutes must be non-negative")
        if minutes > self.remaining_minutes():
            raise ValueError("Not enough remaining minutes in this block")
        self.used_minutes += minutes

    def next_start_time(self) -> time:
        """Return the next free start time within the block."""
        return _add_minutes(self.start_time, self.used_minutes)


@dataclass
class Owner:
    name: str
    pets: list[Pet] = field(default_factory=list)
    availability_blocks: list[AvailabilityBlock] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to this owner."""
        if any(p.id == pet.id for p in self.pets):
            raise ValueError(f"Pet with id {pet.id!r} already exists")
        self.pets.append(pet)

    def remove_pet(self, pet_id: str) -> None:
        """Remove a pet from this owner by id."""
        self.pets = [p for p in self.pets if p.id != pet_id]

    def add_availability_block(self, block: AvailabilityBlock) -> None:
        """Add an availability block to the owner's schedule."""
        if any(b.id == block.id for b in self.availability_blocks):
            raise ValueError(f"AvailabilityBlock with id {block.id!r} already exists")
        self.availability_blocks.append(block)

    def remove_availability_block(self, block_id: str) -> None:
        """Remove an availability block by id."""
        self.availability_blocks = [b for b in self.availability_blocks if b.id != block_id]

    def get_pet(self, pet_id: str) -> Optional[Pet]:
        """Return a pet by id, or None if not found."""
        for p in self.pets:
            if p.id == pet_id:
                return p
        return None

    def get_all_tasks(self) -> list[Task]:
        """Return all tasks across all pets."""
        tasks: list[Task] = []
        for pet in self.pets:
            tasks.extend(pet.get_tasks())
        return tasks

    def get_task(self, task_id: str) -> Optional[Task]:
        """Return a task by id across all pets, or None if not found."""
        for task in self.get_all_tasks():
            if task.id == task_id:
                return task
        return None


@dataclass
class RecurrenceRule:
    frequency: str  # "daily" | "weekly"
    times_per_day: int = 1
    days_of_week: list[str] = field(default_factory=list)  # e.g., ["Mon", "Wed", "Fri"]

    def is_active_on(self, on_date: date) -> bool:
        """Return whether this recurrence produces occurrences on the given date."""
        if self.times_per_day <= 0:
            return False
        if self.frequency == "daily":
            return True
        if self.frequency == "weekly":
            if not self.days_of_week:
                return False
            # Python: Monday=0..Sunday=6
            dow = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][on_date.weekday()]
            return dow in set(self.days_of_week)
        raise ValueError("Unsupported frequency; use 'daily' or 'weekly'")


@dataclass
class Task:
    id: str
    pet_id: str
    name: str
    category: str
    duration_minutes: int
    priority: int
    time: Optional[str] = None
    due_date: Optional[date] = None
    description: str = ""
    recurrence: Optional[RecurrenceRule] = None
    completed_dates: set[date] = field(default_factory=set)
    completed_count_by_date: dict[date, int] = field(default_factory=dict)

    def is_due_on(self, on_date: date) -> bool:
        """Return whether this task should be scheduled on the given date."""
        if self.recurrence is None:
            # One-off task: due until completed, optionally starting at due_date.
            if self.due_date is not None and on_date < self.due_date:
                return False
            return len(self.completed_dates) == 0
        if not self.recurrence.is_active_on(on_date):
            return False
        done = self.completed_count_by_date.get(on_date, 0)
        return done < self.recurrence.times_per_day

    def mark_completed(self, on_date: date) -> None:
        """Record one completion for the given date."""
        if self.recurrence is None:
            self.completed_dates.add(on_date)
            return
        self.completed_count_by_date[on_date] = self.completed_count_by_date.get(on_date, 0) + 1

    def mark_complete(self, on_date: date) -> None:
        """Alias for mark_completed to match assignment wording."""
        self.mark_completed(on_date)

    def remaining_occurrences_today(self, on_date: date) -> int:
        """Return how many more times this task should occur on the given date."""
        if self.recurrence is None:
            return 0 if on_date in self.completed_dates else 1
        if not self.recurrence.is_active_on(on_date):
            return 0
        done = self.completed_count_by_date.get(on_date, 0)
        return max(0, self.recurrence.times_per_day - done)


@dataclass
class ScheduledItem:
    pet_id: str
    task_id: str
    start_time: time
    end_time: time
    block_id: str
    reason: str = ""


@dataclass
class DailyPlan:
    """
    A schedule for one calendar day: placed items, leftovers, and optional warnings.

    ``conflict_warnings`` is filled by :meth:`Scheduler.detect_time_conflicts` (and by
    :meth:`Scheduler.generate_daily_plan` after building the plan). Warnings are
    human-readable strings; they do not block planning.
    """

    date: date
    scheduled_items: list[ScheduledItem] = field(default_factory=list)
    unscheduled_tasks: list[Task] = field(default_factory=list)
    conflict_warnings: list[str] = field(default_factory=list)

    def total_planned_minutes(self) -> int:
        """Return the total number of minutes scheduled in this plan."""
        total = 0
        for item in self.scheduled_items:
            start = datetime.combine(self.date, item.start_time)
            end = datetime.combine(self.date, item.end_time)
            total += int((end - start).total_seconds() // 60)
        return total

    def to_display_rows(self, owner: Owner) -> list[dict[str, object]]:
        """Return display-ready rows for the UI (e.g., for st.dataframe)."""
        pet_name_by_id = {p.id: p.name for p in owner.pets}
        block_label_by_id = {b.id: b.label for b in owner.availability_blocks}

        rows: list[dict[str, object]] = []
        for item in sorted(self.scheduled_items, key=lambda i: (i.start_time, i.end_time)):
            task = owner.get_task(item.task_id)
            rows.append(
                {
                    "time": format_time_range(item.start_time, item.end_time),
                    "block": block_label_by_id.get(item.block_id, item.block_id),
                    "pet": pet_name_by_id.get(item.pet_id, item.pet_id),
                    "task": task.name if task else item.task_id,
                    "category": task.category if task else "",
                    "duration_min": (
                        int(
                            (
                                datetime.combine(self.date, item.end_time)
                                - datetime.combine(self.date, item.start_time)
                            ).total_seconds()
                            // 60
                        )
                    ),
                    "priority": task.priority if task else None,
                    "reason": item.reason,
                }
            )
        return rows


class Scheduler:
    """
    Planning and task utilities: build a daily plan, sort/filter tasks, complete
    recurring work, and detect overlapping scheduled times.
    """

    def detect_time_conflicts(self, plan: DailyPlan, owner: Owner) -> list[str]:
        """
        Find overlapping scheduled intervals and return warning messages.

        Compares every unordered pair of :class:`ScheduledItem` rows on ``plan.date``.
        If two items' time ranges overlap (same pet or different pets), appends one
        warning per pair. This is intentionally lightweight: O(n²) in the number of
        scheduled items, which is fine for typical household-sized days.

        Args:
            plan: Plan whose ``scheduled_items`` are checked (same-day times).
            owner: Used to resolve pet and task names in warning text.

        Returns:
            A list of human-readable warning strings. Empty if no overlaps.
            Does not modify ``plan`` except through the caller's use of the result.
        """
        warnings: list[str] = []
        items = plan.scheduled_items
        pet_name = {p.id: p.name for p in owner.pets}

        def describe(it: ScheduledItem) -> str:
            p = pet_name.get(it.pet_id, it.pet_id)
            task = owner.get_task(it.task_id)
            tname = task.name if task else it.task_id
            tr = format_time_range(it.start_time, it.end_time)
            return f"{p}: {tname} ({tr})"

        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                a, b = items[i], items[j]
                if _intervals_overlap(plan.date, a.start_time, a.end_time, b.start_time, b.end_time):
                    warnings.append(
                        "Warning: overlapping tasks — "
                        f"{describe(a)} and {describe(b)}; "
                        "the owner likely cannot run both at the same time."
                    )
        return warnings

    def sort_by_time(self, tasks: list[Task]) -> list[Task]:
        """
        Return a new list of tasks sorted by preferred time-of-day.

        Sort key is ``(parsed_time, task_name)``: ``Task.time`` is parsed as
        ``'HH:MM'`` via :func:`_parse_hhmm`, then ties break on ``Task.name``.
        Tasks without a valid time sort near the end (parser fallback).

        Args:
            tasks: Tasks to sort (input list is not mutated).

        Returns:
            New list sorted chronologically by ``time``, then by name.
        """
        return sorted(tasks, key=lambda t: (_parse_hhmm(t.time), t.name))

    def filter_tasks(
        self,
        owner: Owner,
        tasks: list[Task],
        *,
        on_date: date,
        completed: Optional[bool] = None,
        pet_name: Optional[str] = None,
    ) -> list[Task]:
        """
        Return tasks matching optional pet name and/or completion state on ``on_date``.

        Pet matching is case-insensitive exact match on the owner's pet name.
        Completion uses :meth:`Task.is_due_on`: if a task is not due on ``on_date``,
        it is treated as completed for that day for filtering purposes.

        Args:
            owner: Supplies pet id → name mapping.
            tasks: Candidate tasks (usually ``owner.get_all_tasks()``).
            on_date: Day used for due/completed checks.
            completed: If True, keep only tasks not due (done for that day).
                If False, keep only tasks still due. If None, ignore completion.
            pet_name: If set, keep only tasks for the pet with this name.

        Returns:
            New list of tasks matching all provided filters.
        """
        pet_name_by_id = {p.id: p.name for p in owner.pets}
        pet_name_norm = pet_name.strip().lower() if pet_name else None

        filtered: list[Task] = []
        for task in tasks:
            if pet_name_norm is not None:
                name = pet_name_by_id.get(task.pet_id, "")
                if name.lower() != pet_name_norm:
                    continue

            if completed is not None:
                is_completed = not task.is_due_on(on_date)
                if completed != is_completed:
                    continue

            filtered.append(task)

        return filtered

    def mark_task_complete(self, owner: Owner, task_id: str, on_date: date) -> Optional[Task]:
        """
        Record completion and roll recurring tasks forward to a new task instance.

        Always calls :meth:`Task.mark_complete` for the given task and date.
        For recurring tasks, after all required occurrences that day are satisfied,
        appends a **new** :class:`Task` on the same pet with the same rule and a
        ``due_date`` of the next occurrence:

        - **daily:** ``on_date + timedelta(days=1)``
        - **weekly:** ``on_date + timedelta(days=7)``

        The previous task row is turned into a one-off completed task so it does
        not reappear on later days.

        Args:
            owner: Owner whose pets/tasks are updated.
            task_id: Id of the task to complete.
            on_date: Calendar day of the completion.

        Returns:
            The newly created :class:`Task` if a next instance was added; otherwise None
            (one-off task, missing task/pet, or recurrence not finished for that day).
        """
        task = owner.get_task(task_id)
        if task is None:
            return None

        # Record completion first (supports times_per_day > 1)
        task.mark_complete(on_date)

        if task.recurrence is None:
            return None

        # Only spawn the next instance when today's required occurrences are done.
        if task.remaining_occurrences_today(on_date) > 0:
            return None

        if task.recurrence.frequency == "daily":
            next_due = on_date + timedelta(days=1)
        elif task.recurrence.frequency == "weekly":
            next_due = on_date + timedelta(days=7)
        else:
            return None

        pet = owner.get_pet(task.pet_id)
        if pet is None:
            return None

        next_task = Task(
            id=f"{task.id}-next-{uuid4().hex[:8]}",
            pet_id=task.pet_id,
            name=task.name,
            description=task.description,
            category=task.category,
            time=task.time,
            due_date=next_due,
            duration_minutes=task.duration_minutes,
            priority=task.priority,
            recurrence=task.recurrence,
        )

        # Convert the current task into a completed one-off so it won't reappear tomorrow.
        task.recurrence = None
        task.completed_dates.add(on_date)

        pet.add_task(next_task)
        return next_task

    def generate_daily_plan(
        self,
        owner: Owner,
        tasks: list[Task],
        on_date: date,
    ) -> DailyPlan:
        """
        Build a :class:`DailyPlan` by greedily packing due tasks into availability blocks.

        Due tasks are expanded for ``times_per_day``, ordered by priority (higher first)
        then shorter duration, then name. Each task is placed in the first block with
        enough remaining minutes; otherwise it is listed in ``unscheduled_tasks``.

        After scheduling, sets ``plan.conflict_warnings`` from
        :meth:`detect_time_conflicts` (overlap detection only; does not remove items).

        Args:
            owner: Availability blocks and pets (blocks are copied per call).
            tasks: Task templates to consider (typically all tasks).
            on_date: Which day to plan for.

        Returns:
            ``DailyPlan`` with ``scheduled_items``, ``unscheduled_tasks``, and
            ``conflict_warnings`` populated.
        """
        plan = DailyPlan(date=on_date)

        # Reset daily usage on blocks (simple approach for a per-day plan)
        blocks = [
            AvailabilityBlock(
                id=b.id,
                label=b.label,
                start_time=b.start_time,
                end_time=b.end_time,
                capacity_minutes=b.capacity_minutes,
                used_minutes=0,
            )
            for b in owner.availability_blocks
        ]

        # Expand tasks into "units" based on recurrence times-per-day
        units: list[Task] = []
        for task in tasks:
            if not task.is_due_on(on_date):
                continue
            for _ in range(task.remaining_occurrences_today(on_date)):
                units.append(task)

        # Greedy strategy: highest priority first, then shorter tasks first (packs better)
        units.sort(key=lambda t: (-t.priority, t.duration_minutes, t.name))

        for task in units:
            scheduled = False
            for block in blocks:
                if task.duration_minutes <= block.remaining_minutes():
                    start = block.next_start_time()
                    end = _add_minutes(start, task.duration_minutes)
                    block.allocate_minutes(task.duration_minutes)
                    plan.scheduled_items.append(
                        ScheduledItem(
                            pet_id=task.pet_id,
                            task_id=task.id,
                            start_time=start,
                            end_time=end,
                            block_id=block.id,
                            reason=f"Scheduled because priority={task.priority} and it fit in '{block.label}'.",
                        )
                    )
                    scheduled = True
                    break
            if not scheduled:
                plan.unscheduled_tasks.append(task)

        plan.conflict_warnings = self.detect_time_conflicts(plan, owner)
        return plan

