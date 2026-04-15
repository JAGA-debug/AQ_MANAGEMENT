from django.urls import path
from . import views

urlpatterns = [
    path("",          views.dashboard_view, name="dashboard"),
    path("upload/",   views.upload_view,    name="upload"),
    path("api/data/", views.api_data,       name="api_data"),
    path("api/stats/",views.api_stats,      name="api_stats"),
]