import os.path
from urlparse import urljoin
from django.conf import settings
import requests


def get_latest_xbtfw_version():
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
