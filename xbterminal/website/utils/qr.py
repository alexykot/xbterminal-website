import base64
from cStringIO import StringIO
import qrcode


def generate_qr_code(text, size=4):
    """
    Generate base64-encoded QR code
    """
    qr_output = StringIO()
    qr_code = qrcode.make(text, box_size=size)
    qr_code.save(qr_output, "PNG")
    qr_code_src = "data:image/png;base64,{0}".format(
        base64.b64encode(qr_output.getvalue()))
    qr_output.close()
    return qr_code_src
