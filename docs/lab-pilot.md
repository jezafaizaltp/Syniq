# Running the pilot on a school lab computer

This guide runs SYNiq on **one computer in the school**. Students, teachers and the admin then use it from the lab computers and tablets over the school Wi-Fi, in an ordinary browser. You don't need a server, a web address or a bank card. Nothing is installed on the student computers.

It is the same SYNiq as the online version, with the same database, so moving to a real server later keeps every student's progress (see step 10).

## What changes compared with a real server

| | Lab computer | Real server ([docs/deploy.md](deploy.md)) |
| --- | --- | --- |
| Where it works | Only inside the school, on the school network | Anywhere with internet |
| Parents | Can see their child's page only while at school | From home, on their phone |
| When it works | Only while the lab computer is switched on | Always |
| Install as an app / works offline | No (needs a secure `https://` address) | Yes |
| Cost | Nothing | About ₹1,000 to ₹2,000 a month |
| Student data | Stays on that one computer | On the server, in India |

For a pilot where students use SYNiq in lab periods, the lab computer is enough. The main loss is that parents and students can't use it from home.

## Can one computer handle 50 students?

Yes. On 5 November 2026 we rehearsed the pilot on this setup, held to **2 processor cores** (like an ordinary school desktop):

| What we did | Result |
| --- | --- |
| Admin imports 50 students and 48 parents from a sheet | 11.6 seconds |
| All 50 sign in for the first time within a minute and choose a password | No errors. Slowest sign-in 0.6 s |
| All 50 practise together for 9½ minutes: reading explanations, answering (949 answers), asking for hints, wrong-answer pictures, plus two teachers watching their class page | **No errors.** Typical reply 30 to 45 ms, slowest 0.6 s |
| All 48 consented students press "Next" at the very same moment | Everyone answered within 1.5 s |
| All 50 sign in at the very same moment | Everyone in within 3.3 s |
| Two students whose consent form came back unsigned | Correctly kept out of practice |

At the busiest moment the two cores were about two-thirds busy, and SYNiq used about 400 MB of memory. A computer with 2 cores and 4 GB of memory is enough. The slow part on a real lab day is more likely to be the school Wi-Fi than this computer, so try it with a full class once before the pilot starts.

## 1. What you need

- **One computer that stays in the lab** and is switched on whenever students use SYNiq. It needs a 64-bit processor, at least 8 GB of memory (4 GB is enough on Ubuntu), and 20 GB of free disk. A cable to the school router is better than Wi-Fi for this one computer.
- It can run **Ubuntu or KITE GNU/Linux** (simplest) or **Windows 10/11**.
- **Internet for the first set-up** (about 2 GB to download). After that, SYNiq works on the school network even if the internet is down. Only the optional AI tutor needs internet.
- **A pen drive** for the weekly backup copy.
- The person who looks after the school Wi-Fi, for 10 minutes in step 5.

## 2. Install Docker (once)

Docker is the free program that runs SYNiq's parts (database, app, web server) together.

**On Ubuntu or KITE GNU/Linux**, open a Terminal and run:

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
sudo systemctl enable docker
sudo apt install -y git
```

Then log out and log in again.

**On Windows**, install **Docker Desktop** from docker.com (the free personal/education licence covers this), and allow it to turn on WSL 2 if it asks, then restart. In Docker Desktop **Settings → General**, tick **Start Docker Desktop when you sign in**. Also install **Git for Windows** from git-scm.com. In Windows **Settings → Accounts → Sign-in options**, set the computer to sign in automatically, or SYNiq only starts once someone signs in.

## 3. Get SYNiq

In a Terminal (Ubuntu) or PowerShell (Windows):

```bash
git clone https://github.com/jezafaizaltp/Syniq.git syniq
```

The repository is private, so Git asks for the owner's GitHub sign-in the first time. If Git isn't possible, download the ZIP from the GitHub page (**Code → Download ZIP**) while signed in, and unzip it to a folder called `syniq`. With the ZIP, updates in step 9 mean downloading it again.

## 4. Start SYNiq

**Ubuntu:**

```bash
cd syniq/deploy/lab
./start.sh
```

**Windows:** open the `syniq\deploy\lab` folder and double-click **start-windows.bat**.

The first start takes 5 to 15 minutes. The script then:

1. Makes a random database password and saves it in `deploy/lab/.env`. **Copy this file to the pen drive** as well, and keep it safe.
2. Asks for the **school admin's email and password** (at least 8 characters). This is the account that adds students and teachers.
3. Shows the address to type on the student computers, for example `http://192.168.1.20`.

Run the same script again at any time. It only starts what isn't already running, and shows the address again.

## 5. Make the address stay the same

The router gives each computer its address, and it can change after a restart. Ask the person who manages the school Wi-Fi to **reserve** this computer's address in the router (usually called *DHCP reservation* or *static lease*), so the address never changes.

