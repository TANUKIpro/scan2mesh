"""Profiles page - manage scan profiles."""

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


def render_profile_card(profile: Profile, service: ProfileService) -> None:
    """Render a profile card."""
    with st.container():
        col1, col2, col3 = st.columns([4, 2, 1])

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
            # Actions
            current_profile = st.session_state.get("current_profile")
            is_selected = current_profile and current_profile.id == profile.id

            if is_selected:
                st.success("Selected")
            else:
                if st.button("Select", key=f"select_{profile.id}"):
                    st.session_state.current_profile = profile
                    st.session_state.navigate_to = "registry"
                    st.rerun()

            # Delete button (with confirmation)
            if st.button("Delete", key=f"delete_{profile.id}", type="secondary"):
                st.session_state[f"confirm_delete_{profile.id}"] = True
                st.rerun()

        # Confirmation dialog
        if st.session_state.get(f"confirm_delete_{profile.id}"):
            st.warning(f"Are you sure you want to delete '{profile.name}'? This cannot be undone.")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Yes, Delete", key=f"confirm_yes_{profile.id}"):
                    service.delete_profile(profile.id)
                    if current_profile and current_profile.id == profile.id:
                        st.session_state.current_profile = None
                    del st.session_state[f"confirm_delete_{profile.id}"]
                    st.success("Profile deleted")
                    st.rerun()
            with col2:
                if st.button("Cancel", key=f"confirm_no_{profile.id}"):
                    del st.session_state[f"confirm_delete_{profile.id}"]
                    st.rerun()

        st.divider()


# Run the page when loaded directly by Streamlit
render_profiles()
