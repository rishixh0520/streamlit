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

import { describe, expect, it } from "vitest"

import { StreamlitTheme } from "@streamlit/component-v2-lib"

import { objectToCssCustomProperties } from "~lib/components/widgets/BidiComponent/utils/theme"

describe("BidiComponent/utils/theme", () => {
  describe("objectToCssCustomProperties", () => {
    it("should convert ComponentsV2Theme to CSS custom properties", () => {
      const input: StreamlitTheme = {
        primaryColor: "#ff0000",
        backgroundColor: "#ffffff",
        secondaryBackgroundColor: "#f0f0f0",
        textColor: "#000000",
        font: "Source Sans Pro, sans-serif",
      }

      const result = objectToCssCustomProperties(input)

      expect(result).toEqual({
        "--st-primary-color": "#ff0000",
        "--st-background-color": "#ffffff",
        "--st-secondary-background-color": "#f0f0f0",
        "--st-text-color": "#000000",
        "--st-font": "Source Sans Pro, sans-serif",
      })
    })

    it("should use custom prefix when provided", () => {
      const input: StreamlitTheme = {
        primaryColor: "#00ff00",
        backgroundColor: "#000000",
        secondaryBackgroundColor: "#1e1e1e",
        textColor: "#ffffff",
        font: "Arial, sans-serif",
      }

      const result = objectToCssCustomProperties(input, "--custom")

      expect(result).toEqual({
        "--custom-primary-color": "#00ff00",
        "--custom-background-color": "#000000",
        "--custom-secondary-background-color": "#1e1e1e",
        "--custom-text-color": "#ffffff",
        "--custom-font": "Arial, sans-serif",
      })
    })

    it("should handle kebab-case conversion for property names", () => {
      const input: StreamlitTheme = {
        primaryColor: "#ff0000",
        backgroundColor: "#ffffff",
        secondaryBackgroundColor: "#f0f0f0",
        textColor: "#000000",
        font: "Roboto, sans-serif",
      }

      const result = objectToCssCustomProperties(input)

      // Verify that camelCase properties are converted to kebab-case
      expect(result).toHaveProperty("--st-primary-color")
      expect(result).toHaveProperty("--st-background-color")
      expect(result).toHaveProperty("--st-secondary-background-color")
      expect(result).toHaveProperty("--st-text-color")
    })
  })
})
