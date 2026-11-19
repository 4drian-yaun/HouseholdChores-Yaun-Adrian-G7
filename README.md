# HouseholdChores

Who's doing what this week? A Django + PostgreSQL/Supabase chore rotation tracker for roommates and families.

## Features

- Account: register, log in/out, role-based dashboards, profile, change password
- Household: create a household, add/edit/order/remove members (with or without a login)
- Chores: add, edit, and retire recurring weekly chores
- Rotation: every chore moves to the next member each Monday; unfinished chores become missed
- Dashboard: this week's assignments with progress and "Mark done"
- History: past weeks, filterable by week
- Analytics: completed vs. missed pie, completed per member, most missed chores, weekly trend

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

## How it works

1. A Household Admin signs up, then creates a household on the dashboard.
2. Members sign up and give their username to the admin, who adds them under Members. People without an account can be added by name and marked done by an admin.
3. The admin adds chores. Each chore is assigned immediately and rotates weekly.
4. Weeks run Monday to Sunday. Rotation is applied automatically whenever a household page is opened, and can also be run on a schedule:

```bash
python manage.py rotate_weekly
```

## Tests

```bash
python manage.py test
```
