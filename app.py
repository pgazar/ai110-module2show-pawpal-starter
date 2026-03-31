"""
PawPal+ -- Streamlit UI
Run: streamlit run app.py
"""

import streamlit as st
from datetime import datetime
from pawpal_system import Owner, Pet, Task, Scheduler, build_plan

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")
st.caption("Your daily pet care planner")

# ---------------------------------------------------------------------------
# Session state defaults
# ---------------------------------------------------------------------------

if "pets"        not in st.session_state: st.session_state.pets:        list[dict] = []
if "tasks"       not in st.session_state: st.session_state.tasks:       list[dict] = []
if "edit_index"  not in st.session_state: st.session_state.edit_index  = None
if "active_pet"  not in st.session_state: st.session_state.active_pet  = None
if "saved_plans" not in st.session_state: st.session_state.saved_plans: dict       = {}
if "sort_mode"   not in st.session_state: st.session_state.sort_mode   = "priority"

# ---------------------------------------------------------------------------
# Constants / helpers
# ---------------------------------------------------------------------------

SPECIES_ICON   = {"dog": "🐕", "cat": "🐈", "rabbit": "🐇", "bird": "🐦", "other": "🐾"}
PRIORITY_COLOR = {"high": "🔴", "medium": "🟡", "low": "🟢"}
PRIORITY_BADGE = {"high": "🔴 High", "medium": "🟡 Medium", "low": "🟢 Low"}

def pet_names() -> list[str]:
    return [p["name"] for p in st.session_state.pets]

def save_plan(pet_name, species, rows, skipped, reasoning,
              conflicts, total_minutes, available):
    """Persist a built plan to session state under the pet's name."""
    st.session_state.saved_plans[pet_name] = {
        "pet_name": pet_name, "species": species,
        "saved_at": datetime.now().strftime("%H:%M:%S"),
        "total_minutes": total_minutes, "available": available,
        "rows": rows, "skipped": skipped,
        "reasoning": reasoning, "conflicts": conflicts,
    }

def render_saved_plan(p: dict) -> None:
    """Render one saved plan record inside the Saved Plans section."""
    icon = SPECIES_ICON.get(p["species"], "🐾")
    pct  = p["total_minutes"] / p["available"] if p["available"] else 0

    st.markdown(
        icon + " **" + p["pet_name"] + "** (" + p["species"] + ")  "
        + "· saved at " + p["saved_at"] + "  "
        + "· " + str(p["total_minutes"]) + "/" + str(p["available"]) + " min used"
    )
    st.progress(min(pct, 1.0))

    # Conflict warnings first — most important for the owner to see
    if p.get("conflicts"):
        for w in p["conflicts"]:
            st.warning("⚠️ " + w)

    if p["rows"]:
        st.table(p["rows"])

    if p["skipped"]:
        st.markdown("**⏭️ Skipped (not enough time):**")
        for s in p["skipped"]:
            st.markdown(
                "- **" + s["title"] + "** ("
                + str(s["duration_minutes"]) + " min, "
                + s["priority"] + " priority)"
            )

    with st.expander("🧠 Why this plan? (scheduler reasoning)", expanded=False):
        for line in p["reasoning"]:
            if "CONFLICT" in line:
                st.warning(line)
            elif line.startswith("Skipped"):
                st.markdown("- ⏭️ " + line)
            elif line.startswith("Scheduled"):
                st.markdown("- ✅ " + line)
            else:
                st.markdown("- " + line)

# ---------------------------------------------------------------------------
# Section 1: Owner info
# ---------------------------------------------------------------------------

