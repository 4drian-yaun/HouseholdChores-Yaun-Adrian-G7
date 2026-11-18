from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views import View
from django.views.generic import TemplateView

from accounts.models import CustomUser


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


class AdminDashboardView(RoleRequiredMixin, TemplateView):
    template_name = "dashboard/admin_dashboard.html"
    required_role = CustomUser.Role.ADMIN

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["account_count"] = CustomUser.objects.count()
        context["admin_count"] = CustomUser.objects.filter(role=CustomUser.Role.ADMIN).count()
        context["member_count"] = CustomUser.objects.filter(role=CustomUser.Role.MEMBER).count()
        return context


class MemberDashboardView(RoleRequiredMixin, TemplateView):
    template_name = "dashboard/member_dashboard.html"
    required_role = CustomUser.Role.MEMBER
