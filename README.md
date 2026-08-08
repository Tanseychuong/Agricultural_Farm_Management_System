farm_management/
├── manage.py
├── farm_management/          # project config
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py / asgi.py
├── farm/                      # single app — one is enough here
│   ├── models.py             # unmanaged models mirroring your schema
│   ├── admin.py               # free CRUD scaffold for demo/debugging
│   ├── views.py               # generic class-based views
│   ├── forms.py                # ModelForms with validation
│   ├── filters.py              # django-filter FilterSets
│   ├── urls.py
│   ├── reports.py              # raw-SQL calls into your Phase 6 SQL views
│   └── migrations/
│       └── 0001_initial.py    # empty/no-op — see below
├── templates/
│   └── farm/
└── static/