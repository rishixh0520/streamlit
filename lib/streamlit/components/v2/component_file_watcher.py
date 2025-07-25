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
    from pathlib import Path

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

        # Track individual files being watched
        self._watched_files: dict[str, list[str]] = {}  # file_path -> component_names

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
            self._watched_files.clear()
            self._watching_active = False
            _LOGGER.debug("Stopped file watching for component registry")

    def _start_file_watching(self) -> None:
        """Internal method to start file watching."""
        with self._lock:
            if self._watching_active or not _get_is_development_mode():
                return

            if not self._glob_watchers:
                _LOGGER.debug("No patterns to watch")
                return

            try:
                from streamlit.watcher.path_watcher import (
                    get_default_path_watcher_class,
                )

                path_watcher_class = get_default_path_watcher_class()

                # Collect patterns to watch
                directories_to_watch, files_to_watch = self._collect_patterns_to_watch()

                # Setup watchers
                self._setup_directory_watchers(path_watcher_class, directories_to_watch)
                self._setup_file_watchers(path_watcher_class, files_to_watch)

                self._watching_active = True
                _LOGGER.debug(
                    "Started file watching for %d directories and %d files",
                    len(self._watched_directories),
                    len(self._watched_files),
                )

            except ImportError:
                _LOGGER.warning("File watching not available: watchdog not installed")
            except Exception as e:
                _LOGGER.warning("Failed to start file watching: %s", e)

    def _collect_patterns_to_watch(
        self,
    ) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
        """Collect patterns to watch and group them by directories and files.

        Returns
        -------
        tuple[dict[str, list[str]], dict[str, list[str]]]
            A tuple of (directories_to_watch, files_to_watch) where each maps
            paths to lists of component names.
        """
        directories_to_watch: dict[str, list[str]] = {}
        files_to_watch: dict[str, list[str]] = {}

        for comp_name, glob_info in self._glob_watchers.items():
            # Process JS pattern
            if glob_info.js_pattern:
                self._process_pattern_for_watching(
                    pattern=glob_info.js_pattern,
                    package_root=glob_info.package_root,
                    comp_name=comp_name,
                    directories_to_watch=directories_to_watch,
                    files_to_watch=files_to_watch,
                )

            # Process CSS pattern
            if glob_info.css_pattern:
                self._process_pattern_for_watching(
                    pattern=glob_info.css_pattern,
                    package_root=glob_info.package_root,
                    comp_name=comp_name,
                    directories_to_watch=directories_to_watch,
                    files_to_watch=files_to_watch,
                )

        return directories_to_watch, files_to_watch

    def _process_pattern_for_watching(
        self,
        pattern: str,
        package_root: Path,
        comp_name: str,
        directories_to_watch: dict[str, list[str]],
        files_to_watch: dict[str, list[str]],
    ) -> None:
        """Process a single pattern and add it to the appropriate watching collection.

        Parameters
        ----------
        pattern : str
            The pattern to process (JS or CSS)
        package_root : Path
            The package root directory
        comp_name : str
            The component name
        directories_to_watch : dict[str, list[str]]
            Dictionary to collect directory watches
        files_to_watch : dict[str, list[str]]
            Dictionary to collect file watches
        """
        if ComponentPathUtils.has_glob_characters(pattern):
            # It's a glob pattern - watch the directory
            search_path = package_root / pattern
            directory = str(search_path.parent.resolve())
            if directory not in directories_to_watch:
                directories_to_watch[directory] = []
            if comp_name not in directories_to_watch[directory]:
                directories_to_watch[directory].append(comp_name)
        else:
            # It's a direct file path - watch the specific file
            file_path = str((package_root / pattern).resolve())
            if file_path not in files_to_watch:
                files_to_watch[file_path] = []
            if comp_name not in files_to_watch[file_path]:
                files_to_watch[file_path].append(comp_name)

    def _setup_directory_watchers(
        self, path_watcher_class: type, directories_to_watch: dict[str, list[str]]
    ) -> None:
        """Setup watchers for directories containing glob patterns.

        Parameters
        ----------
        path_watcher_class : type
            The path watcher class to use
        directories_to_watch : dict[str, list[str]]
            Directories to watch and their associated component names
        """
        for directory, component_names in directories_to_watch.items():
            try:
                # Create a closure to capture the component names for this directory
                def create_callback(comps: list[str]) -> Callable[[str], None]:
                    def callback(changed_path: str) -> None:
                        _LOGGER.debug(
                            "Directory change detected: %s, checking components: %s",
                            changed_path,
                            comps,
                        )
                        self._handle_component_change(comps)

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
                _LOGGER.exception("Failed to start watching directory %s", directory)

    def _setup_file_watchers(
        self, path_watcher_class: type, files_to_watch: dict[str, list[str]]
    ) -> None:
        """Setup watchers for specific files.

        Parameters
        ----------
        path_watcher_class : type
            The path watcher class to use
        files_to_watch : dict[str, list[str]]
            Files to watch and their associated component names
        """
        for file_path, component_names in files_to_watch.items():
            try:
                # Create a closure to capture the component names for this file
                def create_file_callback(comps: list[str]) -> Callable[[str], None]:
                    def callback(changed_path: str) -> None:
                        _LOGGER.debug(
                            "File change detected: %s, checking components: %s",
                            changed_path,
                            comps,
                        )
                        self._handle_component_change(comps)

                    return callback

                # Watch the specific file
                watcher = path_watcher_class(
                    file_path,
                    create_file_callback(component_names),
                    glob_pattern=None,  # Watch the specific file
                    allow_nonexistent=True,  # File might not exist yet
                )
                self._path_watchers.append(watcher)
                self._watched_files[file_path] = component_names
                _LOGGER.debug(
                    "Started watching file %s for components: %s",
                    file_path,
                    component_names,
                )
            except Exception:  # noqa: PERF203
                _LOGGER.exception("Failed to start watching file %s", file_path)

    def _handle_component_change(self, affected_components: list[str]) -> None:
        """Handle component changes for both directory and file events.

        Parameters
        ----------
        affected_components : list[str]
            List of component names affected by the change
        """
        if not _get_is_development_mode() or not self._watching_active:
            return

        # Re-resolve patterns for affected components
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
                _LOGGER.exception("Failed to re-resolve patterns for %s", comp_name)

        # Log the update
        if updated_components:
            _LOGGER.info(
                "Updated component definitions due to file changes: %s",
                updated_components,
            )

    def _re_resolve_component_patterns(self, comp_name: str) -> dict[str, Any] | None:
        """Re-resolve patterns/paths for a component and return updated definition data.

        This method handles both glob patterns and direct file paths.

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

        # Resolve patterns
        new_js = self._resolve_single_pattern(
            pattern=glob_info.js_pattern,
            package_root=glob_info.package_root,
            comp_name=comp_name,
            pattern_type="JS",
        )

        new_css = self._resolve_single_pattern(
            pattern=glob_info.css_pattern,
            package_root=glob_info.package_root,
            comp_name=comp_name,
            pattern_type="CSS",
        )

        # Check if anything was resolved
        if new_js is not None or new_css is not None:
            return {
                "name": comp_name,
                "js": new_js,
                "css": new_css,
                "html": self._extract_html_content(glob_info, comp_name),
            }

        return None

    def _resolve_single_pattern(
        self,
        pattern: str | None,
        package_root: Path,
        comp_name: str,
        pattern_type: str,
    ) -> Path | None:
        """Resolve a single pattern (JS or CSS) and return the resolved path.

        Parameters
        ----------
        pattern : str | None
            The pattern to resolve
        package_root : Path
            The package root directory
        comp_name : str
            The component name (for logging)
        pattern_type : str
            The type of pattern ("JS" or "CSS") for logging

        Returns
        -------
        Path | None
            The resolved path, or None if pattern doesn't exist or can't be resolved
        """
        if not pattern:
            return None

        try:
            if ComponentPathUtils.has_glob_characters(pattern):
                # It's a glob pattern
                resolved_path = ComponentPathUtils.resolve_glob_pattern(
                    pattern, package_root
                )
                _LOGGER.info(
                    "Resolved %s file for %s: %s",
                    pattern_type,
                    comp_name,
                    resolved_path,
                )
                return resolved_path
            # It's a direct file path
            ComponentPathUtils.validate_path_security(pattern)
            resolved_path = package_root / pattern

            # For direct file paths, only include if file exists
            if resolved_path.exists():
                _LOGGER.info(
                    "Resolved %s file for %s: %s",
                    pattern_type,
                    comp_name,
                    resolved_path,
                )
                return resolved_path
            _LOGGER.debug(
                "%s file '%s' doesn't exist for %s",
                pattern_type,
                resolved_path,
                comp_name,
            )
            return None

        except StreamlitAPIException:
            # Pattern might not match any files anymore or file doesn't exist
            _LOGGER.debug(
                "%s pattern/path '%s' no longer matches files or doesn't exist for %s",
                pattern_type,
                pattern,
                comp_name,
            )
            return None

    def _extract_html_content(
        self, glob_info: ComponentGlobInfo, comp_name: str
    ) -> str | None:
        """Extract HTML content from the component manifest.

        Parameters
        ----------
        glob_info : ComponentGlobInfo
            The component glob information
        comp_name : str
            The full component name

        Returns
        -------
        str | None
            The HTML content or None if not found
        """
        comp_base_name = comp_name.split(".")[
            -1
        ]  # Extract component name from full name
        for comp_config in glob_info.manifest.components:
            if comp_config.get("name") == comp_base_name:
                return comp_config.get("html")
        return None
