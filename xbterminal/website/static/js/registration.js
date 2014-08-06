var Registration = (function () {
    'use strict';

    var exchangeRate;
    var getExchangeRate = function () {
        $.ajax({
            url: 'https://cryptopay.me/api/v1/rates',
            success: function (data) {
                exchangeRate = data.GBP;
                calculateSubTotal();
            }
        });
    };

    var subTotal_GBP, subTotal_mBTC;
    var formatAmounts = function (amount_GBP, amount_mBTC) {
        var gbp = '£<span class="gbp">'
            + amount_GBP.toFixed(2)
            + '</span> GBP';
        if ($('[name="payment_method"]:checked').val() == 'bitcoin') {
            var mbtc = '฿<span class="mbtc">'
                + amount_mBTC.toFixed(5)
                + '</span> mBTC';
            return gbp + ' / ' + mbtc;
        } else {
            return gbp;
        }
    };
    var calculateSubTotal = function () {
        var quantity = $('[name="quantity"]').val();
        var price = $('#calculation').data('price');
        subTotal_GBP = quantity * price;
        subTotal_mBTC = subTotal_GBP / exchangeRate * 1000;
        $('#calculation').html(formatAmounts(subTotal_GBP, subTotal_mBTC));
    };

    var showErrors = function (formErrors) {
        var errorMessages = $('#error-messages').empty().show();
        var fieldList = $('<ul/>').appendTo(errorMessages);
        for (var fieldName in formErrors) {
            var fieldLabel = $('label[for="id_' + fieldName + '"]').text();
            var fieldItem = $('<li/>').text(fieldLabel).appendTo(fieldList);
            var fieldErrorList = $('<ul/>').appendTo(fieldItem);
            $.each(formErrors[fieldName], function (i, error) {
                $('<li/>').html(error).appendTo(fieldErrorList);
            });
        }
    };
    var clearErrors = function () {
        $('#error-messages').empty().hide();
    };

    var billingAddressFields = [
        'company_name',
        'business_address',
        'business_address1',
        'town',
        'county',
        'post_code',
        'country'
    ];
    var deliveryAddressFields = [
        'company_name',
        'delivery_address',
        'delivery_address1',
        'delivery_town',
        'delivery_county',
        'delivery_post_code',
        'delivery_country'
    ];
    var getAddress = function (addressFieldNames) {
        var result = [];
        $.each(addressFieldNames, function (i, fieldName) {
            var field = $('[name="' + fieldName + '"]');
            var fieldValue;
            if (field.prop('tagName') == 'SELECT') {
                var option = field.find('option[value="' + field.val() + '"]');
                fieldValue = option.text();
            } else {
                fieldValue = field.val();
            }
            if (fieldValue) {
                result.push(fieldValue);
            }
        });
        return result;
    };
    var getBillingAddress = function () {
        return getAddress(billingAddressFields);
    };
    var getDeliveryAddress = function () {
        if ($('[name="delivery_address_differs"]').prop('checked')) {
            return getAddress(deliveryAddressFields);
        } else {
            return getAddress(billingAddressFields);
        }
    };

    var validator;
    var setUpValidator = function () {
        $.validator.addMethod('emailUnique', function (value, element) {
            if (this.optional(element)) {
                return true;
            }
            var isValid;
            $.ajax({
                type: 'GET',
                url: '/registration/validate/',
                data: {email: value},
                beforeSend: function () {
                    $('#loading-image').show();
                },
                success: function (data) {
                    isValid = data.email;
                },
                complete: function () {
                    $('#loading-image').hide();
                },
                async: false
            });
            return isValid;
        }, 'Merchant account with this contact email already exists. Please <a href="/login">login</a> or <a>reset your password</a>.');

        $.validator.addMethod('phone', function (value, element) {
            return this.optional(element) || /^[0-9\s-+().]{5,20}$/.test(value);
        }, 'Please enter a valid phone number.');

        $.validator.addMethod('postCode', function (value, element) {
            return this.optional(element) || /^[a-zA-Z0-9\s-+]{2,10}$/.test(value);
        }, 'Please enter a valid post code.');

        validator = $('#merchant-form').validate({
            showErrors: function (errorMap, errorList) {
                var formErrors = {};
                for (var fieldName in errorMap) {
                    formErrors[fieldName] = [errorMap[fieldName]];
                }
                showErrors(formErrors);
            },
            rules: {
                company_name_copy: 'required',
                contact_email: 'emailUnique',
                contact_phone: 'phone',
                post_code: 'postCode',
                delivery_post_code: 'postCode',
                quantity: {
                    number: true,
                    min: 1
                },
                terms: 'required'
            },
            messages: {
                terms: 'Please accept terms & conditions.'
            },
            onsubmit: false,
            onfocusout: false,
            onkeyup: false,
            onclick: false
        });
    };

    var init = function () {
        $('#continue-step-2').on('click', function (event) {
            event.preventDefault();
            if (validator.form()) {
                clearErrors();
                $('#registration-step-1').hide();
                $('#registration-step-2').show();
                $('#step span').text('2');
                var regtype = $('[name="regtype"]').val();
                if (regtype == 'default') {
                    $('[name="company_name"]').val($('[name="company_name_copy"]').val());
                } else if (regtype == 'terminal') {
                    $('#delivery-address-preview').html(getBillingAddress().join('<br>'));
                }
            }
        });
        $('#continue-step-3').on('click', function (event) {
            event.preventDefault();
            if (validator.form()) {
                clearErrors();
                $('#registration-step-2').hide();
                $('#registration-step-3').show();
                $('#step span').text('3');
                $('#od-quantity').text($('[name="quantity"]').val());
                $('#od-billing-address').html(getBillingAddress().join('<br>'));
                $('#od-delivery-address').html(getDeliveryAddress().join('<br>'));
                $('#od-subtotal').html(formatAmounts(subTotal_GBP, subTotal_mBTC));
                $('#od-vat').html(formatAmounts(subTotal_GBP * 0.2, subTotal_mBTC * 0.2));
                $('#od-total').html(formatAmounts(subTotal_GBP * 1.2, subTotal_mBTC * 1.2));
                $('#od-payment-method').text($('[name="payment_method"]:checked').parent().text());
            }
        });
        $('#back-step-1').on('click', function (event) {
            event.preventDefault();
            $('#registration-step-2').hide();
            $('#registration-step-1').show();
            $('#step span').text('1');
        });
        $('#back-step-2').on('click', function (event) {
            event.preventDefault();
            $('#registration-step-3').hide();
            $('#registration-step-2').show();
            $('#step span').text('2');
        });

        $('[name="delivery_address_differs"]').on('click', function () {
            $('#delivery-address-group').toggle();
        });

        $('#quantity-plus').on('click', function (event) {
            var field = $('[name="quantity"]');
            var currentValue = parseInt(field.val());
            if (isNaN(currentValue)) {
                field.val(1);
            } else {
                field.val(currentValue + 1);
            }
            field.change();
        });
        $('#quantity-minus').on('click', function (event) {
            var field = $('[name="quantity"]');
            var currentValue = parseInt(field.val());
            if (isNaN(currentValue) || currentValue == 1) {
                field.val(1);
            } else {
                field.val(currentValue - 1);
            }
            field.change();
        });

        $('[name="payment_method"]').on('change', function () {
            calculateSubTotal();
        });
        $('[name="quantity"]').on('input change', function () {
            calculateSubTotal();
        });

        $('#merchant-form').on('submit', function (event) {
            event.preventDefault();
            if (!validator.form()) {
                return false;
            }
            clearErrors();
            var form = $(this);
            $.ajax({
                type: 'POST',
                url: form.attr('action'),
                data: form.serialize(),
                beforeSend: function () {
                    $('#loading-image').show();
                }
            }).done(function (data) {
                if (data.result === 'ok') {
                    window.location.href = data.next;
                } else {
                    showErrors(data.errors);
                }
            }).always(function () {
                $('#loading-image').hide();
            });
        });

        getExchangeRate();
        setUpValidator();
    };
    return {init: init};
}());

$(function () {
    Registration.init();
});
