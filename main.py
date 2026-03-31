"""
main.py -- Terminal demo for PawPal+ logic.

Demonstrates:
  1. Tasks added out of order (mixed priority, preferred_time, pet)
  2. sort_by_priority() using lambda key on (-priority_rank, duration_minutes)
  3. sort_by_time()     using lambda key on preferred_time integer
  4. filter_by_completion() and filter_by_pet()
  5. Recurring task auto-spawn via timedelta
  6. Conflict detection -- two tasks at the same time trigger a warning

Run: python3 main.py
"""

from datetime import date
from pawpal_system import Owner, Pet, Task, Scheduler, ScheduledTask

DIV  = "=" * 62
DIV2 = "-" * 62

# ── 1. Owner and two pets ─────────────────────────────────────────────────────

jordan = Owner(name="Jordan", available_minutes=120)
mochi  = Pet(name="Mochi",  species="dog", owner=jordan)
pepper = Pet(name="Pepper", species="cat", owner=jordan)

# ── 2. Tasks added OUT OF ORDER ───────────────────────────────────────────────

tasks = [
    Task("Enrichment toy",  duration_minutes=15, priority="low",
         preferred_time=1020, pet_name="Mochi",  frequency="once"),        # 5 PM

    Task("Morning meds",    duration_minutes=5,  priority="high",
         preferred_time=480,  pet_name="Mochi",  frequency="daily",
         due_date=date.today()),                                            # 8 AM

    Task("Afternoon groom", duration_minutes=20, priority="medium",
         preferred_time=840,  pet_name="Pepper", frequency="weekly",
         due_date=date.today()),                                            # 2 PM

    Task("Lunch feeding",   duration_minutes=10, priority="high",
         preferred_time=720,  pet_name="Mochi",  frequency="daily",
         due_date=date.today()),                                            # 12 PM

    Task("Evening walk",    duration_minutes=30, priority="high",
         preferred_time=1080, pet_name="Mochi",  frequency="daily",
         due_date=date.today()),                                            # 6 PM

    Task("Nail trim",       duration_minutes=10, priority="low",
         preferred_time=None, pet_name="Pepper", frequency="once"),        # no pref

    Task("Vet appointment", duration_minutes=60, priority="high",
         preferred_time=600,  pet_name="Pepper", frequency="once"),        # 10 AM
]

# ── Helper: pretty-print a task list ─────────────────────────────────────────

def fmt_time(mins):
    if mins is None:
        return "any time "
    h, m = divmod(mins, 60)
    period = "AM" if h < 12 else "PM"
    return f"{h % 12 or 12}:{m:02d} {period}"

def print_tasks(task_list, label):
    print(f"\n  {label} ({len(task_list)} task(s))")
    print("  " + DIV2)
    if not task_list:
        print("  (none)")
        return
    for t in task_list:
        due  = f"  due {t.due_date}" if t.due_date else ""
        done = " ✓" if t.completed else ""
        print(f"  {'✓' if t.completed else '·'} [{t.priority:<6}] "
              f"{t.title:<22} {fmt_time(t.preferred_time):<11}"
              f"pet={t.pet_name or '—':<8} freq={t.frequency}{due}{done}")

scheduler = Scheduler(pet=mochi, tasks=tasks)

# ── 3. Sorting ────────────────────────────────────────────────────────────────

print("\n" + DIV)
print("  STEP 1 & 2  --  SORTING")
print(DIV)
print("\n  sort_by_priority() key: lambda t: (-t.priority_rank, t.duration_minutes)")
print("  sort_by_time()     key: lambda t: t.preferred_time  (integers, None last)")

print_tasks(scheduler.sort_by_priority(), "Sorted by PRIORITY (high → low, shortest first)")
print_tasks(scheduler.sort_by_time(),     "Sorted by TIME     (earliest preferred_time first)")

# ── 4. Filtering ─────────────────────────────────────────────────────────────

print("\n" + DIV)
print("  STEP 2  --  FILTERING")
print(DIV)

print_tasks(scheduler.filter_by_completion(False), "Pending tasks  (filter_by_completion=False)")
print_tasks(scheduler.filter_by_completion(True),  "Done tasks     (filter_by_completion=True)")
print_tasks(scheduler.filter_by_pet("Mochi"),      "Mochi's tasks  (filter_by_pet)")
print_tasks(scheduler.filter_by_pet("Pepper"),     "Pepper's tasks (filter_by_pet)")

# ── 5. Recurring tasks ───────────────────────────────────────────────────────

print("\n" + DIV)
print("  STEP 3  --  RECURRING TASK AUTO-SPAWN (timedelta)")
print(DIV)

for task in [t for t in tasks if t.frequency in ("daily", "weekly")]:
    next_task = task.mark_complete()
    print(f"\n  Completed : '{task.title}'  (freq={task.frequency}, due {task.due_date})")
    if next_task:
        delta = (next_task.due_date - task.due_date).days
        print(f"  Next copy : '{next_task.title}'  "
              f"due {next_task.due_date}  (+{delta} day(s) via timedelta(days={delta}))")

print("\n")
print_tasks(scheduler.filter_by_completion(True),  "Now done (after recurring completions)")
print_tasks(scheduler.filter_by_completion(False), "Still pending")

# ── 6. Conflict detection ────────────────────────────────────────────────────

print("\n" + DIV)
print("  STEP 4  --  CONFLICT DETECTION")
print(DIV)

# Build two ScheduledTask objects that intentionally overlap:
#   Task A: starts 9:00 AM, lasts 30 min → ends 9:30 AM
#   Task B: starts 9:15 AM, lasts 20 min → ends 9:35 AM
#   Window A (540–570) overlaps window B (555–575) ✓

task_a = Task("Morning walk",  duration_minutes=30, priority="high",  pet_name="Mochi")
task_b = Task("Brush & groom", duration_minutes=20, priority="medium", pet_name="Mochi")
task_c = Task("Feeding",       duration_minutes=10, priority="high",  pet_name="Mochi")

overlapping = [
    ScheduledTask(task=task_a, start_minute=540),   # 9:00 AM – 9:30 AM
    ScheduledTask(task=task_b, start_minute=555),   # 9:15 AM – 9:35 AM  ← overlaps A
    ScheduledTask(task=task_c, start_minute=600),   # 10:00 AM – 10:10 AM ← no overlap
]

print("\n  Checking these manually placed ScheduledTasks:")
for st in overlapping:
    print(f"    · {st.task.title:<22} {st.start_time_str()} – {st.end_time_str()}")

conflicts = scheduler.detect_conflicts(overlapping)

print(f"\n  detect_conflicts() found {len(conflicts)} conflict(s):\n")
if conflicts:
    for w in conflicts:
        print(f"  ⚠️  {w}")
else:
    print("  (none)")

# Also show that build_plan() surfaces conflicts automatically
print("\n  --- build_plan() conflict check on a plan with forced overlaps ---")
conflict_scheduler = Scheduler(
    pet=mochi,
    tasks=[task_a, task_b, task_c],
    owner=Owner(name="Jordan", available_minutes=120),
    day_start_minute=540,   # greedy packing from 9 AM won't overlap naturally,
)                           # so we demo detect_conflicts() directly above instead.

plan = conflict_scheduler.build_plan()
print(f"\n  Plan scheduled {len(plan.scheduled)} task(s). "
      f"Reasoning tail (last 3 lines):")
for line in plan.reasoning[-3:]:
    print(f"    {line}")

print("\n" + DIV + "\n")
