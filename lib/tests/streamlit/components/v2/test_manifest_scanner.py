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
from unittest.mock import Mock, mock_open, patch

from streamlit.components.v2.manifest_scanner import ComponentManifest


def test_process_single_package_no_files() -> None:
    """Test _process_single_package with distribution that has no files."""
    from streamlit.components.v2.manifest_scanner import _process_single_package

    # Create mock distribution with no files
    mock_dist = Mock()
    mock_dist.files = None
    mock_dist.name = "test-package"

    result = _process_single_package(mock_dist)
    assert result is None


def test_process_single_package_no_pyproject() -> None:
    """Test _process_single_package with distribution that has no pyproject.toml."""
    from streamlit.components.v2.manifest_scanner import _process_single_package

    # Create mock distribution with files but no pyproject.toml
    mock_file = Mock()
    mock_file.name = "some_file.py"

    mock_dist = Mock()
    mock_dist.files = [mock_file]
    mock_dist.name = "test-package"

    result = _process_single_package(mock_dist)
    assert result is None


def test_process_single_package_no_streamlit_config() -> None:
    """Test _process_single_package with pyproject.toml but no Streamlit config."""
    from streamlit.components.v2.manifest_scanner import _process_single_package

    # Create mock file and distribution
    mock_file = Mock()
    mock_file.name = "pyproject.toml"

    mock_dist = Mock()
    mock_dist.files = [mock_file]
    mock_dist.name = "test-package"
    mock_dist.locate_file.return_value = "/path/to/pyproject.toml"

    # Mock toml content without Streamlit config
    toml_content = """
    [build-system]
    requires = ["setuptools"]

    [project]
    name = "test-package"
    """

    with (
        patch("builtins.open", mock_open(read_data=toml_content)),
        patch("streamlit.components.v2.manifest_scanner.toml.load") as mock_toml_load,
        patch("streamlit.components.v2.manifest_scanner.Path"),
    ):
        mock_toml_load.return_value = {
            "build-system": {"requires": ["setuptools"]},
            "project": {"name": "test-package"},
        }

        result = _process_single_package(mock_dist)
        assert result is None


def test_process_single_package_valid_manifest() -> None:
    """Test _process_single_package with valid Streamlit component manifest."""
    from streamlit.components.v2.manifest_scanner import _process_single_package

    # Create mock file and distribution
    mock_file = Mock()
    mock_file.name = "pyproject.toml"

    mock_init_file = Mock()
    mock_init_file.__str__ = Mock(return_value="test_package/__init__.py")

    mock_dist = Mock()
    mock_dist.files = [mock_file, mock_init_file]
    mock_dist.name = "test-package"
    mock_dist.locate_file.side_effect = (
        lambda f: "/path/to/pyproject.toml"
        if f == mock_file
        else "/path/to/test_package/__init__.py"
    )
    mock_dist.metadata.get.return_value = "test-package"

    with (
        patch("builtins.open", mock_open()),
        patch("streamlit.components.v2.manifest_scanner.toml.load") as mock_toml_load,
        patch("streamlit.components.v2.manifest_scanner.Path") as mock_path,
    ):
        mock_toml_load.return_value = {
            "project": {"name": "test-package", "version": "1.0.0"},
            "tool": {
                "streamlit": {
                    "component": {
                        "components": [
                            {
                                "name": "slider",
                                "js": "slider.js",
                                "css": "slider.css",
                            }
                        ],
                        "security": {"network_access": True},
                    }
                }
            },
        }

        # Mock Path behavior
        mock_path_instance = Mock()
        mock_path_instance.parent = "/path/to/test_package"
        mock_path.return_value = mock_path_instance

        result = _process_single_package(mock_dist)

        assert result is not None
        manifest, package_root = result
        assert manifest.name == "test-package"
        assert manifest.version == "1.0.0"
        assert len(manifest.components) == 1
        assert manifest.components[0]["name"] == "slider"
        assert manifest.security == {"network_access": True}


