import streamlit as st

# Logic layer imports (backend classes live in pawpal_system.py)
from pawpal_system import AvailabilityBlock, Owner, Pet, Scheduler, Task  # noqa: F401

from datetime import date, time

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

st.markdown(
    """
Welcome to the PawPal+ starter app.

This file is intentionally thin. It gives you a working Streamlit app so you can start quickly,
but **it does not implement the project logic**. Your job is to design the system and build it.

Use this app as your interactive demo once your backend classes/functions exist.
"""
)

with st.expander("Scenario", expanded=True):
    st.markdown(
        """
**PawPal+** is a pet care planning assistant. It helps a pet owner plan care tasks
for their pet(s) based on constraints like time, priority, and preferences.

You will design and implement the scheduling logic and connect it to this Streamlit UI.
"""
    )

with st.expander("What you need to build", expanded=True):
    st.markdown(
        """
At minimum, your system should:
- Represent pet care tasks (what needs to happen, how long it takes, priority)
- Represent the pet and the owner (basic info and preferences)
- Build a plan/schedule for a day that chooses and orders tasks based on constraints
- Explain the plan (why each task was chosen and when it happens)
"""
    )

st.divider()

st.subheader("Owner")
owner_name = st.text_input("Owner name", value="Jordan")

st.markdown("### Session vault (persistent objects)")
st.caption(
    "We store backend objects in st.session_state so they persist across reruns while you use the app."
)

# Treat st.session_state like a dictionary-backed vault for Python objects.
if "owner" not in st.session_state:
    st.session_state.owner = Owner(name=owner_name)
else:
    # Keep the stored object in sync with the latest UI input.
    st.session_state.owner.name = owner_name

if "id_counter" not in st.session_state:
    st.session_state.id_counter = 0


def _next_id(prefix: str) -> str:
    st.session_state.id_counter += 1
    return f"{prefix}-{st.session_state.id_counter}"


st.divider()
st.subheader("Pets")

with st.form("add_pet_form", clear_on_submit=True):
    new_pet_name = st.text_input("Pet name")
    new_pet_species = st.selectbox("Species", ["dog", "cat", "other"], key="new_pet_species")
    submitted_pet = st.form_submit_button("Add pet")

    if submitted_pet:
        if not new_pet_name.strip():
            st.error("Please enter a pet name.")
        else:
            pet = Pet(id=_next_id("pet"), name=new_pet_name.strip(), species=new_pet_species)
            st.session_state.owner.add_pet(pet)  # <-- Phase 2 method call
            st.session_state.active_pet_id = pet.id
            st.success(f"Added pet: {pet.name}")

if "active_pet_id" not in st.session_state and st.session_state.owner.pets:
    st.session_state.active_pet_id = st.session_state.owner.pets[0].id

pet_options = {p.id: f"{p.name} ({p.species})" for p in st.session_state.owner.pets}
if pet_options:
    st.session_state.active_pet_id = st.selectbox(
        "Select active pet",
        options=list(pet_options.keys()),
        format_func=lambda pid: pet_options[pid],
        key="active_pet_select",
    )
    active_pet = st.session_state.owner.get_pet(st.session_state.active_pet_id)
else:
    active_pet = None
    st.info("No pets yet. Add one above.")

st.markdown("### Tasks")
st.caption("Add a few tasks. In your final version, these should feed into your scheduler.")

if active_pet is not None:
    with st.form("add_task_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            task_title = st.text_input("Task title", value="Morning walk")
            category = st.selectbox(
                "Category",
                ["walk", "feeding", "meds", "grooming", "enrichment", "other"],
                index=0,
            )
        with col2:
            duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
            priority_label = st.selectbox("Priority", ["low", "medium", "high"], index=2)

        submitted_task = st.form_submit_button("Add task")

        if submitted_task:
            priority_map = {"low": 1, "medium": 3, "high": 5}
            task = Task(
                id=_next_id("task"),
                pet_id=active_pet.id,
                name=task_title.strip() or "Untitled task",
                category=category,
                duration_minutes=int(duration),
                priority=priority_map[priority_label],
            )
            active_pet.add_task(task)  # <-- Phase 2 method call
            st.success(f"Added task to {active_pet.name}: {task.name}")

    tasks_rows = [
        {
            "pet": p.name,
            "task": t.name,
            "category": t.category,
            "duration_min": t.duration_minutes,
            "priority": t.priority,
        }
        for p in st.session_state.owner.pets
        for t in p.get_tasks()
    ]
    if tasks_rows:
        st.write("Current tasks:")
        st.table(tasks_rows)
    else:
        st.info("No tasks yet. Add one above.")

st.divider()

st.subheader("Build Schedule")
st.caption("Generate a daily plan based on your availability blocks and task priorities.")

if not st.session_state.owner.availability_blocks:
    st.session_state.owner.add_availability_block(
        AvailabilityBlock(
            id="morning",
            label="Morning",
            start_time=time(8, 0),
            end_time=time(10, 0),
            capacity_minutes=120,
        )
    )
    st.session_state.owner.add_availability_block(
        AvailabilityBlock(
            id="evening",
            label="Evening",
            start_time=time(18, 0),
            end_time=time(19, 30),
            capacity_minutes=90,
        )
    )

if st.button("Generate schedule"):
    scheduler = Scheduler()
    plan = scheduler.generate_daily_plan(
        owner=st.session_state.owner,
        tasks=st.session_state.owner.get_all_tasks(),
        on_date=date.today(),
    )

    st.markdown("### Today's Schedule")
    rows = plan.to_display_rows(st.session_state.owner)
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("Nothing scheduled yet. Add tasks and try again.")

    if plan.unscheduled_tasks:
        st.markdown("### Unscheduled tasks")
        st.table(
            [
                {
                    "task": t.name,
                    "pet_id": t.pet_id,
                    "duration_min": t.duration_minutes,
                    "priority": t.priority,
                }
                for t in plan.unscheduled_tasks
            ]
        )
