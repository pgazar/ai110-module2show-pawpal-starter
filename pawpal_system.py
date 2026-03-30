from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Optional


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
    description: str = ""
    recurrence: Optional[RecurrenceRule] = None
    completed_dates: set[date] = field(default_factory=set)
    completed_count_by_date: dict[date, int] = field(default_factory=dict)

    def is_due_on(self, on_date: date) -> bool:
        """Return whether this task should be scheduled on the given date."""
        if self.recurrence is None:
            # One-off task: due until completed
            return on_date not in self.completed_dates
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
    date: date
    scheduled_items: list[ScheduledItem] = field(default_factory=list)
    unscheduled_tasks: list[Task] = field(default_factory=list)

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
    def generate_daily_plan(
        self,
        owner: Owner,
        tasks: list[Task],
        on_date: date,
    ) -> DailyPlan:
        """Generate a daily plan by fitting due tasks into availability blocks."""
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

        return plan

