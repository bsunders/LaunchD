#!/usr/bin/env bash
# Shortcut: remediate / roll back to the old hero (same as ./remediate.sh off).
exec "$(dirname "$0")/remediate.sh" off
