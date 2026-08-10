import datetime
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.urls import reverse_lazy
from django.db import connection, DatabaseError
from django.views.generic import (
    TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView,
)
from django.views import View

from .models import (
    Farm, Crop, Worker, Sale, Harvest, Equipment, Fertilizer,
    CropWorker, WorkerEquipment, CropFertilizer, HarvestSale,
)
from .forms import (
    FarmForm, CropForm, HarvestForm, EquipmentForm, FertilizerForm, SaleForm,
    CropWorkerForm, WorkerEquipmentForm, CropFertilizerForm, HarvestSaleForm,
)
from .permissions import (
    PermissionRequiredMixin, GroupRequiredMixin, SuperuserRequiredMixin,
    farms_for_user, crops_for_user, workers_for_user, coworkers_for_user, harvests_for_user,
)


class DashboardRouterView(View):
    """
    The '/' route. Sends each user straight to the dashboard that
    matches their role, instead of showing one dashboard to everyone.

    A logged-in user with no role assigned yet — not a superuser, not
    in any of the three groups — is a real state worth surfacing
    directly rather than guessing which dashboard to show them: it
    means whoever created their account forgot to add them to a group.
    """

    def get(self, request):
        user = request.user
        if user.is_superuser:
            return redirect('admin-dashboard')
        if user.groups.filter(name='Farm Manager').exists():
            return redirect('manager-dashboard')
        if user.groups.filter(name='Field Worker').exists():
            return redirect('worker-dashboard')
        if user.groups.filter(name='Sales Clerk').exists():
            return redirect('sales-dashboard')
        return render(request, 'farm/no_role.html')


class AdminDashboardView(SuperuserRequiredMixin, TemplateView):
    """Superuser-only. Full, unscoped view across every farm."""
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


class ManagerDashboardView(GroupRequiredMixin, TemplateView):
    """
    Farm Manager only. Everything here is scoped through farms_for_user
    / crops_for_user / workers_for_user (permissions.py) — derived from
    which crops this Manager's linked Worker is assigned to, since
    Worker has no direct FK to Farm. A Manager overseeing Farm A never
    sees Farm B's data here.
    """
    required_group = 'Farm Manager'
    template_name = 'manager/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['farms'] = farms_for_user(user)
        context['crops'] = crops_for_user(user).select_related('farm')
        context['crop_count'] = context['crops'].count()
        context['worker_count'] = workers_for_user(user).count()
        context['recent_harvests'] = (
            harvests_for_user(user)
            .select_related('crop', 'crop__farm')
            .order_by('-harvest_date')[:5]
        )
        # Equipment and fertilizer aren't farm-specific in the schema
        # (no farm_id column on either table) — shared resources across
        # the whole operation, so these stay unscoped.
        context['equipment_count'] = Equipment.objects.count()
        context['low_stock_fertilizer'] = Fertilizer.objects.filter(stock_level__lte=20)
        return context


class WorkerDashboardView(GroupRequiredMixin, TemplateView):
    """
    Field Worker only. Read-only by design — no create/edit/delete
    links anywhere on this page, matching the spec ("no editing/
    deleting administrative data"). Same scoping helpers as the Manager
    dashboard, just presented without any management actions.
    """
    required_group = 'Field Worker'
    template_name = 'worker/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['farms'] = farms_for_user(user)
        context['crops'] = crops_for_user(user).select_related('farm')
        context['coworkers'] = coworkers_for_user(user)
        return context


class SalesDashboardView(GroupRequiredMixin, TemplateView):
    """Sales Clerk only. Sales aren't farm-scoped in the schema (a Sale
    links to a Customer, not a Worker/Farm), so this stays unscoped."""
    required_group = 'Sales Clerk'
    template_name = 'sale_clerk/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['recent_sales'] = (
            Sale.objects
            .select_related('customer')
            .order_by('-sale_date')[:10]
        )
        context['sale_count'] = Sale.objects.count()
        context['customer_count'] = Sale.objects.values('customer_id').distinct().count()
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

    def get_queryset(self):
        return farms_for_user(self.request.user).order_by('farm_name')


class FarmDetailView(PermissionRequiredMixin, DetailView):
    model = Farm
    template_name = 'farm/farm_detail.html'
    context_object_name = 'farm'
    pk_url_kwarg = 'farm_id'
    permission_required = 'farm.view_farm'

    def get_queryset(self):
        # Scoping get_queryset() (not just permission_required) means a
        # farm outside farms_for_user() 404s instead of rendering — a
        # Field Worker can't view another farm's page by guessing its UUID.
        return farms_for_user(self.request.user)


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

    def get_queryset(self):
        return crops_for_user(self.request.user).select_related('farm').order_by('-planting_date')


class CropDetailView(PermissionRequiredMixin, DetailView):
    model = Crop
    template_name = 'farm/crop_detail.html'
    context_object_name = 'crop'
    pk_url_kwarg = 'crop_id'
    permission_required = 'farm.view_crop'

    def get_queryset(self):
        return crops_for_user(self.request.user)


