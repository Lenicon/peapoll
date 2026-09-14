"""
URL configuration for peapoll project.
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', RedirectView.as_view(pattern_name='accounts:login', permanent=False)),
    path('accounts/', include('accounts.urls')),
    path('home/', include('home.urls')),
]
