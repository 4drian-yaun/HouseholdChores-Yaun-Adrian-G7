from django import forms

from .models import Chore


class ChoreForm(forms.ModelForm):
    class Meta:
        model = Chore
        fields = ("name", "description")
        labels = {"name": "Chore name", "description": "Details (optional)"}
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "e.g. Take out trash"}),
            "description": forms.TextInput(
                attrs={"placeholder": "e.g. Empty kitchen & bathroom bins before Sunday evening"}
            ),
        }

    def __init__(self, *args, household, **kwargs):
        super().__init__(*args, **kwargs)
        self.household = household

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if not name:
            raise forms.ValidationError("Chore name is required.")
        clash = Chore.objects.filter(household=self.household, is_active=True, name__iexact=name)
        if self.instance.pk:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise forms.ValidationError("An active chore with that name already exists.")
        return name

    def clean_description(self):
        return self.cleaned_data["description"].strip()
