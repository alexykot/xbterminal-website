import os

from django.forms.widgets import (
    ChoiceFieldRenderer,
    RadioChoiceInput,
    RendererMixin,
    Select, TextInput, TimeInput,
    FileInput)
from django.utils.encoding import force_text
from django.utils.html import format_html
from django.utils.safestring import mark_safe


class ButtonGroupChoiceInput(RadioChoiceInput):
    def render(self, name=None, value=None, attrs=None, choices=()):
        name = name or self.name
        value = value or self.value
        attrs = attrs or self.attrs
        if 'id' in self.attrs:
            label_for = format_html(' for="{0}_{1}"', self.attrs['id'], self.index)
        else:
            label_for = ''

        if self.is_checked():
            template = '<label{0} class="btn btn-primary active">{1} {2}</label>'
        else:
            template = '<label{0} class="btn btn-primary">{1} {2}</label>'

        return format_html(template, label_for, self.tag(), self.choice_label)


class ButtonGroupFieldRenderer(ChoiceFieldRenderer):
    choice_input_class = ButtonGroupChoiceInput

    def render(self):
        id_ = self.attrs.get('id', None)
        if id_:
            start_tag = format_html('<div><div id="{0}" class="btn-group" data-toggle="buttons">', id_)
        else:
            start_tag = '<div><div class="btn-group" data-toggle="buttons">'
        output = [start_tag]

        for widget in self:
            output.append(format_html('{0}', force_text(widget)))
        output.append('</div></div>')
        return mark_safe('\n'.join(output))


class ButtonGroupRadioSelect(RendererMixin, Select):
    renderer = ButtonGroupFieldRenderer

    def render(self, name, value, attrs=None, choices=()):
        return self.get_renderer(name, value, attrs, choices).render()


class PercentWidget(TextInput):

    class Media:
        js = ['lib/jquery-ui.min.js', 'js/percent_widget.js']
        css = {'all': ['lib/jquery-ui.min.css']}


class TimeWidget(TimeInput):

    class Media:
        js = ['lib/jquery.ptTimeSelect.js']
        css = {'all': ['lib/jquery-ui.min.css', 'lib/jquery.ptTimeSelect.css']}


class FileWidget(FileInput):

    def render(self, name, value, attrs=None):
        template = '''
            <div class="file-widget">
                <div class="file-dd">
                    Drag and drop here or click to browse files {0}
                </div>
                <ul class="file-uploaded">{1}</ul>
            </div>'''
        file_input = super(FileWidget, self).render(name, value, attrs)
        if value:
            list_item = format_html(
                '<li>{0}<a class="glyphicon glyphicon-remove file-remove" data-name="{1}"></a></li>',
                os.path.basename(value.name).encode('ascii', 'ignore'),
                name)
        else:
            list_item = ''
        output = format_html(template, file_input, list_item)
        return mark_safe(output)