def test_scan_component_manifests_performance() -> None:
    """Test that scanning handles multiple packages correctly."""
    from streamlit.components.v2.manifest_scanner import (
        scan_component_manifests,
    )

    # Create mock distributions with proper name and metadata attributes
    mock_dists = []
    for i in range(10):
        mock_dist = Mock()
        # Make some packages look like streamlit components
        if i < 5:
            mock_dist.name = f"streamlit-package-{i}"
            package_name = f"streamlit-package-{i}"
        else:
            mock_dist.name = f"package-{i}"
            package_name = f"package-{i}"

        # Mock metadata that returns proper strings
        mock_metadata = Mock()

        # Create closure to capture the current value of i
        def make_metadata_side_effect(package_index, pkg_name):
            def side_effect(key, default=""):
                return {
                    "Name": pkg_name,
                    "Summary": f"Description for {pkg_name}",
                }.get(key, default)

            return side_effect

        mock_metadata.get.side_effect = make_metadata_side_effect(i, package_name)
        mock_metadata.get_all.return_value = []
        mock_dist.metadata = mock_metadata
        mock_dists.append(mock_dist)

    results = []
    for i in range(3):  # Only 3 packages have valid manifests
        results.append(
            (
                ComponentManifest(
                    name=f"component_{i}",
                    version="1.0.0",
                    components=[{"name": "test"}],
                    security={},
                ),
                Path(f"/path/to/component_{i}"),
            )
        )

    with (
        patch(
            "streamlit.components.v2.manifest_scanner.importlib.metadata.distributions"
        ) as mock_distributions,
        patch(
            "streamlit.components.v2.manifest_scanner._process_single_package"
        ) as mock_process,
    ):
        mock_distributions.return_value = mock_dists
        mock_process.side_effect = (
            lambda dist: results[int(dist.name.split("-")[-1])]
            if "streamlit" in dist.name and int(dist.name.split("-")[-1]) < 3
            else None
        )

        manifests = scan_component_manifests(max_workers=2)

        # Should return 3 valid manifests
        assert len(manifests) == 3
        assert all(manifest.name.startswith("component_") for manifest, _ in manifests)


def test_scan_component_manifests_max_workers() -> None:
    """Test that max_workers parameter is respected."""
    from streamlit.components.v2.manifest_scanner import (
        scan_component_manifests,
    )

    # Create a small number of mock distributions with proper name and metadata attributes
    mock_dists = []
    for i in range(3):
        mock_dist = Mock()
        # Make all packages look like streamlit components for this test
        mock_dist.name = f"streamlit-package-{i}"
        package_name = f"streamlit-package-{i}"

        # Mock metadata that returns proper strings
        mock_metadata = Mock()

        # Create closure to capture the current value of i
        def make_metadata_side_effect(package_index, pkg_name):
            def side_effect(key, default=""):
                return {
                    "Name": pkg_name,
                    "Summary": f"Description for {pkg_name}",
                }.get(key, default)

            return side_effect

        mock_metadata.get.side_effect = make_metadata_side_effect(i, package_name)
        mock_metadata.get_all.return_value = []
        mock_dist.metadata = mock_metadata
        mock_dists.append(mock_dist)

    with (
        patch(
            "streamlit.components.v2.manifest_scanner.importlib.metadata.distributions"
        ) as mock_distributions,
        patch(
            "streamlit.components.v2.manifest_scanner._process_single_package"
        ) as mock_process,
        patch(
            "streamlit.components.v2.manifest_scanner.ThreadPoolExecutor"
        ) as mock_executor,
    ):
        mock_distributions.return_value = mock_dists
        mock_process.return_value = None

        # Mock the executor to work with as_completed
        mock_executor_instance = Mock()
        mock_executor.return_value.__enter__.return_value = mock_executor_instance
        mock_future = Mock()
        mock_future.result.return_value = None
        mock_executor_instance.submit.return_value = mock_future

        # Mock as_completed to return the futures immediately
        with patch(
            "streamlit.components.v2.manifest_scanner.as_completed"
        ) as mock_as_completed:
            mock_as_completed.return_value = [mock_future] * len(mock_dists)

            # Test with explicit max_workers
            scan_component_manifests(max_workers=2)
            mock_executor.assert_called_with(max_workers=2)

            # Test with default max_workers (should be limited by number of packages)
            scan_component_manifests()
            # Should use min(default, len(distributions), 16) = min(?, 3, 16) = 3
            assert mock_executor.call_args[1]["max_workers"] <= 3


