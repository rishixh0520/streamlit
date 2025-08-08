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

"""Unit tests for trigger widget filtering in bidi components.

These tests verify that trigger widgets created by bidi_component
are properly marked as internal and filtered out of st.session_state.
"""

from __future__ import annotations

import pytest

from streamlit.components.v2.bidi_component import EVENT_DELIM, make_trigger_id
from streamlit.errors import StreamlitAPIException
from streamlit.runtime.state.session_state import (
    STREAMLIT_INTERNAL_KEY_PREFIX,
    _is_internal_key,
)


def test_make_trigger_id_creates_internal_key() -> None:
    """Test that make_trigger_id creates widget IDs with internal prefix.

    Trigger widgets should be marked as internal so they don't appear
    in st.session_state when accessed by end users.
    """
    base_id = "my_component_123"
    event = "click"

    trigger_id = make_trigger_id(base_id, event)

    # Should start with internal prefix
    assert trigger_id.startswith(STREAMLIT_INTERNAL_KEY_PREFIX), (
        f"Trigger ID should start with {STREAMLIT_INTERNAL_KEY_PREFIX}, got: {trigger_id}"
    )

    # Should contain the base component ID
    assert base_id in trigger_id, (
        f"Trigger ID should contain base '{base_id}', got: {trigger_id}"
    )

    # Should contain the event name
    assert event in trigger_id, (
        f"Trigger ID should contain event '{event}', got: {trigger_id}"
    )

    # Should contain the event delimiter
    assert EVENT_DELIM in trigger_id, (
        f"Trigger ID should contain delimiter '{EVENT_DELIM}', got: {trigger_id}"
    )


def test_trigger_id_is_detected_as_internal() -> None:
    """Test that trigger widget IDs are correctly identified as internal keys."""
    base_id = "my_component_123"
    event = "click"

    trigger_id = make_trigger_id(base_id, event)

    # Trigger ID should be detected as internal
    assert _is_internal_key(trigger_id), (
        f"Trigger ID should be detected as internal: {trigger_id}"
    )


def test_regular_keys_are_not_detected_as_internal() -> None:
    """Test that regular keys and widget IDs are not detected as internal."""
    regular_key = "user_defined_key"
    regular_widget_id = "$$ID-my_widget-None"  # Typical auto-generated widget ID
    component_id = "my_component_main_widget"  # Component main widget ID

    # Regular keys should not be detected as internal
    assert not _is_internal_key(regular_key), (
        f"Regular key should not be detected as internal: {regular_key}"
    )
    assert not _is_internal_key(regular_widget_id), (
        f"Regular widget ID should not be detected as internal: {regular_widget_id}"
    )
    assert not _is_internal_key(component_id), (
        f"Component ID should not be detected as internal: {component_id}"
    )


def test_make_trigger_id_validates_base_delimiter() -> None:
    """Test that make_trigger_id raises exception if base contains delimiter."""
    with pytest.raises(StreamlitAPIException, match="delimiter sequence"):
        make_trigger_id("base__with__delim", "click")


def test_make_trigger_id_validates_event_delimiter() -> None:
    """Test that make_trigger_id raises exception if event contains delimiter."""
    with pytest.raises(StreamlitAPIException, match="delimiter sequence"):
        make_trigger_id("normal_base", "click__event")


def test_make_trigger_id_normal_case() -> None:
    """Test that make_trigger_id works correctly for normal inputs."""
    base_id = "normal_base"
    event = "normal_event"

    trigger_id = make_trigger_id(base_id, event)

    # Should succeed and return a valid internal key
    assert trigger_id is not None
    assert _is_internal_key(trigger_id)
    assert base_id in trigger_id
    assert event in trigger_id


def test_multiple_trigger_ids_are_all_internal() -> None:
    """Test that multiple trigger IDs for the same component are all internal."""
    base_id = "my_component_456"
    events = ["click", "change", "submit", "hover"]

    trigger_ids = [make_trigger_id(base_id, event) for event in events]

    # All trigger IDs should be internal
    for trigger_id in trigger_ids:
        assert _is_internal_key(trigger_id), (
            f"All trigger IDs should be internal: {trigger_id}"
        )

    # All trigger IDs should be unique
    assert len(trigger_ids) == len(set(trigger_ids)), "All trigger IDs should be unique"
