from mock import Mock, patch
from django.test import TestCase
from django.test.utils import override_settings

from api.utils import aptly


@override_settings(APTLY_SERVERS={
    'default': {
        'HOST': 'https://test',
        'CLIENT_CERT': 'test',
        'CLIENT_KEY': 'test',
        'CA_CERT': 'test',
    },
})
class AptlyTestCase(TestCase):

    @patch('api.utils.aptly.requests.get')
    def test_get_latest_version(self, get_mock):
        get_mock.return_value = Mock(**{
            'json.return_value': [{
                'Version': '0.9.6.20160822-b1-master-r0.0',
            }],
        })
        latest = aptly.get_latest_version('qemuarm', 'xbterminal-gui')
        self.assertEqual(latest, '0.9.6.20160822-b1-master-r0.0')
        self.assertEqual(
            get_mock.call_args[0][0],
            'https://test/api/repos/xbtfw-qemuarm-dev/packages')
