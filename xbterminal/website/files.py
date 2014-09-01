import os
import re

from django.utils.encoding import filepath_to_uri


def get_verification_file_info(file):
    match = re.match('^[12]__(.*)$', os.path.basename(file.name))
    filename = match.group(1).encode('ascii', 'ignore')
    path = filepath_to_uri(file.name)
    return filename, path
