from __future__ import unicode_literals

from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.db.models import Max
from django.db.transaction import atomic

from wallet.constants import BIP44_PURPOSE, BIP44_COIN_TYPES, MAX_INDEX
from wallet.utils.keys import derive_key, generate_p2pkh_script


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

    def get_private_key(self):
        """
        Returns corresponding private key (BIP32Node instance)
        """
        return derive_key(self.wallet_account.parent_key.private_key,
                          self.relative_path)

    @atomic
    def save(self, *args, **kwargs):
        if not self.pk:
            self.index = self.wallet_account.address_set.\
                filter(is_change=self.is_change).count()
            self.address = self.get_script(as_address=True)
        super(Address, self).save(*args, **kwargs)

    @classmethod
    @atomic
    def create(cls, coin_name, is_change=False):
        """
        Accepts:
            coin_name: coin name (currency name)
            is_change: boolean
        Returns:
            address: Address instance
        """
        coin_type = BIP44_COIN_TYPES.for_constant(coin_name).value
        try:
            wallet_key = WalletKey.objects.get(coin_type=coin_type)
        except WalletKey.DoesNotExist:
            raise ImproperlyConfigured
        try:
            account = wallet_key.walletaccount_set.\
                filter(address__is_change=is_change).\
                annotate(address_max_index=Max('address__index')).\
                exclude(address_max_index__gte=MAX_INDEX).\
                latest('index')
        except WalletAccount.DoesNotExist:
            account = wallet_key.walletaccount_set.create()
        return account.address_set.create(is_change=is_change)
