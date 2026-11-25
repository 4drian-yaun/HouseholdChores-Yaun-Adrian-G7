from datetime import date, timedelta
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from accounts.models import CustomUser
from households.services import add_member, create_household

from .models import Assignment
from .services import create_chore

MONDAY = date(2026, 11, 16)


def at(day):
    return patch("django.utils.timezone.localdate", return_value=day)


def make_user(username):
    return CustomUser.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="StrongPass123",
        first_name=username.title(),
        last_name="Tester",
    )


class RotateWeeklyCommandTests(TestCase):
    def test_rotate_weekly_closes_past_pending_and_rotates_all_households(self):
        u1 = make_user("cmd_boss1")
        u2 = make_user("cmd_ana1")
        h1 = create_household(u1, "House One")
        m1 = h1.members.get(user=u1)
        m2, _ = add_member(h1, "Ana", u2)

        u3 = make_user("cmd_boss2")
        h2 = create_household(u3, "House Two")

        with at(MONDAY):
            c1 = create_chore(h1, "Trash", "")
            c2 = create_chore(h2, "Dishes", "")

        out = StringIO()
        next_monday = MONDAY + timedelta(days=7)
        with at(next_monday):
            call_command("rotate_weekly", stdout=out)

        self.assertIn("Rotated 2 household(s).", out.getvalue())

        old_a1 = Assignment.objects.get(chore=c1, week_start_date=MONDAY)
        new_a1 = Assignment.objects.get(chore=c1, week_start_date=next_monday)
        self.assertEqual(old_a1.status, Assignment.Status.MISSED)
        self.assertEqual(new_a1.status, Assignment.Status.PENDING)
        self.assertEqual(new_a1.member, m2 if old_a1.member == m1 else m1)

        old_a2 = Assignment.objects.get(chore=c2, week_start_date=MONDAY)
        new_a2 = Assignment.objects.get(chore=c2, week_start_date=next_monday)
        self.assertEqual(old_a2.status, Assignment.Status.MISSED)
        self.assertEqual(new_a2.status, Assignment.Status.PENDING)
