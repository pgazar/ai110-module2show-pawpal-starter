# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

The design started from the question: *what real-world things does this app need to know about?* That produced five classes and one module, each with a single clear responsibility.

**`Owner`** represents the person doing the caregiving. Its only job is to carry two pieces of information the scheduler needs: who the owner is (`name`) and how much time they have available today (`available_minutes`). Keeping the time budget here — rather than passing it as a loose integer — means the scheduler can always ask "whose budget is this?" and the answer travels with the number.

**`Pet`** represents the animal being cared for. It holds the pet's name and species, and carries an optional reference back to its `Owner`. The species field was included early because different animals have different care needs (a dog needs walks; a cat does not), which opens the door to species-aware scheduling in a future iteration without changing the class structure.

**`Task`** represents a single care action — a walk, a feeding, a medication dose, a grooming session. It owns four attributes: a human-readable `title`, a `duration_minutes` estimate, a `priority` level (low / medium / high), and an optional `notes` field. `Task` is also responsible for validating itself: it raises a `ValueError` immediately if any attribute is out of range, so bad data never reaches the scheduler. The `priority_rank` property converts the string priority into a sortable integer, keeping that mapping in one place.

**`ScheduledTask`** is a thin wrapper that adds a time placement to a `Task`. It stores the task and a `start_minute` (minutes from midnight), and computes `end_minute`, `start_time_str`, and `end_time_str` from those two values. Separating this from `Task` was a deliberate choice: a task is a description of *what* needs to happen; a scheduled task is a decision about *when*. Mixing them would make it impossible to reuse the same task definition across multiple plans.

**`DailyPlan`** is the scheduler's output object. It holds three lists — `scheduled` (the tasks that fit), `skipped` (the tasks that didn't), and `reasoning` (a plain-English log of every decision) — plus a reference to the `Pet` the plan belongs to. Putting the reasoning inside the plan rather than printing it as side-effects meant the Streamlit UI could display the explanation without any extra logic: it simply iterates `plan.reasoning`.

**`scheduler` (module → class)** began as a single `build_plan()` function but grew into a full `Scheduler` class once sorting, filtering, and conflict detection each needed a home. Its responsibility is purely algorithmic: given a pet, a list of tasks, and an owner, produce a `DailyPlan`.

**Three core user actions the system is designed around:**

1. **Add or edit a care task.** A user can describe something their pet needs — such as a morning walk, a feeding, or a medication dose — by giving it a name, an estimated duration in minutes, and a priority level (low, medium, or high). They can also edit or delete any task after adding it. This action populates the task list that the scheduler draws from. Without it, the system has nothing to plan.

2. **Generate a daily schedule.** Once tasks are entered, the user provides their time budget for the day (how many minutes they have available) and a start hour, then clicks "Build schedule." The system automatically sorts tasks by priority, fits as many as possible into the available window, and assigns each a concrete start and end time. Tasks that do not fit are listed separately as skipped, so nothing is silently dropped.

3. **Understand why the plan looks the way it does.** After a schedule is generated, the user can expand a "Why this plan?" section that shows a plain-English log of every scheduling decision — which tasks were included and when, which were skipped and why, and how much of the time budget was consumed. This gives the owner transparency and lets them adjust priorities or durations if the result is not what they expected.

**b. Design changes**

One meaningful change: `ScheduledTask` was originally a plain tuple `(task, start_minute)`. During implementation it became a proper dataclass once I needed computed properties (`end_minute`, `start_time_str`, `end_time_str`). Keeping those helpers on the object made the Streamlit UI cleaner — it could just call `st.start_time_str()` rather than repeating time arithmetic in two places.

A second change: the `scheduler` module became a `Scheduler` class when the number of methods grew beyond what a flat module could cleanly contain. Sorting, filtering, and conflict detection all operate on the same task list and time budget, so grouping them into an object with shared state made the API cleaner and the tests more readable.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

The scheduler considers two constraints: (1) task priority (`high > medium > low`) and (2) the owner's `available_minutes` budget. Priority was chosen as the primary key because a missed medication is far more consequential than a skipped nail trim. Duration is the tiebreaker within the same priority level so that shorter tasks are preferred, allowing more items to fit.

**b. Tradeoffs**

The greedy approach can leave a gap of unused time when a high-priority long task is followed by a low-priority short one that could have filled that gap. For example, if 10 minutes remain and only a 5-minute low-priority task is left, it is still skipped because it was sorted after tasks that already exhausted the budget. This is a reasonable tradeoff for a daily pet care app: owners tend to prefer a predictable block of "done" time over a fragmented schedule that theoretically squeezes in every task.

A second tradeoff appears in the conflict-detection strategy. `detect_conflicts()` only checks whether two tasks' time windows overlap — it does not prevent overlaps from occurring inside `build_plan` itself, because the greedy scheduler always packs tasks end-to-start and therefore never produces overlaps on its own. Conflict detection is most useful when a user manually supplies a list of `ScheduledTask` objects with fixed times, or in a future version where tasks can be pinned. The check is O(n²) over pairs, which is fine for daily pet-care plans (typically fewer than 20 tasks) but would need a sweep-line algorithm at scale. Returning warning strings rather than raising exceptions means the UI can surface conflicts as notifications without crashing — accepting the risk that a conflict could be ignored in exchange for never blocking the user.

---

## 3. AI Collaboration

**a. How you used AI**

AI was used throughout every phase of this project.

