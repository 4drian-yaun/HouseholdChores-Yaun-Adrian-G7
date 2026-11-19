from datetime import date

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import FormView, TemplateView

from households.mixins import HouseholdContextMixin

from .forms import ChoreForm
from .models import Assignment, Chore
from .services import (
    CompletionError,
    analytics,
    complete_assignment,
    create_chore,
    current_week_start,
    past_weeks,
    retire_chore,
    week_overview,
)


class ChoreListView(HouseholdContextMixin, TemplateView):
    admin_only = True
    template_name = "chores/chore_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        household = self.request.household
        week = current_week_start()
        current = {
            a.chore_id: a
            for a in Assignment.objects.filter(
                chore__household=household, week_start_date=week
            ).select_related("member")
        }
        chores = list(household.chores.all())
        for chore in chores:
            chore.current = current.get(chore.id)
        context["active_chores"] = [c for c in chores if c.is_active]
        context["retired_chores"] = [c for c in chores if not c.is_active]
        return context


class ChoreFormMixin(HouseholdContextMixin):
    admin_only = True
    form_class = ChoreForm
    template_name = "chores/chore_form.html"
    success_url = reverse_lazy("chore_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["household"] = self.request.household
        return kwargs


class ChoreCreateView(ChoreFormMixin, FormView):
    def form_valid(self, form):
        chore = create_chore(
            self.request.household, form.cleaned_data["name"], form.cleaned_data["description"]
        )
        messages.success(self.request, f'"{chore.name}" was added and assigned for this week.')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Chore not saved. Please fix the errors below.")
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(heading="Add a chore", submit_label="Add chore")
        return context


class ChoreEditView(ChoreFormMixin, FormView):
    def get_chore(self):
        return get_object_or_404(
            Chore, pk=self.kwargs["pk"], household=self.request.household, is_active=True
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.get_chore()
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Chore updated.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Chore not saved. Please fix the errors below.")
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(heading="Edit chore", submit_label="Save changes")
        return context


class ChoreRetireView(HouseholdContextMixin, TemplateView):
    admin_only = True
    template_name = "chores/chore_confirm_retire.html"

    def get_chore(self, pk):
        return get_object_or_404(Chore, pk=pk, household=self.request.household, is_active=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["chore"] = self.get_chore(kwargs["pk"])
        return context

    def post(self, request, pk):
        chore = self.get_chore(pk)
        retire_chore(chore)
        messages.success(request, f'"{chore.name}" was retired. Its history is kept.')
        return redirect("chore_list")


class CompleteAssignmentView(HouseholdContextMixin, View):
    http_method_names = ["post"]

    def post(self, request, pk):
        assignment = get_object_or_404(
            Assignment.objects.select_related("chore", "member"),
            pk=pk,
            chore__household=request.household,
        )
        try:
            complete_assignment(request.membership, assignment)
        except CompletionError as error:
            messages.error(request, str(error))
        else:
            messages.success(request, f'"{assignment.chore.name}" marked as done.')
        return redirect("dashboard")


class HistoryView(HouseholdContextMixin, TemplateView):
    template_name = "chores/history.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        household = self.request.household
        weeks = past_weeks(household)
        selected = None
        raw = self.request.GET.get("week", "")
        if raw:
            try:
                parsed = date.fromisoformat(raw)
            except ValueError:
                parsed = None
            if parsed in weeks:
                selected = parsed
        if selected is None and weeks:
            selected = weeks[0]
        context["weeks"] = weeks
        context["selected"] = selected
        if selected:
            context["overview"] = week_overview(household, self.request.membership, selected)
        return context


class AnalyticsView(HouseholdContextMixin, TemplateView):
    template_name = "chores/analytics.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["stats"] = analytics(self.request.household)
        context["current_pending"] = week_overview(
            self.request.household, self.request.membership
        )["pending"]
        return context
