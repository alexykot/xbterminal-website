from django import forms
from django.db import models

from website.validators import validate_bitcoin

from south.modelsinspector import add_introspection_rules


class BCAddressField(forms.CharField):
    def __init__(self, *args, **kwargs):
        super(BCAddressField, self).__init__(*args, **kwargs)

    def validate(self, value):
        super(BCAddressField, self).validate(value)

        if value in self.empty_values and not self.required:
            return

        validate_bitcoin(value)


class FirmwarePathField(models.FilePathField):

    def __init__(self, path_south="/var/firmware", *args, **kwargs):
        self.path_south = path_south
        super(FirmwarePathField, self).__init__(*args, **kwargs)


add_introspection_rules([
    ([FirmwarePathField], [], {"path": ["path_south", {}]}),
], ["^website\.fields\.FirmwarePathField"])
