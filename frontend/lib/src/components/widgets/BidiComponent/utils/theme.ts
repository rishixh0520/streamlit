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

import kebabCase from "lodash/kebabCase"

import {
  StreamlitTheme,
  StreamlitThemeCssProperties,
} from "@streamlit/component-v2-lib"

import { EmotionTheme } from "~lib/theme"

/**
 * Converts an object to CSS custom properties
 * with the --st- prefix and kebab-case naming
 */
export const objectToCssCustomProperties = (
  obj: StreamlitTheme,
  prefix = "--st"
): StreamlitThemeCssProperties => {
  const result: Record<string, string> = {}

  Object.entries(obj).forEach(([key, value]) => {
    const kebabKey = kebabCase(key)
    const propertyName = `${prefix}-${kebabKey}`
    result[propertyName] = String(value)
  })

  return result as StreamlitThemeCssProperties
}

/**
 * Extracts only the properties defined in ComponentsV2Theme from the emotion theme
 */
export const extractComponentsV2Theme = (
  theme: EmotionTheme
): StreamlitTheme => {
  const result: StreamlitTheme = {
    primaryColor: theme.colors.primary,
    backgroundColor: theme.colors.bgColor,
    secondaryBackgroundColor: theme.colors.secondaryBg,
    textColor: theme.colors.bodyText,
    font: theme.fonts.sansSerif,
  }

  return result
}
