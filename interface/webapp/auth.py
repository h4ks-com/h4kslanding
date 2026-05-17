from mozilla_django_oidc.auth import OIDCAuthenticationBackend
from django.contrib.auth.models import User
from django.conf import settings
from .models import UserProfile
from urllib.parse import urlencode

class LogtoOIDCAuthenticationBackend(OIDCAuthenticationBackend):

    def filter_users_by_claims(self, claims):
        """Look up user by Logto sub, falling back to email/username for legacy
        accounts created before logto_sub linking (e.g. Django superusers)."""
        sub = claims.get('sub')
        if sub:
            try:
                profile = UserProfile.objects.get(logto_sub=sub)
                return self.UserModel.objects.filter(id=profile.user.id)
            except UserProfile.DoesNotExist:
                pass

        email = claims.get('email', '').strip()
        if email:
            by_email = self.UserModel.objects.filter(
                email__iexact=email, profile__logto_sub__isnull=True,
            )
            if by_email.count() == 1:
                return by_email

        logto_username = (claims.get('username') or '').strip()
        if logto_username:
            by_username = self.UserModel.objects.filter(
                username__iexact=logto_username, profile__logto_sub__isnull=True,
            )
            if by_username.count() == 1:
                return by_username

        return self.UserModel.objects.none()

    def create_user(self, claims):
        """Create user from claims; sub is the stable identity key."""
        email = claims.get('email', '') or ''
        sub = claims.get('sub')
        if not sub:
            return None

        username = (claims.get('username') or '').strip()
        if not username and email:
            username = email.split('@')[0]
        if not username:
            return None

        base_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        user = self.UserModel.objects.create_user(
            username=username,
            email=email,
        )

        if hasattr(user, 'profile'):
            user.profile.logto_sub = sub
            user.profile.save()

        return user

    def update_user(self, user, claims):
        """Update user profile with latest claims."""
        user.email = claims.get('email', user.email)
        user.save()

        if hasattr(user, 'profile'):
            sub = claims.get('sub')
            if sub and not user.profile.logto_sub:
                user.profile.logto_sub = sub
                user.profile.save()

        return user


def provider_logout(request):
    """Generate Logto logout URL with post_logout_redirect_uri."""
    redirect_uri = request.build_absolute_uri('/')

    params = {
        'client_id': settings.OIDC_RP_CLIENT_ID,
        'post_logout_redirect_uri': redirect_uri,
    }

    logout_url = f"{settings.LOGTO_ENDPOINT}/oidc/session/end?{urlencode(params)}"
    return logout_url