During **Phase 1 (design)**, the most effective Copilot feature was Inline Chat on an empty `pawpal_system.py` file. Asking "what classes does a pet care scheduling app need?" produced a first-draft list of `Owner`, `Pet`, `Task`, `ScheduledTask`, and `DailyPlan` — which matched the intuition from the domain but arrived in seconds rather than minutes. The most useful prompt pattern was naming the constraint first: "given that the app needs to handle a time budget, a priority ordering, and an explanation of why tasks were chosen, what methods should `Scheduler` have?" This produced the `sort_by_priority`, `build_plan`, and `reasoning` list in one response.

During **Phase 2 (logic)**, Agent Mode was used for multi-file edits — for example, adding `frequency` and `due_date` to `Task` and simultaneously updating `mark_complete()`, `to_dict()`, `from_dict()`, and the test fixtures that needed the new fields. Doing this manually across four locations would have introduced inconsistencies; Agent Mode kept every location in sync. The `#file:pawpal_system.py` context anchor was also effective: attaching the actual file to a Copilot Chat prompt ("based on this file, what updates should I make to my UML diagram?") produced accurate suggestions that reflected the real code rather than a hallucinated version of it.

During **Phase 3 (UI)**, the most useful Copilot feature was the `#codebase` context for README drafting. Without it, describing the features accurately would have required manually cross-referencing the code; with it, the draft reflected the actual method names and lambda key patterns already in the file.

Using **separate chat sessions for different phases** helped significantly with organisation. A session focused on the Scheduler class did not accumulate context about Streamlit layout, and vice versa. When returning to a phase after working on another, starting a fresh session with the relevant `#file:` anchor meant the suggestions were precise rather than confused by earlier unrelated context.

**b. Judgment and verification**

One example of a rejected AI suggestion: when asked to implement `sort_by_time()`, Copilot suggested collapsing the timed and untimed task separation into a single `sorted()` call using `key=lambda t: (t.preferred_time is None, t.preferred_time or 0, -t.priority_rank, t.duration_minutes)`. This is more compact — four lines become one — but the intent is not obvious without reading it carefully. A new reader would not immediately understand why `t.preferred_time is None` is the first element of the tuple, or why `t.preferred_time or 0` is safe. The current implementation keeps the two groups explicit:

```python
timed   = sorted([t for t in self.tasks if t.preferred_time is not None], key=lambda t: t.preferred_time)
untimed = sorted([t for t in self.tasks if t.preferred_time is None],     key=lambda t: (-t.priority_rank, t.duration_minutes))
return timed + untimed
```

This version is longer but the structure directly reflects the mental model: "timed tasks in time order, then untimed tasks in priority order." The AI's version was evaluated, understood, and consciously declined in favour of readability.

A second example: Copilot's initial `detect_conflicts()` suggestion raised a `ValueError` on the first conflict found. That was rejected because crashing the app when a user accidentally schedules two tasks at the same time is a worse user experience than showing a warning. The return-a-list-of-strings approach was substituted specifically so the UI could display `st.warning()` banners without a try-except wrapper.

---

## 4. Testing and Verification

**a. What you tested**

61 tests across 12 test classes. `TestModelValidation` checks that bad inputs raise `ValueError` immediately. `TestBuildPlan` verifies the core greedy contract: empty input, all-fit, budget overflow, priority ordering, tiebreaker, no-overlap guarantee, and unlimited-budget fallback. `TestScheduledTask` checks time string formatting. `TestSortByTime`, `TestFiltering`, `TestConflictDetection`, and `TestRecurringTasks` each cover their respective `Scheduler` methods in full, including edge cases (empty list, single task, no-conflict, exact end-to-start). Three checkpoint-named classes — `TestSortingCorrectness`, `TestRecurrenceLogic`, and `TestConflictFlagging` — make the most important behaviours immediately recognisable by name.

**b. Confidence**

Confidence in the happy path, priority ordering, and chronological sorting is high — all are directly exercised with explicit assertions. The recurring task logic is pinned to a fixed date (`2026-03-30`) so the test does not drift over time. Edge cases I would add next: tasks that exactly match the remaining budget, a pet whose species automatically adds species-specific tasks, and end-to-end Streamlit UI tests using `streamlit.testing`.

---

## 5. Reflection

**a. What went well**

Consolidating all backend logic into a single `pawpal_system.py` file made the project easy to navigate. Any developer (or AI tool) can open one file and understand the entire domain model and scheduling algorithm. The `DailyPlan.reasoning` list was the single most effective design decision — it gave the UI a free, structured explanation layer with no additional code, and it made the scheduler's decisions legible both in the terminal (`main.py`) and in the Streamlit expander.

**b. What you would improve**

The next iteration would add time-of-day constraints (e.g., medication must be given before noon), task pinning (a fixed start time that the scheduler must respect), and a persistent storage layer so plans survive a browser refresh. Each of those would require moving from a greedy list to an interval-placement algorithm, which would also make the conflict-detection guarantee more interesting to test.

**c. Key takeaway: being the lead architect in an AI-assisted workflow**

The most important lesson from this project is that AI tools are most useful when you already have a clear model in your head of what you are trying to build. When a prompt is vague — "help me with scheduling" — the output is generic. When a prompt is precise — "given `Scheduler` holds a `list[Task]` and an `available_minutes` int, write a `sort_by_time()` method that puts tasks with `preferred_time=None` at the end, ordered by `(-priority_rank, duration_minutes)`" — the output is immediately usable.

Being the lead architect means deciding which AI suggestions to accept, which to modify, and which to discard. In this project, the string-sort suggestion for priorities was discarded (fragile), the compact `sort_by_time` lambda was simplified (unreadable), and the exception-raising conflict detector was replaced (bad UX). In each case the AI produced a technically correct answer to a narrowly stated question, and the human judgment was applied at the level of whether that answer fit the broader design goals. That division of labour — AI for rapid generation, human for architectural judgment — is the most effective pattern I found for this kind of project.
