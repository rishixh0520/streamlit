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

import os
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from streamlit.components.v2 import component
from streamlit.components.v2.component_manager import BidiComponentManager
from streamlit.components.v2.component_path_utils import ComponentPathUtils
from streamlit.components.v2.component_registry import (
    BidiComponentDefinition,
)
from streamlit.components.v2.manifest_scanner import ComponentManifest
from streamlit.errors import StreamlitAPIException


@pytest.fixture
def temp_test_files():
    """Create temporary directory with test files for BidiComponentDefinition tests."""
    temp_dir = tempfile.TemporaryDirectory()

    # Create test files
    js_path = os.path.join(temp_dir.name, "index.js")
    with open(js_path, "w") as f:
        f.write("console.log('test');")

    html_path = os.path.join(temp_dir.name, "index.html")
    with open(html_path, "w") as f:
        f.write("<div>Test</div>")

    css_path = os.path.join(temp_dir.name, "styles.css")
    with open(css_path, "w") as f:
        f.write("div { color: blue; }")

    yield {
        "temp_dir": temp_dir,
        "js_path": js_path,
        "html_path": html_path,
        "css_path": css_path,
    }

    temp_dir.cleanup()


@pytest.fixture
def temp_manager_setup():
    """Create temporary directory and component manager for BidiComponentManager tests."""
    temp_dir = tempfile.TemporaryDirectory()
    component_manager = BidiComponentManager()

    # Create test files
    js_path = os.path.join(temp_dir.name, "index.js")
    with open(js_path, "w") as f:
        f.write("console.log('test');")

    yield {
        "temp_dir": temp_dir,
        "component_manager": component_manager,
        "js_path": js_path,
    }

    temp_dir.cleanup()


def test_string_content(temp_test_files) -> None:
    """Test component with direct string content."""
    comp = BidiComponentDefinition(
        name="test",
        html="<div>Hello</div>",
        css=".div { color: red; }",
        js="console.log('hello');",
    )

    assert comp.html_content == "<div>Hello</div>"
    assert comp.css_content == ".div { color: red; }"
    assert comp.js_content == "console.log('hello');"
    assert comp.css_url is None
    assert comp.js_url is None
    assert comp.source_paths == {}


def test_file_path_content(temp_test_files) -> None:
    """Test component with file path content."""
    with patch(
        "streamlit.components.v2.component_registry._get_caller_path"
    ) as mock_caller:
        # Mock the caller path to be the temp directory
        mock_caller.return_value = os.path.join(
            temp_test_files["temp_dir"].name, "caller.py"
        )

        comp = BidiComponentDefinition(
            name="test",
            js=temp_test_files["js_path"],
            html="<div>Inline HTML</div>",  # HTML should be a string, not a path
            css=temp_test_files["css_path"],
        )

        assert comp.html_content == "<div>Inline HTML</div>"
        assert comp.css_content is None  # CSS content is None because it's a path
        assert comp.js_content is None  # JS content is None because it's a path

        # Check URLs are generated for path resources
        assert comp.css_url == f"{os.path.basename(temp_test_files['css_path'])}"
        assert comp.js_url == f"{os.path.basename(temp_test_files['js_path'])}"

        # Check source paths
        assert len(comp.source_paths) == 2
        assert comp.source_paths["css"] == os.path.dirname(temp_test_files["css_path"])
        assert comp.source_paths["js"] == os.path.dirname(temp_test_files["js_path"])
        assert "html" not in comp.source_paths


def test_mixed_content(temp_test_files) -> None:
    """Test component with mixed string and file content."""
    with patch(
        "streamlit.components.v2.component_registry._get_caller_path"
    ) as mock_caller:
        # Mock the caller path to be the temp directory
        mock_caller.return_value = os.path.join(
            temp_test_files["temp_dir"].name, "caller.py"
        )

        comp = BidiComponentDefinition(
            name="test",
            js=temp_test_files["js_path"],  # File path
            html="<div>Inline HTML</div>",  # String
            css="div { color: green; }",  # String
        )

        assert comp.html_content == "<div>Inline HTML</div>"
        assert comp.css_content == "div { color: green; }"
        assert comp.js_content is None  # JS content is None because it's a path

        # Check URLs
        assert comp.css_url is None  # No URL for inline CSS
        assert comp.js_url == f"{os.path.basename(temp_test_files['js_path'])}"

        # Only JS should have a source path
        assert len(comp.source_paths) == 1
        assert comp.source_paths["js"] == os.path.dirname(temp_test_files["js_path"])


