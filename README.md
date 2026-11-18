# HouseholdChores

Who's doing what this week? Django + PostgreSQL/Supabase chore rotation tracker.

Phase 1: Account feature (registration, login/logout, role-based dashboards, profile).

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

Fill in `.env` with your PostgreSQL or Supabase credentials. For Supabase use the connection details from Project Settings > Database, and set `DB_SSLMODE=require`.

## Roles

- Household Admin (`ADMIN`): `/dashboard/admin/`
- Household Member (`MEMBER`): `/dashboard/member/`

`/` sends each logged-in user to the dashboard for their role. Superusers are always Household Admins.

## Tests

```bash
python manage.py test
```
