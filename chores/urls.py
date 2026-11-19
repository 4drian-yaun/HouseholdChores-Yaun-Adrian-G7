from django.urls import path

from .views import (
    AnalyticsView,
    ChoreCreateView,
    ChoreEditView,
    ChoreListView,
    ChoreRetireView,
    CompleteAssignmentView,
    HistoryView,
)

urlpatterns = [
    path("chores/", ChoreListView.as_view(), name="chore_list"),
    path("chores/add/", ChoreCreateView.as_view(), name="chore_add"),
    path("chores/<int:pk>/edit/", ChoreEditView.as_view(), name="chore_edit"),
    path("chores/<int:pk>/retire/", ChoreRetireView.as_view(), name="chore_retire"),
    path("assignments/<int:pk>/complete/", CompleteAssignmentView.as_view(), name="assignment_complete"),
    path("history/", HistoryView.as_view(), name="history"),
    path("analytics/", AnalyticsView.as_view(), name="analytics"),
]
