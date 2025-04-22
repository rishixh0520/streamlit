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

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final

from streamlit.components.v2.component_path_utils import ComponentPathUtils
from streamlit.errors import StreamlitAPIException
from streamlit.logger import get_logger

if TYPE_CHECKING:
    from collections.abc import MutableMapping
    from pathlib import Path

    from streamlit.components.v2.manifest_scanner import ComponentManifest

_LOGGER: Final = get_logger(__name__)


@dataclass
class ComponentGlobInfo:
    """Information about a component's glob pattern for file watching."""

    component_name: str
    manifest: ComponentManifest
    package_root: Path
    js_pattern: str | None
    css_pattern: str | None


class ComponentManifestHandler:
    """Handles component registration from manifest files and related operations."""

    def __init__(self) -> None:
        # Component metadata from pyproject.toml
        self._metadata: MutableMapping[str, ComponentManifest] = {}
        self._security_requirements: MutableMapping[str, dict[str, Any]] = {}
        # Glob information for file watching
        self._glob_watchers: dict[str, ComponentGlobInfo] = {}

    def process_manifest(
        self, manifest: ComponentManifest, package_root: Path
    ) -> dict[str, dict[str, Any]]:
        """Process a manifest and return component definitions to register.

        Parameters
        ----------
        manifest : ComponentManifest
            The manifest to process
        package_root : Path
            The package root directory

        Returns
        -------
        dict[str, dict[str, Any]]
            Dictionary mapping component names to their definitions
        """
        base_name = manifest.name
        component_definitions = {}

        # Store security requirements
        self._security_requirements[base_name] = manifest.security

        # Process each component in the manifest
        for comp_config in manifest.components:
            comp_name = f"{base_name}.{comp_config['name']}"

            # Track glob patterns for file watching in dev mode
            js_pattern = comp_config.get("js")
            css_pattern = comp_config.get("css")

            # Store glob info for potential watching
            if self._should_track_for_watching(js_pattern, css_pattern):
                self._glob_watchers[comp_name] = ComponentGlobInfo(
                    component_name=comp_name,
                    manifest=manifest,
                    package_root=package_root,
                    js_pattern=js_pattern
                    if js_pattern and ComponentPathUtils.has_glob_characters(js_pattern)
                    else None,
                    css_pattern=css_pattern
                    if css_pattern
                    and ComponentPathUtils.has_glob_characters(css_pattern)
                    else None,
                )

            # Resolve file paths
            js_path = self._resolve_component_path(js_pattern, package_root)
            css_path = self._resolve_component_path(css_pattern, package_root)
            html = comp_config.get("html")

            # Create component definition data
            component_definitions[comp_name] = {
                "name": comp_name,
                "js": js_path,
                "css": css_path,
                "html": html,
            }

            # Store metadata
            self._metadata[comp_name] = manifest

        return component_definitions

    def get_glob_watchers(self) -> dict[str, ComponentGlobInfo]:
        """Get all glob watcher information for file watching."""
        return self._glob_watchers.copy()

    def get_metadata(self, component_name: str) -> ComponentManifest | None:
        """Get metadata for a specific component."""
        return self._metadata.get(component_name)

    def get_security_requirements(self, base_name: str) -> dict[str, Any] | None:
        """Get security requirements for a component package."""
        return self._security_requirements.get(base_name)

    def _should_track_for_watching(
        self, js_pattern: str | None, css_pattern: str | None
    ) -> bool:
        """Check if component should be tracked for file watching."""
        return (js_pattern and ComponentPathUtils.has_glob_characters(js_pattern)) or (
            css_pattern and ComponentPathUtils.has_glob_characters(css_pattern)
        )

    def _resolve_component_path(
        self, pattern: str | None, package_root: Path
    ) -> Path | None:
        """Resolve a component path pattern to an actual path.

        Parameters
        ----------
        pattern : str | None
            The path pattern to resolve
        package_root : Path
            The package root directory

        Returns
        -------
        Path | None
            The resolved path or None if no pattern provided
        """
        if not pattern:
            return None

        if ComponentPathUtils.has_glob_characters(pattern):
            try:
                return ComponentPathUtils.resolve_glob_pattern(pattern, package_root)
            except StreamlitAPIException:
                _LOGGER.exception(
                    "Failed to resolve pattern '%s' in package root %s",
                    pattern,
                    package_root,
                )
                raise
        else:
            # Simple path - check for security issues first
            ComponentPathUtils.validate_path_security(pattern)
            return package_root / pattern
