import json
import os.path
import logging
from django.conf import settings

import requests

logger = logging.getLogger(__name__)


class Salt(object):

    def __init__(self, server='default'):
        self.config = settings.SALT_SERVERS[server]
        self._auth_token = None

    def _send_request(self, method, url,
                      params=None, data=None,
                      jsonify=True):
        headers = {
            'Accept': 'application/json',
        }
        if self._auth_token:
            headers['X-Auth-Token'] = self._auth_token
        if jsonify:
            headers['Content-Type'] = 'application/json'
            data = json.dumps(data)
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
        result = self._send_request('post', '/login', data=payload, jsonify=False)
        self._auth_token = result['token']
        logger.info('login successful')

    def check_fingerprint(self, minion_id, fingerprint):
        """
        https://docs.saltstack.com/en/2015.5/ref/wheel/all
            /salt.wheel.key.html#salt.wheel.key.finger
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

    def delete(self, minion_id):
        payload = {
            'client': 'wheel',
            'fun': 'key.delete',
            'match': minion_id,
        }
        result = self._send_request('post', '/', data=payload)
        logger.info('minion deleted')

    def upgrade(self, minion_id, version):
        """
        https://docs.saltstack.com/en/2015.5/ref/modules/all
            /salt.modules.state.html#salt.modules.state.highstate
        """
        payload = {
            'client': 'local_async',
            'fun': 'state.highstate',
            'tgt': minion_id,
            'kwarg': {
                'pillar': {
                    'xbt': {
                        'version': version,
                    },
                },
            },
        }
        result = self._send_request('post', '/', data=payload)
        logger.info('job id {0}'.format(result['jid']))
