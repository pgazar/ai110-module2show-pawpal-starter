from __future__ import annotations

from datetime import date, time

from pawpal_system import (
    AvailabilityBlock,
    Owner,
    Pet,
    RecurrenceRule,
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
            duration_minutes=5,
            priority=5,
            recurrence=RecurrenceRule(frequency="daily", times_per_day=1),
        )
    )

    scheduler = Scheduler()
    plan = scheduler.generate_daily_plan(owner=owner, tasks=owner.get_all_tasks(), on_date=today)

    print("Today's Schedule")
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

