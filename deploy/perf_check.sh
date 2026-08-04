#!/bin/sh
set -eu

BASE_URL="${1:-http://127.0.0.1:8080}"
SAMPLES="${2:-10}"

case "$SAMPLES" in
  *[!0-9]*|"") echo "samples must be a positive integer" >&2; exit 2 ;;
esac

sample() {
  label="$1"
  path="$2"
  index=1
  while [ "$index" -le "$SAMPLES" ]; do
    curl -sS --compressed -o /dev/null --max-time 20 \
      -w "$label code=%{http_code} connect=%{time_connect} ttfb=%{time_starttransfer} total=%{time_total} bytes=%{size_download}\n" \
      "${BASE_URL}${path}"
    index=$((index + 1))
  done
}

echo "ABA performance sample: base=${BASE_URL} samples=${SAMPLES}"
sample "home" "/"
sample "health" "/health"
sample "bootstrap-unauthenticated" "/api/v1/bootstrap"
