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

from typing import TYPE_CHECKING, Any

import streamlit as st

if TYPE_CHECKING:
    from streamlit.elements.lib.bidi_component_delta_generator import (
        BidiComponentDeltaGenerator,
    )
    from streamlit.runtime.state.common import WidgetCallback

st.header("Bidi Component")

JS_CODE = """
export default function(component) {
  const { parentElement, setStateValue } = component

  const handleRangeChange = (event) => {
    setStateValue("range", event.target.value)
  }

  const handleTextChange = (event) => {
    setStateValue("text_value", event.target.value)
  }

  const rangeInput = parentElement.querySelector("#range")
  rangeInput.addEventListener("change", handleRangeChange)

  const textInput = parentElement.querySelector("#text")
  textInput.addEventListener("input", handleTextChange)

  return () => {
    rangeInput.removeEventListener("change", handleRangeChange)
    textInput.removeEventListener("input", handleTextChange)
  }
}
"""

HTML_CODE = """
<div>
  <label for="range">Range</label>
  <input type="range" id="range" min="0" max="100" value="50" />
  <label for="text">Text</label>
  <input type="text" id="text" value="Text input" />
</div>
"""

CSS_CODE = """
label {
  color: var(--st-colors-primary);
}
"""

_my_component_dg = st.components.v2.component_dg(
    "my_component_dg",
    js=JS_CODE,
    html=HTML_CODE,
    css=CSS_CODE,
)


def my_component_dg(
    *,
    key: str | None = None,
    data: Any | None = None,
    on_range_change: WidgetCallback | None = None,
    on_text_value_change: WidgetCallback | None = None,
) -> BidiComponentDeltaGenerator:
    out = _my_component_dg(
        isolate_styles=True,
        key=key,
        data=data,
        on_range_change=on_range_change,
        on_text_value_change=on_text_value_change,
    )
    return out


if "range_change_count" not in st.session_state:
    st.session_state.range_change_count = 0
if "text_change_count" not in st.session_state:
    st.session_state.text_change_count = 0


def handle_range_change():
    st.session_state.range_change_count += 1


def handle_text_value_change():
    st.session_state.text_change_count += 1


result_dg = my_component_dg(
    key="my_component_2",
    on_range_change=handle_range_change,
    on_text_value_change=handle_text_value_change,
)
result_dg.write("Hello from result_dg.write")

st.write(f"Result: {result_dg}")
st.write(f"Result: range: `{result_dg.range}`, text_value: `{result_dg.text_value}`")


is_clicked = st.button("st.button trigger")

if is_clicked:
    st.write("st.button was clicked")
