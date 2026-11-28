from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from chores.services import active_members, next_in_rotation, sync_household, week_overview
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
        members = active_members(household)
        my_pending = [
            a for a in overview["assignments"] if a.is_mine and a.status == "PENDING"
        ]
        my_done_count = sum(
            1 for a in overview["assignments"] if a.is_mine and a.status == "COMPLETED"
        )
        my_next_chores = []
        if members:
            for a in overview["assignments"]:
                if a.chore.is_active:
                    nxt = next_in_rotation(a.member, members, a.chore)
                    if nxt and nxt.id == membership.id:
                        my_next_chores.append(a.chore)

        today_idx = timezone.localdate().weekday()
        day_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        week_days = [
            {
                "label": day_labels[i],
                "is_past": i < today_idx,
                "is_today": i == today_idx,
            }
            for i in range(7)
        ]

        context["household"] = household
        context["overview"] = overview
        context["member_count"] = len(members)
        context["chore_count"] = household.chores.filter(is_active=True).count()
        context["my_pending"] = my_pending
        context["my_pending_count"] = len(my_pending)
        context["my_done_count"] = my_done_count
        context["my_next_chores"] = my_next_chores
        context["week_days"] = week_days
        context["is_admin"] = membership.role == HouseholdMember.Role.ADMIN
        return context


class DashboardLegacyRedirectView(LoginRequiredMixin, View):
    def get(self, request):
        return redirect("dashboard")
