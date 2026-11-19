from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ["username", "first_name", "last_name", "email", "is_staff"]
    fieldsets = UserAdmin.fieldsets + (("Contact", {"fields": ("contact_number",)}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("Contact", {"fields": ("email", "contact_number")}),)
