from django.views.generic import TemplateView
from .models import Farm, Crop, Worker, Sale


class DashboardView(TemplateView):
    """
    First working page — confirms the ORM can read the existing Supabase
    tables end to end. CRUD views for each entity (Crop, Worker, Harvest,
    Sale, etc.) follow the same generic-CBV + django-filter pattern and
    slot in next to this one; see farm/forms.py and farm/filters.py for
    where that logic starts.
    """
    template_name = 'farm/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['farm_count'] = Farm.objects.count()
        context['crop_count'] = Crop.objects.count()
        context['worker_count'] = Worker.objects.count()
        context['recent_sales'] = Sale.objects.select_related('customer').order_by('-sale_date')[:5]
        return context
