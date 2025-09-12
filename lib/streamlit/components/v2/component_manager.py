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

from streamlit.components.v2.component_definition_resolver import (
    build_definition_with_validation,
)
from streamlit.components.v2.component_file_watcher import ComponentFileWatcher
from streamlit.components.v2.component_manifest_handler import ComponentManifestHandler
from streamlit.components.v2.component_registry import (
    BidiComponentDefinition,
    BidiComponentRegistry,
)
from streamlit.logger import get_logger

if TYPE_CHECKING:
    from pathlib import Path

    from streamlit.components.v2.manifest_scanner import ComponentManifest

_LOGGER: Final = get_logger(__name__)


@dataclass
class _ApiInputs:
    caller_dir: str
    css: str | None
    js: str | None


class BidiComponentManager:
    """Manager class that composes component registry, manifest handler, and file watcher.

    This class provides a unified interface for working with bidirectional components
    while maintaining clean separation of concerns through composition. It handles
    the coordination and lifecycle management of all component-related functionality.
    """

    def __init__(
        self,
        registry: BidiComponentRegistry | None = None,
        manifest_handler: ComponentManifestHandler | None = None,
        file_watcher: ComponentFileWatcher | None = None,
    ) -> None:
        """Initialize the component manager.

        Parameters
        ----------
        registry : BidiComponentRegistry, optional
            Component registry instance. If not provided, a new one will be created.
        manifest_handler : ComponentManifestHandler, optional
            Manifest handler instance. If not provided, a new one will be created.
        file_watcher : ComponentFileWatcher, optional
            File watcher instance. If not provided, a new one will be created.
        """
        # Create dependencies
        self._registry = registry or BidiComponentRegistry()
        self._manifest_handler = manifest_handler or ComponentManifestHandler()
        # Store API inputs for re-resolution on change events
        self._api_inputs: dict[str, _ApiInputs] = {}
        # TODO: Do not instantiate file watcher in production
        self._file_watcher = file_watcher or ComponentFileWatcher(
            self._on_components_changed
        )

    def record_api_inputs(
        self, component_key: str, caller_dir: str, css: str | None, js: str | None
    ) -> None:
        """Record original API inputs for later re-resolution on changes."""
        self._api_inputs[component_key] = _ApiInputs(
            caller_dir=caller_dir, css=css, js=js
        )

    def register_from_manifest(
        self, manifest: ComponentManifest, package_root: Path
    ) -> None:
        """Register components from a manifest file.

        This is a high-level method that processes the manifest and registers
        all components found within it.

        Parameters
        ----------
        manifest : ComponentManifest
            The component manifest to process
        package_root : Path
            Root path of the package containing the components
        """
        # First process the manifest (persists security requirements & metadata)
        component_definitions = self._manifest_handler.process_manifest(
            manifest, package_root
        )

        # Validate after processing so security metadata is stored even if invalid
        # With js/css ignored in Solution 2, each component must declare at least
        # one of HTML content or an asset_dir. If neither is present, raise.
        for comp in manifest.components:
            comp_full_name = f"{manifest.name}.{comp['name']}"
            has_asset_root = (
                self._manifest_handler.get_asset_root(comp_full_name) is not None
            )
            has_html = comp.get("html") is not None
            if not has_asset_root and not has_html:
                raise ValueError(
                    "BidiComponentDefinition must have at least one of html, css, or js."
                )

        # Register all component definitions
        self._registry.register_components_from_definitions(component_definitions)

        _LOGGER.debug(
            "Registered %d components from manifest", len(component_definitions)
        )

    def register(self, definition: BidiComponentDefinition) -> None:
        """Register a single component definition.

        Parameters
        ----------
        definition : BidiComponentDefinition
            The component definition to register
        """
        self._registry.register(definition)

    def get(self, name: str) -> BidiComponentDefinition | None:
        """Get a component definition by name.

        Parameters
        ----------
        name : str
            The name of the component to retrieve

        Returns
        -------
        BidiComponentDefinition or None
            The component definition if found, otherwise None
        """
        return self._registry.get(name)

    def unregister(self, name: str) -> None:
        """Unregister a component by name.

        Parameters
        ----------
        name : str
            The name of the component to unregister
        """
        self._registry.unregister(name)

    def clear(self) -> None:
        """Clear all registered components."""
        self._registry.clear()

    def get_component_path(self, name: str) -> str | None:
        """Get the filesystem path for a component.

        Parameters
        ----------
        name : str
            The name of the component

        Returns
        -------
        str or None
            The component's source directory if found, otherwise None
        """
        # Prefer manifest-declared asset_dir as the sandbox root when available.
        # This ensures all file-serving is rooted at the package-declared assets directory.
        asset_root = self._manifest_handler.get_asset_root(name)
        if asset_root is not None:
            return str(asset_root)

        # Fallback to registry-provided source paths (inline-only scenarios/tests).
        return self._registry.get_component_path(name)

    def start_file_watching(self) -> None:
        """Start file watching for component changes."""
        if self._file_watcher.is_watching_active:
            _LOGGER.warning("File watching is already started")
            return

        # Get asset watch roots from manifest handler
        asset_roots = self._manifest_handler.get_asset_watch_roots()

        # Start file watching
        self._file_watcher.start_file_watching(asset_roots)

        if self._file_watcher.is_watching_active:
            _LOGGER.debug("Started file watching for component changes")  # type: ignore[unreachable]
        else:
            _LOGGER.debug("File watching not started (likely not in development mode)")

    def stop_file_watching(self) -> None:
        """Stop file watching."""
        if not self._file_watcher.is_watching_active:
            _LOGGER.warning("File watching is not started")
            return

        self._file_watcher.stop_file_watching()

        _LOGGER.debug("Stopped file watching")

    def get_security_requirements(self, base_name: str) -> dict[str, Any] | None:
        """Get security requirements for a component package.

        Parameters
        ----------
        base_name : str
            The base name of the component package

        Returns
        -------
        dict[str, Any] or None
            The security requirements if found, None otherwise
        """
        return self._manifest_handler.get_security_requirements(base_name)

    def get_metadata(self, component_name: str) -> ComponentManifest | None:
        """Get metadata for a component.

        Parameters
        ----------
        component_name : str
            The name of the component to get metadata for

        Returns
        -------
        ComponentManifest or None
            The component metadata if found, None otherwise
        """
        return self._manifest_handler.get_metadata(component_name)

    def get_glob_watchers(self) -> dict[str, Any]:
        """Deprecated: manifests no longer provide js/css globs. Returns empty dict."""
        return {}

    def _on_components_changed(self, component_names: list[str]) -> None:
        """Handle change events for components' asset roots.

        For each component, re-resolve from stored API inputs and update registry.
        """
        for name in component_names:
            try:
                updated = self._recompute_definition_from_api(name)
                if updated is not None:
                    self._registry.update_component(name, updated)
            except Exception:  # noqa: PERF203
                _LOGGER.exception("Failed to update component after change: %s", name)

    def _recompute_definition_from_api(
        self, component_name: str
    ) -> dict[str, Any] | None:
        """Recompute definition using stored API inputs. Returns update dict or None."""
        inputs = self._api_inputs.get(component_name)
        if inputs is None:
            return None

        # Get existing def to preserve html unless new content is provided later
        existing_def = self._registry.get(component_name)
        html_value = existing_def.html if existing_def else None

        try:
            new_def = build_definition_with_validation(
                manager=self,
                component_key=component_name,
                caller_dir=inputs.caller_dir,
                html=html_value,
                css=inputs.css,
                js=inputs.js,
            )
        except Exception as e:
            _LOGGER.debug(
                "Skipping update for %s due to re-resolution error: %s",
                component_name,
                e,
            )
            return None

        return {
            "name": new_def.name,
            "html": new_def.html,
            "css": new_def.css,
            "js": new_def.js,
            "css_asset_relative_path": new_def.css_asset_relative_path,
            "js_asset_relative_path": new_def.js_asset_relative_path,
        }

    @property
    def registry(self) -> BidiComponentRegistry:
        """Get the component registry instance.

        Provides direct access to the registry for advanced use cases.

        Returns
        -------
        BidiComponentRegistry
            The registry instance
        """
        return self._registry

    @property
    def manifest_handler(self) -> ComponentManifestHandler:
        """Get the manifest handler instance.

        Provides direct access to the manifest handler for advanced use cases.

        Returns
        -------
        ComponentManifestHandler
            The manifest handler instance
        """
        return self._manifest_handler

    @property
    def file_watcher(self) -> ComponentFileWatcher:
        """Get the file watcher instance.

        Provides direct access to the file watcher for advanced use cases.

        Returns
        -------
        ComponentFileWatcher
            The file watcher instance
        """
        return self._file_watcher

    @property
    def is_file_watching_started(self) -> bool:
        """Check if file watching is currently active.

        Returns
        -------
        bool
            True if file watching is started, False otherwise
        """
        return self._file_watcher.is_watching_active
