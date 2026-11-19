from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect

from chores.services import sync_household

from .models import HouseholdMember
from .utils import get_membership


class HouseholdContextMixin(LoginRequiredMixin):
    admin_only = False

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        membership = get_membership(request.user)
        if membership is None:
            messages.error(request, "You are not part of a household yet.")
            return redirect("dashboard")
        if self.admin_only and membership.role != HouseholdMember.Role.ADMIN:
            messages.error(request, "Only a Household Admin can do that.")
            return redirect("dashboard")
        request.membership = membership
        request.household = membership.household
        sync_household(membership.household)
        return super().dispatch(request, *args, **kwargs)
