"""
tests/test_pawpal.py -- Full test suite for PawPal+.

Covers:
  - Model validation          (TestModelValidation)
  - Scheduling behaviour      (TestBuildPlan)
  - ScheduledTask helpers     (TestScheduledTask)
  - Scheduler.sort_by_time    (TestSortByTime)
  - Scheduler.filter_by_*     (TestFiltering)
  - Conflict detection        (TestConflictDetection)
  - Recurring task recurrence (TestRecurringTasks)
  - Task completion           (TestTaskCompletion)
  - Pet task management       (TestPetTaskAddition)

  ── Checkpoint tests (explicitly named) ──────────────────────
  - TestSortingCorrectness    tasks returned in chronological order
  - TestRecurrenceLogic       daily task complete → new task for following day
  - TestConflictFlagging      scheduler flags duplicate/same start times

Run: python -m pytest
"""

import sys
import os
import pytest
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pawpal_system import (
    Owner, Pet, Task, DailyPlan, ScheduledTask,
    Scheduler, build_plan, DAY_START_MINUTE,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def owner():
    return Owner(name="Jordan", available_minutes=60)

@pytest.fixture
def pet(owner):
    return Pet(name="Mochi", species="dog", owner=owner)

@pytest.fixture
def sample_tasks():
    return [
        Task("Morning walk",   duration_minutes=20, priority="high"),
        Task("Feeding",        duration_minutes=10, priority="high"),
        Task("Medication",     duration_minutes=5,  priority="high"),
        Task("Grooming",       duration_minutes=30, priority="medium"),
        Task("Enrichment toy", duration_minutes=15, priority="low"),
    ]


# ---------------------------------------------------------------------------
# Model validation
# ---------------------------------------------------------------------------

class TestModelValidation:
    def test_invalid_priority_raises(self):
        with pytest.raises(ValueError, match="priority"):
            Task("Walk", duration_minutes=10, priority="urgent")

    def test_zero_duration_raises(self):
        with pytest.raises(ValueError, match="duration_minutes"):
            Task("Walk", duration_minutes=0)

    def test_negative_available_minutes_raises(self):
        with pytest.raises(ValueError, match="available_minutes"):
            Owner(name="Alex", available_minutes=-10)

    def test_empty_owner_name_raises(self):
        with pytest.raises(ValueError, match="name"):
            Owner(name="  ", available_minutes=60)

    def test_empty_task_title_raises(self):
        with pytest.raises(ValueError):
            Task(title="", duration_minutes=10)

    def test_negative_preferred_time_raises(self):
        with pytest.raises(ValueError, match="preferred_time"):
            Task("Walk", duration_minutes=10, preferred_time=-1)

    def test_invalid_frequency_raises(self):
        with pytest.raises(ValueError, match="frequency"):
            Task("Walk", duration_minutes=10, frequency="hourly")


# ---------------------------------------------------------------------------
# Scheduling behaviour
# ---------------------------------------------------------------------------

class TestBuildPlan:
    def test_empty_tasks_returns_empty_plan(self, pet):
        plan = build_plan(pet, tasks=[])
        assert len(plan.scheduled) == 0
        assert len(plan.skipped) == 0

    def test_all_tasks_fit(self, pet):
        tasks = [Task("Walk",20,priority="high"), Task("Feed",10,priority="high"), Task("Meds",5,priority="high")]
        plan = build_plan(pet, tasks)
        assert len(plan.scheduled) == 3
        assert plan.total_minutes == 35

    def test_tasks_exceed_budget_are_skipped(self, pet):
        tasks = [Task("Walk",30,priority="high"), Task("Groom",30,priority="medium"), Task("Enrich",20,priority="low")]
        plan = build_plan(pet, tasks)
        assert plan.total_minutes <= 60
        assert len(plan.skipped) >= 1

    def test_high_priority_scheduled_before_low(self, pet):
        tasks = [Task("Low",10,priority="low"), Task("High",10,priority="high")]
        plan = build_plan(pet, tasks)
        titles = [st.task.title for st in plan.scheduled]
        assert titles.index("High") < titles.index("Low")

    def test_shorter_task_preferred_as_tiebreaker(self, pet):
        tasks = [Task("Long",30,priority="medium"), Task("Short",10,priority="medium")]
        plan = build_plan(pet, tasks)
        assert plan.scheduled[0].task.title == "Short"

    def test_plan_total_never_exceeds_budget(self, pet, sample_tasks):
        plan = build_plan(pet, sample_tasks)
        assert plan.total_minutes <= pet.owner.available_minutes  # type: ignore[union-attr]

    def test_reasoning_is_populated(self, pet, sample_tasks):
        assert len(build_plan(pet, sample_tasks).reasoning) > 0

    def test_scheduled_times_do_not_overlap(self, pet, sample_tasks):
        plan = build_plan(pet, sample_tasks)
        for i in range(len(plan.scheduled) - 1):
            assert plan.scheduled[i].end_minute <= plan.scheduled[i+1].start_minute

    def test_start_time_respects_day_start(self, pet):
        plan = build_plan(pet, [Task("Walk",20,priority="high")], day_start_minute=600)
        assert plan.scheduled[0].start_minute == 600

    def test_no_owner_uses_unlimited_budget(self):
        plan = build_plan(Pet(name="Whiskers",species="cat"), [Task("Play",9999,priority="medium")])
        assert len(plan.scheduled) == 1


# ---------------------------------------------------------------------------
# ScheduledTask time helpers
# ---------------------------------------------------------------------------

class TestScheduledTask:
    def test_start_time_str_morning(self, pet):
        plan = build_plan(pet, [Task("Walk",30,priority="high")], day_start_minute=480)
        assert plan.scheduled[0].start_time_str() == "8:00 AM"

    def test_end_time_str(self, pet):
        plan = build_plan(pet, [Task("Walk",30,priority="high")], day_start_minute=480)
        assert plan.scheduled[0].end_time_str() == "8:30 AM"

    def test_pm_time_str(self, pet):
        plan = build_plan(pet, [Task("Walk",20,priority="high")], day_start_minute=1080)
        assert plan.scheduled[0].start_time_str() == "6:00 PM"


# ---------------------------------------------------------------------------
# Scheduler.sort_by_time()
# ---------------------------------------------------------------------------

class TestSortByTime:
    def test_timed_tasks_sorted_by_preferred_time(self, pet):
        tasks = [
            Task("Afternoon", duration_minutes=20, priority="medium", preferred_time=840),
            Task("Morning",   duration_minutes=5,  priority="high",   preferred_time=480),
            Task("Lunch",     duration_minutes=10, priority="high",   preferred_time=720),
        ]
        result = Scheduler(pet, tasks).sort_by_time()
        assert [t.title for t in result] == ["Morning", "Lunch", "Afternoon"]

    def test_untimed_tasks_go_to_end(self, pet):
        tasks = [Task("No pref",15,priority="low",preferred_time=None), Task("Morning",5,priority="high",preferred_time=480)]
        result = Scheduler(pet, tasks).sort_by_time()
        assert result[0].title == "Morning"
        assert result[1].title == "No pref"

    def test_untimed_ordered_by_priority(self, pet):
        tasks = [Task("Low",10,priority="low"), Task("High",10,priority="high"), Task("Medium",10,priority="medium")]
        result = Scheduler(pet, tasks).sort_by_time()
        assert [t.title for t in result] == ["High", "Medium", "Low"]

    def test_sort_by_time_does_not_mutate(self, pet):
        tasks = [Task("B",10,priority="medium",preferred_time=600), Task("A",10,priority="medium",preferred_time=480)]
        s = Scheduler(pet, tasks)
        original = [t.title for t in s.tasks]
        s.sort_by_time()
        assert [t.title for t in s.tasks] == original

    def test_build_plan_time_mode(self, pet):
        tasks = [Task("Late",10,priority="high",preferred_time=900), Task("Early",10,priority="low",preferred_time=480)]
        plan = Scheduler(pet, tasks).build_plan(sort_mode="time")
        assert plan.scheduled[0].task.title == "Early"
        assert plan.scheduled[1].task.title == "Late"


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------

class TestFiltering:
    @pytest.fixture
    def mixed_tasks(self):
        t1 = Task("Walk",  20, priority="high",   pet_name="Mochi")
        t2 = Task("Feed",  10, priority="high",   pet_name="Mochi")
        t3 = Task("Groom", 20, priority="medium", pet_name="Pepper")
        t4 = Task("Meds",   5, priority="high",   pet_name="Mochi")
        t1.mark_complete()
        return [t1, t2, t3, t4]

    @pytest.fixture
    def sched(self, pet, mixed_tasks):
        return Scheduler(pet, mixed_tasks)

    def test_filter_pending(self, sched):
        result = sched.filter_by_completion(False)
        assert len(result) == 3
        assert all(not t.completed for t in result)

    def test_filter_done(self, sched):
        result = sched.filter_by_completion(True)
        assert len(result) == 1
        assert result[0].title == "Walk"

    def test_filter_by_pet_mochi(self, sched):
        assert len(sched.filter_by_pet("Mochi")) == 3

    def test_filter_by_pet_pepper(self, sched):
        result = sched.filter_by_pet("Pepper")
        assert len(result) == 1
        assert result[0].title == "Groom"

    def test_filter_by_pet_case_insensitive(self, sched):
        assert len(sched.filter_by_pet("mochi")) == 3
        assert len(sched.filter_by_pet("PEPPER")) == 1

    def test_filter_by_pet_unknown_returns_empty(self, sched):
        assert sched.filter_by_pet("Buddy") == []


# ---------------------------------------------------------------------------
# Conflict detection
# ---------------------------------------------------------------------------

class TestConflictDetection:
    """Verify detect_conflicts() finds overlapping ScheduledTask windows."""

    def _st(self, title, start, dur, priority="medium"):
        return ScheduledTask(
            task=Task(title=title, duration_minutes=dur, priority=priority),
            start_minute=start,
        )

    def test_no_conflicts_when_tasks_are_sequential(self, pet):
        items = [
            self._st("Walk", 480, 30),
            self._st("Feed", 510, 10),
            self._st("Meds", 520,  5),
        ]
        assert Scheduler(pet, []).detect_conflicts(items) == []

    def test_detects_direct_overlap(self, pet):
        items = [
            self._st("Walk",  540, 30),
            self._st("Groom", 555, 20),
        ]
        warnings = Scheduler(pet, []).detect_conflicts(items)
        assert len(warnings) == 1
        assert "Walk" in warnings[0]
        assert "Groom" in warnings[0]

    def test_detects_multiple_conflicts(self, pet):
        items = [
            self._st("A", 480, 60),
            self._st("B", 510, 60),
            self._st("C", 520, 60),
        ]
        warnings = Scheduler(pet, []).detect_conflicts(items)
        assert len(warnings) == 3

    def test_exact_end_to_start_is_not_a_conflict(self, pet):
        items = [
            self._st("Walk", 480, 30),
            self._st("Feed", 510, 10),
        ]
        assert Scheduler(pet, []).detect_conflicts(items) == []

    def test_empty_list_returns_no_warnings(self, pet):
        assert Scheduler(pet, []).detect_conflicts([]) == []

    def test_single_task_returns_no_warnings(self, pet):
        assert Scheduler(pet, []).detect_conflicts([self._st("Walk", 480, 30)]) == []

    def test_conflict_warning_is_string(self, pet):
        items = [self._st("A", 480, 60), self._st("B", 500, 60)]
        warnings = Scheduler(pet, []).detect_conflicts(items)
        assert all(isinstance(w, str) for w in warnings)

    def test_build_plan_no_conflicts_in_greedy_output(self, pet):
        tasks = [Task("Walk",20,priority="high"), Task("Feed",10,priority="high"), Task("Meds",5,priority="high")]
        plan = Scheduler(pet, tasks).build_plan()
        assert [r for r in plan.reasoning if "CONFLICT" in r] == []


# ---------------------------------------------------------------------------
# Recurring tasks
# ---------------------------------------------------------------------------

class TestRecurringTasks:
    def test_once_task_returns_none(self):
        task = Task("Bath", duration_minutes=25, priority="medium", frequency="once")
        assert task.mark_complete() is None
        assert task.completed is True

    def test_daily_task_returns_next_day(self):
        today = date(2026, 1, 1)
        task = Task("Feeding", 10, priority="high", frequency="daily", due_date=today)
        next_task = task.mark_complete()
        assert next_task.due_date == today + timedelta(days=1)

    def test_weekly_task_returns_next_week(self):
        today = date(2026, 1, 1)
        task = Task("Grooming", 20, priority="medium", frequency="weekly", due_date=today)
        next_task = task.mark_complete()
        assert next_task.due_date == today + timedelta(days=7)

    def test_next_task_inherits_attributes(self):
        today = date(2026, 3, 1)
        task = Task("Morning meds", 5, priority="high", notes="supplement",
                    pet_name="Mochi", frequency="daily", due_date=today, preferred_time=480)
        next_task = task.mark_complete()
        assert next_task.title == "Morning meds"
        assert next_task.pet_name == "Mochi"
        assert next_task.preferred_time == 480
        assert next_task.completed is False

    def test_daily_without_due_date_uses_today(self):
        task = Task("Walk", 20, priority="high", frequency="daily")
        next_task = task.mark_complete()
        assert next_task.due_date == date.today() + timedelta(days=1)


# ---------------------------------------------------------------------------
# Task completion
# ---------------------------------------------------------------------------

class TestTaskCompletion:
    def test_task_starts_incomplete(self):
        assert Task("Walk", 30, priority="high").completed is False

    def test_mark_complete_sets_flag(self):
        t = Task("Walk", 30, priority="high")
        t.mark_complete()
        assert t.completed is True

    def test_mark_complete_is_idempotent(self):
        t = Task("Feed", 10, priority="high")
        t.mark_complete(); t.mark_complete()
        assert t.completed is True


# ---------------------------------------------------------------------------
# Pet task management
# ---------------------------------------------------------------------------

class TestPetTaskAddition:
    def test_pet_starts_with_zero_tasks(self):
        assert Pet(name="Mochi", species="dog").task_count() == 0

    def test_add_one_task_increases_count(self):
        p = Pet(name="Mochi", species="dog")
        p.add_task(Task("Walk", 20, priority="high"))
        assert p.task_count() == 1

    def test_add_multiple_tasks_increases_count(self):
        p = Pet(name="Pepper", species="cat")
        for title in ["Feeding", "Grooming", "Nail trim"]:
            p.add_task(Task(title, 10, priority="medium"))
        assert p.task_count() == 3

    def test_tasks_are_stored_in_order(self):
        p = Pet(name="Mochi", species="dog")
        p.add_task(Task("Walk", 30, priority="high"))
        p.add_task(Task("Medication", 5, priority="high"))
        assert p.tasks[0].title == "Walk"
        assert p.tasks[1].title == "Medication"


# ===========================================================================
# CHECKPOINT TESTS
# Explicitly named to match the three checkpoint requirements:
#   1. Sorting Correctness  — tasks returned in chronological order
#   2. Recurrence Logic     — daily task complete → new task for following day
#   3. Conflict Flagging    — scheduler flags duplicate / same-time tasks
# ===========================================================================

class TestSortingCorrectness:
    """
    Checkpoint: Verify tasks are returned in chronological order.

    sort_by_time() must return tasks ordered by preferred_time ascending —
    earliest minute value first — regardless of the order they were added.
    """

    def test_tasks_returned_in_chronological_order(self, pet):
        """
        Tasks added in reverse time order (5 PM, 2 PM, 8 AM, 12 PM) must
        come out sorted earliest-first: 8 AM → 12 PM → 2 PM → 5 PM.
        """
        tasks = [
            Task("Evening walk",    duration_minutes=30, priority="high",   preferred_time=1020),  # 5:00 PM
            Task("Afternoon groom", duration_minutes=20, priority="medium", preferred_time=840),   # 2:00 PM
            Task("Morning meds",    duration_minutes=5,  priority="high",   preferred_time=480),   # 8:00 AM
            Task("Lunch feeding",   duration_minutes=10, priority="high",   preferred_time=720),   # 12:00 PM
        ]
        result = Scheduler(pet, tasks).sort_by_time()
        times = [t.preferred_time for t in result]
        assert times == sorted(times), (
            "sort_by_time() did not return tasks in chronological order. "
            f"Got preferred_times: {times}"
        )
        assert [t.title for t in result] == [
            "Morning meds",
            "Lunch feeding",
            "Afternoon groom",
            "Evening walk",
        ]

    def test_chronological_order_preserved_for_equal_times(self, pet):
        """
        Two tasks at the same preferred_time should both appear before
        any task with a later preferred_time.
        """
        tasks = [
            Task("Late task",   duration_minutes=10, priority="low",  preferred_time=900),
            Task("Early A",     duration_minutes=10, priority="high", preferred_time=480),
            Task("Early B",     duration_minutes=5,  priority="low",  preferred_time=480),
        ]
        result = Scheduler(pet, tasks).sort_by_time()
        late_index  = next(i for i, t in enumerate(result) if t.title == "Late task")
        early_a_idx = next(i for i, t in enumerate(result) if t.title == "Early A")
        early_b_idx = next(i for i, t in enumerate(result) if t.title == "Early B")
        assert early_a_idx < late_index
        assert early_b_idx < late_index


class TestRecurrenceLogic:
    """
    Checkpoint: Confirm that marking a daily task complete creates
    a new task for the following day.
    """

    def test_completing_daily_task_creates_task_for_following_day(self):
        """
        The canonical checkpoint case: a daily task due today, when
        completed, must produce a new task due exactly tomorrow.
        """
        today     = date(2026, 3, 30)
        tomorrow  = today + timedelta(days=1)

        daily_task = Task(
            title="Morning feeding",
            duration_minutes=10,
            priority="high",
            frequency="daily",
            due_date=today,
        )

        next_task = daily_task.mark_complete()

        # Original task must be marked done
        assert daily_task.completed is True, "Original task should be completed"

        # A new task must be returned
        assert next_task is not None, "A follow-up task must be created for a daily task"

        # It must be due the following day — not today, not two days from now
        assert next_task.due_date == tomorrow, (
            f"Expected due date {tomorrow}, got {next_task.due_date}"
        )

    def test_follow_up_task_is_not_completed(self):
        """The spawned task must start incomplete, ready to be done tomorrow."""
        today = date(2026, 3, 30)
        task  = Task("Meds", 5, priority="high", frequency="daily", due_date=today)
        next_task = task.mark_complete()
        assert next_task.completed is False, "Follow-up task must not be pre-completed"

    def test_follow_up_task_keeps_same_title_and_priority(self):
        """The follow-up task must be recognisably the same task."""
        today = date(2026, 3, 30)
        task  = Task("Evening walk", 30, priority="high", frequency="daily", due_date=today)
        next_task = task.mark_complete()
        assert next_task.title    == "Evening walk"
        assert next_task.priority == "high"
        assert next_task.duration_minutes == 30

    def test_once_task_does_not_create_follow_up(self):
        """A one-off task must return None — no follow-up should be created."""
        task = Task("Vet visit", 60, priority="high", frequency="once")
        next_task = task.mark_complete()
        assert next_task is None, "A 'once' task must not generate a follow-up"


class TestConflictFlagging:
    """
    Checkpoint: Verify that the Scheduler flags duplicate / same-start-time tasks.

    Two tasks that start at the exact same time — or whose windows overlap —
    must produce a warning from detect_conflicts(). The method must never
    raise; it must always return a list of strings.
    """

    def _st(self, title: str, start: int, dur: int) -> ScheduledTask:
        """Helper: build a ScheduledTask at an explicit start_minute."""
        return ScheduledTask(
            task=Task(title=title, duration_minutes=dur, priority="medium"),
            start_minute=start,
        )

    def test_same_start_time_is_flagged(self, pet):
        """
        Two tasks starting at the exact same minute must be flagged as a
        conflict — this is the 'duplicate time' case.
        """
        items = [
            self._st("Walk",  480, 30),   # both start at 8:00 AM
            self._st("Feed",  480, 10),   # same start → guaranteed overlap
        ]
        warnings = Scheduler(pet, []).detect_conflicts(items)
        assert len(warnings) == 1, (
            f"Expected 1 conflict for same-start tasks, got {len(warnings)}"
        )

    def test_warning_message_names_both_conflicting_tasks(self, pet):
        """The warning string must identify which two tasks conflict."""
        items = [
            self._st("Morning walk", 480, 30),
            self._st("Feeding",      480, 10),
        ]
        warnings = Scheduler(pet, []).detect_conflicts(items)
        assert len(warnings) == 1
        assert "Morning walk" in warnings[0], "Warning must name the first conflicting task"
        assert "Feeding"      in warnings[0], "Warning must name the second conflicting task"

    def test_no_exception_raised_on_conflict(self, pet):
        """detect_conflicts() must return a list, never raise an exception."""
        items = [
            self._st("A", 480, 60),
            self._st("B", 480, 60),
        ]
        try:
            result = Scheduler(pet, []).detect_conflicts(items)
        except Exception as exc:
            pytest.fail(f"detect_conflicts() raised unexpectedly: {exc}")
        assert isinstance(result, list)

    def test_non_overlapping_same_duration_not_flagged(self, pet):
        """Tasks of equal length placed end-to-start must not be flagged."""
        items = [
            self._st("Walk", 480, 30),   # 8:00–8:30
            self._st("Feed", 510, 30),   # 8:30–9:00  ← starts exactly when Walk ends
        ]
        warnings = Scheduler(pet, []).detect_conflicts(items)
        assert warnings == [], (
            f"End-to-start tasks must not be flagged as conflicting, got: {warnings}"
        )
