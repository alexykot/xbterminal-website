from django import forms

from website.validators import validate_bitcoin


class BCAddressField(forms.CharField):
    def __init__(self, *args, **kwargs):
        super(BCAddressField, self).__init__(*args, **kwargs)

    def validate(self, value):
        super(BCAddressField, self).validate(value)

        if value in self.empty_values and not self.required:
            return

        validate_bitcoin(value)
