"""Registry page - manage scan objects."""

import streamlit as st

from scan2mesh_gui.components.metrics_display import render_quality_badge
from scan2mesh_gui.components.sidebar import get_stage_icon
from scan2mesh_gui.config import get_config_manager
from scan2mesh_gui.models.scan_object import PipelineStage, QualityStatus, ScanObject
from scan2mesh_gui.services.object_service import ObjectService


def render_registry() -> None:
    """Render the object registry page."""
    st.title("Object Registry")

    # Check for selected profile
    current_profile = st.session_state.get("current_profile")
    if not current_profile:
        st.warning("Please select a profile first")
        if st.button("Go to Profiles"):
            st.session_state.navigate_to = "profiles"
            st.rerun()
        return

    st.markdown(f"Managing objects in **{current_profile.name}**")

    config = get_config_manager()
    service = ObjectService(config.profiles_dir, config.projects_dir)

    # Create new object section
    with st.expander("Add New Object", expanded=False):
        render_create_object_form(service, current_profile.id)

    st.divider()

    # Filter controls
    col1, col2, col3 = st.columns([3, 1, 1])

    with col1:
        search_query = st.text_input(
            "Search objects",
            placeholder="Search by name...",
            label_visibility="collapsed",
        )

    with col2:
        stage_filter = st.selectbox(
            "Stage",
            ["All"] + [s.value.capitalize() for s in PipelineStage],
            label_visibility="collapsed",
        )

    with col3:
        status_filter = st.selectbox(
            "Status",
            ["All"] + [s.value.upper() for s in QualityStatus],
            label_visibility="collapsed",
        )

    # Get objects with filters
    filter_stage = None
    if stage_filter != "All":
        filter_stage = PipelineStage(stage_filter.lower())

    filter_status = None
    if status_filter != "All":
        filter_status = QualityStatus(status_filter.lower())

    objects = service.list_objects(
        current_profile.id,
        filter_stage=filter_stage,
        filter_status=filter_status,
    )

    # Apply search filter
    if search_query:
        query_lower = search_query.lower()
        objects = [
            o for o in objects
            if query_lower in o.name.lower() or query_lower in o.display_name.lower()
        ]

    # Update session state counts
    all_objects = service.list_objects(current_profile.id)
    st.session_state.object_count = len(all_objects)
    st.session_state.status_counts = service.get_status_counts(current_profile.id)
    st.session_state.recent_objects = all_objects[:10]

    # Display objects
    st.subheader(f"Objects ({len(objects)})")

    if not objects:
        st.info("No objects yet. Add your first object above!")
        return

    for obj in objects:
        render_object_card(obj, service, current_profile.id)


def render_create_object_form(service: ObjectService, profile_id: str) -> None:
    """Render the create object form."""
    with st.form("create_object"):
        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input(
                "Object Name (ID) *",
                placeholder="e.g., ball_01 (lowercase, no spaces)",
            )
            display_name = st.text_input(
                "Display Name *",
                placeholder="e.g., Soccer Ball",
            )

        with col2:
            class_id = st.number_input(
                "Class ID *",
                min_value=0,
                max_value=9999,
                value=0,
            )
            tags_input = st.text_input(
                "Tags",
                placeholder="Comma-separated tags",
            )

        col3, col4 = st.columns(2)

        with col3:
            known_dimension = st.number_input(
                "Known Dimension (mm)",
                min_value=0.0,
                value=0.0,
                help="Enter a known measurement for scale calibration",
            )

        with col4:
            dimension_type = st.selectbox(
                "Dimension Type",
                ["", "diameter", "length", "width", "height"],
            )

        submitted = st.form_submit_button("Add Object")

        if submitted:
            if not name or not display_name:
                st.error("Object name and display name are required")
                return

            # Parse tags
            tags = []
            if tags_input:
                tags = [t.strip() for t in tags_input.split(",") if t.strip()]

            try:
                obj = service.create_object(
                    profile_id=profile_id,
                    name=name,
                    display_name=display_name,
                    class_id=int(class_id),
                    tags=tags,
                    known_dimension_mm=known_dimension if known_dimension > 0 else None,
                    dimension_type=dimension_type if dimension_type else None,
                )
                st.success(f"Object '{obj.display_name}' added successfully!")
                st.rerun()
            except ValueError as e:
                st.error(f"Failed to add object: {e}")


def render_object_card(obj: ScanObject, service: ObjectService, profile_id: str) -> None:
    """Render an object card."""
    with st.container():
        col1, col2, col3, col4 = st.columns([3, 2, 1, 2])

        with col1:
            st.markdown(f"**{obj.display_name}**")
            st.caption(f"ID: {obj.name} | Class: {obj.class_id}")

            if obj.tags:
                tags_html = " ".join(
                    f'<span style="background: #e9ecef; padding: 2px 6px; border-radius: 3px; font-size: 11px;">{tag}</span>'
                    for tag in obj.tags
                )
                st.markdown(tags_html, unsafe_allow_html=True)

        with col2:
            # Pipeline stage
            icon = get_stage_icon(obj.current_stage)
            st.markdown(f":{icon}: {obj.current_stage.value.capitalize()}")

            if obj.known_dimension_mm:
                st.caption(f"{obj.dimension_type}: {obj.known_dimension_mm:.1f}mm")

        with col3:
            # Quality status
            render_quality_badge(obj.quality_status, size="small")

        with col4:
            # Action buttons
            if st.button("Scan", key=f"scan_{obj.id}", type="primary"):
                st.session_state.selected_object = obj
                st.session_state.navigate_to = "capture_plan"
                st.rerun()

            if st.button("Delete", key=f"delete_{obj.id}"):
                service.delete_object(profile_id, obj.id)
                st.success("Object deleted")
                st.rerun()

        st.divider()


# Run the page when loaded directly by Streamlit
render_registry()
