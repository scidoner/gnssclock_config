
#!/usr/bin/env bash

# Configuration
WEBHOOK_URL="https://your-webhook-url-here"

# Check that Chrony is running
if ! systemctl is-active --quiet chronyd && \
   ! systemctl is-active --quiet chrony; then
    echo "ERROR: Chrony is not running"
    exit 1
fi

# Check that Chrony is synchronised
if ! chronyc tracking | grep -q "Leap status.*Normal"; then
    echo "ERROR: Chrony is not synchronised"
    exit 1
fi

echo "OK: Chrony is running and synchronised"

# Check that GPSD is running
if ! systemctl is-active --quiet gpsd; then
    echo "ERROR: GPSD is not running"
    exit 1
fi

# Require GPS 3D fix (mode 3)
GPS_STATUS=$(timeout 5 gpspipe -w -n 10 2>/dev/null)

if ! echo "$GPS_STATUS" | grep -q '"mode":3'; then
    echo "ERROR: GPS does not have a 3D fix"
    exit 1
fi

echo "OK: GPS has a 3D fix"

# Both conditions satisfied - send webhook
echo "Chrony and GPS checks passed. Sending webhook..."

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    --max-time 10 \
    -X POST \
    -H "Content-Type: application/json" \
    -d '{
        "status": "healthy",
        "chrony": "synchronised",
        "gps": "3d_fix"
    }' \
    "$WEBHOOK_URL")

if [[ "$HTTP_CODE" =~ ^2[0-9][0-9]$ ]]; then
    echo "SUCCESS: Webhook sent (HTTP $HTTP_CODE)"
else
    echo "ERROR: Webhook failed (HTTP $HTTP_CODE)"
    exit 1
fi
