from django.core.urlresolvers import reverse
from django.forms.widgets import (
    Widget,
    Select,
    FileInput)
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from website.utils.files import get_verification_file_name
from transactions.services import blockcypher


class FileWidget(FileInput):

    def render(self, name, value, attrs=None):
        template = '''
            <div class="file-widget">
                <div class="file-dd">
                    Drag and drop here or click to browse files {0}
                </div>
                <div class="progress">
                    <div class="progress-bar" role="progressbar"></div>
                </div>
                <ul class="file-uploaded">{1}</ul>
            </div>'''
        file_input = super(FileWidget, self).render(name, value, attrs)
        if value:
            list_item = format_html(
                '<li>{0}<a class="glyphicon glyphicon-remove file-remove"></a></li>',
                get_verification_file_name(value))
        else:
            list_item = ''
        output = format_html(template, file_input, list_item)
        return mark_safe(output)  # nosec


class ForeignKeyWidget(Select):

    def __init__(self, *args, **kwargs):
        self.model = kwargs.pop('model', None)
        super(ForeignKeyWidget, self).__init__(*args, **kwargs)

    def render(self, name, value, attrs=None):
        output = super(ForeignKeyWidget, self).render(name, value, attrs)
        if value:
            instance = self.model.objects.get(pk=value)
            instance_url = reverse(
                'admin:{0}_{1}_change'.format(
                    instance._meta.app_label, instance._meta.model_name),
                args=[instance.pk])
            output += format_html('&nbsp;<a href="{0}">{1}</a>&nbsp;',
                                  instance_url,
                                  str(instance))
        return mark_safe(output)  # nosec


class BitcoinAddressWidget(Widget):

    def __init__(self, *args, **kwargs):
        self.network = kwargs.pop('network', None)
        super(BitcoinAddressWidget, self).__init__(*args, **kwargs)

    def render(self, name, value, attrs=None):
        if value:
            output = format_html(
                '<a target="_blank" href="{0}">{1}</a>',
                blockcypher.get_address_url(value, self.network),
                value)
        else:
            output = '-'
        return mark_safe(output)  # nosec


class BitcoinTransactionWidget(Widget):

    def __init__(self, *args, **kwargs):
        self.network = kwargs.pop('network', None)
        super(BitcoinTransactionWidget, self).__init__(*args, **kwargs)

    def render(self, name, value, attrs=None):
        if value:
            output = format_html(
                '<a target="_blank" href="{0}">{1}</a>',
                blockcypher.get_tx_url(value, self.network),
                value)
        else:
            output = '-'
        return mark_safe(output)  # nosec


class BitcoinTransactionArrayWidget(Widget):

    def __init__(self, *args, **kwargs):
        self.network = kwargs.pop('network', None)
        super(BitcoinTransactionArrayWidget, self).__init__(*args, **kwargs)

    def render(self, name, value, attrs=None):
        output = ''
        if value:
            for tx_id in value.split(','):
                output += format_html(
                    '<a target="_blank" href="{0}">{1}</a><br>',
                    blockcypher.get_tx_url(tx_id, self.network),
                    tx_id)
        else:
            output = '-'
        return mark_safe(output)  # nosec


class ReadOnlyAdminWidget(Widget):

    def __init__(self, *args, **kwargs):
        self.instance = kwargs.pop('instance', None)
        super(ReadOnlyAdminWidget, self).__init__(*args, **kwargs)

    def render(self, name, value, attrs=None):
        if self.instance:
            try:
                value = getattr(self.instance, 'get_{0}_display'.format(name))()
            except AttributeError:
                value = getattr(self.instance, name)
        return str(value)

    def value_from_datadict(self, data, files, name):
        return data.get(name, '')

    def decompress(self, value):
        return []
