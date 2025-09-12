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
from pathlib import Path
from typing import Final

from streamlit.errors import StreamlitAPIException
from streamlit.logger import get_logger

_LOGGER: Final = get_logger(__name__)


class ComponentPathUtils:
    """Utility class for component path operations and security validation."""

    @staticmethod
    def has_glob_characters(path: str) -> bool:
        """Check if a path contains glob pattern characters.

        Parameters
        ----------
        path : str
            The path to check

        Returns
        -------
        bool
            True if the path contains glob characters
        """
        return any(char in path for char in ["*", "?", "[", "]"])

    @staticmethod
    def validate_path_security(path: str) -> None:
        """Validate that a path doesn't contain security vulnerabilities.

        Parameters
        ----------
        path : str
            The path to validate

        Raises
        ------
        StreamlitAPIException
            If the path contains security vulnerabilities like path traversal attempts
        """
        # Check for path traversal attempts
        if ".." in path:
            raise StreamlitAPIException(
                f"Path traversal attempts are not allowed in component paths: {path}"
            )

        # Check for absolute paths
        if os.path.isabs(path):
            raise StreamlitAPIException(
                f"Absolute paths are not allowed in component paths: {path}"
            )

    @staticmethod
    def resolve_glob_pattern(pattern: str, package_root: Path) -> Path:
        """Resolve a glob pattern to a single file path with security checks.

        Parameters
        ----------
        pattern : str
            The glob pattern to resolve
        package_root : Path
            The package root directory for security validation

        Returns
        -------
        Path
            The resolved file path

        Raises
        ------
        StreamlitAPIException
            If zero or more than one file matches the pattern, or if security
            checks fail (path traversal attempts)
        """
        # Ensure pattern is relative and doesn't contain path traversal attempts
        if os.path.isabs(pattern):
            raise StreamlitAPIException(
                f"Absolute paths are not allowed in glob patterns: {pattern}"
            )

        # Check for path traversal attempts
        if ".." in pattern or pattern.startswith("/"):
            raise StreamlitAPIException(
                f"Path traversal attempts are not allowed in glob patterns: {pattern}"
            )

        # Resolve the pattern relative to package root
        search_pattern = package_root / pattern

        # Use glob to find matching files
        matching_files = list(search_pattern.parent.glob(search_pattern.name))

        # Ensure all matched files are within package_root (security check)
        validated_files = []
        for file_path in matching_files:
            try:
                # Resolve to absolute path and check if it's within package_root
                resolved_path = file_path.resolve()
                package_root_resolved = package_root.resolve()

                # Check if the resolved path is within the package root
                if not str(resolved_path).startswith(str(package_root_resolved)):
                    _LOGGER.warning(
                        "Skipping file outside package root: %s", resolved_path
                    )
                    continue

                validated_files.append(resolved_path)
            except (OSError, ValueError) as e:
                _LOGGER.warning("Failed to resolve path %s: %s", file_path, e)
                continue

        # Ensure exactly one file matches
        if len(validated_files) == 0:
            raise StreamlitAPIException(
                f"No files found matching pattern '{pattern}' in package root {package_root}"
            )
        if len(validated_files) > 1:
            file_list = ", ".join(str(f) for f in validated_files)
            raise StreamlitAPIException(
                f"Multiple files found matching pattern '{pattern}': {file_list}. "
                "Exactly one file must match the pattern."
            )

        return Path(validated_files[0])

    @staticmethod
    def ensure_within_root(abs_path: Path, root: Path, *, kind: str) -> None:
        """Ensure that abs_path is within root; raise if not.

        Parameters
        ----------
        abs_path : Path
            Absolute file path
        root : Path
            Root directory path
        kind : str
            Human-readable descriptor for error messages (e.g., "js" or "css")
        """
        try:
            resolved = abs_path.resolve()
            root_resolved = root.resolve()
        except Exception as e:
            raise StreamlitAPIException(
                f"Failed to resolve {kind} path '{abs_path}': {e}"
            ) from e

        if not str(resolved).startswith(str(root_resolved)):
            raise StreamlitAPIException(
                f"{kind} path '{abs_path}' is outside the declared asset_dir '{root}'."
            )

    @staticmethod
    def looks_like_inline_content(value: str) -> bool:
        r"""Heuristic to detect inline JS/CSS content strings.

        Treat a string as a file path ONLY if it looks path-like:
        - Does not contain newlines
        - Contains glob characters (*, ?, [, ])
        - Starts with ./, /, or \
        - Contains a path separator ("/" or "\\")
        - Or ends with a common asset extension like .js, .mjs, .cjs, or .css

        Otherwise, treat it as inline content.
        """
        s = value.strip()
        # If the value contains newlines, it's definitely inline content
        if "\n" in s or "\r" in s:
            return True
        # Glob patterns indicate path-like
        if ComponentPathUtils.has_glob_characters(s):
            return False
        # Obvious path prefixes
        if s.startswith(("./", "/", "\\")):
            return False
        # Any path separator
        if "/" in s or "\\" in s:
            return False

        return not (s.lower().endswith((".js", ".css", ".mjs", ".cjs")))
