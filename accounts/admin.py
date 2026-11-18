from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ["username", "first_name", "last_name", "email", "role", "is_staff"]
    list_filter = UserAdmin.list_filter + ("role",)
    fieldsets = UserAdmin.fieldsets + (("Household", {"fields": ("role", "contact_number")}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("Household", {"fields": ("email", "role", "contact_number")}),)
