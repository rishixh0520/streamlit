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

import inspect
import logging
import os
from pathlib import Path

# Used at runtime for caller inspection - must be imported outside TYPE_CHECKING.
from typing import TYPE_CHECKING, Any, Callable

from streamlit.components.v2.component_path_utils import ComponentPathUtils
from streamlit.components.v2.component_registry import BidiComponentDefinition
from streamlit.components.v2.get_bidi_component_manager import (
    get_bidi_component_manager,
)
from streamlit.errors import StreamlitAPIException

if TYPE_CHECKING:
    from types import FrameType

    from streamlit.components.v2.bidi_component import BidiComponentResult
    from streamlit.elements.lib.layout_utils import Height, Width
    from streamlit.runtime.state.common import WidgetCallback


_LOGGER = logging.getLogger(__name__)


def _register_component(
    name: str,
    html: str | None = None,
    css: str | None = None,
    js: str | None = None,
) -> str:
    """Register a component and return its fully qualified key.

    This shared function handles the component registration including frame
    inspection, key generation, and handling pre-registered components from
    ``pyproject.toml``.

    Parameters
    ----------
    name : str
        A short, descriptive identifier for the component.
    html : str or None
        Inline HTML markup for the component root.
    css : str | None
        Either inline CSS (string) or a string path/glob to a ``.css`` file.
        When a path-like string is provided, the file MUST reside inside the
        manifest-declared ``asset_dir`` for this component (configured in the
        package's ``pyproject.toml``). Relative paths are resolved against the
        caller's file location. Globs are allowed and must resolve to exactly one
        file within ``asset_dir``. Attempts to reference files outside ``asset_dir``
        (including traversal) will raise ``StreamlitAPIException``.
    js : str | None
        Either inline JavaScript (string) or a string path/glob to a ``.js`` file,
        validated with the same rules as ``css``.

    Returns
    -------
    str
        The fully qualified component key in the form ``<module_name>.<n>``.
    """
    # Parameter type guards: only strings or None are supported for js/css
    for _param_name, _param_value in (("css", css), ("js", js)):
        if _param_value is not None and not isinstance(_param_value, str):
            raise StreamlitAPIException(
                f"{_param_name} must be a string or None. Pass a string path or glob."
            )

    # Inspect the *call-site* to derive the caller's module and build a fully
    # qualified component key in the form ``<module_name>.<n>``. This mirrors
    # the behavior of Components V1 and prevents cross-module name collisions.

    current_frame: FrameType | None = inspect.currentframe()
    if current_frame is None:
        raise RuntimeError("Unable to inspect current frame for component declaration.")

    # Go up two frames: current -> component -> user code
    caller_frame = current_frame.f_back
    if caller_frame is None:
        raise RuntimeError(
            "Unable to determine caller frame for component declaration."
        )

    user_caller_frame = caller_frame.f_back
    if user_caller_frame is None:
        raise RuntimeError(
            "Unable to determine user caller frame for component declaration."
        )

    component_key = name

    registry = get_bidi_component_manager()
    # Check if component was pre-registered from pyproject.toml
    existing_def = registry.get(component_key)

    if existing_def:
        # Component exists from pyproject.toml - allow runtime override. Any
        # provided field (including html) indicates an override operation.
        if html is not None or css is not None or js is not None:
            # Create a new definition using exactly the provided values. Fields
            # omitted by the caller are cleared (set to None) so properties can
            # be removed via subsequent registrations.
            # Determine the caller directory to resolve relative paths
            caller_dir = os.path.dirname(inspect.getfile(user_caller_frame))
            new_def = _build_definition_with_validation(
                manager=registry,
                component_key=component_key,
                caller_dir=caller_dir,
                html=html,
                css=css,
                js=js,
            )
            registry.register(new_def)
            _LOGGER.debug(
                "Runtime override for pre-registered component %s", component_key
            )
    else:
        # Normal registration for non-manifest components
        caller_dir = os.path.dirname(inspect.getfile(user_caller_frame))
        registry.register(
            _build_definition_with_validation(
                manager=registry,
                component_key=component_key,
                caller_dir=caller_dir,
                html=html,
                css=css,
                js=js,
            )
        )

    return component_key


