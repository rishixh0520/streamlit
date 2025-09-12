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
from unittest.mock import Mock, patch

import pytest

from streamlit.components.v2.component_file_watcher import ComponentFileWatcher


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
    # Directory-only: no file watcher state exists anymore
    assert not hasattr(watcher, "_watched_files") or watcher._watched_files == {}
    assert watcher._path_watchers == []
    assert watcher._asset_watch_roots == {}


@patch("streamlit.components.v2.component_file_watcher._get_is_development_mode")
def test_start_file_watching_disabled_in_production(mock_dev_mode, file_watcher):
    """Test that file watching is disabled when not in development mode."""
    mock_dev_mode.return_value = False

    asset_roots = {"test.component": Path("/tmp")}
    file_watcher.start_file_watching(asset_roots)

    assert not file_watcher.is_watching_active


@patch("streamlit.components.v2.component_file_watcher._get_is_development_mode")
def test_start_file_watching_no_watchers(mock_dev_mode, file_watcher):
    """Test starting file watching with no asset roots."""
    mock_dev_mode.return_value = True

    file_watcher.start_file_watching({})

    assert not file_watcher.is_watching_active


@patch("streamlit.components.v2.component_file_watcher._get_is_development_mode")
@patch("streamlit.watcher.path_watcher.get_default_path_watcher_class")
def test_start_file_watching_single_asset_root(
    mock_path_watcher_class,
    mock_dev_mode,
    file_watcher,
    temp_component_files,
):
    """Test file watching for a single asset root directory."""
    mock_dev_mode.return_value = True
    mock_watcher_instance = Mock()
    mock_path_watcher_class.return_value = Mock(return_value=mock_watcher_instance)

    asset_roots = {"test.component": temp_component_files["temp_dir"]}
    file_watcher.start_file_watching(asset_roots)

    # Should be watching
    assert file_watcher.is_watching_active
    assert len(file_watcher._path_watchers) == 1
    assert len(file_watcher._watched_directories) == 1


@patch("streamlit.components.v2.component_file_watcher._get_is_development_mode")
@patch("streamlit.watcher.path_watcher.get_default_path_watcher_class")
def test_start_file_watching_multiple_roots(
    mock_path_watcher_class,
    mock_dev_mode,
    file_watcher,
    temp_component_files,
):
    """Test file watching for multiple asset root directories."""
    mock_dev_mode.return_value = True
    mock_watcher_instance = Mock()
    mock_path_watcher_class.return_value = Mock(return_value=mock_watcher_instance)

    js_root = temp_component_files["temp_dir"] / "js"
    css_root = temp_component_files["temp_dir"] / "css"

    asset_roots = {
        "test.js_component": js_root,
        "test.css_component": css_root,
    }
    file_watcher.start_file_watching(asset_roots)

    # Should be watching two distinct roots
    assert file_watcher.is_watching_active
    assert len(file_watcher._path_watchers) == 2
    assert len(file_watcher._watched_directories) == 2


@patch("streamlit.components.v2.component_file_watcher._get_is_development_mode")
@patch("streamlit.watcher.path_watcher.get_default_path_watcher_class")
def test_start_file_watching_shared_root(
    mock_path_watcher_class, mock_dev_mode, file_watcher, temp_component_files
):
    """Test file watching with multiple components sharing the same asset root."""
    mock_dev_mode.return_value = True
    mock_watcher_instance = Mock()
    mock_path_watcher_class.return_value = Mock(return_value=mock_watcher_instance)

    root = temp_component_files["temp_dir"]
    asset_roots = {
        "test.direct": root,
        "test.glob": root,
    }
    file_watcher.start_file_watching(asset_roots)

    # Should be watching
    assert file_watcher.is_watching_active
    # Only one watcher because roots are the same
    assert len(file_watcher._path_watchers) == 1
    assert len(file_watcher._watched_directories) == 1


def test_stop_file_watching(file_watcher):
    """Test stopping file watching."""
    # Mock some active watchers
    mock_watcher1 = Mock()
    mock_watcher2 = Mock()
    file_watcher._path_watchers = [mock_watcher1, mock_watcher2]
    file_watcher._watched_directories = {"dir1": ["comp1"]}
    # No file watchers in directory-only approach
    file_watcher._watching_active = True

    file_watcher.stop_file_watching()

    # Should have closed all watchers
    mock_watcher1.close.assert_called_once()
    mock_watcher2.close.assert_called_once()

    # Should have cleared all state
    assert not file_watcher.is_watching_active
    assert file_watcher._path_watchers == []
    assert file_watcher._watched_directories == {}
    assert file_watcher._watched_directories == {}


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
def test_on_directory_changed(mock_dev_mode, file_watcher, temp_component_files):
    """Test directory change event handling."""
    mock_dev_mode.return_value = True
    file_watcher._watching_active = True

    # Trigger component change (simulating directory change)
    file_watcher._handle_component_change(["test.component"])

    # Should have called the update callback with a list of components
    file_watcher._component_update_callback.assert_called_once()


