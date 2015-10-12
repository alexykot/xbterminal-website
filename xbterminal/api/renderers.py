from rest_framework.renderers import BaseRenderer


class TarArchiveRenderer(BaseRenderer):

    media_type = 'application/gzip'
    format = 'tar.gz'
    charset = None
    render_style = 'binary'

    def render(self, data, media_type=None, renderer_context=None):
        return data
