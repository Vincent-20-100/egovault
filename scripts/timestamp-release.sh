#!/bin/bash
# scripts/timestamp-release.sh — timestamp a version tag via OpenTimestamps
# Usage: bash scripts/timestamp-release.sh v0.3.0

set -e
command -v ots >/dev/null 2>&1 || { echo "ERROR: ots not installed (pip install opentimestamps-client)"; exit 1; }

TAG="${1:?Usage: $0 <tag>}"

# Verify tag exists
git rev-parse "$TAG" >/dev/null 2>&1 || { echo "ERROR: tag $TAG does not exist"; exit 1; }

# Only allow v0.X.0 tags
[[ "$TAG" =~ ^v[0-9]+\.[0-9]+\.0$ ]] || { echo "ERROR: only v0.X.0 tags are timestamped"; exit 1; }

TIMESTAMP_DIR=".timestamps"
mkdir -p "$TIMESTAMP_DIR"

COMMIT_HASH=$(git rev-parse "$TAG")
OTS_FILE="$TIMESTAMP_DIR/$TAG.ots"
HASH_FILE="$TIMESTAMP_DIR/$TAG.hash"

[ -f "$OTS_FILE" ] && { echo "$TAG already timestamped"; exit 0; }

# ots stamp works on files — create a file with the commit hash
echo -n "$COMMIT_HASH" > "$HASH_FILE"
ots stamp "$HASH_FILE"

# ots creates <file>.ots next to the file
mv "$HASH_FILE.ots" "$OTS_FILE"

echo "[OTS] Timestamped $TAG ($COMMIT_HASH) → $OTS_FILE"
echo ""
echo "Next steps:"
echo "  1. git add $TIMESTAMP_DIR && git commit -m 'chore: add OTS proof for $TAG'"
echo "  2. Wait 1-2 hours for Bitcoin confirmation"
echo "  3. Verify: ots verify $OTS_FILE $HASH_FILE"
