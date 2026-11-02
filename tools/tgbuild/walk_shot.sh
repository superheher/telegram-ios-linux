#!/bin/sh
# One walk step: screenshot the device into the ui-walk assets and check for new
# Telegram crash reports. Usage: walk_shot.sh <label>
set -e
PATH=/usr/local/usr/bin:$HOME/.local/bin:$PATH
export PATH
LABEL="$1"
LABEL="${LABEL##*/}"   # a label is a bare filename; strip any directory part
OUT="docs/receipts/assets/ui-walk/${LABEL}.png"
mkdir -p docs/receipts/assets/ui-walk /tmp/walk-crashes
idevicescreenshot "$OUT"
echo "screenshot: $OUT"
idevicecrashreport -e /tmp/walk-crashes >/dev/null 2>&1 || true
NEW=$(ls -t /tmp/walk-crashes/*.ips 2>/dev/null | head -5)
if [ -n "$NEW" ]; then
  echo "recent crash reports:"
  echo "$NEW"
else
  echo "no crash reports"
fi
