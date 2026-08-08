from django.shortcuts import redirect
from django.views.generic import TemplateView, ListView, FormView, UpdateView, DetailView, DeleteView

from .models import Farm, Crop, Worker, Sale
from .forms import FarmForm

from django.urls import reverse_lazy




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



class DashboardView(TemplateView):
    template_name = 'farm/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['farm_count'] = Farm.objects.count()
        context['crop_count'] = Crop.objects.count()
        context['worker_count'] = Worker.objects.count()
        context['recent_sales'] = (
            Sale.objects
            .select_related('customer')
            .order_by('-sale_date')[:5]
        )
        return context


class FarmListView(ListView):
    model = Farm
    template_name = 'farm/farm_list.html'
    context_object_name = 'farms'
    ordering = ['farm_name']


class FarmCreateView(FormView):
    template_name = 'farm/farm_form.html'
    form_class = FarmForm

    def form_valid(self, form):
        form.save()
        return redirect('farm-list')


class DashboardView(TemplateView):
    template_name = 'farm/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['farm_count'] = Farm.objects.count()
        context['crop_count'] = Crop.objects.count()
        context['worker_count'] = Worker.objects.count()
        context['recent_sales'] = (
            Sale.objects
            .select_related('customer')
            .order_by('-sale_date')[:5]
        )
        return context


class FarmListView(ListView):
    model = Farm
    template_name = 'farm/farm_list.html'
    context_object_name = 'farms'


class FarmDetailView(DetailView):
    model = Farm
    template_name = 'farm/farm_detail.html'
    context_object_name = 'farm'
    pk_url_kwarg = 'farm_id'


class FarmUpdateView(UpdateView):
    model = Farm
    fields = ['farm_name', 'location', 'total_size']
    template_name = 'farm/farm_form.html'
    success_url = reverse_lazy('farm-list')

class FarmDeleteView(DeleteView):
    model = Farm
    template_name = 'farm/farm_confirm_delete.html'

    def get_success_url(self):
        return reverse_lazy('farm-list')