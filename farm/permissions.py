"""
Role resolution and object-level scoping.

Django's Group + Permission system answers "can this user use this KIND
of view at all" — that's what PermissionRequiredMixin below checks, and
it's what makes /farms/<id>/edit/ actually reject an unauthorized user
instead of just relying on a template hiding the Edit button.

It does NOT answer "which SPECIFIC rows can they see" — a Field Worker
with view_crop permission is still allowed to view crops in general, but
should only see the crops they're actually assigned to, not every crop
on every farm. That's row-level scoping, and it's what the functions
below are for. Any dashboard/list view that needs to be scoped to a
farm, not just permission-gated, should filter its queryset through one
of these rather than relying on permissions alone.
"""

from django.contrib.auth.mixins import PermissionRequiredMixin as _DjangoPermissionRequiredMixin

from .models import Farm, Crop, Worker, CropWorker


class PermissionRequiredMixin(_DjangoPermissionRequiredMixin):
    """
    Identical to Django's own PermissionRequiredMixin, with raise_exception
    always on. Without this, a logged-in user who lacks permission gets
    silently redirected back to the login page — which looks like a bug
    (they're already logged in) rather than an access-denied message.
    This returns a clean 403 instead. Use this everywhere in this app
    instead of importing Django's version directly.
    """
    raise_exception = True


def get_worker(user):
    """The Worker row linked to this Django user, or None — e.g. a Sales
    Clerk or Admin account has no reason to be linked to one."""
    profile = getattr(user, 'worker_profile', None)
    return profile.worker if profile and profile.worker_id else None


def farms_for_user(user):
    """Distinct farms this user's linked worker is assigned to, derived
    from crop_worker -> crop -> farm (Worker has no direct FK to Farm).
    Superusers get every farm."""
    if user.is_superuser:
        return Farm.objects.all()
    worker = get_worker(user)
    if worker is None:
        return Farm.objects.none()
    farm_ids = (
        CropWorker.objects
        .filter(worker=worker)
        .values_list('crop__farm_id', flat=True)
        .distinct()
    )
    return Farm.objects.filter(farm_id__in=farm_ids)


def crops_for_user(user):
    """Distinct crops this user's linked worker is assigned to.
    Superusers get every crop."""
    if user.is_superuser:
        return Crop.objects.all()
    worker = get_worker(user)
    if worker is None:
        return Crop.objects.none()
    crop_ids = (
        CropWorker.objects
        .filter(worker=worker)
        .values_list('crop_id', flat=True)
        .distinct()
    )
    return Crop.objects.filter(crop_id__in=crop_ids)


def coworkers_for_user(user):
    """Other workers assigned to any crop on any farm this user works on
    — i.e. "who else works here". Superusers get every worker."""
    if user.is_superuser:
        return Worker.objects.all()
    worker = get_worker(user)
    if worker is None:
        return Worker.objects.none()
    farm_ids = farms_for_user(user).values_list('farm_id', flat=True)
    worker_ids = (
        CropWorker.objects
        .filter(crop__farm_id__in=farm_ids)
        .values_list('worker_id', flat=True)
        .distinct()
    )
    return Worker.objects.filter(worker_id__in=worker_ids).exclude(worker_id=worker.worker_id)
