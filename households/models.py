from django.conf import settings
from django.db import models
from django.db.models import Q


class Household(models.Model):
    name = models.CharField(max_length=100)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="households_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class HouseholdMember(models.Model):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Household Admin"
        MEMBER = "MEMBER", "Household Member"

    household = models.ForeignKey(Household, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="member_profiles",
    )
    display_name = models.CharField(max_length=100)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.MEMBER)
    rotation_order = models.PositiveIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_active", "rotation_order", "display_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=Q(is_active=True),
                name="unique_active_profile_per_user",
            ),
            models.UniqueConstraint(
                fields=["household", "rotation_order"],
                name="unique_rotation_order_per_household",
            ),
            models.CheckConstraint(
                condition=Q(rotation_order__isnull=True) | Q(rotation_order__gte=1),
                name="rotation_order_positive",
            ),
            models.CheckConstraint(
                condition=Q(role__in=["ADMIN", "MEMBER"]),
                name="member_role_valid",
            ),
        ]

    @property
    def has_account(self):
        return self.user_id is not None

    def __str__(self):
        return f"{self.display_name} ({self.household})"
