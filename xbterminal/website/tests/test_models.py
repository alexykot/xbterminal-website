from django.test import TestCase

from website.models import User
from website.tests.factories import UserFactory


class UserTestCase(TestCase):

    def test_create_user(self):
        user = UserFactory.create()
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertTrue(user.check_password('password'))

    def test_get_full_name(self):
        user = UserFactory.create()
        self.assertEqual(user.get_full_name(), user.email)
