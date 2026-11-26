from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import CustomUser


class CustomUserCreationForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={"placeholder": "e.g. Alex", "autocomplete": "given-name"}),
    )
    last_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={"placeholder": "e.g. Rivera", "autocomplete": "family-name"}),
    )
    email = forms.EmailField(
        max_length=254,
        required=True,
        widget=forms.EmailInput(
            attrs={"placeholder": "alex.rivera@gmail.com", "autocomplete": "email"}
        ),
    )
    contact_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(
            attrs={
                "type": "tel",
                "inputmode": "tel",
                "placeholder": "0917 123 4567",
                "autocomplete": "tel",
                "data-phone-mask": "true",
            }
        ),
    )

    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ("username", "first_name", "last_name", "email", "contact_number")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update(
            {"placeholder": "e.g. alex_rivera", "autocomplete": "username"}
        )
        self.fields["password1"].widget.attrs.update(
            {"placeholder": "At least 8 characters", "autocomplete": "new-password"}
        )
        self.fields["password2"].widget.attrs.update(
            {"placeholder": "Re-enter your password", "autocomplete": "new-password"}
        )

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if CustomUser.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("A user with that username already exists.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if CustomUser.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email


class CustomAuthenticationForm(AuthenticationForm):
    error_messages = {
        "invalid_login": "Invalid username or password. Please try again.",
        "inactive": "This account is inactive.",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update(
            {"placeholder": "e.g. alex_rivera", "autocomplete": "username"}
        )
        self.fields["password"].widget.attrs.update(
            {"placeholder": "Enter your password", "autocomplete": "current-password"}
        )


class ProfileForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={"placeholder": "e.g. Alex", "autocomplete": "given-name"}),
    )
    last_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={"placeholder": "e.g. Rivera", "autocomplete": "family-name"}),
    )
    email = forms.EmailField(
        max_length=254,
        required=True,
        widget=forms.EmailInput(
            attrs={"placeholder": "alex.rivera@gmail.com", "autocomplete": "email"}
        ),
    )

    class Meta:
        model = CustomUser
        fields = ("first_name", "last_name", "email", "contact_number")
        widgets = {
            "contact_number": forms.TextInput(
                attrs={
                    "type": "tel",
                    "inputmode": "tel",
                    "placeholder": "0917 123 4567",
                    "autocomplete": "tel",
                    "data-phone-mask": "true",
                }
            ),
        }

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if CustomUser.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email


class AccountDeleteForm(forms.Form):
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"placeholder": "Enter your current password", "autocomplete": "current-password"}
        ),
        label="Enter your password to confirm",
        help_text="For your security, please enter your current password to permanently delete your account.",
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if not self.user or not self.user.check_password(password):
            raise forms.ValidationError("Incorrect password. Please try again.")
        return password
