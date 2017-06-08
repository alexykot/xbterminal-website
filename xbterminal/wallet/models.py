from __future__ import unicode_literals

from django.db import models
from django.db.transaction import atomic

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


class WalletAccount(models.Model):
    """
    Represents BIP32 account entity
    """
    parent_key = models.ForeignKey(
        WalletKey,
        on_delete=models.PROTECT)
    index = models.PositiveIntegerField()

    class Meta:
        unique_together = ('parent_key', 'index')

    def __str__(self):
        return self.path

    @property
    def path(self):
        return "{parent}/{index}".format(
            parent=self.parent_key.path,
            index=self.index)

    @atomic
    def save(self, *args, **kwargs):
        if not self.pk and not self.index:
            self.index = self.parent_key.walletaccount_set.count()
        super(WalletAccount, self).save(*args, **kwargs)
