import json
import os.path
import logging
import time
from urlparse import urljoin
from django.conf import settings

import requests

logger = logging.getLogger(__name__)


class SaltError(Exception):
    pass


class SaltTimeout(Exception):
    pass


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
        ca_cert = os.path.join(settings.CERT_PATH, self.config['CA_CERT'])
        response = requests.request(method.upper(),
                                    urljoin(self.config['HOST'], url),
                                    params=params,
                                    data=data,
                                    headers=headers,
                                    cert=certs,
                                    verify=ca_cert)
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

    def _lookup_jid(self, jid):
        """
        https://docs.saltstack.com/en/latest/ref/runners/all
            /salt.runners.jobs.html#salt.runners.jobs.lookup_jid
        """
        payload = {
            'client': 'runner',
            'fun': 'jobs.lookup_jid',
            'args': [jid],
        }
        result = self._send_request('post', '/', data=payload)
        return result

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

    def ping(self, minion_id):
        payload = {
            'client': 'local',
            'fun': 'test.ping',
            'tgt': minion_id,
        }
        result = self._send_request('post', '/', data=payload)
        return result.get(minion_id, False)

    def get_grain(self, minion_id, key):
        payload = {
            'client': 'local',
            'fun': 'grains.item',
            'tgt': minion_id,
            'arg': [key],
        }
        result = self._send_request('post', '/', data=payload)
        return result[minion_id].get(key)

    def highstate(self, minion_id, pillar_data, timeout=60):
        """
        https://docs.saltstack.com/en/2015.5/ref/modules/all
            /salt.modules.state.html#salt.modules.state.highstate
        """
        payload = {
            'client': 'local_async',
            'fun': 'state.highstate',
            'tgt': minion_id,
            'kwarg': {
                'pillar': pillar_data,
            },
        }
        result = self._send_request('post', '/', data=payload)
        jid = result['jid']
        # Wait for result
        start_time = time.time()
        interval = 3
        while time.time() < start_time + timeout:
            job_info = self._lookup_jid(jid)
            try:
                results = job_info['data'][minion_id]
            except KeyError:
                # Minion is not ready yet
                pass
            else:
                # Parse results
                errors = []
                if isinstance(results, list):
                    errors = results
                else:
                    for state, result in results.items():
                        if not result['result']:
                            errors.append(result['comment'])
                if errors:
                    raise SaltError(errors)
                else:
                    logger.info('highstate executed')
                    return
            time.sleep(interval)
        raise SaltTimeout

    def reboot(self, minion_id):
        """
        https://docs.saltstack.com/en/2015.5/ref/modules/all
            /salt.modules.system.html#salt.modules.system.reboot
        """
        payload = {
            'client': 'local_async',
            'fun': 'system.reboot',
            'tgt': minion_id,
        }
        self._send_request('post', '/', data=payload)
        logger.info('device {} is going to reboot'.format(minion_id))
