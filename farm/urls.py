from django.urls import path
from django.contrib.auth.decorators import login_required
from . import views


urlpatterns = [
    path(
        '',
        login_required(views.DashboardView.as_view()),
        name='dashboard'
    ),

    path(
        'farms/',
        login_required(views.FarmListView.as_view()),
        name='farm-list'
    ),

    path(
        'farms/create/',
        login_required(views.FarmCreateView.as_view()),
        name='farm-create'
    ),

    path(
        'farms/<uuid:farm_id>/',
        login_required(views.FarmDetailView.as_view()),
        name='farm-detail'
    ),

    path(
        'farms/<uuid:pk>/edit/',
        views.FarmUpdateView.as_view(),
        name='farm-edit'
    ),

    path(
        'farms/<uuid:pk>/delete/',
        views.FarmDeleteView.as_view(),
        name='farm-delete'
    ),
]