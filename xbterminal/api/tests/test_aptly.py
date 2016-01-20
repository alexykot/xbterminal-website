from mock import Mock, patch
from django.test import TestCase
from django.test.utils import override_settings

from api.utils import aptly


@override_settings(APTLY_SERVERS={
    'default': {
        'HOST': 'http://test',
        'CLIENT_CERT': 'test',
        'CLIENT_KEY': 'test',
        'CA_CERT': 'test',
    },
})
class AptlyTestCase(TestCase):

    @patch('api.utils.aptly.requests.get')
    def test_get_latest_version(self, get_mock):
        get_mock.return_value = Mock(
            content='Package: xbterminal-firmware\n'
                    'Version: 0.9.1\n'
                    '\n'
                    'Package: xbterminal-firmware\n'
                    'Version: 0.9.2\n'
                    '\n'
                    'Package: test\n'
                    'Version: 1.0.0\n')
        latest = aptly.get_latest_version('qemuarm', 'xbterminal-firmware')
        self.assertEqual(latest, '0.9.2')
        self.assertEqual(
            get_mock.call_args[0][0],
            'http://test/repos/deb/jethro/xbtfw-qemuarm-dev/dists/poky/main/binary-armel/Packages')
