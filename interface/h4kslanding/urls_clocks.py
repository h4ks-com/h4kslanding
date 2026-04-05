from django.urls import path

from webapp import views

urlpatterns = [
    path('', views.clocks_page, name='clocks'),
]
