# HouseholdChores

**Who's doing what this week?** A web-based weekly chore rotation tracker built with Django and PostgreSQL/Supabase for roommates, families, dormitories, and shared living spaces.

**Live App:** https://householdchores-yaun-adrian-g7.onrender.com

## Tech Stack

- **Backend:** Python, Django 6.1
- **Database:** PostgreSQL / Supabase (with automatic SQLite fallback for tests or local dev via `USE_SQLITE=True`)
- **Frontend:** Django Templates, vanilla CSS & JavaScript (no external frontend frameworks)

## Features

- **Landing Page:** Public home page (`/`) with an interactive chore board preview; automatically redirects signed-in users to `/dashboard/`.
- **Account & Profile (F-01, F-02):** Register, log in/out, edit profile, change password with live strength checklist, show/hide password toggles, and self-service account deletion with password confirmation and safe household cleanup.
- **Household Management (F-03):** Any user can create a household and automatically become its Household Admin; rename the household; add, edit, reorder, promote/demote, and remove member profiles (with or without login accounts); live rotation chain display; and leave household (with last-admin protection).
- **Chore Management (F-04):** Add, edit, and retire recurring weekly chores with a live **Next Monday** assignee preview.
- **Automated Weekly Rotation (F-05):** Monday–Sunday cycles; every active chore shifts to the next active member in rotation order each Monday, wrapping back to the first member, while unfinished chores close as `Missed`.
- **Dashboard (F-06):** Unified weekly view with KPI stat cards, week countdown badge, progress bar, interactive chore filters (*All / Assigned to me / Pending / Done*), and a copyable username card for users waiting to join a household.
- **Completion Tracking (F-07):** One-click **Mark done** logs an immutable system timestamp; restricted to the assigned member (or a Household Admin for members without login accounts) during the assigned week only.
- **History View (F-08):** Read-only archive of past weeks filterable by week and member, with Older/Newer week navigation and per-week KPI summaries.
- **Simple Analytics (F-09):** Computed solely from stored assignment records (excluding current-week pending tasks), featuring a Household insight strip, KPI cards, interactive SVG donut chart (*Completed vs. missed*), sortable member leaderboard (*Most done / Best rate*), most missed chores, and a weekly completion trend chart with hover tooltips.
- **Light & Dark Mode:** Navbar theme switcher with OS preference detection, zero-flash initialization, and saved `localStorage` preference.

## Project Structure

```text
HouseholdChores-Yaun-Adrian-G7/
├── accounts/          # Custom user model, auth, profile, password change, account deletion
├── households/        # Household & member models, rotation order, role delegation, context processor
├── chores/            # Chore & assignment models, weekly rotation engine, history, analytics, CLI command
├── dashboard/         # Landing page (/) and unified weekly dashboard (/dashboard/)
├── householdchores/   # Django project settings and root URLs
├── scripts/           # Cron example and Windows Task Scheduler PowerShell script for F-05
├── static/            # CSS theme/animations (style.css), vanilla JS (app.js), logo assets
└── templates/         # HTML templates across all apps
```

## Setup

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### Environment Variables (`.env`)

| Variable | Description | Default |
| :--- | :--- | :--- |
| `SECRET_KEY` | Django secret key | `django-insecure-change-me` |
| `DEBUG` | Enable debug mode (`True` / `False`) | `True` |
| `ALLOWED_HOSTS` | Comma-separated allowed hostnames | `localhost,127.0.0.1` |
| `CSRF_TRUSTED_ORIGINS` | Comma-separated HTTPS origins (e.g. `https://your-app.onrender.com`) | *(auto-set on Render)* |
| `USE_SQLITE` | Set `True` to run locally with SQLite instead of PostgreSQL | `False` |
| `DB_NAME` | PostgreSQL / Supabase database name | `postgres` |
| `DB_USER` | Database username | `postgres` |
| `DB_PASSWORD` | Database password | *(empty)* |
| `DB_HOST` | Database host (use Supabase Session pooler host) | `localhost` |
| `DB_PORT` | Database port | `5432` |
| `DB_SSLMODE` | SSL mode (`require` for Supabase) | `prefer` |

## Automated Weekly Rotation (F-05 Scheduler)

Chore weeks run from **Monday to Sunday**. Opening any household page automatically catches up any elapsed weeks, and a Django management command is provided for scheduled execution:

```bash
python manage.py rotate_weekly
```

### GitHub Actions (Cloud Cron)
A workflow is included at `.github/workflows/rotate_weekly.yml` to run `rotate_weekly` every Monday at `00:00 Asia/Manila` (`Sunday 16:00 UTC`) using repository secrets (`SECRET_KEY`, `DB_*`).

### Linux / Crontab
See `scripts/crontab.example` or add via `crontab -e`:
```bash
0 0 * * 1 cd /path/to/HouseholdChores && /path/to/venv/bin/python manage.py rotate_weekly >> /var/log/rotate_weekly.log 2>&1
```

### Windows Task Scheduler
Use the included `scripts/rotate_weekly.ps1`:
```powershell
$Action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-ExecutionPolicy Bypass -File .\scripts\rotate_weekly.ps1"
$Trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 00:00
Register-ScheduledTask -TaskName "HouseholdChoresWeeklyRotation" -Action $Action -Trigger $Trigger
```

## How It Works

1. Visit `/` to preview the landing page, then register an account.
2. Create a household on the dashboard to automatically become its **Household Admin**, or share your username so an existing Admin can add you.
3. The Household Admin adds members (linked to user accounts or by display name only) and arranges their rotation order under **Members**.
4. The Household Admin adds recurring weekly chores under **Chores**. New chores are assigned immediately and rotate every Monday.
5. Members mark their chores complete during the week, browse read-only past logs in **History**, and review fairness metrics in **Analytics**.

## Tests

The test suite includes **84 automated tests** verifying authentication, household/member rules, database constraints, weekly rotation, completion tracking, history, and analytics (automatically uses SQLite during test runs):

```bash
python manage.py test
```

## Deployment (Render + Supabase)

Production support (`gunicorn`, `whitenoise`, `STATIC_ROOT`, `CSRF_TRUSTED_ORIGINS`, `build.sh`, and `render.yaml`) is pre-configured:

1. Push the repository to GitHub.
2. On [Render](https://render.com), create a **New Web Service** from your repository:
   - **Build Command:** `pip install -r requirements.txt && python manage.py collectstatic --no-input && python manage.py migrate` (or `./build.sh`)
   - **Start Command:** `gunicorn householdchores.wsgi:application`
3. Add your environment variables (`SECRET_KEY`, `DEBUG=False`, `USE_SQLITE=False`, and your Supabase Session pooler `DB_*` credentials with `DB_SSLMODE=require`). `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` automatically include Render's `RENDER_EXTERNAL_HOSTNAME`.