While they're in the router settings, check these:

- **Client isolation** (also called *AP isolation*) must be **off** on the Wi-Fi students use. When it's on, tablets can't reach other computers on the network.
- The student Wi-Fi and the lab computer must be on the **same network**, not a separate guest network.

## 6. Check from a student computer or tablet

On the school Wi-Fi, open the browser and type the address from step 4 (with `http://`, not `https://`). The SYNiq sign-in page should appear. Add it as a bookmark, or **Add to Home screen** on tablets, so students don't have to type it.

If it doesn't open:

- Check the device is on the school Wi-Fi, not mobile data.
- **Ubuntu firewall:** run `sudo ufw allow 80/tcp`.
- **Windows firewall:** set the network to **Private** (Settings → Network → the network → Private), and allow Docker Desktop when Windows asks.
- Run the start script again and check the address it shows.

## 7. Set up the pilot

This is the same as on a real server. Follow [step 7 of docs/deploy.md](deploy.md#7-set-up-the-pilot): sign in as the admin, then on **School** import the students and parents from the CSV, print the login slips, add the Class 9 chapters and add the teachers.

## The first lab day

1. Switch on the lab computer 10 minutes early and open the SYNiq address on one tablet to check it works.
2. Give each student their slip. The address is printed on it.
3. Students type the login and password from the slip, then choose their own password (at least 8 letters or numbers). **Ask them to write it in their notebook**: if they forget it, the admin presses **New password** on the School page.
4. Each subject offers a short optional check first. Students can take it, so SYNiq skips what they already know, or skip it.
5. At the end, everyone presses **Sign out**.

## 8. Every day

- Switch the lab computer on before the lab period and **don't let it go to sleep** while students are using SYNiq. Turn off sleep in power settings. The screen can still turn off.
- SYNiq starts by itself when the computer starts (on Windows, after sign-in). Nothing needs to be clicked.
- Students should **sign out** at the end, because lab computers are shared.

## Optional: free AI for questions the notes don't cover

Ask SYNiq answers questions about a topic from SYNiq's own notes. That works without the internet. Questions the notes don't cover can go to Cloudflare Workers AI, which is free (no card, 10,000 "neurons" a day, roughly 130 questions) and does not train on what is sent. Each student can send at most 20 a day, and no student names or details are sent.

1. Sign in at https://dash.cloudflare.com and open **AI** → **Workers AI** in the left menu.
2. Click **Use REST API**, then **Create a Workers AI API Token**. Keep the suggested name and click **Create API Token**.
3. Copy the token (Cloudflare shows it only once) and the **Account ID** on the same page.
4. On the lab computer, add both to `deploy/lab/.env`:
   ```
   CLOUDFLARE_ACCOUNT_ID=your account id
   CLOUDFLARE_API_TOKEN=your token
   ```
5. Run the start script again. Answers from Cloudflare are marked "Answered by AI". Without the internet, those questions are saved for the admin instead.

To switch it off, empty those two lines and run the start script again.

## 9. Backups and updates

A backup copy of the database is made every time SYNiq starts and every 24 hours after that. The copies are kept for 14 days in `deploy/lab/backups`.

**Every week, copy the `deploy/lab/backups` folder to the pen drive**, and keep the pen drive somewhere other than the lab. If the lab computer breaks, this copy is all that's left.

To **make a backup right now** (for example, before an update):

```bash
cd syniq/deploy/lab
docker compose restart backup
```

To **update SYNiq** to the newest version, take a backup first, then run `./start.sh --update` (Ubuntu) or `start-windows.bat -Update` from a Command Prompt in that folder (Windows). Database changes are applied automatically.

To **restore a backup** (this replaces everything in the database):

```bash
cd syniq/deploy/lab
docker compose stop api web
docker compose exec -T db psql -U syniq -d postgres -c "DROP DATABASE syniq WITH (FORCE);" -c "CREATE DATABASE syniq OWNER syniq;"
gunzip -c backups/syniq-2026-11-20.sql.gz | docker compose exec -T db psql -U syniq -d syniq
docker compose start api web
```

Wait about a minute before signing in again: SYNiq checks the database and content as it starts.

On Windows, run these in Git Bash (installed with Git for Windows) so `gunzip` works.

**Never run `docker compose down -v`**: the `-v` deletes the database. To stop SYNiq, use `docker compose stop`.

## 10. Moving to a real server later

When a server is ready, set it up with [docs/deploy.md](deploy.md) up to step 5, then restore the newest backup from the lab computer onto it (step 8 of that guide). Every account, consent record and student's progress moves across. Students then use the new web address, and parents can use it from home.

## Checking on it

```bash
cd syniq/deploy/lab
docker compose ps                 # all five should say "running"
docker compose logs --tail 100 api
```
