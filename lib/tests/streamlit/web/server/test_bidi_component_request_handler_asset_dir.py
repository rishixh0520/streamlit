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

import tornado.testing
import tornado.web

from streamlit.components.v2.component_manager import BidiComponentManager
from streamlit.components.v2.manifest_scanner import ComponentManifest
from streamlit.web.server.bidi_component_request_handler import (
    BidiComponentRequestHandler,
)


class BidiComponentRequestHandlerAssetDirTest(tornado.testing.AsyncHTTPTestCase):
    def setUp(self) -> None:  # type: ignore[override]
        self.manager = BidiComponentManager()
        self.temp_dir = tempfile.TemporaryDirectory()
        super().setUp()

        # Prepare a package with asset_dir and a file to be served
        self.package_root = Path(self.temp_dir.name) / "pkg"
        self.package_root.mkdir(parents=True, exist_ok=True)
        self.assets_dir = self.package_root / "assets"
        self.assets_dir.mkdir(parents=True, exist_ok=True)

        self.js_file_path = self.assets_dir / "bundle.js"
        with open(self.js_file_path, "w") as f:
            f.write("console.log('served from asset_dir');")

        manifest = ComponentManifest(
            name="pkg",
            version="0.0.1",
            components=[{"name": "slider", "asset_dir": "assets"}],
            security={},
        )
        self.manager.register_from_manifest(manifest, self.package_root)

    def tearDown(self) -> None:  # type: ignore[override]
        super().tearDown()
        self.temp_dir.cleanup()

    def get_app(self) -> tornado.web.Application:  # type: ignore[override]
        return tornado.web.Application(
            [
                (
                    r"/bidi-components/(.*)",
                    BidiComponentRequestHandler,
                    {"component_manager": self.manager},
                )
            ]
        )

    def test_serves_within_asset_dir(self) -> None:
        """Handler should serve files under manifest-declared asset_dir."""
        resp = self.fetch("/bidi-components/pkg.slider/bundle.js")
        assert resp.code == 200
        assert resp.body.decode() == "console.log('served from asset_dir');"

    def test_forbids_traversal_outside_asset_dir(self) -> None:
        """Traversal outside asset_dir is forbidden and returns 403."""
        resp = self.fetch("/bidi-components/pkg.slider/../../etc/passwd")
        assert resp.code == 403