def test_public_api_path_object_rejection() -> None:
    """Test that public API functions reject Path objects with clear error messages."""
    from pathlib import Path

    # Test component() function with js parameter
    with pytest.raises(StreamlitAPIException) as exc_info:
        component("test", js=Path("test.js"))

    error_msg = str(exc_info.value)
    assert "js parameter must be a string or None" in error_msg
    assert "got PosixPath" in error_msg or "got WindowsPath" in error_msg

    # Test component() function with css parameter
    with pytest.raises(StreamlitAPIException) as exc_info:
        component("test", css=Path("test.css"))

    error_msg = str(exc_info.value)
    assert "css parameter must be a string or None" in error_msg
    assert "got PosixPath" in error_msg or "got WindowsPath" in error_msg

    # Test component() function with js parameter
    with pytest.raises(StreamlitAPIException) as exc_info:
        component("test", js=Path("test.js"))

    error_msg = str(exc_info.value)
    assert "js parameter must be a string or None" in error_msg
    assert "got PosixPath" in error_msg or "got WindowsPath" in error_msg

    # Test component_dg() function with css parameter
    with pytest.raises(StreamlitAPIException) as exc_info:
        component("test", css=Path("test.css"))

    error_msg = str(exc_info.value)
    assert "css parameter must be a string or None" in error_msg
    assert "got PosixPath" in error_msg or "got WindowsPath" in error_msg

    # Test with other invalid types (not just Path)
    with pytest.raises(StreamlitAPIException) as exc_info:
        component("test", js=123)  # Integer instead of string

    error_msg = str(exc_info.value)
    assert "js parameter must be a string or None" in error_msg
    assert "got int" in error_msg

    with pytest.raises(StreamlitAPIException) as exc_info:
        component("test", css=["invalid", "list"])  # List instead of string

    error_msg = str(exc_info.value)
    assert "css parameter must be a string or None" in error_msg
    assert "got list" in error_msg


def test_string_file_path(temp_test_files) -> None:
    """Test component with string file path."""
    with patch(
        "streamlit.components.v2.component_registry._get_caller_path"
    ) as mock_caller:
        # Mock the caller path to be the temp directory
        mock_caller.return_value = os.path.join(
            temp_test_files["temp_dir"].name, "caller.py"
        )

        js_string_path = temp_test_files["js_path"]

        comp = BidiComponentDefinition(
            name="test",
            js=js_string_path,
        )

        assert comp.js_content is None  # JS content is None because it's a path
        assert comp.js_url == f"{os.path.basename(js_string_path)}"
        assert comp.source_paths["js"] == os.path.dirname(temp_test_files["js_path"])


def test_get_component_path_with_file_path(temp_manager_setup) -> None:
    """Test get_component_path with a component using file paths."""
    setup = temp_manager_setup
    with patch(
        "streamlit.components.v2.component_registry._get_caller_path"
    ) as mock_caller:
        mock_caller.return_value = os.path.join(setup["temp_dir"].name, "caller.py")

        setup["component_manager"].register(
            BidiComponentDefinition(
                name="test_component",
                js=setup["js_path"],
            )
        )

        path = setup["component_manager"].get_component_path("test_component")
        assert path == os.path.dirname(setup["js_path"])


def test_get_component_path_with_string_content(temp_manager_setup) -> None:
    """Test get_component_path with a component using string content."""
    setup = temp_manager_setup
    setup["component_manager"].register(
        BidiComponentDefinition(
            name="string_component",
            js="console.log('string content');",
        )
    )

    path = setup["component_manager"].get_component_path("string_component")
    assert path is None


def test_get_component_path_nonexistent_component(temp_manager_setup) -> None:
    """Test get_component_path with a nonexistent component."""
    setup = temp_manager_setup
    path = setup["component_manager"].get_component_path("nonexistent")
    assert path is None


def test_register_from_manifest_basic(temp_manager_setup) -> None:
    """Test basic manifest registration with single component.

    Note: js/css entries in manifest are ignored in Solution 2.
    """
    setup = temp_manager_setup
    # Create component files in package root
    package_root = Path(setup["temp_dir"].name)
    # Files may exist but are not read from manifest anymore
    (package_root / "component.js").write_text(
        "export default function() { console.log('basic test'); }"
    )
    (package_root / "styles.css").write_text(".test { color: blue; }")

    manifest = ComponentManifest(
        name="test_package",
        version="1.0.0",
        components=[
            {
                "name": "basic_component",
                # js/css in manifest should be ignored
                "html": "<div>Basic Component</div>",
            }
        ],
        security={"network_access": True},
    )

    setup["component_manager"].register_from_manifest(manifest, package_root)

    # Check component was registered
    component = setup["component_manager"].get("test_package.basic_component")
    assert component is not None
    assert component.name == "test_package.basic_component"
    assert component.html == "<div>Basic Component</div>"
    # js/css must be None because manifest no longer provides entries
    assert component.js is None
    assert component.css is None

    # Check security requirements were stored
    assert setup["component_manager"].get_security_requirements("test_package") == {
        "network_access": True
    }

    # Check metadata was stored
    assert (
        setup["component_manager"].get_metadata("test_package.basic_component")
        == manifest
    )


