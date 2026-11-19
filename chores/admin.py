from django.contrib import admin

from .models import Assignment, Chore


@admin.register(Chore)
class ChoreAdmin(admin.ModelAdmin):
    list_display = ["name", "household", "is_active", "created_at"]
    list_filter = ["is_active", "household"]


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ["chore", "member", "week_start_date", "due_date", "status", "completed_at"]
    list_filter = ["status", "week_start_date"]
