from __future__ import unicode_literals

from django.db import models

from wallet.enums import BIP44_COIN_TYPES


class WalletKey(models.Model):
    """
    Represents BIP32 extended key
    """
    coin_type = models.PositiveSmallIntegerField(
        choices=BIP44_COIN_TYPES,
        unique=True)
    private_key = models.CharField(
        max_length=120,
        unique=True,
        help_text='Private key, WIF')
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.path

    @property
    def path(self):
        return "{purpose}'/{coin}'".format(
            purpose=0,
            coin=self.coin_type)
