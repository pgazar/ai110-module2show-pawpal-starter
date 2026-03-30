from __future__ import annotations

from datetime import date, time, timedelta

from pawpal_system import (
    DailyPlan,
    Owner,
    Pet,
    RecurrenceRule,
    ScheduledItem,
    Scheduler,
    Task,
)


def test_task_completion_marks_task_complete_for_one_off_task() -> None:
    today = date.today()
    task = Task(
        id="t1",
        pet_id="p1",
        name="One-off vet call",
        category="admin",
        duration_minutes=10,
        priority=3,
    )

    assert task.is_due_on(today) is True
    task.mark_complete(today)
    assert task.is_due_on(today) is False


def test_task_addition_increases_pet_task_count() -> None:
    pet = Pet(id="p1", name="Bella", species="Dog")
    assert len(pet.get_tasks()) == 0

    pet.add_task(
        Task(
            id="t1",
            pet_id="p1",
            name="Walk",
            category="walk",
            duration_minutes=30,
            priority=5,
        )
    )

    assert len(pet.get_tasks()) == 1


def test_sort_by_time_returns_tasks_in_chronological_order() -> None:
    scheduler = Scheduler()
    tasks = [
        Task(
            id="t-late",
            pet_id="p1",
            name="Z last by name tie",
            category="care",
            duration_minutes=5,
            priority=1,
            time="14:00",
        ),
        Task(
            id="t-early",
            pet_id="p1",
            name="Morning",
            category="care",
            duration_minutes=5,
            priority=1,
            time="07:30",
        ),
        Task(
            id="t-mid",
            pet_id="p1",
            name="Noon",
            category="care",
            duration_minutes=5,
            priority=1,
            time="09:00",
        ),
    ]

    sorted_tasks = scheduler.sort_by_time(tasks)

    assert [t.time for t in sorted_tasks] == ["07:30", "09:00", "14:00"]


def test_sort_by_time_breaks_ties_by_task_name() -> None:
    scheduler = Scheduler()
    tasks = [
        Task(
            id="b",
            pet_id="p1",
            name="Beta",
            category="care",
            duration_minutes=5,
            priority=1,
            time="10:00",
        ),
        Task(
            id="a",
            pet_id="p1",
            name="Alpha",
            category="care",
            duration_minutes=5,
            priority=1,
            time="10:00",
        ),
    ]

    sorted_tasks = scheduler.sort_by_time(tasks)

    assert [t.name for t in sorted_tasks] == ["Alpha", "Beta"]


def test_mark_daily_recurring_complete_spawns_next_day_task() -> None:
    on_date = date(2026, 3, 30)
    pet = Pet(id="pet-1", name="Bella", species="dog")
    daily_rule = RecurrenceRule(frequency="daily", times_per_day=1)
    recurring = Task(
        id="feed-daily",
        pet_id="pet-1",
        name="Feed",
        category="food",
        duration_minutes=10,
        priority=5,
        time="08:00",
        recurrence=daily_rule,
    )
    pet.add_task(recurring)

    owner = Owner(name="Alex")
    owner.add_pet(pet)
    scheduler = Scheduler()

    new_task = scheduler.mark_task_complete(owner, "feed-daily", on_date)

    assert new_task is not None
    assert new_task.due_date == on_date + timedelta(days=1)
    assert new_task.recurrence is not None
    assert new_task.recurrence.frequency == "daily"

    original = owner.get_task("feed-daily")
    assert original is not None
    assert original.recurrence is None
    assert on_date in original.completed_dates

    pet_tasks = pet.get_tasks()
    assert any(t.id == new_task.id for t in pet_tasks)


def test_detect_time_conflicts_flags_overlapping_scheduled_items() -> None:
    plan_date = date(2026, 3, 30)
    owner = Owner(name="Alex")
    owner.add_pet(Pet(id="p1", name="Bella", species="dog"))
    owner.add_pet(Pet(id="p2", name="Milo", species="cat"))

    plan = DailyPlan(date=plan_date)
    # Identical windows — duplicate / overlapping times.
    plan.scheduled_items = [
        ScheduledItem(
            pet_id="p1",
            task_id="t-a",
            start_time=time(9, 0),
            end_time=time(9, 30),
            block_id="b1",
        ),
        ScheduledItem(
            pet_id="p2",
            task_id="t-b",
            start_time=time(9, 0),
            end_time=time(9, 30),
            block_id="b1",
        ),
    ]

    scheduler = Scheduler()
    warnings = scheduler.detect_time_conflicts(plan, owner)

    assert len(warnings) == 1
    assert "overlapping" in warnings[0].lower()
    assert "09:00" in warnings[0] or "9:00" in warnings[0]

