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
    from streamlit.components.v2.bidi_component import BidiComponentResult
    from streamlit.runtime.state.common import WidgetCallback


st.header("Bidi Component")


default = {
    "formValues": {
        "range": 20,
        "text": "Text input",
    },
}


JS_CODE = """
export default function(component) {
  const { data, parentElement, setStateValue, setTriggerValue } = component

  console.log(component)
  const form = parentElement.querySelector("form")
  const handleSubmit = (event) => {
    event.preventDefault()
    const formValues = {
      range: event.target.range.value,
      text: event.target.text.value,
    }
    setStateValue("formValues", formValues)
  }

  form.addEventListener("submit", handleSubmit)

  const handleClick = () => {
    setTriggerValue("clicked", true)
  }

  parentElement.addEventListener("click", handleClick)

  return () => {
    form.removeEventListener("submit", handleSubmit)
    parentElement.removeEventListener("click", handleClick)
  }
}
"""

HTML_CODE = f"""
<h1>Hello World</h1>
<form>
  <label for="range">Range</label>
  <input type="range" id="range" min="0" max="100" value="{default["formValues"]["range"]}" />
  <label for="text">Text</label>
  <input type="text" id="text" value="{default["formValues"]["text"]}" />
  <button type="submit">Submit form</button>
</form>
"""

CSS_CODE = """
div {
    color: var(--st-primary-color);
    background-color: var(--st-background-color);
}
"""


def my_component(
    *,
    key: str | None = None,
    data: Any | None = None,
    on_formValues_change: WidgetCallback | None = None,  # noqa: N803
    on_clicked_change: WidgetCallback | None = None,
    default: dict[str, Any] | None = None,
) -> BidiComponentResult:
    component = st.components.v2.component(
        name="my_component",
        js=JS_CODE,
        html=HTML_CODE,
        css=CSS_CODE,
    )

    return component(
        isolate_styles=True,
        key=key,
        data=data,
        on_formValues_change=on_formValues_change,
        on_clicked_change=on_clicked_change,
        default=default,
    )


if "click_count" not in st.session_state:
    st.session_state.click_count = 0


def handle_click():
    st.session_state.click_count += 1


def handle_change():
    pass


result = my_component(
    key="my_component_1",
    data={"label": "Some data from python"},
    on_formValues_change=handle_change,
    on_clicked_change=handle_click,
    default=default,
)

st.write(f"Result: {result}")
st.text(f"session_state: {st.session_state.get('my_component_1')}")

st.write(f"Click count: {st.session_state.click_count}")
