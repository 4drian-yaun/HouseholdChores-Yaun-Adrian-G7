from django.urls import path

from .views import DashboardLegacyRedirectView, DashboardView, HomeView

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("dashboard/admin/", DashboardLegacyRedirectView.as_view(), name="admin_dashboard"),
    path("dashboard/member/", DashboardLegacyRedirectView.as_view(), name="member_dashboard"),
]
