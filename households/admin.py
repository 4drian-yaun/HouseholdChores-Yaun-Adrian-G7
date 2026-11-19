from django.contrib import admin

from .models import Household, HouseholdMember


@admin.register(Household)
class HouseholdAdmin(admin.ModelAdmin):
    list_display = ["name", "created_by", "created_at"]


@admin.register(HouseholdMember)
class HouseholdMemberAdmin(admin.ModelAdmin):
    list_display = ["display_name", "household", "user", "role", "rotation_order", "is_active"]
    list_filter = ["role", "is_active", "household"]