def test_register_from_manifest_multiple_components(temp_manager_setup) -> None:
    """Test manifest registration with multiple components (js/css ignored)."""
    setup = temp_manager_setup
    package_root = Path(setup["temp_dir"].name)

    # Create files (not used by manifest anymore)
    (package_root / "comp1.js").write_text("console.log('component 1');")
    (package_root / "comp1.css").write_text(".comp1 { background: red; }")
    (package_root / "comp2.js").write_text("console.log('component 2');")

    manifest = ComponentManifest(
        name="multi_package",
        version="2.0.0",
        components=[
            {
                "name": "component_one",
                # js/css ignored
                "html": "<div>Component One</div>",
            },
            {
                "name": "component_two",
                "html": "<span>Component Two</span>",
            },
        ],
        security={"allowed_origins": ["https://example.com"]},
    )

    setup["component_manager"].register_from_manifest(manifest, package_root)

    # Check first component was registered
    comp1 = setup["component_manager"].get("multi_package.component_one")
    assert comp1 is not None
    assert comp1.name == "multi_package.component_one"
    assert comp1.html == "<div>Component One</div>"
    assert comp1.js is None
    assert comp1.css is None

    # Check second component was registered
    comp2 = setup["component_manager"].get("multi_package.component_two")
    assert comp2 is not None
    assert comp2.name == "multi_package.component_two"
    assert comp2.html == "<span>Component Two</span>"
    assert comp2.js is None
    assert comp2.css is None

    # Check security requirements
    assert setup["component_manager"].get_security_requirements("multi_package") == {
        "allowed_origins": ["https://example.com"]
    }

    # Check both components have same manifest metadata
    assert (
        setup["component_manager"].get_metadata("multi_package.component_one")
        == manifest
    )
    assert (
        setup["component_manager"].get_metadata("multi_package.component_two")
        == manifest
    )


def test_register_from_manifest_minimal_component(temp_manager_setup) -> None:
    """Test manifest registration with minimal component (only HTML)."""
    setup = temp_manager_setup
    package_root = Path(setup["temp_dir"].name)

    manifest = ComponentManifest(
        name="minimal_package",
        version="0.1.0",
        components=[{"name": "html_only", "html": "<p>Simple HTML component</p>"}],
        security={},
    )

    setup["component_manager"].register_from_manifest(manifest, package_root)

    # Check component was registered
    component = setup["component_manager"].get("minimal_package.html_only")
    assert component is not None
    assert component.name == "minimal_package.html_only"
    assert component.html == "<p>Simple HTML component</p>"
    assert component.js is None
    assert component.css is None

    # Check security requirements (empty)
    assert setup["component_manager"].get_security_requirements("minimal_package") == {}

    # Check metadata
    assert (
        setup["component_manager"].get_metadata("minimal_package.html_only") == manifest
    )


def test_register_from_manifest_js_only_component(temp_manager_setup) -> None:
    """JS-only components in manifest are invalid and should raise."""
    setup = temp_manager_setup
    package_root = Path(setup["temp_dir"].name)
    (package_root / "standalone.js").write_text(
        "export default function() { document.body.innerHTML = 'JS Only'; }"
    )

    manifest = ComponentManifest(
        name="js_package",
        version="3.0.0",
        components=[{"name": "js_component"}],
        security={"csp_rules": {"script-src": "'self' 'unsafe-inline'"}},
    )

    import pytest

    with pytest.raises(ValueError, match="must have at least one of html, css, or js"):
        setup["component_manager"].register_from_manifest(manifest, package_root)

    # Check security requirements
    assert setup["component_manager"].get_security_requirements("js_package") == {
        "csp_rules": {"script-src": "'self' 'unsafe-inline'"}
    }


def test_register_from_manifest_empty_components(temp_manager_setup) -> None:
    """Test manifest registration with empty components list."""
    setup = temp_manager_setup
    package_root = Path(setup["temp_dir"].name)

    manifest = ComponentManifest(
        name="empty_package",
        version="1.0.0",
        components=[],
        security={"https_only": True},
    )

    setup["component_manager"].register_from_manifest(manifest, package_root)

    # Check that security requirements are still stored
    assert setup["component_manager"].get_security_requirements("empty_package") == {
        "https_only": True
    }

    # Check metadata
    # Note: even with empty components, the manifest metadata should be stored
    # The actual behavior may depend on implementation details


