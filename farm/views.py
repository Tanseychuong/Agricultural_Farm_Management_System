import datetime
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.urls import reverse_lazy
from django.db import connection, DatabaseError
from django.views.generic import (
    TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView,
)

from .models import (
    Farm, Crop, Worker, Sale,
    CropWorker, WorkerEquipment, CropFertilizer, HarvestSale,
)
from .forms import (
    FarmForm, CropForm,
    CropWorkerForm, WorkerEquipmentForm, CropFertilizerForm, HarvestSaleForm,
)
from .permissions import PermissionRequiredMixin


class DashboardView(TemplateView):
    """
    First working page — confirms the ORM can read the existing Supabase
    tables end to end. CRUD views for each entity follow the same
    generic-CBV pattern used below for Farm and Crop.
    """
    template_name = 'admin/dashboard.html'

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

class SCDashboardView(TemplateView):
    """
    First working page — confirms the ORM can read the existing Supabase
    tables end to end. CRUD views for each entity follow the same
    generic-CBV pattern used below for Farm and Crop.
    """
    template_name = 'sale_clerk/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['recent_sales'] = (
            Sale.objects
            .select_related('customer')
            .order_by('-sale_date')[:10]
        )
        return context

# --- Farm CRUD ---------------------------------------------------------
# Only view_farm is granted to any group (see setup_roles.py) — nobody
# but a superuser can create/edit/delete a Farm. That's not an oversight:
# the spec gives Managers "see their farm(s)", never "manage farms".

class FarmListView(PermissionRequiredMixin, ListView):
    model = Farm
    template_name = 'farm/farm_list.html'
    context_object_name = 'farms'
    ordering = ['farm_name']
    permission_required = 'farm.view_farm'


class FarmDetailView(PermissionRequiredMixin, DetailView):
    model = Farm
    template_name = 'farm/farm_detail.html'
    context_object_name = 'farm'
    pk_url_kwarg = 'farm_id'
    permission_required = 'farm.view_farm'


class FarmCreateView(PermissionRequiredMixin, CreateView):
    model = Farm
    form_class = FarmForm
    template_name = 'farm/farm_form.html'
    success_url = reverse_lazy('farm-list')
    permission_required = 'farm.add_farm'


class FarmUpdateView(PermissionRequiredMixin, UpdateView):
    model = Farm
    form_class = FarmForm
    template_name = 'farm/farm_form.html'
    permission_required = 'farm.change_farm'

    def get_success_url(self):
        return reverse_lazy('farm-detail', kwargs={'farm_id': self.object.pk})


class FarmDeleteView(PermissionRequiredMixin, DeleteView):
    model = Farm
    template_name = 'farm/farm_confirm_delete.html'
    success_url = reverse_lazy('farm-list')
    permission_required = 'farm.delete_farm'


# --- Crop CRUD -----------------------------------------------------------
# Mirrors the Farm CRUD above exactly — same five-view shape, same
# form_class + generic CBV pattern. Copy this block for Worker, Harvest,
# Sale, Equipment, Fertilizer, Customer to finish out single-PK CRUD.

class CropListView(PermissionRequiredMixin, ListView):
    model = Crop
    template_name = 'farm/crop_list.html'
    context_object_name = 'crops'
    ordering = ['-planting_date']
    permission_required = 'farm.view_crop'


class CropDetailView(PermissionRequiredMixin, DetailView):
    model = Crop
    template_name = 'farm/crop_detail.html'
    context_object_name = 'crop'
    pk_url_kwarg = 'crop_id'
    permission_required = 'farm.view_crop'


class CropCreateView(PermissionRequiredMixin, CreateView):
    model = Crop
    form_class = CropForm
    template_name = 'farm/crop_form.html'
    success_url = reverse_lazy('crop-list')
    permission_required = 'farm.add_crop'


class CropUpdateView(PermissionRequiredMixin, UpdateView):
    model = Crop
    form_class = CropForm
    template_name = 'farm/crop_form.html'
    pk_url_kwarg = 'crop_id'
    permission_required = 'farm.change_crop'

    def get_success_url(self):
        return reverse_lazy('crop-detail', kwargs={'crop_id': self.object.pk})


class CropDeleteView(PermissionRequiredMixin, DeleteView):
    model = Crop
    template_name = 'farm/crop_confirm_delete.html'
    pk_url_kwarg = 'crop_id'
    success_url = reverse_lazy('crop-list')
    permission_required = 'farm.delete_crop'


