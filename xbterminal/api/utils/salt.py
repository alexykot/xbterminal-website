import os.path
import logging
from django.conf import settings

import requests

logger = logging.getLogger(__name__)


class Salt(object):

    def __init__(self, server='default'):
        self.config = settings.SALT_SERVERS[server]
        self._auth_token = None

    def _send_request(self, method, url, params=None, data=None):
        headers = {
            'Accept': 'application/json',
        }
        if self._auth_token:
            headers['X-Auth-Token'] = self._auth_token
        certs = (
            os.path.join(settings.CERT_PATH, self.config['CLIENT_CERT']),
            os.path.join(settings.CERT_PATH, self.config['CLIENT_KEY']),
        )
        response = requests.request(method.upper(),
                                    self.config['HOST'] + url,
                                    params=params,
                                    data=data,
                                    headers=headers,
                                    cert=certs,
                                    verify=False)
        response.raise_for_status()
        return response.json()['return'][0]

    def login(self):
        payload = {
            'username': self.config['USER'],
            'password': self.config['PASSWORD'],
            'eauth': 'pam',
        }
        result = self._send_request('post', '/login', data=payload)
        self._auth_token = result['token']
        logger.info('login successful')

    def check_fingerprint(self, minion_id, fingerprint):
        """
        https://docs.saltstack.com/en/latest/ref/wheel/all/salt.wheel.key.html
        """
        payload = {
            'client': 'wheel',
            'fun': 'key.finger',
            'match': minion_id,
        }
        result = self._send_request('post', '/', data=payload)
        fingerprints = result['data']['return']
        try:
            return fingerprints['minions_pre'][minion_id] == fingerprint
        except KeyError:
            return False

    def accept(self, minion_id):
        payload = {
            'client': 'wheel',
            'fun': 'key.accept',
            'match': minion_id,
        }
        result = self._send_request('post', '/', data=payload)
        assert minion_id in result['data']['return']['minions']
        logger.info('minion accepted')

    def reject(self, minion_id):
        payload = {
            'client': 'wheel',
            'fun': 'key.reject',
            'match': minion_id,
        }
        result = self._send_request('post', '/', data=payload)
        logger.info('minion rejected')