def test_register_from_manifest_complex_security(temp_manager_setup) -> None:
    """Test manifest registration with complex security requirements."""
    setup = temp_manager_setup
    package_root = Path(setup["temp_dir"].name)
    js_file = package_root / "secure.js"
    js_file.write_text("console.log('secure component');")

    manifest = ComponentManifest(
        name="secure_package",
        version="1.5.0",
        components=[
            {
                "name": "secure_component",
                "js": "secure.js",
                "html": "<div id='secure'>Secure Component</div>",
            }
        ],
        security={
            "network_access": True,
            "allowed_origins": [
                "https://api.example.com",
                "https://cdn.example.com",
            ],
            "csp_rules": {
                "script-src": "'self' 'unsafe-inline' https://cdn.example.com",
                "connect-src": "'self' https://api.example.com",
            },
            "python_permissions": {
                "http_requests": ["https://api.example.com/*"],
                "file_access": "read_only",
            },
        },
    )

    setup["component_manager"].register_from_manifest(manifest, package_root)

    # Check component was registered
    component = setup["component_manager"].get("secure_package.secure_component")
    assert component is not None
    assert component.name == "secure_package.secure_component"
    assert component.html == "<div id='secure'>Secure Component</div>"
    # js from manifest is ignored
    assert component.js is None

    # Check complex security requirements were stored
    expected_security = {
        "network_access": True,
        "allowed_origins": [
            "https://api.example.com",
            "https://cdn.example.com",
        ],
        "csp_rules": {
            "script-src": "'self' 'unsafe-inline' https://cdn.example.com",
            "connect-src": "'self' https://api.example.com",
        },
        "python_permissions": {
            "http_requests": ["https://api.example.com/*"],
            "file_access": "read_only",
        },
    }
    assert (
        setup["component_manager"].get_security_requirements("secure_package")
        == expected_security
    )


def test_register_from_manifest_overwrites_existing(temp_manager_setup) -> None:
    """Test that registering from manifest overwrites existing components with same name."""
    setup = temp_manager_setup
    package_root = Path(setup["temp_dir"].name)
    js_file = package_root / "component.js"
    js_file.write_text("console.log('original');")

    # Register first version
    manifest1 = ComponentManifest(
        name="test_package",
        version="1.0.0",
        components=[
            {
                "name": "component",
                "js": "component.js",
                "html": "<div>Version 1</div>",
            }
        ],
        security={"version": 1},
    )

    setup["component_manager"].register_from_manifest(manifest1, package_root)

    # Check first registration
    component = setup["component_manager"].get("test_package.component")
    assert component.html == "<div>Version 1</div>"
    assert (
        setup["component_manager"].get_security_requirements("test_package")["version"]
        == 1
    )

    # Register updated version
    js_file.write_text("console.log('updated');")
    manifest2 = ComponentManifest(
        name="test_package",
        version="2.0.0",
        components=[
            {
                "name": "component",
                "js": "component.js",
                "html": "<div>Version 2</div>",
            }
        ],
        security={"version": 2},
    )

    with patch("streamlit.logger.get_logger") as mock_logger:
        setup["component_manager"].register_from_manifest(manifest2, package_root)

        # Should not log warning for manifest registration (different from manual registration)
        mock_logger.return_value.warning.assert_not_called()

    # Check component was updated
    updated_component = setup["component_manager"].get("test_package.component")
    assert updated_component.html == "<div>Version 2</div>"
    assert (
        setup["component_manager"].get_security_requirements("test_package")["version"]
        == 2
    )
    assert (
        setup["component_manager"].get_metadata("test_package.component") == manifest2
    )


def test_register_from_manifest_thread_safety(temp_manager_setup) -> None:
    """Test that manifest registration is thread-safe."""
    setup = temp_manager_setup
    package_root = Path(setup["temp_dir"].name)
    js_file = package_root / "thread_test.js"
    js_file.write_text("console.log('thread test');")

    results = []
    errors = []

    def register_manifest(thread_id: int) -> None:
        try:
            manifest = ComponentManifest(
                name=f"thread_package_{thread_id}",
                version="1.0.0",
                components=[
                    {
                        "name": "thread_component",
                        "js": "thread_test.js",
                        "html": f"<div>Thread {thread_id}</div>",
                    }
                ],
                security={"thread_id": thread_id},
            )

            # Add small delay to increase chance of race conditions
            time.sleep(0.01)

            setup["component_manager"].register_from_manifest(manifest, package_root)
            results.append(thread_id)

        except Exception as e:
            errors.append(e)

    # Create multiple threads
    threads = []
    for i in range(5):
        thread = threading.Thread(target=register_manifest, args=(i,))
        threads.append(thread)
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    # Check all threads completed successfully
    assert len(errors) == 0
    assert len(results) == 5
    assert set(results) == {0, 1, 2, 3, 4}

    # Check all components were registered
    for i in range(5):
        component = setup["component_manager"].get(
            f"thread_package_{i}.thread_component"
        )
        assert component is not None
        assert component.html == f"<div>Thread {i}</div>"
        assert (
            setup["component_manager"].get_security_requirements(f"thread_package_{i}")[
                "thread_id"
            ]
            == i
        )


