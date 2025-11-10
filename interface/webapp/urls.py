from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('accounts/login', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-dashboard/generate-signup-url/', views.generate_signup_url, name='generate_signup_url'),
    path('signup/', views.signup_form, name='signup_form'),
    path('signup/submit/', views.signup_submit, name='signup_submit'),
]

