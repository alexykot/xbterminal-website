from rest_framework.renderers import BaseRenderer


class PlainTextRenderer(BaseRenderer):

    media_type = 'text/plain'
    format = 'txt'

    def render(self, data, media_type=None, renderer_context=None):
        if isinstance(data, basestring):
            return data


class TarArchiveRenderer(BaseRenderer):

    media_type = 'application/gzip'
    format = 'tar.gz'
    charset = None
    render_style = 'binary'

    def render(self, data, media_type=None, renderer_context=None):
        return data


class PaymentRequestRenderer(BaseRenderer):

    media_type = 'application/bitcoin-paymentrequest'
    format = 'pp-req'
    charset = None
    render_style = 'binary'

    def render(self, data, media_type=None, renderer_context=None):
        return data


class PaymentACKRenderer(BaseRenderer):

    media_type = 'application/bitcoin-paymentack'
    format = 'pp-ack'
    charset = None
    render_style = 'binary'

    def render(self, data, media_type=None, renderer_context=None):
        return data
