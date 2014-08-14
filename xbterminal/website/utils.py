from cStringIO import StringIO
import os
import unicodecsv
from zipfile import ZipFile
from decimal import Decimal

import qrcode

from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.conf import settings
from django.utils.html import strip_tags
from django.utils.text import get_valid_filename
from django.template.loader import render_to_string
from django.db.models import Sum

from constance import config

from api.shortcuts import generate_pdf

REPORT_FIELDS = [
    ('ID', 'id'),
    ('datetime', lambda t: t.time.strftime('%d-%b-%Y %l:%M %p')),
    ('device name', lambda t: t.device.name),
    ('amount', 'fiat_amount'),
    ('currency', 'fiat_currency'),
    ('amount mBTC', lambda t: "{0:.2f}".format(t.scaled_btc_amount())),
    ('exchange rate', lambda t: "{0:.4f}".format(t.scaled_exchange_rate())),
    ('fee mBTC', 'fee_btc_amount'),
    ('effective exchange rate', lambda t: t.scaled_effective_exchange_rate()),
    ('total mBTC', lambda t: t.scaled_total_btc_amount()),
    ('amount converted', 'instantfiat_fiat_amount'),
    ('amount converted BTC', 'instantfiat_btc_amount'),
    ('processor invoice ID', lambda t: t.instantfiat_invoice_id or 'N/A'),
    ('transction bitcoin ID #2', 'bitcoin_transaction_id_2'),
    ('destination address', 'dest_address'),
]

REPORT_FIELDS_SHORT = [
    ('ID', 'id'),
    ('datetime', lambda t: t.time.strftime('%d-%b-%Y %l:%M %p')),
    ('amount', 'fiat_amount'),
    ('currency', 'fiat_currency'),
]


def get_transaction_csv(transactions, csv_file=None, short=False):
    if csv_file is None:
        csv_file = StringIO()
    writer = unicodecsv.writer(csv_file, encoding='utf-8')
    fields = REPORT_FIELDS_SHORT if short else REPORT_FIELDS
    # Write header
    field_names = [field[0] for field in fields]
    writer.writerow(field_names)
    # Write data
    totals = {}
    for transaction in transactions:
        row = []
        for field_name, field_getter in fields:
            if isinstance(field_getter, str):
                value = getattr(transaction, field_getter)
            else:
                value = field_getter(transaction)
            if isinstance(value, Decimal):
                if field_name not in totals:
                    totals[field_name] = Decimal(0)
                totals[field_name] += value
                value = '{0:g}'.format(float(value))
            row.append(unicode(value))
        writer.writerow(row)
    # Write totals
    totals_row = []
    for field_name in field_names:
        if field_name in totals:
            value = '{0:g}'.format(float(totals[field_name]))
        else:
            value = ''
        totals_row.append(value)
    writer.writerow(totals_row)
    return csv_file


def get_transaction_pdf_archive(transactions, to_file=None):
    if to_file is None:
        to_file = StringIO()
    archive = ZipFile(to_file, "w")

    for transaction in transactions:
        result = generate_pdf(
            'api/transaction.html',
            {'transaction': transaction})
        archive.writestr('receipt #%s.pdf' % transaction.id, result.getvalue())
        result.close()

    archive.close()

    return to_file


def get_transactions_filename(device, date=None):
    s = "XBTerminal transactions, {0}".format(
        device.merchant.company_name)
    if date is not None:
        s += ", {0}".format(date.strftime('%d %b %Y'))
    s += ".csv"
    return get_valid_filename(s)


def get_receipts_filename(device, date=None):
    s = "XBTerminal receipts, {0}".format(
        device.merchant.company_name)
    if date is not None:
        s += ", {0}".format(date.strftime('%d %b %Y'))
    s += ".zip"
    return get_valid_filename(s)


def create_html_message(subject, template, context,
                        from_email, recipient_list):
    html_content = render_to_string(template, context)
    text_content = strip_tags(html_content)
    email = EmailMultiAlternatives(
        subject, text_content, from_email, recipient_list)
    email.attach_alternative(html_content, 'text/html')
    return email


def send_reconciliation(recipient, device, rec_range):
    """
    Send reconciliation email
    """
    transactions = device.transaction_set.filter(time__range=rec_range)
    btc_sum = transactions.aggregate(sum=Sum('btc_amount'))['sum']
    fiat_sum = transactions.aggregate(sum=Sum('fiat_amount'))['sum']
    context = {
        'device': device,
        'transactions': transactions,
        'btc_amount': 0 if btc_sum is None else btc_sum,
        'fiat_amount': 0 if fiat_sum is None else fiat_sum,
        'rec_datetime': rec_range[1],
    }
    email = create_html_message(
        'XBTerminal reconciliation report, {0}'.format(rec_range[1].strftime('%d %b %Y')),
        'website/email/reconciliation.html',
        context,
        settings.DEFAULT_FROM_EMAIL,
        [recipient])
    if transactions:
        csv = get_transaction_csv(transactions, short=True)
        csv.seek(0)
        csv_data = csv.read()
        csv_filename = get_transactions_filename(device, rec_range[1])
        with open(os.path.join(settings.REPORTS_PATH, csv_filename), 'w') as f:
            f.write(csv_data)
        email.attach(csv_filename, csv_data, "text/csv")
        archive = get_transaction_pdf_archive(transactions)
        archive_data = archive.getvalue()
        archive_filename = get_receipts_filename(device, rec_range[1])
        email.attach(archive_filename, archive_data, "application/x-zip-compressed")
        with open(os.path.join(settings.REPORTS_PATH, archive_filename), 'wb') as f:
            f.write(archive_data)
    email.send(fail_silently=False)


def generate_qr_code(text, size=4):
    """
    Generate base64-encoded QR code
    """
    qr_output = StringIO()
    qr_code = qrcode.make(text, box_size=size)
    qr_code.save(qr_output, "PNG")
    qr_code_src = "data:image/png;base64,{0}".format(
        qr_output.getvalue().encode("base64"))
    qr_output.close()
    return qr_code_src


def send_invoice(order):
    message_text = render_to_string(
        "website/email/order.txt",
        {'order': order})
    message = EmailMessage(
        "Your XBTerminal Pre-Order",
        message_text,
        settings.DEFAULT_FROM_EMAIL,
        [order.merchant.contact_email])
    if order.payment_method == 'wire':
        pdf = generate_pdf("pdf/invoice.html", {
            'order': order,
            'terminal_price': config.TERMINAL_PRICE,
        })
        message.attach('invoice.pdf', pdf.getvalue(), 'application/pdf')
    message.send(fail_silently=False)
