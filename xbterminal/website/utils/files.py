import base64
import mimetypes
import os
import re

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible

from slugify import slugify


def verification_file_path_gen(instance, filename):
    """
    Accepts:
        instance: KYCDocument instance
        filename: file name
    """
    merchant_id = instance.merchant.id
    filename, ext = os.path.splitext(filename)
    prefixed = '{0}__{1}{2}'.format(
        instance.document_type,
        slugify(filename, separator='_'),
        ext.encode('ascii', 'ignore'))
    path = os.path.join('verification', str(merchant_id), prefixed)
    return path


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


def decode_base64(data):
    """
    Accepts:
        data: base64 encoded file, string
    Returns:
        ContentFile instance
    """
    match = re.match(r'^data:(?P<type>.+?);base64,(?P<content>.+)$',
                     data.strip())
    mimetype = match.group('type')
    b64_content = match.group('content')
    extension = mimetypes.guess_extension(mimetype)
    assert extension
    file_name = b64_content[:8].encode('hex') + extension
    file = ContentFile(base64.b64decode(b64_content),
                       name=file_name)
    return file


# TODO: remove storage class

@deconstructible
class VerificationFileStorage(FileSystemStorage):

    def __init__(self, **kwargs):
        kwargs['location'] = os.path.join(settings.MEDIA_ROOT,
                                          'verification')
        kwargs['base_url'] = '/verification/'
        super(VerificationFileStorage, self).__init__(**kwargs)
