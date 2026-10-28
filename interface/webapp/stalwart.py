from django.conf import settings
import httpx

USING = ['urn:ietf:params:jmap:core', 'urn:stalwart:jmap']
PROFILE_PASSWORD_DESCRIPTION = 'h4ks.com profile'


class StalwartError(Exception):
    pass


def _call(method: str, args: dict) -> dict:
    resp = httpx.post(
        settings.STALWART_JMAP_URL,
        headers={'Authorization': f'Bearer {settings.STALWART_API_KEY}'},
        json={'using': USING, 'methodCalls': [[method, args, '0']]},
        timeout=8.0,
    )
    resp.raise_for_status()
    name, result, _ = resp.json()['methodResponses'][0]
    if name == 'error':
        raise StalwartError(f'{method}: {result}')
    return result


def _domain_id(domain: str) -> str:
    ids = _call('x:Domain/query', {'filter': {'name': domain}})['ids']
    domains = _call('x:Domain/get', {'ids': ids, 'properties': ['name']})['list']
    for found in domains:
        if found['name'] == domain:
            return found['id']
    raise StalwartError(f'domain {domain} is not hosted')


def _account_id(email: str, quota: int) -> str:
    """Return the mail account for this address, creating it when the user
    never logged in to mail.

    Stalwart matches Logto logins to accounts by address, so an account
    created here is the same one the user reaches through webmail later.
    """
    local, domain = email.split('@', 1)
    domain_id = _domain_id(domain)
    ids = _call('x:Account/query', {'filter': {'name': local, 'domainId': domain_id}})['ids']
    if ids:
        accounts = _call('x:Account/get', {'ids': ids, 'properties': ['emailAddress']})['list']
        for account in accounts:
            if account['emailAddress'] == email:
                return account['id']
    created = _call('x:Account/set', {'create': {'new': {
        '@type': 'User',
        'name': local,
        'domainId': domain_id,
        'roles': {'@type': 'User'},
        'quotas': {'maxDiskQuota': quota},
    }}})
    if 'new' not in created.get('created', {}):
        raise StalwartError(f'account create failed: {created.get("notCreated")}')
    return created['created']['new']['id']


def replace_profile_password(email: str, quota: int) -> str:
    """Issue a new app password for the mailbox and revoke the one this page
    issued before."""
    account_id = _account_id(email, quota)
    existing = _call('x:AppPassword/get', {'accountId': account_id, 'properties': ['description']})['list']
    stale = [p['id'] for p in existing if p['description'] == PROFILE_PASSWORD_DESCRIPTION]
    if stale:
        _call('x:AppPassword/set', {'accountId': account_id, 'destroy': stale})
    created = _call('x:AppPassword/set', {'accountId': account_id, 'create': {'new': {
        'description': PROFILE_PASSWORD_DESCRIPTION,
        'permissions': {'@type': 'Inherit'},
        'allowedIps': {},
    }}})
    if 'new' not in created.get('created', {}):
        raise StalwartError(f'app password create failed: {created.get("notCreated")}')
    return created['created']['new']['secret']
