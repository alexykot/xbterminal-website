from django.conf.urls import url

from website import views

urlpatterns = [
    url(r'^$', views.LandingView.as_view(), name='landing'),
    url(r'^android-app$', views.android_app, name='android_app'),
    url(r'^ios-app$', views.ios_app, name='ios_app'),
    url(r'^privacy/$', views.PrivacyPolicyView.as_view(), name='privacy'),
    url(r'^terms/$', views.TermsConditionsView.as_view(), name='terms'),
    url(r'^team/$', views.TeamView.as_view(), name='team'),
    url(r'^contact/$', views.ContactView.as_view(), name='contact'),
    url(r'^feedback/$', views.FeedbackView.as_view(), name='feedback'),
    url(r'^login/$', views.LoginView.as_view(), name='login'),
    url(r'^logout/$', views.LogoutView.as_view(), name='logout'),
    url(r'^reset_password/$', views.ResetPasswordView.as_view(), name='reset_password'),
    url(r'^registration/$', views.RegistrationView.as_view(), name='registration'),
    url(r'^registration/validate/$', views.RegValidationView.as_view(), name='reg_validation'),
    url(r'^profile/$', views.UpdateProfileView.as_view(), name='profile'),
    url(r'^change_password/$', views.ChangePasswordView.as_view(), name='change_password'),
    url(r'^verification/$', views.VerificationView.as_view(), name='verification'),
    url(r'^verification/(?P<merchant_pk>\d+)/(?P<name>.+)$',
        views.VerificationFileView.as_view(),
        name='verification_file'),

    url(r'^accounts/$', views.AccountListView.as_view(), name='accounts'),
    url(r'^accounts/(?P<pk>\d+)/$', views.EditAccountView.as_view(), name='account'),
    url(r'^accounts/(?P<pk>\d+)/add_funds/$', views.AddFundsView.as_view(), name='add_funds'),

    url(r'^devices/$', views.DeviceList.as_view(), name='devices'),
    url(r'^devices/activate/$', views.ActivateDeviceView.as_view(), name='activate_device'),
    url(r'^devices/(?P<device_key>[0-9a-zA-Z]{8,64})/activation/$',
        views.ActivationView.as_view(),
        name='activation'),
    url(r'^devices/(?P<device_key>[0-9a-zA-Z]{8,64})/$',
        views.UpdateDeviceView.as_view(),
        name='device'),
    url(r'^devices/(?P<device_key>[0-9a-zA-Z]{8,64})/transactions/$',
        views.DeviceTransactionsView.as_view(),
        name='device_transactions'),
    url(r'^devices/(?P<device_key>[0-9a-zA-Z]{8,64})/report/$',
        views.ReportView.as_view(),
        name='report'),
]
