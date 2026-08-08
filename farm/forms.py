from django import forms
from .models import Crop, Farm


class CropForm(forms.ModelForm):
    """
    Worked example — copy this pattern for Worker, Harvest, Sale, etc.
    ModelForm gets you free client+server-side validation (required fields,
    max_length, date parsing); the DB CHECK constraints and triggers from
    Phase 4/7 remain the last line of defense if this form is ever bypassed
    (e.g. direct ORM use in a management command).
    """
    class Meta:
        model = Crop
        fields = ['farm', 'crop_type', 'planting_date', 'expected_harvest_date', 'status', 'plot_number']
        widgets = {
            'planting_date': forms.DateInput(attrs={'type': 'date'}),
            'expected_harvest_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        planting_date = cleaned_data.get('planting_date')
        expected_harvest_date = cleaned_data.get('expected_harvest_date')
        if planting_date and expected_harvest_date and expected_harvest_date < planting_date:
            raise forms.ValidationError('Expected harvest date cannot be before the planting date.')
        return cleaned_data
from django import forms


class FarmForm(forms.ModelForm):
    class Meta:
        model = Farm
        fields = ['farm_name', 'location', 'total_size']

    def clean_total_size(self):
        total_size = self.cleaned_data['total_size']

        if total_size <= 0:
            raise forms.ValidationError(
                'Farm size must be greater than zero.'
            )

        return total_size