from __future__ import annotations

from datetime import date

from pawpal_system import Pet, Task


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

