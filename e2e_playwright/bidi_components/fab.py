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

from typing import Any

import streamlit as st

# region Component Definition

# Create the FAB component with comprehensive styling and theming
fab = st.components.v2.component(
    "fab",
    css="""
    .fab-container {
        position: fixed;
        bottom: 24px;
        right: 24px;
        z-index: 1000;
        font-family: var(--st-font, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif);
    }

    .fab-button {
        width: 56px;
        height: 56px;
        border-radius: 50%;
        border: none;
        cursor: pointer;
        outline: none;
        position: relative;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 24px;
        font-weight: 500;

        /* Use Streamlit theme colors */
        background-color: var(--st-primary-color, #ff6b6b);
        color: var(--st-background-color, #ffffff);

        /* Beautiful shadows */
        box-shadow:
            0 3px 5px -1px rgba(0, 0, 0, 0.2),
            0 6px 10px 0 rgba(0, 0, 0, 0.14),
            0 1px 18px 0 rgba(0, 0, 0, 0.12);

        /* Smooth transitions */
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        transform: scale(1);
    }

    .fab-button:hover:not(:disabled) {
        transform: scale(1.1);
        box-shadow:
            0 5px 5px -3px rgba(0, 0, 0, 0.2),
            0 8px 10px 1px rgba(0, 0, 0, 0.14),
            0 3px 14px 2px rgba(0, 0, 0, 0.12);
    }

    .fab-button:active:not(:disabled) {
        transform: scale(1.05);
        transition-duration: 0.1s;
    }

    .fab-button:disabled {
        background-color: var(--st-secondary-background-color, #f0f2f6);
        color: var(--st-text-color, #262730);
        opacity: 0.6;
        cursor: not-allowed;
        box-shadow:
            0 2px 1px -1px rgba(0, 0, 0, 0.1),
            0 1px 1px 0 rgba(0, 0, 0, 0.07),
            0 1px 3px 0 rgba(0, 0, 0, 0.06);
    }

    /* Ripple effect for click feedback */
    .fab-button::before {
        content: '';
        position: absolute;
        top: 50%;
        left: 50%;
        width: 0;
        height: 0;
        border-radius: 50%;
        background-color: rgba(255, 255, 255, 0.3);
        transform: translate(-50%, -50%);
        transition: width 0.6s, height 0.6s;
        pointer-events: none;
    }

    .fab-button.clicked::before {
        width: 80px;
        height: 80px;
    }

    /* Icon styling */
    .fab-icon {
        display: inline-block;
        line-height: 1;
        transition: transform 0.2s ease;
    }

    .fab-button:hover:not(:disabled) .fab-icon {
        transform: rotate(45deg);
    }

    /* Tooltip */
    .fab-tooltip {
        position: absolute;
        right: 100%;
        top: 50%;
        transform: translateY(-50%);
        background-color: var(--st-secondary-background-color, #f0f2f6);
        color: var(--st-text-color, #262730);
        padding: 8px 12px;
        border-radius: 4px;
        font-size: 14px;
        white-space: nowrap;
        margin-right: 12px;
        opacity: 0;
        visibility: hidden;
        transition: all 0.3s ease;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        z-index: 1001;
    }

    .fab-tooltip::after {
        content: '';
        position: absolute;
        top: 50%;
        left: 100%;
        margin-top: -5px;
        border: 5px solid transparent;
        border-left-color: var(--st-secondary-background-color, #f0f2f6);
    }

    .fab-container:hover .fab-tooltip {
        opacity: 1;
        visibility: visible;
    }

    /* Accessibility focus ring */
    .fab-button:focus-visible {
        outline: 2px solid var(--st-primary-color, #ff6b6b);
        outline-offset: 2px;
    }

    /* Animation for showing/hiding */
    .fab-container.hidden {
        transform: scale(0);
        opacity: 0;
    }

    .fab-container.visible {
        transform: scale(1);
        opacity: 1;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    """,
    html="""
    <div class="fab-container visible">
        <div class="fab-tooltip st-fab-tooltip-element">Add new item</div>
        <button class="fab-button st-fab-button-element" aria-label="Add new item">
            <span class="fab-icon">+</span>
        </button>
    </div>
    """,
    js="""
    export default function(component) {
        const { setTriggerValue, setStateValue, parentElement, data } = component;

        const container = parentElement.querySelector('.fab-container');

        const tooltip = container.querySelector('.st-fab-tooltip-element');
        const button = container.querySelector('.st-fab-button-element');

        // Store timeout ID for cleanup
        let rippleTimeoutId = null;

        // Handle data from Python
        const {
            disabled = false,
            icon = '+',
            tooltip_text = 'Add new item',
            hidden = false
        } = data;

        // Apply initial state
        button.disabled = disabled;
        button.querySelector('.fab-icon').textContent = icon;
        tooltip.textContent = tooltip_text;
        button.setAttribute('aria-label', tooltip_text);

        if (hidden) {
            container.classList.remove('visible');
            container.classList.add('hidden');
        } else {
            container.classList.remove('hidden');
            container.classList.add('visible');
        }

        const handleClick = () => {
            if (!button.disabled) {
                // Add ripple effect
                button.classList.add('clicked');
                rippleTimeoutId = setTimeout(() => {
                    button.classList.remove('clicked');
                    rippleTimeoutId = null;
                }, 600);

                setTriggerValue('clicked', true);

                // Provide haptic feedback if available
                if (navigator.vibrate) {
                    navigator.vibrate(50);
                }
            }
        };

        // Keyboard accessibility
        const handleKeyDown = (event) => {
            if ((event.key === 'Enter' || event.key === ' ') && !button.disabled) {
                event.preventDefault();
                handleClick();
            }
        };

        button.addEventListener('click', handleClick);
        button.addEventListener('keydown', handleKeyDown);

        // Cleanup function
        return () => {
            button.removeEventListener('click', handleClick);
            button.removeEventListener('keydown', handleKeyDown);

            // Cancel pending timeout if it exists
            if (rippleTimeoutId !== null) {
                clearTimeout(rippleTimeoutId);
                rippleTimeoutId = null;
            }
        };
    }
    """,
)


