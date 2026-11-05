#!/usr/bin/env bash
# Start SYNiq on this lab computer (Ubuntu / KITE GNU/Linux) and show the address students type.
# Safe to run again at any time: it only builds and starts what is not already running.
# Usage:  ./start.sh            start (the first time it also asks for the school admin's email and password)
#         ./start.sh --update   get the newest SYNiq first, then start
set -euo pipefail
cd "$(dirname "$0")"

say() { printf '\n== %s\n' "$*"; }

if ! command -v docker >/dev/null 2>&1 || ! docker compose version >/dev/null 2>&1; then
  echo "Docker is not installed. See docs/lab-pilot.md, step 2."
  exit 1
fi
if ! docker info >/dev/null 2>&1; then
  echo "Docker is installed but not running, or this user may not use it."
  echo "Try: sudo systemctl start docker   (and log out and in again after: sudo usermod -aG docker \$USER)"
  exit 1
fi

if [ "${1:-}" = "--update" ]; then
  say "Getting the newest SYNiq"
  git -C ../.. pull --ff-only
fi

if [ ! -f .env ]; then
  say "First start: making a database password"
  password=$(head -c 24 /dev/urandom | base64 | tr -d '/+=\n')
  sed "s/^POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=${password}/" .env.example > .env
  chmod 600 .env
  echo "Saved in deploy/lab/.env. Keep a copy of that file somewhere safe (not on this computer only)."
fi
port=$(grep -E '^PORT=' .env | cut -d= -f2)
port=${port:-80}

say "Starting SYNiq (the first time takes 5 to 15 minutes and needs internet)"
docker compose up -d --build

say "Waiting for SYNiq to answer"
for _ in $(seq 1 90); do
  if curl -fsS "http://localhost:${port}/api/health" >/dev/null 2>&1; then ready=1; break; fi
  sleep 2
done
if [ -z "${ready:-}" ]; then
  echo "SYNiq did not answer after 3 minutes. See what went wrong with: docker compose logs --tail 50 api"
  exit 1
fi

if [ ! -f .admin-created ]; then
  say "Create the school admin (the person who adds students and teachers)"
  if [ -t 0 ]; then
    read -rp "Admin email: " admin_email
    while true; do
      read -rsp "Admin password (at least 8 characters): " admin_password; echo
      read -rsp "Type it again: " again; echo
      [ "$admin_password" = "$again" ] && [ ${#admin_password} -ge 8 ] && break
      echo "The two did not match or were too short. Try again."
    done
    docker compose exec -T -e SYNIQ_ADMIN_EMAIL="$admin_email" -e SYNIQ_ADMIN_PASSWORD="$admin_password" api python -m app.bootstrap
    touch .admin-created
  else
    echo "Run ./start.sh in a terminal to create the admin."
  fi
fi

say "SYNiq is running"
addresses=$(hostname -I 2>/dev/null | tr ' ' '\n' | grep -E '^[0-9]+\.' | grep -vE '^(127|172\.(1[6-9]|2[0-9]|3[01]))\.' || true)
suffix=""; [ "$port" != "80" ] && suffix=":${port}"
if [ -n "$addresses" ]; then
  echo "On the school Wi-Fi, students and teachers open:"
  for a in $addresses; do echo "    http://${a}${suffix}"; done
else
  echo "Could not find this computer's network address. Check it is connected to the school network."
fi
echo "On this computer itself:  http://localhost${suffix}"
echo "Backups are saved every day in deploy/lab/backups. Copy that folder to a pen drive every week."