with st.expander("👤 Owner Info", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        owner_name = st.text_input("Owner name", value="Jordan")
    with col2:
        available = st.number_input(
            "Time available today (minutes)", min_value=5, max_value=1440, value=120,
            help="Total minutes available for pet care today"
        )
    start_hour = st.slider(
        "Day start hour", min_value=5, max_value=12, value=8,
        help="What hour do you start pet care? (e.g. 8 = 8:00 AM)"
    )

# ---------------------------------------------------------------------------
# Section 2: Pets
# ---------------------------------------------------------------------------

st.divider()
st.subheader("🐶 My Pets")

with st.expander("➕ Add a pet", expanded=len(st.session_state.pets) == 0):
    pc1, pc2, pc3 = st.columns([3, 2, 1])
    with pc1:
        new_pet_name = st.text_input("Pet name", key="new_pet_name")
    with pc2:
        new_pet_species = st.selectbox(
            "Species", ["dog", "cat", "rabbit", "bird", "other"], key="new_pet_species"
        )
    with pc3:
        st.write(""); st.write("")
        if st.button("Add pet", use_container_width=True):
            if not new_pet_name.strip():
                st.error("Pet name is required.")
            elif any(p["name"].lower() == new_pet_name.strip().lower()
                     for p in st.session_state.pets):
                st.error("A pet with that name already exists.")
            else:
                st.session_state.pets.append(
                    {"name": new_pet_name.strip(), "species": new_pet_species}
                )
                if st.session_state.active_pet is None:
                    st.session_state.active_pet = new_pet_name.strip()
                st.rerun()

if st.session_state.pets:
    for i, p in enumerate(st.session_state.pets):
        col_info, col_del = st.columns([8, 1])
        with col_info:
            icon = SPECIES_ICON.get(p["species"], "🐾")
            st.markdown(icon + " **" + p["name"] + "** — " + p["species"])
        with col_del:
            if st.button("🗑️", key="del_pet_" + str(i), help="Remove this pet"):
                removed = p["name"]
                st.session_state.tasks = [
                    t for t in st.session_state.tasks if t.get("pet_name") != removed
                ]
                st.session_state.saved_plans.pop(removed, None)
                st.session_state.pets.pop(i)
                if st.session_state.active_pet == removed:
                    st.session_state.active_pet = (
                        st.session_state.pets[0]["name"] if st.session_state.pets else None
                    )
                st.rerun()
else:
    st.info("No pets yet. Add one above — at least one pet is needed to build a schedule.")

# ---------------------------------------------------------------------------
# Section 3: Tasks
# ---------------------------------------------------------------------------

st.divider()
st.subheader("📋 Tasks")

if not st.session_state.pets:
    st.warning("Add at least one pet above before creating tasks.")
else:
    # ── Pet selector ──────────────────────────────────────────────────────
    names = pet_names()
    if st.session_state.active_pet not in names:
        st.session_state.active_pet = names[0]

    selected_for_tasks = st.selectbox(
        "Select pet to add tasks to", names,
        index=names.index(st.session_state.active_pet),
        key="task_pet_selector",
    )
    st.session_state.active_pet = selected_for_tasks

    # ── Sort mode toggle (drives the preview list below) ─────────────────
    sort_col1, sort_col2 = st.columns([3, 3])
    with sort_col1:
        sort_choice = st.radio(
            "Preview sort order",
            ["By priority", "By time"],
            horizontal=True,
            key="sort_mode_radio",
            help="Controls how tasks are displayed below and how the schedule is built",
        )
    st.session_state.sort_mode = "priority" if sort_choice == "By priority" else "time"

    # ── PATH A: Quick-add presets ─────────────────────────────────────────
    with st.expander("⚡ Quick-add common tasks", expanded=True):
        st.caption(
            "Click any task below to add it instantly to **" + selected_for_tasks + "**."
        )
        presets = [
            ("Morning walk",    30, "high"),
            ("Feeding",         10, "high"),
            ("Medication",       5, "high"),
            ("Grooming",        20, "medium"),
            ("Enrichment toy",  15, "medium"),
            ("Vet appointment", 60, "high"),
            ("Bath time",       25, "medium"),
            ("Nail trim",       10, "low"),
        ]
        cols = st.columns(4)
        for i, (name, dur, pri) in enumerate(presets):
            with cols[i % 4]:
                if st.button("+ " + name, key="preset_" + str(i), use_container_width=True):
                    st.session_state.tasks.append({
                        "title": name, "duration_minutes": dur,
                        "priority": pri, "notes": "",
                        "pet_name": selected_for_tasks,
                    })
                    st.rerun()

    # ── PATH B: Custom task form ──────────────────────────────────────────
    editing   = st.session_state.edit_index is not None
    form_label = "✏️ Edit Task" if editing else "➕ Add a custom task"

    with st.expander(form_label, expanded=editing):
        defaults = {"title": "", "duration_minutes": 15, "priority": "medium", "notes": ""}
        if editing:
            defaults = st.session_state.tasks[st.session_state.edit_index]

        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            t_title = st.text_input("Task title", value=defaults["title"], key="form_title")
        with col2:
            t_duration = st.number_input(
                "Duration (min)", min_value=1, max_value=480,
                value=int(defaults["duration_minutes"]), key="form_duration"
            )
        with col3:
            priority_opts = ["low", "medium", "high"]
            t_priority = st.selectbox(
                "Priority", priority_opts,
                index=priority_opts.index(defaults["priority"]),
                key="form_priority"
            )
        t_notes = st.text_input(
            "Notes (optional)", value=defaults.get("notes", ""), key="form_notes"
        )

        save_col, cancel_col = st.columns([1, 4])
        with save_col:
            if st.button("💾 Save task", use_container_width=True):
                if not t_title.strip():
                    st.error("Task title is required.")
                else:
                    new_task = {
                        "title": t_title.strip(),
                        "duration_minutes": int(t_duration),
                        "priority": t_priority,
                        "notes": t_notes.strip(),
                        "pet_name": selected_for_tasks,
                    }
                    if editing:
                        st.session_state.tasks[st.session_state.edit_index] = new_task
                        st.session_state.edit_index = None
                        st.success('Updated "' + t_title + '"!')
                    else:
                        st.session_state.tasks.append(new_task)
                        st.success('Added "' + t_title + '" for ' + selected_for_tasks + '!')
                    st.rerun()
        if editing:
            with cancel_col:
                if st.button("✖ Cancel edit"):
                    st.session_state.edit_index = None
                    st.rerun()

    # ── Task list — sorted via Scheduler ─────────────────────────────────
    raw_pet_tasks = [
        t for t in st.session_state.tasks
        if t.get("pet_name") == selected_for_tasks
    ]

    if raw_pet_tasks:
        # Build Task objects and use Scheduler to sort the preview
        try:
            task_objs = [Task.from_dict(t) for t in raw_pet_tasks]
            preview_owner = Owner(
                name=owner_name.strip() or "Owner",
                available_minutes=int(available)
            )
            preview_pet = Pet(
                name=selected_for_tasks, species="other", owner=preview_owner
            )
            sched_preview = Scheduler(preview_pet, task_objs)

            if st.session_state.sort_mode == "time":
                sorted_task_objs = sched_preview.sort_by_time()
                sort_label = "sorted by preferred time"
            else:
                sorted_task_objs = sched_preview.sort_by_priority()
                sort_label = "sorted by priority"

            # Map sorted Task objects back to their original dicts (for edit/delete indices)
            title_to_index = {
                t.get("title"): i
                for i, t in enumerate(st.session_state.tasks)
                if t.get("pet_name") == selected_for_tasks
            }

        except Exception:
            sorted_task_objs = None
            sort_label = ""

        st.markdown(
            "**" + str(len(raw_pet_tasks)) + " task(s) for "
            + selected_for_tasks + "** (" + sort_label + "):"
        )

        if sorted_task_objs:
            for task_obj in sorted_task_objs:
                orig_index = title_to_index.get(task_obj.title)
                orig_dict  = (
                    st.session_state.tasks[orig_index]
                    if orig_index is not None else {}
                )
                col_info, col_edit, col_del = st.columns([6, 1, 1])
                with col_info:
                    notes_part = (" · _" + task_obj.notes + "_") if task_obj.notes else ""
                    st.markdown(
                        PRIORITY_COLOR[task_obj.priority]
                        + " **" + task_obj.title + "** — "
                        + str(task_obj.duration_minutes) + " min · "
                        + task_obj.priority + " priority"
                        + notes_part
                    )
                with col_edit:
                    if orig_index is not None and st.button(
                        "✏️", key="edit_" + str(orig_index), help="Edit"
                    ):
                        st.session_state.edit_index = orig_index
                        st.rerun()
                with col_del:
                    if orig_index is not None and st.button(
                        "🗑️", key="del_task_" + str(orig_index), help="Delete"
                    ):
                        st.session_state.tasks.pop(orig_index)
                        st.rerun()
        else:
            # Fallback: plain display if Scheduler fails
            for i, t in [
                (i, t) for i, t in enumerate(st.session_state.tasks)
                if t.get("pet_name") == selected_for_tasks
            ]:
                col_info, col_edit, col_del = st.columns([6, 1, 1])
                with col_info:
                    notes_part = (" · _" + t["notes"] + "_") if t.get("notes") else ""
                    st.markdown(
                        PRIORITY_COLOR[t["priority"]] + " **" + t["title"] + "** — "
                        + str(t["duration_minutes"]) + " min · "
                        + t["priority"] + " priority" + notes_part
                    )
                with col_edit:
                    if st.button("✏️", key="edit_" + str(i), help="Edit"):
                        st.session_state.edit_index = i
                        st.rerun()
                with col_del:
                    if st.button("🗑️", key="del_task_" + str(i), help="Delete"):
                        st.session_state.tasks.pop(i)
                        st.rerun()

        if st.button("🗑️ Clear tasks for " + selected_for_tasks, type="secondary"):
            st.session_state.tasks = [
                t for t in st.session_state.tasks
                if t.get("pet_name") != selected_for_tasks
            ]
            st.rerun()
    else:
        st.info(
            "No tasks yet for " + selected_for_tasks
            + ". Use Quick-add above or fill in a custom task."
        )

# ---------------------------------------------------------------------------
# Section 4: Generate schedule
# ---------------------------------------------------------------------------

st.divider()
st.subheader("📅 Generate Daily Plan")

if st.session_state.pets:
    pet_options = [
        p["name"] + " (" + p["species"] + ")" for p in st.session_state.pets
    ]
    selected_label   = st.selectbox("Generate plan for", pet_options, key="plan_pet_selector")
    selected_plan_pet = st.session_state.pets[pet_options.index(selected_label)]["name"]
else:
    selected_plan_pet = None

# Sort mode for plan generation
plan_sort = st.radio(
    "Schedule sort mode",
    ["By priority (recommended)", "By preferred time"],
    horizontal=True,
    key="plan_sort_radio",
    help="Priority mode fills as many high-priority tasks as possible. "
         "Time mode respects preferred start times.",
)
plan_sort_mode = "priority" if "priority" in plan_sort else "time"

if st.button("✨ Build schedule", type="primary", use_container_width=True):
    if not st.session_state.pets:
        st.warning("Add at least one pet before generating a schedule.")
    else:
        pet_task_dicts = [
            t for t in st.session_state.tasks
            if t.get("pet_name") == selected_plan_pet
        ]
        if not pet_task_dicts:
            st.warning(
                "No tasks assigned to **" + selected_plan_pet + "** yet. "
                "Select this pet in the Tasks section and add some tasks first."
            )
            st.stop()

        try:
            owner = Owner(
                name=owner_name.strip() or "Owner",
                available_minutes=int(available)
            )
            pet_dict = next(
                p for p in st.session_state.pets if p["name"] == selected_plan_pet
            )
            pet   = Pet(name=pet_dict["name"], species=pet_dict["species"], owner=owner)
            tasks = [Task.from_dict(t) for t in pet_task_dicts]
        except ValueError as e:
            st.error("Invalid input: " + str(e))
            st.stop()

        # ── Use Scheduler directly ────────────────────────────────────────
        scheduler = Scheduler(pet, tasks, owner=owner,
                              day_start_minute=start_hour * 60)
        plan = scheduler.build_plan(sort_mode=plan_sort_mode)

        # ── Conflict warnings — displayed prominently ─────────────────────
        conflict_warnings = scheduler.detect_conflicts(plan.scheduled)
        if conflict_warnings:
            st.error(
                "⚠️ **" + str(len(conflict_warnings))
                + " scheduling conflict(s) detected.** "
                "Review the warnings below and adjust task times or durations."
            )
            for w in conflict_warnings:
                st.warning(w)
        else:
            st.success(
                "✅ No conflicts detected — all tasks fit without overlap."
            )

        # ── Pending / completed filter preview ────────────────────────────
        pending = scheduler.filter_by_completion(False)
        done    = scheduler.filter_by_completion(True)
        if done:
            st.info(
                str(len(done)) + " task(s) already marked complete and excluded from plan. "
                + str(len(pending)) + " pending task(s) scheduled."
            )

        # ── Plan summary banner ───────────────────────────────────────────
        SPECIES_ICON_PLAN = SPECIES_ICON.get(pet.species, "🐾")
        st.success(
            SPECIES_ICON_PLAN + " Plan ready for **" + pet.name
            + "** (" + pet.species + ")  ·  "
            + str(len(plan.scheduled)) + " tasks scheduled  ·  "
            + str(plan.total_minutes) + " / " + str(available) + " min  ·  💾 saved"
        )

        # ── Scheduled tasks table ─────────────────────────────────────────
        rows = []
        for st_task in plan.scheduled:
            rows.append({
                "Time":     st_task.start_time_str() + " – " + st_task.end_time_str(),
                "Task":     st_task.task.title,
                "Duration": str(st_task.task.duration_minutes) + " min",
                "Priority": PRIORITY_BADGE[st_task.task.priority],
                "Notes":    st_task.task.notes or "—",
            })

        if rows:
            st.markdown("### ✅ Scheduled tasks")
            st.table(rows)

        # ── Skipped tasks ─────────────────────────────────────────────────
        if plan.skipped:
            st.markdown("### ⏭️ Skipped — not enough time")
            for skipped in plan.skipped:
                st.markdown(
                    "- " + PRIORITY_COLOR[skipped.priority]
                    + " **" + skipped.title + "** ("
                    + str(skipped.duration_minutes) + " min, "
                    + skipped.priority + " priority)"
                )

        # ── Progress bar ──────────────────────────────────────────────────
        pct = plan.total_minutes / int(available)
        st.markdown(
            "**Time used:** " + str(plan.total_minutes) + " / " + str(available) + " min"
        )
        st.progress(min(pct, 1.0))

        # ── Reasoning expander ────────────────────────────────────────────
        with st.expander("🧠 Why this plan? (scheduler reasoning)", expanded=False):
            for line in plan.reasoning:
                if "CONFLICT" in line:
                    st.warning(line)
                elif "Skipped" in line:
                    st.markdown("- ⏭️ " + line)
                elif "Scheduled" in line:
                    st.markdown("- ✅ " + line)
                else:
                    st.markdown("- " + line)

        # ── Auto-save ─────────────────────────────────────────────────────
        skipped_data = [
            {"title": s.title, "duration_minutes": s.duration_minutes, "priority": s.priority}
            for s in plan.skipped
        ]
        save_plan(
            pet_name=pet.name, species=pet.species,
            rows=rows, skipped=skipped_data,
            reasoning=plan.reasoning, conflicts=conflict_warnings,
            total_minutes=plan.total_minutes, available=int(available),
        )

# ---------------------------------------------------------------------------
# Section 5: Saved Plans
# ---------------------------------------------------------------------------

st.divider()
st.subheader("💾 Saved Plans")

if not st.session_state.saved_plans:
    st.info("No plans saved yet. Build a schedule above — it will be saved here automatically.")
else:
    saved      = st.session_state.saved_plans
    tab_labels = [
        SPECIES_ICON.get(saved[name]["species"], "🐾") + " " + name
        for name in saved
    ]
    tabs = st.tabs(tab_labels)

    for tab, pet_name in zip(tabs, saved):
        with tab:
            plan_data = saved[pet_name]
            render_saved_plan(plan_data)

            del_col, _ = st.columns([1, 5])
            with del_col:
                if st.button(
                    "🗑️ Delete plan",
                    key="del_plan_" + pet_name,
                    help="Remove saved plan for " + pet_name,
                ):
                    del st.session_state.saved_plans[pet_name]
                    st.rerun()
