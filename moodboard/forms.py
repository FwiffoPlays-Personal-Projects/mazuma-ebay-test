from django import forms
from .models import Moodboard, Image, Tag

class MoodboardForm(forms.ModelForm):
    class Meta:
        model = Moodboard
        fields = ['title', 'description', 'tags']

class ImageForm(forms.ModelForm):
    class Meta:
        model = Image
        fields = ['image']

ImageFormSet = forms.inlineformset_factory(
    Moodboard, Image, form=ImageForm, extra=1, can_delete=True, max_num=10
)

class TagForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = ['name']