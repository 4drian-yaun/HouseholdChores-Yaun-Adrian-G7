from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import FormView, TemplateView

from .forms import HouseholdForm, MemberForm
from .mixins import HouseholdContextMixin
from .models import HouseholdMember
from .services import (
    MemberError,
    add_member,
    create_household,
    leave_household,
    move_member,
    remove_member,
    update_member,
)
from .utils import get_membership


class CreateHouseholdView(LoginRequiredMixin, View):
    http_method_names = ["post"]

    def post(self, request):
        if get_membership(request.user) is not None:
            messages.error(request, "You already belong to a household.")
            return redirect("dashboard")
        form = HouseholdForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Please enter a household name.")
            return redirect("dashboard")
        household = create_household(request.user, form.cleaned_data["name"])
        messages.success(
            request, f'Household "{household.name}" created. Add your members and chores next.'
        )
        return redirect("dashboard")


class HouseholdEditView(HouseholdContextMixin, FormView):
    admin_only = True
    form_class = HouseholdForm
    template_name = "households/household_form.html"
    success_url = reverse_lazy("dashboard")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.request.household
        return kwargs

    def form_valid(self, form):
        household = form.save()
        messages.success(self.request, f'Household renamed to "{household.name}".')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Household name not saved. Please fix the errors below.")
        return super().form_invalid(form)


class LeaveHouseholdView(HouseholdContextMixin, TemplateView):
    template_name = "households/household_confirm_leave.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        membership = self.request.membership
        is_sole_admin = (
            membership.role == HouseholdMember.Role.ADMIN
            and not self.request.household.members.filter(
                is_active=True, role=HouseholdMember.Role.ADMIN
            )
            .exclude(pk=membership.pk)
            .exists()
        )
        context["is_sole_admin"] = is_sole_admin
        return context

    def post(self, request):
        household_name = request.household.name
        try:
            reassigned = leave_household(request.membership)
        except MemberError as error:
            messages.error(request, str(error))
            return redirect("household_leave")
        messages.success(request, f'You have left "{household_name}".')
        if reassigned:
            messages.info(request, f"{reassigned} pending chore(s) were handed to other members.")
        return redirect("dashboard")


class MemberListView(HouseholdContextMixin, TemplateView):
    admin_only = True
    template_name = "households/member_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        members = self.request.household.members.select_related("user")
        context["active_members"] = [m for m in members if m.is_active]
        context["former_members"] = [m for m in members if not m.is_active]
        context["last_order"] = len(context["active_members"])
        return context


class MemberFormMixin(HouseholdContextMixin):
    admin_only = True
    form_class = MemberForm
    template_name = "households/member_form.html"
    success_url = reverse_lazy("member_list")
    member = None

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["household"] = self.request.household
        kwargs["member"] = self.member
        return kwargs


class MemberAddView(MemberFormMixin, FormView):
    def form_valid(self, form):
        member, moved = add_member(
            self.request.household,
            form.cleaned_data["display_name"],
            form.cleaned_data["username"],
            form.cleaned_data["role"],
        )
        messages.success(self.request, f"{member.display_name} was added to the household.")
        if moved:
            messages.info(
                self.request,
                f'{member.display_name} took over "{moved.chore.name}" for this week.',
            )
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Member not saved. Please fix the errors below.")
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(heading="Add a member", submit_label="Add member")
        return context


class MemberEditView(MemberFormMixin, FormView):
    def get_form_kwargs(self):
        self.member = get_object_or_404(
            HouseholdMember.objects.select_related("user"),
            pk=self.kwargs["pk"],
            household=self.request.household,
            is_active=True,
        )
        return super().get_form_kwargs()

    def form_valid(self, form):
        try:
            update_member(
                self.member,
                form.cleaned_data["display_name"],
                form.cleaned_data["username"],
                form.cleaned_data["role"],
            )
        except MemberError as error:
            messages.error(self.request, str(error))
            return self.form_invalid(form)
        messages.success(self.request, "Member updated.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Member not saved. Please fix the errors below.")
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(heading="Edit member", submit_label="Save changes", member=self.member)
        return context


class MemberActionMixin(HouseholdContextMixin):
    admin_only = True

    def get_member(self, pk):
        return get_object_or_404(
            HouseholdMember, pk=pk, household=self.request.household, is_active=True
        )


class MemberMoveView(MemberActionMixin, View):
    http_method_names = ["post"]

    def post(self, request, pk, direction):
        member = self.get_member(pk)
        if direction not in ("up", "down"):
            raise Http404
        move_member(member, direction)
        return redirect("member_list")


class MemberRemoveView(MemberActionMixin, TemplateView):
    template_name = "households/member_confirm_remove.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["member"] = self.get_member(kwargs["pk"])
        return context

    def post(self, request, pk):
        member = self.get_member(pk)
        try:
            reassigned = remove_member(member, request.membership)
        except MemberError as error:
            messages.error(request, str(error))
            return redirect("member_list")
        messages.success(request, f"{member.display_name} was removed from the household.")
        if reassigned:
            messages.info(request, f"{reassigned} pending chore(s) were handed to other members.")
        return redirect("member_list")