def fab_button(
    *,
    key: str | None = None,
    disabled: bool = False,
    icon: str = "+",
    tooltip_text: str = "Add new item",
    hidden: bool = False,
    on_click: Any | None = None,
) -> Any:
    """
    A Floating Action Button with Streamlit theming.

    Parameters
    ----------
    key : str or None
        An optional string to use as the unique key for the widget.
    disabled : bool
        Whether the button is disabled. Default is False.
    icon : str
        The icon character or text to display. Default is "+".
    tooltip_text : str
        The text to show in the tooltip. Default is "Add new item".
    hidden : bool
        Whether to hide the button. Default is False.
    on_click : callable or None
        Callback function to execute when button is clicked.

    Returns
    -------
    BidiComponentResult
        Component result with clicked trigger.
    """
    return fab(
        key=key,
        data={
            "disabled": disabled,
            "icon": icon,
            "tooltip_text": tooltip_text,
            "hidden": hidden,
        },
        on_clicked_change=on_click,
    )


# endregion

# region Demo
st.header("FAB Button with CCv2")

# Demo usage
st.subheader("Demo Controls")

col1, col2 = st.columns(2)

with col1:
    disabled = st.checkbox("Disabled", value=False)
    hidden = st.checkbox("Hidden", value=False)

with col2:
    icon = st.text_input("Icon", value="+", max_chars=3)
    tooltip_text = st.text_input("Tooltip Text", value="Add new item")

# Track clicks
if "fab_clicks" not in st.session_state:
    st.session_state.fab_clicks = 0


def handle_fab_click():
    st.session_state.fab_clicks += 1


# Create the FAB button
result = fab_button(
    key="demo_fab",
    disabled=disabled,
    icon=icon,
    tooltip_text=tooltip_text,
    hidden=hidden,
    on_click=handle_fab_click,
)

# Display results
st.write(f"**Component Result:** {result}")
st.write(f"**Total FAB clicks this session:** {st.session_state.fab_clicks}")

if result.clicked:
    st.info("FAB was just clicked!")

# endregion