class CropCreateView(PermissionRequiredMixin, CreateView):
    model = Crop
    form_class = CropForm
    template_name = 'farm/crop_form.html'
    success_url = reverse_lazy('crop-list')
    permission_required = 'farm.add_crop'

    def get_form(self, form_class=None):
        # Without this, the farm dropdown shows every farm in the
        # system — a Manager could attach a new crop to a farm they
        # don't oversee, even though they'd never be able to see it
        # afterwards (CropDetailView is scoped too). Scoping the choices
        # here stops the mistake at the source instead of just hiding
        # its result.
        form = super().get_form(form_class)
        form.fields['farm'].queryset = farms_for_user(self.request.user)
        return form


class CropUpdateView(PermissionRequiredMixin, UpdateView):
    model = Crop
    form_class = CropForm
    template_name = 'farm/crop_form.html'
    pk_url_kwarg = 'crop_id'
    permission_required = 'farm.change_crop'

    def get_queryset(self):
        return crops_for_user(self.request.user)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['farm'].queryset = farms_for_user(self.request.user)
        return form

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

    def get_queryset(self):
        return workers_for_user(self.request.user).order_by('last_name', 'first_name')


class WorkerDetailView(PermissionRequiredMixin, DetailView):
    model = Worker
    template_name = 'farm/worker_detail.html'
    context_object_name = 'worker'
    pk_url_kwarg = 'worker_id'
    permission_required = 'farm.view_worker'

    def get_queryset(self):
        return workers_for_user(self.request.user)

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


class WorkerDeleteView(PermissionRequiredMixin, DeleteView):
    """
    The gap this fills: setup_roles.py grants Farm Manager the
    delete_worker permission, but until now there was no view or route
    that let a Manager actually use it — the permission existed with
    nothing behind it.

    worker.crop_worker and worker.worker_equipment both CASCADE on
    delete (see Phase 4 DDL), so deleting a Worker silently deletes
    their entire assignment history too. The confirm template makes
    this explicit rather than letting it be a surprise.
    """
    model = Worker
    template_name = 'farm/worker_confirm_delete.html'
    pk_url_kwarg = 'worker_id'
    success_url = reverse_lazy('worker-list')
    permission_required = 'farm.delete_worker'

    def get_queryset(self):
        return workers_for_user(self.request.user)


# --- Harvest CRUD (Farm Manager) --------------------------------------------

class HarvestListView(PermissionRequiredMixin, ListView):
    model = Harvest
    template_name = 'farm/harvest_list.html'
    context_object_name = 'harvests'
    ordering = ['-harvest_date']
    permission_required = 'farm.view_harvest'

    def get_queryset(self):
        return harvests_for_user(self.request.user).select_related('crop', 'crop__farm').order_by('-harvest_date')