def test_scan_component_manifests_empty_distributions() -> None:
    """Test scanning with no installed packages."""
    from streamlit.components.v2.manifest_scanner import (
        scan_component_manifests,
    )

    with patch(
        "streamlit.components.v2.manifest_scanner.importlib.metadata.distributions"
    ) as mock_distributions:
        mock_distributions.return_value = []

        manifests = scan_component_manifests()
        assert manifests == []


def test_scan_component_manifests_error_handling() -> None:
    """Test that scanning handles errors gracefully."""
    from streamlit.components.v2.manifest_scanner import (
        scan_component_manifests,
    )

    # Create mock distributions, some will cause errors
    mock_dists = []
    for i in range(5):
        mock_dist = Mock()
        # Make all packages look like streamlit components for this test
        mock_dist.name = f"streamlit-package-{i}"
        package_name = f"streamlit-package-{i}"

        # Mock metadata that returns proper strings
        mock_metadata = Mock()

        # Create closure to capture the current value of i
        def make_metadata_side_effect(package_index, pkg_name):
            def side_effect(key, default=""):
                return {
                    "Name": pkg_name,
                    "Summary": f"Description for {pkg_name}",
                }.get(key, default)

            return side_effect

        mock_metadata.get.side_effect = make_metadata_side_effect(i, package_name)
        mock_metadata.get_all.return_value = []
        mock_dist.metadata = mock_metadata
        mock_dists.append(mock_dist)

    def mock_process_with_errors(dist):
        if "package-2" in dist.name:
            # Simulate an error by returning None (what the real function does on error)
            return
        return  # For this test, all packages return None (no manifests found)

    with (
        patch(
            "streamlit.components.v2.manifest_scanner.importlib.metadata.distributions"
        ) as mock_distributions,
        patch(
            "streamlit.components.v2.manifest_scanner._process_single_package"
        ) as mock_process,
    ):
        mock_distributions.return_value = mock_dists
        mock_process.side_effect = mock_process_with_errors

        # Should not raise exception even with errors
        manifests = scan_component_manifests()
        assert manifests == []


# Tests for editable installs and _find_package_pyproject_toml function


def test_validate_pyproject_for_package_project_name_match() -> None:
    """Test _validate_pyproject_for_package with matching project name."""
    from streamlit.components.v2.manifest_scanner import _validate_pyproject_for_package

    with tempfile.TemporaryDirectory() as temp_dir:
        pyproject_path = Path(temp_dir) / "pyproject.toml"
        pyproject_content = """
[project]
name = "test-package"

        """

        pyproject_path.write_text(pyproject_content.strip())

        # Should match
        assert _validate_pyproject_for_package(
            pyproject_path, "test-package", "test_package"
        )
        assert _validate_pyproject_for_package(
            pyproject_path, "test_package", "test_package"
        )

        # Should not match
        assert not _validate_pyproject_for_package(
            pyproject_path, "different-package", "different_package"
        )


def test_validate_pyproject_for_package_streamlit_component_fallback() -> None:
    """Test _validate_pyproject_for_package falls back to streamlit component presence."""
    from streamlit.components.v2.manifest_scanner import _validate_pyproject_for_package

    with tempfile.TemporaryDirectory() as temp_dir:
        pyproject_path = Path(temp_dir) / "pyproject.toml"
        # No project name, but presence of tool.streamlit.component still accepted
        pyproject_content = """
[tool.streamlit.component]
components = []
        """

        pyproject_path.write_text(pyproject_content.strip())

        # Should match due to streamlit component presence (heuristic)
        assert _validate_pyproject_for_package(
            pyproject_path, "test-package", "test_package"
        )


