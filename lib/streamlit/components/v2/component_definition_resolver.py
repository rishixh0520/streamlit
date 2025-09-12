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

"""Shared resolver for building component definitions with path validation.

This module centralizes the logic for interpreting js/css inputs as inline
content vs path/glob strings, validating them against a component's asset
directory, and producing a BidiComponentDefinition with correct asset-relative
URLs used by the server.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from streamlit.components.v2.component_path_utils import ComponentPathUtils
from streamlit.components.v2.component_registry import BidiComponentDefinition
from streamlit.errors import StreamlitAPIException


def build_definition_with_validation(
    *,
    manager: Any,
    component_key: str,
    caller_dir: str,
    html: str | None,
    css: str | None,
    js: str | None,
) -> BidiComponentDefinition:
    """Construct definition and validate js/css inputs against asset_dir.

    Behavior
    --------
    - Inline strings are treated as content (no manifest required).
    - Path-like strings require the component to be declared in the package
      manifest with an ``asset_dir``.
    - Globs are supported only within ``asset_dir`` and must resolve to exactly one
      file; otherwise an exception is raised.
    - Relative paths are resolved against the user's calling file and must end up
      within ``asset_dir`` after resolution; traversal outside will raise.
    - For file-backed entries, the URL sent to the frontend is the path relative to
      ``asset_dir`` so the server serves it under
      ``/bidi-components/<component>/<relative_path>``.
    """

    asset_root = manager.manifest_handler.get_asset_root(component_key)
    # Fallback: use manager.get_component_path which prefers manifest asset_dir
    if asset_root is None:
        try:
            maybe_path = manager.get_component_path(component_key)
        except Exception:
            maybe_path = None
        if maybe_path:
            asset_root = Path(maybe_path)

    def _resolve_entry(
        value: str | None, *, kind: str
    ) -> tuple[str | None, str | None]:
        # Inline content: None rel URL
        if value is None:
            return None, None
        if ComponentPathUtils.looks_like_inline_content(value):
            return value, None

        # For path-like strings, asset_root must exist
        if asset_root is None:
            raise StreamlitAPIException(
                f"Component '{component_key}' must be declared in pyproject.toml with asset_dir "
                f"to use file-backed {kind}."
            )

        value_str = value

        # If looks like a glob, resolve strictly inside asset_root
        if ComponentPathUtils.has_glob_characters(value_str):
            resolved = ComponentPathUtils.resolve_glob_pattern(value_str, asset_root)
            ComponentPathUtils.ensure_within_root(resolved, asset_root, kind=kind)
            # Use resolved absolute paths to avoid macOS /private prefix mismatch
            rel_url = str(
                resolved.resolve().relative_to(asset_root.resolve()).as_posix()
            )
            return str(resolved), rel_url

        # Concrete path: resolve relative to caller for non-absolute string
        p = Path(value_str)
        candidate = p if p.is_absolute() else (Path(caller_dir) / p)

        # Normalize and ensure it's within asset_root
        ComponentPathUtils.ensure_within_root(candidate, asset_root, kind=kind)
        resolved_candidate = candidate.resolve()
        rel_url = str(resolved_candidate.relative_to(asset_root.resolve()).as_posix())
        return str(resolved_candidate), rel_url

    css_value, css_rel = _resolve_entry(css, kind="css")
    js_value, js_rel = _resolve_entry(js, kind="js")

    # Build definition with possible asset_dir-relative paths
    return BidiComponentDefinition(
        name=component_key,
        html=html,
        css=css_value,
        js=js_value,
        css_asset_relative_path=css_rel,
        js_asset_relative_path=js_rel,
    )
