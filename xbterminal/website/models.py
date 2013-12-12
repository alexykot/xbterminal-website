"""
"""
# -*- coding: utf-8 -*-
from django.db import models

class Contact(models.Model):
  """
  Simple contact info from users
  """
  email = models.EmailField(max_length=254)
  add_date = models.DateTimeField(auto_now_add=True)
  add_date.editable=True # hack to show datetime in admin
  message = models.TextField()
  def __unicode__(self):
    return self.message
  class Meta:
    db_table = "website_contact"

class MerchantAccount(models.Model):
  """
  Merchant account model
  """
  name = models.CharField(max_length=255)
  contact_phone = models.CharField(max_length=20)
  # using for login
  email = models.EmailField(max_length=254)
  business_name = models.CharField(max_length=1000)
  class Meta:
    db_table = "website_merch_acc"

class MerchantAccountAddress(models.Model):
  """
  Address for merchant account
  """
  merchant_account = models.ForeignKey(MerchantAccount)
  house_name = models.CharField(max_length=255,null=True)
  house_number = models.CharField(max_length=50,null=True)
  street_address = models.CharField(max_length=1000)
  street_address2 = models.CharField(max_length=1000,null=True)
  town = models.CharField(max_length=100)
  country = models.CharField(max_length=100,null=True)
  postcode = models.CharField(max_length=50,null=True)
  class Meta:
    db_table = "website_merch_acc_adr"
