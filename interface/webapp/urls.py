from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('oidc/', include('mozilla_django_oidc.urls')),
    path('profile/', views.profile, name='profile'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-dashboard/generate-signup-url/', views.generate_signup_url, name='generate_signup_url'),
    path('signup/', views.signup_form, name='signup_form'),
    path('signup/submit/', views.signup_submit, name='signup_submit'),
]

