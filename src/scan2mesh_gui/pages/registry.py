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


def render_object_detail(
    obj: ScanObject, service: ObjectService, profile_id: str
) -> None:
    """Render the object detail section."""
    with st.container():
        st.markdown("---")
        st.markdown("#### Object Details")

        # Layout: Preview image (left) and info (right)
        col_preview, col_info = st.columns([1, 2])

        with col_preview:
            # Preview image
            if obj.preview_image:
                image_path = service.get_reference_image_path(
                    profile_id, obj.id, obj.preview_image
                )
                if image_path:
                    st.image(str(image_path), caption="Preview", use_container_width=True)
                else:
                    st.info("Preview image not found")
            else:
                st.info("No preview image")

        with col_info:
            # Settings
            st.markdown("**Settings**")
            st.markdown(f"- **Name (ID):** `{obj.name}`")
            st.markdown(f"- **Display Name:** {obj.display_name}")
            st.markdown(f"- **Class ID:** {obj.class_id}")

            if obj.known_dimension_mm and obj.dimension_type:
                st.markdown(
                    f"- **Known Dimension:** {obj.known_dimension_mm:.1f}mm ({obj.dimension_type})"
                )
            elif obj.known_dimension_mm:
                st.markdown(f"- **Known Dimension:** {obj.known_dimension_mm:.1f}mm")

            if obj.tags:
                st.markdown(f"- **Tags:** {', '.join(obj.tags)}")

        # Pipeline Status
        col_status, col_timestamps = st.columns(2)

        with col_status:
            st.markdown("**Pipeline Status**")
            stage_icon = get_stage_icon(obj.current_stage)
            st.markdown(f"- **Current Stage:** :{stage_icon}: {obj.current_stage.value.capitalize()}")

            status_colors = {
                QualityStatus.PASS: "green",
                QualityStatus.WARN: "orange",
                QualityStatus.FAIL: "red",
                QualityStatus.PENDING: "gray",
            }
            status_color = status_colors.get(obj.quality_status, "gray")
            st.markdown(
                f"- **Quality Status:** :{status_color}[{obj.quality_status.value.upper()}]"
            )

        with col_timestamps:
            st.markdown("**Timestamps**")
            st.markdown(f"- **Created:** {obj.created_at.strftime('%Y-%m-%d %H:%M')}")
            st.markdown(f"- **Updated:** {obj.updated_at.strftime('%Y-%m-%d %H:%M')}")
            if obj.last_scan_at:
                st.markdown(
                    f"- **Last Scan:** {obj.last_scan_at.strftime('%Y-%m-%d %H:%M')}"
                )
            else:
                st.markdown("- **Last Scan:** Never")

        # Reference images section
        render_reference_images(obj, service, profile_id)


def render_reference_images(
    obj: ScanObject, service: ObjectService, profile_id: str
) -> None:
    """Render the reference images section."""
    st.markdown("**Reference Images**")

    # Display existing images
    if obj.reference_images:
        cols = st.columns(min(len(obj.reference_images), 4))
        for i, rel_path in enumerate(obj.reference_images):
            with cols[i % 4]:
                image_path = service.get_reference_image_path(profile_id, obj.id, rel_path)
                if image_path:
                    st.image(str(image_path), use_container_width=True)
                    # Delete button
                    if st.button("Delete", key=f"del_img_{obj.id}_{i}"):
                        if service.delete_reference_image(profile_id, obj.id, rel_path):
                            st.success("Image deleted")
                            st.rerun()
                        else:
                            st.error("Failed to delete image")
    else:
        st.caption("No reference images uploaded yet.")

    # Upload new image
    uploaded_file = st.file_uploader(
        "Upload Reference Image",
        type=["png", "jpg", "jpeg"],
        key=f"upload_ref_{obj.id}",
        help="Upload PNG or JPEG images (max 10MB)",
    )

    if uploaded_file is not None and st.button("Add Image", key=f"add_img_{obj.id}"):
        try:
            image_data = uploaded_file.read()
            service.add_reference_image(
                profile_id=profile_id,
                object_id=obj.id,
                image_data=image_data,
                filename=uploaded_file.name,
                mime_type=uploaded_file.type,
            )
            st.success("Image uploaded successfully!")
            st.rerun()
        except ValueError as e:
            st.error(f"Upload failed: {e}")


