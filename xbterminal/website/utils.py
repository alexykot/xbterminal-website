from cStringIO import StringIO
import unicodecsv
from zipfile import ZipFile
from decimal import Decimal

import qrcode

from django.core.mail import EmailMessage
from django.conf import settings
from django.template.loader import render_to_string
from django.db.models import Sum

from api.shotcuts import generate_pdf

TRANSACTION_CSV_FIELDS = (
    ('transaction id', 'id'),
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
    ('destination address', 'dest_address')
)


def get_transaction_csv(transactions, csv_file=None):
    if csv_file is None:
        csv_file = StringIO()
    writer = unicodecsv.writer(csv_file, encoding='utf-8')
    # Write header
    field_name_row = [field[0] for field in TRANSACTION_CSV_FIELDS]
    writer.writerow(field_name_row)
    # Write data
    field_names = [field[1] for field in TRANSACTION_CSV_FIELDS]
    for transaction in transactions:
        row = []
        for field in field_names:
            if isinstance(field, str):
                value = getattr(transaction, field)
            else:
                value = field(transaction)
            if isinstance(value, Decimal):
                value = '{0:g}'.format(float(value))
            row.append(unicode(value))
        writer.writerow(row)
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


def send_reconciliation(recipient, device, rec_range):
    transactions = device.transaction_set.filter(time__range=rec_range)
    btc_sum = transactions.aggregate(sum=Sum('btc_amount'))['sum']
    fiat_sum = transactions.aggregate(sum=Sum('fiat_amount'))['sum']

    mail_text = render_to_string('website/email/reconciliation.txt', {
        'device': device,
        'transactions': transactions,
        'btc_amount': 0 if btc_sum is None else btc_sum,
        'fiat_amount': 0 if fiat_sum is None else fiat_sum,
        'rec_datetime': rec_range[1],
    })

    email = EmailMessage(
        'XBTerminal reconciliation report, {0}'.format(rec_range[1].strftime('%d %b %Y')),
        mail_text,
        settings.DEFAULT_FROM_EMAIL,
        [recipient])

    if transactions:
        csv = get_transaction_csv(transactions)
        csv.seek(0)
        email.attach('transactions.csv', csv.read(), 'text/csv')

        archive = get_transaction_pdf_archive(transactions)
        email.attach('receipts.zip', archive.getvalue(), 'application/x-zip-compressed')

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
