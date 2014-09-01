import os
import re
import unicodedata

from django.utils.encoding import filepath_to_uri


def get_verification_file_name(file):
    match = re.match('^[12]__(.*)$', os.path.basename(file.name))
    filename = match.group(1)
    return unicodedata.normalize('NFKD', filename).encode('ascii', 'ignore')


def get_verification_file_info(file):
    filename = get_verification_file_name(file)
    path = filepath_to_uri(file.name)
    return filename, path