def test_validate_pyproject_for_package_no_match() -> None:
    """Test _validate_pyproject_for_package with no matching criteria."""
    from streamlit.components.v2.manifest_scanner import _validate_pyproject_for_package

    with tempfile.TemporaryDirectory() as temp_dir:
        pyproject_path = Path(temp_dir) / "pyproject.toml"
        # No project name and no streamlit component config
        pyproject_content = """
[project]
name = "different-package"

[tool.other]
config = "value"
        """

        pyproject_path.write_text(pyproject_content.strip())

        # Should not match
        assert not _validate_pyproject_for_package(
            pyproject_path, "test-package", "test_package"
        )


def test_validate_pyproject_for_package_invalid_file() -> None:
    """Test _validate_pyproject_for_package with invalid file."""
    from streamlit.components.v2.manifest_scanner import _validate_pyproject_for_package

    with tempfile.TemporaryDirectory() as temp_dir:
        pyproject_path = Path(temp_dir) / "pyproject.toml"
        pyproject_path.write_text("invalid toml content [[[")

        # Should return False for invalid files
        assert not _validate_pyproject_for_package(
            pyproject_path, "test-package", "test_package"
        )


def test_validate_pyproject_for_package_uses_package_name() -> None:
    """Test _validate_pyproject_for_package correctly uses package_name parameter."""
    from streamlit.components.v2.manifest_scanner import _validate_pyproject_for_package

    with tempfile.TemporaryDirectory() as temp_dir:
        pyproject_path = Path(temp_dir) / "pyproject.toml"
        # Project name matches package_name but NOT dist_name
        pyproject_content = """
[project]
name = "my_component"
        """

        pyproject_path.write_text(pyproject_content.strip())

        # Should match because project name "my_component" matches package_name "my_component"
        # even though it doesn't match dist_name "my-awesome-component"
        assert _validate_pyproject_for_package(
            pyproject_path, "my-awesome-component", "my_component"
        )

        # Should not match when neither dist_name nor package_name match
        assert not _validate_pyproject_for_package(
            pyproject_path, "different-component", "different_component"
        )


def test_find_package_pyproject_toml_traditional_approach() -> None:
    """Test _find_package_pyproject_toml with traditional dist.files approach."""
    from streamlit.components.v2.manifest_scanner import _find_package_pyproject_toml

    # Create mock file and distribution
    mock_file = Mock()
    mock_file.name = "pyproject.toml"

    mock_dist = Mock()
    mock_dist.files = [mock_file]
    mock_dist.name = "test-package"
    mock_dist.locate_file.return_value = "/path/to/pyproject.toml"

    # Mock metadata properly
    mock_metadata = Mock()
    mock_metadata.get.return_value = "test-package"
    mock_dist.metadata = mock_metadata

    # Make sure read_text fails so it goes to the traditional approach
    mock_dist.read_text.side_effect = Exception("read_text not available")

    with (
        patch("streamlit.components.v2.manifest_scanner.Path") as mock_path_class,
        patch(
            "streamlit.components.v2.manifest_scanner._validate_pyproject_for_package"
        ) as mock_validate,
    ):
        # Create a real Path object that the function can use
        expected_path = Path("/path/to/pyproject.toml")
        mock_path_class.return_value = expected_path
        mock_validate.return_value = True

        result = _find_package_pyproject_toml(mock_dist)

        assert result == expected_path
        mock_dist.locate_file.assert_called_once_with(mock_file)
        mock_validate.assert_called_once_with(
            expected_path, "test-package", "test_package"
        )