def render_edit_object_form(
    obj: ScanObject, service: ObjectService, profile_id: str
) -> None:
    """Render the edit object form."""
    with st.form(f"edit_object_{obj.id}"):
        st.markdown(f"### Edit: {obj.name}")

        col1, col2 = st.columns(2)

        with col1:
            display_name = st.text_input(
                "Display Name *",
                value=obj.display_name,
            )
            class_id = st.number_input(
                "Class ID *",
                min_value=0,
                max_value=9999,
                value=obj.class_id,
            )

        with col2:
            tags_input = st.text_input(
                "Tags",
                value=", ".join(obj.tags) if obj.tags else "",
                placeholder="Comma-separated tags",
            )
            known_dimension = st.number_input(
                "Known Dimension (mm)",
                min_value=0.0,
                value=obj.known_dimension_mm if obj.known_dimension_mm else 0.0,
                help="Enter a known measurement for scale calibration",
            )

        dimension_type = st.selectbox(
            "Dimension Type",
            ["", "diameter", "length", "width", "height"],
            index=(
                ["", "diameter", "length", "width", "height"].index(obj.dimension_type)
                if obj.dimension_type
                else 0
            ),
        )

        col_save, col_cancel = st.columns(2)
        with col_save:
            submitted = st.form_submit_button("Save Changes")
        with col_cancel:
            cancelled = st.form_submit_button("Cancel")

        if submitted:
            if not display_name:
                st.error("Display name is required")
                return

            # Parse tags
            tags = []
            if tags_input:
                tags = [t.strip() for t in tags_input.split(",") if t.strip()]

            try:
                updated_obj = service.update_object(
                    profile_id=profile_id,
                    object_id=obj.id,
                    display_name=display_name,
                    class_id=int(class_id),
                    tags=tags,
                    known_dimension_mm=known_dimension if known_dimension > 0 else None,
                    dimension_type=dimension_type if dimension_type else None,
                )
                if updated_obj:
                    st.success("Object updated successfully!")
                    # Update selected object if it was selected
                    selected = st.session_state.get("selected_object")
                    if selected and selected.id == obj.id:
                        st.session_state.selected_object = updated_obj
                    # Clear editing state
                    st.session_state.editing_object_id = None
                    st.rerun()
                else:
                    st.error("Failed to update object")
            except ValueError as e:
                st.error(f"Failed to update object: {e}")

        if cancelled:
            st.session_state.editing_object_id = None
            st.rerun()


def render_object_card(obj: ScanObject, service: ObjectService, profile_id: str) -> None:
    """Render an object card."""
    # Check if this object is being edited
    is_editing = st.session_state.get("editing_object_id") == obj.id

    if is_editing:
        render_edit_object_form(obj, service, profile_id)
        st.divider()
        return

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
            # Action buttons - Row 1: Scan
            if st.button("Scan", key=f"scan_{obj.id}", type="primary"):
                st.session_state.selected_object = obj
                st.session_state.navigate_to = "capture_plan"
                st.rerun()

            # Action buttons - Row 2: Edit, Details, Delete
            action_col1, action_col2, action_col3 = st.columns(3)
            with action_col1:
                if st.button("Edit", key=f"edit_{obj.id}"):
                    st.session_state.editing_object_id = obj.id
                    st.rerun()
            with action_col2:
                if st.button("Details", key=f"details_{obj.id}"):
                    if st.session_state.get("expanded_object_id") == obj.id:
                        st.session_state.expanded_object_id = None
                    else:
                        st.session_state.expanded_object_id = obj.id
                    st.rerun()
            with action_col3:
                if st.button("Delete", key=f"delete_{obj.id}"):
                    st.session_state[f"confirm_delete_obj_{obj.id}"] = True
                    st.rerun()

        # Confirmation dialog for deletion
        if st.session_state.get(f"confirm_delete_obj_{obj.id}"):
            st.warning(
                f"Are you sure you want to delete '{obj.display_name}'? This cannot be undone."
            )
            confirm_col1, confirm_col2 = st.columns(2)
            with confirm_col1:
                if st.button("Yes, Delete", key=f"confirm_yes_{obj.id}"):
                    service.delete_object(profile_id, obj.id)
                    if (
                        st.session_state.get("selected_object")
                        and st.session_state.selected_object.id == obj.id
                    ):
                        st.session_state.selected_object = None
                    del st.session_state[f"confirm_delete_obj_{obj.id}"]
                    st.success("Object deleted")
                    st.rerun()
            with confirm_col2:
                if st.button("Cancel", key=f"confirm_no_{obj.id}"):
                    del st.session_state[f"confirm_delete_obj_{obj.id}"]
                    st.rerun()

        # Object details section (expandable)
        if st.session_state.get("expanded_object_id") == obj.id:
            render_object_detail(obj, service, profile_id)

        st.divider()


# Run the page when loaded directly by Streamlit
render_registry()
