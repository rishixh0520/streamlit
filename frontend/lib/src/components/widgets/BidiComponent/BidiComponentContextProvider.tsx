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

import { FC, memo, PropsWithChildren, useCallback, useMemo } from "react"

import type { BidiComponent as BidiComponentProto } from "@streamlit/protobuf"

import { WidgetStateManager } from "~lib/WidgetStateManager"
import {
  BidiComponentContext,
  BidiComponentContextShape,
} from "~lib/components/widgets/BidiComponent/BidiComponentContext"
import { reconstructMixedData } from "~lib/components/widgets/BidiComponent/utils/reconstructMixedData"
import { assertNever } from "~lib/util/assertNever"

export type BidiComponentContextProviderProps = {
  element: BidiComponentProto
  widgetMgr: WidgetStateManager
  fragmentId: string | undefined
}

export const BidiComponentContextProvider: FC<
  PropsWithChildren<BidiComponentContextProviderProps>
> = memo(({ element, children, widgetMgr, fragmentId }) => {
  const {
    arrow,
    bytes,
    componentName,
    cssContent,
    cssSourcePath,
    data,
    htmlContent,
    id,
    jsContent,
    json,
    jsSourcePath,
    mixed,
  } = element

  const getWidgetValue = useCallback(() => {
    const value = widgetMgr.getJsonValue(element)
    return value ? JSON.parse(value) : {}
  }, [element, widgetMgr])

  const parsedData = useMemo(() => {
    switch (data) {
      case "json":
        return json ? JSON.parse(json) : null
      case "arrow":
        return arrow?.data || null
      case "bytes":
        return bytes || null
      // TODO: Fix investigate this:
      // @ts-expect-error I don't know why this is throwing an error, when it should definitely be "mixed"
      case "mixed":
      case "any": {
        if (mixed) {
          const { json: mixedJson, arrowBlobs } = mixed
          if (mixedJson) {
            const jsonData = JSON.parse(mixedJson)

            // Convert protobuf map to plain object
            const arrowBlobsMap: Record<string, Uint8Array> = {}
            if (arrowBlobs) {
              Object.entries(arrowBlobs).forEach(([key, arrowProto]) => {
                if (arrowProto && arrowProto.data) {
                  arrowBlobsMap[key] = arrowProto.data
                }
              })
            }

            return reconstructMixedData(jsonData, arrowBlobsMap)
          }
        }

        // For other unknown data types, try to handle gracefully
        return null
      }
      case undefined:
        return null
      default:
        assertNever(data)
    }

    return undefined
  }, [data, json, arrow, bytes, mixed])

  const contextValue = useMemo<BidiComponentContextShape>(() => {
    return {
      componentName,
      cssContent: cssContent?.trim(),
      cssSourcePath: cssSourcePath || undefined,
      data: parsedData,
      fragmentId,
      getWidgetValue,
      htmlContent: htmlContent?.trim(),
      id,
      jsContent: jsContent || undefined,
      jsSourcePath: jsSourcePath || undefined,
      widgetMgr,
    }
  }, [
    componentName,
    cssContent,
    cssSourcePath,
    fragmentId,
    getWidgetValue,
    htmlContent,
    id,
    jsContent,
    jsSourcePath,
    widgetMgr,
    parsedData,
  ])

  return (
    <BidiComponentContext.Provider value={contextValue}>
      {children}
    </BidiComponentContext.Provider>
  )
})
