import re
from typing import Literal, TypedDict, get_args

RoleName = Literal['admin', 'mail', 'navidrome', 'radio', 'ai', 'game']
PlanKey = Literal['guest', 'shell', 'daemon', 'kernel', 'root']


class PlanConfig(TypedDict):
    display: str
    description: str
    roles: list[str]


USERNAME_RE: re.Pattern[str] = re.compile(r'^[a-z0-9.\-]{3,30}$')

# Each tier adds roles on top of the previous one; order defines plan hierarchy.
_PLAN_TIERS: list[tuple[PlanKey, str, str, list[str]]] = [
    ('guest',  'Guest',  'Community access only',        []),
    ('shell',  'Shell',  '+ Email (IMAP/SMTP)',           ['mail']),
    ('daemon', 'Daemon', '+ Music streaming & radio',    ['navidrome', 'radio']),
    ('kernel', 'Kernel', '+ AI assistant & game server', ['ai', 'game']),
    ('root',   'Root',   'All services + admin access',  ['admin']),
]


def _build_plans() -> dict[PlanKey, PlanConfig]:
    result: dict[PlanKey, PlanConfig] = {}
    accumulated: list[str] = []
    for key, display, desc, added in _PLAN_TIERS:
        accumulated = accumulated + added
        result[key] = {'display': display, 'description': desc, 'roles': list(accumulated)}
    return result


PLANS: dict[PlanKey, PlanConfig] = _build_plans()
ALL_PLAN_ROLES: frozenset[str] = frozenset(get_args(RoleName))


def plan_from_roles(role_names: set[str]) -> PlanKey:
    """Return the highest matching plan key for a given set of role names."""
    for plan_key in reversed(list(PLANS)):
        required = set(PLANS[plan_key]['roles'])
        if required and required <= role_names:
            return plan_key
    return 'guest'
