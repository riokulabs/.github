#!/usr/bin/env bash
# The checks CI and the pull request template ask for. Run from anywhere in the clone.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
@@test_script|raw@@
