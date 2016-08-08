import base64
import mimetypes
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
    normalized = unicodedata.normalize('NFKD', unicode(filename)).\
        encode('ascii', 'ignore')
    prefixed = '{0}__{1}'.format(instance.document_type, normalized)
    return os.path.join('verification', str(merchant_id), prefixed)


def get_verification_file_name(file):
    match = re.match('^[0-9]__(.*)$', os.path.basename(file.name))
    return match.group(1)


def encode_base64(file):
    """
    Accepts:
        file: file-like object
    Returns:
        string
    """
    mimetype, encoding = mimetypes.guess_type(file.name)
    assert mimetype
    data = 'data:{mimetype};base64,{content}'.format(
        mimetype=mimetype,
        content=base64.b64encode(file.read()))
    return data


# TODO: remove storage class

@deconstructible
class VerificationFileStorage(FileSystemStorage):

    def __init__(self, **kwargs):
        kwargs['location'] = os.path.join(settings.MEDIA_ROOT,
                                          'verification')
        kwargs['base_url'] = '/verification/'
        super(VerificationFileStorage, self).__init__(**kwargs)
