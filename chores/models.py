import datetime

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q, Value

from households.models import Household, HouseholdMember


class Chore(models.Model):
    household = models.ForeignKey(Household, on_delete=models.CASCADE, related_name="chores")
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["household", "name"],
                condition=Q(is_active=True),
                name="unique_active_chore_name_per_household",
            ),
        ]

    def __str__(self):
        return self.name


class Assignment(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        COMPLETED = "COMPLETED", "Completed"
        MISSED = "MISSED", "Missed"

    chore = models.ForeignKey(Chore, on_delete=models.CASCADE, related_name="assignments")
    member = models.ForeignKey(HouseholdMember, on_delete=models.PROTECT, related_name="assignments")
    week_start_date = models.DateField()
    due_date = models.DateField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["chore", "week_start_date"],
                name="one_assignment_per_chore_per_week",
            ),
            models.CheckConstraint(
                condition=Q(status__in=["PENDING", "COMPLETED", "MISSED"]),
                name="assignment_status_valid",
            ),
            models.CheckConstraint(
                condition=(
                    Q(status="COMPLETED", completed_at__isnull=False)
                    | (~Q(status="COMPLETED") & Q(completed_at__isnull=True))
                ),
                name="completed_at_matches_status",
            ),
            models.CheckConstraint(
                condition=Q(week_start_date__iso_week_day=1),
                name="week_start_is_monday",
            ),
            models.CheckConstraint(
                condition=Q(due_date=F("week_start_date") + Value(datetime.timedelta(days=6))),
                name="due_date_is_sunday",
            ),
        ]

    def clean(self):
        super().clean()
        if self.chore_id and self.member_id:
            if self.chore.household_id != self.member.household_id:
                raise ValidationError("Assigned member must belong to the same household as the chore.")
            if self._state.adding and not self.member.is_active:
                raise ValidationError("Chore can only be assigned to an active household member.")

    def save(self, *args, **kwargs):
        self.due_date = self.week_start_date + datetime.timedelta(days=6)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.chore} - {self.member} - {self.week_start_date}"
