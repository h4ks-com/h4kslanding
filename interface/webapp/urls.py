from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('clocks/', views.clocks_page, name='clocks'),
    path('oidc/', include('mozilla_django_oidc.urls')),
    path('profile/', views.profile, name='profile'),
    path('profile/set-mail-password/', views.set_mail_password, name='set_mail_password'),
    path('user-management/', views.user_management, name='user_management'),
    path('user-management/generate-signup-url/', views.generate_signup_url, name='generate_signup_url'),
    path('logout/', views.logout_view, name='logout'),
    path('sign-up/', views.sign_up, name='sign_up'),
    path('signup/', views.signup_form, name='signup_form'),
    path('signup/submit/', views.signup_submit, name='signup_submit'),
    path('api/announce/', views.api_announce, name='api_announce'),
    path('api/chat/', views.api_chat, name='api_chat'),
    path('api/timezone-stats/', views.api_timezone_stats, name='api_timezone_stats'),
    path('api/admin/users/', views.api_logto_users, name='api_logto_users'),
    path('api/admin/users/<str:logto_id>/set-plan/', views.api_set_user_plan, name='api_set_user_plan'),
    path('api/admin/batch-set-plan/', views.api_batch_set_plan, name='api_batch_set_plan'),
]