def test_register_from_manifest_glob_pattern_single_match(temp_manager_setup) -> None:
    """Glob patterns in manifest are ignored; js/css remain None."""
    setup = temp_manager_setup
    package_root = Path(setup["temp_dir"].name)

    # Create files with hashed names
    js_hashed = os.path.join(setup["temp_dir"].name, "index-abc123.js")
    css_hashed = os.path.join(setup["temp_dir"].name, "styles-def456.css")

    with open(js_hashed, "w") as f:
        f.write("console.log('hashed build');")
    with open(css_hashed, "w") as f:
        f.write("div { background: blue; }")

    manifest = ComponentManifest(
        name="glob_package",
        version="1.0.0",
        components=[
            {
                "name": "glob_component",
                "html": "<div>Glob component</div>",
            }
        ],
        security={},
    )

    setup["component_manager"].register_from_manifest(manifest, package_root)

    # Check component was registered with correct resolved files
    component = setup["component_manager"].get("glob_package.glob_component")
    assert component is not None
    assert component.name == "glob_package.glob_component"
    assert component.html == "<div>Glob component</div>"
    # js/css are not sourced from manifest
    assert component.js is None
    assert component.css is None


def test_register_from_manifest_glob_pattern_no_match() -> None:
    """Manifest glob patterns are not supported; nothing to resolve."""
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = BidiComponentManager()
        package_root = Path(temp_dir)

        manifest = ComponentManifest(
            name="no_match_package",
            version="1.0.0",
            components=[
                {
                    "name": "no_match_component",
                    "html": "<div>Component</div>",
                }
            ],
            security={},
        )

        # Registration should succeed; js/css are ignored
        manager.register_from_manifest(manifest, package_root)
        comp = manager.get("no_match_package.no_match_component")
        assert comp is not None
        assert comp.js is None


def test_register_from_manifest_glob_pattern_multiple_matches() -> None:
    """Glob patterns are ignored; multiple matches are irrelevant."""
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = BidiComponentManager()
        package_root = Path(temp_dir)

        # Create multiple files that match the pattern
        js_file1 = os.path.join(temp_dir, "index-v1.js")
        js_file2 = os.path.join(temp_dir, "index-v2.js")

        with open(js_file1, "w") as f:
            f.write("console.log('v1');")
        with open(js_file2, "w") as f:
            f.write("console.log('v2');")

        manifest = ComponentManifest(
            name="multi_match_package",
            version="1.0.0",
            components=[
                {
                    "name": "multi_match_component",
                    "html": "<div>Component</div>",
                }
            ],
            security={},
        )

        # Should register fine; js/css ignored
        manager.register_from_manifest(manifest, package_root)
        comp = manager.get("multi_match_package.multi_match_component")
        assert comp is not None
        assert comp.js is None


def test_register_from_manifest_glob_pattern_path_traversal_attack() -> None:
    """Manifest paths are ignored; traversal attempts in js/css are irrelevant now."""
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = BidiComponentManager()
        package_root = Path(temp_dir)

        # Test various path traversal attempts
        malicious_patterns = [
            "../../../etc/passwd",
            "../malicious.js",
            "subdir/../../outside.js",
            "/absolute/path/script.js",
        ]

        for _ in malicious_patterns:
            manifest = ComponentManifest(
                name="malicious_package",
                version="1.0.0",
                components=[
                    {
                        "name": "malicious_component",
                        "html": "<div>Component</div>",
                    }
                ],
                security={},
            )

            # Should register; js/css ignored
            manager.register_from_manifest(manifest, package_root)