def test_find_package_pyproject_toml_traditional_approach_fails() -> None:
    """Test _find_package_pyproject_toml when traditional approach fails but file exists."""
    from streamlit.components.v2.manifest_scanner import _find_package_pyproject_toml

    # Create mock file and distribution
    mock_file = Mock()
    mock_file.name = "pyproject.toml"

    mock_dist = Mock()
    mock_dist.files = [mock_file]
    mock_dist.name = "test-package"
    mock_dist.locate_file.side_effect = Exception("Failed to locate file")
    mock_dist.metadata.get.return_value = "test-package"

    with (
        patch(
            "streamlit.components.v2.manifest_scanner.importlib.util.find_spec"
        ) as mock_find_spec,
        patch(
            "streamlit.components.v2.manifest_scanner._validate_pyproject_for_package"
        ) as mock_validate,
        tempfile.TemporaryDirectory() as temp_dir,
    ):
        # Create package directory
        package_dir = Path(temp_dir) / "test_package"
        package_dir.mkdir()

        # Mock importlib to find the package
        mock_spec = Mock()
        mock_spec.origin = str(package_dir / "__init__.py")
        mock_find_spec.return_value = mock_spec

        # Create pyproject.toml file in the package directory
        pyproject_path = package_dir / "pyproject.toml"
        pyproject_path.write_text("[project]\nname = 'test-package'")

        # Mock validation to return True
        mock_validate.return_value = True

        result = _find_package_pyproject_toml(mock_dist)

        assert result == pyproject_path
        mock_find_spec.assert_called_once_with("test_package")
        mock_validate.assert_called_once_with(
            pyproject_path, "test-package", "test_package"
        )


def test_find_package_pyproject_toml_editable_install() -> None:
    """Test _find_package_pyproject_toml with editable install (no dist.files)."""
    from streamlit.components.v2.manifest_scanner import _find_package_pyproject_toml

    mock_dist = Mock()
    mock_dist.files = None  # Simulates editable install
    mock_dist.name = "test-package"
    mock_dist.metadata.get.return_value = "test-package"

    with (
        patch(
            "streamlit.components.v2.manifest_scanner.importlib.util.find_spec"
        ) as mock_find_spec,
        patch(
            "streamlit.components.v2.manifest_scanner._validate_pyproject_for_package"
        ) as mock_validate,
        tempfile.TemporaryDirectory() as temp_dir,
    ):
        # Create a real directory structure for testing
        package_dir = Path(temp_dir) / "test_package"
        package_dir.mkdir()
        pyproject_path = package_dir / "pyproject.toml"
        pyproject_path.write_text("[project]\nname = 'test-package'")

        # Mock importlib to find the package
        mock_spec = Mock()
        mock_spec.origin = str(package_dir / "__init__.py")
        mock_find_spec.return_value = mock_spec

        # Mock validation to return True
        mock_validate.return_value = True

        result = _find_package_pyproject_toml(mock_dist)

        assert result == pyproject_path
        mock_find_spec.assert_called_once_with("test_package")
        mock_validate.assert_called_once_with(
            pyproject_path, "test-package", "test_package"
        )


def test_find_package_pyproject_toml_no_parent_traversal() -> None:
    """Test _find_package_pyproject_toml does not traverse parent directories for security."""
    from streamlit.components.v2.manifest_scanner import _find_package_pyproject_toml

    mock_dist = Mock()
    mock_dist.files = None
    mock_dist.name = "test-package"
    mock_dist.metadata.get.return_value = "test-package"

    with (
        patch(
            "streamlit.components.v2.manifest_scanner.importlib.util.find_spec"
        ) as mock_find_spec,
        patch(
            "streamlit.components.v2.manifest_scanner._validate_pyproject_for_package"
        ) as mock_validate,
        tempfile.TemporaryDirectory() as temp_dir,
    ):
        # Create a nested directory structure
        src_dir = Path(temp_dir) / "src"
        src_dir.mkdir()
        package_dir = src_dir / "test_package"
        package_dir.mkdir()

        # Create pyproject.toml in the root directory (parent of src/)
        pyproject_path = Path(temp_dir) / "pyproject.toml"
        pyproject_path.write_text("[project]\nname = 'test-package'")

        # Mock importlib to find the package
        mock_spec = Mock()
        mock_spec.origin = str(package_dir / "__init__.py")
        mock_find_spec.return_value = mock_spec

        # Mock validation to return True
        mock_validate.return_value = True

        result = _find_package_pyproject_toml(mock_dist)

        # For security, should NOT find pyproject.toml in parent directory
        assert result is None
        mock_find_spec.assert_called_once_with("test_package")
        # Should check package directory but not find pyproject.toml there
        mock_validate.assert_not_called()


