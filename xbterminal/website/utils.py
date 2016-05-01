# TODO: move all functions to website.utils package
import base64
from cStringIO import StringIO
import os
import unicodecsv
from zipfile import ZipFile
from decimal import Decimal

import qrcode

from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.utils.html import strip_tags
from django.utils.text import get_valid_filename
from django.template.loader import render_to_string
from django.db.models import Sum, F
from django.utils.translation import ugettext as _

from api.utils.pdf import generate_pdf

REPORT_FIELDS = [
    ('ID', 'id'),
    ('datetime', lambda p: p.time_notified.strftime('%d-%b-%Y %l:%M %p')),
    ('POS', lambda p: p.device.name),
    ('currency', 'fiat_currency'),
    ('amount', lambda p: "{0:.2f}".format(p.fiat_amount)),
    ('amount mBTC', lambda p: "{0:.5f}".format(p.scaled_btc_amount)),
    ('exchange rate', lambda p: "{0:.4f}".format(p.scaled_effective_exchange_rate)),
    ('incoming transactions', lambda p: '\n'.join(p.incoming_tx_ids)),
    ('outgoing transactions', 'outgoing_tx_id'),
]

REPORT_FIELDS_SHORT = [
    ('ID', 'id'),
    ('datetime', lambda t: t.time_notified.strftime('%d-%b-%Y %l:%M %p')),
    ('currency', 'fiat_currency'),
    ('amount', 'fiat_amount'),
]


def get_report_csv(payment_orders, csv_file=None, short=False):
    if csv_file is None:
        csv_file = StringIO()
    writer = unicodecsv.writer(csv_file, encoding='utf-8')
    fields = REPORT_FIELDS_SHORT if short else REPORT_FIELDS
    # Write header
    field_names = [field[0] for field in fields]
    writer.writerow(field_names)
    # Write data
    totals = {
        'amount': Decimal(0),
        'amount mBTC': Decimal(0),
    }
    for payment_order in payment_orders:
        row = []
        for field_name, field_getter in fields:
            if isinstance(field_getter, str):
                value = getattr(payment_order, field_getter)
            else:
                value = field_getter(payment_order)
            if field_name in totals:
                totals[field_name] += Decimal(value)
            row.append(unicode(value))
        writer.writerow(row)
    # Write totals
    totals_row = []
    for field_name in field_names:
        if field_name in totals:
            value = '{0:g}'.format(totals[field_name])
        else:
            value = ''
        totals_row.append(value)
    writer.writerow(totals_row)
    return csv_file


def get_receipts_archive(payment_orders, to_file=None):
    if to_file is None:
        to_file = StringIO()
    archive = ZipFile(to_file, "w")

    for payment_order in payment_orders:
        result = generate_pdf(
            'pdf/receipt.html',
            {'order': payment_order})
        archive.writestr(
            'receipt #{0}.pdf'.format(payment_order.id),
            result.getvalue())
        result.close()

    archive.close()

    return to_file


def get_report_filename(device, date=None):
    s = "XBTerminal transactions, {0}".format(
        device.merchant.company_name)
    if date is not None:
        s += ", {0}".format(date.strftime('%d %b %Y'))
    s += ".csv"
    return get_valid_filename(s)


def get_receipts_archive_filename(device, date=None):
    s = "XBTerminal receipts, {0}".format(
        device.merchant.company_name)
    if date is not None:
        s += ", {0}".format(date.strftime('%d %b %Y'))
    s += ".zip"
    return get_valid_filename(s)


def create_html_message(subject, template, context,
                        from_email, recipient_list,
                        attachments=None):
    html_content = render_to_string(template, context)
    text_content = strip_tags(html_content)
    email = EmailMultiAlternatives(
        subject, text_content, from_email, recipient_list)
    email.attach_alternative(html_content, 'text/html')
    if attachments:
        for file_name, file_data, file_type in attachments:
            email.attach(file_name, file_data, file_type)
    return email


