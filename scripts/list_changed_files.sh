#!/usr/bin/env bash

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

set -euo pipefail

# Determine repo root for absolute path output
repo_root=$(git rev-parse --show-toplevel)

# Prefer PR base in CI via GITHUB_BASE_REF; default to develop locally
base_remote="${GITHUB_BASE_REF:-develop}"

# Best-effort fetch of the base ref
git fetch origin "$base_remote" --depth=1 >/dev/null 2>&1 || true

# Compute merge-base with HEAD if available, else fall back to none
base_commit=$(git merge-base "origin/$base_remote" HEAD 2>/dev/null || true)

# Build union of: committed vs base, staged, unstaged, and untracked
changed_files=$(
  {
    if [ -n "${base_commit:-}" ]; then
      git diff --name-only "$base_commit"...HEAD
    fi
    git diff --name-only --cached
    git diff --name-only
    git ls-files --others --exclude-standard
  } | sort -u | sed "s#^#$repo_root/#"
)

# Print absolute paths (one per line)
printf "%s\n" "$changed_files"
