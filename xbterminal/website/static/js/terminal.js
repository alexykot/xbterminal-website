var backspace = 8;
var numKeys = {
    48: 0,
    49: 1,
    50: 2,
    51: 3,
    52: 4,
    53: 5,
    54: 6,
    55: 7,
    56: 8,
    57: 9,
    96: 0,
    97: 1,
    98: 2,
    99: 3,
    100: 4,
    101: 5,
    102: 6,
    103: 7,
    104: 8,
    105: 9
};

var paymentInit = function (form) {
    $.ajax({
        url: form.attr('action'),
        method: 'POST',
        data: {
            amount: form.find('[name="amount"]').val()
        },
        headers: {
            'X-CSRFToken': form.find('[name="csrfmiddlewaretoken"]').val()
        }
    }).done(function (data) {
        form.hide();
        $('.payment-init').show();
        $('.fiat-amount').text(data.fiat_amount.toFixed(2));
        $('.mbtc-amount').text(data.mbtc_amount.toFixed(2));
        $('.exchange-rate').text(data.exchange_rate.toFixed(3));
        $('.payment-request').
            attr('alt', data.payment_uri).
            attr('src', data.qr_code_src);
        paymentCheck(data.check_url);
    });
};

var currentCheck;
var paymentCheck = function (checkURL) {
    currentCheck = setInterval(function () {
        $.ajax({
            url: checkURL
        }).done(function (data) {
            if (data.paid === 1) {
                clearInterval(currentCheck);
                $('.payment-init').hide();
                $('.payment-success').show();
                $('.payment-message').text(data.message);
                $('.payment-receipt').
                    attr('alt', data.receipt_url).
                    attr('src', data.qr_code_src);
            }
        });
    }, 2000);
};

var paymentReset = function () {
    if (currentCheck) {
        clearInterval(currentCheck);
    }
    $('.enter-amount [name="amount"]').val('0.00');
    $('.payment-init, .payment-success').hide();
    $('.enter-amount').show();
};


$(function () {

    $('.enter-amount [name="amount"]').on('keydown', function (event) {
        var currentAmount = parseFloat($(this).val());
        var amount;
        if (event.which === backspace) {
            event.preventDefault();
            amount = Math.floor(currentAmount * 10) / 100;
            $(this).val(amount.toFixed(2));
        } else if (event.which in numKeys) {
            event.preventDefault();
            amount = currentAmount * 10 + 0.01 * numKeys[event.which];
            $(this).val(amount.toFixed(2));
        }
    });

    $('.enter-amount').on('submit', function (event) {
        event.preventDefault();
        var form = $(this);
        var amount = parseFloat(form.find('[name="amount"]').val());
        if (amount < 0.01) {
            return false;
        }
        paymentInit(form);
    });

    $('.payment-reset').on('click', function (event) {
        event.preventDefault();
        paymentReset();
    });

    $('.enter-amount [name="amount"]').val('0.00').focus();
});
