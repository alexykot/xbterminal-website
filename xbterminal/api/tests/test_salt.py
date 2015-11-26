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
    def test_upgrade(self, send_mock):
        salt = Salt()
        salt.upgrade('m1', '0.00')
        self.assertTrue(send_mock.called)

    @patch('api.utils.salt.Salt._send_request')
    def test_reboot(self, send_mock):
        salt = Salt()
        salt.reboot('m1')
        self.assertTrue(send_mock.called)