# --- Worker views ---------------------------------------------------------
# Read-only in the app UI (list + detail) — create/edit/delete for Worker
# stay in the Django admin, which already handles this single-PK entity
# fine without any custom code. The detail page is the interesting part:
# Worker has no direct FK to Farm (a worker reaches a farm only via
# crop_worker -> crop -> farm), so "which farms does this worker work on"
# has to be derived from their crop assignments, not read off a field.

class WorkerListView(PermissionRequiredMixin, ListView):
    model = Worker
    template_name = 'farm/worker_list.html'
    context_object_name = 'workers'
    ordering = ['last_name', 'first_name']
    permission_required = 'farm.view_worker'


class WorkerDetailView(PermissionRequiredMixin, DetailView):
    model = Worker
    template_name = 'farm/worker_detail.html'
    context_object_name = 'worker'
    pk_url_kwarg = 'worker_id'
    permission_required = 'farm.view_worker'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        assignments = (
            self.object.crop_assignments
            .select_related('crop', 'crop__farm')
            .order_by('-assigned_date')
        )
        context['assignments'] = assignments
        # Distinct farms via crop_worker -> crop -> farm, de-duplicated by
        # farm_id since a worker can be assigned to several crops on the
        # same farm and should only show up once per farm here.
        seen_farm_ids = set()
        farms = []
        for a in assignments:
            farm = a.crop.farm
            if farm.farm_id not in seen_farm_ids:
                seen_farm_ids.add(farm.farm_id)
                farms.append(farm)
        context['farms'] = farms
        return context

# ============================================================
# Junction-table CRUD — plain function-based views, not CBVs.
#
# Each of these four tables has a 3-column composite primary key
# (see models.py). Generic DeleteView's default get_object() expects a
# single pk value from the URL, so it doesn't fit here. Rather than mix
# CBVs for two actions and function views for a third, each entity uses
# one consistent trio: _list, _create, _delete.
# ============================================================


# --- Crop <-> Worker assignments ----------------------------------------

@permission_required('farm.view_cropworker', raise_exception=True)
def crop_worker_list(request):
    assignments = CropWorker.objects.select_related('crop', 'worker').order_by('-assigned_date')
    return render(request, 'farm/crop_worker_list.html', {'assignments': assignments})


@permission_required('farm.add_cropworker', raise_exception=True)
def crop_worker_create(request):
    if request.method == 'POST':
        form = CropWorkerForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            try:
                # Calls sp_assign_worker_to_crop (Phase 6) instead of a
                # plain INSERT — the procedure checks for a duplicate
                # assignment first and raises a clear error if found.
                with connection.cursor() as cursor:
                    cursor.execute(
                        'CALL sp_assign_worker_to_crop(%s, %s, %s, %s)',
                        [data['crop'].pk, data['worker'].pk, data['assigned_date'], data['task_role']],
                    )
                messages.success(request, 'Worker assigned to crop.')
                return redirect('crop-worker-list')
            except DatabaseError as e:
                form.add_error(None, str(e))
    else:
        form = CropWorkerForm()
    return render(request, 'farm/crop_worker_form.html', {'form': form})


@permission_required('farm.delete_cropworker', raise_exception=True)
def crop_worker_delete(request, crop_id, worker_id, assigned_date):
    assignment = get_object_or_404(
        CropWorker, crop_id=crop_id, worker_id=worker_id,
        assigned_date=datetime.date.fromisoformat(assigned_date),
    )
    if request.method == 'POST':
        assignment.delete()
        messages.success(request, 'Assignment removed.')
        return redirect('crop-worker-list')
    return render(request, 'farm/confirm_delete.html', {
        'object': assignment, 'cancel_url': 'crop-worker-list',
    })


# --- Worker <-> Equipment assignments -------------------------------------

@permission_required('farm.view_workerequipment', raise_exception=True)
def worker_equipment_list(request):
    assignments = WorkerEquipment.objects.select_related('worker', 'equipment').order_by('-assigned_date')
    return render(request, 'farm/worker_equipment_list.html', {'assignments': assignments})


@permission_required('farm.add_workerequipment', raise_exception=True)
def worker_equipment_create(request):
    if request.method == 'POST':
        form = WorkerEquipmentForm(request.POST)
        if form.is_valid():
            try:
                # Plain save — trg_validate_equipment_dates still fires on
                # the INSERT; form.clean() below just gives a friendlier
                # error before that trigger would ever need to fire.
                form.save()
                messages.success(request, 'Equipment assignment recorded.')
                return redirect('worker-equipment-list')
            except DatabaseError as e:
                form.add_error(None, str(e))
    else:
        form = WorkerEquipmentForm()
    return render(request, 'farm/worker_equipment_form.html', {'form': form})


