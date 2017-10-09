from django.test import TestCase

from wallet.utils.keys import create_master_key, is_valid_master_key


class KeyUtilsTestCase(TestCase):

    def test_is_valid_master_key(self):
        master_key = create_master_key(2222)
        key_1 = master_key.hwif(as_private=True)
        self.assertIs(is_valid_master_key(key_1), True)
        # Public key
        key_2 = master_key.hwif()
        self.assertIs(is_valid_master_key(key_2), False)
        # Child key
        key_3 = master_key.subkey_for_path("0'/0'").hwif(as_private=True)
        self.assertIs(is_valid_master_key(key_3), False)