def _build_definition_with_validation(
    *,
    manager: Any,
    component_key: str,
    caller_dir: str,
    html: str | None,
    css: str | None,
    js: str | None,
) -> BidiComponentDefinition:
    """Construct definition and validate js/css inputs against ``asset_dir``.

    Behavior
    --------
    - Inline strings are treated as content (no manifest required).
    - Path-like strings require the component to be declared in the package
      manifest with an ``asset_dir``.
    - Globs are supported only within ``asset_dir`` and must resolve to exactly one
      file; otherwise an exception is raised.
    - Relative paths are resolved against the user's calling file and must end up
      within ``asset_dir`` after resolution; traversal outside will raise.
    - For file-backed entries, the URL sent to the frontend is the path relative to
      ``asset_dir`` so the server can serve it under
      ``/bidi-components/<component>/<relative_path>``.
    """
    asset_root = manager.manifest_handler.get_asset_root(component_key)
    # Fallback: use manager.get_component_path which prefers manifest asset_dir
    if asset_root is None:
        try:
            maybe_path = manager.get_component_path(component_key)
        except Exception:
            maybe_path = None
        if maybe_path:
            asset_root = Path(maybe_path)

    def _resolve_entry(
        value: str | None, *, kind: str
    ) -> tuple[str | None, str | None]:
        # Inline content: None rel URL
        if value is None:
            return None, None
        if ComponentPathUtils.looks_like_inline_content(value):
            return value, None

        # For path-like strings, asset_root must exist
        if asset_root is None:
            raise StreamlitAPIException(
                f"Component '{component_key}' must be declared in pyproject.toml with asset_dir "
                f"to use file-backed {kind}."
            )

        value_str = value

        # If looks like a glob, resolve strictly inside asset_root
        if ComponentPathUtils.has_glob_characters(value_str):
            resolved = ComponentPathUtils.resolve_glob_pattern(value_str, asset_root)
            ComponentPathUtils.ensure_within_root(resolved, asset_root, kind=kind)
            rel_url = str(resolved.relative_to(asset_root).as_posix())
            return str(resolved), rel_url

        # Concrete path: resolve relative to caller for non-absolute string/Path
        p = Path(value_str)
        candidate = p if p.is_absolute() else (Path(caller_dir) / p)

        # Normalize and ensure it's within asset_root
        ComponentPathUtils.ensure_within_root(candidate, asset_root, kind=kind)
        resolved_candidate = candidate.resolve()
        rel_url = str(resolved_candidate.relative_to(asset_root.resolve()).as_posix())
        return str(resolved_candidate), rel_url

    css_value, css_rel = _resolve_entry(css, kind="css")
    js_value, js_rel = _resolve_entry(js, kind="js")

    # Build definition with possible asset_dir-relative paths
    return BidiComponentDefinition(
        name=component_key,
        html=html,
        css=css_value,
        js=js_value,
        css_asset_relative_path=css_rel,
        js_asset_relative_path=js_rel,
    )