def test_find_package_pyproject_toml_read_text_approach() -> None:
    """Test _find_package_pyproject_toml using dist.read_text() method for editable installs."""
    from streamlit.components.v2.manifest_scanner import _find_package_pyproject_toml

    # Create a mock file that looks like a Python file
    mock_file = Mock()
    mock_file.name = (
        "__init__.py"  # This will match the condition in the implementation
    )
    mock_file.__str__ = Mock(return_value="__init__.py")  # Make sure str(file) works

    mock_dist = Mock()
    mock_dist.files = [mock_file]
    mock_dist.name = "test-package"
    mock_dist.metadata.get.return_value = "test-package"
    mock_dist.read_text.return_value = "[project]\nname = 'test-package'"

    with (
        patch(
            "streamlit.components.v2.manifest_scanner._validate_pyproject_for_package"
        ) as mock_validate,
        tempfile.TemporaryDirectory() as temp_dir,
    ):
        # Create a real pyproject.toml file that validation can find
        pyproject_path = Path(temp_dir) / "pyproject.toml"
        pyproject_path.write_text("[project]\nname = 'test-package'")

        # Mock locate_file to return a file in the same directory as pyproject.toml
        mock_dist.locate_file.return_value = Path(temp_dir) / "__init__.py"

        # Mock validation to return True
        mock_validate.return_value = True

        result = _find_package_pyproject_toml(mock_dist)

        assert result == pyproject_path
        mock_dist.read_text.assert_called_once_with("pyproject.toml")
        mock_validate.assert_called_once_with(
            pyproject_path, "test-package", "test_package"
        )


def test_find_package_pyproject_toml_path_distribution() -> None:
    """Test _find_package_pyproject_toml using Method 3 (find_spec) for editable installs."""
    from streamlit.components.v2.manifest_scanner import _find_package_pyproject_toml

    mock_dist = Mock()
    mock_dist.files = None  # No files to trigger Methods 1 and 2 failure
    mock_dist.name = "test-package"
    mock_dist.metadata.get.return_value = "test-package"

    # Make sure read_text fails so it doesn't use Method 1
    mock_dist.read_text.side_effect = Exception("read_text not available")

    with (
        patch(
            "streamlit.components.v2.manifest_scanner.importlib.util.find_spec"
        ) as mock_find_spec,
        patch(
            "streamlit.components.v2.manifest_scanner._validate_pyproject_for_package"
        ) as mock_validate,
        tempfile.TemporaryDirectory() as temp_dir,
    ):
        # Create pyproject.toml in temp directory
        pyproject_path = Path(temp_dir) / "pyproject.toml"
        pyproject_path.write_text("[project]\nname = 'test-package'")

        # Mock find_spec to return a spec that points to our temp directory
        mock_spec = Mock()
        mock_spec.origin = str(Path(temp_dir) / "__init__.py")
        mock_find_spec.return_value = mock_spec

        # Mock validation to return True
        mock_validate.return_value = True

        result = _find_package_pyproject_toml(mock_dist)

        assert result == pyproject_path
        mock_validate.assert_called_once_with(
            pyproject_path, "test-package", "test_package"
        )


def test_find_package_pyproject_toml_validation_rejects_wrong_package() -> None:
    """Test _find_package_pyproject_toml when validation rejects wrong package."""
    from streamlit.components.v2.manifest_scanner import _find_package_pyproject_toml

    mock_dist = Mock()
    mock_dist.files = None
    mock_dist.name = "test-package"
    mock_dist.metadata.get.return_value = "test-package"

    with (
        patch(
            "streamlit.components.v2.manifest_scanner.importlib.util.find_spec"
        ) as mock_find_spec,
        patch(
            "streamlit.components.v2.manifest_scanner._validate_pyproject_for_package"
        ) as mock_validate,
        tempfile.TemporaryDirectory() as temp_dir,
    ):
        # Create directory structure
        package_dir = Path(temp_dir) / "test_package"
        package_dir.mkdir()
        pyproject_path = package_dir / "pyproject.toml"
        pyproject_path.write_text(
            "[project]\nname = 'different-package'"
        )  # Wrong package

        # Mock importlib to find the package
        mock_spec = Mock()
        mock_spec.origin = str(package_dir / "__init__.py")
        mock_find_spec.return_value = mock_spec

        # Mock validation to return False (wrong package)
        mock_validate.return_value = False

        result = _find_package_pyproject_toml(mock_dist)

        assert result is None  # Should not find anything
        mock_validate.assert_called_once_with(
            pyproject_path, "test-package", "test_package"
        )


