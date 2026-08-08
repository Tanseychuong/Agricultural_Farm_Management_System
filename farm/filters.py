import django_filters
from .models import Crop


class CropFilter(django_filters.FilterSet):
    """
    Worked example — copy this pattern for other list views (Worker,
    Harvest, Sale). Renders as filter fields in a template via
    {{ filter.form }} and narrows the queryset automatically.
    """
    crop_type = django_filters.CharFilter(lookup_expr='icontains')
    planted_after = django_filters.DateFilter(field_name='planting_date', lookup_expr='gte')
    planted_before = django_filters.DateFilter(field_name='planting_date', lookup_expr='lte')

    class Meta:
        model = Crop
        fields = ['farm', 'status', 'crop_type']
