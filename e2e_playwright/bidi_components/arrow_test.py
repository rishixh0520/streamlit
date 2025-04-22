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


from playwright.sync_api import Page, expect


def test_arrow_serialization_works(app: Page):
    """Test that the component with multiple dataframes works and is serialized and deserialized correctly."""
    expect(app.get_by_text("Cols: a")).to_be_visible()
    expect(app.get_by_text('Rows: {"a": 1},{"a": 2},{"a": 3}')).to_be_visible()
    expect(app.get_by_text("Cols2: b")).to_be_visible()
    expect(app.get_by_text('Rows2: {"b": 4},{"b": 5},{"b": 6}')).to_be_visible()
    expect(app.get_by_text("Label: Hello World")).to_be_visible()
