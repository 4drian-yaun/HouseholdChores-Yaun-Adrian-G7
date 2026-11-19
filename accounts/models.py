from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    email = models.EmailField("email address", unique=True)
    contact_number = models.CharField(max_length=20, blank=True)

    REQUIRED_FIELDS = ["email"]

    @property
    def full_name(self):
        return self.get_full_name() or self.username

    def save(self, *args, **kwargs):
        self.email = self.email.strip().lower()
        super().save(*args, **kwargs)
