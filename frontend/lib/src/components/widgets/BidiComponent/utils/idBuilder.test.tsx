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

import { STREAMLIT_INTERNAL_KEY_PREFIX } from "~lib/components/widgets/BidiComponent/constants"
import { makeTriggerId } from "~lib/components/widgets/BidiComponent/utils/idBuilder"

describe("makeTriggerId", () => {
  it("creates trigger IDs with internal prefix to hide them from session state", () => {
    expect(makeTriggerId("myComponent", "click")).toBe(
      `${STREAMLIT_INTERNAL_KEY_PREFIX}_myComponent__click`
    )
    expect(makeTriggerId("myComponent", "change")).toBe(
      `${STREAMLIT_INTERNAL_KEY_PREFIX}_myComponent__change`
    )
    expect(makeTriggerId("myComponent", "input")).toBe(
      `${STREAMLIT_INTERNAL_KEY_PREFIX}_myComponent__input`
    )
    expect(makeTriggerId("myComponent", "submit")).toBe(
      `${STREAMLIT_INTERNAL_KEY_PREFIX}_myComponent__submit`
    )
    expect(makeTriggerId("myComponent", "reset")).toBe(
      `${STREAMLIT_INTERNAL_KEY_PREFIX}_myComponent__reset`
    )
    expect(makeTriggerId("myComponent", "blur")).toBe(
      `${STREAMLIT_INTERNAL_KEY_PREFIX}_myComponent__blur`
    )
    expect(makeTriggerId("myComponent", "focus")).toBe(
      `${STREAMLIT_INTERNAL_KEY_PREFIX}_myComponent__focus`
    )
  })

  it("concatenates base and event with the expected format", () => {
    const triggerIds = [
      makeTriggerId("component123", "click"),
      makeTriggerId("anotherComponent", "hover"),
    ]

    triggerIds.forEach(triggerId => {
      // Should start with internal prefix
      expect(triggerId).toMatch(new RegExp(`^\\$\\$STREAMLIT_INTERNAL_KEY_`))
      // Should contain the delimiter
      expect(triggerId).toMatch(/__/)
      // Should be structured as prefix_base__event
      expect(triggerId).toMatch(
        new RegExp(`^\\$\\$STREAMLIT_INTERNAL_KEY_[^_]+__[^_]+$`)
      )
    })
  })

  it("throws when base or event contains the delimiter", () => {
    expect(() => makeTriggerId("bad__base", "click")).toThrow()
    expect(() => makeTriggerId("base", "bad__event")).toThrow()
  })
})
