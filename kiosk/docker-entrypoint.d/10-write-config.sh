#!/bin/sh
set -e
: "${LAT:?LAT is required}" "${LON:?LON is required}" "${GRAFANA_URL:?GRAFANA_URL is required}"
printf '{"lat":%s,"lon":%s,"grafanaUrl":"%s"}\n' "$LAT" "$LON" "$GRAFANA_URL" \
  > /usr/share/nginx/html/config.json
