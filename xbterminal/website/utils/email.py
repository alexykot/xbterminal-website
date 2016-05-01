from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.utils.html import strip_tags
from django.template.loader import render_to_string
from django.utils.translation import ugettext as _


def create_html_message(subject, template, context,
                        from_email, recipient_list,
                        attachments=None):
    html_content = render_to_string(template, context)
    text_content = strip_tags(html_content)
    email = EmailMultiAlternatives(
        subject, text_content, from_email, recipient_list)
    email.attach_alternative(html_content, 'text/html')
    if attachments:
        for file_name, file_data, file_type in attachments:
            email.attach(file_name, file_data, file_type)
    return email


def send_reconciliation_email(recipient, date, context, files):
    email = create_html_message(
        _('XBTerminal reconciliation report, {0}').format(
            date.strftime('%d %b %Y')),
        'email/reconciliation.html',
        context,
        settings.DEFAULT_FROM_EMAIL,
        [recipient],
        attachments=files)
    email.send(fail_silently=False)


def send_error_message(tb=None, order=None):
    """
    Accepts:
        tb: traceback object
        order: PaymentOrder or WithdrawalOrder instance
    """
    email = create_html_message(
        'XBTerminal - error',
        'email/error.html',
        {'traceback': tb, 'order': order},
        settings.DEFAULT_FROM_EMAIL,
        settings.CONTACT_EMAIL_RECIPIENTS)
    email.send(fail_silently=False)


def send_registration_email(email, password):
    """
    Send merchant registration email
    """
    message = create_html_message(
        _('Registration for XBTerminal.io'),
        'email/registration.html',
        {'email': email, 'password': password},
        settings.DEFAULT_FROM_EMAIL,
        [email])
    message.send(fail_silently=False)


def send_registration_info(merchant):
    """
    Send merchant registration info (for admin)
    """
    context = {
        'merchant': merchant,
    }
    email = create_html_message(
        'XBTerminal registration info',
        'email/registration_info.html',
        context,
        settings.DEFAULT_FROM_EMAIL,
        settings.CONTACT_EMAIL_RECIPIENTS)
    email.send(fail_silently=False)


def send_reset_password_email(email, password):
    message = create_html_message(
        _('Reset password for xbterminal.io'),
        'email/reset_password.html',
        {'password': password},
        settings.DEFAULT_FROM_EMAIL,
        [email])
    message.send(fail_silently=False)


def send_contact_email(form_data):
    message = create_html_message(
        _('Message from xbterminal.io'),
        'email/contact.html',
        form_data,
        settings.DEFAULT_FROM_EMAIL,
        settings.CONTACT_EMAIL_RECIPIENTS)
    message.send(fail_silently=False)


def send_feedback_email(form_data):
    message = create_html_message(
        _('Message from xbterminal.io'),
        'email/feedback.html',
        form_data,
        settings.DEFAULT_FROM_EMAIL,
        settings.CONTACT_EMAIL_RECIPIENTS)
    message.send(fail_silently=False)


def send_balance_admin_notification(info):
    """
    Send email to admin if balance mismatch detected
    Accepts:
        info: dict
    """
    email = create_html_message(
        _('Balance mismatch'),
        'email/admin_balance_notification.html',
        {'info': info},
        settings.DEFAULT_FROM_EMAIL,
        settings.CONTACT_EMAIL_RECIPIENTS)
    email.send(fail_silently=False)
