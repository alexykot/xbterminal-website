from django.http import Http404
from django.utils import timezone

from rest_framework import status, viewsets, mixins
from rest_framework.decorators import detail_route
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_jwt.authentication import JSONWebTokenAuthentication

from website.forms import SimpleMerchantRegistrationForm
from website.models import MerchantAccount
from website.utils import email, kyc

from api.serializers import (
    MerchantSerializer,
    KYCDocumentsSerializer,
    ThirdPartyDeviceSerializer,
    TransactionSerializer)
from api.views_v2 import PaymentViewSet as Version2PaymentViewSet


class MerchantViewSet(mixins.RetrieveModelMixin,
                      viewsets.GenericViewSet):

    queryset = MerchantAccount.objects.all()
    serializer_class = MerchantSerializer
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        if self.action == 'create':
            return
        super(MerchantViewSet, self).check_permissions(request)

    def check_object_permissions(self, request, obj):
        merchant = getattr(self.request.user, 'merchant')
        if not merchant or obj.pk != merchant.pk:
            self.permission_denied(request)
        super(MerchantViewSet, self).check_object_permissions(request, obj)

    def create(self, *args, **kwargs):
        form = SimpleMerchantRegistrationForm(data=self.request.data)
        if not form.is_valid():
            return Response(form.errors,
                            status=status.HTTP_400_BAD_REQUEST)
        merchant = form.save()
        email.send_registration_info(merchant)
        serializer = self.get_serializer(merchant)
        return Response(serializer.data,
                        status=status.HTTP_201_CREATED)

    @detail_route(methods=['POST'])
    def upload_kyc(self, *args, **kwargs):
        merchant = self.get_object()
        if not merchant.has_managed_cryptopay_profile:
            raise Http404
        if merchant.verification_status != 'unverified':
            raise Http404
        kyc_serializer = KYCDocumentsSerializer(
            data=self.request.data,
            context={'merchant': merchant})
        kyc_serializer.is_valid(raise_exception=True)
        uploaded = kyc_serializer.save()
        kyc.upload_documents(merchant, uploaded)
        serializer = self.get_serializer(merchant)
        return Response(serializer.data)


class MerchantMixin(object):

    def initial(self, *args, **kwargs):
        self.merchant = getattr(self.request.user, 'merchant', None)
        if not self.merchant:
            self.permission_denied(self.request)
        super(MerchantMixin, self).initial(*args, **kwargs)


class DeviceViewSet(MerchantMixin,
                    mixins.CreateModelMixin,
                    viewsets.GenericViewSet):

    lookup_field = 'key'
    serializer_class = ThirdPartyDeviceSerializer
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.merchant.device_set.exclude(status='suspended')

    def get_serializer_context(self):
        context = super(DeviceViewSet, self).get_serializer_context()
        context['merchant'] = self.merchant
        return context

    def retrieve(self, *args, **kwargs):
        device = self.get_object()
        device.last_activity = timezone.now()
        device.save()
        serializer = self.get_serializer(device)
        return Response(serializer.data)

    @detail_route(methods=['GET'])
    def list_transactions(self, *args, **kwargs):
        device = self.get_object()
        serializer = TransactionSerializer(
            device.get_transactions(), many=True)
        return Response(serializer.data)


class PaymentViewSet(Version2PaymentViewSet):

    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
