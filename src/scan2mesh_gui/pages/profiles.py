"""Profiles page - manage scan profiles."""

import zipfile

import streamlit as st

from scan2mesh_gui.config import get_config_manager
from scan2mesh_gui.models.profile import Profile
from scan2mesh_gui.services.profile_service import ProfileService


def render_profiles() -> None:
    """Render the profiles management page."""
    st.title("Profiles")
    st.markdown("Manage your scan profiles")

    config = get_config_manager()
    service = ProfileService(config.profiles_dir)

    # Create new profile section
    with st.expander("Create New Profile", expanded=False):
        render_create_profile_form(service)

    # Import profile section
    with st.expander("Import Profile", expanded=False):
        render_import_section(service)

    st.divider()

    # Profile list
    profiles = service.list_profiles()

    if not profiles:
        st.info("No profiles yet. Create your first profile above!")
        return

    # Update session state
    st.session_state.profiles = profiles

    # Filter and search
    col1, col2 = st.columns([3, 1])
    with col1:
        search_query = st.text_input(
            "Search profiles",
            placeholder="Search by name or tag...",
            label_visibility="collapsed",
        )
    with col2:
        sort_by = st.selectbox(
            "Sort by",
            ["Updated", "Created", "Name"],
            label_visibility="collapsed",
        )

    # Filter profiles
    filtered_profiles = profiles
    if search_query:
        query_lower = search_query.lower()
        filtered_profiles = [
            p for p in profiles
            if query_lower in p.name.lower()
            or any(query_lower in tag.lower() for tag in p.tags)
        ]

    # Sort profiles
    if sort_by == "Name":
        filtered_profiles = sorted(filtered_profiles, key=lambda p: p.name.lower())
    elif sort_by == "Created":
        filtered_profiles = sorted(filtered_profiles, key=lambda p: p.created_at, reverse=True)
    # Default is already sorted by updated_at

    # Display profiles
    st.subheader(f"Profiles ({len(filtered_profiles)})")

    for profile in filtered_profiles:
        render_profile_card(profile, service)


def render_create_profile_form(service: ProfileService) -> None:
    """Render the create profile form."""
    with st.form("create_profile"):
        name = st.text_input(
            "Profile Name *",
            placeholder="e.g., RoboCup 2025 Objects",
        )
        description = st.text_area(
            "Description",
            placeholder="Optional description...",
        )
        tags_input = st.text_input(
            "Tags",
            placeholder="Comma-separated tags, e.g., robocup, 2025",
        )

        submitted = st.form_submit_button("Create Profile")

        if submitted:
            if not name:
                st.error("Profile name is required")
                return

            # Parse tags
            tags = []
            if tags_input:
                tags = [t.strip() for t in tags_input.split(",") if t.strip()]

            try:
                profile = service.create_profile(
                    name=name,
                    description=description,
                    tags=tags,
                )
                st.success(f"Profile '{profile.name}' created successfully!")
                st.session_state.current_profile = profile
                st.rerun()
            except ValueError as e:
                st.error(f"Failed to create profile: {e}")


def render_import_section(service: ProfileService) -> None:
    """Render the import profile section."""
    st.markdown("Upload a ZIP file to import a profile.")

    uploaded_file = st.file_uploader(
        "Choose a ZIP file",
        type=["zip"],
        key="import_profile_file",
        label_visibility="collapsed",
    )

    if uploaded_file is not None:
        if st.button("Import Profile", key="import_profile_btn"):
            try:
                zip_data = uploaded_file.read()
                profile = service.import_profile(zip_data)
                st.success(f"Profile '{profile.name}' imported successfully!")
                st.session_state.current_profile = profile
                st.rerun()
            except ValueError as e:
                st.error(f"Validation error: {e}")
            except zipfile.BadZipFile:
                st.error("Invalid ZIP file. Please upload a valid ZIP file.")
            except Exception as e:
                st.error(f"Import failed: {e}")


