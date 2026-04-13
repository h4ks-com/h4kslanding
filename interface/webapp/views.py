from django.http import HttpRequest, HttpResponse, JsonResponse, Http404
from django.shortcuts import redirect, render
from django.template import loader
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import user_passes_test, login_required
from django.conf import settings
from django.core.cache import cache
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from django.db.models import Count

from .models import Location, App, PendingUser, UserProfile, Announcement, FeaturedProject, ApiToken, ChatLine
from .plans import PLANS, ALL_PLAN_ROLES, USERNAME_RE, plan_from_roles
import logging
import httpx
import base64
import imaplib
import secrets
import hashlib
import json
import ssl
from functools import wraps
from urllib.parse import quote, urlparse

logger = logging.getLogger(__name__)

_MAIL_QUOTA = 100 * 1024 * 1024  # 100 MB — applied on first password set


def _bootstrap_stalwart_principal(access_token: str) -> None:
    """Force Stalwart to create a local principal by doing an OAUTHBEARER IMAP
    auth.

    Stalwart with storage.directory = "logto" rejects POST
    /api/principal (OIDC dirs are read-only via admin API). The only way
    to create the principal is to let Stalwart process a real OIDC
    authentication — it auto-creates the record on first login. We do
    that here transparently so the user never has to open Roundcube.
    """
    imap_host = urlparse(settings.STALWART_API_URL).hostname
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    # OAUTHBEARER SASL (RFC 7628): n,,\x01auth=Bearer <token>\x01\x01
    auth_bytes = b"n,,\x01auth=Bearer " + access_token.encode() + b"\x01\x01"
    with imaplib.IMAP4_SSL(imap_host, 993, ssl_context=ctx) as imap:
        imap.authenticate('OAUTHBEARER', lambda _: auth_bytes)
        imap.logout()

def require_api_token(view_func):
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth_header.startswith('Bearer '):
            return JsonResponse({'error': 'Unauthorized'}, status=401)
        raw_token = auth_header[len('Bearer '):]
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        valid = ApiToken.objects.filter(active=True).values_list('token_hash', flat=True)
        if not any(secrets.compare_digest(token_hash, h) for h in valid):
            return JsonResponse({'error': 'Unauthorized'}, status=401)
        return view_func(request, *args, **kwargs)
    return wrapped


@ensure_csrf_cookie
def index(request):
    context = {
        'apps': App.objects.all(),
        'projects': FeaturedProject.objects.filter(active=True),
    }
    return render(request, 'index.html', context)


def clocks_page(request):
    user_timezone = ''
    if request.user.is_authenticated:
        try:
            user_timezone = request.user.profile.timezone
        except UserProfile.DoesNotExist:
            pass
    context = {
        'locations': Location.objects.all(),
        'apps': App.objects.all(),
        'user_timezone': user_timezone,
        'user': request.user,
    }
    return render(request, 'clocks.html', context)


