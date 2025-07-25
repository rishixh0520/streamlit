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
from unittest.mock import MagicMock, Mock, patch

import pytest

from streamlit.components.v2.component_file_watcher import ComponentFileWatcher
from streamlit.components.v2.component_manifest_handler import ComponentGlobInfo
from streamlit.components.v2.manifest_scanner import ComponentManifest


@pytest.fixture
def temp_component_files():
    """Create temporary directory structure with component files for testing."""
    temp_dir = tempfile.TemporaryDirectory()
    temp_path = Path(temp_dir.name)

    # Create directory structure
    js_dir = temp_path / "js"
    css_dir = temp_path / "css"
    js_dir.mkdir()
    css_dir.mkdir()

    # Create test files
    js_file = js_dir / "component.js"
    js_file.write_text("console.log('original');")

    css_file = css_dir / "styles.css"
    css_file.write_text(".test { color: red; }")

    # Create glob pattern files
    glob_js_file = js_dir / "component-v1.0.js"
    glob_js_file.write_text("console.log('glob v1');")

    glob_css_file = css_dir / "styles-v1.0.css"
    glob_css_file.write_text(".glob { color: blue; }")

    yield {
        "temp_dir": temp_path,
        "js_file": js_file,
        "css_file": css_file,
        "glob_js_file": glob_js_file,
        "glob_css_file": glob_css_file,
    }

    temp_dir.cleanup()


@pytest.fixture
def mock_component_manifest():
    """Create a mock component manifest."""
    manifest = MagicMock(spec=ComponentManifest)
    manifest.components = [
        {
            "name": "component",  # This should match the last part of "test.component"
            "js": "js/component.js",
            "css": "css/styles.css",
            "html": "<div>Test Component</div>",
        }
    ]
    return manifest


@pytest.fixture
def mock_glob_component_manifest():
    """Create a mock component manifest with glob patterns."""
    manifest = MagicMock(spec=ComponentManifest)
    manifest.components = [
        {
            "name": "glob_component",  # This should match the last part of "test.glob_component"
            "js": "js/component-*.js",
            "css": "css/styles-*.css",
            "html": "<div>Glob Component</div>",
        }
    ]
    return manifest


@pytest.fixture
def mock_callback():
    """Create a mock callback function."""
    return Mock()


@pytest.fixture
def file_watcher(mock_callback):
    """Create a ComponentFileWatcher instance with mock callback."""
    return ComponentFileWatcher(mock_callback)


def test_init(mock_callback):
    """Test initialization of ComponentFileWatcher."""
    watcher = ComponentFileWatcher(mock_callback)

    assert watcher._component_update_callback is mock_callback
    assert not watcher.is_watching_active
    assert watcher._watched_directories == {}
    assert watcher._watched_files == {}
    assert watcher._path_watchers == []
    assert watcher._glob_watchers == {}


@patch("streamlit.components.v2.component_file_watcher._get_is_development_mode")
def test_start_file_watching_disabled_in_production(mock_dev_mode, file_watcher):
    """Test that file watching is disabled when not in development mode."""
    mock_dev_mode.return_value = False

    glob_watchers = {"test.component": MagicMock()}
    file_watcher.start_file_watching(glob_watchers)

    assert not file_watcher.is_watching_active


@patch("streamlit.components.v2.component_file_watcher._get_is_development_mode")
def test_start_file_watching_no_watchers(mock_dev_mode, file_watcher):
    """Test starting file watching with no glob watchers."""
    mock_dev_mode.return_value = True

    file_watcher.start_file_watching({})

    assert not file_watcher.is_watching_active


