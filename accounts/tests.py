from django.test import TestCase
from django.urls import reverse

from .models import CustomUser


def make_user(username, role=CustomUser.Role.MEMBER, email=None, password="StrongPass123"):
    return CustomUser.objects.create_user(
        username=username,
        email=email or f"{username}@example.com",
        password=password,
        first_name=username.title(),
        last_name="Tester",
        role=role,
    )


class RegistrationTests(TestCase):
    def payload(self, **overrides):
        data = {
            "username": "newuser",
            "first_name": "New",
            "last_name": "User",
            "email": "new@example.com",
            "contact_number": "",
            "role": "MEMBER",
            "password1": "StrongPass123",
            "password2": "StrongPass123",
        }
        data.update(overrides)
        return data

    def test_register_success_hashes_password(self):
        response = self.client.post(reverse("signup"), self.payload(), follow=True)
        self.assertRedirects(response, reverse("login"))
        self.assertContains(response, "Account created successfully")
        user = CustomUser.objects.get(username="newuser")
        self.assertNotEqual(user.password, "StrongPass123")
        self.assertTrue(user.password.startswith("pbkdf2_"))

    def test_password_mismatch(self):
        response = self.client.post(reverse("signup"), self.payload(password2="Different123"))
        self.assertEqual(CustomUser.objects.count(), 0)
        self.assertContains(response, "Registration failed")

    def test_short_password_rejected(self):
        self.client.post(reverse("signup"), self.payload(password1="Ab1", password2="Ab1"))
        self.assertEqual(CustomUser.objects.count(), 0)

    def test_invalid_email(self):
        self.client.post(reverse("signup"), self.payload(email="not-an-email"))
        self.assertEqual(CustomUser.objects.count(), 0)

    def test_required_fields(self):
        self.client.post(reverse("signup"), self.payload(first_name="", last_name="", email=""))
        self.assertEqual(CustomUser.objects.count(), 0)

    def test_duplicate_username(self):
        make_user("newuser")
        self.client.post(reverse("signup"), self.payload())
        self.assertEqual(CustomUser.objects.count(), 1)

    def test_duplicate_email_case_insensitive(self):
        make_user("other", email="new@example.com")
        response = self.client.post(reverse("signup"), self.payload(email="NEW@example.com"))
        self.assertEqual(CustomUser.objects.count(), 1)
        self.assertContains(response, "already exists")


class LoginLogoutTests(TestCase):
    def setUp(self):
        self.admin = make_user("boss", CustomUser.Role.ADMIN)
        self.member = make_user("roomie")

    def test_admin_login_goes_to_admin_dashboard(self):
        response = self.client.post(reverse("login"), {"username": "boss", "password": "StrongPass123"}, follow=True)
        self.assertRedirects(response, reverse("admin_dashboard"))

    def test_member_login_goes_to_member_dashboard(self):
        response = self.client.post(reverse("login"), {"username": "roomie", "password": "StrongPass123"}, follow=True)
        self.assertRedirects(response, reverse("member_dashboard"))

    def test_invalid_credentials(self):
        response = self.client.post(reverse("login"), {"username": "boss", "password": "wrong"})
        self.assertContains(response, "Invalid username or password")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout_ends_session(self):
        self.client.force_login(self.member)
        response = self.client.post(reverse("logout"))
        self.assertRedirects(response, reverse("login"))
        self.assertNotIn("_auth_user_id", self.client.session)


class AccessControlTests(TestCase):
    def setUp(self):
        self.admin = make_user("boss", CustomUser.Role.ADMIN)
        self.member = make_user("roomie")

    def test_anonymous_redirected_to_login(self):
        for name in ["dashboard", "admin_dashboard", "member_dashboard", "profile", "password_change"]:
            url = reverse(name)
            response = self.client.get(url)
            self.assertRedirects(response, f"{reverse('login')}?next={url}")

    def test_member_cannot_open_admin_dashboard(self):
        self.client.force_login(self.member)
        response = self.client.get(reverse("admin_dashboard"), follow=True)
        self.assertRedirects(response, reverse("member_dashboard"))
        self.assertContains(response, "do not have access")

    def test_admin_cannot_open_member_dashboard(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("member_dashboard"), follow=True)
        self.assertRedirects(response, reverse("admin_dashboard"))

    def test_each_role_sees_own_dashboard(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("admin_dashboard")).status_code, 200)
        self.client.force_login(self.member)
        self.assertEqual(self.client.get(reverse("member_dashboard")).status_code, 200)

    def test_logged_in_user_redirected_from_signup_and_login(self):
        self.client.force_login(self.member)
        self.assertRedirects(self.client.get(reverse("signup")), reverse("dashboard"), fetch_redirect_response=False)
        self.assertEqual(self.client.get(reverse("login")).status_code, 302)

    def test_superuser_gets_admin_role(self):
        user = CustomUser.objects.create_superuser("root", "root@example.com", "StrongPass123")
        self.assertEqual(user.role, CustomUser.Role.ADMIN)


class ProfileTests(TestCase):
    def setUp(self):
        self.user = make_user("roomie")
        self.other = make_user("other")
        self.client.force_login(self.user)

    def test_profile_shows_own_data(self):
        response = self.client.get(reverse("profile"))
        self.assertContains(response, "roomie@example.com")
        self.assertNotContains(response, "other@example.com")

    def test_update_profile(self):
        response = self.client.post(
            reverse("profile"),
            {"first_name": "Rm", "last_name": "Mate", "email": "rm@example.com", "contact_number": "09171234567"},
            follow=True,
        )
        self.assertContains(response, "Your profile was updated")
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "rm@example.com")
        self.assertEqual(self.user.contact_number, "09171234567")

    def test_cannot_use_other_users_email(self):
        self.client.post(
            reverse("profile"),
            {"first_name": "Rm", "last_name": "Mate", "email": "other@example.com", "contact_number": ""},
        )
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "roomie@example.com")

    def test_profile_post_cannot_change_role_or_other_user(self):
        self.client.post(
            reverse("profile"),
            {"first_name": "Rm", "last_name": "Mate", "email": "roomie@example.com", "contact_number": "", "role": "ADMIN"},
        )
        self.user.refresh_from_db()
        self.other.refresh_from_db()
        self.assertEqual(self.user.role, CustomUser.Role.MEMBER)
        self.assertEqual(self.other.first_name, "Other")

    def test_change_password(self):
        response = self.client.post(
            reverse("password_change"),
            {"old_password": "StrongPass123", "new_password1": "BrandNewPass456", "new_password2": "BrandNewPass456"},
            follow=True,
        )
        self.assertContains(response, "Your password was changed")
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("BrandNewPass456"))

    def test_change_password_wrong_current(self):
        self.client.post(
            reverse("password_change"),
            {"old_password": "nope", "new_password1": "BrandNewPass456", "new_password2": "BrandNewPass456"},
        )
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("StrongPass123"))
