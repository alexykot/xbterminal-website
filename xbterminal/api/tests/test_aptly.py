from mock import Mock, patch
from django.test import TestCase
from django.test.utils import override_settings

from api.utils import aptly


@override_settings(APTLY_SERVERS={
    'default': {
        'HOST': 'http://test',
        'CLIENT_CERT': 'test',
        'CLIENT_KEY': 'test',
    },
})
class AptlyTestCase(TestCase):

    @patch('api.utils.aptly.requests.get')
    def test_get_xbtfw_latest_version(self, get_mock):
        get_mock.return_value = Mock(**{
            'json.return_value': [
                {'Version': '0.9.1'},
                {'Version': '0.9.2'},
            ],
        })
        latest = aptly.get_latest_xbtfw_version()
        self.assertEqual(latest, '0.9.2')
        self.assertEqual(
            get_mock.call_args[0][0],
            'http://test/api/repos/xbtfw-wandboard-dev/packages')
