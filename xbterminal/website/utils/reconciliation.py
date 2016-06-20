from cStringIO import StringIO
import unicodecsv
from zipfile import ZipFile
from decimal import Decimal

from django.utils.text import get_valid_filename
from django.db.models import Sum, F

from api.utils.pdf import generate_pdf
from website.utils.email import send_reconciliation_email

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
    files = []
    if payment_orders:
        csv = get_report_csv(payment_orders, short=True)
        csv.seek(0)
        csv_data = csv.read()
        csv_filename = get_report_filename(device, rec_range[1])
        files.append([csv_filename, csv_data, 'text/csv'])
        archive = get_receipts_archive(payment_orders)
        archive_data = archive.getvalue()
        archive_filename = get_receipts_archive_filename(device, rec_range[1])
        files.append([archive_filename, archive_data, 'application/x-zip-compressed'])
    send_reconciliation_email(recipient, rec_range[1], context, files)
