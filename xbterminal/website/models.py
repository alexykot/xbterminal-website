# -*- coding: utf-8 -*-
from django.db import models
from django.conf import settings
from django.core.urlresolvers import reverse


class Contact(models.Model):
    """
    Simple contact info from users
    """
    email = models.EmailField(max_length=254)
    add_date = models.DateTimeField(auto_now_add=True)
    message = models.TextField()

    def __unicode__(self):
        return self.message


class MerchantAccount(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name="merchant", null=True)
    company_name = models.CharField(max_length=254)
    business_address = models.CharField(max_length=1000)
    business_address1 = models.CharField('', max_length=1000, blank=True, default='')
    business_address2 = models.CharField('', max_length=1000, blank=True, default='')
    town = models.CharField(max_length=1000)
    county = models.CharField(max_length=1000, blank=True, default='')
    post_code = models.CharField(max_length=1000)
    contact_name = models.CharField(max_length=1000)
    contact_phone = models.CharField(max_length=1000)
    contact_email = models.EmailField(unique=True)

    def __unicode__(self):
        return self.company_name

    def get_first_device_url(self):
        if not self.device_set.exists():
            return reverse('website:create_device')
        return reverse('website:device', kwargs={'number': 1})


class Device(models.Model):
    merchant = models.ForeignKey(MerchantAccount)

    name = models.CharField(max_length=100)
    comment = models.CharField(max_length=100)
    instantfiat = models.CharField('instantfiat service used', max_length=100)
    api_key = models.CharField('instantfiat service API key', max_length=100)
    percent = models.SmallIntegerField('percent to convert to fiat')
    bitcoin_address = models.CharField('bitcoin address to send to', max_length=100)

    class Meta:
        ordering = ['id']

    def __unicode__(self):
        return 'device: %s' % self.name
