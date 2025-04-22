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

import pandas as pd

import streamlit as st

if TYPE_CHECKING:
    from streamlit.components.v2.bidi_component import BidiComponentResult

component_name = "my_arrow_component"


def my_arrow_component(key: str, data: Any) -> BidiComponentResult:
    component = st.components.v2.component(
        component_name,
        js="""
export default function(component) {
  const { parentElement, data } = component

  const root = parentElement.querySelector("#my-arrow-component")

  const { df, df2, label } = data;
  const cols = df.schema.fields.map((f) => f.name);
  const rows = df.toArray();
  const cols2 = df2.schema.fields.map((f) => f.name);
  const rows2 = df2.toArray();

  root.innerText = `Label: ${label}\nCols: ${cols}\nRows: ${rows}\nCols2: ${cols2}\nRows2: ${rows2}`
}
""",
        html="""
<div id="my-arrow-component"></div>
""",
    )

    return component(key=key, data=data)


df = pd.DataFrame({"a": [1, 2, 3]})

df2 = pd.DataFrame({"b": [4, 5, 6]})

my_arrow_component(
    key="my_arrow_component",
    data={
        "df": df,  # Dataframe will be automatically detected and serialized as Arrow
        "df2": df2,  # Dataframe will be automatically detected and serialized as Arrow
        "label": "Hello World",
    },
)
