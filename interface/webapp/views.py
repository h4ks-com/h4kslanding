from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.http import Http404, HttpResponseServerError
from django.shortcuts import render
from django.template import loader
from django.utils import timezone
from django.contrib.auth.decorators import user_passes_test
from django.conf import settings
from django.views.decorators.http import require_http_methods
from urllib.parse import urlencode, quote

from datetime import datetime
from .models import Location, App, PendingUser
import requests
import base64
import json
import secrets
import hashlib

index_template="index.html"

def index(request):
    template = loader.get_template(index_template)
    locations = Location.objects.all()
    apps = App.objects.all()
    context = { "locations": locations, "apps": apps, }
    return HttpResponse(template.render(context, request))

def is_admin(user):
    return user.is_authenticated and user.is_staff

@user_passes_test(is_admin, login_url='/accounts/login')
def admin_dashboard(request):
    template = loader.get_template('admin_dashboard.html')
    context = {
        'signup_url': None,
        'error': None,
        'email': None
    }
    return HttpResponse(template.render(context, request))

@user_passes_test(is_admin, login_url='/accounts/login')
@require_http_methods(["POST"])
def generate_signup_url(request):
    email = request.POST.get('email', '').strip()

    if not email:
        return JsonResponse({'error': 'Email is required'}, status=400)

    try:
        PendingUser.cleanup_expired()

        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        pending_user, created = PendingUser.objects.update_or_create(
            email=email,
            defaults={'token_hash': token_hash}
        )

        signup_url = request.build_absolute_uri(f"/signup?token={token}")

        message = 'New signup link generated.' if created else 'Updated existing signup link (previous link invalidated).'

        return JsonResponse({
            'success': True,
            'signup_url': signup_url,
            'email': email,
            'message': message
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def get_logto_access_token():
    credentials = f"{settings.LOGTO_M2M_CLIENT_ID}:{settings.LOGTO_M2M_CLIENT_SECRET}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()

    headers = {
        'Authorization': f'Basic {encoded_credentials}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    data = {
        'grant_type': 'client_credentials',
        'resource': 'https://default.logto.app/api',
        'scope': 'all'
    }

    try:
        response = requests.post(
            f"{settings.LOGTO_ENDPOINT}/oidc/token",
            headers=headers,
            data=data,
            timeout=10
        )

        if response.status_code == 200:
            return response.json().get('access_token')
        else:
            print(f"Logto token error: {response.status_code} - {response.text}")
            return None

    except Exception as e:
        print(f"Exception getting Logto token: {str(e)}")
        return None

def create_logto_user(access_token, email):
    import secrets
    import string

    random_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    data = {
        'primaryEmail': email,
        'password': random_password,
        'name': email.split('@')[0]
    }

    try:
        response = requests.post(
            f"{settings.LOGTO_ENDPOINT}/api/users",
            headers=headers,
            json=data,
            timeout=10
        )

        if response.status_code in [200, 201]:
            return True
        elif response.status_code == 422:
            error_data = response.json()
            if error_data.get('code') == 'user.email_already_in_use':
                print(f"User with email {email} already exists")
                return True
            print(f"Logto create user validation error: {response.text}")
            return False
        else:
            print(f"Logto create user error: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        print(f"Exception creating user: {str(e)}")
        return False


def signup_form(request):
    token = request.GET.get('token', '').strip()

    if not token:
        raise Http404("Invalid signup link")

    PendingUser.cleanup_expired()

    token_hash = hashlib.sha256(token.encode()).hexdigest()

    try:
        pending_user = PendingUser.objects.get(token_hash=token_hash)
    except PendingUser.DoesNotExist:
        raise Http404("Invalid or expired signup link")

    if pending_user.is_expired():
        pending_user.delete()
        raise Http404("This signup link has expired")

    template = loader.get_template('signup.html')
    context = {
        'email': pending_user.email,
        'token': token
    }
    return HttpResponse(template.render(context, request))


@require_http_methods(["POST"])
def signup_submit(request):
    token = request.POST.get('token', '').strip()
    password = request.POST.get('password', '').strip()
    confirm_password = request.POST.get('confirm_password', '').strip()
    recovery_email = request.POST.get('recovery_email', '').strip()

    if not token or not password:
        return JsonResponse({'error': 'Missing required fields'}, status=400)

    if password != confirm_password:
        return JsonResponse({'error': 'Passwords do not match'}, status=400)

    if len(password) < 8:
        return JsonResponse({'error': 'Password must be at least 8 characters'}, status=400)

    PendingUser.cleanup_expired()

    token_hash = hashlib.sha256(token.encode()).hexdigest()

    try:
        pending_user = PendingUser.objects.get(token_hash=token_hash)
    except PendingUser.DoesNotExist:
        return JsonResponse({'error': 'Invalid or expired signup link'}, status=400)

    if pending_user.is_expired():
        pending_user.delete()
        return JsonResponse({'error': 'This signup link has expired'}, status=400)

    try:
        access_token = get_logto_access_token()

        if not access_token:
            return JsonResponse({'error': 'Failed to authenticate with authentication service'}, status=500)

        email = pending_user.email
        username = email.split('@')[0]

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        data = {
            'username': username,
            'password': password,
            'primaryEmail': email,
            'name': username
        }

        if recovery_email:
            data['customData'] = {'recovery_email': recovery_email}

        response = requests.post(
            f"{settings.LOGTO_ENDPOINT}/api/users",
            headers=headers,
            json=data,
            timeout=10
        )

        if response.status_code in [200, 201]:
            pending_user.delete()
            return JsonResponse({
                'success': True,
                'message': 'Account created successfully! You can now log in.',
                'login_url': settings.LOGTO_ENDPOINT
            })
        elif response.status_code == 422:
            error_data = response.json()
            if error_data.get('code') == 'user.email_already_in_use':
                pending_user.delete()
                return JsonResponse({'error': 'This email is already registered. Please log in instead.'}, status=400)
            if error_data.get('code') == 'user.username_already_in_use':
                pending_user.delete()
                return JsonResponse({'error': 'This username is already taken. Please contact support.'}, status=400)
            return JsonResponse({'error': f"Registration failed: {error_data.get('message', 'Unknown error')}"}, status=400)
        else:
            return JsonResponse({'error': f"Registration failed: {response.status_code}"}, status=500)

    except Exception as e:
        return JsonResponse({'error': f"An error occurred: {str(e)}"}, status=500)
