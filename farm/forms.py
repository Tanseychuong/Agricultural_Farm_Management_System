from django import forms
from .models import Crop, Farm, CropWorker, WorkerEquipment, CropFertilizer, HarvestSale


class FarmForm(forms.ModelForm):
    class Meta:
        model = Farm
        fields = ['farm_name', 'location', 'total_size']

    def clean_total_size(self):
        total_size = self.cleaned_data['total_size']
        if total_size <= 0:
            raise forms.ValidationError('Farm size must be greater than zero.')
        return total_size


class CropForm(forms.ModelForm):
    """
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


# --- Junction-table forms ---------------------------------------------------
# ModelForm works fine against CompositePrimaryKey models — the Django
# limitations only affect the admin and FK-targeting, neither of which
# apply here. These get plain function-based views instead of admin/CBVs
# (see views.py) purely because DeleteView's default get_object() expects
# a single pk value, and ours is a 3-column tuple.

class CropWorkerForm(forms.ModelForm):
    class Meta:
        model = CropWorker
        fields = ['crop', 'worker', 'assigned_date', 'task_role']
        widgets = {'assigned_date': forms.DateInput(attrs={'type': 'date'})}


class WorkerEquipmentForm(forms.ModelForm):
    class Meta:
        model = WorkerEquipment
        fields = ['worker', 'equipment', 'assigned_date', 'return_date']
        widgets = {
            'assigned_date': forms.DateInput(attrs={'type': 'date'}),
            'return_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean(self):
        # Mirrors trg_validate_equipment_dates — same rule, checked here so
        # the user sees a friendly form error instead of a raw DB exception.
        cleaned_data = super().clean()
        assigned_date = cleaned_data.get('assigned_date')
        return_date = cleaned_data.get('return_date')
        if assigned_date and return_date and return_date < assigned_date:
            raise forms.ValidationError('Return date cannot be earlier than the assignment date.')
        return cleaned_data


class CropFertilizerForm(forms.ModelForm):
    class Meta:
        model = CropFertilizer
        fields = ['crop', 'fertilizer', 'usage_date', 'quantity_used']
        widgets = {'usage_date': forms.DateInput(attrs={'type': 'date'})}


class HarvestSaleForm(forms.ModelForm):
    class Meta:
        model = HarvestSale
        fields = ['harvest', 'sale', 'quantity_sold', 'unit_price']
