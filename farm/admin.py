from django.contrib import admin
from .models import Farm, Customer, Worker, Equipment, Fertilizer, Crop, Harvest, Sale

# Composite-PK models (CropWorker, WorkerEquipment, CropFertilizer, HarvestSale)
# can't be registered here — Django admin doesn't support composite primary
# keys yet. They get plain function-based views instead (see views.py).
# This gives instant working CRUD for the 8 "main" entities with zero
# extra code, which is most of Phase 8's CRUD requirement for free.


@admin.register(Farm)
class FarmAdmin(admin.ModelAdmin):
    list_display = ('farm_name', 'location', 'total_size')
    search_fields = ('farm_name', 'location')


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'contact_details')
    search_fields = ('first_name', 'last_name', 'contact_details')


@admin.register(Worker)
class WorkerAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'job_role', 'hire_date')
    list_filter = ('job_role',)
    search_fields = ('first_name', 'last_name')


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ('equipment_name', 'equipment_type', 'status')
    list_filter = ('status', 'equipment_type')
    search_fields = ('equipment_name',)


@admin.register(Fertilizer)
class FertilizerAdmin(admin.ModelAdmin):
    list_display = ('fertilizer_type', 'stock_level', 'unit')
    search_fields = ('fertilizer_type',)


@admin.register(Crop)
class CropAdmin(admin.ModelAdmin):
    list_display = ('crop_type', 'farm', 'status', 'planting_date', 'expected_harvest_date', 'plot_number')
    list_filter = ('status', 'farm', 'crop_type')
    search_fields = ('crop_type', 'plot_number')
    autocomplete_fields = ('farm',)


@admin.register(Harvest)
class HarvestAdmin(admin.ModelAdmin):
    list_display = ('crop', 'harvest_date', 'quantity')
    list_filter = ('harvest_date',)
    autocomplete_fields = ('crop',)


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'customer', 'sale_date', 'total_amount')
    list_filter = ('sale_date',)
    search_fields = ('invoice_number',)
    autocomplete_fields = ('customer',)
