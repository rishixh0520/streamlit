/**
 * Copyright (c) Streamlit Inc. (2018-2022) Snowflake Inc. (2022-2025)
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

/**
 * The base type of the returned state from a Streamlit v2 Component. Authors
 * can extend this type to add their own state key/value pairs, or utilize their
 * own type by providing it as the first generic parameter to `ComponentArgs`.
 *
 * @see BidiComponentState in lib/streamlit/components/v2/bidi_component.py
 */

/* Re-export Apache Arrow types so that component authors can use them. This
also allows us to keep our versions in sync. */
export type { Table } from "apache-arrow"

export type ComponentState = Record<string, unknown>

export type ArrowData = Uint8Array<ArrayBufferLike> | null

/**
 * The arguments passed to a Streamlit v2 Component's top-level
 * `export default` function.
 */
export type ComponentArgs<
  TComponentState extends ComponentState = ComponentState,
  /**
   * The shape of the data passed to the component.
   * Users should provide this type for type safety.
   *
   * @see st.bidi_component in lib/streamlit/components/v2/__init__.py
   */
  TDataShape = unknown,
> = {
  data: TDataShape
  key: string
  name: string
  parentElement: HTMLElement | ShadowRoot
  setStateValue: (
    name: keyof TComponentState,
    value: TComponentState[keyof TComponentState]
  ) => void
  setTriggerValue: (
    name: keyof TComponentState,
    value: TComponentState[keyof TComponentState]
  ) => void
}

export type ComponentResult =
  | (() => void)
  | void
  // TODO: Technically, a Promise is undefined behavior, but we'll allow it
  // for now.
  | Promise<() => void>
  | Promise<void>

/**
 * The Streamlit v2 Component signature.
 */
export type Component<
  TComponentState extends ComponentState = ComponentState,
  TDataShape = unknown,
> = (
  componentArgs: ComponentArgs<TComponentState, TDataShape>
) => ComponentResult
