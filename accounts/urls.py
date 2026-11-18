from django.contrib.auth.views import LogoutView
from django.urls import path

from .views import ChangePasswordView, CustomLoginView, ProfileView, SignUpView

urlpatterns = [
    path("signup/", SignUpView.as_view(), name="signup"),
    path("login/", CustomLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("password-change/", ChangePasswordView.as_view(), name="password_change"),
]
