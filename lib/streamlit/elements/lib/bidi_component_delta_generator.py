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

from typing import TYPE_CHECKING, Any, cast

from typing_extensions import Self

from streamlit.delta_generator import DeltaGenerator
from streamlit.errors import StreamlitAPIException
from streamlit.runtime.scriptrunner_utils.script_run_context import get_script_run_ctx

if TYPE_CHECKING:
    from streamlit.cursor import Cursor
    from streamlit.proto.BidiComponent_pb2 import BidiComponent as BidiComponentProto


class BidiComponentDeltaGenerator(DeltaGenerator):
    """A DeltaGenerator subclass that provides state access for bidirectional components."""

    @staticmethod
    def _validate_state_names(state_names: set[str]) -> None:
        """Validate that component state names don't conflict with DeltaGenerator attributes.

        Parameters
        ----------
        state_names : set[str]
            Set of state names to validate

        Raises
        ------
        StreamlitAPIException
            If any state name conflicts with a DeltaGenerator attribute or method
        """
        conflicting_names = []

        # Check against all attributes in the DeltaGenerator class hierarchy
        for attr_name in state_names:
            if hasattr(DeltaGenerator, attr_name):
                conflicting_names = [
                    attr_name
                    for attr_name in state_names
                    if hasattr(DeltaGenerator, attr_name)
                ]

        if conflicting_names:
            conflict_list = ", ".join(f'"{name}"' for name in sorted(conflicting_names))
            raise StreamlitAPIException(
                f"Component state names cannot conflict with DeltaGenerator methods/attributes. "
                f"The following state names are reserved: {conflict_list}. "
                f"Please use different names for your component state."
            )

    @staticmethod
    def _create(
        parent: DeltaGenerator,
        component_name: str,
        component_instance_id: str,
        proto: BidiComponentProto,
        callbacks_by_event: dict[str, Any] | None = None,
        default: dict[str, Any] | None = None,
    ) -> BidiComponentDeltaGenerator:
        """Factory method following the pattern of Dialog and StatusContainer."""
        # Validate state names before creating the component
        all_state_names = set()
        if default:
            all_state_names.update(default.keys())
        if callbacks_by_event:
            all_state_names.update(callbacks_by_event.keys())

        if all_state_names:
            BidiComponentDeltaGenerator._validate_state_names(all_state_names)

        # Create a basic block proto for the DeltaGenerator
        from streamlit.proto.Block_pb2 import Block as BlockProto

        block_proto = BlockProto()
        block_proto.allow_empty = True

        bidi_dg = cast(
            "BidiComponentDeltaGenerator",
            parent._block(block_proto=block_proto, dg_type=BidiComponentDeltaGenerator),
        )

        # Initialize component-specific attributes
        bidi_dg._component_name = component_name
        bidi_dg._component_instance_id = component_instance_id
        bidi_dg._proto = proto
        bidi_dg._callbacks_by_event = callbacks_by_event or {}
        bidi_dg._default = default or {}

        return bidi_dg

    def __init__(
        self,
        root_container: int | None,
        cursor: Cursor | None,
        parent: DeltaGenerator | None,
        block_type: str | None,
    ) -> None:
        super().__init__(root_container, cursor, parent, block_type)

        # Initialized in `_create()`:
        self._component_name: str | None = None
        self._component_instance_id: str | None = None
        self._proto: BidiComponentProto | None = None
        self._callbacks_by_event: dict[str, Any] = {}
        self._default: dict[str, Any] = {}

        # Cached state values
        self._state_cache: dict[str, Any] = {}
        self._trigger_cache: dict[str, Any] = {}

    def _refresh_state(self) -> None:
        """Refresh the cached state from the widget state store."""
        if self._component_instance_id is None:
            return

        # Get current session state
        script_run_ctx = get_script_run_ctx()
        if script_run_ctx is None:
            # No session state available (e.g., during testing)
            self._state_cache = {}
            self._trigger_cache = {}
            return

        session_state = script_run_ctx.session_state

        # Get component state
        try:
            if self._component_instance_id in session_state:
                component_state = session_state[self._component_instance_id]
                # Component state is expected to be wrapped in {"value": {...}}
                if isinstance(component_state, dict) and "value" in component_state:
                    new_state_cache = component_state["value"]
                    if isinstance(new_state_cache, dict):
                        # Validate any new state names from JavaScript
                        new_state_names = set(new_state_cache.keys()) - set(
                            self._state_cache.keys()
                        )
                        if new_state_names:
                            self._validate_state_names(new_state_names)
                        self._state_cache = new_state_cache
                    else:
                        self._state_cache = {}
                else:
                    self._state_cache = {}
            else:
                self._state_cache = {}
        except KeyError:
            self._state_cache = {}

        # Get trigger values using known callback names
        from streamlit.components.v2.bidi_component import make_trigger_id

        self._trigger_cache = {}
        for event_name in self._callbacks_by_event:
            trigger_id = make_trigger_id(self._component_instance_id, event_name)
            try:
                trigger_value = session_state[trigger_id]
                if trigger_value is not None:
                    self._trigger_cache[event_name] = trigger_value
            except KeyError:
                # No trigger value for this event, which is normal
                pass

    def __getattr__(self, name: str) -> Any:
        """Access component state values as attributes."""
        # Refresh state and check if it's a state value
        self._refresh_state()

        # Trigger values take precedence over state values
        if name in self._trigger_cache:
            return self._trigger_cache[name]
        if name in self._state_cache:
            return self._state_cache[name]
        # Check for default state values
        if name in self._default:
            return self._default[name]

        # Check if this is a DeltaGenerator method/attribute
        if hasattr(DeltaGenerator, name):
            # This is a DeltaGenerator method/attribute, delegate to parent
            return super().__getattr__(name)

        # Not found in component state and not a DeltaGenerator attribute, return None
        return None

    def __getitem__(self, key: str) -> Any:
        """Dictionary-style access for component state."""
        self._refresh_state()

        # Trigger values take precedence
        if key in self._trigger_cache:
            return self._trigger_cache[key]
        if key in self._state_cache:
            return self._state_cache[key]
        if key in self._default:
            return self._default[key]
        raise KeyError(f"State key '{key}' not found")

    def __contains__(self, key: str) -> bool:
        """Check if a state key exists."""
        self._refresh_state()
        return (
            key in self._state_cache
            or key in self._trigger_cache
            or key in self._default
        )

    def get(self, key: str, default: Any = None) -> Any:
        """Get state value with optional default."""
        self._refresh_state()

        if key in self._trigger_cache:
            return self._trigger_cache[key]
        if key in self._state_cache:
            return self._state_cache[key]
        if key in self._default:
            return self._default[key]
        return default

    def __enter__(self) -> Self:
        """Support usage as a context manager."""
        super().__enter__()
        return self
