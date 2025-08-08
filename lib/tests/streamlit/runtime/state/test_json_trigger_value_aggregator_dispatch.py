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

import json

from streamlit.proto.WidgetStates_pb2 import WidgetState as WidgetStateProto
from streamlit.runtime.state.common import WidgetMetadata
from streamlit.runtime.state.session_state import SessionState


def test_json_trigger_aggregator_routes_to_named_callback() -> None:
    called: list[str] = []

    def cb_click() -> None:
        called.append("click")

    def cb_submit() -> None:
        called.append("submit")

    ss = SessionState()
    wid = "w-trig"
    meta = WidgetMetadata(
        id=wid,
        # Convert JSON string from proto into a dict
        deserializer=lambda s: json.loads(s) if s else None,
        serializer=lambda v: v,
        value_type="json_trigger_value",
        callbacks={"click": cb_click, "submit": cb_submit},
    )

    ss._set_widget_metadata(meta)

    # Emulate serialized proto received from frontend
    ws = WidgetStateProto(id=wid)
    ws.json_trigger_value = json.dumps({"event": "submit"})
    ss._new_widget_state.set_widget_from_proto(ws)

    ss._call_callbacks()
    assert called == ["submit"]
