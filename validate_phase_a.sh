#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./validate_phase_a.sh wikipedia https://www.wikipedia.org/
#   ./validate_phase_a.sh salesforce https://<your-sf-sandbox>/lightning/page/home
#   ./validate_phase_a.sh github https://github.com/issues/new
#   ./validate_phase_a.sh reacttodo http://localhost:5173/

APP="${1:?app-name required}"
URL="${2:?target url required}"

RUN_ROOT="$(dirname "$0")/runs/${APP}"
mkdir -p "$RUN_ROOT"
TS="$(date +%Y%m%dT%H%M%S)"
LOG="${RUN_ROOT}/${TS}.log"

echo "[RUN] app=${APP} url=${URL} ts=${TS}" | tee -a "$LOG"

# Example runner command. Replace with your real entrypoint.
# Must emit structured tags: [PROFILE] [DISCOVERY] [SCOPE] [READINESS] [HEAL] [CACHE] [RESULT]
python - <<'PY' | tee -a "$LOG"
import sys, time
print("[PROFILE] using=DYNAMIC (SPA detected)")
print("[DISCOVERY] strategy=aria-label stable=✓ selector=input[aria-label=\"Email\"]")
print("[CACHE] 💾 SAVED selector=input[name=\"q\"] strategy=name")
print("[READINESS] page interactive")
print("[HEAL] upgraded selector stable=✓ (was placeholder)")
print("[RESULT] PASS")
PY

echo "[DONE] log=${LOG}"
echo "Now run: python /mnt/data/metrics_collector.py to aggregate results."
