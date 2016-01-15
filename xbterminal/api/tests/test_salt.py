from mock import Mock, patch
from django.test import TestCase
from django.test.utils import override_settings

from api.utils.salt import Salt


@override_settings(SALT_SERVERS={
    'default': {
        'HOST': 'test',
        'USER': 'test',
        'PASSWORD': 'test',
        'CLIENT_CERT': 'test',
        'CLIENT_KEY': 'test',
    },
})
class SaltTestCase(TestCase):

    @patch('api.utils.salt.requests.request')
    def test_login(self, request_mock):
        request_mock.return_value = Mock(**{
            'json.return_value': {'return': [{'token': 'abc'}]},
        })
        salt = Salt()
        salt.login()
        self.assertEqual(salt._auth_token, 'abc')

    @patch('api.utils.salt.Salt._send_request')
    def test_check_fingerprint(self, send_mock):
        send_mock.return_value = {
            'data': {'return': {'minions_pre': {'m1': 'k1'}}},
        }
        salt = Salt()
        self.assertTrue(salt.check_fingerprint('m1', 'k1'))
        self.assertFalse(salt.check_fingerprint('m1', 'k2'))
        self.assertFalse(salt.check_fingerprint('m2', 'k2'))

        send_mock.return_value = {
            'data': {'return': {}},
        }
        salt = Salt()
        self.assertFalse(salt.check_fingerprint('m1', 'k1'))

    @patch('api.utils.salt.Salt._send_request')
    def test_accept(self, send_mock):
        send_mock.return_value = {
            'data': {'return': {'minions': ['m1']}},
        }
        salt = Salt()
        self.assertIsNone(salt.accept('m1'))
        with self.assertRaises(AssertionError):
            salt.accept('m2')

    @patch('api.utils.salt.Salt._send_request')
    def test_ping(self, send_mock):
        send_mock.return_value = {'m1': True}
        salt = Salt()
        self.assertTrue(salt.ping('m1'))
        self.assertFalse(salt.ping('m2'))

    @patch('api.utils.salt.Salt._send_request')
    def test_get_grain(self, send_mock):
        send_mock.return_value = {'m1': {'machine': 'qemuarm'}}
        salt = Salt()
        self.assertEqual(salt.get_grain('m1', 'machine'), 'qemuarm')
        with self.assertRaises(KeyError):
            salt.get_grain('m2', 'machine')

    @patch('api.utils.salt.Salt._send_request')
    @patch('api.utils.salt.Salt._lookup_jid')
    def test_highstate(self, lookup_jid_mock, send_mock):
        send_mock.return_value = {'jid': 'test'}
        lookup_jid_mock.return_value = {
            'data': {
                'm1': {
                    'pkg_|-xbterminal-firmware_|-xbterminal-firmware_|-installed': {
                        'result': True,
                    },
                },
            },
        }
        salt = Salt()
        salt.highstate('m1', {'test': 'test'})
        self.assertTrue(send_mock.called)
        payload = send_mock.call_args[1]['data']
        self.assertEqual(payload['kwarg']['pillar']['test'], 'test')
        self.assertTrue(lookup_jid_mock.called)
        self.assertEqual(lookup_jid_mock.call_args[0][0], 'test')

    @patch('api.utils.salt.Salt._send_request')
    def test_reboot(self, send_mock):
        send_mock.return_value = {'jid': 'test'}
        salt = Salt()
        salt.reboot('m1')
        self.assertTrue(send_mock.called)
