from django.contrib import messages
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, FormView, UpdateView

from .forms import AccountDeleteForm, CustomAuthenticationForm, CustomUserCreationForm, ProfileForm
from .services import delete_user_account


class SignUpView(CreateView):
    form_class = CustomUserCreationForm
    template_name = "registration/signup.html"
    success_url = reverse_lazy("login")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("dashboard")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Account created successfully. You can now log in.")
        return response

    def form_invalid(self, form):
        messages.error(self.request, "Registration failed. Please fix the errors below.")
        return super().form_invalid(form)


class CustomLoginView(LoginView):
    authentication_form = CustomAuthenticationForm
    template_name = "registration/login.html"
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Welcome back, {form.get_user().full_name}!")
        return response

    def form_invalid(self, form):
        messages.error(self.request, "Login failed. Check your username and password.")
        return super().form_invalid(form)


class ProfileView(LoginRequiredMixin, UpdateView):
    form_class = ProfileForm
    template_name = "accounts/profile.html"
    success_url = reverse_lazy("profile")

    def get_object(self, queryset=None):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from chores.models import Assignment
        from households.models import HouseholdMember

        membership = (
            HouseholdMember.objects.select_related("household")
            .filter(user=self.request.user, is_active=True)
            .first()
        )
        my_stats = None
        recent_done = []
        if membership:
            mine = Assignment.objects.filter(member=membership)
            done = mine.filter(status=Assignment.Status.COMPLETED).count()
            missed = mine.filter(status=Assignment.Status.MISSED).count()
            pending = mine.filter(status=Assignment.Status.PENDING).count()
            closed = done + missed
            rate = round(done * 100 / closed) if closed else 0
            active_members = HouseholdMember.objects.filter(
                household=membership.household, is_active=True
            ).count()
            my_stats = {
                "done": done,
                "missed": missed,
                "pending": pending,
                "closed": closed,
                "rate": rate,
                "active_members": active_members,
            }
            recent_done = list(
                mine.filter(status=Assignment.Status.COMPLETED)
                .select_related("chore")
                .order_by("-completed_at", "-week_start_date")[:4]
            )
        context["my_stats"] = my_stats
        context["recent_done"] = recent_done
        return context

    def form_valid(self, form):
        messages.success(self.request, "Your profile was updated.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Profile not saved. Please fix the errors below.")
        return super().form_invalid(form)


class ChangePasswordView(LoginRequiredMixin, PasswordChangeView):
    template_name = "registration/password_change_form.html"
    success_url = reverse_lazy("profile")

    def form_valid(self, form):
        messages.success(self.request, "Your password was changed.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Password not changed. Please fix the errors below.")
        return super().form_invalid(form)


class AccountDeleteView(LoginRequiredMixin, FormView):
    template_name = "accounts/account_confirm_delete.html"
    form_class = AccountDeleteForm
    success_url = reverse_lazy("login")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        user = self.request.user
        delete_user_account(user)
        auth_logout(self.request)
        messages.success(self.request, "Your account has been permanently deleted.")
        return redirect(self.success_url)

    def form_invalid(self, form):
        messages.error(self.request, "Could not delete account. Please verify your password.")
        return super().form_invalid(form)
