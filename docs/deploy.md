# Putting SYNiq online for the pilot

This guide sets up SYNiq on one small server, with HTTPS, a PostgreSQL database and a backup every night. Students, parents and teachers then use it from any browser, on school computers or phones.

Everything runs with Docker Compose (`deploy/docker-compose.yml`):

| Service | What it does |
| --- | --- |
| `caddy` | The front door. Gets and renews the HTTPS certificate automatically, sends `/api/...` to the API and everything else to the web app |
| `web` | The Next.js web app |
| `api` | The FastAPI backend. Applies database migrations each time it starts |
| `db` | PostgreSQL 16 |
| `backup` | Saves a compressed copy of the database every 24 hours to `deploy/backups/`, keeping the last 14 days |

## 1. What you need

- **A server in India** (keeps student data in the country, and is faster for Calicut). For 50 students, 2 CPUs, 4 GB memory and 40 GB disk is plenty. Pick a Mumbai, Hyderabad or Bangalore region. Ubuntu 24.04 LTS. This is usually ₹1,000 to ₹2,000 a month.
- **A web address**, for example `learn.syniq.in` or `syniq.providence.edu.in`.
- **An email address for the school admin** (the person who will add students and teachers).

## 2. Point the web address at the server

At the domain provider, add an `A` record for the address, pointing to the server's public IP address. Wait until `ping learn.syniq.in` answers from that IP before going on, or the HTTPS certificate can't be issued.

Allow ports 80 and 443 in the server's firewall. Keep port 22 (SSH) open only to the people who manage the server.

## 3. Install Docker and get the code

On the server:

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER   # then log out and back in
git clone https://github.com/jezafaizaltp/Syniq.git syniq
cd syniq/deploy
```

## 4. Fill in the settings

```bash
cp .env.example .env
openssl rand -base64 24   # use this as POSTGRES_PASSWORD
nano .env
```

| Setting | What to put |
| --- | --- |
| `DOMAIN` | The web address from step 2, without `https://` |
| `POSTGRES_PASSWORD` | The random password from above. Keep a copy somewhere safe |
| `ANTHROPIC_API_KEY` | Leave empty for now. See step 9 |

`.env` holds secrets: never commit it or send it by email.

## 5. Start SYNiq

```bash
docker compose up -d --build
docker compose ps        # all five should say "running" (db "healthy")
curl https://$DOMAIN/api/health   # replace $DOMAIN; should print {"ok":true}
```

The first build takes a few minutes. If the HTTPS certificate fails, check step 2 and see `docker compose logs caddy`.

## 6. Create the school admin

This adds the nine Class 9 subjects and the first admin account. There are no demo accounts on a live server.

```bash
docker compose exec -e SYNIQ_ADMIN_EMAIL=admin@school.example -e SYNIQ_ADMIN_PASSWORD='a-long-password' api python -m app.bootstrap
```

Running it again is safe: it only adds what is missing.

## 7. Set up the pilot

The admin signs in at `https://<your address>` and opens **School**:

1. **Download the template** and fill in one row per student in Excel or Google Sheets: the student's name, class (e.g. `9 A`), the parent's name, the parent's email if they have one, and `yes` or `no` for each of the three consent boxes on the paper form. Save it as CSV. Don't include marks or how students were chosen.
2. **Choose the CSV file.** SYNiq checks every row first and lists any problems. Nothing is created until the whole sheet is right.
3. **Create accounts**, then **Print login sheet** straight away. Temporary passwords are shown only once. Cut the sheet into slips for each student and parent.
4. **Add the Class 9 chapters and topics** from a sheet (see `content/README.md`; a draft list is in `content/class9-syllabus-draft.csv`). Check it against the textbooks first.
5. **Add a teacher** for each class. Give them their temporary password in person.

Everyone chooses their own password the first time they sign in. If someone forgets theirs, the admin presses **New password** next to their name and gives them the new temporary one.

When a parent returns a changed consent form, tick or untick the boxes for that student. Parents can also change consent themselves on their parent page.

## 8. Backups

A backup runs when SYNiq starts and then every 24 hours. Files are in `deploy/backups/` as `syniq-YYYY-MM-DD.sql.gz`.

**Copy them off the server.** A backup on the same server is lost if the server is. At least once a week, from your own computer:

```bash
scp 'user@server:syniq/deploy/backups/*.sql.gz' ./syniq-backups/
```

Most hosting providers also offer automatic server snapshots for a small fee; it is worth switching on.

**To restore a backup** (this replaces everything in the database):

```bash
docker compose stop api web
docker compose exec -T db psql -U syniq -d postgres -c "DROP DATABASE syniq WITH (FORCE);" -c "CREATE DATABASE syniq OWNER syniq;"
gunzip -c backups/syniq-2026-11-02.sql.gz | docker compose exec -T db psql -U syniq -d syniq
docker compose start api web
```

Practise a restore once before the pilot starts, on a spare server or your own computer.

## 9. Updating

```bash
cd syniq
git pull
cd deploy
docker compose up -d --build
```

Database changes are applied automatically when the API starts. Take a backup copy first (step 8) before any big update.

**Switching on the AI tutor later:** put the key in `ANTHROPIC_API_KEY` in `.env`, then run `docker compose up -d`. Remove it and run the same command to switch AI off again.

## 10. Checking on it

```bash
docker compose ps
docker compose logs --tail 100 api
df -h          # keep an eye on disk space
```

The API docs pages (`/api/docs`) are switched off on a live server. Sign-in is limited to 10 wrong passwords in 15 minutes per account and device, and anyone who hasn't used SYNiq for 14 days is signed out.
