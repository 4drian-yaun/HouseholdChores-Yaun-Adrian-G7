from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView

from .forms import CustomAuthenticationForm, CustomUserCreationForm, ProfileForm


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
