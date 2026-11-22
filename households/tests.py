from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser

from .models import HouseholdMember
from .services import MemberError, add_member, create_household, move_member, remove_member


def make_user(username):
    return CustomUser.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="StrongPass123",
        first_name=username.title(),
        last_name="Tester",
    )


class MemberTests(TestCase):
    def setUp(self):
        self.boss = make_user("boss")
        self.ana = make_user("ana")
        self.household = create_household(self.boss, "Casa")
        self.boss_member = self.household.members.get(user=self.boss)

    def orders(self):
        return list(
            self.household.members.filter(is_active=True)
            .order_by("rotation_order")
            .values_list("display_name", "rotation_order")
        )

    def test_creator_becomes_admin_first_in_rotation(self):
        self.assertEqual(self.boss_member.role, HouseholdMember.Role.ADMIN)
        self.assertEqual(self.boss_member.rotation_order, 1)

    def test_members_get_sequential_unique_orders(self):
        add_member(self.household, "Ana", self.ana)
        add_member(self.household, "Cam", None)
        self.assertEqual([o for _, o in self.orders()], [1, 2, 3])

    def test_profile_without_account_has_no_login(self):
        member, _ = add_member(self.household, "Cam", None)
        self.assertFalse(member.has_account)

    def test_move_reorders(self):
        ana, _ = add_member(self.household, "Ana", self.ana)
        add_member(self.household, "Cam", None)
        move_member(ana, "up")
        self.assertEqual([n for n, _ in self.orders()], ["Ana", self.boss_member.display_name, "Cam"])
        move_member(ana, "up")
        self.assertEqual(self.orders()[0][0], "Ana")

    def test_remove_marks_inactive_and_compacts_order(self):
        ana, _ = add_member(self.household, "Ana", self.ana)
        add_member(self.household, "Cam", None)
        remove_member(ana, self.boss_member)
        ana.refresh_from_db()
        self.assertFalse(ana.is_active)
        self.assertIsNone(ana.rotation_order)
        self.assertEqual([o for _, o in self.orders()], [1, 2])

    def test_cannot_remove_yourself(self):
        with self.assertRaises(MemberError):
            remove_member(self.boss_member, self.boss_member)

    def test_cannot_remove_last_admin(self):
        ana, _ = add_member(self.household, "Ana", self.ana)
        with self.assertRaises(MemberError):
            remove_member(self.boss_member, ana)

    def test_can_remove_an_admin_when_another_remains(self):
        second = make_user("second")
        second_member, _ = add_member(
            self.household, "Second", second, role=HouseholdMember.Role.ADMIN
        )
        remove_member(self.boss_member, second_member)
        self.boss_member.refresh_from_db()
        self.assertFalse(self.boss_member.is_active)

    def test_account_linked_to_one_active_profile_only(self):
        add_member(self.household, "Ana", self.ana)
        other_boss = make_user("other")
        other_house = create_household(other_boss, "Rival")
        self.client.force_login(other_boss)
        response = self.client.post(
            reverse("member_add"),
            {"display_name": "Ana", "username": "ana", "role": HouseholdMember.Role.MEMBER},
        )
        self.assertContains(response, "already linked")
        self.assertEqual(other_house.members.count(), 1)

    def test_removed_account_can_join_again(self):
        ana, _ = add_member(self.household, "Ana", self.ana)
        remove_member(ana, self.boss_member)
        again, _ = add_member(self.household, "Ana", self.ana)
        self.assertTrue(again.is_active)

    def test_unknown_username_rejected(self):
        self.client.force_login(self.boss)
        response = self.client.post(
            reverse("member_add"),
            {"display_name": "Ghost", "username": "nobody", "role": HouseholdMember.Role.MEMBER},
        )
        self.assertContains(response, "No account has that username")

    def test_admin_views_add_edit_remove_flow(self):
        self.client.force_login(self.boss)
        response = self.client.post(
            reverse("member_add"),
            {"display_name": "Ana", "username": "ANA", "role": HouseholdMember.Role.MEMBER},
            follow=True,
        )
        self.assertContains(response, "was added")
        member = HouseholdMember.objects.get(display_name="Ana")
        self.assertEqual(member.user, self.ana)
        self.assertEqual(member.role, HouseholdMember.Role.MEMBER)

        # Promote Ana to ADMIN
        self.client.post(
            reverse("member_edit", args=[member.pk]),
            {"display_name": "Anabel", "username": "ana", "role": HouseholdMember.Role.ADMIN},
        )
        member.refresh_from_db()
        self.assertEqual(member.display_name, "Anabel")
        self.assertEqual(member.role, HouseholdMember.Role.ADMIN)

        self.assertEqual(
            self.client.get(reverse("member_remove", args=[member.pk])).status_code, 200
        )
        self.client.post(reverse("member_remove", args=[member.pk]))
        member.refresh_from_db()
        self.assertFalse(member.is_active)

    def test_member_account_cannot_manage_members(self):
        add_member(self.household, "Ana", self.ana)
        self.client.force_login(self.ana)
        for name in ("member_list", "member_add"):
            response = self.client.get(reverse(name), follow=True)
            self.assertContains(response, "Only a Household Admin")

    def test_anonymous_redirected_from_all_new_pages(self):
        for name in (
            "member_list",
            "member_add",
            "chore_list",
            "chore_add",
            "history",
            "analytics",
        ):
            url = reverse(name)
            self.assertRedirects(self.client.get(url), f"{reverse('login')}?next={url}")

    def test_cannot_touch_member_of_other_household(self):
        other_boss = make_user("other")
        create_household(other_boss, "Rival")
        self.client.force_login(other_boss)
        response = self.client.get(reverse("member_edit", args=[self.boss_member.pk]))
        self.assertEqual(response.status_code, 404)
        response = self.client.post(reverse("member_remove", args=[self.boss_member.pk]))
        self.assertEqual(response.status_code, 404)

    def test_admin_can_rename_household_and_member_cannot(self):
        add_member(self.household, "Ana", self.ana)
        self.client.force_login(self.ana)
        blocked = self.client.post(reverse("household_edit"), {"name": "Hacked"}, follow=True)
        self.assertContains(blocked, "Only a Household Admin")
        self.household.refresh_from_db()
        self.assertEqual(self.household.name, "Casa")

        self.client.force_login(self.boss)
        ok = self.client.post(reverse("household_edit"), {"name": "Casa Nueva"}, follow=True)
        self.assertContains(ok, "Casa Nueva")
        self.household.refresh_from_db()
        self.assertEqual(self.household.name, "Casa Nueva")

    def test_member_can_leave_household_and_sole_admin_cannot(self):
        ana_member, _ = add_member(self.household, "Ana", self.ana)
        self.client.force_login(self.boss)
        blocked = self.client.post(reverse("household_leave"), follow=True)
        self.assertContains(blocked, "only active Household Admin")
        self.boss_member.refresh_from_db()
        self.assertTrue(self.boss_member.is_active)

        self.client.force_login(self.ana)
        left = self.client.post(reverse("household_leave"), follow=True)
        self.assertContains(left, "You have left")
        ana_member.refresh_from_db()
        self.assertFalse(ana_member.is_active)
        self.assertIsNone(ana_member.rotation_order)

    def test_admin_can_leave_when_another_admin_exists(self):
        add_member(self.household, "Ana", self.ana, role=HouseholdMember.Role.ADMIN)
        self.client.force_login(self.boss)
        response = self.client.post(reverse("household_leave"), follow=True)
        self.assertContains(response, "You have left")
        self.boss_member.refresh_from_db()
        self.assertFalse(self.boss_member.is_active)
