from datetime import date

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import FormView, TemplateView

from households.mixins import HouseholdContextMixin
from households.models import HouseholdMember

from .forms import ChoreForm
from .models import Assignment, Chore
from .services import (
    CompletionError,
    active_members,
    analytics,
    complete_assignment,
    completion_block_reason,
    create_chore,
    current_week_start,
    next_in_rotation,
    past_weeks,
    percent,
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
        members = active_members(household)
        chores = list(household.chores.all())
        for chore in chores:
            chore.current = current.get(chore.id)
            if chore.is_active and chore.current and members:
                chore.next_member = next_in_rotation(chore.current.member, members, chore)
            else:
                chore.next_member = None
        context["active_chores"] = [c for c in chores if c.is_active]
        context["retired_chores"] = [c for c in chores if not c.is_active]
        return context


class ChoreDetailView(HouseholdContextMixin, TemplateView):
    template_name = "chores/chore_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        household = self.request.household
        membership = self.request.membership
        chore = get_object_or_404(Chore, pk=self.kwargs["pk"], household=household)
        week = current_week_start()
        assignments = list(
            chore.assignments.filter(member__is_active=True)
            .select_related("member")
            .order_by("-week_start_date")
        )
        current = None
        for assignment in assignments:
            assignment.can_complete = completion_block_reason(membership, assignment) is None
            assignment.is_mine = assignment.member_id == membership.id
            if assignment.week_start_date == week:
                current = assignment

        done = sum(1 for a in assignments if a.status == Assignment.Status.COMPLETED)
        missed = sum(1 for a in assignments if a.status == Assignment.Status.MISSED)
        closed_total = done + missed
        members = active_members(household)
        next_member = (
            next_in_rotation(current.member, members, chore)
            if chore.is_active and current and members
            else None
        )

        context.update(
            chore=chore,
            assignments=assignments,
            current=current,
            next_member=next_member,
            done=done,
            missed=missed,
            closed_total=closed_total,
            rate=percent(done, closed_total),
            is_admin=membership.role == HouseholdMember.Role.ADMIN,
        )
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

        member_id = None
        raw_member = self.request.GET.get("member", "")
        if raw_member.isdigit():
            parsed_id = int(raw_member)
            if household.members.filter(pk=parsed_id, is_active=True).exists():
                member_id = parsed_id

        prev_week = None
        next_week = None
        if selected and weeks:
            idx = weeks.index(selected)
            if idx + 1 < len(weeks):
                prev_week = weeks[idx + 1]
            if idx - 1 >= 0:
                next_week = weeks[idx - 1]

        context["weeks"] = weeks
        context["selected"] = selected
        context["prev_week"] = prev_week
        context["next_week"] = next_week
        context["members"] = list(household.members.filter(is_active=True).order_by("display_name"))
        context["selected_member"] = member_id
        if selected:
            context["overview"] = week_overview(
                household, self.request.membership, selected, member_id=member_id
            )
        return context


class AnalyticsView(HouseholdContextMixin, TemplateView):
    template_name = "chores/analytics.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        household = self.request.household
        membership = self.request.membership
        this_week = week_overview(household, membership)
        mine = Assignment.objects.filter(member=membership)
        my_done = mine.filter(status=Assignment.Status.COMPLETED).count()
        my_missed = mine.filter(status=Assignment.Status.MISSED).count()
        my_pending = mine.filter(
            week_start_date=this_week["week_start"], status=Assignment.Status.PENDING
        ).count()
        my_closed = my_done + my_missed
        member_count = household.members.filter(is_active=True).count()
        chore_count = household.chores.filter(is_active=True).count()

        context["stats"] = analytics(household)
        context["this_week"] = this_week
        context["current_pending"] = this_week["pending"]
        context["member_count"] = member_count
        context["chore_count"] = chore_count
        context["my_stats"] = {
            "done": my_done,
            "missed": my_missed,
            "pending": my_pending,
            "closed": my_closed,
            "rate": percent(my_done, my_closed),
            "rotation_order": membership.rotation_order,
        }
        return context
