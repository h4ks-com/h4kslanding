from django.urls import path

from webapp import views

urlpatterns = [
    path('', views.clocks_page, name='clocks'),
    path('api/timezone-stats/', views.api_timezone_stats, name='api_timezone_stats'),
]
