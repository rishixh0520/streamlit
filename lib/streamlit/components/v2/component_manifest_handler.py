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

from typing import TYPE_CHECKING, Any, Final

from streamlit.components.v2.component_path_utils import ComponentPathUtils
from streamlit.errors import StreamlitAPIException
from streamlit.logger import get_logger

if TYPE_CHECKING:
    from collections.abc import MutableMapping
    from pathlib import Path

    from streamlit.components.v2.manifest_scanner import ComponentManifest

_LOGGER: Final = get_logger(__name__)


class ComponentManifestHandler:
    """Handles component registration from manifest files and related operations."""

    def __init__(self) -> None:
        # Component metadata from pyproject.toml
        self._metadata: MutableMapping[str, ComponentManifest] = {}
        self._security_requirements: MutableMapping[str, dict[str, Any]] = {}
        # Resolved asset roots keyed by fully-qualified component name
        self._asset_roots: MutableMapping[str, Path] = {}

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

            # Parse and persist asset_dir if provided. This is the sandbox root
            # for any files later referenced via the Python API.
            asset_dir = comp_config.get("asset_dir")
            if asset_dir:
                # Validate security of the configured path string first
                ComponentPathUtils.validate_path_security(asset_dir)
                # Store absolute asset root path and validate existence
                asset_root = package_root / asset_dir
                if not asset_root.exists() or not asset_root.is_dir():
                    raise StreamlitAPIException(
                        f"Declared asset_dir '{asset_dir}' for component '{comp_name}' "
                        f"does not exist or is not a directory under package root '{package_root}'."
                    )
                self._asset_roots[comp_name] = asset_root

            # Ignore any manifest-provided js/css entries entirely.
            js_path = None
            css_path = None
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

    def get_glob_watchers(self) -> dict[str, Any]:
        """Return an empty mapping; manifest js/css watching is removed."""
        return {}

    def get_metadata(self, component_name: str) -> ComponentManifest | None:
        """Get metadata for a specific component."""
        return self._metadata.get(component_name)

    def get_asset_root(self, component_name: str) -> Path | None:
        """Get the absolute asset root directory for a component if declared.

        Parameters
        ----------
        component_name : str
            Fully-qualified component name (e.g. "package.component").

        Returns
        -------
        Path | None
            Absolute path to the component's asset root if present, otherwise None.
        """
        return self._asset_roots.get(component_name)

    def get_asset_watch_roots(self) -> dict[str, Path]:
        """Get a mapping of component names to their asset root directories.

        Returns
        -------
        dict[str, Path]
            A shallow copy mapping fully-qualified component names to absolute
            asset root directories.
        """
        return dict(self._asset_roots)

    def get_security_requirements(self, base_name: str) -> dict[str, Any] | None:
        """Get security requirements for a component package."""
        return self._security_requirements.get(base_name)

    # Legacy helpers removed: manifest-based js/css resolution and tracking are no-ops.
