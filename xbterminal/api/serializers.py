from rest_framework import serializers

from website.models import Transaction


class TransactionSerializer(serializers.ModelSerializer):
    device = serializers.SlugRelatedField(slug_field='key')

    class Meta:
        model = Transaction
