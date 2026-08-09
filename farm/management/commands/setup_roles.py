"""
Creates/updates the three role groups and their permissions. Safe to
re-run any time (uses get_or_create + .set(), so it's idempotent — running
it twice doesn't duplicate anything, and re-running after adding a new
model/permission just picks up the change).

Run with: python manage.py setup_roles

Deliberately NOT covered here: Admin. Django superusers already bypass
every permission check automatically (that's built-in Django behavior)
— there's no group to create for "has access to everything."

Permission grants below map directly to the spec:

Farm Manager
  - view farms (not create/edit/delete — that stays Admin-only)
  - full CRUD on crops, crop-worker assignments, harvests, equipment,
    equipment assignments, fertilizer, fertilizer usage
  - view + delete on workers, but NOT add/change — creating or editing a
    Worker's own record isn't in the spec, only removing one. Note this
    is separate from "create authentication accounts": deleting a
    Worker row is a domain-data action; nothing here touches auth.User,
    so Managers still can't create logins for anyone.

Field Worker
  - view-only across the board, nothing else

Sales Clerk
  - view/create/edit sales and sale line items (no delete — not in spec)
  - view customers (needed to even show whose sale it is)
  - nothing on farms/crops/workers/equipment/fertilizer
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission

ROLE_PERMISSIONS = {
    'Farm Manager': [
        ('farm', 'view_farm'),

        ('farm', 'view_crop'), ('farm', 'add_crop'), ('farm', 'change_crop'), ('farm', 'delete_crop'),

        ('farm', 'view_cropworker'), ('farm', 'add_cropworker'),
        ('farm', 'change_cropworker'), ('farm', 'delete_cropworker'),

        ('farm', 'view_harvest'), ('farm', 'add_harvest'),
        ('farm', 'change_harvest'), ('farm', 'delete_harvest'),

        ('farm', 'view_equipment'), ('farm', 'add_equipment'),
        ('farm', 'change_equipment'), ('farm', 'delete_equipment'),

        ('farm', 'view_workerequipment'), ('farm', 'add_workerequipment'),
        ('farm', 'change_workerequipment'), ('farm', 'delete_workerequipment'),

        ('farm', 'view_fertilizer'), ('farm', 'add_fertilizer'),
        ('farm', 'change_fertilizer'), ('farm', 'delete_fertilizer'),

        ('farm', 'view_cropfertilizer'), ('farm', 'add_cropfertilizer'),
        ('farm', 'change_cropfertilizer'), ('farm', 'delete_cropfertilizer'),

        ('farm', 'view_worker'), ('farm', 'delete_worker'),
    ],
    'Field Worker': [
        ('farm', 'view_farm'),
        ('farm', 'view_crop'),
        ('farm', 'view_cropworker'),
        ('farm', 'view_worker'),
        ('farm', 'view_harvest'),
    ],
    'Sales Clerk': [
        ('farm', 'view_sale'), ('farm', 'add_sale'), ('farm', 'change_sale'),
        ('farm', 'view_harvestsale'), ('farm', 'add_harvestsale'),
        ('farm', 'view_customer'),
    ],
}


class Command(BaseCommand):
    help = 'Creates/updates the Farm Manager, Field Worker, and Sales Clerk groups with their permissions.'

    def handle(self, *args, **options):
        for group_name, perms in ROLE_PERMISSIONS.items():
            group, created = Group.objects.get_or_create(name=group_name)
            permission_objs = []
            missing = []
            for app_label, codename in perms:
                try:
                    permission_objs.append(
                        Permission.objects.get(content_type__app_label=app_label, codename=codename)
                    )
                except Permission.DoesNotExist:
                    missing.append(f'{app_label}.{codename}')

            group.permissions.set(permission_objs)
            verb = 'Created' if created else 'Updated'
            self.stdout.write(self.style.SUCCESS(f'{verb} group "{group_name}" ({len(permission_objs)} permissions)'))
            if missing:
                self.stdout.write(self.style.WARNING(f'  Skipped (not found yet): {", ".join(missing)}'))
