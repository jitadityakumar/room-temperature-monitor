#!/bin/sh
set -e
cat > /usr/share/nginx/html/config.json <<EOF
{"lat":${LAT},"lon":${LON}}
EOF
