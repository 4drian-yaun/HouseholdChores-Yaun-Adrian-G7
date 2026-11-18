from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Household Admin"
        MEMBER = "MEMBER", "Household Member"

    email = models.EmailField("email address", unique=True)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.MEMBER)
    contact_number = models.CharField(max_length=20, blank=True)

    REQUIRED_FIELDS = ["email"]

    @property
    def full_name(self):
        return self.get_full_name() or self.username

    @property
    def is_household_admin(self):
        return self.role == self.Role.ADMIN

    def save(self, *args, **kwargs):
        if self.is_superuser:
            self.role = self.Role.ADMIN
        self.email = self.email.strip().lower()
        super().save(*args, **kwargs)
