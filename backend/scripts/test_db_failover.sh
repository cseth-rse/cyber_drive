#!/usr/bin/env bash
# scripts/test_db_failover.sh
# Simulates PostgreSQL primary failure and validates repmgr promotion.
# RUN ON A STAGING / TEST ENVIRONMENT ONLY — this stops the primary DB!
#
# Usage: ./scripts/test_db_failover.sh <primary-host> <standby-host>
set -euo pipefail

PRIMARY="${1:-db1}"
STANDBY="${2:-db2}"
APP_URL="${3:-http://localhost:3000}"

echo "============================================"
echo "  Cyber Drive DB Failover Test"
echo "  Primary : $PRIMARY"
echo "  Standby : $STANDBY"
echo "  App URL : $APP_URL"
echo "============================================"

step() { echo ""; echo "── $1 ──"; }

step "1. Verify initial cluster state"
ssh "$PRIMARY" "sudo -u postgres repmgr -f /etc/repmgr.conf cluster show"

step "2. Verify app is healthy before failover"
curl -sf "$APP_URL/health" | python3 -m json.tool

step "3. Simulate primary failure (stop PostgreSQL on $PRIMARY)"
echo "   ⚠️  This will stop PostgreSQL on $PRIMARY"
read -rp "   Continue? [y/N] " confirm
[[ "$confirm" =~ ^[yY]$ ]] || { echo "Aborted."; exit 0; }
ssh "$PRIMARY" "sudo systemctl stop postgresql"
FAILOVER_START=$(date +%s)
echo "   Primary stopped at $(date)"

step "4. Wait for repmgrd to detect failure and promote standby"
echo "   Polling cluster state every 5 seconds..."
for i in $(seq 1 24); do
    sleep 5
    ROLE=$(ssh "$STANDBY" "sudo -u postgres repmgr -f /etc/repmgr/repmgr-standby.conf cluster show 2>/dev/null | grep $STANDBY" | awk '{print $3}' || echo unknown)
    echo "   [${i}] $STANDBY role: $ROLE"
    if [[ "$ROLE" == "primary" ]]; then
        FAILOVER_END=$(date +%s)
        echo "   ✅ Standby promoted to primary in $((FAILOVER_END - FAILOVER_START))s"
        break
    fi
done

step "5. Verify app is still responding"
for i in $(seq 1 6); do
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$APP_URL/health")
    echo "   [${i}] /health → HTTP $STATUS"
    sleep 5
done

step "6. Update PgBouncer to point to new primary ($STANDBY)"
echo "   Manual step — edit /etc/pgbouncer/pgbouncer.ini on db1 if needed:"
echo "   cyber_db = host=$STANDBY port=5432 dbname=cyber_db"
echo "   sudo systemctl reload pgbouncer"

step "7. Recovery — re-register old primary as standby"
echo "   When $PRIMARY comes back, run on $PRIMARY:"
echo "   sudo systemctl start postgresql"
echo "   sudo -u postgres repmgr standby clone -h $STANDBY -U repmgr -d repmgr -f /etc/repmgr.conf --force"
echo "   sudo -u postgres repmgr standby register -f /etc/repmgr.conf --force"

echo ""
echo "============================================"
echo "  Test complete. Verify /health returns 'ok'"
echo "============================================"
