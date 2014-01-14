from rest_framework import serializers

from website.models import Transaction


class TransactionSerializer(serializers.ModelSerializer):
    receipt_url = serializers.CharField(source='get_api_url', read_only=True)
    device = serializers.SlugRelatedField(slug_field='key')

    class Meta:
        model = Transaction
