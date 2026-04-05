from django.conf import settings
from django.http import HttpRequest


def ui_flags(_request: HttpRequest) -> dict:
    return {'show_nav': getattr(settings, 'SHOW_NAV', True)}
