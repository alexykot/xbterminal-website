import os.path
from urlparse import urljoin

from django.conf import settings
from distutils.version import LooseVersion
import requests


def get_latest_version(machine, package_name):
    """
    https://www.aptly.info/doc/api/repos/
    """
    config = settings.APTLY_SERVERS['default']
    repo_name = 'xbtfw-{machine}-dev'.format(machine=machine)
    api_url = '/api/repos/{name}/packages'.format(name=repo_name)
    params = {
        'q': package_name,
        'format': 'details',
    }
    certs = (
        os.path.join(settings.CERT_PATH, config['CLIENT_CERT']),
        os.path.join(settings.CERT_PATH, config['CLIENT_KEY']),
    )
    ca_cert = os.path.join(settings.CERT_PATH, config['CA_CERT'])
    response = requests.get(urljoin(config['HOST'], api_url),
                            params=params,
                            cert=certs,
                            verify=ca_cert)
    result = response.json()
    latest = max((pkg['Version'] for pkg in result), key=LooseVersion)
    return latest
