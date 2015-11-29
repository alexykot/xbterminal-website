import os.path
from urlparse import urljoin
from django.conf import settings
import requests


def get_latest_xbtfw_version_():
    """
    https://www.aptly.info/doc/api/repos/
    """
    config = settings.APTLY_SERVERS['default']
    api_url = '/api/repos/xbtfw-wandboard-dev/packages'
    params = {
        'q': 'xbterminal-firmware',
        'format': 'details',
    }
    certs = (
        os.path.join(settings.CERT_PATH, config['CLIENT_CERT']),
        os.path.join(settings.CERT_PATH, config['CLIENT_KEY']),
    )
    response = requests.get(urljoin(config['HOST'], api_url),
                            params=params,
                            cert=certs,
                            verify=False)
    result = response.json()
    latest = max(pkg['Version'] for pkg in result)
    return latest


def get_latest_xbtfw_version():
    config = settings.APTLY_SERVERS['default']
    url = urljoin(
        config['HOST'],
        '/repos/deb/fido/xbtfw-wandboard-dev/dists/poky/main/binary-armel/Packages')
    certs = (
        os.path.join(settings.CERT_PATH, config['CLIENT_CERT']),
        os.path.join(settings.CERT_PATH, config['CLIENT_KEY']),
    )
    response = requests.get(url, cert=certs, verify=False)
    # Parse response
    packages = []
    for line in response.content.splitlines():
        if not line.strip():
            continue
        if line.startswith('Package:') or line.startswith('Version:'):
            key, value = line.split(': ')
            if key == 'Package':
                packages.append({})
            packages[-1][key] = value
    # Find latest version
    latest = max(pkg['Version'] for pkg in packages
                 if pkg['Package'] == 'xbterminal-firmware')
    return latest
