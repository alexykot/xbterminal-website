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
  name = models.CharField(max_length=255,blank=False)
  contact_phone = models.CharField(max_length=20,blank=False)
  email = models.EmailField(max_length=254,blank=False) # using for login
  business_name = models.CharField(max_length=1000,blank=False)
  add_date = models.DateTimeField(auto_now_add=True)
  add_date.editable=True # hack to show datetime in admin
  is_enabled = models.BooleanField(blank=True,default=False)
  house_name = models.CharField(max_length=255,blank=True)
  house_number = models.CharField(max_length=50,blank=True)
  street_address = models.CharField(max_length=1000,blank=False)
  street_address2 = models.CharField(max_length=1000,blank=True)
  town = models.CharField(max_length=100,blank=False)
  country = models.CharField(max_length=100,blank=True)
  postcode = models.CharField(max_length=50,blank=True)
  def __unicode__(self):
    return self.name
  class Meta:
    db_table = "website_merch_acc"
