from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, time
from typing import Optional


@dataclass
class AvailabilityBlock:
    id: str
    label: str
    start_time: time
    end_time: time
    capacity_minutes: int

    def remaining_minutes(self) -> int:
        raise NotImplementedError


@dataclass
class Owner:
    name: str
    availability_blocks: list[AvailabilityBlock] = field(default_factory=list)

    def add_availability_block(self, block: AvailabilityBlock) -> None:
        raise NotImplementedError

    def remove_availability_block(self, block_id: str) -> None:
        raise NotImplementedError


@dataclass
class Pet:
    id: str
    name: str
    species: str


@dataclass
class RecurrenceRule:
    frequency: str  # "daily" | "weekly"
    times_per_day: int = 1
    days_of_week: list[str] = field(default_factory=list)  # e.g., ["Mon", "Wed", "Fri"]

    def is_active_on(self, on_date: date) -> bool:
        raise NotImplementedError


@dataclass
class Task:
    id: str
    pet_id: str
    name: str
    category: str
    duration_minutes: int
    priority: int
    recurrence: Optional[RecurrenceRule] = None

    def is_due_on(self, on_date: date) -> bool:
        raise NotImplementedError


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
        raise NotImplementedError


class Scheduler:
    def generate_daily_plan(
        self,
        owner: Owner,
        pets: list[Pet],
        tasks: list[Task],
        on_date: date,
    ) -> DailyPlan:
        raise NotImplementedError