class HarvestDetailView(PermissionRequiredMixin, DetailView):
    model = Harvest
    template_name = 'farm/harvest_detail.html'
    context_object_name = 'harvest'
    pk_url_kwarg = 'harvest_id'
    permission_required = 'farm.view_harvest'

    def get_queryset(self):
        return harvests_for_user(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sales'] = self.object.harvestsale_set.select_related('sale')
        return context


class HarvestCreateView(PermissionRequiredMixin, CreateView):
    model = Harvest
    form_class = HarvestForm
    template_name = 'farm/harvest_form.html'
    success_url = reverse_lazy('harvest-list')
    permission_required = 'farm.add_harvest'

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['crop'].queryset = crops_for_user(self.request.user)
        return form


class HarvestUpdateView(PermissionRequiredMixin, UpdateView):
    model = Harvest
    form_class = HarvestForm
    template_name = 'farm/harvest_form.html'
    pk_url_kwarg = 'harvest_id'
    permission_required = 'farm.change_harvest'

    def get_queryset(self):
        return harvests_for_user(self.request.user)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['crop'].queryset = crops_for_user(self.request.user)
        return form

    def get_success_url(self):
        return reverse_lazy('harvest-detail', kwargs={'harvest_id': self.object.pk})


class HarvestDeleteView(PermissionRequiredMixin, DeleteView):
    model = Harvest
    template_name = 'farm/harvest_confirm_delete.html'
    pk_url_kwarg = 'harvest_id'
    success_url = reverse_lazy('harvest-list')
    permission_required = 'farm.delete_harvest'

    def form_valid(self, form):
        # harvest_sale.harvest_id is ON DELETE RESTRICT — deleting a
        # harvest that's already been sold from fails at the DB level.
        # Without this, that shows up as a raw 500 error instead of a
        # message the user can act on.
        try:
            return super().form_valid(form)
        except DatabaseError:
            messages.error(
                self.request,
                'This harvest has sale records against it and cannot be deleted. '
                'Remove the related sale line items first.',
            )
            return redirect('harvest-detail', harvest_id=self.object.pk)


# --- Equipment CRUD (Farm Manager) ------------------------------------------
# No separate detail page — Equipment has few enough fields that the
# edit form doubles as the detail view. Same for Fertilizer below.

class EquipmentListView(PermissionRequiredMixin, ListView):
    model = Equipment
    template_name = 'farm/equipment_list.html'
    context_object_name = 'equipment_items'
    ordering = ['equipment_name']
    permission_required = 'farm.view_equipment'


class EquipmentCreateView(PermissionRequiredMixin, CreateView):
    model = Equipment
    form_class = EquipmentForm
    template_name = 'farm/equipment_form.html'
    success_url = reverse_lazy('equipment-list')
    permission_required = 'farm.add_equipment'


class EquipmentUpdateView(PermissionRequiredMixin, UpdateView):
    model = Equipment
    form_class = EquipmentForm
    template_name = 'farm/equipment_form.html'
    pk_url_kwarg = 'equipment_id'
    success_url = reverse_lazy('equipment-list')
    permission_required = 'farm.change_equipment'


class EquipmentDeleteView(PermissionRequiredMixin, DeleteView):
    model = Equipment
    template_name = 'farm/equipment_confirm_delete.html'
    pk_url_kwarg = 'equipment_id'
    success_url = reverse_lazy('equipment-list')
    permission_required = 'farm.delete_equipment'


# --- Fertilizer CRUD (Farm Manager) -----------------------------------------

class FertilizerListView(PermissionRequiredMixin, ListView):
    model = Fertilizer
    template_name = 'farm/fertilizer_list.html'
    context_object_name = 'fertilizers'
    ordering = ['fertilizer_type']
    permission_required = 'farm.view_fertilizer'


class FertilizerCreateView(PermissionRequiredMixin, CreateView):
    model = Fertilizer
    form_class = FertilizerForm
    template_name = 'farm/fertilizer_form.html'
    success_url = reverse_lazy('fertilizer-list')
    permission_required = 'farm.add_fertilizer'


class FertilizerUpdateView(PermissionRequiredMixin, UpdateView):
    model = Fertilizer
    form_class = FertilizerForm
    template_name = 'farm/fertilizer_form.html'
    pk_url_kwarg = 'fertilizer_id'
    success_url = reverse_lazy('fertilizer-list')
    permission_required = 'farm.change_fertilizer'


class FertilizerDeleteView(PermissionRequiredMixin, DeleteView):
    model = Fertilizer
    template_name = 'farm/fertilizer_confirm_delete.html'
    pk_url_kwarg = 'fertilizer_id'
    success_url = reverse_lazy('fertilizer-list')
    permission_required = 'farm.delete_fertilizer'

    def form_valid(self, form):
        # crop_fertilizer.fertilizer_id is also ON DELETE RESTRICT.
        try:
            return super().form_valid(form)
        except DatabaseError:
            messages.error(
                self.request,
                'This fertilizer has usage records against it and cannot be deleted.',
            )
            return redirect('fertilizer-list')


# --- Sale CRUD (Sales Clerk) ------------------------------------------------
# No delete view — delete_sale isn't granted to any group (see
# setup_roles.py), matching the spec: Sales Clerk can view/create/edit,
# never delete. Only a superuser could delete a Sale, and that's
# available through Django admin already.

class SaleListView(PermissionRequiredMixin, ListView):
    model = Sale
    template_name = 'farm/sale_list.html'
    context_object_name = 'sales'
    ordering = ['-sale_date']
    permission_required = 'farm.view_sale'

    def get_queryset(self):
        return super().get_queryset().select_related('customer')


class SaleDetailView(PermissionRequiredMixin, DetailView):
    model = Sale
    template_name = 'farm/sale_detail.html'
    context_object_name = 'sale'
    pk_url_kwarg = 'sale_id'
    permission_required = 'farm.view_sale'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['line_items'] = self.object.harvestsale_set.select_related('harvest', 'harvest__crop')
        return context


class SaleCreateView(PermissionRequiredMixin, CreateView):
    model = Sale
    form_class = SaleForm
    template_name = 'farm/sale_form.html'
    permission_required = 'farm.add_sale'

    def form_valid(self, form):
        # total_amount isn't a form field — a new sale starts at 0 and
        # grows as harvest-sale line items get added via
        # sp_record_harvest_sale (see harvest_sale_create above), so it
        # can never drift out of sync with what was actually sold.
        form.instance.total_amount = 0
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('sale-detail', kwargs={'sale_id': self.object.pk})


class SaleUpdateView(PermissionRequiredMixin, UpdateView):
    model = Sale
    form_class = SaleForm
    template_name = 'farm/sale_form.html'
    pk_url_kwarg = 'sale_id'
    permission_required = 'farm.change_sale'

    def get_success_url(self):
        return reverse_lazy('sale-detail', kwargs={'sale_id': self.object.pk})


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
        form.fields['crop'].queryset = crops_for_user(request.user)
        form.fields['worker'].queryset = workers_for_user(request.user)
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
        # Without this, the dropdowns show every crop/worker in the
        # system — a Manager could assign a worker they don't oversee
        # to a crop they don't oversee, on a farm that isn't theirs.
        form.fields['crop'].queryset = crops_for_user(request.user)
        form.fields['worker'].queryset = workers_for_user(request.user)
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
