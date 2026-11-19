from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views import View
from django.views.generic import TemplateView

from accounts.models import CustomUser
from chores.services import sync_household, week_overview
from households.forms import HouseholdForm
from households.utils import get_membership


class RoleRequiredMixin(LoginRequiredMixin):
    required_role = None

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user.role != self.required_role:
            messages.error(request, "You do not have access to that page.")
            return redirect("dashboard")
        return super().dispatch(request, *args, **kwargs)


class DashboardRedirectView(LoginRequiredMixin, View):
    def get(self, request):
        if request.user.role == CustomUser.Role.ADMIN:
            return redirect("admin_dashboard")
        return redirect("member_dashboard")


class HouseholdDashboardMixin(RoleRequiredMixin):
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
        return context


class AdminDashboardView(HouseholdDashboardMixin, TemplateView):
    template_name = "dashboard/admin_dashboard.html"
    required_role = CustomUser.Role.ADMIN


class MemberDashboardView(HouseholdDashboardMixin, TemplateView):
    template_name = "dashboard/member_dashboard.html"
    required_role = CustomUser.Role.MEMBER
