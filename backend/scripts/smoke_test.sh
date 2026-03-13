#!/usr/bin/env bash
# scripts/smoke_test.sh
# Quick post-deployment smoke test.
# Usage: ./scripts/smoke_test.sh https://yourdomain.com your_access_token
set -euo pipefail

BASE_URL="${1:-http://localhost:3000}"
TOKEN="${2:-}"
PASS=0; FAIL=0

check() {
    local label="$1" expected="$2" actual="$3"
    if [ "$actual" = "$expected" ]; then
        echo "  ✅  $label"
        ((PASS++))
    else
        echo "  ❌  $label — expected $expected, got $actual"
        ((FAIL++))
    fi
}

echo "=== Cyber Drive smoke test ==="
echo "    Base URL: $BASE_URL"
echo ""

# Health
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/health")
check "GET /health returns 200" "200" "$STATUS"

HEALTH_STATUS=$(curl -s "$BASE_URL/health" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['status'])" 2>/dev/null)
check "Health overall status is ok or degraded" "ok" "$HEALTH_STATUS" 2>/dev/null || \
check "Health overall status is ok or degraded" "degraded" "$HEALTH_STATUS"

# Levels (public)
if [ -n "$TOKEN" ]; then
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $TOKEN" "$BASE_URL/levels")
    check "GET /levels returns 200" "200" "$STATUS"

    STATUS=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $TOKEN" "$BASE_URL/documents")
    check "GET /documents returns 200" "200" "$STATUS"
fi

# 404 on unknown routes
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/nonexistent-route-xyz")
check "Unknown route returns 404" "404" "$STATUS"

# Rate limiter is alive (not 500)
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/auth/register" \
    -H "Content-Type: application/json" -d '{"email":"test@example.com"}')
check "POST /auth/register returns non-500" "not-500" "$([ "$STATUS" != "500" ] && echo not-500 || echo 500)"

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
[ "$FAIL" -eq 0 ]