def _create_component_callable(
    name: str,
    *,
    html: str | None = None,
    css: str | None = None,
    js: str | None = None,
) -> Callable[..., Any]:
    """Create a component callable, handling both lookup and registration cases.

    Parameters
    ----------
    name : str
        A short, descriptive identifier for the component.
    html : str | None
        Inline HTML markup for the component root.
    css : str | None
        Inline CSS (string) or a string path/glob to a file under ``asset_dir``;
        see :func:`_register_component` for path validation semantics.
    js : str | None
        Inline JavaScript (string) or a string path/glob to a file under
        ``asset_dir``; see :func:`_register_component` for path validation semantics.

    Returns
    -------
    Callable[..., Any]
        A function that, when called inside a Streamlit script, mounts the
        component and returns its state.
    """
    # Check if this is a lookup for a pre-registered component from `pyproject.toml`.
    if html is None and css is None and js is None:
        # Look up component in registry by fully qualified name
        current_frame: FrameType | None = inspect.currentframe()
        if current_frame is None:
            raise RuntimeError("Unable to inspect current frame for component lookup.")

        caller_frame = current_frame.f_back
        if caller_frame is None:
            raise RuntimeError("Unable to determine caller frame for component lookup.")

        component_key = name

        registry = get_bidi_component_manager()
        existing_component = registry.get(component_key)
        if existing_component is not None:
            # Component is pre-registered, return callable without re-registration
            def _mount_pre_registered_component(
                *,
                key: str | None = None,
                data: Any | None = None,
                default: dict[str, Any] | None = None,
                width: Width = "stretch",
                height: Height = "content",
                isolate_styles: bool = True,
                **on_callbacks: WidgetCallback | None,
            ) -> Any:
                import streamlit as st

                return st.bidi_component(
                    component_key,
                    key=key,
                    data=data,
                    default=default,
                    width=width,
                    height=height,
                    isolate_styles=isolate_styles,
                    **on_callbacks,
                )

            return _mount_pre_registered_component
        # Component not found in registry
        raise StreamlitAPIException(
            f"Component '{name}' is not registered. "
            f"To use pre-registered components, ensure the component is defined in "
            f"your pyproject.toml file. To register a component at runtime, provide "
            f"html, css, or js parameters. Component key: {component_key}"
        )

    # Original registration logic for components with assets
    component_key = _register_component(name=name, html=html, css=css, js=js)

    # The inner callable that mounts the component.
    def _mount_component(
        *,
        key: str | None = None,
        data: Any | None = None,
        default: dict[str, Any] | None = None,
        width: Width = "stretch",
        height: Height = "content",
        isolate_styles: bool = True,
        **on_callbacks: WidgetCallback | None,
    ) -> Any:
        """
        Parameters
        ----------
        key : str or None
            An optional string to use as the unique key for the component.
        data : Any or None
            Data to pass to the component (JSON-serializable).
        default : dict[str, Any] or None
            A dictionary of default values for state properties. Keys must
            correspond to valid state names (those with on_*_change callbacks).
        width : Width
            The width of the component.
        height : Height
            The height of the component.
        isolate_styles : bool
            Whether to sandbox the component styles in a shadow-root. Defaults to
            True.
        **on_callbacks : WidgetCallback
            Callback functions for handling component events. Use pattern
            on_{state_name}_change (e.g., on_click_change, on_value_change).

        Returns
        -------
        BidiComponentResult
            Component state.
        """
        import streamlit as st

        return st.bidi_component(
            component_key,
            key=key,
            data=data,
            default=default,
            width=width,
            height=height,
            isolate_styles=isolate_styles,
            **on_callbacks,
        )

    return _mount_component


def component(
    name: str,
    *,
    html: str | None = None,
    css: str | None = None,
    js: str | None = None,
) -> Callable[
    ...,  # positional args prohibited; enforce keyword-only at call-time
    BidiComponentResult,
]:
    """Register a bidirectional component and return a callable to mount it.

    Parameters
    ----------
    name : str
        A short, descriptive identifier for the component.
    html : str | None
        Inline HTML markup for the component root.
    css : str | None
        Inline CSS (string) or a string path/glob to a ``.css`` file under
        the component's manifest-declared ``asset_dir``. Relative paths are
        resolved against the caller file; globs must match exactly one file.
        Attempts to reference files outside ``asset_dir`` will raise.
    js : str | None
        Inline JavaScript (string) or a string path/glob to a ``.js`` file
        under ``asset_dir`` with the same validation rules as ``css``.

    Returns
    -------
    Callable[..., BidiComponentResult]
        A function that, when called inside a Streamlit script, mounts the
        component and returns its state as a ``BidiComponentResult``.
    """
    return _create_component_callable(name, html=html, css=css, js=js)


__all__ = [
    "component",
]
