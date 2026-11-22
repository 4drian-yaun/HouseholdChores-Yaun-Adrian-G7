from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views import View
from django.views.generic import TemplateView

from chores.services import sync_household, week_overview
from households.forms import HouseholdForm
from households.models import HouseholdMember
from households.utils import get_membership


class HomeView(TemplateView):
    template_name = "dashboard/landing.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("dashboard")
        return super().dispatch(request, *args, **kwargs)


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        membership = get_membership(self.request.user)
        context["membership"] = membership
        if membership is None:
            context["household_form"] = HouseholdForm()
            return context
        household = membership.household
        sync_household(household)
        overview = week_overview(household, membership)
        context["household"] = household
        context["overview"] = overview
        context["member_count"] = household.members.filter(is_active=True).count()
        context["chore_count"] = household.chores.filter(is_active=True).count()
        context["my_pending_count"] = sum(
            1 for a in overview["assignments"] if a.is_mine and a.status == "PENDING"
        )
        context["is_admin"] = membership.role == HouseholdMember.Role.ADMIN
        return context


class DashboardLegacyRedirectView(LoginRequiredMixin, View):
    def get(self, request):
        return redirect("dashboard")
