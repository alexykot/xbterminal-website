import json
import os.path
import logging
import time
from urlparse import urljoin
from django.conf import settings

import requests

logger = logging.getLogger(__name__)


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
        response = requests.request(method.upper(),
                                    urljoin(self.config['HOST'], url),
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

    def upgrade(self, minion_id, version, timeout=60):
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
        jid = result['jid']
        # Wait for result
        state = 'pkg_|-xbterminal-firmware_|-xbterminal-firmware_|-installed'
        start_time = time.time()
        interval = 3
        while time.time() < start_time + timeout:
            job_info = self._lookup_jid(jid)
            if 'data' in job_info:
                assert job_info['data'][minion_id][state]['result']
                logger.info('device upgraded')
                return
            time.sleep(interval)
        raise SaltTimeout

    def reboot(self, minion_id, timeout=120):
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
        # Wait for device to shut down
        start_time = time.time()
        interval = 3
        while time.time() < start_time + timeout:
            if not self.ping(minion_id):
                # Wait for device to boot
                while time.time() < start_time + timeout:
                    if self.ping(minion_id):
                        logger.info('device rebooted')
                        return
                    time.sleep(interval)
                raise SaltTimeout
            time.sleep(interval)
        raise SaltTimeout
