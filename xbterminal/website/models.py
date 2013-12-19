# -*- coding: utf-8 -*-
from django.db import models
from django.conf import settings


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
    user = models.OneToOneField(settings.AUTH_USER_MODEL, null=True)
    company_name = models.CharField(max_length=254)
    business_address = models.CharField(max_length=1000)
    business_address1 = models.CharField(max_length=1000, blank=True, default='')
    business_address2 = models.CharField(max_length=1000, blank=True, default='')
    town = models.CharField(max_length=1000)
    county = models.CharField(max_length=1000, blank=True, default='')
    post_code = models.CharField(max_length=1000)
    contact_name = models.CharField(max_length=1000)
    contact_phone = models.CharField(max_length=1000)
    contact_email = models.EmailField(unique=True)

    def __unicode__(self):
        return self.company_name
