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
 * Utility type to convert camelCase to kebab-case
 */
type CamelToKebab<S extends string> = S extends `${infer T}${infer U}`
  ? `${T extends Capitalize<T> ? "-" : ""}${Lowercase<T>}${CamelToKebab<U>}`
  : S

/**
 * Utility type to convert an object type to CSS custom properties
 * with a specified prefix and kebab-case naming
 */
type ObjectToCssCustomProperties<
  T extends object,
  Prefix extends string = "--st",
> = {
  [K in keyof T as `${Prefix}-${CamelToKebab<string & K>}`]: string
}

/**
 * The Streamlit theme properties that are exposed to the component.
 */
export interface StreamlitTheme {
  primaryColor: string
  backgroundColor: string
  secondaryBackgroundColor: string
  textColor: string
  font: string
}

/**
 * Derived type that statically types the CSS Custom Properties from the
 * StreamlitTheme.
 */
export type StreamlitThemeCssProperties =
  ObjectToCssCustomProperties<StreamlitTheme>
