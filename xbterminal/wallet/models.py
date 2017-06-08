from __future__ import unicode_literals

from django.db import models
from django.db.transaction import atomic

from wallet.enums import BIP44_PURPOSE, BIP44_COIN_TYPES
from wallet.utils.keys import generate_p2pkh_script


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
            purpose=BIP44_PURPOSE,
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


class Address(models.Model):

    wallet_account = models.ForeignKey(
        WalletAccount,
        on_delete=models.PROTECT)
    is_change = models.BooleanField()
    index = models.PositiveIntegerField()
    address = models.CharField(
        max_length=50,
        unique=True)

    class Meta:
        ordering = ['wallet_account', 'is_change', 'index']
        unique_together = ['wallet_account', 'is_change', 'index']
        verbose_name_plural = 'addresses'

    def __str__(self):
        return self.address

    @property
    def relative_path(self):
        return '{account}/{change}/{index}'.format(
            account=self.wallet_account.index,
            change=int(self.is_change),
            index=self.index)

    def get_script(self, as_address=True):
        """
        Returns script or address
        """
        return generate_p2pkh_script(
            self.wallet_account.parent_key.private_key,
            self.relative_path,
            as_address=as_address)

    @atomic
    def save(self, *args, **kwargs):
        if not self.pk:
            self.index = self.wallet_account.address_set.\
                filter(is_change=self.is_change).count()
            self.address = self.get_script(as_address=True)
        super(Address, self).save(*args, **kwargs)
