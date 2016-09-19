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
    message = create_html_message(
        'XBTerminal registration info',
        'email/registration_info.html',
        {'merchant': merchant},
        settings.DEFAULT_FROM_EMAIL,
        settings.CONTACT_EMAIL_RECIPIENTS)
    message.send(fail_silently=False)


def send_reset_password_email(email, password):
    message = create_html_message(
        _('Reset password for xbterminal.io'),
        'email/reset_password.html',
        {'password': password},
        settings.DEFAULT_FROM_EMAIL,
        [email])
    message.send(fail_silently=False)


def send_verification_info(merchant, documents):
    """
    Send notification about KYC documents (for admin)
    Accepts:
        merchant: MerchantAccount instance
        documents: list of KYCDocument instances
    """
    message = create_html_message(
        _('KYC documents status changed'),
        'email/admin_verification.html',
        {'merchant': merchant, 'documents': documents},
        settings.DEFAULT_FROM_EMAIL,
        settings.CONTACT_EMAIL_RECIPIENTS)
    message.send(fail_silently=False)


def send_verification_notification(merchant):
    """
    Send KYC notification to merchant
    Accepts:
        merchant: MerchantAccount instance
    """
    message = create_html_message(
        _('KYC documents notification'),
        'email/verification.html',
        {'merchant': merchant},
        settings.DEFAULT_FROM_EMAIL,
        [merchant.user.email])
    message.send(fail_silently=False)


def send_withdrawal_request(account, amount):
    """
    Send withdrawal request details to admin
    """
    message = create_html_message(
        _('Withdrawal request'),
        'email/withdrawal.html',
        {'account': account, 'amount': amount},
        settings.DEFAULT_FROM_EMAIL,
        settings.CONTACT_EMAIL_RECIPIENTS)
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
    message = create_html_message(
        _('Balance mismatch'),
        'email/admin_balance_notification.html',
        {'info': info},
        settings.DEFAULT_FROM_EMAIL,
        settings.CONTACT_EMAIL_RECIPIENTS)
    message.send(fail_silently=False)
