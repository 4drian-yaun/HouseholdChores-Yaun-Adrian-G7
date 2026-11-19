from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views import View
from django.views.generic import TemplateView

from chores.services import sync_household, week_overview
from households.forms import HouseholdForm
from households.models import HouseholdMember
from households.utils import get_membership


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
        context["household"] = household
        context["overview"] = week_overview(household, membership)
        context["member_count"] = household.members.filter(is_active=True).count()
        context["chore_count"] = household.chores.filter(is_active=True).count()
        context["is_admin"] = membership.role == HouseholdMember.Role.ADMIN
        return context


class DashboardLegacyRedirectView(LoginRequiredMixin, View):
    def get(self, request):
        return redirect("dashboard")
