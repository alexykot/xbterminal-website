var Registration = (function () {
    'use strict';

    var exchangeRate;
    var getExchangeRate = function () {
        $.ajax({
            url: 'https://cryptopay.me/api/v1/rates',
            success: function (data) {
                exchangeRate = data.GBP;
                calculateSum();
            }
        });
    };

    var calculateSum = function () {
        var quantity = $('#id_quantity').val();
        var price = $('#calculation').data('price');
        var sumGBP = quantity * price;
        var sumBTC = sumGBP / exchangeRate * 1000;
        $('#sum-gbp').text(sumGBP.toFixed(2));
        $('#sum-mbtc').text(sumBTC.toFixed(2));
    };

    var showErrors = function (formErrors) {
        var errorMessages = $('#error-messages').empty().show();
        var fieldList = $('<ul/>').appendTo(errorMessages);
        for (var fieldName in formErrors) {
            var fieldLabel = $('label[for="id_' + fieldName + '"]').text();
            var fieldItem = $('<li/>').text(fieldLabel).appendTo(fieldList);
            var fieldErrorList = $('<ul/>').appendTo(fieldItem);
            $.each(formErrors[fieldName], function (i, error) {
                $('<li/>').text(error).appendTo(fieldErrorList);
            });
        }
    };
    var clearErrors = function () {
        $('#error-messages').empty().hide();
    };

    var getTradingAddress = function () {
        var addressFieldNames = [
            'business_address',
            'business_address1',
            'town',
            'post_code',
            'county',
        ]
        var result = [];
        $.each(addressFieldNames, function (i, fieldName) {
            var fieldValue = $('[name="' + fieldName + '"]').val();
            if (fieldValue) {
                result.push(fieldValue);
            }
        });
        var countryCode = $('[name="country"]').val();
        var countryOption = $('[name="country"] option[value="' + countryCode + '"]');
        result.push(countryOption.text());
        return result;
    };

    var validateRegistrationStep1 = function () {
        var form = $('#merchant-form');
        var formErrors = {};
        // Pre-validation
        var regtype = form.find('[name="regtype"]').val();
        if (regtype == 'default') {
            $('[name="company_name_copy"]').val($('[name="company_name"]').val());
        } else if (regtype == 'terminal') {
            if (!$('#terms').is(':checked')) {
                alert('Please accept terms & conditions');
                return false;
            }
            $('#delivery-address-preview').html(getTradingAddress().join('<br>'));
        }
        // Validation
        var validator = form.validate({
            showErrors: function (errorMap, errorList) {
                for (var fieldName in errorMap) {
                    formErrors[fieldName] = [errorMap[fieldName]];
                }
            },
            onsubmit: false,
            onfocusout: false,
            onkeyup: false,
            onclick: false
        });
        if (validator.form()) {
            clearErrors();
            return true;
        } else {
            showErrors(formErrors);
            return false;
        }
    };

    var init = function () {
        $('#next-step').on('click', function () {
            if (validateRegistrationStep1()) {
                $('#registration-step-1').hide();
                $('#registration-step-2').show();
                $('#step span').text('2');
            }
        });
        $('#previous-step').on('click', function () {
            $('#registration-step-2').hide();
            $('#registration-step-1').show();
            $('#step span').text('1');
        });

        $('#id_delivery_address_differs').on('click', function () {
            $('#delivery-address-group').toggle();
        });

        $('#id_quantity').on('change', function () {
            calculateSum();
        });

        $('#merchant-form').on('submit', function (event) {
            event.preventDefault();
            if (!$('#terms').is(':checked')) {
                alert('Please accept terms & conditions');
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
    };
    return {init: init};
}());

$(function () {
    Registration.init();
});
