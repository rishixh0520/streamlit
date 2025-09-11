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

import os
import tempfile
from pathlib import Path

from streamlit.components.v2.component_manager import BidiComponentManager
from streamlit.components.v2.component_registry import BidiComponentDefinition
from streamlit.components.v2.manifest_scanner import ComponentManifest


def test_get_component_path_prefers_asset_dir_when_present() -> None:
    """Manager should return manifest-declared asset_dir over registry paths."""
    manager = BidiComponentManager()

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        # Create a registry-backed JS file in dir A
        dir_a = tmp_path / "dir_a"
        dir_a.mkdir(parents=True)
        js_a = dir_a / "index.js"
        js_a.write_text("console.log('A');")

        # Register component with file-backed JS path (registry fallback)
        comp_name = "pkg.slider"
        manager.register(
            BidiComponentDefinition(
                name=comp_name,
                js=str(js_a),
            )
        )

        # Prepare manifest-declared asset_dir (dir B)
        package_root = tmp_path / "package"
        assets_b = package_root / "assets"
        assets_b.mkdir(parents=True)
        (assets_b / "index.js").write_text("console.log('B');")

        manifest = ComponentManifest(
            name="pkg",
            version="0.0.1",
            components=[{"name": "slider", "asset_dir": "assets"}],
            security={},
        )

        # Register manifest; manager should now prefer asset_dir
        manager.register_from_manifest(manifest, package_root)

        got = manager.get_component_path(comp_name)
        assert got is not None
        assert os.path.realpath(got) == os.path.realpath(str(assets_b))


def test_get_component_path_falls_back_when_no_asset_dir() -> None:
    """When no asset_dir is declared, manager should use registry source_paths."""
    manager = BidiComponentManager()

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        comp_dir = tmp_path / "comp"
        comp_dir.mkdir(parents=True)
        js_file = comp_dir / "index.js"
        js_file.write_text("console.log('fallback');")

        comp_name = "pkg.other"
        manager.register(
            BidiComponentDefinition(
                name=comp_name,
                js=str(js_file),
            )
        )

        got = manager.get_component_path(comp_name)
        assert got is not None
        assert os.path.realpath(got) == os.path.realpath(str(comp_dir))
