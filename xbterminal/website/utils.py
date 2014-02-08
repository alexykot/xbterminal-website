from cStringIO import StringIO
import unicodecsv
from zipfile import ZipFile
from decimal import Decimal

from django.core.mail import EmailMessage
from django.conf import settings

from api.shotcuts import generate_pdf

TRANSACTION_CSV_FIELDS = (
    ('transaction id', 'id'),
    ('datetime', 'time'),
    ('device name', lambda t: t.device.name),
    ('amount', 'fiat_amount'),
    ('currency', 'fiat_currency'),
    ('amount mBTC', lambda t: t.scaled_btc_amount()),
    ('exchange rate', lambda t: t.scaled_exchange_rate()),
    ('fee mBTC', 'fee_btc_amount'),
    ('effective exchange rate', lambda t: t.scaled_effective_exchange_rate()),
    ('total mBTC', lambda t: t.scaled_total_btc_amount()),
    ('amount converted', 'instantfiat_fiat_amount'),
    ('amount converted BTC', 'instantfiat_btc_amount'),
    ('cryptopay invoice ID', 'instantfiat_invoice_id'),
    ('transction bitcoin ID #2', 'bitcoin_transaction_id_2'),
    ('destination address', 'dest_address')
)


def get_transaction_csv(transactions, csv_file=None):
    if csv_file is None:
        csv_file = StringIO()
    writer = unicodecsv.writer(csv_file, encoding='utf-8')

    field_name_row = [field[0] for field in TRANSACTION_CSV_FIELDS]
    writer.writerow(field_name_row)

    field_names = [field[1] for field in TRANSACTION_CSV_FIELDS]
    for transaction in transactions:
        row = []
        for field in field_names:
            value = getattr(transaction, field) if isinstance(field, str) else field(transaction)
            if isinstance(value, Decimal):
                value = '{0:g}'.format(float(value))
            row.append(unicode(value))

        writer.writerow(row)

    return csv_file


def get_transaction_pdf_archive(transactions):
    f = StringIO()
    archive = ZipFile(f, "w")

    for transaction in transactions:
        result = generate_pdf(
            'api/transaction.html', {
                'transaction': transaction,
                'STATIC_ROOT': settings.STATIC_ROOT
            }
        )
        archive.writestr('receipt #%s' % transaction.id, result.getvalue())
        result.close()

    archive.close()

    return f


def send_reconciliation(email, device, date):
    email = EmailMessage(
        'Reconciliation',
        '',
        settings.DEFAULT_FROM_EMAIL,
        [email]
    )

    transactions = device.get_transactions_by_date(date)

    csv = get_transaction_csv(transactions)
    csv.seek(0)
    email.attach('reconciliation.csv', csv.read(), 'text/csv')

    archive = get_transaction_pdf_archive(transactions)
    email.attach('receipts.zip', archive.getvalue(), 'application/x-zip-compressed')

    email.send()
