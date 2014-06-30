from django.forms.widgets import ChoiceFieldRenderer, RadioChoiceInput, RendererMixin,\
                                 Select, TextInput, TimeInput
from django.utils.encoding import force_text
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.html import escapejs


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
    def render(self, name, value, attrs=None):
        rendered = super(PercentWidget, self).render(name, value, attrs=attrs)
        return rendered + mark_safe(u'<script type="text/javascript">'
                                    '$(document).ready(function(){'
                                        '$("#id_%s").percentWidget();'
                                    '})'
                                    '</script>' % escapejs(name))

    class Media:
        js = ('jquery-ui/slider.min.js',
              'js/percentWidget.js')
        css = {'all': ("https://code.jquery.com/ui/1.10.3/themes/smoothness/jquery-ui.css",)}


class TimeWidget(TimeInput):
    def render(self, name, value, attrs=None):
        rendered = super(TimeWidget, self).render(name, value, attrs=attrs)
        return rendered + mark_safe(u'<script type="text/javascript">'
                                    '$(document).ready(function(){'
                                        '$("#id_%s").ptTimeSelect();'
                                    '})'
                                    '</script>' % escapejs(name))

    class Media:
        js = ('jquery.ptTimeSelect/jquery.ptTimeSelect.js',)
        css = {'all': ("https://code.jquery.com/ui/1.10.3/themes/smoothness/jquery-ui.css",
                       "jquery.ptTimeSelect/jquery.ptTimeSelect.css")}
