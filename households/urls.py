from django.urls import path

from .views import (
    CreateHouseholdView,
    MemberAddView,
    MemberEditView,
    MemberListView,
    MemberMoveView,
    MemberRemoveView,
)

urlpatterns = [
    path("household/create/", CreateHouseholdView.as_view(), name="household_create"),
    path("members/", MemberListView.as_view(), name="member_list"),
    path("members/add/", MemberAddView.as_view(), name="member_add"),
    path("members/<int:pk>/edit/", MemberEditView.as_view(), name="member_edit"),
    path("members/<int:pk>/move/<str:direction>/", MemberMoveView.as_view(), name="member_move"),
    path("members/<int:pk>/remove/", MemberRemoveView.as_view(), name="member_remove"),
]
