from mozilla_django_oidc.auth import OIDCAuthenticationBackend
from django.contrib.auth.models import User
from django.conf import settings
from .models import UserProfile
from urllib.parse import urlencode

class LogtoOIDCAuthenticationBackend(OIDCAuthenticationBackend):

    def filter_users_by_claims(self, claims):
        """Look up user by Logto sub claim stored in UserProfile."""
        sub = claims.get('sub')
        if not sub:
            return self.UserModel.objects.none()

        try:
            profile = UserProfile.objects.get(logto_sub=sub)
            return self.UserModel.objects.filter(id=profile.user.id)
        except UserProfile.DoesNotExist:
            return self.UserModel.objects.none()

    def create_user(self, claims):
        """Create user with email-based username and store sub in profile."""
        email = claims.get('email', '')
        sub = claims.get('sub')

        if not email:
            return None

        username = email.split('@')[0]

        base_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        user = self.UserModel.objects.create_user(
            username=username,
            email=email
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
