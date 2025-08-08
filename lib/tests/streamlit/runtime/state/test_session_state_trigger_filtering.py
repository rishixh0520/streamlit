# Copyright (c) Streamlit Inc. (2018-2022) Snowflake Inc. (2022-2025)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Unit tests for session state filtering of trigger widgets.

These tests verify that trigger widgets created by bidi_component
are properly filtered out of the session state exposed to users.
"""

from __future__ import annotations

from streamlit.components.v2.bidi_component import make_trigger_id
from streamlit.runtime.state.common import WidgetMetadata
from streamlit.runtime.state.session_state import SessionState, Value


def test_filtered_state_excludes_trigger_widgets() -> None:
    """Test that filtered_state excludes trigger widgets from session state.

    Trigger widgets should not appear when users access st.session_state,
    even though they exist internally for handling events.
    """
    session_state = SessionState()

    # Create some regular session state entries
    session_state["regular_key"] = "regular_value"
    session_state["user_counter"] = 42

    # Simulate trigger widgets being registered (this would normally happen
    # through the bidi_component registration process)
    component_id = "my_component_123"
    click_trigger_id = make_trigger_id(component_id, "click")
    change_trigger_id = make_trigger_id(component_id, "change")

    # Add trigger widgets to internal widget state
    session_state._new_widget_state.states[click_trigger_id] = Value(True)
    session_state._new_widget_state.states[change_trigger_id] = Value(None)

    # Add metadata for the trigger widgets
    click_metadata = WidgetMetadata(
        id=click_trigger_id,
        deserializer=lambda x: x or False,
        serializer=lambda x: x,
        value_type="json_trigger_value",
    )
    change_metadata = WidgetMetadata(
        id=change_trigger_id,
        deserializer=lambda x: x,
        serializer=lambda x: x,
        value_type="json_trigger_value",
    )

    session_state._new_widget_state.widget_metadata[click_trigger_id] = click_metadata
    session_state._new_widget_state.widget_metadata[change_trigger_id] = change_metadata

    # Get filtered state (what users see via st.session_state)
    filtered = session_state.filtered_state

    # Regular keys should be present
    assert "regular_key" in filtered
    assert "user_counter" in filtered
    assert filtered["regular_key"] == "regular_value"
    assert filtered["user_counter"] == 42

    # Trigger widgets should be filtered out
    assert click_trigger_id not in filtered
    assert change_trigger_id not in filtered

    # Verify the trigger widgets still exist internally
    assert click_trigger_id in session_state._new_widget_state.states
    assert change_trigger_id in session_state._new_widget_state.states


def test_filtered_state_includes_keyed_widgets() -> None:
    """Test that filtered_state includes regular keyed widgets.

    Regular widgets with user keys should still appear in session state,
    even after adding trigger widget filtering.
    """
    session_state = SessionState()

    # Create a regular widget with a user key
    widget_id = "$$ID-my_button-my_key"
    user_key = "my_key"

    # Set up key mapping
    session_state._key_id_mapper[user_key] = widget_id

    # Add widget state
    session_state._new_widget_state.states[widget_id] = Value(False)

    # Add metadata
    metadata = WidgetMetadata(
        id=widget_id,
        deserializer=lambda x: x or False,
        serializer=lambda x: x,
        value_type="bool_value",
    )
    session_state._new_widget_state.widget_metadata[widget_id] = metadata

    # Get filtered state
    filtered = session_state.filtered_state

    # The widget should appear under its user key
    assert user_key in filtered
    assert filtered[user_key] is False


def test_filtered_state_excludes_internal_keyed_widgets() -> None:
    """Test that filtered_state excludes keyed widgets that are internal.

    If a trigger widget somehow had a user key, it should still be
    filtered out because it has the internal key prefix.
    """
    session_state = SessionState()

    # Create a trigger widget that hypothetically has a user key
    component_id = "my_component_123"
    trigger_id = make_trigger_id(component_id, "click")
    user_key = "trigger_key"  # This shouldn't happen in practice

    # Set up key mapping
    session_state._key_id_mapper[user_key] = trigger_id

    # Add widget state
    session_state._new_widget_state.states[trigger_id] = Value(True)

    # Add metadata
    metadata = WidgetMetadata(
        id=trigger_id,
        deserializer=lambda x: x or False,
        serializer=lambda x: x,
        value_type="json_trigger_value",
    )
    session_state._new_widget_state.widget_metadata[trigger_id] = metadata

    # Get filtered state
    filtered = session_state.filtered_state

    # The trigger widget should be filtered out even if it has a user key
    assert user_key not in filtered
    assert trigger_id not in filtered


def test_session_state_iteration_excludes_trigger_widgets() -> None:
    """Test that iterating over session state excludes trigger widgets.

    When users iterate over st.session_state, trigger widgets should
    not appear in the iteration.
    """
    session_state = SessionState()

    # Add regular session state
    session_state["regular_key"] = "value"

    # Add trigger widget
    component_id = "my_component_123"
    trigger_id = make_trigger_id(component_id, "click")
    session_state._new_widget_state.states[trigger_id] = Value(True)

    # Add metadata for trigger widget
    metadata = WidgetMetadata(
        id=trigger_id,
        deserializer=lambda x: x or False,
        serializer=lambda x: x,
        value_type="json_trigger_value",
    )
    session_state._new_widget_state.widget_metadata[trigger_id] = metadata

    # Get all keys that would be visible to users
    visible_keys = list(session_state.filtered_state.keys())

    # Only regular keys should be visible
    assert "regular_key" in visible_keys
    assert trigger_id not in visible_keys
    assert (
        len([k for k in visible_keys if k.startswith("$$STREAMLIT_INTERNAL_KEY")]) == 0
    )
