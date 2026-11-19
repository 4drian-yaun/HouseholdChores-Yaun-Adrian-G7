from datetime import date, timedelta
from unittest.mock import patch

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser
from households.models import HouseholdMember
from households.services import add_member, create_household, remove_member

from .models import Assignment, Chore
from .services import (
    analytics,
    complete_assignment,
    create_chore,
    CompletionError,
    retire_chore,
    sync_household,
)

MONDAY = date(2026, 11, 16)


def at(day):
    return patch("django.utils.timezone.localdate", return_value=day)


def make_user(username, role=CustomUser.Role.MEMBER):
    return CustomUser.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="StrongPass123",
        first_name=username.title(),
        last_name="Tester",
        role=role,
    )


class Base(TestCase):
    def setUp(self):
        self.boss = make_user("boss", CustomUser.Role.ADMIN)
        self.ana = make_user("ana")
        self.household = create_household(self.boss, "Casa")
        self.boss_member = self.household.members.get(user=self.boss)
        self.ana_member, _ = add_member(self.household, "Ana", self.ana)
        self.cam_member, _ = add_member(self.household, "Cam", None)

    def chore(self, name):
        return create_chore(self.household, name, "")

    def assignment(self, chore, week=None):
        return Assignment.objects.get(chore=chore, week_start_date=week or MONDAY)


class RotationTests(Base):
    def test_new_chore_gets_one_assignment_this_week_immediately(self):
        with at(date(2026, 11, 19)):
            chore = self.chore("Trash")
        assignment = self.assignment(chore)
        self.assertEqual(assignment.status, Assignment.Status.PENDING)
        self.assertEqual(assignment.due_date, MONDAY + timedelta(days=6))

    def test_new_chores_spread_across_members(self):
        with at(MONDAY):
            chores = [self.chore(n) for n in ("A", "B", "C")]
        owners = {self.assignment(c).member_id for c in chores}
        self.assertEqual(len(owners), 3)

    def test_rotates_to_next_member_and_wraps(self):
        with at(MONDAY):
            chore = self.chore("Trash")
        first = self.assignment(chore).member
        order = [self.boss_member, self.ana_member, self.cam_member]
        seen = [first]
        for weeks in (1, 2, 3):
            with at(MONDAY + timedelta(weeks=weeks)):
                sync_household(self.household)
            seen.append(self.assignment(chore, MONDAY + timedelta(weeks=weeks)).member)
        start = order.index(first)
        expected = [order[(start + i) % 3] for i in range(4)]
        self.assertEqual(seen, expected)

    def test_pending_becomes_missed_when_week_ends(self):
        with at(MONDAY):
            chore = self.chore("Trash")
        with at(MONDAY + timedelta(days=7)):
            sync_household(self.household)
        self.assertEqual(self.assignment(chore).status, Assignment.Status.MISSED)
        self.assertIsNone(self.assignment(chore).completed_at)

    def test_skipped_weeks_are_backfilled_as_missed(self):
        with at(MONDAY):
            chore = self.chore("Trash")
        with at(MONDAY + timedelta(weeks=3)):
            sync_household(self.household)
        weeks = list(Assignment.objects.filter(chore=chore).order_by("week_start_date").values_list("status", flat=True))
        self.assertEqual(weeks, ["MISSED", "MISSED", "MISSED", "PENDING"])

    def test_sync_is_idempotent(self):
        with at(MONDAY):
            chore = self.chore("Trash")
            sync_household(self.household)
            sync_household(self.household)
        self.assertEqual(Assignment.objects.filter(chore=chore).count(), 1)

    def test_retired_chore_gets_no_new_assignments_but_keeps_history(self):
        with at(MONDAY):
            chore = self.chore("Trash")
        with at(MONDAY + timedelta(days=7)):
            retire_chore(chore)
            sync_household(self.household)
        self.assertEqual(Assignment.objects.filter(chore=chore, week_start_date=MONDAY + timedelta(days=7)).count(), 0)
        self.assertTrue(Assignment.objects.filter(chore=chore, week_start_date=MONDAY).exists())

    def test_retire_removes_unfinished_current_assignment(self):
        with at(MONDAY):
            chore = self.chore("Trash")
            retire_chore(chore)
        self.assertFalse(Assignment.objects.filter(chore=chore).exists())

    def test_new_member_mid_week_takes_a_chore_from_overloaded_member(self):
        solo = make_user("solo", CustomUser.Role.ADMIN)
        household = create_household(solo, "Solo House")
        with at(MONDAY):
            create_chore(household, "A", "")
            create_chore(household, "B", "")
            create_chore(household, "C", "")
            member, moved = add_member(household, "New", None)
        self.assertIsNotNone(moved)
        self.assertEqual(Assignment.objects.filter(member=member, week_start_date=MONDAY).count(), 1)

    def test_removed_member_chores_move_and_rotation_skips_them(self):
        with at(MONDAY):
            for name in ("A", "B", "C"):
                self.chore(name)
            remove_member(self.cam_member, self.boss_member)
        self.assertFalse(Assignment.objects.filter(member=self.cam_member, status="PENDING").exists())
        with at(MONDAY + timedelta(days=7)):
            sync_household(self.household)
        self.assertFalse(
            Assignment.objects.filter(member=self.cam_member, week_start_date=MONDAY + timedelta(days=7)).exists()
        )