def api_timezone_stats(request):
    stats = list(
        UserProfile.objects
        .exclude(timezone='')
        .values('timezone')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    return JsonResponse(stats, safe=False)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def api_announce(request):
    if request.method == 'GET':
        try:
            limit = min(int(request.GET.get('limit', 20)), 100)
            offset = int(request.GET.get('offset', 0))
        except ValueError:
            limit, offset = 20, 0

        total = Announcement.objects.count()
        items = list(Announcement.objects.all()[offset:offset + limit])
        has_more = offset + limit < total

        data = [
            {
                'id': a.id,
                'body': a.body,
                'author': a.author,
                'source': a.source,
                'pinned': a.pinned,
                'created_at': a.created_at.isoformat(),
            }
            for a in items
        ]
        return JsonResponse({'announcements': data, 'has_more': has_more, 'next_offset': offset + limit})

    # POST — requires token
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth_header.startswith('Bearer '):
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    raw_token = auth_header[len('Bearer '):]
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    valid = list(ApiToken.objects.filter(active=True).values_list('token_hash', flat=True))
    if not any(secrets.compare_digest(token_hash, h) for h in valid):
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    body = payload.get('body', '').strip()
    author = payload.get('author', 'anonymous').strip()
    source = payload.get('source', 'bot').strip()

    if not body:
        return JsonResponse({'error': 'body is required'}, status=400)
    if len(body) > 500:
        return JsonResponse({'error': 'body exceeds 500 characters'}, status=400)
    if source not in ('admin', 'bot'):
        source = 'bot'

    announcement = Announcement.objects.create(body=body, author=author[:100], source=source)
    return JsonResponse({'id': announcement.id, 'created_at': announcement.created_at.isoformat()}, status=201)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def api_chat(request):
    if request.method == 'GET':
        try:
            limit = min(int(request.GET.get('limit', 50)), 100)
        except ValueError:
            limit = 50
        before_id = request.GET.get('before')

        qs = ChatLine.objects.all()
        if before_id:
            try:
                qs = qs.filter(id__lt=int(before_id))
            except ValueError:
                pass

        lines = list(qs.order_by('-created_at')[:limit])
        has_more = False
        if lines:
            oldest_in_page = lines[-1]
            has_more = ChatLine.objects.filter(id__lt=oldest_in_page.id).exists()

        lines.reverse()
        oldest_id = lines[0].id if lines else None

        data = [
            {
                'id': line.id,
                'nick': line.nick,
                'message': line.message,
                'channel': line.channel,
                'created_at': line.created_at.isoformat(),
            }
            for line in lines
        ]
        return JsonResponse({'lines': data, 'has_more': has_more, 'oldest_id': oldest_id})

    # POST — requires token
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth_header.startswith('Bearer '):
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    raw_token = auth_header[len('Bearer '):]
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    valid = list(ApiToken.objects.filter(active=True).values_list('token_hash', flat=True))
    if not any(secrets.compare_digest(token_hash, h) for h in valid):
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    nick = payload.get('nick', '').strip()
    message = payload.get('message', '').strip()
    channel = payload.get('channel', '#lobby').strip()

    if not nick or not message:
        return JsonResponse({'error': 'nick and message are required'}, status=400)

    line = ChatLine.objects.create(nick=nick[:100], message=message[:500], channel=channel[:100])

    excess = ChatLine.objects.count() - 50
    if excess > 0:
        oldest_ids = list(ChatLine.objects.values_list('id', flat=True)[:excess])
        ChatLine.objects.filter(id__in=oldest_ids).delete()

    return JsonResponse({'id': line.id, 'created_at': line.created_at.isoformat()}, status=201)

def logout_view(request: HttpRequest) -> HttpResponse:
    auth_logout(request)
    return redirect('/')


def is_admin(user):
    return user.is_authenticated and user.is_staff

@user_passes_test(is_admin, login_url='/accounts/login')
def user_management(request: HttpRequest) -> HttpResponse:
    context = {
        'plans': PLANS,
        'plans_json': json.dumps(PLANS),
        'user': request.user,
    }
    return render(request, 'user_management.html', context)

@user_passes_test(is_admin, login_url='/accounts/login')
@require_http_methods(["POST"])
def generate_signup_url(request):
    email = request.POST.get('email', '').strip()

    if not email:
        return JsonResponse({'error': 'Email is required'}, status=400)

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


@user_passes_test(is_admin, login_url='/accounts/login')
@require_http_methods(["GET"])
def api_logto_users(request: HttpRequest) -> JsonResponse:
    access_token = get_logto_access_token()
    if not access_token:
        return JsonResponse({'error': 'Could not authenticate with Logto'}, status=502)

    search = request.GET.get('search', '').strip()
    try:
        page = max(1, int(request.GET.get('page', 1)))
        page_size = min(25, max(1, int(request.GET.get('page_size', 10))))
    except ValueError:
        page, page_size = 1, 10

    params = {'page': str(page), 'page_size': str(page_size)}
    if search:
        params['search'] = f'%{search}%'

    try:
        response = httpx.get(
            f"{settings.LOGTO_ENDPOINT}/api/users",
            headers={'Authorization': f'Bearer {access_token}'},
            params=params,
            timeout=10.0,
        )
        if response.status_code != 200:
            return JsonResponse({'error': f'Logto error: {response.status_code}'}, status=502)

        users = response.json()
        total = int(response.headers.get('Total-Number', len(users)))

        enriched = []
        for user in users:
            role_names: set[str]
            try:
                roles_resp = httpx.get(
                    f"{settings.LOGTO_ENDPOINT}/api/users/{user['id']}/roles",
                    headers={'Authorization': f'Bearer {access_token}'},
                    timeout=8.0,
                )
                role_names = {r['name'] for r in roles_resp.json()} if roles_resp.status_code == 200 else set()
            except httpx.RequestError:
                role_names = set()

            enriched.append({
                'id': user['id'],
                'username': user.get('username') or '',
                'primaryEmail': user.get('primaryEmail') or '',
                'name': user.get('name') or '',
                'createdAt': user.get('createdAt') or '',
                'plan': plan_from_roles(role_names),
            })

        return JsonResponse({'users': enriched, 'total': total, 'page': page, 'page_size': page_size})

    except httpx.RequestError as e:
        return JsonResponse({'error': f'Could not reach Logto: {str(e)}'}, status=502)


@user_passes_test(is_admin, login_url='/accounts/login')
@require_http_methods(["POST"])
def api_set_user_plan(request: HttpRequest, logto_id: str) -> JsonResponse:
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    plan_key = body.get('plan', '').strip()
    if plan_key not in PLANS:
        return JsonResponse({'error': f'Unknown plan: {plan_key}'}, status=400)

    access_token = get_logto_access_token()
    if not access_token:
        return JsonResponse({'error': 'Could not authenticate with Logto'}, status=502)

    headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}

    try:
        roles_resp = httpx.get(
            f"{settings.LOGTO_ENDPOINT}/api/users/{logto_id}/roles",
            headers=headers,
            timeout=8.0,
        )
        if roles_resp.status_code != 200:
            return JsonResponse({'error': 'Could not fetch user roles'}, status=502)

        for role in roles_resp.json():
            if role['name'] in ALL_PLAN_ROLES:
                httpx.delete(
                    f"{settings.LOGTO_ENDPOINT}/api/users/{logto_id}/roles/{role['id']}",
                    headers=headers,
                    timeout=8.0,
                )

        new_role_names = PLANS[plan_key]['roles']
        if new_role_names:
            roles_map = get_logto_roles_map(access_token)
            role_ids = [roles_map[name] for name in new_role_names if name in roles_map]
            if role_ids:
                httpx.post(
                    f"{settings.LOGTO_ENDPOINT}/api/users/{logto_id}/roles",
                    headers=headers,
                    json={'roleIds': role_ids},
                    timeout=8.0,
                )

        return JsonResponse({'success': True, 'plan': plan_key})

    except httpx.RequestError as e:
        return JsonResponse({'error': f'Could not reach Logto: {str(e)}'}, status=502)


