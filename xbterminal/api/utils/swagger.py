import os

from django.conf import settings


def get_spec(version):
    spec_path = os.path.join(
        settings.SWAGGER_SPEC_PATH,
        'api_v{0}.yml'.format(version))
    with open(spec_path, 'r') as spec_file:
        return spec_file.read()
