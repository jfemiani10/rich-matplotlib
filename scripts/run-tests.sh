#!/usr/bin/env bash
# Run the test suite from whatever environment is available.
#
# Git hooks are not always launched from an activated shell -- VS Code's Source
# Control panel, JetBrains, and most GUI clients spawn git from the environment the
# editor itself started in, which usually has no virtualenv on PATH. Looking for the
# project venv explicitly makes the hook behave the same everywhere.
set -euo pipefail

# Hooks run with the working directory set to the repository root.
if [ -x .venv/bin/pytest ]; then
    exec .venv/bin/pytest "$@"
fi

# Fall back to whatever python is on PATH (CI, a differently named venv, conda).
exec python -m pytest "$@"
