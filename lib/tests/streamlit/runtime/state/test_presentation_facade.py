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

from types import SimpleNamespace
from typing import Any

from streamlit.runtime.state.presentation import present_for_session


class _FakeWStates:
    def __init__(self) -> None:
        self.widget_metadata: dict[str, Any] = {}


class _FakeSession:
    def __init__(self) -> None:
        self._new_widget_state = _FakeWStates()


def test_present_for_session_returns_base_when_no_meta() -> None:
    ss = _FakeSession()
    base = {"value": 1}
    out = present_for_session(ss, "wid", base)
    assert out is base


def test_present_for_session_returns_base_when_no_presenter() -> None:
    ss = _FakeSession()
    ss._new_widget_state.widget_metadata["wid"] = SimpleNamespace()
    base = [1, 2, 3]
    out = present_for_session(ss, "wid", base)
    assert out is base


def test_present_for_session_applies_presenter() -> None:
    def _presenter(base: Any, _ss: Any) -> Any:
        return {"presented": base}

    ss = _FakeSession()
    ss._new_widget_state.widget_metadata["wid"] = SimpleNamespace(presenter=_presenter)
    base = {"value": 123}
    out = present_for_session(ss, "wid", base)
    assert out == {"presented": {"value": 123}}


def test_present_for_session_swallows_presenter_errors() -> None:
    def _boom(_base: Any, _ss: Any) -> Any:
        raise RuntimeError("boom")

    ss = _FakeSession()
    ss._new_widget_state.widget_metadata["wid"] = SimpleNamespace(presenter=_boom)
    base = "hello"
    out = present_for_session(ss, "wid", base)
    assert out is base