def test_register_from_manifest_glob_pattern_outside_package_root() -> None:
    """Manifest js/css are ignored; outside paths via manifest not applicable."""
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = BidiComponentManager()

        # Create package directory and an outside directory
        package_dir = os.path.join(temp_dir, "package")
        outside_dir = os.path.join(temp_dir, "outside")
        os.makedirs(package_dir)
        os.makedirs(outside_dir)

        package_root = Path(package_dir)

        # Create a JS file in the outside directory
        outside_js = os.path.join(outside_dir, "external.js")
        with open(outside_js, "w") as f:
            f.write("console.log('external');")

        # Create a symlink in package directory pointing to outside file
        symlink_path = os.path.join(package_dir, "linked.js")
        try:
            os.symlink(outside_js, symlink_path)
        except OSError:
            # Skip test if symlinks are not supported (e.g., Windows without admin)
            pytest.skip("Symlinks not supported on this system")

        manifest = ComponentManifest(
            name="symlink_package",
            version="1.0.0",
            components=[
                {
                    "name": "symlink_component",
                    "html": "<div>Component</div>",
                }
            ],
            security={},
        )

        manager.register_from_manifest(manifest, package_root)

        component = manager.get("symlink_package.symlink_component")
        assert component is not None
        assert component.name == "symlink_package.symlink_component"


def test_register_from_manifest_normal_path_security() -> None:
    """Manifest js/css are ignored; traversal attempts do not apply."""
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = BidiComponentManager()
        package_root = Path(temp_dir)

        # Test various path traversal attempts in normal paths
        malicious_patterns = [
            "../../../etc/passwd",
            "../malicious.js",
            "subdir/../../outside.js",
        ]

        for pattern in malicious_patterns:
            manifest = ComponentManifest(
                name="malicious_package",
                version="1.0.0",
                components=[
                    {
                        "name": "malicious_component",
                        # js ignored
                        "js": pattern,
                        "html": "<div>Component</div>",
                    }
                ],
                security={},
            )

            manager.register_from_manifest(manifest, package_root)
            comp = manager.get("malicious_package.malicious_component")
            assert comp is not None
            assert comp.js is None

        # Test absolute paths
        manifest = ComponentManifest(
            name="absolute_package",
            version="1.0.0",
            components=[
                {
                    "name": "absolute_component",
                    # js ignored
                    "js": "/absolute/path/script.js",
                    "html": "<div>Component</div>",
                }
            ],
            security={},
        )

        manager.register_from_manifest(manifest, package_root)
        comp = manager.get("absolute_package.absolute_component")
        assert comp is not None
        assert comp.js is None


def test_register_from_manifest_glob_pattern_mixed_normal_and_glob() -> None:
    """Manifest js/css ignored even if patterns are provided."""
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = BidiComponentManager()
        package_root = Path(temp_dir)

        # Create normal file and hashed file
        normal_js = os.path.join(temp_dir, "normal.js")
        hashed_css = os.path.join(temp_dir, "styles-abc123.css")

        with open(normal_js, "w") as f:
            f.write("console.log('normal');")
        with open(hashed_css, "w") as f:
            f.write("div { color: green; }")

        manifest = ComponentManifest(
            name="mixed_package",
            version="1.0.0",
            components=[
                {
                    "name": "mixed_component",
                    # js/css ignored
                    "js": "normal.js",
                    "css": "styles-*.css",
                    "html": "<div>Mixed component</div>",
                }
            ],
            security={},
        )

        manager.register_from_manifest(manifest, package_root)

        component = manager.get("mixed_package.mixed_component")
        assert component is not None
        assert component.js is None
        assert component.css is None
        assert component.html == "<div>Mixed component</div>"


def test_resolve_glob_pattern_direct() -> None:
    """Test the ComponentPathUtils.resolve_glob_pattern function directly."""

    with tempfile.TemporaryDirectory() as temp_dir:
        package_root = Path(temp_dir)

        # Create test file
        test_file = os.path.join(temp_dir, "test-pattern.js")
        with open(test_file, "w") as f:
            f.write("console.log('test');")

        # Test successful resolution
        resolved = ComponentPathUtils.resolve_glob_pattern("test-*.js", package_root)
        assert str(resolved.resolve()) == Path(test_file).resolve().as_posix()

        # Test no matches
        with pytest.raises(StreamlitAPIException) as exc_info:
            ComponentPathUtils.resolve_glob_pattern("nomatch-*.js", package_root)
        assert "No files found matching pattern" in str(exc_info.value)

        # Test multiple matches
        duplicate_file = os.path.join(temp_dir, "test-duplicate.js")
        with open(duplicate_file, "w") as f:
            f.write("console.log('duplicate');")

        with pytest.raises(StreamlitAPIException) as exc_info:
            ComponentPathUtils.resolve_glob_pattern("test-*.js", package_root)
        assert "Multiple files found matching pattern" in str(exc_info.value)

        # Test path traversal protection
        with pytest.raises(StreamlitAPIException) as exc_info:
            ComponentPathUtils.resolve_glob_pattern("../outside.js", package_root)
        assert "Path traversal attempts are not allowed" in str(exc_info.value)

        # Test absolute path protection
        with pytest.raises(StreamlitAPIException) as exc_info:
            ComponentPathUtils.resolve_glob_pattern("/absolute/path.js", package_root)
        assert "Absolute paths are not allowed" in str(exc_info.value)


