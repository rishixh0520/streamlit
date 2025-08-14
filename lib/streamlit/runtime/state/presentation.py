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


def present_for_session(session_state: Any, widget_id: str, base_value: Any) -> Any:
    """Return the user-visible value for a widget in st.session_state.

    This facade isolates presentation concerns from core session state logic.
    If the widget provides a `presenter` in its metadata, that presenter is
    used to transform the widget's stored value into the user-visible value.

    Any exceptions raised by presenters are swallowed and the base value is
    returned, so that presentation never interferes with core behavior.
    """

    try:
        meta = session_state._new_widget_state.widget_metadata.get(widget_id)
        presenter = getattr(meta, "presenter", None) if meta is not None else None
        if presenter is None:
            return base_value
        try:
            return presenter(base_value, session_state)
        except Exception:
            return base_value
    except Exception:
        # If metadata is unavailable or any other error occurs, degrade gracefully.
        return base_value