@user_passes_test(is_admin, login_url='/accounts/login')
@require_http_methods(["POST"])
def api_batch_set_plan(request: HttpRequest) -> JsonResponse:
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    user_ids = body.get('user_ids', [])
    plan_key = body.get('plan', '').strip()

    if not user_ids or not isinstance(user_ids, list):
        return JsonResponse({'error': 'user_ids must be a non-empty list'}, status=400)
    if plan_key not in PLANS:
        return JsonResponse({'error': f'Unknown plan: {plan_key}'}, status=400)

    access_token = get_logto_access_token()
    if not access_token:
        return JsonResponse({'error': 'Could not authenticate with Logto'}, status=502)

    headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}
    new_role_names = PLANS[plan_key]['roles']
    new_role_ids: list[str] = []
    if new_role_names:
        roles_map = get_logto_roles_map(access_token)
        new_role_ids = [roles_map[name] for name in new_role_names if name in roles_map]

    updated = 0
    try:
        for logto_id in user_ids:
            roles_resp = httpx.get(
                f"{settings.LOGTO_ENDPOINT}/api/users/{logto_id}/roles",
                headers=headers,
                timeout=8.0,
            )
            if roles_resp.status_code != 200:
                continue

            for role in roles_resp.json():
                if role['name'] in ALL_PLAN_ROLES:
                    httpx.delete(
                        f"{settings.LOGTO_ENDPOINT}/api/users/{logto_id}/roles/{role['id']}",
                        headers=headers,
                        timeout=8.0,
                    )

            if new_role_ids:
                httpx.post(
                    f"{settings.LOGTO_ENDPOINT}/api/users/{logto_id}/roles",
                    headers=headers,
                    json={'roleIds': new_role_ids},
                    timeout=8.0,
                )
            updated += 1

        return JsonResponse({'success': True, 'updated': updated})

    except httpx.RequestError as e:
        return JsonResponse({'error': f'Could not reach Logto: {str(e)}'}, status=502)


