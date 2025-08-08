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

from streamlit.runtime.state.common import WidgetMetadata
from streamlit.runtime.state.session_state import SessionState


def test_per_key_callbacks_only_fire_for_changed_keys() -> None:
    calls: list[str] = []

    def cb_a() -> None:
        calls.append("a")

    def cb_b() -> None:
        calls.append("b")

    ss = SessionState()
    wid = "w-json"
    meta = WidgetMetadata(
        id=wid,
        deserializer=lambda v: v,
        serializer=lambda v: v,
        value_type="json_value",
        callbacks={"a": cb_a, "b": cb_b},
    )

    # Register metadata
    ss._set_widget_metadata(meta)

    # Old state: {value: {a:1, b:2}}
    ss._old_state[wid] = {"value": {"a": 1, "b": 2}}
    # New state: {value: {a:1, b:3}}
    ss._new_widget_state.set_from_value(wid, {"value": {"a": 1, "b": 3}})

    # Drive callback pump
    ss._call_callbacks()

    assert calls == ["b"]
