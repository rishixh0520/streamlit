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

import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from streamlit.components.v2 import component as component_api
from streamlit.components.v2.component_manager import BidiComponentManager
from streamlit.components.v2.manifest_scanner import ComponentManifest

if TYPE_CHECKING:
    import pytest


def _make_manifest(
    pkg_name: str, comp_name: str, asset_dir: str, html: str = "<div/>"
) -> ComponentManifest:
    return ComponentManifest(
        name=pkg_name,
        version="0.0.1",
        components=[{"name": comp_name, "asset_dir": asset_dir, "html": html}],
        security={},
    )


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def test_re_resolves_js_glob_on_change(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        assets = root / "assets"
        js_dir = assets / "js"

        # Initial file
        first_js = js_dir / "index-abc123.js"
        _write(first_js, "console.log('abc');")

        # Register manifest with asset_dir
        manager = BidiComponentManager()
        manifest = _make_manifest("pkg", "comp", asset_dir="assets")
        manager.register_from_manifest(manifest, root)

        # Bind public API to our manager instance
        monkeypatch.setattr(
            "streamlit.components.v2.get_bidi_component_manager",
            lambda: manager,
        )

        # Register runtime API with a JS glob under asset_dir
        component_api("pkg.comp", js="js/index-*.js")
        initial = manager.get("pkg.comp")
        assert initial is not None
        assert initial.js is not None
        assert initial.js.endswith("index-abc123.js")
        assert initial.js_url == "js/index-abc123.js"

        # Simulate a new build replacing the hashed file
        first_js.unlink()
        second_js = js_dir / "index-def456.js"
        _write(second_js, "console.log('def');")

        # Trigger change handling
        manager._on_components_changed(["pkg.comp"])  # type: ignore[attr-defined]

        updated = manager.get("pkg.comp")
        assert updated is not None
        assert updated.js is not None
        assert updated.js.endswith("index-def456.js")
        assert updated.js_url == "js/index-def456.js"


def test_re_resolution_no_match_keeps_previous(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        assets = root / "assets"
        js_dir = assets / "js"

        # Initial file
        first_js = js_dir / "index-abc123.js"
        _write(first_js, "console.log('abc');")

        manager = BidiComponentManager()
        manifest = _make_manifest("pkg2", "comp", asset_dir="assets")
        manager.register_from_manifest(manifest, root)

        monkeypatch.setattr(
            "streamlit.components.v2.get_bidi_component_manager",
            lambda: manager,
        )

        component_api("pkg2.comp", js="js/index-*.js")
        baseline = manager.get("pkg2.comp")
        assert baseline is not None
        assert baseline.js is not None
        assert baseline.js.endswith("index-abc123.js")

        # Remove the only matching file -> glob would have zero matches now
        first_js.unlink()

        manager._on_components_changed(["pkg2.comp"])  # type: ignore[attr-defined]

        # Definition should remain unchanged
        after = manager.get("pkg2.comp")
        assert after is not None
        assert after.js is not None
        assert after.js.endswith("index-abc123.js")