@patch("streamlit.components.v2.component_file_watcher._get_is_development_mode")
@patch("streamlit.watcher.path_watcher.get_default_path_watcher_class")
def test_start_file_watching_direct_file_paths(
    mock_path_watcher_class,
    mock_dev_mode,
    file_watcher,
    temp_component_files,
    mock_component_manifest,
):
    """Test file watching for direct file paths (not glob patterns)."""
    mock_dev_mode.return_value = True
    mock_watcher_instance = Mock()
    mock_path_watcher_class.return_value = Mock(return_value=mock_watcher_instance)

    # Create ComponentGlobInfo for direct file paths
    glob_info = ComponentGlobInfo(
        component_name="test.component",
        manifest=mock_component_manifest,
        package_root=temp_component_files["temp_dir"],
        js_pattern="js/component.js",  # Direct path, no glob characters
        css_pattern="css/styles.css",  # Direct path, no glob characters
    )

    glob_watchers = {"test.component": glob_info}
    file_watcher.start_file_watching(glob_watchers)

    # Should be watching
    assert file_watcher.is_watching_active

    # Should have created watchers for individual files
    assert len(file_watcher._path_watchers) == 2  # JS and CSS files
    assert len(file_watcher._watched_files) == 2
    assert (
        len(file_watcher._watched_directories) == 0
    )  # No directories for direct paths


@patch("streamlit.components.v2.component_file_watcher._get_is_development_mode")
@patch("streamlit.watcher.path_watcher.get_default_path_watcher_class")
def test_start_file_watching_glob_patterns(
    mock_path_watcher_class,
    mock_dev_mode,
    file_watcher,
    temp_component_files,
    mock_glob_component_manifest,
):
    """Test file watching for glob patterns."""
    mock_dev_mode.return_value = True
    mock_watcher_instance = Mock()
    mock_path_watcher_class.return_value = Mock(return_value=mock_watcher_instance)

    # Create ComponentGlobInfo for glob patterns
    glob_info = ComponentGlobInfo(
        component_name="test.glob_component",
        manifest=mock_glob_component_manifest,
        package_root=temp_component_files["temp_dir"],
        js_pattern="js/component-*.js",  # Glob pattern
        css_pattern="css/styles-*.css",  # Glob pattern
    )

    glob_watchers = {"test.glob_component": glob_info}
    file_watcher.start_file_watching(glob_watchers)

    # Should be watching
    assert file_watcher.is_watching_active

    # Should have created watchers for directories
    assert len(file_watcher._path_watchers) == 2  # JS and CSS directories
    assert len(file_watcher._watched_directories) == 2
    assert (
        len(file_watcher._watched_files) == 0
    )  # No individual files for glob patterns


@patch("streamlit.components.v2.component_file_watcher._get_is_development_mode")
@patch("streamlit.watcher.path_watcher.get_default_path_watcher_class")
def test_start_file_watching_mixed_patterns(
    mock_path_watcher_class, mock_dev_mode, file_watcher, temp_component_files
):
    """Test file watching with mixed glob patterns and direct file paths."""
    mock_dev_mode.return_value = True
    mock_watcher_instance = Mock()
    mock_path_watcher_class.return_value = Mock(return_value=mock_watcher_instance)

    # Create mixed ComponentGlobInfo
    direct_manifest = MagicMock()
    direct_manifest.components = [{"name": "direct", "html": "<div>Direct</div>"}]

    glob_manifest = MagicMock()
    glob_manifest.components = [{"name": "glob", "html": "<div>Glob</div>"}]

    direct_glob_info = ComponentGlobInfo(
        component_name="test.direct",
        manifest=direct_manifest,
        package_root=temp_component_files["temp_dir"],
        js_pattern="js/component.js",  # Direct path
        css_pattern=None,
    )

    glob_glob_info = ComponentGlobInfo(
        component_name="test.glob",
        manifest=glob_manifest,
        package_root=temp_component_files["temp_dir"],
        js_pattern=None,
        css_pattern="css/styles-*.css",  # Glob pattern
    )

    glob_watchers = {
        "test.direct": direct_glob_info,
        "test.glob": glob_glob_info,
    }
    file_watcher.start_file_watching(glob_watchers)

    # Should be watching
    assert file_watcher.is_watching_active

    # Should have both types of watchers
    assert len(file_watcher._path_watchers) == 2  # One file, one directory
    assert len(file_watcher._watched_directories) == 1  # CSS directory for glob
    assert len(file_watcher._watched_files) == 1  # JS file for direct path


