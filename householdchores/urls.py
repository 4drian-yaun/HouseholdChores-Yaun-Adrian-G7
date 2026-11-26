from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "HouseholdChores Admin"
admin.site.site_title = "HouseholdChores Admin"
admin.site.index_title = "Site Administration"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("", include("households.urls")),
    path("", include("chores.urls")),
    path("", include("dashboard.urls")),
]
