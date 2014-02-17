from cStringIO import StringIO
import unicodecsv
from zipfile import ZipFile
from decimal import Decimal

from django.core.mail import EmailMessage
from django.conf import settings
from django.template.loader import render_to_string
from django.db.models import Sum

from api.shotcuts import generate_pdf

TRANSACTION_CSV_FIELDS = (
    ('transaction id', 'id'),
    ('datetime', 'time'),
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
        archive.writestr('receipt #%s.pdf' % transaction.id, result.getvalue())
        result.close()

    archive.close()

    return f


def send_reconciliation(email, device, date):
    transactions = device.get_transactions_by_date(date)

    mail_text = render_to_string('website/email/reconciliation.txt', {
        'device': device,
        'transactions': transactions,
        'amount': transactions.aggregate(sum=Sum('btc_amount'))['sum']
    })

    formated_date = date.strftime('%d %b %Y')
    email = EmailMessage(
        'Reconciliation for %s' % formated_date,
        mail_text,
        settings.DEFAULT_FROM_EMAIL,
        [email]
    )

    if transactions:
        csv = get_transaction_csv(transactions)
        csv.seek(0)
        csv_name = '%s - transactions.csv' % formated_date
        email.attach(csv_name, csv.read(), 'text/csv')

        archive = get_transaction_pdf_archive(transactions)
        archive_name = '%s - receipts.zip' % formated_date
        email.attach(archive_name, archive.getvalue(), 'application/x-zip-compressed')

    email.send()