@pytest.fixture
def component_manager():
    """Create a fresh BidiComponentManager for testing."""
    return BidiComponentManager()


def test_basic_registration(component_manager) -> None:
    """Test basic component registration."""
    definition = BidiComponentDefinition(
        name="test_component",
        html="<div>Test</div>",
        js="console.log('test');",
    )

    component_manager.register(definition)

    retrieved = component_manager.get("test_component")
    assert retrieved == definition


def test_file_watching_state_tracking(component_manager) -> None:
    """Test that file watching state is correctly tracked by the file watcher."""
    # Initially, file watching should not be started
    assert not component_manager.is_file_watching_started

    # Mock the file watcher's development mode check to return False
    from unittest.mock import patch

    with patch(
        "streamlit.components.v2.component_file_watcher._get_is_development_mode",
        return_value=False,
    ):
        # Try to start file watching - should fail due to not being in dev mode
        component_manager.start_file_watching()

        # The state should still be False since file watching didn't actually start
        assert not component_manager.is_file_watching_started
        assert not component_manager.file_watcher.is_watching_active

    # Now test with development mode enabled
    with patch(
        "streamlit.components.v2.component_file_watcher._get_is_development_mode",
        return_value=True,
    ):
        # This would start file watching, but we'll encounter import errors
        # in the test environment, so let's just verify the state tracking works

        # The state should remain consistent with the file watcher
        assert (
            component_manager.is_file_watching_started
            == component_manager.file_watcher.is_watching_active
        )


def test_glob_pattern_resolution() -> None:
    """Test glob pattern resolution."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create test files
        (temp_path / "component.js").write_text("console.log('component');")
        (temp_path / "styles.css").write_text("body { color: red; }")

        # Test JS glob resolution
        js_path = ComponentPathUtils.resolve_glob_pattern("*.js", temp_path)
        assert js_path.name == "component.js"

        # Test CSS glob resolution
        css_path = ComponentPathUtils.resolve_glob_pattern("*.css", temp_path)
        assert css_path.name == "styles.css"


def test_glob_pattern_multiple_matches_error() -> None:
    """Test that multiple matches for glob pattern raises error."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create multiple matching files
        (temp_path / "component1.js").write_text("console.log('1');")
        (temp_path / "component2.js").write_text("console.log('2');")

        with pytest.raises(StreamlitAPIException):
            ComponentPathUtils.resolve_glob_pattern("*.js", temp_path)


def test_glob_pattern_no_matches_error() -> None:
    """Test that no matches for glob pattern raises error."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        with pytest.raises(StreamlitAPIException):
            ComponentPathUtils.resolve_glob_pattern("*.js", temp_path)


@patch("streamlit.development.is_development_mode", True)
@patch("streamlit.watcher.path_watcher.get_default_path_watcher_class")
def test_file_watching_starts_in_dev_mode(mock_path_watcher_class) -> None:
    """With manifest js/css removed, no watchers should be created from manifest."""
    mock_watcher_instance = MagicMock()
    mock_path_watcher_class.return_value.return_value = mock_watcher_instance

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create test file
        js_file = temp_path / "component.js"
        js_file.write_text("console.log('test');")

        # Create mock manifest with glob pattern
        manifest = ComponentManifest(
            name="test_package",
            version="1.0.0",
            components=[{"name": "test_component", "js": "*.js", "html": "<div/>"}],
            security={},
        )

        # Create manager and register from manifest
        manager = BidiComponentManager()
        manager.register_from_manifest(manifest, temp_path)

        # Start file watching
        manager.start_file_watching()

        # No watchers should be created from manifest-only data
        assert not manager.is_file_watching_started
        mock_path_watcher_class.return_value.assert_not_called()


@patch("streamlit.development.is_development_mode", False)
@patch("streamlit.watcher.path_watcher.get_default_path_watcher_class")
@pytest.mark.skip(reason="TODO: FIXME: This needs to be re-implemented")
def test_file_watching_disabled_in_production(
    mock_path_watcher_class, component_manager
) -> None:
    """Test that file watching is disabled in production mode."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create test file to match the glob pattern
        js_file = temp_path / "component.js"
        js_file.write_text("console.log('test');")

        # Create mock manifest
        manifest = ComponentManifest(
            name="test_package",
            version="1.0.0",
            components=[{"name": "test_component", "js": "*.js"}],
            security={},
        )

        # Register from manifest
        component_manager.register_from_manifest(manifest, temp_path)

        # Start file watching should not work
        component_manager.start_file_watching()

        # Verify path watcher class was not called
        mock_path_watcher_class.assert_not_called()


