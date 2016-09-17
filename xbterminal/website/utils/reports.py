from cStringIO import StringIO
import unicodecsv
from decimal import Decimal

from django.utils.text import get_valid_filename


def get_report_csv(transactions, csv_file=None):
    if csv_file is None:
        csv_file = StringIO()
    writer = unicodecsv.writer(csv_file, encoding='utf-8')
    # Write header
    writer.writerow(['ID', 'Date', 'Currency', 'Amount'])
    # Write data
    total_amount = Decimal(0)
    for transaction in transactions:
        row = [
            transaction.pk,
            transaction.created_at.strftime('%d-%b-%Y %l:%M %p'),
            transaction.account.currency.name,
            transaction.amount,
        ]
        total_amount += transaction.amount
        writer.writerow(row)
    # Write totals
    writer.writerow(['', '', '', total_amount])
    return csv_file


def get_report_filename(device_or_account, date=None):
    s = "XBTerminal transactions, {0}".format(
        device_or_account.merchant.company_name)
    if date is not None:
        s += ", {0}".format(date.strftime('%d %b %Y'))
    s += ".csv"
    return get_valid_filename(s)