class ConstraintTests(Base):
    def test_one_assignment_per_chore_per_week(self):
        with at(MONDAY):
            chore = self.chore("Trash")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Assignment.objects.create(chore=chore, member=self.boss_member, week_start_date=MONDAY)

    def test_week_must_start_on_monday(self):
        with at(MONDAY):
            chore = self.chore("Trash")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Assignment.objects.create(chore=chore, member=self.boss_member, week_start_date=MONDAY + timedelta(days=9))

    def test_active_chore_names_unique_but_retired_name_reusable(self):
        with at(MONDAY):
            chore = self.chore("Trash")
            with self.assertRaises(IntegrityError), transaction.atomic():
                Chore.objects.create(household=self.household, name="Trash")
            retire_chore(chore)
            Chore.objects.create(household=self.household, name="Trash")

    def test_rotation_order_unique_per_household(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            HouseholdMember.objects.create(household=self.household, display_name="Dup", rotation_order=1)


class CompletionTests(Base):
    def setUp(self):
        super().setUp()
        with at(MONDAY):
            self.chore_obj = self.chore("Trash")
        self.assignment_obj = self.assignment(self.chore_obj)

    def reassign(self, member):
        Assignment.objects.filter(pk=self.assignment_obj.pk).update(member=member)
        self.assignment_obj.refresh_from_db()

    def test_assignee_can_complete_and_timestamp_is_system_generated(self):
        self.reassign(self.ana_member)
        with at(MONDAY):
            done = complete_assignment(self.ana_member, self.assignment_obj)
        self.assertEqual(done.status, Assignment.Status.COMPLETED)
        self.assertIsNotNone(done.completed_at)

    def test_other_member_cannot_complete(self):
        self.reassign(self.ana_member)
        with at(MONDAY), self.assertRaises(CompletionError):
            complete_assignment(self.boss_member, self.assignment_obj)

    def test_admin_completes_for_member_without_account(self):
        self.reassign(self.cam_member)
        with at(MONDAY):
            done = complete_assignment(self.boss_member, self.assignment_obj)
        self.assertEqual(done.status, Assignment.Status.COMPLETED)

    def test_member_cannot_complete_for_account_less_member(self):
        self.reassign(self.cam_member)
        with at(MONDAY), self.assertRaises(CompletionError):
            complete_assignment(self.ana_member, self.assignment_obj)

    def test_cannot_complete_twice(self):
        self.reassign(self.ana_member)
        with at(MONDAY):
            complete_assignment(self.ana_member, self.assignment_obj)
            with self.assertRaises(CompletionError):
                complete_assignment(self.ana_member, self.assignment_obj)

    def test_cannot_complete_past_week(self):
        self.reassign(self.ana_member)
        with at(MONDAY + timedelta(days=7)):
            sync_household(self.household)
            with self.assertRaises(CompletionError):
                complete_assignment(self.ana_member, self.assignment_obj)

    def test_view_complete_flow_and_get_not_allowed(self):
        self.reassign(self.ana_member)
        self.client.force_login(self.ana)
        url = reverse("assignment_complete", args=[self.assignment_obj.pk])
        with at(MONDAY):
            self.assertEqual(self.client.get(url).status_code, 405)
            response = self.client.post(url, follow=True)
        self.assertContains(response, "marked as done")
        self.assignment_obj.refresh_from_db()
        self.assertEqual(self.assignment_obj.status, Assignment.Status.COMPLETED)

    def test_other_household_assignment_is_404(self):
        stranger = make_user("stranger", CustomUser.Role.ADMIN)
        create_household(stranger, "Other House")
        self.client.force_login(stranger)
        with at(MONDAY):
            response = self.client.post(reverse("assignment_complete", args=[self.assignment_obj.pk]))
        self.assertEqual(response.status_code, 404)


class DashboardHistoryAnalyticsTests(Base):
    def test_dashboard_shows_only_own_household(self):
        other = make_user("other", CustomUser.Role.ADMIN)
        other_house = create_household(other, "Rival House")
        with at(MONDAY):
            self.chore("Trash")
            create_chore(other_house, "Secret Chore", "")
            self.client.force_login(self.boss)
            response = self.client.get(reverse("admin_dashboard"))
        self.assertContains(response, "Casa")
        self.assertContains(response, "Trash")
        self.assertNotContains(response, "Secret Chore")
        self.assertNotContains(response, "Rival House")

    def test_member_without_household_sees_waiting_page(self):
        loner = make_user("loner")
        self.client.force_login(loner)
        response = self.client.get(reverse("member_dashboard"))
        self.assertContains(response, "Waiting for your household")

    def test_admin_without_household_can_create_one(self):
        fresh = make_user("fresh", CustomUser.Role.ADMIN)
        self.client.force_login(fresh)
        response = self.client.post(reverse("household_create"), {"name": "New Place"}, follow=True)
        self.assertContains(response, "New Place")
        member = HouseholdMember.objects.get(user=fresh)
        self.assertEqual(member.role, HouseholdMember.Role.ADMIN)

    def test_household_needs_a_name(self):
        fresh = make_user("fresh", CustomUser.Role.ADMIN)
        self.client.force_login(fresh)
        self.client.post(reverse("household_create"), {"name": "   "})
        self.assertFalse(HouseholdMember.objects.filter(user=fresh).exists())

    def test_member_account_cannot_create_household(self):
        loner = make_user("loner")
        self.client.force_login(loner)
        self.client.post(reverse("household_create"), {"name": "Nope"})
        self.assertFalse(HouseholdMember.objects.filter(user=loner).exists())

    def test_history_lists_past_weeks_and_filters(self):
        with at(MONDAY):
            self.chore("Trash")
        with at(MONDAY + timedelta(days=7)):
            sync_household(self.household)
            self.client.force_login(self.boss)
            response = self.client.get(reverse("history"))
            self.assertContains(response, "Nov 16, 2026")
            self.assertContains(response, "Missed")
            filtered = self.client.get(reverse("history"), {"week": "2026-11-16"})
            self.assertContains(filtered, "Trash")
            bad = self.client.get(reverse("history"), {"week": "garbage"})
            self.assertEqual(bad.status_code, 200)

    def test_history_empty_state(self):
        self.client.force_login(self.boss)
        with at(MONDAY):
            response = self.client.get(reverse("history"))
        self.assertContains(response, "No past weeks yet")

    def test_analytics_excludes_current_week_pending(self):
        with at(MONDAY):
            self.chore("Trash")
            stats = analytics(self.household)
        self.assertFalse(stats["has_data"])

    def test_analytics_counts_completed_and_missed(self):
        with at(MONDAY):
            first = self.chore("Trash")
            second = self.chore("Dishes")
            a = self.assignment(first)
            owner = a.member
            if owner.user_id is None:
                complete_assignment(self.boss_member, a)
            else:
                complete_assignment(owner, a)
        with at(MONDAY + timedelta(days=7)):
            sync_household(self.household)
            stats = analytics(self.household)
        self.assertEqual(stats["done"], 1)
        self.assertEqual(stats["missed"], 1)
        self.assertEqual(stats["done_pct"], 50)
        self.assertEqual(sum(m["done"] for m in stats["members"]), 1)
        self.assertEqual(stats["chores"][0]["chore__name"], "Dishes")
        self.assertEqual(stats["weeks"][0]["rate"], 50)

    def test_analytics_page_renders_with_data(self):
        with at(MONDAY):
            self.chore("Trash")
        with at(MONDAY + timedelta(days=7)):
            sync_household(self.household)
            self.client.force_login(self.ana)
            response = self.client.get(reverse("analytics"))
        self.assertContains(response, "Completed vs. missed")
        self.assertContains(response, "Weekly completion trend")


class ChoreManagementTests(Base):
    def test_member_cannot_manage_chores(self):
        self.client.force_login(self.ana)
        for name in ("chore_list", "chore_add"):
            response = self.client.get(reverse(name), follow=True)
            self.assertContains(response, "Only a Household Admin")

    def test_admin_adds_edits_and_retires_chore(self):
        self.client.force_login(self.boss)
        with at(MONDAY):
            response = self.client.post(reverse("chore_add"), {"name": "Vacuum", "description": "Living room"}, follow=True)
            self.assertContains(response, "was added")
            chore = Chore.objects.get(name="Vacuum")
            self.client.post(reverse("chore_edit", args=[chore.pk]), {"name": "Vacuum all", "description": ""})
            chore.refresh_from_db()
            self.assertEqual(chore.name, "Vacuum all")
            self.client.post(reverse("chore_retire", args=[chore.pk]))
            chore.refresh_from_db()
        self.assertFalse(chore.is_active)

    def test_duplicate_active_chore_name_rejected_case_insensitive(self):
        self.client.force_login(self.boss)
        with at(MONDAY):
            self.chore("Trash")
            response = self.client.post(reverse("chore_add"), {"name": "trash", "description": ""})
        self.assertContains(response, "already exists")
        self.assertEqual(Chore.objects.filter(household=self.household).count(), 1)

    def test_cannot_edit_other_households_chore(self):
        stranger = make_user("stranger", CustomUser.Role.ADMIN)
        other_house = create_household(stranger, "Other House")
        with at(MONDAY):
            foreign = create_chore(other_house, "Foreign", "")
        self.client.force_login(self.boss)
        response = self.client.get(reverse("chore_edit", args=[foreign.pk]))
        self.assertEqual(response.status_code, 404)
