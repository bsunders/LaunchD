#!/usr/bin/env bash
# Turn the hero boolean flag on or off via LaunchDarkly REST API (Part 1 remediation).
#
# Uses LaunchDarkly's recommended semantic patch (turnFlagOn / turnFlagOff), not raw JSON Patch,
# so the request stays valid as LD's flag JSON shape evolves.
#
# You only pass: on | off (release vs rollback).
#
# Prerequisites:
#   1) API access token: LaunchDarkly → Account settings → Authorization (Writer+). Not sdk-…
#   2) Project / environment keys from the flag URL:
#      …/app.launchdarkly.com/<PROJECT_KEY>/<ENVIRONMENT_KEY>/features/<FLAG_KEY>
#
# Usage:
#   export LD_API_TOKEN='api-…'
#   export LD_PROJECT_KEY=my-project        # default: default
#   export LD_ENVIRONMENT_KEY=test          # must match LAUNCHDARKLY_SDK_KEY's environment
#   export LD_FLAG_KEY=hero-component-v2
#   ./remediate.sh on
#   ./remediate.sh off

set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

STATE="${1:-}"
if [[ "$STATE" != "on" && "$STATE" != "off" ]]; then
  echo "Usage: $0 on|off" >&2
  echo "  on  — set the flag to served (new hero) for that environment" >&2
  echo "  off — turn the flag off (remediate / old hero)" >&2
  exit 1
fi

if [[ -z "${LD_API_TOKEN:-}" ]]; then
  echo "error: LD_API_TOKEN is not set." >&2
  echo "Create an API access token (not the SDK key) and run: export LD_API_TOKEN='…'" >&2
  exit 1
fi

PROJECT="${LD_PROJECT_KEY:-default}"
ENVKEY="${LD_ENVIRONMENT_KEY:-test}"
FLAG="${LD_FLAG_KEY:-hero-component-v2}"

# Semantic patch instructions (see LD API: PATCH /flags/{project}/{flag}, semantic patch).
case "$STATE" in
  on)  KIND="turnFlagOn" ;;
  off) KIND="turnFlagOff" ;;
esac

# JSON body: environmentKey + instructions — avoids brittle JSON-Patch paths on the flag document.
BODY=$(printf '{"environmentKey":"%s","instructions":[{"kind":"%s"}]}' "$ENVKEY" "$KIND")

URL="https://app.launchdarkly.com/api/v2/flags/${PROJECT}/${FLAG}"
CT="application/json; domain-model=launchdarkly.semanticpatch"

TMP="$(mktemp)"
HTTP_CODE="$(curl -sS -o "$TMP" -w "%{http_code}" -X PATCH "$URL" \
  -H "Authorization: ${LD_API_TOKEN}" \
  -H "Content-Type: ${CT}" \
  -d "$BODY")"

cat "$TMP"
echo ""
rm -f "$TMP"

if [[ "$HTTP_CODE" -lt 200 || "$HTTP_CODE" -ge 300 ]]; then
  echo "---" >&2
  echo "HTTP ${HTTP_CODE}. Common fixes:" >&2
  echo "  • LD_PROJECT_KEY — open your flag in LD; first path segment after launchdarkly.com is the project key." >&2
  echo "  • LD_ENVIRONMENT_KEY — second segment; must match the environment your LAUNCHDARKLY_SDK_KEY belongs to." >&2
  echo "  • LD_FLAG_KEY — must match FEATURE_FLAG_KEY and the flag key in LaunchDarkly." >&2
  echo "  • Token must be a REST API access token with Writer (or higher), not sdk-… or client-side keys." >&2
  exit 1
fi