def test_stop_file_watching(file_watcher):
    """Test stopping file watching."""
    # Mock some active watchers
    mock_watcher1 = Mock()
    mock_watcher2 = Mock()
    file_watcher._path_watchers = [mock_watcher1, mock_watcher2]
    file_watcher._watched_directories = {"dir1": ["comp1"]}
    file_watcher._watched_files = {"file1": ["comp2"]}
    file_watcher._watching_active = True

    file_watcher.stop_file_watching()

    # Should have closed all watchers
    mock_watcher1.close.assert_called_once()
    mock_watcher2.close.assert_called_once()

    # Should have cleared all state
    assert not file_watcher.is_watching_active
    assert file_watcher._path_watchers == []
    assert file_watcher._watched_directories == {}
    assert file_watcher._watched_files == {}


def test_stop_file_watching_with_close_errors(file_watcher):
    """Test stopping file watching when watcher.close() raises an exception."""
    # Mock a watcher that raises an exception on close
    mock_watcher = Mock()
    mock_watcher.close.side_effect = Exception("Close failed")
    file_watcher._path_watchers = [mock_watcher]
    file_watcher._watching_active = True

    # Should not raise exception, just log it
    file_watcher.stop_file_watching()

    # Should still clean up state
    assert not file_watcher.is_watching_active
    assert file_watcher._path_watchers == []


@patch("streamlit.components.v2.component_file_watcher._get_is_development_mode")
def test_on_directory_changed(
    mock_dev_mode, file_watcher, temp_component_files, mock_component_manifest
):
    """Test directory change event handling."""
    mock_dev_mode.return_value = True
    file_watcher._watching_active = True

    # Create glob info and add to watchers
    glob_info = ComponentGlobInfo(
        component_name="test.component",
        manifest=mock_component_manifest,
        package_root=temp_component_files["temp_dir"],
        js_pattern="js/component-*.js",
        css_pattern=None,
    )
    file_watcher._glob_watchers = {"test.component": glob_info}

    with patch.object(file_watcher, "_re_resolve_component_patterns") as mock_resolve:
        mock_resolve.return_value = {
            "name": "test.component",
            "js": temp_component_files["glob_js_file"],
            "css": None,
            "html": "<div>Test Component</div>",
        }

        # Trigger component change (simulating directory change)
        file_watcher._handle_component_change(["test.component"])

        # Should have called re-resolve
        mock_resolve.assert_called_once_with("test.component")

        # Should have called the update callback
        file_watcher._component_update_callback.assert_called_once()


@patch("streamlit.components.v2.component_file_watcher._get_is_development_mode")
def test_on_file_changed(
    mock_dev_mode, file_watcher, temp_component_files, mock_component_manifest
):
    """Test file change event handling."""
    mock_dev_mode.return_value = True
    file_watcher._watching_active = True

    # Create glob info and add to watchers
    glob_info = ComponentGlobInfo(
        component_name="test.component",
        manifest=mock_component_manifest,
        package_root=temp_component_files["temp_dir"],
        js_pattern="js/component.js",  # Direct file path
        css_pattern=None,
    )
    file_watcher._glob_watchers = {"test.component": glob_info}

    with patch.object(file_watcher, "_re_resolve_component_patterns") as mock_resolve:
        mock_resolve.return_value = {
            "name": "test.component",
            "js": temp_component_files["js_file"],
            "css": None,
            "html": "<div>Test Component</div>",
        }

        # Trigger component change (simulating file change)
        file_watcher._handle_component_change(["test.component"])

        # Should have called re-resolve
        mock_resolve.assert_called_once_with("test.component")

        # Should have called the update callback
        file_watcher._component_update_callback.assert_called_once()


