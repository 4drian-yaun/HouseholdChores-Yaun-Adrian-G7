# HouseholdChores

Who's doing what this week? A Django + PostgreSQL/Supabase chore rotation tracker for roommates and families.

## Features

- **Account (F-01, F-02):** register, log in/out, profile, change password.
- **Household (F-03):** create a household (creator automatically becomes Household Admin), add/edit/order/remove members (with or without a login), and promote/demote members.
- **Chores (F-04):** add, edit, and retire recurring weekly chores.
- **Rotation (F-05):** every chore moves to the next member each Monday; unfinished chores become missed.
- **Dashboard (F-06):** unified view of this week's assignments with progress and "Mark done" action.
- **Completion Tracking (F-07):** record completion timestamp with strict permission rules.
- **History (F-08):** past weeks, filterable by week.
- **Analytics (F-09):** completed vs. missed pie chart, completed per member, most missed chores, weekly trend.

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

Fill in `.env` with your PostgreSQL or Supabase credentials. For Supabase use the Session pooler details and set `DB_SSLMODE=require`.

## Automated Weekly Rotation (F-05 Scheduler)

Chore assignments run from Monday to Sunday. When any household page is opened, the system lazily catches up. To ensure assignments rotate and close out on schedule even when no user logs in:

### Linux / Crontab:
Add the following line via `crontab -e`:
```bash
0 0 * * 1 cd /path/to/HouseholdChores && /path/to/venv/bin/python manage.py rotate_weekly >> /var/log/rotate_weekly.log 2>&1
```

### Windows Task Scheduler:
A PowerShell script is provided in `scripts/rotate_weekly.ps1`. You can schedule it with:
```powershell
$Action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-ExecutionPolicy Bypass -File .\scripts\rotate_weekly.ps1"
$Trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 00:00
Register-ScheduledTask -TaskName "HouseholdChoresWeeklyRotation" -Action $Action -Trigger $Trigger
```

Or trigger manual rotation at any time:
```bash
python manage.py rotate_weekly
```

## How It Works

1. Any user registers an account.
2. If they are creating a household, they enter the household name on the dashboard and automatically become its **Household Admin**.
3. Other members register their accounts and share their username with the Household Admin, who adds them under **Members**. Members without an account can also be added by name.
4. The Household Admin adds chores. Each chore is assigned immediately and rotates weekly in the member rotation order.
5. Members mark their chores complete during the week.

## Tests

Run the test suite (uses fast SQLite when `USE_SQLITE=True` or during `test` execution):
```bash
python manage.py test
```
