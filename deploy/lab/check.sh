#!/usr/bin/env bash
# Check the lab computer is ready before a class: SYNiq running, reachable on the school network,
# enough free disk space, and a recent backup. Changes nothing. Run it 10 minutes before the lab period.
# Usage:  ./check.sh
set -uo pipefail
cd "$(dirname "$0")"

problems=0; warnings=0
ok()   { printf '  OK     %s\n' "$*"; }
warn() { printf '  CHECK  %s\n' "$*"; warnings=$((warnings + 1)); }
fail() { printf '  FIX    %s\n' "$*"; problems=$((problems + 1)); }

port=80
[ -f .env ] && port=$(grep -E '^PORT=' .env | cut -d= -f2)
port=${port:-80}
suffix=""; [ "$port" != "80" ] && suffix=":${port}"

echo "SYNiq lab check, $(date '+%d %b %Y %H:%M')"

# 1. Docker and the five parts of SYNiq
if ! command -v docker >/dev/null 2>&1 || ! docker info >/dev/null 2>&1; then
  fail "Docker is not running. Start it (sudo systemctl start docker), then run ./start.sh"
else
  running=$(docker compose ps --status running --services 2>/dev/null | sort | tr '\n' ' ')
  missing=""
  for s in api backup caddy db web; do
    case " $running" in *" $s "*) ;; *) missing="$missing $s" ;; esac
  done
  if [ -z "$missing" ]; then ok "All five parts of SYNiq are running"
  else fail "Not running:${missing}. Run ./start.sh, or see: docker compose logs --tail 50${missing}"; fi
fi

# 2. SYNiq answers on this computer
if curl -fsS -m 5 "http://localhost:${port}/api/health" >/dev/null 2>&1; then
  ok "SYNiq answers at http://localhost${suffix}"
else
  fail "SYNiq does not answer at http://localhost${suffix}. Run ./start.sh"
fi

# 3. The network address students type
addresses=$(hostname -I 2>/dev/null | tr ' ' '\n' | grep -E '^[0-9]+\.' | grep -vE '^(127|172\.(1[6-9]|2[0-9]|3[01]))\.' || true)
if [ -z "$addresses" ]; then
  fail "No school network address found. Connect this computer to the school Wi-Fi or cable."
else
  for a in $addresses; do
    if curl -fsS -m 5 "http://${a}${suffix}/api/health" >/dev/null 2>&1; then
      ok "Students open http://${a}${suffix}"
    else
      fail "SYNiq does not answer at http://${a}${suffix}. Run ./start.sh"
    fi
  done
  if [ -f .last-address ] && [ "$(cat .last-address)" != "$addresses" ]; then
    warn "The address changed since the last check (was $(tr '\n' ' ' < .last-address)). Login slips and bookmarks show the old one: see docs/lab-pilot.md step 5."
  fi
  printf '%s' "$addresses" > .last-address
fi
if command -v ufw >/dev/null 2>&1 && ufw status 2>/dev/null | grep -q '^Status: active'; then
  if ufw status 2>/dev/null | grep -qE "^${port}(/tcp)?[[:space:]]+ALLOW"; then ok "Firewall lets students in on port ${port}"
  else warn "The firewall may block students. Run: sudo ufw allow ${port}/tcp"; fi
fi

# 4. Free disk space
free_gb=$(df -Pk . | awk 'NR==2 {printf "%d", $4 / 1048576}')
if [ "$free_gb" -lt 2 ]; then fail "Only ${free_gb} GB free on this disk. Delete old files, or SYNiq may stop saving work."
elif [ "$free_gb" -lt 5 ]; then warn "${free_gb} GB free on this disk. Make room soon (5 GB or more is comfortable)."
else ok "${free_gb} GB free on this disk"; fi

# 5. A recent backup
newest=$(ls -t backups/syniq-*.sql.gz 2>/dev/null | head -1)
if [ -z "$newest" ]; then
  fail "No backup found in deploy/lab/backups. Make one now: docker compose restart backup"
else
  age_h=$(( ($(date +%s) - $(stat -c %Y "$newest")) / 3600 ))
  if ! gzip -t "$newest" 2>/dev/null || [ "$(gzip -cd "$newest" 2>/dev/null | head -c 100000 | grep -c 'CREATE TABLE')" -eq 0 ]; then
    fail "The newest backup ($(basename "$newest")) looks broken. Make one now: docker compose restart backup"
  elif [ "$age_h" -gt 30 ]; then
    fail "The newest backup is ${age_h} hours old. Make one now: docker compose restart backup"
  else
    ok "Newest backup $(basename "$newest") is ${age_h} hours old"
  fi
  oldest_days=$(( ($(date +%s) - $(stat -c %Y "$(ls -t backups/syniq-*.sql.gz | tail -1)")) / 86400 ))
  [ "$oldest_days" -ge 7 ] && printf '  NOTE   %s\n' "Copy deploy/lab/backups to the pen drive once a week."
fi

# 6. Lessons and questions are loaded
if command -v docker >/dev/null 2>&1 && content=$(docker compose exec -T api python -m tools.content_counts 2>/dev/null); then
  ok "Content: ${content}"
else
  fail "No lessons or questions found. Restart SYNiq (./start.sh); if it stays empty see: docker compose logs --tail 50 api"
fi

echo
if [ "$problems" -gt 0 ]; then
  echo "${problems} thing(s) to fix before students start."
  exit 1
fi
[ "$warnings" -gt 0 ] && echo "Ready, with ${warnings} thing(s) to check." || echo "Ready for the class."
exit 0