def send_reconciliation(recipient, device, rec_range):
    """
    Send reconciliation email
    """
    payment_orders = device.get_payments_by_date(rec_range)
    btc_sum = payment_orders.aggregate(sum=Sum(
        F('merchant_btc_amount') +
        F('instantfiat_btc_amount') +
        F('fee_btc_amount') +
        F('tx_fee_btc_amount')))['sum']
    fiat_sum = payment_orders.aggregate(sum=Sum('fiat_amount'))['sum']
    context = {
        'device': device,
        'payment_orders': payment_orders,
        'btc_amount': 0 if btc_sum is None else btc_sum,
        'fiat_amount': 0 if fiat_sum is None else fiat_sum,
        'rec_datetime': rec_range[1],
    }
    attachments = []
    if payment_orders:
        csv = get_report_csv(payment_orders, short=True)
        csv.seek(0)
        csv_data = csv.read()
        csv_filename = get_report_filename(device, rec_range[1])
        with open(os.path.join(settings.REPORTS_PATH, csv_filename), 'w') as f:
            f.write(csv_data)
        attachments.append([csv_filename, csv_data, 'text/csv'])
        archive = get_receipts_archive(payment_orders)
        archive_data = archive.getvalue()
        archive_filename = get_receipts_archive_filename(device, rec_range[1])
        attachments.append([archive_filename, archive_data, 'application/x-zip-compressed'])
        with open(os.path.join(settings.REPORTS_PATH, archive_filename), 'wb') as f:
            f.write(archive_data)
    email = create_html_message(
        _('XBTerminal reconciliation report, {0}').format(rec_range[1].strftime('%d %b %Y')),
        'email/reconciliation.html',
        context,
        settings.DEFAULT_FROM_EMAIL,
        [recipient],
        attachments=attachments)
    email.send(fail_silently=False)


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


def send_error_message(tb=None, order=None):
    """
    Accepts:
        tb: traceback object
        order: PaymentOrder or WithdrawalOrder instance
    """
    email = create_html_message(
        'XBTerminal - error',
        'email/error.html',
        {'traceback': tb, 'order': order},
        settings.DEFAULT_FROM_EMAIL,
        settings.CONTACT_EMAIL_RECIPIENTS)
    email.send(fail_silently=False)


def send_registration_email(email, password):
    """
    Send merchant registration email
    """
    message = create_html_message(
        _('Registration for XBTerminal.io'),
        'email/registration.html',
        {'email': email, 'password': password},
        settings.DEFAULT_FROM_EMAIL,
        [email])
    message.send(fail_silently=False)


def send_registration_info(merchant):
    """
    Send merchant registration info (for admin)
    """
    context = {
        'merchant': merchant,
    }
    email = create_html_message(
        'XBTerminal registration info',
        'email/registration_info.html',
        context,
        settings.DEFAULT_FROM_EMAIL,
        settings.CONTACT_EMAIL_RECIPIENTS)
    email.send(fail_silently=False)


def send_reset_password_email(email, password):
    message = create_html_message(
        _('Reset password for xbterminal.io'),
        'email/reset_password.html',
        {'password': password},
        settings.DEFAULT_FROM_EMAIL,
        [email])
    message.send(fail_silently=False)


def send_contact_email(form_data):
    message = create_html_message(
        _('Message from xbterminal.io'),
        'email/contact.html',
        form_data,
        settings.DEFAULT_FROM_EMAIL,
        settings.CONTACT_EMAIL_RECIPIENTS)
    message.send(fail_silently=False)


def send_feedback_email(form_data):
    message = create_html_message(
        _('Message from xbterminal.io'),
        'email/feedback.html',
        form_data,
        settings.DEFAULT_FROM_EMAIL,
        settings.CONTACT_EMAIL_RECIPIENTS)
    message.send(fail_silently=False)


def send_balance_admin_notification(info):
    """
    Send email to admin if balance mismatch detected
    Accepts:
        info: dict
    """
    email = create_html_message(
        _('Balance mismatch'),
        'email/admin_balance_notification.html',
        {'info': info},
        settings.DEFAULT_FROM_EMAIL,
        settings.CONTACT_EMAIL_RECIPIENTS)
    email.send(fail_silently=False)
