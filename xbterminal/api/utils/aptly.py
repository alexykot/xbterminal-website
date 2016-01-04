import os.path
from urlparse import urljoin
from django.conf import settings
import requests

YOCTO_RELEASE = 'jethro'


def get_latest_xbtfw_version(machine):
    config = settings.APTLY_SERVERS['default']
    repo_name = 'xbtfw-{machine}-dev'.format(machine=machine)
    url = urljoin(
        config['HOST'],
        '/repos/deb/{branch}/{repo}/dists/poky/main/binary-armel/Packages'.format(
            branch=YOCTO_RELEASE,
            repo=repo_name))
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
