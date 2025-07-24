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
        self._file_watcher = file_watcher or ComponentFileWatcher(
            self._registry.update_component
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
        # Process manifest to get component definitions
        component_definitions = self._manifest_handler.process_manifest(
            manifest, package_root
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
        return self._registry.get_component_path(name)

    def start_file_watching(self) -> None:
        """Start file watching for component changes."""
        if self._file_watcher.is_watching_active:
            _LOGGER.warning("File watching is already started")
            return

        # Get glob watchers from manifest handler
        glob_watchers = self._manifest_handler.get_glob_watchers()

        # Start file watching
        self._file_watcher.start_file_watching(glob_watchers)

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
        """Get all glob watcher information for file watching.

        Returns
        -------
        dict[str, Any]
            Dictionary of glob watcher information
        """
        return self._manifest_handler.get_glob_watchers()

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
