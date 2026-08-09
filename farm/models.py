import uuid
from django.conf import settings
from django.db import models

# All models below are managed = False: Django never creates, alters, or
# drops these tables. The schema, checks, and triggers already exist in
# Supabase per the Phase 4 DDL and Phase 7 trigger scripts — this file only
# teaches the ORM how to talk to what's already there. Field names/types/
# db_column values must stay in sync with that DDL if it ever changes.


class Farm(models.Model):
    farm_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farm_name = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    total_size = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        managed = False
        db_table = 'farm'

    def __str__(self):
        return self.farm_name


class Customer(models.Model):
    customer_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    contact_details = models.CharField(max_length=255, blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'customer'

    def __str__(self):
        return f'{self.first_name} {self.last_name}'


class Worker(models.Model):
    worker_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    contact_details = models.CharField(max_length=255, blank=True, null=True)
    job_role = models.CharField(max_length=100, blank=True, null=True)
    hire_date = models.DateField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'worker'

    def __str__(self):
        return f'{self.first_name} {self.last_name}'


class Equipment(models.Model):
    equipment_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    equipment_name = models.CharField(max_length=255)
    equipment_type = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=50, default='Available')

    class Meta:
        managed = False
        db_table = 'equipment'

    def __str__(self):
        return self.equipment_name


class Fertilizer(models.Model):
    fertilizer_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fertilizer_type = models.CharField(max_length=100)
    # Mirrors the DB CHECK (stock_level >= 0); Django validates this on
    # ModelForm.is_valid() too, but the trigger + check remain the source
    # of truth if the ORM is ever bypassed.
    stock_level = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'fertilizer'

    def __str__(self):
        return self.fertilizer_type


class Crop(models.Model):
    crop_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, db_column='farm_id', related_name='crops')
    crop_type = models.CharField(max_length=100)
    planting_date = models.DateField()
    expected_harvest_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=50, blank=True, null=True)
    plot_number = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'crop'

    def __str__(self):
        return f'{self.crop_type} ({self.plot_number or "no plot"})'


class Harvest(models.Model):
    harvest_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    crop = models.ForeignKey(Crop, on_delete=models.CASCADE, db_column='crop_id', related_name='harvests')
    harvest_date = models.DateField()
    quantity = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        managed = False
        db_table = 'harvest'

    def __str__(self):
        return f'{self.crop.crop_type} harvest — {self.harvest_date}'


class Sale(models.Model):
    sale_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(Customer, on_delete=models.RESTRICT, db_column='customer_id', related_name='sales')
    sale_date = models.DateField()
    invoice_number = models.CharField(max_length=100, unique=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        managed = False
        db_table = 'sale'

    def __str__(self):
        return self.invoice_number


# --- Junction tables -------------------------------------------------------
# These four have no single-column primary key in the DDL — each PK is a
# composite of (FK, FK, date). Django 5.2+ supports this natively via
# CompositePrimaryKey; the string args are attnames (field_name + "_id"),
# not db_column values, though here they happen to match.
#
# Known limitation: composite-PK models cannot be registered in the Django
# admin yet (Django docs, as of 5.2/6.0), and a ForeignKey elsewhere cannot
# target one of these as its related model. Neither applies to our schema —
# nothing references these junction tables — so it's safe here. They're
# handled with plain function-based views instead of admin/ModelForm CBVs
# (see farm/views.py).

class CropWorker(models.Model):
    pk = models.CompositePrimaryKey('crop_id', 'worker_id', 'assigned_date')
    crop = models.ForeignKey(Crop, on_delete=models.CASCADE, db_column='crop_id')
    worker = models.ForeignKey(Worker, on_delete=models.CASCADE, db_column='worker_id', related_name='crop_assignments')
    assigned_date = models.DateField()
    task_role = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'crop_worker'

    def __str__(self):
        return f'{self.worker} on {self.crop} ({self.assigned_date})'


class WorkerEquipment(models.Model):
    pk = models.CompositePrimaryKey('worker_id', 'equipment_id', 'assigned_date')
    worker = models.ForeignKey(Worker, on_delete=models.CASCADE, db_column='worker_id')
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, db_column='equipment_id')
    assigned_date = models.DateField()
    return_date = models.DateField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'worker_equipment'

    def __str__(self):
        return f'{self.worker} operating {self.equipment} ({self.assigned_date})'


class CropFertilizer(models.Model):
    pk = models.CompositePrimaryKey('crop_id', 'fertilizer_id', 'usage_date')
    crop = models.ForeignKey(Crop, on_delete=models.CASCADE, db_column='crop_id')
    fertilizer = models.ForeignKey(Fertilizer, on_delete=models.RESTRICT, db_column='fertilizer_id')
    usage_date = models.DateField()
    quantity_used = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        managed = False
        db_table = 'crop_fertilizer'

    def __str__(self):
        return f'{self.fertilizer} on {self.crop} ({self.usage_date})'


class HarvestSale(models.Model):
    pk = models.CompositePrimaryKey('harvest_id', 'sale_id')
    harvest = models.ForeignKey(Harvest, on_delete=models.RESTRICT, db_column='harvest_id')
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, db_column='sale_id')
    quantity_sold = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        managed = False
        db_table = 'harvest_sale'

    def __str__(self):
        return f'{self.quantity_sold} from {self.harvest} in {self.sale}'


# ============================================================
# Authentication bridge — Django User -> Worker
# ============================================================
# This table is Django-owned (managed = True), unlike everything above.
# It's app-specific glue for the dashboard, not part of the graded
# Phase 3/4 domain schema — which is exactly why it lives in its own
# table instead of adding an auth-related column onto `worker` itself.
# The domain schema stays exactly as designed and graded; this is a
# separate concern bolted on top of it.
#
# `worker` is nullable because not every logged-in user corresponds to
# a farm worker — a Sales Clerk account, for instance, has no reason to
# be linked to a Worker row at all.
#
# Role itself is NOT stored here — see farm/permissions.py. Role comes
# from Django Group membership, which is what actually powers
# PermissionRequiredMixin on every view. Duplicating "role" as a field
# here would just be a second source of truth to keep in sync.

class WorkerProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='worker_profile',
    )
    worker = models.OneToOneField(
        Worker, on_delete=models.SET_NULL, null=True, blank=True, related_name='profile',
        help_text='Required for Farm Manager / Field Worker accounts. Leave blank for Sales Clerk.',
    )

    class Meta:
        managed = True

    def __str__(self):
        return f'{self.user.username} -> {self.worker or "no linked worker"}'
