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


def test_default_loads_correctly(app: Page):
    """Test that the component loads with the correct default state values."""
    # Check that the range input has the default value of 20
    expect(app.get_by_label("Range")).to_have_value("20")

    # Check that the text input has the default value
    expect(app.get_by_label("Text")).to_have_value("Text input")

    # Verify the result shows the default state
    expect(
        app.get_by_text(
            "Result: {'delta_generator': DeltaGenerator(), "
            "'formValues': {'range': 20, 'text': 'Text input'}, "
            "'clicked': None}"
        )
    ).to_be_visible()


def test_form_submission_triggers_on_change(app: Page):
    """Test that submitting the form triggers the on_change callback."""
    # Change the range value
    app.get_by_label("Range").fill("50")

    # Change the text value
    app.get_by_label("Text").fill("Modified text")

    # Submit the form
    app.get_by_text("Submit form").click()

    # Wait for the app to update and check the result reflects the new values
    expect(
        app.get_by_text(
            "Result: {'delta_generator': DeltaGenerator(), "
            "'formValues': {'range': '50', 'text': 'Modified text'}, "
            "'clicked': True}"
        )
    ).to_be_visible()
