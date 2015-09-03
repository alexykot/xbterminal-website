import os
import re
import unicodedata

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible


def verification_file_path_gen(instance, filename):
    """
    Accepts:
        instance: KYCDocument instance
        filename: filename
    """
    merchant_id = instance.merchant.id
    normalized = unicodedata.normalize('NFKD', filename).encode('ascii', 'ignore')
    prefixed = '{0}__{1}'.format(instance.document_type, normalized)
    return os.path.join(str(merchant_id), prefixed)


def get_verification_file_name(file):
    match = re.match('^[12]__(.*)$', os.path.basename(file.name))
    return match.group(1)


@deconstructible
class VerificationFileStorage(FileSystemStorage):

    def __init__(self, **kwargs):
        kwargs['location'] = os.path.join(settings.MEDIA_ROOT,
                                          'verification')
        kwargs['base_url'] = '/verification/'
        super(VerificationFileStorage, self).__init__(**kwargs)
