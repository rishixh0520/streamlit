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

import threading
from typing import TYPE_CHECKING, Any, Callable, Final

from streamlit.components.v2.component_path_utils import ComponentPathUtils
from streamlit.errors import StreamlitAPIException
from streamlit.logger import get_logger

if TYPE_CHECKING:
    from streamlit.components.v2.component_manifest_handler import ComponentGlobInfo

_LOGGER: Final = get_logger(__name__)


def _get_is_development_mode() -> bool:
    """Return True if development mode is enabled, False otherwise."""
    # TODO: FIXME: We actually need a config variable for this
    return True


class ComponentFileWatcher:
    """Handles file watching for component glob patterns in development mode."""

    def __init__(
        self, component_update_callback: Callable[[str, dict[str, Any]], None]
    ) -> None:
        """Initialize the file watcher.

        Parameters
        ----------
        component_update_callback : Callable[[str, dict[str, Any]], None]
            Callback function to call when a component needs updating.
            Signature: (component_name, updated_definition_data)
        """
        self._component_update_callback = component_update_callback
        self._lock = threading.Lock()

        # File watching state
        self._watched_directories: dict[
            str, list[str]
        ] = {}  # directory -> component_names
        self._path_watchers: list[Any] = []  # Store actual watcher instances
        self._watching_active = False

        # Store glob watchers for re-resolution
        self._glob_watchers: dict[str, ComponentGlobInfo] = {}

    @property
    def is_watching_active(self) -> bool:
        """Check if file watching is currently active.

        Returns
        -------
        bool
            True if file watching is active, False otherwise
        """
        return self._watching_active

    def start_file_watching(self, glob_watchers: dict[str, ComponentGlobInfo]) -> None:
        """Start file watching for glob patterns in development mode only.

        Parameters
        ----------
        glob_watchers : dict[str, ComponentGlobInfo]
            Dictionary mapping component names to their glob information
        """
        if not _get_is_development_mode():
            _LOGGER.debug("File watching disabled: not in development mode")
            return

        self._glob_watchers = glob_watchers.copy()
        self._start_file_watching()

    def stop_file_watching(self) -> None:
        """Stop file watching and clean up watchers."""
        with self._lock:
            if not self._watching_active:
                return

            # Close all path watchers
            for watcher in self._path_watchers:
                try:
                    watcher.close()
                except Exception:  # noqa: PERF203
                    _LOGGER.exception("Failed to close path watcher")

            self._path_watchers.clear()
            self._watched_directories.clear()
            self._watching_active = False
            _LOGGER.debug("Stopped file watching for component registry")

    def _start_file_watching(self) -> None:
        """Internal method to start file watching."""
        with self._lock:
            if self._watching_active or not _get_is_development_mode():
                return

            if not self._glob_watchers:
                _LOGGER.debug("No glob patterns to watch")
                return

            try:
                from streamlit.watcher.path_watcher import (
                    get_default_path_watcher_class,
                )

                path_watcher_class = get_default_path_watcher_class()

                # Group components by directory to avoid watching the same directory multiple times
                directories_to_watch: dict[str, list[str]] = {}

                for comp_name, glob_info in self._glob_watchers.items():
                    # For JS patterns
                    if glob_info.js_pattern:
                        js_search_path = glob_info.package_root / glob_info.js_pattern
                        js_dir = str(js_search_path.parent.resolve())
                        if js_dir not in directories_to_watch:
                            directories_to_watch[js_dir] = []
                        directories_to_watch[js_dir].append(comp_name)

                    # For CSS patterns
                    if glob_info.css_pattern:
                        css_search_path = glob_info.package_root / glob_info.css_pattern
                        css_dir = str(css_search_path.parent.resolve())
                        if css_dir not in directories_to_watch:
                            directories_to_watch[css_dir] = []
                        if comp_name not in directories_to_watch[css_dir]:
                            directories_to_watch[css_dir].append(comp_name)

                # Start watching each unique directory
                for directory, component_names in directories_to_watch.items():
                    try:
                        # Create a closure to capture the component names for this directory
                        def create_callback(comps: list[str]) -> Callable[[str], None]:
                            def callback(changed_path: str) -> None:
                                self._on_directory_changed(changed_path, comps)

                            return callback

                        # Use a glob pattern that matches all files to let Streamlit's
                        # watcher handle MD5 calculation and change detection
                        watcher = path_watcher_class(
                            directory,
                            create_callback(component_names),
                            glob_pattern="*",
                            allow_nonexistent=False,
                        )
                        self._path_watchers.append(watcher)
                        self._watched_directories[directory] = component_names
                        _LOGGER.debug(
                            "Started watching directory %s for components: %s",
                            directory,
                            component_names,
                        )
                    except Exception:  # noqa: PERF203
                        _LOGGER.exception(
                            "Failed to start watching directory %s", directory
                        )

                self._watching_active = True
                _LOGGER.debug(
                    "Started file watching for %d directories",
                    len(self._watched_directories),
                )

            except ImportError:
                _LOGGER.warning("File watching not available: watchdog not installed")
            except Exception as e:
                _LOGGER.warning("Failed to start file watching: %s", e)

    def _on_directory_changed(
        self, changed_path: str, affected_components: list[str]
    ) -> None:
        """Handle directory change events for glob pattern re-resolution."""
        if not _get_is_development_mode() or not self._watching_active:
            return

        _LOGGER.debug(
            "Directory change detected: %s, checking components: %s",
            changed_path,
            affected_components,
        )

        # Re-resolve glob patterns for affected components
        updated_components = []
        for comp_name in affected_components:
            if comp_name not in self._glob_watchers:
                continue

            try:
                updated_definition = self._re_resolve_component_patterns(comp_name)
                if updated_definition:
                    updated_components.append(comp_name)
                    # Notify the registry about the update
                    self._component_update_callback(comp_name, updated_definition)
            except Exception:
                _LOGGER.exception(
                    "Failed to re-resolve glob patterns for %s", comp_name
                )

        # Log the update
        if updated_components:
            _LOGGER.info(
                "Updated component definitions due to file changes: %s",
                updated_components,
            )

    def _re_resolve_component_patterns(self, comp_name: str) -> dict[str, Any] | None:
        """Re-resolve glob patterns for a component and return updated definition data.

        Parameters
        ----------
        comp_name : str
            The component name to re-resolve

        Returns
        -------
        dict[str, Any] | None
            Updated component definition data if patterns changed, None otherwise
        """
        glob_info = self._glob_watchers[comp_name]

        # Try to re-resolve glob patterns
        new_js = None
        new_css = None
        updated = False

        # Re-resolve JS pattern if it exists
        if glob_info.js_pattern:
            try:
                resolved_js = ComponentPathUtils.resolve_glob_pattern(
                    glob_info.js_pattern, glob_info.package_root
                )
                new_js = resolved_js
                updated = True
                _LOGGER.info(
                    "Resolved new JS file for %s: %s",
                    comp_name,
                    resolved_js,
                )
            except StreamlitAPIException:
                # Pattern might not match any files anymore
                _LOGGER.debug(
                    "JS pattern '%s' no longer matches files for %s",
                    glob_info.js_pattern,
                    comp_name,
                )

        # Re-resolve CSS pattern if it exists
        if glob_info.css_pattern:
            try:
                resolved_css = ComponentPathUtils.resolve_glob_pattern(
                    glob_info.css_pattern, glob_info.package_root
                )
                new_css = resolved_css
                updated = True
                _LOGGER.info(
                    "Resolved new CSS file for %s: %s",
                    comp_name,
                    resolved_css,
                )
            except StreamlitAPIException:
                # Pattern might not match any files anymore
                _LOGGER.debug(
                    "CSS pattern '%s' no longer matches files for %s",
                    glob_info.css_pattern,
                    comp_name,
                )

        # Return updated definition data if paths changed
        if updated:
            # Get HTML content from the original manifest
            html_content = None
            comp_base_name = comp_name.split(".")[
                -1
            ]  # Extract component name from full name
            for comp_config in glob_info.manifest.components:
                if comp_config.get("name") == comp_base_name:
                    html_content = comp_config.get("html")
                    break

            return {
                "name": comp_name,
                "js": new_js,
                "css": new_css,
                "html": html_content,  # Preserve HTML from original manifest
            }

        return None
