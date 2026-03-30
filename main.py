from __future__ import annotations

from datetime import date, time

from pawpal_system import (
    AvailabilityBlock,
    Owner,
    Pet,
    RecurrenceRule,
    ScheduledItem,
    Scheduler,
    Task,
)


def build_sample_owner() -> Owner:
    owner = Owner(name="Alex")

    owner.add_availability_block(
        AvailabilityBlock(
            id="morning",
            label="Morning (before work)",
            start_time=time(8, 0),
            end_time=time(9, 30),
            capacity_minutes=90,
        )
    )
    owner.add_availability_block(
        AvailabilityBlock(
            id="lunch",
            label="Lunch break",
            start_time=time(12, 0),
            end_time=time(12, 30),
            capacity_minutes=30,
        )
    )
    owner.add_availability_block(
        AvailabilityBlock(
            id="evening",
            label="Evening",
            start_time=time(18, 0),
            end_time=time(19, 0),
            capacity_minutes=60,
        )
    )

    return owner


def main() -> None:
    today = date.today()

    owner = build_sample_owner()

    pet1 = Pet(id="p1", name="Bella", species="Dog")
    pet2 = Pet(id="p2", name="Milo", species="Cat")
    owner.add_pet(pet1)
    owner.add_pet(pet2)

    walk_rule = RecurrenceRule(frequency="daily", times_per_day=2)
    groom_rule = RecurrenceRule(frequency="weekly", days_of_week=["Sat"], times_per_day=1)

    pet1.add_task(
        Task(
            id="t1",
            pet_id="p1",
            name="Walk",
            description="A brisk walk around the neighborhood.",
            category="walk",
            time="12:30",
            duration_minutes=30,
            priority=5,
            recurrence=walk_rule,
        )
    )
    pet1.add_task(
        Task(
            id="t2",
            pet_id="p1",
            name="Brush coat",
            description="Quick brushing session to reduce shedding.",
            category="grooming",
            time="09:00",
            duration_minutes=15,
            priority=2,
            recurrence=groom_rule,
        )
    )
    pet2.add_task(
        Task(
            id="t3",
            pet_id="p2",
            name="Play time",
            description="Interactive play with a wand toy.",
            category="enrichment",
            time="18:30",
            duration_minutes=20,
            priority=4,
            recurrence=RecurrenceRule(frequency="daily", times_per_day=1),
        )
    )
    pet2.add_task(
        Task(
            id="t4",
            pet_id="p2",
            name="Give meds",
            description="Daily medication with a treat.",
            category="meds",
            time="08:10",
            duration_minutes=5,
            priority=5,
            recurrence=RecurrenceRule(frequency="daily", times_per_day=1),
        )
    )

    scheduler = Scheduler()

    # --- Sorting + filtering demo (Module 2 target features) ---
    # Add a couple more tasks out of order by time to verify sort_by_time().
    pet1.add_task(
        Task(
            id="t5",
            pet_id="p1",
            name="Evening potty break",
            description="Quick outdoor break before bed.",
            category="walk",
            time="21:30",
            duration_minutes=10,
            priority=3,
            recurrence=RecurrenceRule(frequency="daily", times_per_day=1),
        )
    )
    pet2.add_task(
        Task(
            id="t6",
            pet_id="p2",
            name="Feed dinner",
            description="Evening meal.",
            category="feeding",
            time="18:05",
            duration_minutes=5,
            priority=4,
            recurrence=RecurrenceRule(frequency="daily", times_per_day=1),
        )
    )

    # Mark one task completed for today so filtering by completion status is visible.
    # Use the scheduler method so recurring tasks spawn their next instance automatically.
    scheduler.mark_task_complete(owner, "t3", today)  # Play time

    plan = scheduler.generate_daily_plan(owner=owner, tasks=owner.get_all_tasks(), on_date=today)

    # Deliberate overlap: two tasks at the same start time (different pets) to verify conflict detection.
    plan.scheduled_items.append(
        ScheduledItem(
            pet_id="p1",
            task_id="t2",
            start_time=time(14, 0),
            end_time=time(14, 20),
            block_id="lunch",
            reason="Demo: overlaps with Milo's task at the same time.",
        )
    )
    plan.scheduled_items.append(
        ScheduledItem(
            pet_id="p2",
            task_id="t6",
            start_time=time(14, 0),
            end_time=time(14, 15),
            block_id="lunch",
            reason="Demo: overlaps with Bella's task at the same time.",
        )
    )
    plan.conflict_warnings = scheduler.detect_time_conflicts(plan, owner)

    print("\nSort tasks by time (HH:MM)")
    print("=" * 26)
    due_today = [t for t in owner.get_all_tasks() if t.is_due_on(today)]
    for t in scheduler.sort_by_time(due_today):
        pet = owner.get_pet(t.pet_id)
        pet_label = pet.name if pet else t.pet_id
        due = t.due_date.isoformat() if t.due_date else "today"
        print(f"- {t.time or '--:--'}  {pet_label}: {t.name} (due {due})")

    print("\nFilter: Bella's pending tasks")
    print("=" * 29)
    for t in scheduler.filter_tasks(owner, owner.get_all_tasks(), on_date=today, completed=False, pet_name="Bella"):
        print(f"- {t.time or '--:--'}  {t.name}")

    print("\nFilter: completed tasks (today)")
    print("=" * 31)
    for t in scheduler.filter_tasks(owner, owner.get_all_tasks(), on_date=today, completed=True):
        pet = owner.get_pet(t.pet_id)
        pet_label = pet.name if pet else t.pet_id
        print(f"- {pet_label}: {t.name}")

    print("\nSchedule conflicts (warnings)")
    print("=" * 28)
    if plan.conflict_warnings:
        for w in plan.conflict_warnings:
            print(w)
    else:
        print("(none)")

    print("\nToday's Schedule")
    print("=" * 16)

    rows = plan.to_display_rows(owner)
    if not rows:
        print("No tasks scheduled for today.")
    else:
        for r in rows:
            print(f"- {r['time']}  [{r['block']}]")
            print(f"  {r['pet']}: {r['task']} ({r['category']}, {r['duration_min']} min, priority={r['priority']})")
            if r["reason"]:
                print(f"  Reason: {r['reason']}")

    if plan.unscheduled_tasks:
        print("\nUnscheduled tasks")
        print("=" * 16)
        for t in plan.unscheduled_tasks:
            print(f"- {t.name} (pet_id={t.pet_id}, {t.duration_minutes} min, priority={t.priority})")


if __name__ == "__main__":
    main()