def test_re_resolve_component_patterns_direct_file_path(
    file_watcher, temp_component_files, mock_component_manifest
):
    """Test re-resolving direct file paths."""
    # Create glob info for direct file paths
    glob_info = ComponentGlobInfo(
        component_name="test.component",
        manifest=mock_component_manifest,
        package_root=temp_component_files["temp_dir"],
        js_pattern="js/component.js",
        css_pattern="css/styles.css",
    )
    file_watcher._glob_watchers = {"test.component": glob_info}

    result = file_watcher._re_resolve_component_patterns("test.component")

    assert result is not None
    assert result["name"] == "test.component"
    assert result["js"] == temp_component_files["temp_dir"] / "js/component.js"
    assert result["css"] == temp_component_files["temp_dir"] / "css/styles.css"
    assert result["html"] == "<div>Test Component</div>"


def test_re_resolve_component_patterns_glob_patterns(
    file_watcher, temp_component_files, mock_glob_component_manifest
):
    """Test re-resolving glob patterns."""
    # Create glob info for glob patterns
    glob_info = ComponentGlobInfo(
        component_name="test.glob_component",
        manifest=mock_glob_component_manifest,
        package_root=temp_component_files["temp_dir"],
        js_pattern="js/component-*.js",
        css_pattern="css/styles-*.css",
    )
    file_watcher._glob_watchers = {"test.glob_component": glob_info}

    result = file_watcher._re_resolve_component_patterns("test.glob_component")

    assert result is not None
    assert result["name"] == "test.glob_component"
    # Use resolve() to normalize the paths to handle symlinks
    assert result["js"].resolve() == temp_component_files["glob_js_file"].resolve()
    assert result["css"].resolve() == temp_component_files["glob_css_file"].resolve()
    assert result["html"] == "<div>Glob Component</div>"


def test_re_resolve_component_patterns_missing_files(
    file_watcher, temp_component_files, mock_component_manifest
):
    """Test re-resolving when files don't exist."""
    # Create glob info for non-existent files
    glob_info = ComponentGlobInfo(
        component_name="test.component",
        manifest=mock_component_manifest,
        package_root=temp_component_files["temp_dir"],
        js_pattern="js/nonexistent.js",
        css_pattern="css/nonexistent.css",
    )
    file_watcher._glob_watchers = {"test.component": glob_info}

    result = file_watcher._re_resolve_component_patterns("test.component")

    # Should return None when no files can be resolved
    assert result is None


def test_re_resolve_component_patterns_partial_resolution(
    file_watcher, temp_component_files, mock_component_manifest
):
    """Test re-resolving when only some files exist."""
    # Create glob info where only JS exists
    glob_info = ComponentGlobInfo(
        component_name="test.component",
        manifest=mock_component_manifest,
        package_root=temp_component_files["temp_dir"],
        js_pattern="js/component.js",  # Exists
        css_pattern="css/nonexistent.css",  # Doesn't exist
    )
    file_watcher._glob_watchers = {"test.component": glob_info}

    result = file_watcher._re_resolve_component_patterns("test.component")

    assert result is not None
    assert result["name"] == "test.component"
    assert result["js"] == temp_component_files["temp_dir"] / "js/component.js"
    assert result["css"] is None  # Should be None since the file doesn't exist
    assert result["html"] == "<div>Test Component</div>"


@patch("streamlit.components.v2.component_file_watcher._get_is_development_mode")
def test_change_events_ignored_when_not_watching(mock_dev_mode, file_watcher):
    """Test that change events are ignored when not in watching mode."""
    mock_dev_mode.return_value = False
    file_watcher._watching_active = False

    # Should not call callback when not watching
    file_watcher._handle_component_change(["test.component"])

    file_watcher._component_update_callback.assert_not_called()


@patch("streamlit.components.v2.component_file_watcher._get_is_development_mode")
def test_change_events_ignored_when_not_in_dev_mode(mock_dev_mode, file_watcher):
    """Test that change events are ignored when not in development mode."""
    mock_dev_mode.return_value = False
    file_watcher._watching_active = True

    # Should not call callback when not in dev mode
    file_watcher._handle_component_change(["test.component"])

    file_watcher._component_update_callback.assert_not_called()
