import tarfile

from django.test import TestCase

from website.tests.factories import DeviceBatchFactory
from website.utils import get_batch_info_archive


class GetBatchInfoArchiveTestCase(TestCase):

    def test_func(self):
        batch = DeviceBatchFactory.create()
        result = get_batch_info_archive(batch)
        result.seek(0)

        with tarfile.open(fileobj=result, mode='r:gz') as archive:
            members = archive.getmembers()
            self.assertEqual(len(members), 1)
            self.assertEqual(
                members[0].name,
                '/srv/xbterminal/xbterminal/runtime/batch_number')
            batch_number_file = archive.extractfile(members[0])
            self.assertEqual(batch_number_file.read(),
                             batch.batch_number)
            batch_number_file.close()
