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

from __future__ import annotations

from typing import Any

from streamlit.components.v2.bidi_component import make_trigger_id
from streamlit.components.v2.presentation import make_bidi_component_presenter
from streamlit.runtime.state.common import WidgetMetadata
from streamlit.runtime.state.session_state import SessionState, Value


def test_session_state_merges_ccv2_trigger_values_via_presenter() -> None:
    """Integration: SessionState uses presenter to merge CCv2 trigger values.

    We simulate a CCv2 component with a persistent state widget and an internal
    trigger aggregator. The component registers a presenter via the shared
    facade. We then assert that SessionState.filtered_state (user-facing view)
    returns the persistent state merged with the latest trigger values, while
    the underlying stored state remains unmodified.
    """

    session_state = SessionState()

    # Simulate a component persistent state widget with user key mapping
    component_id = "$$ID-bidi_component-my_component"
    user_key = "my_component"
    session_state._key_id_mapper[user_key] = component_id

    # Store base persistent state as {"value": {...}}
    base_persistent = {"value": {"alpha": 1}}
    session_state._new_widget_state.states[component_id] = Value(base_persistent)
    session_state._new_widget_state.widget_metadata[component_id] = WidgetMetadata(
        id=component_id,
        deserializer=lambda x: x,
        serializer=lambda x: x,
        value_type="json_value",
    )

    # Create trigger aggregator and payloads
    aggregator_id = make_trigger_id(component_id, "events")
    session_state._new_widget_state.widget_metadata[aggregator_id] = WidgetMetadata(
        id=aggregator_id,
        deserializer=lambda x: x,
        serializer=lambda x: x,
        value_type="json_trigger_value",
    )
    session_state._new_widget_state.states[aggregator_id] = Value(
        [
            {"event": "foo", "value": True},
            {"event": "bar", "value": 123},
        ]
    )

    # Attach presenter (what bidi_component.py does during registration)
    presenter = make_bidi_component_presenter(aggregator_id)
    meta = session_state._new_widget_state.widget_metadata[component_id]
    object.__setattr__(meta, "presenter", presenter)

    # User-visible filtered state should show merged view
    merged = session_state.filtered_state[user_key]
    assert merged == {"value": {"alpha": 1, "foo": True, "bar": 123}}

    # Underlying stored state remains unmodified
    assert session_state._new_widget_state.states[component_id].value is base_persistent


def test_session_state_presenter_errors_degrade_gracefully() -> None:
    """Integration: presenter exceptions should not break SessionState access.

    If a presenter raises, SessionState should fall back to the base value
    without propagating exceptions to the caller.
    """

    session_state = SessionState()

    component_id = "$$ID-bidi_component-err_component"
    user_key = "err_component"
    session_state._key_id_mapper[user_key] = component_id

    base_persistent: dict[str, Any] = {"value": {"x": 1}}
    session_state._new_widget_state.states[component_id] = Value(base_persistent)
    meta = WidgetMetadata(
        id=component_id,
        deserializer=lambda x: x,
        serializer=lambda x: x,
        value_type="json_value",
    )
    object.__setattr__(
        meta, "presenter", lambda _b, _s: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    session_state._new_widget_state.widget_metadata[component_id] = meta

    # Access should not raise; should return base value instead
    assert session_state.filtered_state[user_key] == base_persistent