def test_find_package_pyproject_toml_read_text_fallback() -> None:
    """Test _find_package_pyproject_toml using read_text fallback method."""
    from streamlit.components.v2.manifest_scanner import _find_package_pyproject_toml

    mock_dist = Mock()
    mock_dist.name = "test-package"
    mock_dist.metadata.get.return_value = "test-package"
    mock_dist.read_text.return_value = "[project]\nname = 'test-package'"

    # Mock importlib to fail
    with (
        patch(
            "streamlit.components.v2.manifest_scanner.importlib.util.find_spec"
        ) as mock_find_spec,
        patch(
            "streamlit.components.v2.manifest_scanner._validate_pyproject_for_package"
        ) as mock_validate,
        tempfile.TemporaryDirectory() as temp_dir,
    ):
        mock_find_spec.side_effect = Exception("Package not found")

        # Create some files to work with
        package_dir = Path(temp_dir) / "test_package"
        package_dir.mkdir()
        pyproject_path = package_dir / "pyproject.toml"
        pyproject_path.write_text("[project]\nname = 'test-package'")

        # Create a mock file that looks like a Python file
        mock_file = Mock()
        mock_file.name = "some_file.py"
        mock_file.__str__ = Mock(return_value="some_file.py")
        mock_dist.files = [mock_file]
        mock_dist.locate_file.return_value = str(package_dir / "some_file.py")

        # Mock validation to return True
        mock_validate.return_value = True

        result = _find_package_pyproject_toml(mock_dist)

        assert result == pyproject_path
        mock_dist.read_text.assert_called_once_with("pyproject.toml")
        mock_validate.assert_called_once_with(
            pyproject_path, "test-package", "test_package"
        )


def test_find_package_pyproject_toml_not_found() -> None:
    """Test _find_package_pyproject_toml when pyproject.toml cannot be found."""
    from streamlit.components.v2.manifest_scanner import _find_package_pyproject_toml

    mock_dist = Mock()
    mock_dist.files = None
    mock_dist.name = "test-package"
    mock_dist.metadata.get.return_value = "test-package"

    # Mock importlib to fail
    with patch(
        "streamlit.components.v2.manifest_scanner.importlib.util.find_spec"
    ) as mock_find_spec:
        mock_find_spec.side_effect = Exception("Package not found")

        result = _find_package_pyproject_toml(mock_dist)

        assert result is None


def test_process_single_package_editable_install_success() -> None:
    """Test _process_single_package with successful editable install detection."""
    from streamlit.components.v2.manifest_scanner import _process_single_package

    mock_dist = Mock()
    mock_dist.files = None  # Editable install
    mock_dist.name = "my-awesome-component"
    mock_dist.metadata.get.return_value = "my-awesome-component"

    pyproject_content = {
        "project": {"name": "my-awesome-component", "version": "2.0.0"},
        "tool": {
            "streamlit": {
                "component": {
                    "components": [
                        {
                            "name": "slider",
                            "js": "slider.js",
                            "css": "slider.css",
                        }
                    ],
                    "security": {"network_access": False},
                }
            }
        },
    }

    with (
        patch(
            "streamlit.components.v2.manifest_scanner._find_package_pyproject_toml"
        ) as mock_find_pyproject,
        patch(
            "streamlit.components.v2.manifest_scanner.importlib.util.find_spec"
        ) as mock_find_spec,
        patch("builtins.open", mock_open()),
        patch("streamlit.components.v2.manifest_scanner.toml.load") as mock_toml_load,
        tempfile.TemporaryDirectory() as temp_dir,
    ):
        # Create real directories for testing
        package_dir = Path(temp_dir) / "my_awesome_component"
        package_dir.mkdir()
        pyproject_path = Path(temp_dir) / "pyproject.toml"
        pyproject_path.write_text("dummy content")

        # Mock the functions
        mock_find_pyproject.return_value = pyproject_path
        mock_toml_load.return_value = pyproject_content
        mock_spec = Mock()
        mock_spec.origin = str(package_dir / "__init__.py")
        mock_find_spec.return_value = mock_spec

        result = _process_single_package(mock_dist)

        assert result is not None
        manifest, package_root = result
        assert manifest.name == "my-awesome-component"
        assert manifest.version == "2.0.0"
        assert len(manifest.components) == 1
        assert manifest.components[0]["name"] == "slider"
        assert manifest.security == {"network_access": False}
        assert package_root == package_dir


