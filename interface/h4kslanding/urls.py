"""URL configuration for h4kslanding project.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/topics/http/urls/
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('', include('webapp.urls')),
    path('admin/', admin.site.urls),
]
