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
]