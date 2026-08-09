from django.urls import path
from django.contrib.auth.decorators import login_required
from . import views


def _protected(view):
    """Small helper so every route below is wrapped in login_required the
    same way, instead of repeating login_required(...) at each line and
    risking one getting missed (which is what happened before)."""
    return login_required(view)


urlpatterns = [
    path('', _protected(views.DashboardView.as_view()), name='dashboard'),

    # --- Farm CRUD ---
    path('farms/', _protected(views.FarmListView.as_view()), name='farm-list'),
    path('farms/create/', _protected(views.FarmCreateView.as_view()), name='farm-create'),
    path('farms/<uuid:farm_id>/', _protected(views.FarmDetailView.as_view()), name='farm-detail'),
    path('farms/<uuid:pk>/edit/', _protected(views.FarmUpdateView.as_view()), name='farm-edit'),
    path('farms/<uuid:pk>/delete/', _protected(views.FarmDeleteView.as_view()), name='farm-delete'),

    # --- Crop CRUD ---
    path('crops/', _protected(views.CropListView.as_view()), name='crop-list'),
    path('crops/create/', _protected(views.CropCreateView.as_view()), name='crop-create'),
    path('crops/<uuid:crop_id>/', _protected(views.CropDetailView.as_view()), name='crop-detail'),
    path('crops/<uuid:crop_id>/edit/', _protected(views.CropUpdateView.as_view()), name='crop-edit'),
    path('crops/<uuid:crop_id>/delete/', _protected(views.CropDeleteView.as_view()), name='crop-delete'),

    # --- Crop <-> Worker assignments ---
    path('crop-workers/', _protected(views.crop_worker_list), name='crop-worker-list'),
    path('crop-workers/create/', _protected(views.crop_worker_create), name='crop-worker-create'),
    path(
        'crop-workers/<uuid:crop_id>/<uuid:worker_id>/<str:assigned_date>/delete/',
        _protected(views.crop_worker_delete),
        name='crop-worker-delete',
    ),

    path('crops/<uuid:crop_id>/delete/', _protected(views.CropDeleteView.as_view()), name='crop-delete'),

    # --- Worker (read-only in-app; create/edit/delete via Django admin) ---
    path('workers/', _protected(views.WorkerListView.as_view()), name='worker-list'),
    path('workers/<uuid:worker_id>/', _protected(views.WorkerDetailView.as_view()), name='worker-detail'),

    # --- Harvest CRUD ---
    path('harvests/', _protected(views.HarvestListView.as_view()), name='harvest-list'),
    path('harvests/create/', _protected(views.HarvestCreateView.as_view()), name='harvest-create'),
    path('harvests/<uuid:harvest_id>/', _protected(views.HarvestDetailView.as_view()), name='harvest-detail'),
    path('harvests/<uuid:harvest_id>/edit/', _protected(views.HarvestUpdateView.as_view()), name='harvest-edit'),
    path('harvests/<uuid:harvest_id>/delete/', _protected(views.HarvestDeleteView.as_view()), name='harvest-delete'),

    # --- Equipment CRUD ---
    path('equipment/', _protected(views.EquipmentListView.as_view()), name='equipment-list'),
    path('equipment/create/', _protected(views.EquipmentCreateView.as_view()), name='equipment-create'),
    path('equipment/<uuid:equipment_id>/edit/', _protected(views.EquipmentUpdateView.as_view()), name='equipment-edit'),
    path('equipment/<uuid:equipment_id>/delete/', _protected(views.EquipmentDeleteView.as_view()), name='equipment-delete'),

    # --- Fertilizer CRUD ---
    path('fertilizer/', _protected(views.FertilizerListView.as_view()), name='fertilizer-list'),
    path('fertilizer/create/', _protected(views.FertilizerCreateView.as_view()), name='fertilizer-create'),
    path('fertilizer/<uuid:fertilizer_id>/edit/', _protected(views.FertilizerUpdateView.as_view()), name='fertilizer-edit'),
    path('fertilizer/<uuid:fertilizer_id>/delete/', _protected(views.FertilizerDeleteView.as_view()), name='fertilizer-delete'),

    # --- Sale CRUD (no delete route -- see views.py) ---
    path('sales/', _protected(views.SaleListView.as_view()), name='sale-list'),
    path('sales/create/', _protected(views.SaleCreateView.as_view()), name='sale-create'),
    path('sales/<uuid:sale_id>/', _protected(views.SaleDetailView.as_view()), name='sale-detail'),
    path('sales/<uuid:sale_id>/edit/', _protected(views.SaleUpdateView.as_view()), name='sale-edit'),

    # --- Worker <-> Equipment assignments ---
    path('worker-equipment/', _protected(views.worker_equipment_list), name='worker-equipment-list'),
    path('worker-equipment/create/', _protected(views.worker_equipment_create), name='worker-equipment-create'),
    path(
        'worker-equipment/<uuid:worker_id>/<uuid:equipment_id>/<str:assigned_date>/delete/',
        _protected(views.worker_equipment_delete),
        name='worker-equipment-delete',
    ),

    # --- Crop <-> Fertilizer usage ---
    path('crop-fertilizer/', _protected(views.crop_fertilizer_list), name='crop-fertilizer-list'),
    path('crop-fertilizer/create/', _protected(views.crop_fertilizer_create), name='crop-fertilizer-create'),
    path(
        'crop-fertilizer/<uuid:crop_id>/<uuid:fertilizer_id>/<str:usage_date>/delete/',
        _protected(views.crop_fertilizer_delete),
        name='crop-fertilizer-delete',
    ),

    # --- Harvest <-> Sale line items ---
    path('harvest-sales/', _protected(views.harvest_sale_list), name='harvest-sale-list'),
    path('harvest-sales/create/', _protected(views.harvest_sale_create), name='harvest-sale-create'),
    path(
        'harvest-sales/<uuid:harvest_id>/<uuid:sale_id>/delete/',
        _protected(views.harvest_sale_delete),
        name='harvest-sale-delete',
    ),
]
