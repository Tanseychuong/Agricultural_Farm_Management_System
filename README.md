# Agricultural Farm Management System

Django front-end for the farm management database (Phases 1–7 already built directly
in SQL against Supabase Postgres — schema, checks, and triggers). Django is a thin
app layer on top: it never runs migrations against the domain tables, it only reads
and writes through them.

## Project layout

```
farm_management/       # project config: settings, root urls, wsgi
farm/                   # single app — models, admin, views, forms, filters, reports
templates/               # farm/ (app pages) and registration/ (Django auth)
```

## Setup

```bash
python -m venv venv
source venv/bin/activate          # venv\Scripts\activate on Windows
pip install -r requirements.txt

cp .env.example .env              # fill in your Supabase DB credentials
python manage.py migrate          # creates Django's OWN tables only (auth, sessions, admin log) —
                                   # the farm/customer/crop/... tables already exist in Supabase
python manage.py createsuperuser
python manage.py runserver
```

Visit `http://127.0.0.1:8000/admin/` for full CRUD on Farm, Customer, Worker, Equipment,
Fertilizer, Crop, Harvest, and Sale out of the box. Visit `/` for the dashboard.

## Why models are `managed = False`

The database schema, `CHECK` constraints, and triggers already exist in Supabase from
the earlier SQL phases. `farm/models.py` maps to that existing schema rather than
generating it — Django's migration system only manages its own internal tables
(auth, sessions, admin log). See the comment block at the top of
`farm/migrations/0001_initial.py` for what that migration actually does (and doesn't
do) at `migrate` time.

## Junction tables and composite primary keys

`crop_worker`, `worker_equipment`, `crop_fertilizer`, and `harvest_sale` have no
single-column primary key in the DDL — each is `(FK, FK, date)`. These use Django
5.2+'s `CompositePrimaryKey` (see `farm/models.py`). Two known limitations from the
Django docs apply here: composite-PK models can't be registered in the Django admin
yet, and a `ForeignKey` elsewhere can't target one as its related model. Neither is a
problem for this schema — nothing references these junction tables — but it does mean
their CRUD is handled with plain function-based views rather than `ModelAdmin`.

## Status / next steps

- [x] Settings wired to Supabase Postgres via env vars
- [x] All 12 tables mapped as unmanaged models, including composite PKs
- [x] Django admin CRUD for the 8 single-PK entities
- [x] Working dashboard page (proves the ORM read path end-to-end)
- [ ] Custom CRUD views/templates for the 4 junction tables (no admin support yet)
- [ ] `django-filter` search/filtering wired into list templates for every entity
- [ ] RBAC via Django Groups + Permissions (Farm Manager / Field Worker / Sales Clerk)
- [ ] Phase 6 SQL views/procedures/functions in the database, then swap `reports.py`
      to read from them directly instead of inline SQL
