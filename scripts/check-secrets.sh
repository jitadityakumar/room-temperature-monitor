#!/bin/bash
if git diff --cached --name-only | grep -E '(^|/)\.env[^/]*$' | grep -qv '\.example$'; then
  echo "ERROR: env file with credentials staged for commit. Remove it before committing."
  exit 1
fi