@permission_required('farm.delete_workerequipment', raise_exception=True)
def worker_equipment_delete(request, worker_id, equipment_id, assigned_date):
    assignment = get_object_or_404(
        WorkerEquipment, worker_id=worker_id, equipment_id=equipment_id,
        assigned_date=datetime.date.fromisoformat(assigned_date),
    )
    if request.method == 'POST':
        assignment.delete()
        messages.success(request, 'Equipment assignment removed.')
        return redirect('worker-equipment-list')
    return render(request, 'farm/confirm_delete.html', {
        'object': assignment, 'cancel_url': 'worker-equipment-list',
    })


# --- Crop <-> Fertilizer usage ---------------------------------------------

@permission_required('farm.view_cropfertilizer', raise_exception=True)
def crop_fertilizer_list(request):
    usages = CropFertilizer.objects.select_related('crop', 'fertilizer').order_by('-usage_date')
    return render(request, 'farm/crop_fertilizer_list.html', {'usages': usages})


@permission_required('farm.add_cropfertilizer', raise_exception=True)
def crop_fertilizer_create(request):
    if request.method == 'POST':
        form = CropFertilizerForm(request.POST)
        if form.is_valid():
            try:
                # Plain save — trg_deduct_fertilizer_stock fires on the
                # INSERT regardless of ORM vs raw SQL, and the CHECK on
                # stock_level >= 0 rolls the insert back automatically if
                # there isn't enough fertilizer left.
                form.save()
                messages.success(request, 'Fertilizer usage recorded.')
                return redirect('crop-fertilizer-list')
            except DatabaseError as e:
                form.add_error(None, str(e))
    else:
        form = CropFertilizerForm()
    return render(request, 'farm/crop_fertilizer_form.html', {'form': form})


@permission_required('farm.delete_cropfertilizer', raise_exception=True)
def crop_fertilizer_delete(request, crop_id, fertilizer_id, usage_date):
    usage = get_object_or_404(
        CropFertilizer, crop_id=crop_id, fertilizer_id=fertilizer_id,
        usage_date=datetime.date.fromisoformat(usage_date),
    )
    if request.method == 'POST':
        usage.delete()
        messages.success(request, 'Fertilizer usage record removed.')
        return redirect('crop-fertilizer-list')
    return render(request, 'farm/confirm_delete.html', {
        'object': usage, 'cancel_url': 'crop-fertilizer-list',
    })


# --- Harvest <-> Sale line items ---------------------------------------------

@permission_required('farm.view_harvestsale', raise_exception=True)
def harvest_sale_list(request):
    line_items = HarvestSale.objects.select_related('harvest', 'sale').order_by('-sale__sale_date')
    return render(request, 'farm/harvest_sale_list.html', {'line_items': line_items})


@permission_required('farm.add_harvestsale', raise_exception=True)
def harvest_sale_create(request):
    if request.method == 'POST':
        form = HarvestSaleForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            try:
                # Calls sp_record_harvest_sale (Phase 6): inserts the line
                # item AND updates sale.total_amount in one transaction.
                # trg_check_harvest_stock still fires on the INSERT inside
                # the procedure and rolls the whole call back if the
                # harvest doesn't have enough quantity left.
                with connection.cursor() as cursor:
                    cursor.execute(
                        'CALL sp_record_harvest_sale(%s, %s, %s, %s)',
                        [data['harvest'].pk, data['sale'].pk, data['quantity_sold'], data['unit_price']],
                    )
                messages.success(request, 'Sale line item recorded.')
                return redirect('harvest-sale-list')
            except DatabaseError as e:
                form.add_error(None, str(e))
    else:
        form = HarvestSaleForm()
    return render(request, 'farm/harvest_sale_form.html', {'form': form})


@permission_required('farm.delete_harvestsale', raise_exception=True)
def harvest_sale_delete(request, harvest_id, sale_id):
    line_item = get_object_or_404(HarvestSale, harvest_id=harvest_id, sale_id=sale_id)
    if request.method == 'POST':
        line_item.delete()
        messages.success(request, 'Sale line item removed.')
        return redirect('harvest-sale-list')
    return render(request, 'farm/confirm_delete.html', {
        'object': line_item, 'cancel_url': 'harvest-sale-list',
    })
