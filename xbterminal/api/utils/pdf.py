import cStringIO as StringIO

from django.conf import settings
from django.template.loader import get_template

import xhtml2pdf.pisa as pisa


def generate_pdf(template_src, context_dict):
    template = get_template(template_src)
    html = template.render(context_dict)
    result = StringIO.StringIO()
    pisa.CreatePDF(
        src=html.encode("utf-8"),
        dest=result,
        encoding='utf-8',
        path=settings.BASE_DIR)
    return result
