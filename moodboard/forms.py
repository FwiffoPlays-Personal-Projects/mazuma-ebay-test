from django import forms
from .models import Moodboard, Image


class MoodboardForm(forms.ModelForm):
    class Meta:
        model = Moodboard
        fields = ["title", "manufacturer", "model_number", "stock_id", "description"]


class ImageForm(forms.ModelForm):
    class Meta:
        model = Image
        fields = ["image"]
        widgets = {
            "image": forms.ClearableFileInput(attrs={"multiple": True}),
        }

class ToggleListedForm(forms.Form):
    toggle = forms.BooleanField(required=False)