@patch("streamlit.components.v2.component_file_watcher._get_is_development_mode")
def test_on_file_changed(mock_dev_mode, file_watcher, temp_component_files):
    """Test file change event handling."""
    mock_dev_mode.return_value = True
    file_watcher._watching_active = True

    # Trigger component change (simulating file change)
    file_watcher._handle_component_change(["test.component"])

    # Should have called the update callback
    file_watcher._component_update_callback.assert_called_once()


def test_no_re_resolve_helpers_present(file_watcher):
    """Ensure legacy re-resolve helpers are removed in asset-root approach."""
    assert not hasattr(file_watcher, "_re_resolve_component_patterns")


def test_no_re_resolve_glob_present(file_watcher):
    """Ensure single-pattern resolver helper has been removed."""
    assert not hasattr(file_watcher, "_resolve_single_pattern")


def test_no_extract_html_present(file_watcher):
    """Ensure manifest HTML extraction helper has been removed."""
    assert not hasattr(file_watcher, "_extract_html_content")


@patch("streamlit.components.v2.component_file_watcher._get_is_development_mode")
@patch("streamlit.watcher.path_watcher.get_default_path_watcher_class")
def test_directory_watches_recursively(
    mock_path_watcher_class,
    mock_dev_mode,
    file_watcher,
    temp_component_files,
):
    """Ensure directory watchers use recursive "**/*" globs for asset roots."""
    mock_dev_mode.return_value = True

    # Mock the watcher class constructor; we care about constructor call kwargs
    mock_watcher_instance = Mock()
    watcher_class_mock = Mock(return_value=mock_watcher_instance)
    mock_path_watcher_class.return_value = watcher_class_mock

    file_watcher.start_file_watching(
        {"test.glob_recursive": temp_component_files["temp_dir"]}
    )

    # One directory watcher should have been created for the root
    assert watcher_class_mock.call_count == 1

    # Assert glob_pattern="**/*" for recursive watching
    call_kwargs = watcher_class_mock.call_args.kwargs
    assert call_kwargs.get("glob_pattern") == "**/*"


@patch("streamlit.components.v2.component_file_watcher._get_is_development_mode")
@patch("streamlit.watcher.path_watcher.get_default_path_watcher_class")
def test_direct_file_also_watches_parent_directory_recursively(
    mock_path_watcher_class, mock_dev_mode, file_watcher, temp_component_files
):
    """Ensure direct file paths register a recursive parent directory watcher.

    Directory-only approach: expect exactly one directory watcher with
    glob_pattern="**/*" for the parent directory.
    """
    mock_dev_mode.return_value = True

    mock_watcher_instance = Mock()
    watcher_class_mock = Mock(return_value=mock_watcher_instance)
    mock_path_watcher_class.return_value = watcher_class_mock

    file_watcher.start_file_watching(
        {"test.direct_parent": temp_component_files["temp_dir"]}
    )

    # Expect exactly one directory watcher (parent dir), recursive
    assert watcher_class_mock.call_count == 1
    assert watcher_class_mock.call_args.kwargs.get("glob_pattern") == "**/*"


@patch("streamlit.components.v2.component_file_watcher._get_is_development_mode")
@patch("streamlit.watcher.path_watcher.get_default_path_watcher_class")
def test_ignores_noisy_directories_in_callbacks(
    mock_path_watcher_class, mock_dev_mode, file_watcher, temp_component_files
):
    """Ensure change events under noisy directories (e.g., node_modules) are ignored.

    This prevents rebuild loops and unnecessary updates when tooling writes under
    typical build/cache directories. We simulate a change event by invoking the
    registered watcher callback directly with a path under node_modules.
    """
    mock_dev_mode.return_value = True

    mock_watcher_instance = Mock()
    watcher_class_mock = Mock(return_value=mock_watcher_instance)
    mock_path_watcher_class.return_value = watcher_class_mock

    file_watcher.start_file_watching(
        {"test.glob_ignore": temp_component_files["temp_dir"]}
    )

    # Prepare deterministic update path by forcing re-resolve to return data
    # Legacy helper removed; directly invoke callback path
    assert watcher_class_mock.call_count == 1
    cb = watcher_class_mock.call_args.args[1]
    noisy_path = str(
        (temp_component_files["temp_dir"] / "js" / "node_modules" / "dep.js").resolve()
    )

    cb(noisy_path)

    # Expect no update callback when the change is under a noisy directory
    file_watcher._component_update_callback.assert_not_called()


@patch("streamlit.components.v2.component_file_watcher._get_is_development_mode")
def test_change_events_ignored_when_not_in_dev_mode(mock_dev_mode, file_watcher):
    """Test that change events are ignored when not in development mode."""
    mock_dev_mode.return_value = False
    file_watcher._watching_active = True

    # Should not call callback when not in dev mode
    file_watcher._handle_component_change(["test.component"])

    file_watcher._component_update_callback.assert_not_called()