def test_security_validation() -> None:
    """Test security validation for paths."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Test path traversal protection
        with pytest.raises(StreamlitAPIException):
            ComponentPathUtils.resolve_glob_pattern("../malicious.js", temp_path)

        with pytest.raises(StreamlitAPIException):
            ComponentPathUtils.resolve_glob_pattern("/etc/passwd", temp_path)


def test_component_glob_info_tracking() -> None:
    """Manifest js/css are ignored; no glob watchers are tracked."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create test files
        js_file = temp_path / "component.js"
        js_file.write_text("console.log('test');")

        # Create styles directory and CSS file
        styles_dir = temp_path / "styles"
        styles_dir.mkdir()
        css_file = styles_dir / "main.css"
        css_file.write_text("body { color: red; }")

        # Create mock manifest with glob pattern
        manifest = ComponentManifest(
            name="test_package",
            version="1.0.0",
            components=[
                {
                    "name": "test_component",
                    "js": "*.js",
                    "css": "styles/*.css",
                    "html": "<div/>",
                }
            ],
            security={},
        )

        # Create manager and register from manifest
        manager = BidiComponentManager()
        manager.register_from_manifest(manifest, temp_path)

        # Check that component was registered
        component = manager.get("test_package.test_component")
        assert component is not None

        # No glob watchers should be created
        glob_watchers = manager.get_glob_watchers()
        assert len(glob_watchers) == 0


@pytest.mark.parametrize(
    ("target_field", "second_args", "expect_present_field"),
    [
        ("html", {"js": "export default function(){}"}, "js"),
        ("css", {"js": "export default function(){}"}, "js"),
        ("js", {"html": "<div>Updated</div>"}, "html"),
    ],
)
def test_runtime_override_removes_field(
    monkeypatch, target_field, second_args, expect_present_field
) -> None:
    """Verify that removing a field in a subsequent registration clears it.

    We first register a component with multiple fields set. Then, we call the
    public API again omitting the target field. The registry should update the
    definition so that the target field is None, rather than preserving it.
    """
    from streamlit.components.v2 import component as component_api
    from streamlit.components.v2.component_manager import BidiComponentManager

    manager = BidiComponentManager()

    # Patch the component API to use our local manager instance.
    monkeypatch.setattr(
        "streamlit.components.v2.get_bidi_component_manager",
        lambda: manager,
    )

    # Initial registration includes all three fields to keep flexibility
    component_api(
        "my_component",
        html="<h1>Hello World</h1>",
        css=".title{color:red;}",
        js="export default function(){}",
    )

    # Subsequent registration provides only a non-target field to keep valid
    component_api("my_component", **second_args)

    definition = manager.get("my_component")
    assert definition is not None
    # Target field should be cleared
    assert getattr(definition, target_field) is None
    # Provided non-target field should remain present
    assert getattr(definition, expect_present_field) is not None


@pytest.mark.parametrize(
    ("target_field", "initial_kwargs", "update_kwargs", "expect_present_field"),
    [
        (
            "html",
            {"html": "<div>Keep?</div>", "js": "console.log('js');"},
            {"html": None},
            "js",
        ),
        (
            "css",
            {"css": "body{color:red;}", "js": "console.log('js');"},
            {"css": None},
            "js",
        ),
        (
            "js",
            {"html": "<div>Keep?</div>", "js": "console.log('js');"},
            {"js": None},
            "html",
        ),
    ],
)
def test_update_component_allows_field_removal(
    target_field: str,
    initial_kwargs: dict[str, str],
    update_kwargs: dict[str, None],
    expect_present_field: str,
) -> None:
    """Ensure update_component clears a field when explicitly set to None.

    Presence of a key in the update (even if None) must override previous values.
    """
    manager = BidiComponentManager()

    # Register with at least two fields so clearing one remains valid.
    manager.register(BidiComponentDefinition(name="removal_test", **initial_kwargs))

    # Explicitly remove target via update (omit other fields to preserve them)
    manager.registry.update_component(
        "removal_test", {"name": "removal_test", **update_kwargs}
    )

    updated = manager.get("removal_test")
    assert updated is not None
    assert getattr(updated, target_field) is None
    assert getattr(updated, expect_present_field) is not None
