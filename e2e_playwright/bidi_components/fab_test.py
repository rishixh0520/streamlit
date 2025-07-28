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

from playwright.sync_api import Page, expect

from e2e_playwright.conftest import wait_for_app_run


def test_fab_click_increments_session_state(app: Page):
    """Test that clicking the FAB button increments the session state counter."""
    # Initial state should show 0 clicks
    expect(app.get_by_text("Total FAB clicks this session: 0")).to_be_visible()

    # Click the FAB button
    fab_button = app.locator(".st-fab-button-element")
    expect(fab_button).to_be_visible()
    fab_button.click()
    wait_for_app_run(app)

    # Verify session state incremented
    expect(app.get_by_text("Total FAB clicks this session: 1")).to_be_visible()

    # Click again to verify it continues incrementing
    fab_button.click()
    wait_for_app_run(app)
    expect(app.get_by_text("Total FAB clicks this session: 2")).to_be_visible()
