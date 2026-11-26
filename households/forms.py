from django import forms

from accounts.models import CustomUser

from .models import Household, HouseholdMember


class HouseholdForm(forms.ModelForm):
    class Meta:
        model = Household
        fields = ("name",)
        labels = {"name": "Household name"}
        widgets = {
            "name": forms.TextInput(
                attrs={"placeholder": "e.g. Apartment 4B or Yaun Family", "autocomplete": "organization"}
            ),
        }

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if not name:
            raise forms.ValidationError("A household must have a name.")
        return name


class MemberForm(forms.Form):
    display_name = forms.CharField(
        max_length=100,
        label="Display name",
        widget=forms.TextInput(attrs={"placeholder": "e.g. Sam Cruz", "autocomplete": "name"}),
    )
    username = forms.CharField(
        max_length=150,
        required=False,
        label="Linked account username",
        help_text="Optional. Enter the username of a registered account so this person can log in. Leave blank for someone without an account.",
        widget=forms.TextInput(attrs={"placeholder": "e.g. sam_cruz", "autocomplete": "off"}),
    )
    role = forms.ChoiceField(
        choices=HouseholdMember.Role.choices,
        initial=HouseholdMember.Role.MEMBER,
        label="Household role",
    )

    def __init__(self, *args, household, member=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.household = household
        self.member = member
        if member is not None:
            self.initial.setdefault("display_name", member.display_name)
            self.initial.setdefault("username", member.user.username if member.user else "")
            self.initial.setdefault("role", member.role)
            if member.role == HouseholdMember.Role.ADMIN and member.user:
                self.fields["username"].help_text = "Enter a different username to transfer this profile, or keep as is."

    def clean_display_name(self):
        name = self.cleaned_data["display_name"].strip()
        if not name:
            raise forms.ValidationError("Display name is required.")
        return name

    def clean_username(self):
        value = (self.cleaned_data.get("username") or "").strip().lstrip("@")
        if not value:
            return None
        user = CustomUser.objects.filter(username__iexact=value).first()
        if user is None:
            raise forms.ValidationError("No account has that username. Ask them to sign up first.")
        taken = HouseholdMember.objects.filter(user=user, is_active=True)
        if self.member is not None:
            taken = taken.exclude(pk=self.member.pk)
        if taken.exists():
            raise forms.ValidationError("That account is already linked to an active member profile.")
        return user

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get("role")
        user = cleaned_data.get("username")
        if role == HouseholdMember.Role.ADMIN and not user:
            self.add_error("role", "A member must have a linked user account to be a Household Admin.")
        if (
            self.member
            and self.member.role == HouseholdMember.Role.ADMIN
            and role != HouseholdMember.Role.ADMIN
        ):
            admins = (
                self.household.members.filter(is_active=True, role=HouseholdMember.Role.ADMIN)
                .exclude(pk=self.member.pk)
                .count()
            )
            if admins < 1:
                self.add_error(
                    "role", "A household must have at least one active Household Admin at all times."
                )
        return cleaned_data
