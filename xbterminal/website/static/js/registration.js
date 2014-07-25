var Registration = (function () {
    'use strict';

    var exchangeRate;
    var getExchangeRate = function () {
        $.ajax({
            url: 'https://cryptopay.me/api/v1/rates',
            success: function (data) {
                exchangeRate = data.GBP;
            }
        });
    };

    var calculateSum = function () {
        var quantity = $('#id_quantity').val();
        var price = 200.00;
        var sumGBP = quantity * price;
        var sumBTC = sumGBP / exchangeRate;
        $('#sum-gbp').text(sumGBP.toFixed(2));
        $('#sum-btc').text(sumBTC.toFixed(3));
        $('#calculation').show();
    };

    var init = function () {
        $('#id_delivery_address_differs').on('click', function () {
            $('#delivery-address-group').toggle();
        });

        $('#id_quantity').on('change', function () {
            calculateSum();
        });

        $('#merchant-form').on('submit', function (event) {
            event.preventDefault();
            $('#error-message').hide();
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
                    $('#error-message').show().html(data.errors);
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