def test_process_single_package_editable_install_fallback_to_pyproject_parent() -> None:
    """Test _process_single_package falls back to pyproject.toml parent for package root."""
    from streamlit.components.v2.manifest_scanner import _process_single_package

    mock_dist = Mock()
    mock_dist.files = None
    mock_dist.name = "test-component"
    mock_dist.metadata.get.return_value = "test-component"

    pyproject_content = {
        "project": {"name": "test-component", "version": "1.0.0"},
        "tool": {
            "streamlit": {
                "component": {
                    "components": [{"name": "widget"}],
                    "security": {},
                }
            }
        },
    }

    with (
        patch(
            "streamlit.components.v2.manifest_scanner._find_package_pyproject_toml"
        ) as mock_find_pyproject,
        patch(
            "streamlit.components.v2.manifest_scanner.importlib.util.find_spec"
        ) as mock_find_spec,
        patch("builtins.open", mock_open()),
        patch("streamlit.components.v2.manifest_scanner.toml.load") as mock_toml_load,
        tempfile.TemporaryDirectory() as temp_dir,
    ):
        # Create pyproject.toml in temp directory
        pyproject_path = Path(temp_dir) / "pyproject.toml"
        pyproject_path.write_text("dummy content")

        # Mock functions
        mock_find_pyproject.return_value = pyproject_path
        mock_toml_load.return_value = pyproject_content
        # Mock importlib to fail finding the package (for both calls)
        mock_find_spec.side_effect = Exception("Package not found")

        result = _process_single_package(mock_dist)

        assert result is not None
        manifest, package_root = result
        assert manifest.name == "test-component"
        assert package_root == Path(temp_dir)  # Should be pyproject.toml parent


def test_process_single_package_mixed_install_scenarios() -> None:
    """Test _process_single_package handles mixed scenarios correctly."""
    from streamlit.components.v2.manifest_scanner import _process_single_package

    mock_dist = Mock()
    mock_dist.files = None
    mock_dist.name = "mixed-component"
    mock_dist.metadata.get.return_value = "mixed-component"

    pyproject_content = {
        "project": {"name": "mixed-component", "version": "1.5.0"},
        "tool": {
            "streamlit": {
                "component": {
                    "components": [{"name": "chart"}],
                    "security": {"cors": True},
                }
            }
        },
    }

    with (
        patch(
            "streamlit.components.v2.manifest_scanner._find_package_pyproject_toml"
        ) as mock_find_pyproject,
        patch(
            "streamlit.components.v2.manifest_scanner.importlib.util.find_spec"
        ) as mock_find_spec,
        patch("builtins.open", mock_open()),
        patch("streamlit.components.v2.manifest_scanner.toml.load") as mock_toml_load,
        tempfile.TemporaryDirectory() as temp_dir,
    ):
        # Create real directories for testing
        package_dir = Path(temp_dir) / "mixed_component"
        package_dir.mkdir()
        pyproject_path = Path(temp_dir) / "pyproject.toml"
        pyproject_path.write_text("dummy content")

        # Mock functions
        mock_find_pyproject.return_value = pyproject_path
        mock_toml_load.return_value = pyproject_content
        mock_spec = Mock()
        mock_spec.origin = str(package_dir / "__init__.py")
        mock_find_spec.return_value = mock_spec

        result = _process_single_package(mock_dist)

        assert result is not None
        manifest, package_root = result
        assert manifest.name == "mixed-component"
        assert manifest.version == "1.5.0"
        assert package_root == package_dir