def get_logto_access_token() -> str | None:
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
        response = httpx.post(
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

    except httpx.RequestError as e:
        print(f"Exception getting Logto token: {str(e)}")
        return None

def get_user_roles(logto_sub: str) -> set[str]:
    access_token = get_logto_access_token()
    if not access_token:
        return set()
    try:
        response = httpx.get(
            f"{settings.LOGTO_ENDPOINT}/api/users/{logto_sub}/roles",
            headers={'Authorization': f'Bearer {access_token}'},
            timeout=8.0,
        )
        if response.status_code != 200:
            return set()
        return {r['name'] for r in response.json()}
    except httpx.RequestError:
        return set()


def user_has_mail_role(logto_sub: str) -> bool:
    return 'mail' in get_user_roles(logto_sub)


def get_logto_roles_map(access_token: str) -> dict[str, str]:
    """Return {role_name: role_id} for all roles in Logto."""
    try:
        response = httpx.get(
            f"{settings.LOGTO_ENDPOINT}/api/roles",
            headers={'Authorization': f'Bearer {access_token}'},
            timeout=8.0,
        )
        if response.status_code != 200:
            return {}
        return {r['name']: r['id'] for r in response.json()}
    except httpx.RequestError:
        return {}


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
        username = email.split('@')[0].lower()

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

        response = httpx.post(
            f"{settings.LOGTO_ENDPOINT}/api/users",
            headers=headers,
            json=data,
            timeout=10
        )

        if response.status_code in [200, 201]:
            pending_user.delete()
            login_url = request.build_absolute_uri('/oidc/authenticate/')
            return JsonResponse({
                'success': True,
                'message': 'Account created successfully! You can now log in.',
                'login_url': login_url
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

    except httpx.RequestError as e:
        return JsonResponse({'error': f"Could not reach authentication service: {str(e)}"}, status=502)


def _get_client_ip(request: HttpRequest) -> str:
    # X-Forwarded-For is set by Traefik with the real client IP.
    # Take only the first entry — subsequent entries could be appended by earlier proxies.
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def _check_signup_rate_limit(ip: str, fp: str = '') -> bool:
    ip_key = f"signup_rate:ip:{ip}"
    ip_count: int = cache.get(ip_key, 0)
    if ip_count >= 5:
        return False

    if fp:
        fp_key = f"signup_rate:fp:{fp}"
        fp_count: int = cache.get(fp_key, 0)
        if fp_count >= 1:
            return False
        cache.set(fp_key, fp_count + 1, 30 * 24 * 3600)

    cache.set(ip_key, ip_count + 1, 3600)
    return True


def _verify_turnstile(token: str, ip: str) -> bool:
    try:
        resp = httpx.post(
            'https://challenges.cloudflare.com/turnstile/v0/siteverify',
            data={'secret': settings.TURNSTILE_SECRET_KEY, 'response': token, 'remoteip': ip},
            timeout=5.0,
        )
        return bool(resp.json().get('success', False))
    except httpx.RequestError:
        return False


@require_http_methods(["GET", "POST"])
def sign_up(request: HttpRequest) -> HttpResponse:
    if request.method == "GET":
        fp = request.get_signed_cookie('_h4k_sf', default=None, salt='signup')
        response = render(request, 'sign_up.html', {'turnstile_site_key': settings.TURNSTILE_SITE_KEY})
        if not fp:
            response.set_signed_cookie(
                '_h4k_sf', secrets.token_hex(16),
                salt='signup', max_age=30 * 24 * 3600,
                httponly=True, samesite='Lax',
            )
        return response

    ip = _get_client_ip(request)
    fp = request.get_signed_cookie('_h4k_sf', default='', salt='signup')

    if not _check_signup_rate_limit(ip, fp):
        return JsonResponse({'error': 'Too many attempts. Try again later.'}, status=429)

    token = request.POST.get('cf-turnstile-response', '').strip()
    if not token or not _verify_turnstile(token, ip):
        return JsonResponse({'error': 'Please complete the challenge.'}, status=400)

    username = request.POST.get('username', '').strip().lower()
    password = request.POST.get('password', '').strip()

    if not username or not password:
        return JsonResponse({'error': 'All fields are required'}, status=400)
    if not USERNAME_RE.match(username):
        return JsonResponse({'error': 'Username must be 3–30 characters, lowercase letters/numbers/dots/hyphens only'}, status=400)
    if len(password) < 8:
        return JsonResponse({'error': 'Password must be at least 8 characters'}, status=400)

    access_token = get_logto_access_token()
    if not access_token:
        return JsonResponse({'error': 'Registration temporarily unavailable'}, status=503)

    try:
        response = httpx.post(
            f"{settings.LOGTO_ENDPOINT}/api/users",
            headers={'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'},
            json={'username': username, 'password': password, 'name': username, 'primaryEmail': f'{username}@h4ks.com'},
            timeout=10.0,
        )

        if response.status_code in (200, 201):
            return JsonResponse({'success': True, 'message': 'Account created! You can now log in.'})

        if response.status_code == 422:
            if response.json().get('code') == 'user.username_already_in_use':
                return JsonResponse({'error': 'Username already taken'}, status=400)

        return JsonResponse({'error': 'Registration failed, please try again'}, status=400)

    except httpx.RequestError:
        return JsonResponse({'error': 'Registration temporarily unavailable'}, status=503)


@login_required
def profile(request):
    try:
        user_profile = request.user.profile
    except UserProfile.DoesNotExist:
        user_profile = UserProfile.objects.create(user=request.user)

    if request.method == 'POST':
        user_profile.timezone = request.POST.get('timezone', '').strip()
        user_profile.save()
        return JsonResponse({'success': True, 'message': 'Profile updated successfully!'})

    roles = get_user_roles(user_profile.logto_sub) if user_profile.logto_sub else set()
    plan_key = 'root' if request.user.is_staff else plan_from_roles(roles)
    template = loader.get_template('profile.html')
    context = {
        'user': request.user,
        'profile': user_profile,
        'has_mail_role': request.user.is_staff or ('mail' in roles),
        'is_guest': plan_key == 'guest',
        'plan': PLANS[plan_key]['display'],
    }
    return HttpResponse(template.render(context, request))


@login_required
def set_mail_password(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)

    password = request.POST.get('mail_password', '').strip()
    confirm  = request.POST.get('mail_password_confirm', '').strip()

    if not password:
        return JsonResponse({'success': False, 'error': 'Password is required.'}, status=400)
    if len(password) < 8:
        return JsonResponse({'success': False, 'error': 'Password must be at least 8 characters.'}, status=400)
    if password != confirm:
        return JsonResponse({'success': False, 'error': 'Passwords do not match.'}, status=400)

    logto_sub = getattr(request.user, 'profile', None) and request.user.profile.logto_sub
    if not request.user.is_staff and (not logto_sub or not user_has_mail_role(logto_sub)):
        return JsonResponse({'success': False, 'error': 'Mail access not enabled for your account.'}, status=403)

    email = request.user.email
    if not email:
        return JsonResponse({'success': False, 'error': 'No email address on your account.'}, status=400)

    api_base = settings.STALWART_API_URL.rstrip('/')
    auth     = (settings.STALWART_ADMIN_USER, settings.STALWART_ADMIN_SECRET)

    # Stalwart creates principals named by full email (directory.logto.fields.username = "email").
    # The @ must be percent-encoded in the URL path to avoid a 401/routing issue.
    principal_id = quote(email, safe='')
    try:
        check_data = httpx.get(f'{api_base}/principal/{principal_id}', auth=auth, timeout=8.0).json()
        if check_data.get('error') == 'notFound':
            token = request.session.get('oidc_access_token')
            if not token:
                return JsonResponse({'success': False, 'error': 'Session expired, please log in again.'}, status=401)
            try:
                _bootstrap_stalwart_principal(token)
            except imaplib.IMAP4.error as e:
                logger.error('mail bootstrap failed for %s: %s', email, e)
                return JsonResponse({'success': False, 'error': 'Could not initialise mail account.'}, status=502)
            check_data = httpx.get(f'{api_base}/principal/{principal_id}', auth=auth, timeout=8.0).json()

        if check_data.get('error') == 'notFound':
            logger.error('mail principal still missing after bootstrap for %s', email)
            return JsonResponse({'success': False, 'error': 'Could not initialise mail account.'}, status=502)

        patch_ops = [{'action': 'set', 'field': 'secrets', 'value': f'$app$mail${password}'}]
        if not check_data.get('quota'):
            patch_ops.append({'action': 'set', 'field': 'quota', 'value': _MAIL_QUOTA})
        resp_data = httpx.patch(
            f'{api_base}/principal/{principal_id}',
            auth=auth,
            json=patch_ops,
            timeout=8.0,
        ).json()
        if resp_data.get('error'):
            logger.error('mail PATCH failed for %s: %s', email, resp_data)
            return JsonResponse({'success': False, 'error': 'Failed to update mail password.'}, status=502)
    except httpx.RequestError as e:
        logger.error('mail server unreachable for %s: %s', email, e)
        return JsonResponse({'success': False, 'error': 'Could not reach mail server.'}, status=502)

    return JsonResponse({'success': True, 'message': 'Mail password updated. Configure your client with this password.'})


@require_http_methods(["GET"])
def mail_userinfo_proxy(request: HttpRequest) -> JsonResponse:
    """Stalwart OIDC directory endpoint with mail-role enforcement.

    Stalwart v0.15 calls this URL with the client's bearer token and
    treats HTTP 200 as authentication success, non-200 as failure. We
    forward the token to Logto's /oidc/me and gate on the 'mail' role
    before returning 200. Remove this proxy when upgrading to Stalwart
    v0.16 (see config.toml comment).
    """
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth_header.startswith('Bearer '):
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    token = auth_header[len('Bearer '):]

    try:
        resp = httpx.get(
            f'{settings.LOGTO_ENDPOINT}/oidc/me',
            headers={'Authorization': f'Bearer {token}'},
            timeout=8.0,
        )
    except httpx.RequestError:
        return JsonResponse({'error': 'Upstream unavailable'}, status=502)

    if resp.status_code != 200:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    data = resp.json()
    roles: list[str] = data.get('roles', [])

    if 'mail' not in roles:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    return JsonResponse(data, status=200)
