import cStringIO as StringIO

from django.template.loader import get_template
from django.template import Context
from django.http import HttpResponse

import xhtml2pdf.pisa as pisa


def generate_pdf(template_src, context_dict):
    template = get_template(template_src)
    context = Context(context_dict)
    html = template.render(context)
    result = StringIO.StringIO()
    pisa.pisaDocument(StringIO.StringIO(html.encode("utf-8")), result, encoding='utf-8')
    return result


def render_to_pdf(template_src, context_dict):
    result = generate_pdf(template_src, context_dict)
    return HttpResponse(result.getvalue(), mimetype='application/pdf')