def render_edit_profile_form(profile: Profile, service: ProfileService) -> None:
    """Render the edit profile form."""
    with st.form(f"edit_profile_{profile.id}"):
        name = st.text_input(
            "Profile Name *",
            value=profile.name,
        )
        description = st.text_area(
            "Description",
            value=profile.description or "",
        )
        tags_input = st.text_input(
            "Tags",
            value=", ".join(profile.tags) if profile.tags else "",
            placeholder="Comma-separated tags",
        )

        col1, col2 = st.columns(2)
        with col1:
            submitted = st.form_submit_button("Save Changes")
        with col2:
            cancelled = st.form_submit_button("Cancel")

        if submitted:
            if not name:
                st.error("Profile name is required")
                return

            # Parse tags
            tags = []
            if tags_input:
                tags = [t.strip() for t in tags_input.split(",") if t.strip()]

            try:
                updated_profile = service.update_profile(
                    profile_id=profile.id,
                    name=name,
                    description=description if description else None,
                    tags=tags,
                )
                if updated_profile:
                    st.success("Profile updated successfully!")
                    # Update current profile if it was selected
                    if st.session_state.get("current_profile"):
                        if st.session_state.current_profile.id == profile.id:
                            st.session_state.current_profile = updated_profile
                    # Clear editing state
                    st.session_state.editing_profile_id = None
                    st.rerun()
                else:
                    st.error("Failed to update profile")
            except ValueError as e:
                st.error(f"Failed to update profile: {e}")

        if cancelled:
            st.session_state.editing_profile_id = None
            st.rerun()


def render_export_download(profile: Profile, service: ProfileService) -> None:
    """Render the export download button."""
    try:
        zip_bytes = service.export_profile(profile.id)
        if zip_bytes:
            # Generate filename
            safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in profile.name)
            filename = f"{safe_name}_{profile.id[:8]}.zip"

            st.download_button(
                label="Download",
                data=zip_bytes,
                file_name=filename,
                mime="application/zip",
                key=f"download_{profile.id}",
            )
        else:
            st.error("Failed to export profile")
    except Exception as e:
        st.error(f"Export failed: {e}")


def render_profile_card(profile: Profile, service: ProfileService) -> None:
    """Render a profile card."""
    # Check if this profile is being edited
    is_editing = st.session_state.get("editing_profile_id") == profile.id

    if is_editing:
        render_edit_profile_form(profile, service)
        st.divider()
        return

    with st.container():
        col1, col2, col3 = st.columns([4, 2, 2])

        with col1:
            # Profile name and description
            st.markdown(f"**{profile.name}**")
            if profile.description:
                st.caption(profile.description)

            # Tags
            if profile.tags:
                tags_html = " ".join(
                    f'<span style="background: #e9ecef; padding: 2px 8px; border-radius: 4px; font-size: 12px;">{tag}</span>'
                    for tag in profile.tags
                )
                st.markdown(tags_html, unsafe_allow_html=True)

        with col2:
            # Timestamps
            st.caption(f"Updated: {profile.updated_at.strftime('%Y-%m-%d')}")
            st.caption(f"Created: {profile.created_at.strftime('%Y-%m-%d')}")

        with col3:
            # Actions - Row 1: Select
            current_profile = st.session_state.get("current_profile")
            is_selected = current_profile and current_profile.id == profile.id

            if is_selected:
                st.success("Selected")
            else:
                if st.button("Select", key=f"select_{profile.id}"):
                    st.session_state.current_profile = profile
                    st.session_state.navigate_to = "registry"
                    st.rerun()

            # Actions - Row 2: Edit, Export, Delete
            action_col1, action_col2, action_col3 = st.columns(3)
            with action_col1:
                if st.button("Edit", key=f"edit_{profile.id}"):
                    st.session_state.editing_profile_id = profile.id
                    st.rerun()
            with action_col2:
                render_export_download(profile, service)
            with action_col3:
                if st.button("Delete", key=f"delete_{profile.id}", type="secondary"):
                    st.session_state[f"confirm_delete_{profile.id}"] = True
                    st.rerun()

        # Confirmation dialog
        if st.session_state.get(f"confirm_delete_{profile.id}"):
            st.warning(f"Are you sure you want to delete '{profile.name}'? This cannot be undone.")
            confirm_col1, confirm_col2 = st.columns(2)
            with confirm_col1:
                if st.button("Yes, Delete", key=f"confirm_yes_{profile.id}"):
                    service.delete_profile(profile.id)
                    if current_profile and current_profile.id == profile.id:
                        st.session_state.current_profile = None
                    del st.session_state[f"confirm_delete_{profile.id}"]
                    st.success("Profile deleted")
                    st.rerun()
            with confirm_col2:
                if st.button("Cancel", key=f"confirm_no_{profile.id}"):
                    del st.session_state[f"confirm_delete_{profile.id}"]
                    st.rerun()

        st.divider()


# Run the page when loaded directly by Streamlit
render_profiles()
